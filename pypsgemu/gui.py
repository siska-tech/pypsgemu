"""
AY-3-8910 PSG Emulator - GUI Entry Point

GUIアプリケーションのメインエントリーポイントを提供します。
"""

import sys
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional


class PyPSGEmuGUI:
    """PyPSGEmu GUI メインアプリケーション"""
    
    def __init__(self):
        """GUIを初期化"""
        self.root = tk.Tk()
        self.root.title("AY-3-8910 PSG Emulator")
        self.root.geometry("600x400")
        
        # デバイス
        self.device = None
        self.driver = None
        
        self._create_widgets()
        self._setup_device()
    
    def _create_widgets(self):
        """ウィジェットを作成"""
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # タイトル
        title_label = ttk.Label(
            main_frame, 
            text="AY-3-8910 PSG Emulator",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # 説明
        desc_text = """
AY-3-8910 PSGチップの完全なソフトウェアエミュレータです。
以下の機能を利用できます：
        """.strip()
        
        desc_label = ttk.Label(main_frame, text=desc_text, justify=tk.CENTER)
        desc_label.pack(pady=(0, 20))
        
        # ボタンフレーム
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # デバッグツールボタン
        debug_frame = ttk.LabelFrame(button_frame, text="デバッグツール", padding=10)
        debug_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(
            debug_frame, 
            text="デバッグUI", 
            command=self._launch_debug_ui,
            width=20
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            debug_frame, 
            text="波形ビューア", 
            command=self._launch_waveform_viewer,
            width=20
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            debug_frame, 
            text="エンベロープビューア", 
            command=self._launch_envelope_viewer,
            width=20
        ).pack(side=tk.LEFT, padx=5)
        
        # サンプルボタン
        sample_frame = ttk.LabelFrame(button_frame, text="サンプル実行", padding=10)
        sample_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(
            sample_frame, 
            text="基本使用例", 
            command=self._run_basic_example,
            width=20
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            sample_frame, 
            text="音声出力例", 
            command=self._run_audio_example,
            width=20
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            sample_frame, 
            text="レジスタ制御例", 
            command=self._run_register_example,
            width=20
        ).pack(side=tk.LEFT, padx=5)
        
        # 情報表示
        info_frame = ttk.LabelFrame(button_frame, text="システム情報", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.info_text = tk.Text(info_frame, height=8, width=70)
        scrollbar = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=self.info_text.yview)
        self.info_text.configure(yscrollcommand=scrollbar.set)
        
        self.info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 終了ボタン
        ttk.Button(
            main_frame, 
            text="終了", 
            command=self._quit,
            width=20
        ).pack(pady=20)
        
        # 初期情報表示
        self._update_info()
    
    def _setup_device(self):
        """デバイスをセットアップ"""
        try:
            from pypsgemu.core.ay38910 import create_ay38910_core
            from pypsgemu.core.device_config import create_default_config
            
            config = create_default_config()
            self.device = create_ay38910_core(config)
            
            self._log("デバイスが正常に初期化されました")
            
        except Exception as e:
            self._log(f"デバイス初期化エラー: {e}")
            messagebox.showerror("エラー", f"デバイスの初期化に失敗しました:\n{e}")
    
    def _launch_debug_ui(self):
        """デバッグUIを起動"""
        try:
            if self.device is None:
                messagebox.showerror("エラー", "デバイスが初期化されていません")
                return
            
            from pypsgemu.debug.ui import create_debug_ui
            
            debug_ui = create_debug_ui(self.device, "AY-3-8910 Debug UI")
            
            # 新しいスレッドでUIを実行
            import threading
            thread = threading.Thread(target=debug_ui.run, daemon=True)
            thread.start()
            
            self._log("デバッグUIを起動しました")
            
        except Exception as e:
            self._log(f"デバッグUI起動エラー: {e}")
            messagebox.showerror("エラー", f"デバッグUIの起動に失敗しました:\n{e}")
    
    def _launch_waveform_viewer(self):
        """波形ビューアを起動"""
        try:
            if self.device is None:
                messagebox.showerror("エラー", "デバイスが初期化されていません")
                return
            
            from pypsgemu.debug.waveform_viewer import create_waveform_viewer
            
            viewer = create_waveform_viewer(self.device)
            
            # 新しいスレッドでビューアを実行
            import threading
            thread = threading.Thread(target=viewer.run, daemon=True)
            thread.start()
            
            self._log("波形ビューアを起動しました")
            
        except Exception as e:
            self._log(f"波形ビューア起動エラー: {e}")
            messagebox.showerror("エラー", f"波形ビューアの起動に失敗しました:\n{e}")
    
    def _launch_envelope_viewer(self):
        """エンベロープビューアを起動"""
        try:
            if self.device is None:
                messagebox.showerror("エラー", "デバイスが初期化されていません")
                return
            
            from pypsgemu.debug.envelope_viewer import create_envelope_viewer
            
            viewer = create_envelope_viewer(self.device)
            
            # 新しいスレッドでビューアを実行
            import threading
            thread = threading.Thread(target=viewer.run, daemon=True)
            thread.start()
            
            self._log("エンベロープビューアを起動しました")
            
        except Exception as e:
            self._log(f"エンベロープビューア起動エラー: {e}")
            messagebox.showerror("エラー", f"エンベロープビューアの起動に失敗しました:\n{e}")
    
    def _run_basic_example(self):
        """基本使用例を実行"""
        try:
            import threading
            from examples.basic_usage import main
            
            def run_example():
                try:
                    main()
                    self._log("基本使用例が完了しました")
                except Exception as e:
                    self._log(f"基本使用例エラー: {e}")
            
            thread = threading.Thread(target=run_example, daemon=True)
            thread.start()
            
            self._log("基本使用例を開始しました")
            
        except Exception as e:
            self._log(f"基本使用例起動エラー: {e}")
            messagebox.showerror("エラー", f"基本使用例の実行に失敗しました:\n{e}")
    
    def _run_audio_example(self):
        """音声出力例を実行"""
        try:
            import threading
            from examples.audio_output import main
            
            def run_example():
                try:
                    main()
                    self._log("音声出力例が完了しました")
                except Exception as e:
                    self._log(f"音声出力例エラー: {e}")
            
            thread = threading.Thread(target=run_example, daemon=True)
            thread.start()
            
            self._log("音声出力例を開始しました")
            
        except Exception as e:
            self._log(f"音声出力例起動エラー: {e}")
            messagebox.showerror("エラー", f"音声出力例の実行に失敗しました:\n{e}")
    
    def _run_register_example(self):
        """レジスタ制御例を実行"""
        try:
            import threading
            from examples.register_control import main
            
            def run_example():
                try:
                    main()
                    self._log("レジスタ制御例が完了しました")
                except Exception as e:
                    self._log(f"レジスタ制御例エラー: {e}")
            
            thread = threading.Thread(target=run_example, daemon=True)
            thread.start()
            
            self._log("レジスタ制御例を開始しました")
            
        except Exception as e:
            self._log(f"レジスタ制御例起動エラー: {e}")
            messagebox.showerror("エラー", f"レジスタ制御例の実行に失敗しました:\n{e}")
    
    def _update_info(self):
        """システム情報を更新"""
        try:
            import pypsgemu
            import sys
            import platform
            
            info_lines = [
                f"PyPSGEmu Version: {getattr(pypsgemu, '__version__', '1.0.0')}",
                f"Python Version: {sys.version}",
                f"Platform: {platform.platform()}",
                "",
                "利用可能な機能:",
                "- AY-3-8910 完全エミュレーション",
                "- リアルタイム音声出力",
                "- デバッグ・可視化ツール",
                "- 状態管理・スナップショット",
                "- 包括的なテストスイート",
                "",
                "使用方法:",
                "1. 上記のボタンでツールやサンプルを起動",
                "2. デバッグUIでリアルタイム制御",
                "3. 各種ビューアで内部状態を可視化",
            ]
            
            if self.device:
                config = self.device.get_config()
                info_lines.extend([
                    "",
                    "デバイス設定:",
                    f"- クロック周波数: {config.clock_frequency/1000000:.1f} MHz",
                    f"- サンプルレート: {config.sample_rate} Hz",
                    f"- 音量スケール: {config.volume_scale}",
                ])
            
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(1.0, "\n".join(info_lines))
            
        except Exception as e:
            self._log(f"情報更新エラー: {e}")
    
    def _log(self, message: str):
        """ログメッセージを追加"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.info_text.insert(tk.END, log_message)
        self.info_text.see(tk.END)
    
    def _quit(self):
        """アプリケーションを終了"""
        try:
            if self.driver:
                self.driver.stop()
            if self.device:
                self.device.reset()
        except Exception:
            pass  # 終了時のエラーは無視
        
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """GUIを実行"""
        try:
            self.root.protocol("WM_DELETE_WINDOW", self._quit)
            self.root.mainloop()
        except KeyboardInterrupt:
            self._quit()


def main(args: Optional[list] = None) -> int:
    """GUIメインエントリーポイント"""
    try:
        app = PyPSGEmuGUI()
        app.run()
        return 0
    except Exception as e:
        print(f"GUI起動エラー: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
