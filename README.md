# PyPSGEmu - AY-3-8910 PSG Emulator

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-orange.svg)](CHANGELOG.md)

PyPSGEmuは、AY-3-8910 Programmable Sound Generator (PSG) チップの高精度エミュレータです。リアルタイム音声生成、デバッグUI、波形可視化機能を提供し、レトロゲーム開発や音楽制作に最適です。

## 特徴

### 🎵 高精度エミュレーション
- AY-3-8910チップの完全な機能実装
- 3チャンネルトーンジェネレータ
- ノイズジェネレータ（17-bit LFSR）
- 16種類のエンベロープ形状
- リアルタイム音声出力

### 🛠️ 開発者向けツール
- **対話型デバッグUI** - リアルタイムレジスタ編集
- **波形ビューア** - オシロスコープ風表示
- **エンベロープビューア** - エンベロープ形状の可視化
- **LFSR可視化** - ノイズ生成アルゴリズムの表示
- **状態管理** - スナップショット保存・復元

### ⚡ パフォーマンス最適化
- バッチ処理による高速実行
- メモリ使用量の最適化
- 低レイテンシ音声バッファ
- パフォーマンス統計監視

## インストール

### 必要な環境
- Python 3.8以上
- NumPy
- Matplotlib
- Tkinter (通常Pythonに含まれています)
- SoundDevice

### pipでのインストール
```bash
pip install pypsgemu
```

### ソースからのインストール
```bash
git clone https://github.com/siska-tech/pypsgemu.git
cd pypsgemu
pip install -e .
```

## クイックスタート

### 基本的な音声生成

```python
from pypsgemu.core.ay38910 import create_ay38910_core
from pypsgemu.core.device_config import create_default_config
from pypsgemu.audio.driver import AudioDriver
from pypsgemu.audio.sample_generator import SampleGenerator
import time

# エミュレータを初期化
config = create_default_config()
device = create_ay38910_core(config)

# 440Hz (A音) を設定
device.write_register(0, 0xFE)  # Tone A Fine
device.write_register(1, 0x00)  # Tone A Coarse
device.write_register(8, 0x0F)  # Volume A (最大)

# 音声出力を開始
generator = SampleGenerator(device, config)
driver = AudioDriver(generator, config)
driver.start()

# 5秒間再生
time.sleep(5)
driver.stop()
```

### デバッグUIの起動

```python
from pypsgemu.debug.ui import create_debug_ui

# デバッグUIを開く
ui = create_debug_ui(device)
ui.run()
```

### コマンドラインから実行

```bash
# 基本的なエミュレータを起動
pypsgemu-cli

# デバッグUIを起動
pypsgemu-gui
```

## 主要機能

### レジスタ制御

AY-3-8910の16個のレジスタを直接制御できます：

```python
# トーンジェネレータの設定
device.write_register(0, fine_tune)    # R0: Tone A Fine
device.write_register(1, coarse_tune)  # R1: Tone A Coarse

# 音量設定
device.write_register(8, volume)       # R8: Volume A (0-15)

# エンベロープ設定
device.write_register(11, env_fine)    # R11: Envelope Fine
device.write_register(12, env_coarse)  # R12: Envelope Coarse
device.write_register(13, env_shape)   # R13: Envelope Shape
```

### エンベロープ使用例

```python
# Attack-Hold エンベロープを設定
device.write_register(11, 0x00)  # Envelope Fine (低速)
device.write_register(12, 0x10)  # Envelope Coarse
device.write_register(13, 0x0D)  # Envelope Shape (Attack-Hold)

# チャンネルAでエンベロープを使用
device.write_register(8, 0x10)   # Volume A (エンベロープモード)
```

### 状態管理

```python
from pypsgemu.utils.state_manager import create_state_manager

manager = create_state_manager()

# 現在の状態を保存
snapshot = manager.create_snapshot(device, "my_config", "My configuration")
manager.save_snapshot_to_file("my_config", "config.json")

# 状態を復元
manager.load_snapshot_from_file("config.json")
manager.restore_snapshot(device, "my_config")
```

