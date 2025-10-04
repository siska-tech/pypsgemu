"""
波形ビューアモジュール

AY-3-8910エミュレータの3チャンネル出力波形オシロスコープ表示を提供します。
リアルタイム波形更新機能とマルチトレース表示を実装しています。
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import tkinter as tk
from tkinter import ttk
from typing import List, Optional, Dict, Any
import threading
import time
from collections import deque
from ..core.types import AY38910Error
from ..api.device import Device


class WaveformViewerError(AY38910Error):
    """波形ビューア関連のエラー"""
    pass


class WaveformBuffer:
    """波形データバッファ
    
    波形表示用のサンプルデータを効率的に管理します。
    循環バッファによる高速なデータ更新を実装しています。
    """
    
    def __init__(self, max_samples: int = 1000, channels: int = 3):
        """WaveformBufferを初期化
        
        Args:
            max_samples: 最大サンプル数
            channels: チャンネル数
        """
        self.max_samples = max_samples
        self.channels = channels
        
        # 各チャンネルのデータバッファ
        self.buffers = [deque(maxlen=max_samples) for _ in range(channels)]
        self.time_buffer = deque(maxlen=max_samples)
        
        # 統計情報
        self.sample_count = 0
        self.last_update_time = 0.0
    
    def add_samples(self, samples: List[float], timestamp: float = None) -> None:
        """サンプルを追加
        
        Args:
            samples: チャンネルごとのサンプル値リスト
            timestamp: タイムスタンプ（Noneで自動生成）
        """
        if len(samples) != self.channels:
            raise WaveformViewerError(f"Expected {self.channels} samples, got {len(samples)}")
        
        if timestamp is None:
            timestamp = time.time()
        
        # 各チャンネルにサンプルを追加
        for i, sample in enumerate(samples):
            self.buffers[i].append(sample)
        
        self.time_buffer.append(timestamp)
        self.sample_count += 1
        self.last_update_time = timestamp
    
    def get_channel_data(self, channel: int) -> tuple:
        """チャンネルデータを取得
        
        Args:
            channel: チャンネル番号
            
        Returns:
            (time_array, amplitude_array) のタプル
        """
        if not (0 <= channel < self.channels):
            raise WaveformViewerError(f"Invalid channel: {channel}")
        
        if len(self.buffers[channel]) == 0:
            return np.array([]), np.array([])
        
        time_array = np.array(list(self.time_buffer))
        amplitude_array = np.array(list(self.buffers[channel]))
        
        return time_array, amplitude_array
    
    def get_all_data(self) -> Dict[str, np.ndarray]:
        """すべてのチャンネルデータを取得
        
        Returns:
            チャンネルデータ辞書
        """
        if len(self.time_buffer) == 0:
            return {'time': np.array([]), 'channels': [np.array([]) for _ in range(self.channels)]}
        
        time_array = np.array(list(self.time_buffer))
        channel_arrays = [np.array(list(buffer)) for buffer in self.buffers]
        
        return {
            'time': time_array,
            'channels': channel_arrays
        }
    
    def clear(self) -> None:
        """バッファをクリア"""
        for buffer in self.buffers:
            buffer.clear()
        self.time_buffer.clear()
        self.sample_count = 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得
        
        Returns:
            統計情報辞書
        """
        return {
            'max_samples': self.max_samples,
            'channels': self.channels,
            'current_samples': len(self.time_buffer),
            'total_samples': self.sample_count,
            'last_update_time': self.last_update_time,
            'buffer_utilization': len(self.time_buffer) / self.max_samples
        }


