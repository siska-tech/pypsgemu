"""
LFSR状態ビジュアライザモジュール

AY-3-8910エミュレータの17ビットLFSR状態のリアルタイム表示を提供します。
ノイズアルゴリズム検証機能と2進数表示、ビット変化の可視化を実装しています。
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional, List
import threading
import time
from ..core.types import AY38910Error
from ..api.device import Device


class LFSRVisualizerError(AY38910Error):
    """LFSRビジュアライザ関連のエラー"""
    pass


class LFSRBitDisplay:
    """LFSRビット表示ウィジェット
    
    17ビットLFSRの各ビットを視覚的に表示します。
    ビット変化のアニメーション効果を提供します。
    """
    
    def __init__(self, parent: tk.Widget, bit_count: int = 17):
        """LFSRBitDisplayを初期化
        
        Args:
            parent: 親ウィジェット
            bit_count: ビット数
        """
        self.parent = parent
        self.bit_count = bit_count
        
        # 現在の値と前回の値
        self.current_value = 0x1FFFF  # 初期値は全ビット1
        self.previous_value = 0x1FFFF
        
        # ビット表示用ラベル
        self.bit_labels = []
        self.bit_frames = []
        
        # 色設定
        self.colors = {
            'bit_0': '#FF4444',      # 赤（0）
            'bit_1': '#44FF44',      # 緑（1）
            'bit_changed': '#FFFF44', # 黄（変化）
            'bit_normal': '#FFFFFF'   # 白（通常）
        }
        
        self._create_widgets()
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        # メインフレーム
        main_frame = ttk.LabelFrame(self.parent, text="17-bit LFSR State", padding=10)
        main_frame.pack(fill=tk.X, pady=5)
        
        # ビット表示フレーム
        bit_frame = ttk.Frame(main_frame)
        bit_frame.pack(fill=tk.X)
        
        # 各ビットのラベルを作成（MSBから順に）
        for i in range(self.bit_count):
            bit_index = self.bit_count - 1 - i  # MSBから表示
            
            # ビット番号ラベル
            bit_num_label = ttk.Label(bit_frame, text=f"B{bit_index:02d}", font=("Courier", 8))
            bit_num_label.grid(row=0, column=i, padx=1)
            
            # ビット値表示フレーム
            frame = tk.Frame(bit_frame, width=30, height=30, relief=tk.RAISED, bd=2)
            frame.grid(row=1, column=i, padx=1, pady=2)
            frame.grid_propagate(False)
            
            # ビット値ラベル
            label = tk.Label(frame, text="1", font=("Courier", 12, "bold"),
                           bg=self.colors['bit_1'], fg='black')
            label.pack(expand=True, fill=tk.BOTH)
            
            self.bit_frames.append(frame)
            self.bit_labels.append(label)
        
        # 値表示フレーム
        value_frame = ttk.Frame(main_frame)
        value_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 16進表示
        ttk.Label(value_frame, text="Hex:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.hex_label = ttk.Label(value_frame, text="0x1FFFF", font=("Courier", 12, "bold"))
        self.hex_label.grid(row=0, column=1, sticky="w", padx=(0, 20))
        
        # 10進表示
        ttk.Label(value_frame, text="Dec:").grid(row=0, column=2, sticky="w", padx=(0, 5))
        self.dec_label = ttk.Label(value_frame, text="131071", font=("Courier", 12, "bold"))
        self.dec_label.grid(row=0, column=3, sticky="w", padx=(0, 20))
        
        # 出力ビット表示
        ttk.Label(value_frame, text="Output:").grid(row=1, column=0, sticky="w", padx=(0, 5))
        self.output_label = ttk.Label(value_frame, text="1", font=("Courier", 12, "bold"))
        self.output_label.grid(row=1, column=1, sticky="w")
        
        # 統計情報
        stats_frame = ttk.LabelFrame(main_frame, text="Statistics", padding=5)
        stats_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 変化カウント
        ttk.Label(stats_frame, text="Changes:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.changes_label = ttk.Label(stats_frame, text="0")
        self.changes_label.grid(row=0, column=1, sticky="w", padx=(0, 20))
        
        # 周期カウント
        ttk.Label(stats_frame, text="Period:").grid(row=0, column=2, sticky="w", padx=(0, 5))
        self.period_label = ttk.Label(stats_frame, text="Unknown")
        self.period_label.grid(row=0, column=3, sticky="w")
        
        # 統計変数
        self.change_count = 0
        self.value_history = []
        self.period_detected = None
    
    def update_value(self, new_value: int) -> None:
        """LFSR値を更新
        
        Args:
            new_value: 新しいLFSR値
        """
        if not (0 <= new_value <= 0x1FFFF):
            raise LFSRVisualizerError(f"Invalid LFSR value: {new_value}")
        
        self.previous_value = self.current_value
        self.current_value = new_value
        
        # 変化を検出
        changed_bits = self.previous_value ^ self.current_value
        if changed_bits != 0:
            self.change_count += 1
        
        # 周期検出
        self._detect_period(new_value)
        
        # 表示更新
        self._update_display(changed_bits)
    
    def _update_display(self, changed_bits: int):
        """表示を更新
        
        Args:
            changed_bits: 変化したビットのマスク
        """
        # 各ビットの表示を更新
        for i in range(self.bit_count):
            bit_index = self.bit_count - 1 - i
            bit_value = (self.current_value >> bit_index) & 1
            
            label = self.bit_labels[i]
            frame = self.bit_frames[i]
            
            # ビット値を設定
            label.config(text=str(bit_value))
            
            # 色を設定
            if (changed_bits >> bit_index) & 1:
                # 変化したビット
                bg_color = self.colors['bit_changed']
                # 少し後で通常色に戻す
                self.parent.after(200, lambda l=label, v=bit_value: self._set_normal_color(l, v))
            else:
                # 通常のビット
                bg_color = self.colors['bit_1'] if bit_value else self.colors['bit_0']
            
            label.config(bg=bg_color)
        
        # 値表示を更新
        self.hex_label.config(text=f"0x{self.current_value:05X}")
        self.dec_label.config(text=str(self.current_value))
        
        # 出力ビット（LSB）を更新
        output_bit = self.current_value & 1
        self.output_label.config(text=str(output_bit))
        
        # 統計情報を更新
        self.changes_label.config(text=str(self.change_count))
        
        if self.period_detected:
            self.period_label.config(text=str(self.period_detected))
    
    def _set_normal_color(self, label: tk.Label, bit_value: int):
        """通常色に戻す
        
        Args:
            label: 対象ラベル
            bit_value: ビット値
        """
        bg_color = self.colors['bit_1'] if bit_value else self.colors['bit_0']
        label.config(bg=bg_color)
    
    def _detect_period(self, value: int):
        """周期を検出
        
        Args:
            value: 現在の値
        """
        self.value_history.append(value)
        
        # 履歴が長すぎる場合は古いものを削除
        if len(self.value_history) > 200000:  # 最大周期の約1.5倍
            self.value_history = self.value_history[-100000:]
        
        # 周期検出（簡易版）
        if len(self.value_history) > 1000:  # 十分なデータがある場合
            # 最初の値と同じ値を探す
            first_value = self.value_history[0]
            for i in range(100, len(self.value_history)):
                if self.value_history[i] == first_value:
                    # 周期候補を検証
                    period_candidate = i
                    if self._verify_period(period_candidate):
                        self.period_detected = period_candidate
                        break
    
    def _verify_period(self, period: int) -> bool:
        """周期を検証
        
        Args:
            period: 検証する周期
            
        Returns:
            周期が正しい場合True
        """
        if period <= 0 or period >= len(self.value_history):
            return False
        
        # 最初の数サイクルを比較
        cycles_to_check = min(3, len(self.value_history) // period)
        
        for cycle in range(1, cycles_to_check):
            for i in range(min(period, 100)):  # 最初の100個を比較
                if (cycle * period + i) >= len(self.value_history):
                    break
                
                if self.value_history[i] != self.value_history[cycle * period + i]:
                    return False
        
        return True
    
    def reset_statistics(self):
        """統計情報をリセット"""
        self.change_count = 0
        self.value_history.clear()
        self.period_detected = None
        
        self.changes_label.config(text="0")
        self.period_label.config(text="Unknown")


class LFSRVisualizer:
    """LFSRビジュアライザ
    
    17ビットLFSR状態のリアルタイム表示を提供します。
    ノイズアルゴリズム検証機能と2進数表示、ビット変化の可視化を実装しています。
    """
    
    def __init__(self, device: Device, parent: tk.Widget = None):
        """LFSRVisualizerを初期化
        
        Args:
            device: 監視対象のデバイス
            parent: 親ウィジェット（Noneで独立ウィンドウ）
        """
        self.device = device
        
        # 更新制御
        self._update_thread = None
        self._stop_update = threading.Event()
        self._update_interval = 0.05  # 20Hz更新
        self._is_running = False
        
        # UI作成
        if parent is None:
            self.root = tk.Tk()
            self.root.title("AY-3-8910 LFSR Visualizer")
            self.root.geometry("900x400")
            self.parent = self.root
        else:
            self.root = None
            self.parent = parent
        
        self._create_widgets()
        self._load_current_state()
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        # メインフレーム
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 制御パネル
        control_frame = ttk.LabelFrame(main_frame, text="LFSR Control", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # ノイズ周期設定
        period_frame = ttk.Frame(control_frame)
        period_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(period_frame, text="Noise Period (R6):").pack(side=tk.LEFT, padx=(0, 5))
        
        self.noise_period_var = tk.IntVar(value=0)
        period_spinbox = ttk.Spinbox(period_frame, from_=0, to=31, width=5,
                                    textvariable=self.noise_period_var,
                                    command=self._on_noise_period_change)
        period_spinbox.pack(side=tk.LEFT, padx=(0, 10))
        
        # 制御ボタン
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X)
        
        self.start_button = ttk.Button(button_frame, text="Start Monitoring", command=self.start)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Reset LFSR", command=self._reset_lfsr).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Reset Stats", command=self._reset_statistics).pack(side=tk.LEFT, padx=5)
        
        # LFSR表示
        self.lfsr_display = LFSRBitDisplay(main_frame)
        
        # アルゴリズム情報
        info_frame = ttk.LabelFrame(main_frame, text="LFSR Algorithm Info", padding=10)
        info_frame.pack(fill=tk.X, pady=(10, 0))
        
        info_text = """
