# AY-3-8910 PSG Emulator - ユーザーガイド

## はじめに

AY-3-8910 PSGエミュレータへようこそ！このガイドでは、エミュレータの基本的な使用方法から高度な機能まで、段階的に説明します。

## 目次

1. [インストール](#インストール)
2. [クイックスタート](#クイックスタート)
3. [基本的な使用方法](#基本的な使用方法)
4. [高度な機能](#高度な機能)
5. [デバッグ機能](#デバッグ機能)
6. [トラブルシューティング](#トラブルシューティング)
7. [FAQ](#faq)

---

## インストール

### システム要件

- **Python**: 3.8以上
- **OS**: Windows 10/11, macOS 10.14+, Linux (Ubuntu 18.04+)
- **メモリ**: 最低512MB、推奨1GB以上
- **オーディオ**: サウンドカード（音声出力用）

### 依存関係

```bash
pip install numpy matplotlib tkinter sounddevice psutil
```

### インストール方法

#### 方法1: pipからインストール（推奨）

```bash
pip install pypsgemu
```

#### 方法2: ソースからインストール

```bash
git clone https://github.com/your-repo/pypsgemu.git
cd pypsgemu
pip install -e .
```

### インストール確認

```python
import pypsgemu
print(f"PyPSGEmu version: {pypsgemu.__version__}")
```

---

## クイックスタート

### 5分で始める音声生成

```python
from pypsgemu.core.ay38910 import create_ay38910_core
from pypsgemu.audio.driver import AudioDriver
from pypsgemu.audio.sample_generator import SampleGenerator
from pypsgemu.core.device_config import create_default_config
import time

# 1. デバイスを作成
config = create_default_config()
device = create_ay38910_core(config)

# 2. 440Hz (A音) を設定
device.write_register(0, 0xFE)  # Tone A Fine
device.write_register(1, 0x00)  # Tone A Coarse
device.write_register(8, 0x0F)  # Volume A (最大)
device.write_register(7, 0xFE)  # Mixer: Tone A有効

# 3. 音声出力を開始
generator = SampleGenerator(device, config)
driver = AudioDriver(generator, config)
driver.start()

print("440Hz の音を5秒間再生します...")
time.sleep(5)

# 4. 停止
driver.stop()
print("再生完了！")
```

このコードを実行すると、440Hz（ピアノのA音）が5秒間再生されます。

---

## 基本的な使用方法

### 1. デバイスの作成と設定

#### デフォルト設定でデバイス作成

```python
from pypsgemu.core.ay38910 import create_ay38910_core
from pypsgemu.core.device_config import create_default_config

config = create_default_config()
device = create_ay38910_core(config)
```

#### カスタム設定でデバイス作成

```python
from pypsgemu.core.device_config import AY38910Config

config = AY38910Config(
    clock_frequency=2000000,  # 2MHz
    sample_rate=48000,        # 48kHz
    volume_scale=0.7,         # 音量70%
    enable_debug=True         # デバッグ有効
)
device = create_ay38910_core(config)
```

### 2. レジスタ操作

AY-3-8910は16個のレジスタ（R0-R15）を持ちます：

| レジスタ | 名前 | 説明 |
|---------|------|------|
| R0 | Tone A Fine | チャンネルA 音程（下位8ビット） |
| R1 | Tone A Coarse | チャンネルA 音程（上位4ビット） |
| R2 | Tone B Fine | チャンネルB 音程（下位8ビット） |
| R3 | Tone B Coarse | チャンネルB 音程（上位4ビット） |
| R4 | Tone C Fine | チャンネルC 音程（下位8ビット） |
| R5 | Tone C Coarse | チャンネルC 音程（上位4ビット） |
| R6 | Noise Period | ノイズ周期 |
| R7 | Mixer Control | ミキサー制御 |
| R8 | Volume A | チャンネルA 音量 |
| R9 | Volume B | チャンネルB 音量 |
| R10 | Volume C | チャンネルC 音量 |
| R11 | Envelope Fine | エンベロープ周期（下位8ビット） |
| R12 | Envelope Coarse | エンベロープ周期（上位8ビット） |
| R13 | Envelope Shape | エンベロープ形状 |
| R14 | I/O Port A | I/OポートA |
| R15 | I/O Port B | I/OポートB |

#### 基本的なレジスタ操作

```python
# レジスタに書き込み
device.write_register(0, 0x12)  # R0に0x12を書き込み

# レジスタから読み込み
value = device.read_register(0)  # R0の値を読み込み
print(f"R0 = 0x{value:02X}")
```

### 3. 音程の設定

音程は12ビット値（R0+R1, R2+R3, R4+R5）で設定します：

```python
def set_tone_frequency(device, channel, frequency_hz, clock_frequency=1789773):
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

# 使用例：チャンネルAに440Hz設定
set_tone_frequency(device, 0, 440)  # A音
```

### 4. 音量の設定

```python
def set_volume(device, channel, volume):
    """音量を設定 (0-15)"""
    volume = max(0, min(15, volume))
    device.write_register(8 + channel, volume)

# 使用例
set_volume(device, 0, 15)  # チャンネルA 最大音量
set_volume(device, 1, 8)   # チャンネルB 中音量
set_volume(device, 2, 0)   # チャンネルC 無音
```

### 5. ミキサーの設定

R7レジスタでトーンとノイズの有効/無効を制御：

```python
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

# 使用例：チャンネルAのトーンのみ有効
set_mixer(device, tone_enable=[True, False, False])
```

### 6. 音声出力

```python
from pypsgemu.audio.driver import AudioDriver
from pypsgemu.audio.sample_generator import SampleGenerator

# サンプルジェネレータとドライバを作成
generator = SampleGenerator(device, config)
driver = AudioDriver(generator, config)

# 音声出力開始
driver.start()

# 音楽を演奏...
# （レジスタ操作でメロディーを制御）

# 音声出力停止
driver.stop()
```

---

## 高度な機能

### 1. エンベロープ機能

エンベロープは音量の時間変化を自動制御する機能です。

#### エンベロープの設定

```python
def set_envelope(device, period, shape):
    """エンベロープを設定
    
    Args:
        period: エンベロープ周期 (0-65535)
        shape: エンベロープ形状 (0-15)
    """
    fine = period & 0xFF
    coarse = (period >> 8) & 0xFF
    
    device.write_register(11, fine)    # Envelope Fine
    device.write_register(12, coarse)  # Envelope Coarse
    device.write_register(13, shape)   # Envelope Shape

# エンベロープ形状の例
ENVELOPE_SHAPES = {
    0x08: "Decay (\\\\\\\\)",           # 減衰のみ
    0x0A: "Decay-Attack Repeat (\\/\\/)", # 減衰→攻撃の繰り返し
    0x0B: "Decay-Hold (\\‾‾‾)",         # 減衰→ホールド
    0x0C: "Attack-Decay Repeat (/|/|)", # 攻撃→減衰の繰り返し
    0x0D: "Attack-Hold (/‾‾‾)",         # 攻撃→ホールド
    0x0E: "Attack-Decay-Attack (/\\/)", # 攻撃→減衰→攻撃の繰り返し
    0x0F: "Attack-Hold (/‾‾‾)"          # 攻撃→ホールド
}

# 使用例：攻撃→ホールド エンベロープ
set_envelope(device, 1000, 0x0D)

# チャンネルAでエンベロープ使用（音量レジスタの最上位ビットを1に）
device.write_register(8, 0x10)  # エンベロープモード
```

### 2. ノイズ機能

```python
def set_noise(device, period, channels=[False, False, False]):
    """ノイズを設定
    
    Args:
        period: ノイズ周期 (0-31)
        channels: 各チャンネルでのノイズ有効化
    """
    device.write_register(6, period)  # Noise Period
    
    # ミキサーでノイズを有効化
    mixer_value = device.read_register(7)
    
    if channels[0]: mixer_value &= ~0x08  # チャンネルA ノイズ有効
    if channels[1]: mixer_value &= ~0x10  # チャンネルB ノイズ有効
    if channels[2]: mixer_value &= ~0x20  # チャンネルC ノイズ有効
    
    device.write_register(7, mixer_value)

# 使用例：チャンネルAでノイズ
set_noise(device, 15, channels=[True, False, False])
set_volume(device, 0, 10)
```

### 3. 和音の演奏

```python
def play_chord(device, frequencies, volumes=None):
    """和音を演奏
    
    Args:
        frequencies: [freq_A, freq_B, freq_C] 周波数リスト
        volumes: [vol_A, vol_B, vol_C] 音量リスト
    """
    if volumes is None:
        volumes = [15, 15, 15]
    
    # 各チャンネルに周波数設定
    for i, freq in enumerate(frequencies):
        if freq > 0:
            set_tone_frequency(device, i, freq)
            set_volume(device, i, volumes[i])
        else:
            set_volume(device, i, 0)
    
    # 全チャンネルのトーンを有効化
    set_mixer(device, tone_enable=[True, True, True])

# 使用例：Cメジャーコード (C-E-G)
play_chord(device, [261.63, 329.63, 392.00])  # C4-E4-G4
```

### 4. 状態管理

```python
from pypsgemu.utils.state_manager import create_state_manager

manager = create_state_manager()

# 現在の状態を保存
snapshot = manager.create_snapshot(device, "my_song_intro", "イントロ部分の設定")

# 設定を変更...
play_chord(device, [440, 554.37, 659.25])  # A-C#-E

# 元の状態に戻す
manager.restore_snapshot(device, "my_song_intro")

# パッチ（部分的な変更）を作成
volume_up_patch = manager.create_patch("volume_up", {
    8: 15,   # Volume A = 最大
    9: 15,   # Volume B = 最大
    10: 15   # Volume C = 最大
})

# パッチを適用
manager.apply_patch(device, "volume_up")
```

---

## デバッグ機能

### 1. デバッグUI

対話型のデバッグインターフェースを起動：

```python
from pypsgemu.debug.ui import launch_debug_ui

# デバッグUIを起動
launch_debug_ui(device)
```

デバッグUIでは以下の操作が可能です：
- リアルタイムレジスタ編集
- ミキサー制御（チェックボックス）
- 状態の保存・復元
- 自動更新機能

### 2. 波形ビューア

リアルタイムで波形を表示：

```python
from pypsgemu.debug.waveform_viewer import launch_waveform_viewer

# 波形ビューアを起動
launch_waveform_viewer(device, window_duration=0.05)  # 50ms窓
```

### 3. エンベロープビューア

エンベロープ形状を可視化：

```python
from pypsgemu.debug.envelope_viewer import launch_envelope_viewer

# エンベロープビューアを起動
launch_envelope_viewer(device)
```

### 4. LFSRビジュアライザ

ノイズ生成用17ビットLFSRの状態を表示：

```python
from pypsgemu.debug.visualizer import launch_lfsr_visualizer

# LFSRビジュアライザを起動
launch_lfsr_visualizer(device)
```

### 5. パフォーマンス監視

```python
# パフォーマンス統計を取得
stats = device.get_performance_stats()
print(f"平均tick時間: {stats['avg_tick_time']*1000000:.2f} μs")
print(f"メモリ使用量: {stats['memory_usage_bytes']/1024:.1f} KB")
print(f"CPU効率: {stats['cpu_efficiency']:.2f}")

# 最適化を適用
device.optimize_for_performance()
```

---

## トラブルシューティング

### よくある問題と解決方法

#### 1. 音が出ない

**症状**: `driver.start()`を実行しても音が出ない

**原因と解決方法**:
- **ミキサー設定**: トーンが無効になっている
  ```python
  device.write_register(7, 0xFE)  # チャンネルAのトーンを有効
  ```
- **音量設定**: 音量が0になっている
  ```python
  device.write_register(8, 0x0F)  # チャンネルAの音量を最大に
  ```
- **オーディオデバイス**: システムの音量設定を確認

#### 2. 音が歪む・ノイズが入る

**症状**: 音声出力に歪みやノイズが発生

**解決方法**:
- **音量スケール調整**:
  ```python
  config.volume_scale = 0.3  # 音量を下げる
  ```
- **バッファサイズ調整**:
  ```python
  config.buffer_size = 2048  # バッファサイズを大きく
  ```

#### 3. 高いCPU使用率

**症状**: エミュレータのCPU使用率が高い

**解決方法**:
- **パフォーマンス最適化を有効化**:
  ```python
  device.optimize_for_performance()
  ```
- **デバッグ機能を無効化**:
  ```python
  config.enable_debug = False
  ```

#### 4. メモリリーク

**症状**: 長時間実行でメモリ使用量が増加

**解決方法**:
- **適切なリソース解放**:
  ```python
  driver.stop()
  device.reset()
  ```
- **ガベージコレクション**:
  ```python
  import gc
  gc.collect()
  ```

#### 5. インポートエラー

**症状**: `ImportError` や `ModuleNotFoundError`

**解決方法**:
- **依存関係の再インストール**:
  ```bash
  pip install --upgrade numpy matplotlib sounddevice
  ```
- **Python環境の確認**:
  ```bash
  python --version  # 3.8以上であることを確認
  ```

### デバッグのヒント

#### ログ出力の有効化

```python
import logging

# デバッグログを有効化
logging.basicConfig(level=logging.DEBUG)

# デバッグ設定でデバイス作成
config = create_debug_config()
device = create_ay38910_core(config)
```

#### レジスタ状態の確認

```python
def print_all_registers(device):
    """全レジスタの状態を表示"""
    print("Register Status:")
    for i in range(16):
        value = device.read_register(i)
        print(f"R{i:2d}: 0x{value:02X} ({value:3d}) {value:08b}")

print_all_registers(device)
```

#### 音声出力の確認

```python
# 音声出力レベルを確認
output = device.get_mixed_output()
print(f"Mixed output: {output:.3f}")

# 各チャンネルの出力を確認
channels = device.get_channel_outputs()
for i, level in enumerate(channels):
    print(f"Channel {chr(65+i)}: {level:.3f}")
```

---

## FAQ

### Q1: どの程度正確なエミュレーションですか？

A: このエミュレータは実際のAY-3-8910チップの動作を可能な限り正確に再現しています。レジスタレベルでの互換性、正確なタイミング、LFSRノイズ生成アルゴリズムなど、ハードウェアの詳細な仕様に基づいて実装されています。

### Q2: リアルタイム演奏は可能ですか？

A: はい。最適化されたコアエンジンにより、リアルタイムでの音声生成と演奏が可能です。MIDIコントローラーやキーボード入力と組み合わせることで、ライブ演奏も実現できます。

### Q3: 他のPSGチップもサポートしますか？

A: 現在はAY-3-8910専用ですが、アーキテクチャは拡張可能に設計されています。将来的にはSN76489やYM2149などの類似チップのサポートも検討されています。

### Q4: 商用利用は可能ですか？

A: ライセンス条項に従って利用してください。詳細はLICENSEファイルを参照してください。

### Q5: パフォーマンスの要件は？

A: 一般的なPC環境で快適に動作します：
- CPU: 1GHz以上（推奨2GHz以上）
- メモリ: 512MB以上（推奨1GB以上）
- Python 3.8以上

### Q6: エラーが発生した場合は？

A: 以下の順序で確認してください：
1. [トラブルシューティング](#トラブルシューティング)セクションを参照
2. 依存関係の再インストール
3. 最新版への更新
4. GitHubのIssuesで報告

---

## 次のステップ

1. **[API Reference](api_reference.md)** - 詳細なAPI仕様
2. **[Examples](../examples/)** - 実用的なサンプルコード
3. **[GitHub Repository](https://github.com/your-repo/pypsgemu)** - ソースコードと最新情報

## サポート

- **GitHub Issues**: バグ報告・機能要望
- **Discussions**: 質問・議論
- **Wiki**: 追加情報・Tips

---

*このガイドがAY-3-8910エミュレータの活用に役立つことを願っています。素晴らしい音楽を作成してください！*
