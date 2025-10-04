#!/usr/bin/env python3
"""
AY-3-8910 PSG Emulator - 音声出力例

このスクリプトは、AY-3-8910エミュレータの音声出力機能を詳しく紹介します。
リアルタイム音声生成、ファイル出力、音声効果などを示します。
"""

import time
import math
import wave
import numpy as np
from pypsgemu.core.ay38910 import create_ay38910_core
from pypsgemu.core.device_config import create_default_config
from pypsgemu.audio.driver import AudioDriver
from pypsgemu.audio.sample_generator import SampleGenerator
from pypsgemu.audio.buffer import create_audio_buffer


def setup_audio_device():
    """音声出力用デバイスをセットアップ"""
    print("音声出力用AY-3-8910エミュレータを初期化中...")
    config = create_default_config()
    config.sample_rate = 44100
    config.volume_scale = 1.0  # 音量を100%に設定
    device = create_ay38910_core(config)
    
    return device, config


def set_tone_frequency(device, channel, frequency_hz, clock_frequency=2000000):
    """指定周波数でトーンを設定"""
    if frequency_hz == 0:
        period = 0
    else:
        period = int(clock_frequency / (16 * frequency_hz))
        period = max(1, min(4095, period))
    
    fine = period & 0xFF
    coarse = (period >> 8) & 0x0F
    
    base_reg = channel * 2
    device.write_register(base_reg, fine)
    device.write_register(base_reg + 1, coarse)


def set_volume(device, channel, volume):
    """音量を設定 (0-15)"""
    volume = max(0, min(15, volume))
    device.write_register(8 + channel, volume)


def example_realtime_audio(device, config):
    """リアルタイム音声出力の例"""
    print("\n=== リアルタイム音声出力 ===")
    
    # 音声出力を準備（バッファを0.2秒に増やして安定性向上）
    driver = AudioDriver(device, config.sample_rate, buffer_duration=0.2)
    
    # 簡単なメロディーを定義
    melody = [
        (261.63, 0.5),  # C4
        (293.66, 0.5),  # D4
        (329.63, 0.5),  # E4
        (349.23, 0.5),  # F4
        (392.00, 0.5),  # G4
        (440.00, 0.5),  # A4
        (493.88, 0.5),  # B4
        (523.25, 1.0),  # C5
    ]
    
    print("メロディーをリアルタイム再生...")
    
    # 初期設定
    set_volume(device, 0, 12)
    device.write_register(7, 0xFE)  # Tone A有効
    
    driver.start()
    
    for freq, duration in melody:
        set_tone_frequency(device, 0, freq)
        time.sleep(duration)
    
    # フェードアウト
    print("フェードアウト中...")
    for vol in range(12, -1, -1):
        set_volume(device, 0, vol)
        time.sleep(0.1)
    
    driver.stop()
    print("リアルタイム再生完了")


