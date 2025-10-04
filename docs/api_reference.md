# AY-3-8910 PSG Emulator - API Reference

## 概要

このドキュメントは、AY-3-8910 PSGエミュレータの完全なAPIリファレンスです。すべての公開クラス、メソッド、関数の詳細な仕様と使用例を提供します。

## 目次

- [コアAPI](#コアapi)
- [オーディオAPI](#オーディオapi)
- [デバッグAPI](#デバッグapi)
- [ユーティリティAPI](#ユーティリティapi)
- [エラーハンドリング](#エラーハンドリング)
- [使用例](#使用例)

---

## コアAPI

### AY38910Core

AY-3-8910チップの完全なエミュレーションを提供するメインクラス。

#### クラス定義

```python
class AY38910Core(Device, AudioDevice):
    """AY-3-8910 コアエミュレータ"""
```

#### コンストラクタ

```python
def __init__(self, config: AY38910Config)
```

**パラメータ:**
- `config` (AY38910Config): エミュレータ設定

**例:**
```python
from pypsgemu.core.ay38910 import create_ay38910_core
from pypsgemu.core.device_config import create_default_config

config = create_default_config()
device = create_ay38910_core(config)
```

#### プロパティ

##### name
```python
@property
def name(self) -> str
```
デバイス名を取得します。

**戻り値:** `"AY-3-8910 PSG"`

#### メソッド

##### reset()
```python
def reset(self) -> None
```
エミュレータを初期状態にリセットします。

**例:**
```python
device.reset()
```

##### tick()
```python
def tick(self, master_cycles: int) -> int
```
指定されたマスタークロックサイクル数だけエミュレーションを実行します。

**パラメータ:**
- `master_cycles` (int): 実行するサイクル数

**戻り値:** 実際に消費されたサイクル数

**例外:**
- `InvalidValueError`: サイクル数が負の場合

**例:**
```python
# 1000サイクル実行
consumed = device.tick(1000)
print(f"Consumed {consumed} cycles")
```

##### read_register()
```python
def read_register(self, address: int) -> int
```
指定されたアドレスのレジスタ値を読み取ります。

**パラメータ:**
- `address` (int): レジスタアドレス (0-15)

**戻り値:** レジスタ値 (0-255)

**例外:**
- `RegisterAccessError`: 無効なアドレスの場合

**例:**
```python
# R0 (Tone A Fine) を読み取り
value = device.read_register(0)
print(f"R0 = 0x{value:02X}")
```

##### write_register()
```python
def write_register(self, address: int, value: int) -> None
```
指定されたアドレスのレジスタに値を書き込みます。

**パラメータ:**
- `address` (int): レジスタアドレス (0-15)
- `value` (int): 書き込み値 (0-255)

**例外:**
- `RegisterAccessError`: 無効なアドレスの場合
- `InvalidValueError`: 無効な値の場合

**例:**
```python
# 440Hz の音程を設定 (A音)
device.write_register(0, 0xFE)  # R0: Tone A Fine
device.write_register(1, 0x00)  # R1: Tone A Coarse
device.write_register(8, 0x0F)  # R8: Volume A (最大)
```

##### get_mixed_output()
```python
def get_mixed_output(self) -> float
```
現在のミックス済み音声出力を取得します。

**戻り値:** 正規化された音声出力 (-1.0〜1.0)

**例:**
```python
output = device.get_mixed_output()
print(f"Audio output: {output:.3f}")
```

##### get_channel_outputs()
```python
def get_channel_outputs(self) -> List[float]
```
各チャンネルの個別出力を取得します。

**戻り値:** 各チャンネルの出力値のリスト [A, B, C]

**例:**
```python
outputs = device.get_channel_outputs()
print(f"Channel A: {outputs[0]:.3f}")
print(f"Channel B: {outputs[1]:.3f}")
print(f"Channel C: {outputs[2]:.3f}")
```

##### get_state()
```python
def get_state(self) -> Dict[str, Any]
```
現在の内部状態を取得します。

**戻り値:** 状態辞書

**例:**
```python
state = device.get_state()
print(f"Master clock: {state['master_clock_counter']}")
print(f"Registers: {state['registers']}")
```

##### set_state()
```python
def set_state(self, state: Dict[str, Any]) -> None
```
内部状態を復元します。

**パラメータ:**
- `state` (Dict[str, Any]): 状態辞書

**例外:**
- `InvalidValueError`: 状態が無効な場合

##### get_performance_stats()
```python
def get_performance_stats(self) -> Dict[str, Any]
```
パフォーマンス統計を取得します。

**戻り値:** パフォーマンス統計辞書

**例:**
```python
stats = device.get_performance_stats()
print(f"Average tick time: {stats['avg_tick_time']:.6f}s")
print(f"Memory usage: {stats['memory_usage_bytes']} bytes")
```

### AY38910Config

エミュレータの設定を管理するクラス。

#### クラス定義

```python
@dataclass
class AY38910Config:
    """AY-3-8910エミュレータ設定"""
```

#### 主要フィールド

```python
clock_frequency: int = 1789773        # クロック周波数 (Hz)
sample_rate: int = 44100             # サンプルレート (Hz)
channels: int = 1                    # チャンネル数
dtype: str = 'float32'               # データ型
buffer_size: int = 1024              # バッファサイズ
volume_scale: float = 0.5            # 音量スケール
enable_debug: bool = False           # デバッグ有効化
```

#### ファクトリ関数

```python
def create_default_config() -> AY38910Config
def create_debug_config() -> AY38910Config
```

**例:**
```python
from pypsgemu.core.device_config import create_default_config, create_debug_config

# デフォルト設定
config = create_default_config()

# デバッグ設定
debug_config = create_debug_config()
```

---

## オーディオAPI

### AudioBuffer

音声サンプル用循環バッファクラス。

#### コンストラクタ

```python
def __init__(self, size: int, channels: int = 1, dtype=np.float32)
```

**パラメータ:**
- `size` (int): バッファサイズ（サンプル数）
- `channels` (int): チャンネル数 (1 or 2)
- `dtype`: サンプルデータ型

#### メソッド

##### write()
```python
def write(self, samples: np.ndarray, timeout: Optional[float] = None) -> int
```
サンプルをバッファに書き込みます。

**パラメータ:**
- `samples` (np.ndarray): 書き込むサンプルデータ
- `timeout` (Optional[float]): タイムアウト時間（秒）

**戻り値:** 実際に書き込まれたサンプル数

**例:**
```python
import numpy as np
from pypsgemu.audio.buffer import AudioBuffer

buffer = AudioBuffer(size=1024, channels=1)
samples = np.array([0.1, 0.2, 0.3], dtype=np.float32)
written = buffer.write(samples)
print(f"Written {written} samples")
```

##### read()
```python
def read(self, count: int, timeout: Optional[float] = None) -> Optional[np.ndarray]
```
サンプルをバッファから読み取ります。

**パラメータ:**
- `count` (int): 読み取るサンプル数
- `timeout` (Optional[float]): タイムアウト時間（秒）

**戻り値:** 読み取ったサンプルデータ、タイムアウト時はNone

##### get_audio_buffer()
```python
def get_audio_buffer(self, count: int = None) -> Optional[np.ndarray]
```
バッファ内容を取得します（デバッグ・可視化用）。

**パラメータ:**
- `count` (Optional[int]): 取得するサンプル数（Noneで全バッファ）

**戻り値:** バッファ内容のコピー

##### optimize_buffer_size()
```python
def optimize_buffer_size(self, target_latency_ms: float, sample_rate: int) -> int
```
最適なバッファサイズを計算します。

**パラメータ:**
- `target_latency_ms` (float): 目標レイテンシ（ミリ秒）
- `sample_rate` (int): サンプルレート

**戻り値:** 推奨バッファサイズ

### AudioDriver

音声出力ドライバクラス。

#### メソッド

##### start()
```python
def start(self) -> None
```
音声出力を開始します。

##### stop()
```python
def stop(self) -> None
```
音声出力を停止します。

**例:**
```python
from pypsgemu.audio.driver import AudioDriver
from pypsgemu.audio.sample_generator import SampleGenerator

# サンプルジェネレータを作成
generator = SampleGenerator(device, config)

# ドライバを作成・開始
driver = AudioDriver(generator, config)
driver.start()

# 音声再生...

driver.stop()
```

---

## デバッグAPI

### DebugUI

対話型デバッグインターフェース。

#### コンストラクタ

```python
def __init__(self, device: Device, title: str = "AY-3-8910 Debug UI")
```

#### メソッド

##### run()
```python
def run(self) -> None
```
UIを実行します。

**例:**
```python
from pypsgemu.debug.ui import create_debug_ui

ui = create_debug_ui(device)
ui.run()  # UIウィンドウが開く
```

### WaveformViewer

波形表示ビューア。

#### コンストラクタ

```python
def __init__(self, device: Device, parent: tk.Widget = None, 
             window_duration: float = 0.02, sample_rate: int = 44100)
```

#### メソッド

##### start()
```python
def start(self) -> None
```
波形表示を開始します。

##### plot_waveform()
```python
def plot_waveform(self, time_data: np.ndarray, amplitude_data: List[np.ndarray]) -> None
```
波形をプロットします。

**例:**
```python
from pypsgemu.debug.waveform_viewer import create_waveform_viewer

viewer = create_waveform_viewer(device)
viewer.start()
```

### EnvelopeViewer

エンベロープ表示ビューア。

#### メソッド

##### plot_envelope()
```python
def plot_envelope(self, shape: int, period: int = 256) -> None
```
エンベロープをプロットします。

##### show_shape()
```python
def show_shape(self, shape: int) -> None
```
エンベロープ形状を表示します。

**例:**
```python
from pypsgemu.debug.envelope_viewer import create_envelope_viewer

viewer = create_envelope_viewer(device)
viewer.plot_envelope(shape=13, period=1000)  # Attack-Hold
```

### LFSRVisualizer

LFSR状態ビジュアライザ。

**例:**
```python
from pypsgemu.debug.visualizer import create_lfsr_visualizer

visualizer = create_lfsr_visualizer(device)
visualizer.run()
```

---

## ユーティリティAPI

### StateManager

状態スナップショット管理。

#### コンストラクタ

```python
def __init__(self, base_directory: str = "states")
```

#### メソッド

##### create_snapshot()
```python
def create_snapshot(self, device: Device, name: str, description: str = "") -> StateSnapshot
```
デバイス状態のスナップショットを作成します。

##### restore_snapshot()
```python
def restore_snapshot(self, device: Device, name: str) -> None
```
スナップショットを復元します。

##### create_patch()
```python
def create_patch(self, name: str, register_changes: Dict[int, int], description: str = "") -> StatePatch
```
レジスタ変更パッチを作成します。

##### apply_patch()
```python
def apply_patch(self, device: Device, patch_name: str) -> None
```
パッチを適用します。

**例:**
```python
from pypsgemu.utils.state_manager import create_state_manager

manager = create_state_manager()

# スナップショット作成
snapshot = manager.create_snapshot(device, "test_state", "Test configuration")

# パッチ作成・適用
patch = manager.create_patch("volume_up", {8: 0x0F, 9: 0x0F, 10: 0x0F})
manager.apply_patch(device, "volume_up")

# 状態復元
manager.restore_snapshot(device, "test_state")
```

---

## エラーハンドリング

### 例外クラス階層

```
AY38910Error (基底例外)
├── RegisterAccessError (レジスタアクセスエラー)
├── InvalidValueError (無効な値エラー)
├── AudioBufferError (音声バッファエラー)
├── AudioDriverError (音声ドライバエラー)
├── StateManagerError (状態管理エラー)
├── WaveformViewerError (波形ビューアエラー)
├── EnvelopeViewerError (エンベロープビューアエラー)
└── LFSRVisualizerError (LFSRビジュアライザエラー)
```

### エラーハンドリングの例

```python
from pypsgemu.core.types import AY38910Error, RegisterAccessError

try:
    device.write_register(16, 0x12)  # 無効なアドレス
except RegisterAccessError as e:
    print(f"Register access error: {e}")
except AY38910Error as e:
    print(f"General AY38910 error: {e}")
```

---

## 使用例

### 基本的な音声生成

```python
from pypsgemu.core.ay38910 import create_ay38910_core
from pypsgemu.core.device_config import create_default_config
from pypsgemu.audio.driver import AudioDriver
from pypsgemu.audio.sample_generator import SampleGenerator

# デバイス作成
config = create_default_config()
device = create_ay38910_core(config)

# 440Hz (A音) を設定
device.write_register(0, 0xFE)  # Tone A Fine
device.write_register(1, 0x00)  # Tone A Coarse
device.write_register(8, 0x0F)  # Volume A

# 音声出力開始
generator = SampleGenerator(device, config)
driver = AudioDriver(generator, config)
driver.start()

# 5秒間再生
import time
time.sleep(5)

driver.stop()
```

### エンベロープ使用例

```python
# エンベロープ設定
device.write_register(11, 0x00)  # Envelope Fine (低速)
device.write_register(12, 0x10)  # Envelope Coarse
device.write_register(13, 0x0D)  # Envelope Shape (Attack-Hold)

# チャンネルAでエンベロープ使用
device.write_register(8, 0x10)   # Volume A (エンベロープモード)
```

### デバッグUI使用例

```python
from pypsgemu.debug.ui import launch_debug_ui

# デバッグUIを起動
launch_debug_ui(device)
```

### 状態管理使用例

```python
from pypsgemu.utils.state_manager import create_state_manager

manager = create_state_manager()

# 現在の状態を保存
snapshot = manager.create_snapshot(device, "my_config")
filepath = manager.save_snapshot_to_file("my_config", "my_config.json")

# 後で復元
manager.load_snapshot_from_file("my_config.json")
manager.restore_snapshot(device, "my_config")
```

---

## パフォーマンス考慮事項

### 最適化のヒント

1. **バッチ処理の活用**
   ```python
   # 効率的：バッチでtick実行
   device.tick(1000)
   
   # 非効率：個別にtick実行
   for _ in range(1000):
       device.tick(1)
   ```

2. **パフォーマンス最適化の適用**
   ```python
   device.optimize_for_performance()
   ```

3. **適切なバッファサイズの設定**
   ```python
   buffer = AudioBuffer(size=1024)  # 適切なサイズ
   optimal_size = buffer.optimize_buffer_size(50.0, 44100)  # 50ms遅延
   ```

### パフォーマンス監視

```python
# パフォーマンス統計の取得
stats = device.get_performance_stats()
print(f"CPU効率: {stats['cpu_efficiency']:.2f}")
print(f"メモリ使用量: {stats['memory_usage_bytes'] / 1024:.1f} KB")
```

---

## バージョン情報

- **API Version**: 1.0.0
- **Compatible Python**: 3.8+
- **Dependencies**: numpy, matplotlib, tkinter, sounddevice

## 関連ドキュメント

- [ユーザーガイド](user_guide.md)
- [実装仕様書](specification/ay-3-8910-detailed-design-specification.md)
- [アーキテクチャ仕様書](specification/ay-3-8910-software-architecture-specification.md)