class WaveformViewer:
    """波形ビューア
    
    3チャンネルの出力波形オシロスコープ表示を提供します。
    リアルタイム波形更新機能とマルチトレース表示を実装しています。
    """
    
    def __init__(self, device: Device, parent: tk.Widget = None, 
                 window_duration: float = 0.02, sample_rate: int = 44100):
        """WaveformViewerを初期化
        
        Args:
            device: 監視対象のデバイス
            parent: 親ウィジェット（Noneで独立ウィンドウ）
            window_duration: 表示時間窓（秒）
            sample_rate: サンプルレート
        """
        self.device = device
        self.window_duration = window_duration
        self.sample_rate = sample_rate
        
        # バッファサイズを計算
        max_samples = int(sample_rate * window_duration * 2)  # 余裕を持たせる
        self.waveform_buffer = WaveformBuffer(max_samples, channels=3)
        
        # 表示設定
        self.channel_colors = ['red', 'green', 'blue']
        self.channel_names = ['Channel A', 'Channel B', 'Channel C']
        self.channel_enabled = [True, True, True]
        
        # 更新制御
        self._update_thread = None
        self._stop_update = threading.Event()
        self._update_interval = 0.02  # 50Hz更新
        self._is_running = False
        
        # UI作成
        if parent is None:
            self.root = tk.Tk()
            self.root.title("AY-3-8910 Waveform Viewer")
            self.root.geometry("800x600")
            self.parent = self.root
        else:
            self.root = None
            self.parent = parent
        
        self._create_widgets()
        self._setup_plot()
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        # メインフレーム
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 制御パネル
        control_frame = ttk.LabelFrame(main_frame, text="Waveform Control", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # チャンネル表示制御
        channel_frame = ttk.Frame(control_frame)
        channel_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(channel_frame, text="Channels:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.channel_vars = []
        for i in range(3):
            var = tk.BooleanVar(value=True)
            self.channel_vars.append(var)
            
            cb = ttk.Checkbutton(channel_frame, text=self.channel_names[i], 
                               variable=var, command=self._on_channel_toggle)
            cb.pack(side=tk.LEFT, padx=5)
        
        # 制御ボタン
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X)
        
        self.start_button = ttk.Button(button_frame, text="Start", command=self.start)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Clear", command=self.clear).pack(side=tk.LEFT, padx=5)
        
        # 時間窓設定
        time_frame = ttk.Frame(button_frame)
        time_frame.pack(side=tk.RIGHT)
        
        ttk.Label(time_frame, text="Time Window (ms):").pack(side=tk.LEFT, padx=(10, 5))
        
        self.time_var = tk.DoubleVar(value=self.window_duration * 1000)
        time_spinbox = ttk.Spinbox(time_frame, from_=10, to=1000, increment=10,
                                  textvariable=self.time_var, width=8,
                                  command=self._on_time_window_change)
        time_spinbox.pack(side=tk.LEFT)
        
        # プロットフレーム
        plot_frame = ttk.LabelFrame(main_frame, text="Waveform Display", padding=5)
        plot_frame.pack(fill=tk.BOTH, expand=True)
        
        # Matplotlibフィギュア
        self.figure = Figure(figsize=(10, 6), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # ステータス表示
        self.status_label = ttk.Label(main_frame, text="Ready")
        self.status_label.pack(pady=5)
    
    def _setup_plot(self):
        """プロットを設定"""
        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Amplitude')
        self.ax.set_title('AY-3-8910 Waveform')
        self.ax.grid(True, alpha=0.3)
        
        # 各チャンネルのライン
        self.lines = []
        for i in range(3):
            line, = self.ax.plot([], [], color=self.channel_colors[i], 
                               label=self.channel_names[i], linewidth=1.5)
            self.lines.append(line)
        
        self.ax.legend()
        self.ax.set_ylim(-1.1, 1.1)
        
        # 初期表示
        self.figure.tight_layout()
        self.canvas.draw()
    
    def _on_channel_toggle(self):
        """チャンネル表示切り替え"""
        for i, var in enumerate(self.channel_vars):
            self.channel_enabled[i] = var.get()
            self.lines[i].set_visible(self.channel_enabled[i])
        
        self.canvas.draw()
    
    def _on_time_window_change(self):
        """時間窓変更"""
        try:
            new_duration = self.time_var.get() / 1000.0  # ms to s
            if 0.001 <= new_duration <= 1.0:
                self.window_duration = new_duration
                
                # バッファサイズを再計算
                max_samples = int(self.sample_rate * self.window_duration * 2)
                self.waveform_buffer = WaveformBuffer(max_samples, channels=3)
                
        except Exception as e:
            print(f"Time window change error: {e}")
    
    def start(self):
        """波形表示を開始"""
        if not self._is_running:
            self._is_running = True
            self._stop_update.clear()
            
            # 更新スレッドを開始
            self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
            self._update_thread.start()
            
            self.start_button.config(state='disabled')
            self.stop_button.config(state='normal')
            self._update_status("Running")
    
    def stop(self):
        """波形表示を停止"""
        if self._is_running:
            self._is_running = False
            self._stop_update.set()
            
            if self._update_thread and self._update_thread.is_alive():
                self._update_thread.join(timeout=1.0)
            
            self.start_button.config(state='normal')
            self.stop_button.config(state='disabled')
            self._update_status("Stopped")
    
    def clear(self):
        """波形データをクリア"""
        self.waveform_buffer.clear()
        self._clear_plot()
        self._update_status("Cleared")
    
    def _clear_plot(self):
        """プロットをクリア"""
        for line in self.lines:
            line.set_data([], [])
        self.canvas.draw()
    
    def _update_loop(self):
        """更新ループ"""
        while not self._stop_update.is_set() and self._is_running:
            try:
                # デバイスから各チャンネルの出力を取得
                channel_outputs = self.device.get_channel_outputs()
                
                # サンプルをバッファに追加
                self.waveform_buffer.add_samples(channel_outputs)
                
                # プロット更新（メインスレッドで実行）
                if self.parent:
                    self.parent.after_idle(self._update_plot)
                
            except Exception as e:
                print(f"Waveform update error: {e}")
            
            time.sleep(self._update_interval)
    
    def _update_plot(self):
        """プロットを更新"""
        try:
            data = self.waveform_buffer.get_all_data()
            
            if len(data['time']) == 0:
                return
            
            # 時間軸を相対時間に変換
            current_time = data['time'][-1]
            relative_time = data['time'] - current_time
            
            # 表示範囲をフィルタ
            mask = relative_time >= -self.window_duration
            if not np.any(mask):
                return
            
            filtered_time = relative_time[mask]
            
            # 各チャンネルのデータを更新
            for i in range(3):
                if self.channel_enabled[i] and len(data['channels'][i]) > 0:
                    filtered_amplitude = data['channels'][i][mask]
                    self.lines[i].set_data(filtered_time, filtered_amplitude)
            
            # 軸範囲を更新
            self.ax.set_xlim(-self.window_duration, 0)
            
            # 描画
            self.canvas.draw_idle()
            
        except Exception as e:
            print(f"Plot update error: {e}")
    
    def _update_status(self, message: str):
        """ステータス更新"""
        stats = self.waveform_buffer.get_statistics()
        status_text = f"{message} | Samples: {stats['current_samples']}/{stats['max_samples']} | " \
                     f"Utilization: {stats['buffer_utilization']:.1%}"
        self.status_label.config(text=status_text)
    
    def add_sample(self, channel_outputs: List[float]) -> None:
        """外部からサンプルを追加
        
        Args:
            channel_outputs: チャンネル出力のリスト
        """
        self.waveform_buffer.add_samples(channel_outputs)
    
    def plot_waveform(self, time_data: np.ndarray, amplitude_data: List[np.ndarray]) -> None:
        """波形をプロット（外部データ用）
        
        Args:
            time_data: 時間データ
            amplitude_data: 各チャンネルの振幅データ
        """
        try:
            for i, amplitude in enumerate(amplitude_data):
                if i < len(self.lines) and self.channel_enabled[i]:
                    self.lines[i].set_data(time_data, amplitude)
            
            if len(time_data) > 0:
                self.ax.set_xlim(time_data[0], time_data[-1])
            
            self.canvas.draw()
            
        except Exception as e:
            raise WaveformViewerError(f"Failed to plot waveform: {e}")
    
    def update_display(self) -> None:
        """表示を更新"""
        self._update_plot()
    
    def run(self):
        """ビューアを実行（独立ウィンドウの場合）"""
        if self.root:
            try:
                self.root.mainloop()
            finally:
                self.stop()
    
    def close(self):
        """ビューアを閉じる"""
        self.stop()
        if self.root:
            self.root.quit()
            self.root.destroy()


# =============================================================================
# ファクトリ関数
# =============================================================================

def create_waveform_viewer(device: Device, parent: tk.Widget = None,
                          window_duration: float = 0.02, sample_rate: int = 44100) -> WaveformViewer:
    """WaveformViewerを作成
    
    Args:
        device: 監視対象のデバイス
        parent: 親ウィジェット（Noneで独立ウィンドウ）
        window_duration: 表示時間窓（秒）
        sample_rate: サンプルレート
        
    Returns:
        WaveformViewerインスタンス
    """
    return WaveformViewer(device, parent, window_duration, sample_rate)


def launch_waveform_viewer(device: Device, window_duration: float = 0.02, 
                          sample_rate: int = 44100) -> None:
    """波形ビューアを起動
    
    Args:
        device: 監視対象のデバイス
        window_duration: 表示時間窓（秒）
        sample_rate: サンプルレート
    """
    viewer = create_waveform_viewer(device, None, window_duration, sample_rate)
    viewer.run()
