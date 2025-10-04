#!/usr/bin/env python3
"""
AY-3-8910 PSG Emulator - レジスタ制御例

このスクリプトは、AY-3-8910エミュレータのレジスタ制御機能を詳しく紹介します。
各レジスタの機能、設定方法、実用的な使用例を示します。
"""

import time
import math
from pypsgemu.core.ay38910 import create_ay38910_core
from pypsgemu.core.device_config import create_default_config
from pypsgemu.audio.driver import AudioDriver
from pypsgemu.audio.sample_generator import SampleGenerator


def setup_device():
    """デバイスをセットアップ"""
    print("AY-3-8910エミュレータを初期化中...")
    config = create_default_config()
    config.volume_scale = 0.4
    device = create_ay38910_core(config)

    # バッファを0.2秒に増やして安定性向上
    driver = AudioDriver(device, config.sample_rate, buffer_duration=0.2)
    
    return device, driver, config


def print_register_info(device, title="レジスタ状態"):
    """レジスタ情報を表示"""
    print(f"\n{title}:")
    register_names = [
        "R0:  Tone A Fine", "R1:  Tone A Coarse",
        "R2:  Tone B Fine", "R3:  Tone B Coarse", 
        "R4:  Tone C Fine", "R5:  Tone C Coarse",
        "R6:  Noise Period", "R7:  Mixer Control",
        "R8:  Volume A", "R9:  Volume B", "R10: Volume C",
        "R11: Envelope Fine", "R12: Envelope Coarse", "R13: Envelope Shape",
        "R14: I/O Port A", "R15: I/O Port B"
    ]
    
    for i in range(16):
        value = device.read_register(i)
        print(f"  {register_names[i]}: 0x{value:02X} ({value:3d}) {value:08b}")


def example_tone_registers(device, driver):
    """トーンレジスタ (R0-R5) の例"""
    print("\n=== トーンレジスタ (R0-R5) ===")
    
    print("トーンレジスタは12ビット値で音程を制御します")
    print("周波数 = クロック周波数 / (16 * トーン値)")
    
    # 各チャンネルに異なる音程を設定
    frequencies = [440, 554.37, 659.25]  # A-C#-E (Aメジャーコード)
    tone_values = []
    
    for i, freq in enumerate(frequencies):
        # 12ビットトーン値を計算
        tone_value = int(1789773 / (16 * freq))
        tone_values.append(tone_value)
        
        # Fine (下位8ビット) と Coarse (上位4ビット) に分割
        fine = tone_value & 0xFF
        coarse = (tone_value >> 8) & 0x0F
        
        # レジスタに設定
        device.write_register(i * 2, fine)      # R0, R2, R4
        device.write_register(i * 2 + 1, coarse) # R1, R3, R5
        
        print(f"チャンネル {chr(65+i)}: {freq:.1f}Hz → トーン値={tone_value} (Fine=0x{fine:02X}, Coarse=0x{coarse:02X})")
    
    # 音量とミキサー設定
    for i in range(3):
        device.write_register(8 + i, 12)  # 音量設定
    device.write_register(7, 0xF8)  # 全チャンネルのトーン有効
    
    print("\nAメジャーコードを3秒間再生...")
    driver.start()
    time.sleep(3)
    driver.stop()
    
    print_register_info(device, "トーンレジスタ設定後")


def example_noise_register(device, driver):
    """ノイズレジスタ (R6) の例"""
    print("\n=== ノイズレジスタ (R6) ===")
    
    print("ノイズレジスタは5ビット値でノイズ周期を制御します")
    print("ノイズ周波数 = クロック周波数 / (16 * ノイズ値)")
    
    # 様々なノイズ周期をテスト
    noise_periods = [1, 5, 10, 20, 31]
    
    # チャンネルAでノイズを有効化
    device.write_register(8, 10)   # Volume A
    device.write_register(7, 0xF7)  # Noise A有効, Tone A無効
    
    driver.start()
    
    for period in noise_periods:
        print(f"ノイズ周期: {period} (約{1789773/(16*period):.0f}Hz)")
        device.write_register(6, period)
        time.sleep(1.5)
    
    driver.stop()
    
    print_register_info(device, "ノイズレジスタ設定後")


