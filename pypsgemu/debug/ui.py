"""
対話型デバッグUIモジュール

AY-3-8910エミュレータの対話型デバッグインターフェースを提供します。
ミキサーパネル、ライブレジスタ編集、リアルタイム制御機能を実装しています。
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from typing import Dict, Any, Optional, Callable, List
import threading
import time
from ..core.types import AY38910Error
from ..api.device import Device
from ..utils.state_manager import StateManager, create_state_manager


class DebugUIError(AY38910Error):
    """デバッグUI関連のエラー"""
    pass


class MixerPanel:
    """ミキサーパネル
    
    R7レジスタの6つのイネーブルビット制御UIを提供します。
    チェックボックスによるミュート/ソロ機能を実装しています。
    """
    
    def __init__(self, parent: tk.Widget, device: Device, update_callback: Callable = None):
        """MixerPanelを初期化
        
        Args:
            parent: 親ウィジェット
            device: 制御対象のデバイス
            update_callback: 更新時のコールバック関数
        """
        self.device = device
        self.update_callback = update_callback
        
        # フレーム作成
        self.frame = ttk.LabelFrame(parent, text="Mixer Control (R7)", padding=10)
        
        # チェックボックス変数
        self.tone_a_enable = tk.BooleanVar(value=True)
        self.tone_b_enable = tk.BooleanVar(value=True)
        self.tone_c_enable = tk.BooleanVar(value=True)
        self.noise_a_enable = tk.BooleanVar(value=True)
        self.noise_b_enable = tk.BooleanVar(value=True)
        self.noise_c_enable = tk.BooleanVar(value=True)
        
        # UI要素を作成
        self._create_widgets()
        
        # 初期状態を読み込み
        self._load_current_state()
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        # トーンイネーブル
        tone_frame = ttk.LabelFrame(self.frame, text="Tone Enable", padding=5)
        tone_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        ttk.Checkbutton(tone_frame, text="Channel A", variable=self.tone_a_enable,
                       command=self._on_mixer_change).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(tone_frame, text="Channel B", variable=self.tone_b_enable,
                       command=self._on_mixer_change).grid(row=1, column=0, sticky="w")
        ttk.Checkbutton(tone_frame, text="Channel C", variable=self.tone_c_enable,
                       command=self._on_mixer_change).grid(row=2, column=0, sticky="w")
        
        # ノイズイネーブル
        noise_frame = ttk.LabelFrame(self.frame, text="Noise Enable", padding=5)
        noise_frame.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Checkbutton(noise_frame, text="Channel A", variable=self.noise_a_enable,
                       command=self._on_mixer_change).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(noise_frame, text="Channel B", variable=self.noise_b_enable,
                       command=self._on_mixer_change).grid(row=1, column=0, sticky="w")
        ttk.Checkbutton(noise_frame, text="Channel C", variable=self.noise_c_enable,
                       command=self._on_mixer_change).grid(row=2, column=0, sticky="w")
        
        # 制御ボタン
        button_frame = ttk.Frame(self.frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="All On", command=self._all_on).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="All Off", command=self._all_off).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Solo A", command=self._solo_a).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Solo B", command=self._solo_b).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Solo C", command=self._solo_c).pack(side=tk.LEFT, padx=5)
        
        # 現在値表示
        self.current_value_label = ttk.Label(self.frame, text="Current R7: 0x00")
        self.current_value_label.grid(row=2, column=0, columnspan=2, pady=5)
    
    def _load_current_state(self):
        """現在の状態を読み込み"""
        try:
            mixer_value = self.device.read_register(7)  # R7
            
            # ビットを解析してチェックボックスに反映
            # R7のビット配置: [7:6]=未使用, [5]=NoiseC, [4]=NoiseB, [3]=NoiseA, [2]=ToneC, [1]=ToneB, [0]=ToneA
            # 0=Enable, 1=Disable なので反転
            self.tone_a_enable.set(not bool(mixer_value & 0x01))
            self.tone_b_enable.set(not bool(mixer_value & 0x02))
            self.tone_c_enable.set(not bool(mixer_value & 0x04))
            self.noise_a_enable.set(not bool(mixer_value & 0x08))
            self.noise_b_enable.set(not bool(mixer_value & 0x10))
            self.noise_c_enable.set(not bool(mixer_value & 0x20))
            
            self._update_current_value_display()
            
        except Exception as e:
            print(f"Failed to load mixer state: {e}")
    
    def _on_mixer_change(self):
        """ミキサー設定変更時の処理"""
        try:
            # チェックボックスの状態からR7値を計算
            mixer_value = 0
            
            # 0=Enable, 1=Disable なので反転
            if not self.tone_a_enable.get():
                mixer_value |= 0x01
            if not self.tone_b_enable.get():
                mixer_value |= 0x02
            if not self.tone_c_enable.get():
                mixer_value |= 0x04
            if not self.noise_a_enable.get():
                mixer_value |= 0x08
            if not self.noise_b_enable.get():
                mixer_value |= 0x10
            if not self.noise_c_enable.get():
                mixer_value |= 0x20
            
            # デバイスに書き込み
            self.device.write_register(7, mixer_value)
            
            # 表示更新
            self._update_current_value_display()
            
            # コールバック呼び出し
            if self.update_callback:
                self.update_callback()
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update mixer: {e}")
    
    def _update_current_value_display(self):
        """現在値表示を更新"""
        try:
            current_value = self.device.read_register(7)
            self.current_value_label.config(text=f"Current R7: 0x{current_value:02X} ({current_value:08b})")
        except Exception:
            self.current_value_label.config(text="Current R7: Error")
    
    def _all_on(self):
        """すべてのチャンネルを有効化"""
        self.tone_a_enable.set(True)
        self.tone_b_enable.set(True)
        self.tone_c_enable.set(True)
        self.noise_a_enable.set(True)
        self.noise_b_enable.set(True)
        self.noise_c_enable.set(True)
        self._on_mixer_change()
    
    def _all_off(self):
        """すべてのチャンネルを無効化"""
        self.tone_a_enable.set(False)
        self.tone_b_enable.set(False)
        self.tone_c_enable.set(False)
        self.noise_a_enable.set(False)
        self.noise_b_enable.set(False)
        self.noise_c_enable.set(False)
        self._on_mixer_change()
    
    def _solo_a(self):
        """チャンネルAのみ有効化"""
        self.tone_a_enable.set(True)
        self.tone_b_enable.set(False)
        self.tone_c_enable.set(False)
        self.noise_a_enable.set(True)
        self.noise_b_enable.set(False)
        self.noise_c_enable.set(False)
        self._on_mixer_change()
    
    def _solo_b(self):
        """チャンネルBのみ有効化"""
        self.tone_a_enable.set(False)
        self.tone_b_enable.set(True)
        self.tone_c_enable.set(False)
        self.noise_a_enable.set(False)
        self.noise_b_enable.set(True)
        self.noise_c_enable.set(False)
        self._on_mixer_change()
    
    def _solo_c(self):
        """チャンネルCのみ有効化"""
        self.tone_a_enable.set(False)
        self.tone_b_enable.set(False)
        self.tone_c_enable.set(True)
        self.noise_a_enable.set(False)
        self.noise_b_enable.set(False)
        self.noise_c_enable.set(True)
        self._on_mixer_change()


class LiveRegisterEditor:
    """ライブレジスタエディタ
    
    レジスタ値のリアルタイム編集インターフェースを提供します。
    スライダーとスピンボックスによる直感的な操作を実装しています。
    """
    
    def __init__(self, parent: tk.Widget, device: Device, update_callback: Callable = None):
        """LiveRegisterEditorを初期化
        
        Args:
            parent: 親ウィジェット
            device: 制御対象のデバイス
            update_callback: 更新時のコールバック関数
        """
        self.device = device
        self.update_callback = update_callback
        
        # フレーム作成
        self.frame = ttk.LabelFrame(parent, text="Live Register Editor", padding=10)
        
        # レジスタ変数
        self.register_vars = [tk.IntVar() for _ in range(16)]
        
        # UI要素を作成
        self._create_widgets()
        
        # 初期状態を読み込み
        self._load_current_registers()
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        # スクロール可能なフレーム
        canvas = tk.Canvas(self.frame, height=400)
        scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # レジスタ名
        register_names = [
            "R0: Tone A Fine", "R1: Tone A Coarse",
            "R2: Tone B Fine", "R3: Tone B Coarse",
            "R4: Tone C Fine", "R5: Tone C Coarse",
            "R6: Noise Period", "R7: Mixer Control",
            "R8: Volume A", "R9: Volume B", "R10: Volume C",
            "R11: Envelope Fine", "R12: Envelope Coarse", "R13: Envelope Shape",
            "R14: I/O Port A", "R15: I/O Port B"
        ]
        
        # 各レジスタのUI作成
        for i in range(16):
            reg_frame = ttk.Frame(scrollable_frame)
            reg_frame.grid(row=i, column=0, sticky="ew", padx=5, pady=2)
            scrollable_frame.columnconfigure(0, weight=1)
            
            # レジスタ名ラベル
            ttk.Label(reg_frame, text=register_names[i], width=20).grid(row=0, column=0, sticky="w")
            
            # スライダー
            scale = ttk.Scale(reg_frame, from_=0, to=255, orient=tk.HORIZONTAL,
                            variable=self.register_vars[i],
                            command=lambda val, reg=i: self._on_register_change(reg, val))
            scale.grid(row=0, column=1, sticky="ew", padx=5)
            reg_frame.columnconfigure(1, weight=1)
            
            # スピンボックス
            spinbox = ttk.Spinbox(reg_frame, from_=0, to=255, width=5,
                                textvariable=self.register_vars[i],
                                command=lambda reg=i: self._on_register_change_spinbox(reg))
            spinbox.grid(row=0, column=2, padx=5)
            
            # 16進表示
            hex_label = ttk.Label(reg_frame, text="0x00", width=5)
            hex_label.grid(row=0, column=3, padx=5)
            setattr(self, f"hex_label_{i}", hex_label)
        
        # スクロールバーとキャンバスを配置
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)
        
        # 制御ボタン
        button_frame = ttk.Frame(self.frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Reset All", command=self._reset_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Load Current", command=self._load_current_registers).pack(side=tk.LEFT, padx=5)
    
    def _load_current_registers(self):
        """現在のレジスタ値を読み込み"""
        try:
            for i in range(16):
                value = self.device.read_register(i)
                self.register_vars[i].set(value)
                self._update_hex_display(i, value)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load registers: {e}")
    
    def _on_register_change(self, register: int, value: str):
        """レジスタ変更時の処理（スライダー）"""
        try:
            int_value = int(float(value))
            self._write_register(register, int_value)
        except Exception as e:
            print(f"Register change error: {e}")
    
    def _on_register_change_spinbox(self, register: int):
        """レジスタ変更時の処理（スピンボックス）"""
        try:
            value = self.register_vars[register].get()
            self._write_register(register, value)
        except Exception as e:
            print(f"Register change error: {e}")
    
    def _write_register(self, register: int, value: int):
        """レジスタに値を書き込み"""
        try:
            # 値の範囲チェック
            value = max(0, min(255, value))
            
            # デバイスに書き込み
            self.device.write_register(register, value)
            
            # 16進表示更新
            self._update_hex_display(register, value)
            
            # コールバック呼び出し
            if self.update_callback:
                self.update_callback()
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to write register R{register}: {e}")
    
    def _update_hex_display(self, register: int, value: int):
        """16進表示を更新"""
        hex_label = getattr(self, f"hex_label_{register}")
        hex_label.config(text=f"0x{value:02X}")
    
    def _reset_all(self):
        """すべてのレジスタをリセット"""
        try:
            for i in range(16):
                self.device.write_register(i, 0)
                self.register_vars[i].set(0)
                self._update_hex_display(i, 0)
            
            if self.update_callback:
                self.update_callback()
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reset registers: {e}")


class DebugUI:
    """対話型デバッグUI
    
    AY-3-8910エミュレータの包括的なデバッグインターフェースを提供します。
    ミキサーパネル、レジスタエディタ、状態管理機能を統合しています。
    """
    
    def __init__(self, device: Device, title: str = "AY-3-8910 Debug UI"):
        """DebugUIを初期化
        
        Args:
            device: 制御対象のデバイス
            title: ウィンドウタイトル
        """
        self.device = device
        self.state_manager = create_state_manager()
        
        # メインウィンドウ作成
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry("800x600")
        
        # 更新スレッド制御
        self._update_thread = None
        self._stop_update = threading.Event()
        self._auto_update = tk.BooleanVar(value=False)
        
        # UI要素を作成
        self._create_widgets()
        
        # 自動更新開始
        self._start_auto_update()
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        # メインフレーム
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 上部フレーム（ミキサーパネル）
        self.mixer_panel = MixerPanel(main_frame, self.device, self._on_update)
        self.mixer_panel.frame.pack(fill=tk.X, pady=(0, 10))
        
        # 中央フレーム（レジスタエディタ）
        self.register_editor = LiveRegisterEditor(main_frame, self.device, self._on_update)
        self.register_editor.frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 下部フレーム（制御パネル）
        control_frame = ttk.LabelFrame(main_frame, text="Control Panel", padding=10)
        control_frame.pack(fill=tk.X)
        
        # 状態管理ボタン
        state_frame = ttk.Frame(control_frame)
        state_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(state_frame, text="Save State", command=self._save_state).pack(side=tk.LEFT, padx=5)
        ttk.Button(state_frame, text="Load State", command=self._load_state).pack(side=tk.LEFT, padx=5)
        ttk.Button(state_frame, text="Reset Device", command=self._reset_device).pack(side=tk.LEFT, padx=5)
        
        # 自動更新制御
        update_frame = ttk.Frame(control_frame)
        update_frame.pack(fill=tk.X)
        
        ttk.Checkbutton(update_frame, text="Auto Update", variable=self._auto_update).pack(side=tk.LEFT, padx=5)
        ttk.Button(update_frame, text="Manual Update", command=self._manual_update).pack(side=tk.LEFT, padx=5)
        
        # ステータス表示
        self.status_label = ttk.Label(control_frame, text="Ready")
        self.status_label.pack(pady=5)
    
    def _on_update(self):
        """更新時のコールバック"""
        self._update_status("Updated")
    
    def _update_status(self, message: str):
        """ステータス表示を更新"""
        self.status_label.config(text=f"Status: {message}")
    
    def _save_state(self):
        """状態を保存"""
        try:
            # 保存名を入力
            name = simpledialog.askstring("Save State", "Enter state name:")
            if not name:
                return
            
            # スナップショットを作成
            snapshot = self.state_manager.create_snapshot(self.device, name, "Manual save from Debug UI")
            
            # ファイルに保存
            filepath = self.state_manager.save_snapshot_to_file(name)
            
            self._update_status(f"State saved: {filepath}")
            messagebox.showinfo("Success", f"State saved as '{name}'")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save state: {e}")
    
    def _load_state(self):
        """状態を読み込み"""
        try:
            # ファイル選択
            filepath = filedialog.askopenfilename(
                title="Load State",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            if not filepath:
                return
            
            # スナップショットを読み込み
            snapshot_name = self.state_manager.load_snapshot_from_file(filepath)
            
            # デバイスに復元
            self.state_manager.restore_snapshot(self.device, snapshot_name)
            
            # UI更新
            self._manual_update()
            
            self._update_status(f"State loaded: {snapshot_name}")
            messagebox.showinfo("Success", f"State '{snapshot_name}' loaded")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load state: {e}")
    
    def _reset_device(self):
        """デバイスをリセット"""
        try:
            if messagebox.askyesno("Confirm", "Reset device to initial state?"):
                self.device.reset()
                self._manual_update()
                self._update_status("Device reset")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reset device: {e}")
    
    def _manual_update(self):
        """手動更新"""
        try:
            self.mixer_panel._load_current_state()
            self.register_editor._load_current_registers()
            self._update_status("Manual update completed")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update: {e}")
    
    def _start_auto_update(self):
        """自動更新を開始"""
        if self._update_thread is None or not self._update_thread.is_alive():
            self._stop_update.clear()
            self._update_thread = threading.Thread(target=self._auto_update_loop, daemon=True)
            self._update_thread.start()
    
    def _auto_update_loop(self):
        """自動更新ループ"""
        while not self._stop_update.is_set():
            if self._auto_update.get():
                try:
                    # UIの更新はメインスレッドで実行
                    self.root.after_idle(self._manual_update)
                except Exception:
                    pass  # エラーは無視
            
            time.sleep(0.5)  # 0.5秒間隔で更新
    
    def run(self):
        """UIを実行"""
        try:
            self.root.mainloop()
        finally:
            self._stop_update.set()
            if self._update_thread and self._update_thread.is_alive():
                self._update_thread.join(timeout=1.0)
    
    def close(self):
        """UIを閉じる"""
        self._stop_update.set()
        self.root.quit()
        self.root.destroy()


# =============================================================================
# ファクトリ関数
# =============================================================================

def create_debug_ui(device: Device, title: str = "AY-3-8910 Debug UI") -> DebugUI:
    """DebugUIを作成
    
    Args:
        device: 制御対象のデバイス
        title: ウィンドウタイトル
        
    Returns:
        DebugUIインスタンス
    """
    return DebugUI(device, title)


def launch_debug_ui(device: Device, title: str = "AY-3-8910 Debug UI") -> None:
    """デバッグUIを起動
    
    Args:
        device: 制御対象のデバイス
        title: ウィンドウタイトル
    """
    ui = create_debug_ui(device, title)
    ui.run()
