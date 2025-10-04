"""
AY-3-8910 PSG Emulator - Command Line Interface

コマンドライン用のエントリーポイントを提供します。
"""

import sys
import argparse
from typing import List, Optional


def demo_main(args: Optional[List[str]] = None) -> int:
    """デモプログラムのメインエントリーポイント"""
    parser = argparse.ArgumentParser(
        description='AY-3-8910 PSG Emulator Demo',
        prog='pypsgemu-demo'
    )
    parser.add_argument(
        '--example', 
        choices=['basic', 'debug', 'audio', 'register'],
        default='basic',
        help='実行するサンプル (default: basic)'
    )
    parser.add_argument(
        '--duration',
        type=float,
        default=None,
        help='実行時間（秒）'
    )
    parser.add_argument(
        '--volume',
        type=float,
        default=0.5,
        help='音量スケール (0.0-1.0, default: 0.5)'
    )
    
    parsed_args = parser.parse_args(args)
    
    try:
        if parsed_args.example == 'basic':
            from examples.basic_usage import main
            print("基本使用例を実行中...")
            main()
        elif parsed_args.example == 'debug':
            from examples.debug_demo import main
            print("デバッグ機能デモを実行中...")
            main()
        elif parsed_args.example == 'audio':
            from examples.audio_output import main
            print("音声出力例を実行中...")
            main()
        elif parsed_args.example == 'register':
            from examples.register_control import main
            print("レジスタ制御例を実行中...")
            main()
        
        return 0
        
    except KeyboardInterrupt:
        print("\n中断されました")
        return 1
    except Exception as e:
        print(f"エラー: {e}")
        return 1


def debug_main(args: Optional[List[str]] = None) -> int:
    """デバッグUIのメインエントリーポイント"""
    parser = argparse.ArgumentParser(
        description='AY-3-8910 PSG Emulator Debug UI',
        prog='pypsgemu-debug'
    )
    parser.add_argument(
        '--tool',
        choices=['ui', 'waveform', 'envelope', 'lfsr'],
        default='ui',
        help='起動するデバッグツール (default: ui)'
    )
    
    parsed_args = parser.parse_args(args)
    
    try:
        from pypsgemu.core.ay38910 import create_ay38910_core
        from pypsgemu.core.device_config import create_debug_config
        
        # デバッグ用デバイス作成
        config = create_debug_config()
        device = create_ay38910_core(config)
        
        if parsed_args.tool == 'ui':
            from pypsgemu.debug.ui import launch_debug_ui
            print("デバッグUIを起動中...")
            launch_debug_ui(device)
        elif parsed_args.tool == 'waveform':
            from pypsgemu.debug.waveform_viewer import launch_waveform_viewer
            print("波形ビューアを起動中...")
            launch_waveform_viewer(device)
        elif parsed_args.tool == 'envelope':
            from pypsgemu.debug.envelope_viewer import launch_envelope_viewer
            print("エンベロープビューアを起動中...")
            launch_envelope_viewer(device)
        elif parsed_args.tool == 'lfsr':
            from pypsgemu.debug.visualizer import launch_lfsr_visualizer
            print("LFSRビジュアライザを起動中...")
            launch_lfsr_visualizer(device)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n中断されました")
        return 1
    except Exception as e:
        print(f"エラー: {e}")
        return 1


def test_main(args: Optional[List[str]] = None) -> int:
    """テストランナーのメインエントリーポイント"""
    parser = argparse.ArgumentParser(
        description='AY-3-8910 PSG Emulator Test Runner',
        prog='pypsgemu-test'
    )
    parser.add_argument(
        '--suite',
        choices=['unit', 'integration', 'performance', 'all'],
        default='all',
        help='実行するテストスイート (default: all)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='詳細出力'
    )
    
    parsed_args = parser.parse_args(args)
    
    try:
        import unittest
        
        # テストディスカバリー
        if parsed_args.suite == 'unit':
            test_dir = 'tests/unit'
        elif parsed_args.suite == 'integration':
            test_dir = 'tests/integration'
        elif parsed_args.suite == 'performance':
            test_dir = 'tests/performance'
        else:
            test_dir = 'tests'
        
        loader = unittest.TestLoader()
        suite = loader.discover(test_dir, pattern='test_*.py')
        
        # テスト実行
        verbosity = 2 if parsed_args.verbose else 1
        runner = unittest.TextTestRunner(verbosity=verbosity)
        result = runner.run(suite)
        
        # 結果に基づく終了コード
        if result.wasSuccessful():
            return 0
        else:
            return 1
            
    except Exception as e:
        print(f"テスト実行エラー: {e}")
        return 1


if __name__ == '__main__':
    # 直接実行された場合はデモを実行
    sys.exit(demo_main())