AY-3-8910 Noise Generator LFSR:
• 17-bit Linear Feedback Shift Register
• Polynomial: x^17 + x^14 + 1 (taps at bits 17 and 14)
• Maximum period: 131,071 (2^17 - 1)
• Output: LSB (bit 0)
• Clock: Master clock / (16 * (Period + 1))
        """.strip()
        
        info_label = ttk.Label(info_frame, text=info_text, justify=tk.LEFT, font=("Courier", 9))
        info_label.pack(anchor=tk.W)
        
        # ステータス表示
        self.status_label = ttk.Label(main_frame, text="Ready")
        self.status_label.pack(pady=5)
    
    def _on_noise_period_change(self):
        """ノイズ周期変更"""
        try:
            period = self.noise_period_var.get()
            if 0 <= period <= 31:
                # デバイスに書き込み
                self.device.write_register(6, period)  # R6: Noise Period
                
        except Exception as e:
            print(f"Noise period change error: {e}")
    
    def _load_current_state(self):
        """現在の状態を読み込み"""
        try:
            # ノイズ周期を読み込み
            noise_period = self.device.read_register(6) & 0x1F  # R6の下位5ビット
            self.noise_period_var.set(noise_period)
            
            # LFSR値を読み込み
            state = self.device.get_state()
            if 'lfsr_value' in state:
                self.lfsr_display.update_value(state['lfsr_value'])
            
        except Exception as e:
            print(f"Failed to load LFSR state: {e}")
    
    def _reset_lfsr(self):
        """LFSRをリセット"""
        try:
            # デバイスをリセット（LFSRも初期値に戻る）
            self.device.reset()
            
            # 表示を更新
            self.lfsr_display.update_value(0x1FFFF)  # 初期値
            
        except Exception as e:
            print(f"Failed to reset LFSR: {e}")
    
    def _reset_statistics(self):
        """統計情報をリセット"""
        self.lfsr_display.reset_statistics()
    
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
            self._update_status("Monitoring LFSR")
    
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
                # デバイスからLFSR状態を取得
                state = self.device.get_state()
                if 'lfsr_value' in state:
                    lfsr_value = state['lfsr_value']
                    
                    # UI更新（メインスレッドで実行）
                    if self.parent:
                        self.parent.after_idle(lambda v=lfsr_value: self.lfsr_display.update_value(v))
                
            except Exception as e:
                print(f"LFSR update error: {e}")
            
            time.sleep(self._update_interval)
    
    def _update_status(self, message: str):
        """ステータス更新"""
        noise_period = self.noise_period_var.get()
        status_text = f"{message} | Noise Period: {noise_period} | LFSR: 0x{self.lfsr_display.current_value:05X}"
        self.status_label.config(text=status_text)
    
    def run(self):
        """ビジュアライザを実行（独立ウィンドウの場合）"""
        if self.root:
            try:
                self.root.mainloop()
            finally:
                self.stop()
    
    def close(self):
        """ビジュアライザを閉じる"""
        self.stop()
        if self.root:
            self.root.quit()
            self.root.destroy()


# =============================================================================
# ファクトリ関数
# =============================================================================

def create_lfsr_visualizer(device: Device, parent: tk.Widget = None) -> LFSRVisualizer:
    """LFSRVisualizerを作成
    
    Args:
        device: 監視対象のデバイス
        parent: 親ウィジェット（Noneで独立ウィンドウ）
        
    Returns:
        LFSRVisualizerインスタンス
    """
    return LFSRVisualizer(device, parent)


def launch_lfsr_visualizer(device: Device) -> None:
    """LFSRビジュアライザを起動
    
    Args:
        device: 監視対象のデバイス
    """
    visualizer = create_lfsr_visualizer(device, None)
    visualizer.run()