def example_wave_file_output(device, config):
    """WAVEファイル出力の例"""
    print("\n=== WAVEファイル出力 ===")
    
    # 出力設定
    duration = 5.0  # 5秒
    sample_rate = config.sample_rate
    total_samples = int(duration * sample_rate)
    
    print(f"WAVEファイル生成中... ({duration}秒, {sample_rate}Hz)")
    
    # 和音設定 (Cメジャーコード)
    frequencies = [261.63, 329.63, 392.00]  # C-E-G
    for i, freq in enumerate(frequencies):
        set_tone_frequency(device, i, freq)
        set_volume(device, i, 8)
    
    device.write_register(7, 0xF8)  # 全チャンネルのトーン有効
    
    # サンプル生成
    generator = SampleGenerator(device, config.sample_rate)
    samples = []
    
    # エンベロープ効果を追加
    device.write_register(11, 0x00)  # Envelope Fine
    device.write_register(12, 0x20)  # Envelope Coarse
    device.write_register(13, 0x0E)  # Envelope Shape (Triangle)
    device.write_register(8, 0x10)   # Channel A: エンベロープモード
    
    for i in range(total_samples):
        # 定期的にエンベロープをトリガー
        if i % (sample_rate // 2) == 0:  # 0.5秒ごと
            device.write_register(13, 0x0E)  # エンベロープ再トリガー
        
        # サンプル生成
        sample = generator.generate_samples(1)[0]
        samples.append(sample)
        
        # 進行状況表示
        if i % (sample_rate // 4) == 0:
            progress = (i / total_samples) * 100
            print(f"  進行状況: {progress:.0f}%")
    
    # WAVEファイルに保存
    filename = "ay38910_output.wav"
    samples_array = np.array(samples, dtype=np.float32)
    
    # 16ビット整数に変換
    samples_int16 = (samples_array * 32767).astype(np.int16)
    
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # モノラル
        wav_file.setsampwidth(2)  # 16ビット
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(samples_int16.tobytes())
    
    print(f"WAVEファイル保存完了: {filename}")
    print(f"  サンプル数: {len(samples)}")
    print(f"  ファイルサイズ: {len(samples_int16.tobytes())/1024:.1f} KB")


def example_audio_effects(device, config):
    """音声効果の例"""
    print("\n=== 音声効果 ===")

    driver = AudioDriver(device, config.sample_rate, buffer_duration=0.2)
    
    # 基本設定
    base_freq = 440  # A音
    set_volume(device, 0, 10)
    device.write_register(7, 0xFE)  # Tone A有効
    
    driver.start()
    
    # 1. ポルタメント効果
    print("1. ポルタメント効果 (音程スライド)")
    start_freq = 220  # A3
    end_freq = 880    # A5
    duration = 3.0
    steps = 100
    
    for i in range(steps):
        progress = i / (steps - 1)
        current_freq = start_freq + (end_freq - start_freq) * progress
        set_tone_frequency(device, 0, current_freq)
        time.sleep(duration / steps)
    
    time.sleep(0.5)
    
    # 2. トレモロ効果 (音量変調)
    print("2. トレモロ効果 (音量変調)")
    set_tone_frequency(device, 0, base_freq)
    
    start_time = time.time()
    while time.time() - start_time < 3.0:
        t = time.time() - start_time
        tremolo = 0.5 + 0.5 * math.sin(2 * math.pi * 4 * t)  # 4Hz変調
        volume = int(15 * tremolo)
        set_volume(device, 0, volume)
        time.sleep(0.02)  # 50Hz更新
    
    time.sleep(0.5)
    
    # 3. ビブラート効果 (周波数変調)
    print("3. ビブラート効果 (周波数変調)")
    set_volume(device, 0, 12)
    
    start_time = time.time()
    while time.time() - start_time < 3.0:
        t = time.time() - start_time
        vibrato = 10 * math.sin(2 * math.pi * 5 * t)  # 5Hz, ±10Hz変調
        current_freq = base_freq + vibrato
        set_tone_frequency(device, 0, current_freq)
        time.sleep(0.01)  # 100Hz更新
    
    time.sleep(0.5)
    
    # 4. アルペジオ効果
    print("4. アルペジオ効果")
    chord_freqs = [440, 554.37, 659.25]  # A-C#-E
    
    start_time = time.time()
    while time.time() - start_time < 4.0:
        for freq in chord_freqs:
            set_tone_frequency(device, 0, freq)
            time.sleep(0.1)  # 100ms間隔
    
    driver.stop()
    print("音声効果デモ完了")


def example_multi_channel_composition(device, config):
    """マルチチャンネル作曲の例"""
    print("\n=== マルチチャンネル作曲 ===")

    driver = AudioDriver(device, config.sample_rate, buffer_duration=0.2)
    
    # 楽曲構成
    # チャンネルA: メロディー
    # チャンネルB: ベース
    # チャンネルC: ハーモニー
    
    melody_notes = [
        (523.25, 0.5),  # C5
        (493.88, 0.5),  # B4
        (440.00, 0.5),  # A4
        (493.88, 0.5),  # B4
        (523.25, 1.0),  # C5
    ]
    
    bass_notes = [
        (130.81, 2.0),  # C3
        (146.83, 1.0),  # D3
    ]
    
    harmony_notes = [
        (329.63, 0.5),  # E4
        (349.23, 0.5),  # F4
        (329.63, 0.5),  # E4
        (349.23, 0.5),  # F4
        (392.00, 1.0),  # G4
    ]
    
    print("マルチチャンネル楽曲を演奏...")
    
    # 初期設定
    set_volume(device, 0, 12)  # メロディー
    set_volume(device, 1, 8)   # ベース
    set_volume(device, 2, 6)   # ハーモニー
    device.write_register(7, 0xF8)  # 全チャンネルのトーン有効
    
    driver.start()
    
    # 同期演奏
    melody_idx = 0
    bass_idx = 0
    harmony_idx = 0
    
    melody_time = 0
    bass_time = 0
    harmony_time = 0
    
    start_time = time.time()
    
    while melody_idx < len(melody_notes):
        current_time = time.time() - start_time
        
        # メロディー更新
        if current_time >= melody_time and melody_idx < len(melody_notes):
            freq, duration = melody_notes[melody_idx]
            set_tone_frequency(device, 0, freq)
            melody_time += duration
            melody_idx += 1
        
        # ベース更新
        if current_time >= bass_time and bass_idx < len(bass_notes):
            freq, duration = bass_notes[bass_idx]
            set_tone_frequency(device, 1, freq)
            bass_time += duration
            bass_idx += 1
        
        # ハーモニー更新
        if current_time >= harmony_time and harmony_idx < len(harmony_notes):
            freq, duration = harmony_notes[harmony_idx]
            set_tone_frequency(device, 2, freq)
            harmony_time += duration
            harmony_idx += 1
        
        time.sleep(0.01)  # 10ms間隔で更新
    
    # フェードアウト
    print("フェードアウト...")
    for vol in range(12, -1, -1):
        set_volume(device, 0, vol)
        set_volume(device, 1, max(0, vol - 4))
        set_volume(device, 2, max(0, vol - 6))
        time.sleep(0.1)
    
    driver.stop()
    print("マルチチャンネル作曲完了")


def example_noise_and_effects(device, config):
    """ノイズと特殊効果の例"""
    print("\n=== ノイズと特殊効果 ===")

    driver = AudioDriver(device, config.sample_rate, buffer_duration=0.2)
    
    driver.start()
    
    # 1. ホワイトノイズ
    print("1. ホワイトノイズ")
    device.write_register(6, 0)     # 最短ノイズ周期
    set_volume(device, 0, 8)
    device.write_register(7, 0xF7)  # Noise A有効, Tone A無効
    time.sleep(2)
    
    # 2. ピンクノイズ風
    print("2. ピンクノイズ風")
    device.write_register(6, 15)    # 中間ノイズ周期
    time.sleep(2)
    
    # 3. 低周波ノイズ
    print("3. 低周波ノイズ")
    device.write_register(6, 31)    # 最長ノイズ周期
    time.sleep(2)
    
    # 4. トーン+ノイズミックス
    print("4. トーン+ノイズミックス")
    set_tone_frequency(device, 0, 220)  # 低音
    device.write_register(6, 10)        # 中間ノイズ
    device.write_register(7, 0xF0)      # Tone A + Noise A有効
    time.sleep(3)
    
    # 5. エンベロープ付きノイズ
    print("5. エンベロープ付きノイズ")
    device.write_register(11, 0x00)  # Envelope Fine
    device.write_register(12, 0x08)  # Envelope Coarse
    device.write_register(13, 0x0A)  # Envelope Shape (Sawtooth)
    device.write_register(8, 0x10)   # エンベロープモード
    device.write_register(7, 0xF7)   # Noise A有効
    
    # エンベロープを数回トリガー
    for _ in range(5):
        device.write_register(13, 0x0A)  # エンベロープ再トリガー
        time.sleep(0.8)
    
    driver.stop()
    print("ノイズと特殊効果デモ完了")


def example_buffer_analysis(device, config):
    """オーディオバッファ解析の例"""
    print("\n=== オーディオバッファ解析 ===")
    
    # カスタムバッファを作成
    buffer = create_audio_buffer(config.sample_rate, buffer_duration=0.1)
    
    print("1. バッファ基本情報:")
    stats = buffer.get_statistics()
    print(f"   サイズ: {stats['size']} samples")
    print(f"   持続時間: {stats['size']/config.sample_rate*1000:.1f} ms")
    print(f"   メモリ使用量: {stats['memory_usage_bytes']/1024:.1f} KB")
    
    # 最適化テスト
    print("2. バッファ最適化テスト:")
    for latency_ms in [10, 25, 50, 100]:
        optimal_size = buffer.optimize_buffer_size(latency_ms, config.sample_rate)
        print(f"   {latency_ms}ms遅延 → {optimal_size} samples")
    
    # パフォーマンステスト
    print("3. バッファパフォーマンステスト:")
    test_samples = np.random.random(1024).astype(np.float32)
    
    start_time = time.time()
    for _ in range(100):
        buffer.write(test_samples)
        buffer.read(1024)
    end_time = time.time()
    
    operations_per_sec = 200 / (end_time - start_time)  # 100回の書き込み+読み込み
    print(f"   操作速度: {operations_per_sec:.0f} ops/sec")
    
    # 最終統計
    final_stats = buffer.get_statistics()
    print("4. 最終統計:")
    print(f"   総書き込み: {final_stats['total_written']} samples")
    print(f"   総読み込み: {final_stats['total_read']} samples")
    print(f"   アンダーラン: {final_stats['underruns']}")
    print(f"   オーバーラン: {final_stats['overruns']}")
    print(f"   効率スコア: {final_stats['efficiency_score']:.2f}")


def main():
    """メイン関数"""
    print("AY-3-8910 PSG Emulator - 音声出力例")
    print("=" * 50)
    
    try:
        # デバイスセットアップ
        device, config = setup_audio_device()
        
        # 各例を実行
        example_realtime_audio(device, config)
        example_wave_file_output(device, config)
        example_audio_effects(device, config)
        example_multi_channel_composition(device, config)
        example_noise_and_effects(device, config)
        example_buffer_analysis(device, config)
        
        print("\n" + "=" * 50)
        print("全ての音声出力例が完了しました！")
        
        # デバイス統計
        print(f"\nデバイス統計:")
        debug_info = device.get_debug_info()
        print(f"  サンプルレート: {config.sample_rate} Hz")
        print(f"  音量スケール: {config.volume_scale}")
        print(f"  総tick数: {debug_info['statistics']['total_ticks']}")
        
        perf_stats = device.get_performance_stats()
        print(f"  メモリ使用量: {perf_stats['memory_usage_bytes']/1024:.1f} KB")
        
        print(f"\n生成されたファイル:")
        print(f"  - ay38910_output.wav (WAVEファイル出力例)")
        
    except KeyboardInterrupt:
        print("\n\n中断されました")
    
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        raise
    
    finally:
        print("リソースをクリーンアップ中...")
        if 'device' in locals():
            device.reset()


if __name__ == "__main__":
    main()
