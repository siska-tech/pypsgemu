#!/usr/bin/env python3
"""
AY-3-8910 PSG Emulator - 基本的な使用例

このスクリプトは、AY-3-8910エミュレータの基本的な使用方法を示します。
単純な音程生成から和音演奏まで、段階的に機能を紹介します。
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
    config.volume_scale = 1.0  # 音量を100%に設定
    device = create_ay38910_core(config)
    
    # 音声出力を準備（バッファを0.2秒に増やして安定性向上）
    driver = AudioDriver(device, config.sample_rate, buffer_duration=0.2)
    
    return device, driver, config


def set_tone_frequency(device, channel, frequency_hz, clock_frequency=2000000):
    """指定周波数でトーンを設定"""
    if frequency_hz == 0:
        period = 0
    else:
        period = int(clock_frequency / (16 * frequency_hz))
        period = max(1, min(4095, period))  # 1-4095の範囲
    
    fine = period & 0xFF
    coarse = (period >> 8) & 0x0F
    
    base_reg = channel * 2
    device.write_register(base_reg, fine)      # Fine
    device.write_register(base_reg + 1, coarse) # Coarse


def set_volume(device, channel, volume):
    """音量を設定 (0-15)"""
    volume = max(0, min(15, volume))
    device.write_register(8 + channel, volume)


def set_mixer(device, tone_enable=[True, True, True], noise_enable=[False, False, False]):
    """ミキサーを設定"""
    mixer_value = 0
    
    # トーンイネーブル（0=有効, 1=無効）
    if not tone_enable[0]: mixer_value |= 0x01
    if not tone_enable[1]: mixer_value |= 0x02
    if not tone_enable[2]: mixer_value |= 0x04
    
    # ノイズイネーブル（0=有効, 1=無効）
    if not noise_enable[0]: mixer_value |= 0x08
    if not noise_enable[1]: mixer_value |= 0x10
    if not noise_enable[2]: mixer_value |= 0x20
    
    device.write_register(7, mixer_value)


def example_1_single_tone(device, driver):
    """例1: 単一トーンの生成"""
    print("\n=== 例1: 単一トーン (440Hz A音) ===")
    
    # チャンネルAに440Hz設定
    set_tone_frequency(device, 0, 440)  # A音
    set_volume(device, 0, 15)           # 最大音量
    set_mixer(device, tone_enable=[True, False, False])  # チャンネルAのみ
    
    print("440Hz (A音) を3秒間再生...")
    driver.start()
    time.sleep(3)
    driver.stop()
    print("完了")


def example_2_scale(device, driver):
    """例2: 音階の演奏"""
    print("\n=== 例2: ドレミファソラシド ===")
    
    # C4からC5までの音階（Hz）
    scale_frequencies = [
        261.63,  # C4 (ド)
        293.66,  # D4 (レ)
        329.63,  # E4 (ミ)
        349.23,  # F4 (ファ)
        392.00,  # G4 (ソ)
        440.00,  # A4 (ラ)
        493.88,  # B4 (シ)
        523.25   # C5 (ド)
    ]
    
    scale_names = ["ド", "レ", "ミ", "ファ", "ソ", "ラ", "シ", "ド"]
    
    set_volume(device, 0, 12)  # 適度な音量
    set_mixer(device, tone_enable=[True, False, False])
    
    driver.start()
    
    for freq, name in zip(scale_frequencies, scale_names):
        print(f"  {name} ({freq:.1f}Hz)")
        set_tone_frequency(device, 0, freq)
        time.sleep(0.5)  # 0.5秒ずつ
    
    driver.stop()
    print("音階演奏完了")


def example_3_chord(device, driver):
    """例3: 和音の演奏"""
    print("\n=== 例3: 和音演奏 ===")
    
    # Cメジャーコード (C-E-G)
    chord_frequencies = [261.63, 329.63, 392.00]  # C4-E4-G4
    chord_names = ["C", "E", "G"]
    
    print("Cメジャーコード (C-E-G) を設定中...")
    
    # 各チャンネルに周波数設定
    for i, (freq, name) in enumerate(zip(chord_frequencies, chord_names)):
        set_tone_frequency(device, i, freq)
        set_volume(device, i, 10)  # 適度な音量
        print(f"  チャンネル{chr(65+i)}: {name} ({freq:.1f}Hz)")
    
    # 全チャンネルのトーンを有効化
    set_mixer(device, tone_enable=[True, True, True])
    
    print("和音を3秒間再生...")
    driver.start()
    time.sleep(3)
    driver.stop()
    print("和音演奏完了")


def example_4_envelope(device, driver):
    """例4: エンベロープ機能"""
    print("\n=== 例4: エンベロープ機能 ===")
    
    # エンベロープ設定
    envelope_period = 2000  # エンベロープ周期
    envelope_shape = 0x0D   # Attack-Hold (攻撃→ホールド)
    
    fine = envelope_period & 0xFF
    coarse = (envelope_period >> 8) & 0xFF
    
    device.write_register(11, fine)    # Envelope Fine
    device.write_register(12, coarse)  # Envelope Coarse
    device.write_register(13, envelope_shape)  # Envelope Shape
    
    print(f"エンベロープ設定: 周期={envelope_period}, 形状=Attack-Hold")
    
    # チャンネルAでエンベロープ使用
    set_tone_frequency(device, 0, 440)  # A音
    device.write_register(8, 0x10)      # エンベロープモード（最上位ビット=1）
    set_mixer(device, tone_enable=[True, False, False])
    
    print("エンベロープ付きA音を5秒間再生...")
    driver.start()
    time.sleep(5)
    driver.stop()
    print("エンベロープ演奏完了")


def example_5_noise(device, driver):
    """例5: ノイズ機能"""
    print("\n=== 例5: ノイズ機能 ===")
    
    # ノイズ設定
    noise_period = 15  # ノイズ周期 (0-31)
    device.write_register(6, noise_period)  # Noise Period
    
    # チャンネルAでノイズを有効化
    set_volume(device, 0, 10)
    
    # ミキサーでノイズを有効、トーンを無効
    mixer_value = 0x01  # トーンA無効
    mixer_value &= ~0x08  # ノイズA有効
    device.write_register(7, mixer_value)
    
    print(f"ノイズ (周期={noise_period}) を3秒間再生...")
    driver.start()
    time.sleep(3)
    driver.stop()
    print("ノイズ再生完了")


def example_6_mixed_sound(device, driver):
    """例6: トーン+ノイズのミックス"""
    print("\n=== 例6: トーン+ノイズのミックス ===")
    
    # チャンネルA: トーン (低音)
    set_tone_frequency(device, 0, 110)  # A2音
    set_volume(device, 0, 8)
    
    # チャンネルB: ノイズ
    device.write_register(6, 20)  # ノイズ周期
    set_volume(device, 1, 6)
    
    # チャンネルC: 高音トーン
    set_tone_frequency(device, 2, 880)  # A5音
    set_volume(device, 2, 4)
    
    # ミキサー設定: 全チャンネルのトーン有効、チャンネルBのノイズ有効
    mixer_value = 0x00  # 全トーン有効
    mixer_value &= ~0x10  # ノイズB有効
    device.write_register(7, mixer_value)
    
    print("トーン+ノイズのミックスを4秒間再生...")
    driver.start()
    time.sleep(4)
    driver.stop()
    print("ミックス再生完了")


def example_7_vibrato(device, driver):
    """例7: ビブラート効果"""
    print("\n=== 例7: ビブラート効果 ===")
    
    base_frequency = 440  # 基本周波数 (A音)
    vibrato_depth = 10    # ビブラートの深さ (Hz)
    vibrato_speed = 5     # ビブラートの速度 (Hz)
    
    set_volume(device, 0, 12)
    set_mixer(device, tone_enable=[True, False, False])
    
    print(f"ビブラート付きA音 (深さ±{vibrato_depth}Hz, 速度{vibrato_speed}Hz) を5秒間再生...")
    
    driver.start()
    
    start_time = time.time()
    while time.time() - start_time < 5.0:
        # ビブラート計算
        t = time.time() - start_time
        vibrato_offset = vibrato_depth * math.sin(2 * math.pi * vibrato_speed * t)
        current_frequency = base_frequency + vibrato_offset
        
        set_tone_frequency(device, 0, current_frequency)
        time.sleep(0.01)  # 10ms間隔で更新
    
    driver.stop()
    print("ビブラート演奏完了")


def main():
    """メイン関数"""
    print("AY-3-8910 PSG Emulator - 基本使用例")
    print("=" * 50)
    
    try:
        # デバイスセットアップ
        device, driver, config = setup_device()
        
        # 各例を実行
        example_1_single_tone(device, driver)
        example_2_scale(device, driver)
        example_3_chord(device, driver)
        example_4_envelope(device, driver)
        example_5_noise(device, driver)
        example_6_mixed_sound(device, driver)
        example_7_vibrato(device, driver)
        
        print("\n" + "=" * 50)
        print("全ての例が完了しました！")
        
        # デバイス情報表示
        print(f"\nデバイス情報:")
        print(f"  名前: {device.name}")
        print(f"  クロック周波数: {config.clock_frequency/1000000:.1f} MHz")
        print(f"  サンプルレート: {config.sample_rate} Hz")
        
        # パフォーマンス統計
        stats = device.get_performance_stats()
        if stats['tick_count'] > 0:
            print(f"  平均tick時間: {stats['avg_tick_time']*1000000:.2f} μs")
            print(f"  メモリ使用量: {stats['memory_usage_bytes']/1024:.1f} KB")
        
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