def example_mixer_register(device, driver):
    """ミキサーレジスタ (R7) の例"""
    print("\n=== ミキサーレジスタ (R7) ===")
    
    print("ミキサーレジスタは各チャンネルのトーン/ノイズを制御します")
    print("ビット配置: [7:6]=未使用, [5]=NoiseC, [4]=NoiseB, [3]=NoiseA, [2]=ToneC, [1]=ToneB, [0]=ToneA")
    print("0=有効, 1=無効")
    
    # 基本設定
    device.write_register(0, 0xFE)  # Tone A: 440Hz
    device.write_register(2, 0xC8)  # Tone B: 554Hz
    device.write_register(4, 0x9C)  # Tone C: 659Hz
    device.write_register(6, 15)    # Noise Period
    
    for i in range(3):
        device.write_register(8 + i, 10)  # 音量設定
    
    # 様々なミキサー設定をテスト
    mixer_configs = [
        (0xFE, "Tone A のみ"),
        (0xFD, "Tone B のみ"),
        (0xFB, "Tone C のみ"),
        (0xF8, "全トーン"),
        (0xF7, "Noise A のみ"),
        (0xF0, "Tone A + Noise A"),
        (0xE0, "全トーン + 全ノイズ"),
    ]
    
    driver.start()
    
    for mixer_value, description in mixer_configs:
        print(f"ミキサー設定: 0x{mixer_value:02X} ({mixer_value:08b}) - {description}")
        device.write_register(7, mixer_value)
        time.sleep(2)
    
    driver.stop()
    
    print_register_info(device, "ミキサーレジスタ設定後")


def example_volume_registers(device, driver):
    """音量レジスタ (R8-R10) の例"""
    print("\n=== 音量レジスタ (R8-R10) ===")
    
    print("音量レジスタは4ビット値で音量を制御します")
    print("ビット4=1の場合、エンベロープモードになります")
    
    # 基本トーン設定
    device.write_register(0, 0xFE)  # 440Hz
    device.write_register(7, 0xFE)  # Tone A有効
    
    driver.start()
    
    # 音量レベルテスト
    print("音量レベルテスト (0-15):")
    for volume in range(16):
        print(f"  音量: {volume:2d}/15")
        device.write_register(8, volume)
        time.sleep(0.3)
    
    time.sleep(0.5)
    
    # エンベロープモードテスト
    print("エンベロープモードテスト:")
    
    # エンベロープ設定
    device.write_register(11, 0x00)  # Envelope Fine
    device.write_register(12, 0x08)  # Envelope Coarse
    device.write_register(13, 0x0E)  # Envelope Shape (Triangle)
    
    print("  固定音量モード (音量=12)")
    device.write_register(8, 12)  # 固定音量
    time.sleep(2)
    
    print("  エンベロープモード")
    device.write_register(8, 0x10)  # エンベロープモード (ビット4=1)
    time.sleep(3)
    
    driver.stop()
    
    print_register_info(device, "音量レジスタ設定後")


def example_envelope_registers(device, driver):
    """エンベロープレジスタ (R11-R13) の例"""
    print("\n=== エンベロープレジスタ (R11-R13) ===")
    
    print("エンベロープレジスタは音量の時間変化を制御します")
    print("R11-R12: 16ビット周期値, R13: 4ビット形状")
    
    # 基本設定
    device.write_register(0, 0xFE)  # 440Hz
    device.write_register(8, 0x10)  # エンベロープモード
    device.write_register(7, 0xFE)  # Tone A有効
    
    # エンベロープ形状の説明
    envelope_shapes = [
        (0x08, "Decay (\\\\\\\\)", "減衰のみ"),
        (0x0A, "Decay-Attack Repeat (\\/\\/)", "減衰→攻撃の繰り返し"),
        (0x0B, "Decay-Hold (\\___)", "減衰→ホールド"),
        (0x0C, "Attack-Decay Repeat (/|/|)", "攻撃→減衰の繰り返し"),
        (0x0D, "Attack-Hold (/___)", "攻撃→ホールド"),
        (0x0E, "Attack-Decay-Attack (/\\/)", "攻撃→減衰→攻撃の繰り返し"),
        (0x0F, "Attack-Hold (/___)", "攻撃→ホールド")
    ]
    
    driver.start()
    
    for shape_value, shape_pattern, description in envelope_shapes:
        print(f"エンベロープ形状: 0x{shape_value:02X} {shape_pattern} - {description}")
        
        # エンベロープ周期設定 (約1秒)
        period = 1789773 // 256  # 約1秒周期
        device.write_register(11, period & 0xFF)        # Fine
        device.write_register(12, (period >> 8) & 0xFF) # Coarse
        device.write_register(13, shape_value)          # Shape
        
        time.sleep(3)
    
    # 異なる周期でのテスト
    print("\n異なる周期でのテスト (Attack-Hold):")
    device.write_register(13, 0x0D)  # Attack-Hold
    
    periods_ms = [100, 500, 1000, 2000]
    for period_ms in periods_ms:
        print(f"  周期: {period_ms}ms")
        period = int(1789773 * period_ms / 1000 / 256)
        device.write_register(11, period & 0xFF)
        device.write_register(12, (period >> 8) & 0xFF)
        device.write_register(13, 0x0D)  # 形状再設定でトリガー
        time.sleep(period_ms / 1000 + 0.5)
    
    driver.stop()
    
    print_register_info(device, "エンベロープレジスタ設定後")


