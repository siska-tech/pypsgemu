"""
エンベロープビューアモジュール

AY-3-8910エミュレータのエンベロープ形状のグラフィカル表示を提供します。
現在レベル表示機能とマーカー、10種類のエンベロープ形状対応を実装しています。
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional, List
import threading
import time
from ..core.types import AY38910Error
from ..api.device import Device


class EnvelopeViewerError(AY38910Error):
    """エンベロープビューア関連のエラー"""
    pass


class EnvelopeShapeGenerator:
    """エンベロープ形状生成器
    
    AY-3-8910の10種類のエンベロープ形状を生成します。
    各形状の特性と動作を正確に模倣しています。
    """
    
    # エンベロープ形状定義
    ENVELOPE_SHAPES = {
        0x00: "\\\\\\\\\\\\\\\\",  # 0000: 減衰のみ
        0x01: "\\\\\\\\\\\\\\\\",  # 0001: 減衰のみ
        0x02: "\\\\\\\\\\\\\\\\",  # 0010: 減衰のみ
        0x03: "\\\\\\\\\\\\\\\\",  # 0011: 減衰のみ
        0x04: "/|/|/|/|/|",      # 0100: 攻撃→減衰の繰り返し
        0x05: "/|/|/|/|/|",      # 0101: 攻撃→減衰の繰り返し
        0x06: "/|/|/|/|/|",      # 0110: 攻撃→減衰の繰り返し
        0x07: "/|/|/|/|/|",      # 0111: 攻撃→減衰の繰り返し
        0x08: "\\\\\\\\\\\\\\\\",  # 1000: 減衰のみ
        0x09: "\\\\\\\\\\\\\\\\",  # 1001: 減衰のみ
        0x0A: "\\/\\/\\/\\/\\",    # 1010: 減衰→攻撃の繰り返し
        0x0B: "\\‾‾‾‾‾‾‾‾",      # 1011: 減衰→ホールド
        0x0C: "/|/|/|/|/|",      # 1100: 攻撃→減衰の繰り返し
        0x0D: "/‾‾‾‾‾‾‾‾",       # 1101: 攻撃→ホールド
        0x0E: "/\\/\\/\\/\\",     # 1110: 攻撃→減衰→攻撃の繰り返し
        0x0F: "/‾‾‾‾‾‾‾‾"        # 1111: 攻撃→ホールド
    }
    
    ENVELOPE_NAMES = {
        0x00: "Decay Only", 0x01: "Decay Only", 0x02: "Decay Only", 0x03: "Decay Only",
        0x04: "Attack-Decay Repeat", 0x05: "Attack-Decay Repeat", 
        0x06: "Attack-Decay Repeat", 0x07: "Attack-Decay Repeat",
        0x08: "Decay Only", 0x09: "Decay Only",
        0x0A: "Decay-Attack Repeat", 0x0B: "Decay-Hold",
        0x0C: "Attack-Decay Repeat", 0x0D: "Attack-Hold",
        0x0E: "Attack-Decay-Attack Repeat", 0x0F: "Attack-Hold"
    }
    
    @staticmethod
    def generate_envelope_shape(shape: int, period: int = 256, cycles: int = 3) -> tuple:
        """エンベロープ形状を生成
        
        Args:
            shape: エンベロープ形状 (0-15)
            period: エンベロープ周期
            cycles: 生成するサイクル数
            
        Returns:
            (time_array, level_array) のタプル
        """
        if not (0 <= shape <= 15):
            raise EnvelopeViewerError(f"Invalid envelope shape: {shape}")
        
        # 基本パラメータ
        total_samples = period * cycles
        time_array = np.linspace(0, cycles, total_samples)
        level_array = np.zeros(total_samples)
        
        # 形状に応じた生成
        continue_bit = (shape >> 3) & 1  # ビット3: Continue
        attack_bit = (shape >> 2) & 1   # ビット2: Attack
        alternate_bit = (shape >> 1) & 1 # ビット1: Alternate
        hold_bit = shape & 1            # ビット0: Hold
        
        for cycle in range(cycles):
            start_idx = cycle * period
            end_idx = (cycle + 1) * period
            cycle_time = np.linspace(0, 1, period)
            
            if cycle == 0:
                # 最初のサイクル
                if attack_bit:
                    # 攻撃（上昇）
                    level_array[start_idx:end_idx] = cycle_time
                else:
                    # 減衰（下降）
                    level_array[start_idx:end_idx] = 1.0 - cycle_time
            else:
                # 継続サイクル
                if not continue_bit:
                    # 継続しない場合は0レベル
                    level_array[start_idx:end_idx] = 0.0
                elif hold_bit:
                    # ホールド
                    if attack_bit:
                        level_array[start_idx:end_idx] = 1.0  # 最大レベルでホールド
                    else:
                        level_array[start_idx:end_idx] = 0.0  # 最小レベルでホールド
                else:
                    # 繰り返し
                    if alternate_bit:
                        # 交互動作
                        if (cycle % 2) == 1:
                            attack_bit = 1 - attack_bit
                    
                    if attack_bit:
                        level_array[start_idx:end_idx] = cycle_time
                    else:
                        level_array[start_idx:end_idx] = 1.0 - cycle_time
        
        # レベルを0-15の範囲にスケール
        level_array = level_array * 15.0
        
        return time_array, level_array


class EnvelopeViewer:
    """エンベロープビューア
    
    エンベロープ形状のグラフィカル表示を提供します。
    現在レベル表示機能とマーカー、10種類のエンベロープ形状対応を実装しています。
    """
    
    def __init__(self, device: Device, parent: tk.Widget = None):
        """EnvelopeViewerを初期化
        
        Args:
            device: 監視対象のデバイス
            parent: 親ウィジェット（Noneで独立ウィンドウ）
        """
        self.device = device
        
        # 現在の状態
        self.current_shape = 0
        self.current_period = 256
        self.current_level = 15
        self.envelope_position = 0.0
        
        # 更新制御
        self._update_thread = None
        self._stop_update = threading.Event()
        self._update_interval = 0.1  # 10Hz更新
        self._is_running = False
        
        # UI作成
        if parent is None:
            self.root = tk.Tk()
            self.root.title("AY-3-8910 Envelope Viewer")
            self.root.geometry("800x600")
            self.parent = self.root
        else:
            self.root = None
            self.parent = parent
        
        self._create_widgets()
        self._setup_plot()
        self._load_current_envelope()
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        # メインフレーム
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 制御パネル
        control_frame = ttk.LabelFrame(main_frame, text="Envelope Control", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # エンベロープ形状選択
        shape_frame = ttk.Frame(control_frame)
        shape_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(shape_frame, text="Shape:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.shape_var = tk.IntVar(value=0)
        shape_spinbox = ttk.Spinbox(shape_frame, from_=0, to=15, width=5,
                                   textvariable=self.shape_var,
                                   command=self._on_shape_change)
        shape_spinbox.pack(side=tk.LEFT, padx=(0, 10))
        
        self.shape_name_label = ttk.Label(shape_frame, text="Decay Only")
        self.shape_name_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # エンベロープ周期設定
        period_frame = ttk.Frame(control_frame)
        period_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(period_frame, text="Period:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.period_var = tk.IntVar(value=256)
        period_spinbox = ttk.Spinbox(period_frame, from_=1, to=65535, width=8,
                                    textvariable=self.period_var,
                                    command=self._on_period_change)
        period_spinbox.pack(side=tk.LEFT, padx=(0, 10))
        
        # 現在レベル表示
        level_frame = ttk.Frame(control_frame)
        level_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(level_frame, text="Current Level:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.level_label = ttk.Label(level_frame, text="15", font=("Arial", 12, "bold"))
        self.level_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # レベルプログレスバー
        self.level_progress = ttk.Progressbar(level_frame, length=200, maximum=15)
        self.level_progress.pack(side=tk.LEFT, padx=(10, 0))
        
        # 制御ボタン
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X)
        
        self.start_button = ttk.Button(button_frame, text="Start Monitoring", command=self.start)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Refresh", command=self._load_current_envelope).pack(side=tk.LEFT, padx=5)
        
        # プロットフレーム
        plot_frame = ttk.LabelFrame(main_frame, text="Envelope Shape", padding=5)
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
        self.ax.set_xlabel('Time (cycles)')
        self.ax.set_ylabel('Envelope Level')
        self.ax.set_title('AY-3-8910 Envelope Shape')
        self.ax.grid(True, alpha=0.3)
        self.ax.set_ylim(-0.5, 15.5)
        
        # エンベロープライン
        self.envelope_line, = self.ax.plot([], [], 'b-', linewidth=2, label='Envelope Shape')
        
        # 現在位置マーカー
        self.position_marker, = self.ax.plot([], [], 'ro', markersize=8, label='Current Position')
        
        # レベルライン
        self.level_line = self.ax.axhline(y=15, color='r', linestyle='--', alpha=0.7, label='Current Level')
        
        self.ax.legend()
        
        # 初期表示
        self.figure.tight_layout()
        self.canvas.draw()
    
    def _on_shape_change(self):
        """エンベロープ形状変更"""
        try:
            shape = self.shape_var.get()
            if 0 <= shape <= 15:
                self.current_shape = shape
                
                # 形状名を更新
                shape_name = EnvelopeShapeGenerator.ENVELOPE_NAMES.get(shape, "Unknown")
                self.shape_name_label.config(text=shape_name)
                
                # デバイスに書き込み
                self.device.write_register(13, shape)  # R13: Envelope Shape
                
                # プロット更新
                self._update_envelope_plot()
                
        except Exception as e:
            print(f"Shape change error: {e}")
    
    def _on_period_change(self):
        """エンベロープ周期変更"""
        try:
            period = self.period_var.get()
            if 1 <= period <= 65535:
                self.current_period = period
                
                # デバイスに書き込み（R11: Fine, R12: Coarse）
                fine = period & 0xFF
                coarse = (period >> 8) & 0xFF
                self.device.write_register(11, fine)
                self.device.write_register(12, coarse)
                
                # プロット更新
                self._update_envelope_plot()
                
        except Exception as e:
            print(f"Period change error: {e}")
    
    def _load_current_envelope(self):
        """現在のエンベロープ設定を読み込み"""
        try:
            # レジスタから読み込み
            shape = self.device.read_register(13) & 0x0F  # R13: Envelope Shape
            fine = self.device.read_register(11)          # R11: Envelope Fine
            coarse = self.device.read_register(12)        # R12: Envelope Coarse
            
            period = (coarse << 8) | fine
            if period == 0:
                period = 1  # 0の場合は1として扱う
            
            # UI更新
            self.shape_var.set(shape)
            self.period_var.set(period)
            
            self.current_shape = shape
            self.current_period = period
            
            # 形状名更新
            shape_name = EnvelopeShapeGenerator.ENVELOPE_NAMES.get(shape, "Unknown")
            self.shape_name_label.config(text=shape_name)
            
            # プロット更新
            self._update_envelope_plot()
            
        except Exception as e:
            print(f"Failed to load envelope settings: {e}")
    
    def _update_envelope_plot(self):
        """エンベローププロットを更新"""
        try:
            # エンベロープ形状を生成
            time_data, level_data = EnvelopeShapeGenerator.generate_envelope_shape(
                self.current_shape, self.current_period, cycles=3
            )
            
            # エンベロープラインを更新
            self.envelope_line.set_data(time_data, level_data)
            
            # 軸範囲を更新
            if len(time_data) > 0:
                self.ax.set_xlim(0, time_data[-1])
            
            self.canvas.draw()
            
        except Exception as e:
            print(f"Plot update error: {e}")
    
    def start(self):
        """監視を開始"""
        if not self._is_running:
            self._is_running = True
            self._stop_update.clear()
            
            # 更新スレッドを開始
            self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
            self._update_thread.start()
            
            self.start_button.config(state='disabled')
            self.stop_button.config(state='normal')
            self._update_status("Monitoring")
    
    def stop(self):
        """監視を停止"""
        if self._is_running:
            self._is_running = False
            self._stop_update.set()
            
            if self._update_thread and self._update_thread.is_alive():
                self._update_thread.join(timeout=1.0)
            
            self.start_button.config(state='normal')
            self.stop_button.config(state='disabled')
            self._update_status("Stopped")
    
    def _update_loop(self):
        """更新ループ"""
        while not self._stop_update.is_set() and self._is_running:
            try:
                # デバイスから現在のエンベロープレベルを取得
                state = self.device.get_state()
                if 'envelope_level' in state:
                    self.current_level = state['envelope_level']
                    
                    # UI更新（メインスレッドで実行）
                    if self.parent:
                        self.parent.after_idle(self._update_level_display)
                
            except Exception as e:
                print(f"Envelope update error: {e}")
            
            time.sleep(self._update_interval)
    
    def _update_level_display(self):
        """レベル表示を更新"""
        try:
            # レベルラベル更新
            self.level_label.config(text=str(self.current_level))
            
            # プログレスバー更新
            self.level_progress['value'] = self.current_level
            
            # レベルライン更新
            self.level_line.set_ydata([self.current_level, self.current_level])
            
            self.canvas.draw_idle()
            
        except Exception as e:
            print(f"Level display update error: {e}")
    
    def _update_status(self, message: str):
        """ステータス更新"""
        status_text = f"{message} | Shape: {self.current_shape} | Period: {self.current_period} | Level: {self.current_level}"
        self.status_label.config(text=status_text)
    
    def plot_envelope(self, shape: int, period: int = 256) -> None:
        """エンベロープをプロット（外部用）
        
        Args:
            shape: エンベロープ形状
            period: エンベロープ周期
        """
        try:
            self.current_shape = shape
            self.current_period = period
            
            self.shape_var.set(shape)
            self.period_var.set(period)
            
            # 形状名更新
            shape_name = EnvelopeShapeGenerator.ENVELOPE_NAMES.get(shape, "Unknown")
            self.shape_name_label.config(text=shape_name)
            
            # プロット更新
            self._update_envelope_plot()
            
        except Exception as e:
            raise EnvelopeViewerError(f"Failed to plot envelope: {e}")
    
    def show_shape(self, shape: int) -> None:
        """エンベロープ形状を表示
        
        Args:
            shape: エンベロープ形状
        """
        self.plot_envelope(shape, self.current_period)
    
    def update_display(self) -> None:
        """表示を更新"""
        self._update_envelope_plot()
        self._update_level_display()
    
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

def create_envelope_viewer(device: Device, parent: tk.Widget = None) -> EnvelopeViewer:
    """EnvelopeViewerを作成
    
    Args:
        device: 監視対象のデバイス
        parent: 親ウィジェット（Noneで独立ウィンドウ）
        
    Returns:
        EnvelopeViewerインスタンス
    """
    return EnvelopeViewer(device, parent)


def launch_envelope_viewer(device: Device) -> None:
    """エンベロープビューアを起動
    
    Args:
        device: 監視対象のデバイス
    """
    viewer = create_envelope_viewer(device, None)
    viewer.run()