## デバッグツール

### 波形ビューア
リアルタイムで3チャンネルの波形を表示：

```python
from pypsgemu.debug.waveform_viewer import create_waveform_viewer

viewer = create_waveform_viewer(device)
viewer.start()
```

### エンベロープビューア
16種類のエンベロープ形状を可視化：

```python
from pypsgemu.debug.envelope_viewer import create_envelope_viewer

viewer = create_envelope_viewer(device)
viewer.plot_envelope(shape=13, period=1000)  # Attack-Hold
```

### LFSR可視化
ノイズジェネレータの17-bit LFSRの状態を表示：

```python
from pypsgemu.debug.visualizer import create_lfsr_visualizer

visualizer = create_lfsr_visualizer(device)
visualizer.run()
```

## パフォーマンス最適化

### バッチ処理
```python
# 効率的：バッチでtick実行
device.tick(1000)

# 非効率：個別にtick実行
for _ in range(1000):
    device.tick(1)
```

### パフォーマンス最適化モード
```python
# デバッグ機能を無効化して最高性能を実現
device.optimize_for_performance()
```

### パフォーマンス監視
```python
stats = device.get_performance_stats()
print(f"平均tick時間: {stats['avg_tick_time']:.6f}秒")
print(f"メモリ使用量: {stats['memory_usage_bytes'] / 1024:.1f} KB")
print(f"CPU効率: {stats['cpu_efficiency']:.2f}")
```

## サンプルコード

`examples/` ディレクトリに以下のサンプルがあります：

- `basic_usage.py` - 基本的な使用方法
- `debug_demo.py` - デバッグ機能のデモ
- `audio_output.py` - 音声出力の例
- `register_control.py` - レジスタ制御の例

## API リファレンス

詳細なAPIドキュメントは [docs/api_reference.md](docs/api_reference.md) を参照してください。

## ユーザーガイド

包括的な使用方法は [docs/user_guide.md](docs/user_guide.md) を参照してください。

## アーキテクチャ

PyPSGEmuの内部構造と設計については以下のドキュメントを参照：

- [ソフトウェアアーキテクチャ仕様書](docs/specification/ay-3-8910-software-architecture-specification.md)
- [詳細設計仕様書](docs/specification/ay-3-8910-detailed-design-specification.md)

## 開発

### 開発環境のセットアップ

```bash
git clone https://github.com/siska-tech/pypsgemu.git
cd pypsgemu
pip install -e ".[dev]"
```

### テストの実行

```bash
# 全テストを実行
python -m pytest

# 特定のテストを実行
python -m pytest tests/unit/
python -m pytest tests/integration/
python -m pytest tests/performance/
```

### コードフォーマット

```bash
# Black でフォーマット
black pypsgemu/ tests/

# isort でインポートを整理
isort pypsgemu/ tests/

# flake8 でリント
flake8 pypsgemu/ tests/
```

## 貢献

プロジェクトへの貢献を歓迎します！以下の手順でお願いします：

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチをプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は [LICENSE](LICENSE) ファイルを参照してください。

## 変更履歴

変更履歴は [CHANGELOG.md](CHANGELOG.md) を参照してください。

## サポート

- **Issues**: [GitHub Issues](https://github.com/siska-tech/pypsgemu/issues)
- **Discussions**: [GitHub Discussions](https://github.com/siska-tech/pypsgemu/discussions)
- **Team**: [Siska-Tech](https://github.com/siska-tech)

## 謝辞

- AY-3-8910チップの仕様情報を提供してくださったコミュニティの皆様
- テストとフィードバックを提供してくださった開発者の皆様
- オープンソースライブラリの開発者の皆様

---

**PyPSGEmu** - レトロサウンドの魅力を現代に蘇らせる 🎵