def example_io_port_registers(device):
    """I/Oポートレジスタ (R14-R15) の例"""
    print("\n=== I/Oポートレジスタ (R14-R15) ===")
    
    print("I/Oポートレジスタは外部デバイスとの通信に使用されます")
    print("このエミュレータでは読み書き可能ですが、実際の機能は実装されていません")
    
    # 様々な値を書き込んでテスト
    test_values = [0x00, 0x55, 0xAA, 0xFF]
    
    for port in [14, 15]:
        port_name = "A" if port == 14 else "B"
        print(f"\nI/Oポート{port_name} (R{port}) テスト:")
        
        for value in test_values:
            device.write_register(port, value)
            read_value = device.read_register(port)
            print(f"  書き込み: 0x{value:02X} → 読み込み: 0x{read_value:02X} {'✓' if value == read_value else '✗'}")
    
    print_register_info(device, "I/Oポートレジスタ設定後")


def example_register_interactions(device, driver):
    """レジスタ間の相互作用の例"""
    print("\n=== レジスタ間の相互作用 ===")
    
    print("複数のレジスタが連携して動作する例を示します")
    
    # 複雑な設定例: 3チャンネル + エンベロープ + ノイズ
    print("\n複雑な設定例:")
    print("- チャンネルA: 440Hz + エンベロープ")
    print("- チャンネルB: 554Hz + 固定音量")
    print("- チャンネルC: ノイズのみ")
    
    # チャンネルA: トーン + エンベロープ
    device.write_register(0, 0xFE)  # Tone A Fine
    device.write_register(1, 0x00)  # Tone A Coarse
    device.write_register(8, 0x10)  # Volume A (エンベロープモード)
    
    # チャンネルB: トーン + 固定音量
    device.write_register(2, 0xC8)  # Tone B Fine
    device.write_register(3, 0x00)  # Tone B Coarse
    device.write_register(9, 0x08)  # Volume B (固定音量)
    
    # チャンネルC: ノイズのみ
    device.write_register(10, 0x06)  # Volume C
    
    # ノイズ設定
    device.write_register(6, 20)    # Noise Period
    
    # エンベロープ設定
    device.write_register(11, 0x00)  # Envelope Fine
    device.write_register(12, 0x10)  # Envelope Coarse
    device.write_register(13, 0x0C)  # Envelope Shape (Attack-Decay Repeat)
    
    # ミキサー設定: Tone A,B + Noise C
    device.write_register(7, 0x24)  # 00100100b
    
    print_register_info(device, "複雑な設定")
    
    print("\n複雑な設定で5秒間再生...")
    driver.start()
    time.sleep(5)
    driver.stop()
    
    # 動的変更の例
    print("\n動的変更の例:")
    print("再生中にレジスタを変更して効果を確認")
    
    driver.start()
    
    # 段階的に設定を変更
    changes = [
        (1, "エンベロープ周期を短縮", lambda: device.write_register(12, 0x04)),
        (1, "チャンネルBの音程を上げる", lambda: device.write_register(2, 0x64)),
        (1, "ノイズ周期を変更", lambda: device.write_register(6, 5)),
        (1, "エンベロープ形状を変更", lambda: device.write_register(13, 0x0E)),
        (1, "全体音量を下げる", lambda: [device.write_register(8, 0x10), device.write_register(9, 0x04), device.write_register(10, 0x03)]),
    ]
    
    for duration, description, change_func in changes:
        print(f"  {description}")
        change_func()
        time.sleep(duration)
    
    driver.stop()
    
    print_register_info(device, "動的変更後")


def main():
    """メイン関数"""
    print("AY-3-8910 PSG Emulator - レジスタ制御例")
    print("=" * 60)
    
    try:
        # デバイスセットアップ
        device, driver, config = setup_device()
        
        print_register_info(device, "初期状態")
        
        # 各レジスタグループの例を実行
        example_tone_registers(device, driver)
        example_noise_register(device, driver)
        example_mixer_register(device, driver)
        example_volume_registers(device, driver)
        example_envelope_registers(device, driver)
        example_io_port_registers(device)
        example_register_interactions(device, driver)
        
        print("\n" + "=" * 60)
        print("全てのレジスタ制御例が完了しました！")
        
        # 最終統計
        print(f"\nデバイス統計:")
        debug_info = device.get_debug_info()
        print(f"  レジスタ書き込み回数: {debug_info['statistics']['register_writes']}")
        print(f"  レジスタ読み込み回数: {debug_info['statistics']['register_reads']}")
        print(f"  総tick数: {debug_info['statistics']['total_ticks']}")
        
        print(f"\nレジスタ制御をマスターして、AY-3-8910の真の力を引き出してください！")
        
    except KeyboardInterrupt:
        print("\n\n中断されました")
        if 'driver' in locals():
            driver.stop()
    
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        if 'driver' in locals():
            driver.stop()
        raise
    
    finally:
        print("リソースをクリーンアップ中...")
        if 'driver' in locals():
            driver.stop()
        if 'device' in locals():
            device.reset()


if __name__ == "__main__":
    main()
