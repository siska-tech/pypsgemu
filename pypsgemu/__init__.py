"""
PyPSGEmu - AY-3-8910 PSG エミュレータ

Python実装のAY-3-8910 Programmable Sound Generator (PSG) エミュレータライブラリ。
リアルタイム音声出力、正確なハードウェアエミュレーション、
豊富なデバッグ機能を提供します。

主な機能:
- 完全なAY-3-8910ハードウェアエミュレーション
- 3チャンネルトーンジェネレータ
- 17ビットLFSRノイズジェネレータ  
- 10種類のエンベロープ形状
- リアルタイム音声出力
- 状態保存・復元
- デバッグ・可視化機能
- MSX、Amstrad CPC等の互換性

使用例:
    >>> from pypsgemu import AY38910Config, create_default_config
    >>> config = create_default_config()
    >>> print(config)
    AY38910Config(clock=2.0MHz, sample_rate=44100Hz, channels=1, dtype=float32, debug=False)

    >>> from pypsgemu.core import AY38910State
    >>> state = AY38910State()
    >>> state.registers[0] = 0x34  # チャンネルAトーン周期設定
"""

# バージョン情報
__version__ = "1.0.0"
__author__ = "PyPSGEmu Development Team"
__email__ = "pypsgemu@example.com"
__license__ = "MIT"
__url__ = "https://github.com/pypsgemu/pypsgemu"
__description__ = "AY-3-8910 PSG Emulator - Complete software emulation of the AY-3-8910 sound chip"

# バージョン情報辞書
VERSION_INFO = {
    'version': __version__,
    'author': __author__,
    'license': __license__,
    'url': __url__,
    'description': __description__
}

# コア機能のインポート
from .core import (
    # エラークラス
    AY38910Error,
    RegisterAccessError,
    InvalidValueError,
    AudioDriverError,
    
    # 状態・設定クラス
    AY38910State,
    AY38910Config,
    
    # 抽象基底クラス
    Device,
    AudioDevice,
    
    # ジェネレータクラス
    ToneGenerator,
    NoiseGenerator,
    EnvelopeGenerator,
    
    # ミキサークラス
    Mixer,
    
    # コアエミュレータクラス
    AY38910Core,
    
    # プリセット設定関数
    create_default_config,
    create_high_quality_config,
    create_low_latency_config,
    create_debug_config,
    create_msx_config,
    create_amstrad_cpc_config,
    
    # ジェネレータファクトリ関数
    create_tone_generator,
    create_noise_generator,
    create_envelope_generator,
    
    # コアエミュレータファクトリ関数
    create_ay38910_core,
    create_debug_core,
    
    # 重要な定数
    NUM_REGISTERS,
    NUM_TONE_CHANNELS,
    REG_TONE_A_FINE,
    REG_TONE_A_COARSE,
    REG_TONE_B_FINE,
    REG_TONE_B_COARSE,
    REG_TONE_C_FINE,
    REG_TONE_C_COARSE,
    REG_NOISE_PERIOD,
    REG_MIXER_CONTROL,
    REG_VOLUME_A,
    REG_VOLUME_B,
    REG_VOLUME_C,
    REG_ENVELOPE_FINE,
    REG_ENVELOPE_COARSE,
    REG_ENVELOPE_SHAPE,
)

# ユーティリティ機能のインポート
from .utils import (
    # ユーティリティクラス
    VolumeTable,
    LFSR,
    
    # ファクトリ関数
    create_mame_volume_table,
    create_default_lfsr,
)

# 音声出力機能のインポート (Phase1 Week4で実装完了)
from .audio import (
    # 音声クラス
    AudioDriver,
    AudioBuffer,
    SampleGenerator,
    StereoSampleGenerator,
    
    # ファクトリ関数
    create_audio_driver,
    create_simple_audio_system,
    create_advanced_audio_system,
    
    # ユーティリティ関数
    list_audio_devices,
    test_audio_system,
)

# パブリックAPI定義
__all__ = [
    # バージョン情報
    "__version__",
    "__author__",
    "__license__",
    "__description__",
    
    # エラークラス
    "AY38910Error",
    "RegisterAccessError",
    "InvalidValueError", 
    "AudioDriverError",
    
    # 状態・設定クラス
    "AY38910State",
    "AY38910Config",
    
    # 抽象基底クラス
    "Device",
    "AudioDevice",
    
    # ジェネレータクラス
    "ToneGenerator",
    "NoiseGenerator",
    "EnvelopeGenerator",
    
    # ミキサークラス
    "Mixer",
    
    # コアエミュレータクラス
    "AY38910Core",
    
    # ユーティリティクラス
    "VolumeTable",
    "LFSR",
    
    # プリセット設定関数
    "create_default_config",
    "create_high_quality_config",
    "create_low_latency_config",
    "create_debug_config",
    "create_msx_config",
    "create_amstrad_cpc_config",
    
    # ジェネレータファクトリ関数
    "create_tone_generator",
    "create_noise_generator",
    "create_envelope_generator",
    
    # コアエミュレータファクトリ関数
    "create_ay38910_core",
    "create_debug_core",
    
    # ユーティリティファクトリ関数
    "create_mame_volume_table",
    "create_default_lfsr",
    
    # 音声出力クラス
    "AudioDriver",
    "AudioBuffer", 
    "SampleGenerator",
    "StereoSampleGenerator",
    
    # 音声出力ファクトリ関数
    "create_audio_driver",
    "create_simple_audio_system",
    "create_advanced_audio_system",
    
    # 音声ユーティリティ関数
    "list_audio_devices",
    "test_audio_system",
    
    # 重要な定数
    "NUM_REGISTERS",
    "NUM_TONE_CHANNELS",
    "REG_TONE_A_FINE",
    "REG_TONE_A_COARSE",
    "REG_TONE_B_FINE",
    "REG_TONE_B_COARSE",
    "REG_TONE_C_FINE",
    "REG_TONE_C_COARSE",
    "REG_NOISE_PERIOD",
    "REG_MIXER_CONTROL",
    "REG_VOLUME_A",
    "REG_VOLUME_B",
    "REG_VOLUME_C",
    "REG_ENVELOPE_FINE",
    "REG_ENVELOPE_COARSE",
    "REG_ENVELOPE_SHAPE",
]


def get_version_info() -> dict:
    """バージョン情報を取得
    
    Returns:
        バージョン情報辞書
    """
    return {
        "version": __version__,
        "author": __author__,
        "license": __license__,
        "description": __description__
    }


def create_emulator(config: AY38910Config = None) -> AY38910Core:
    """エミュレータインスタンスを作成
    
    Args:
        config: エミュレータ設定 (Noneの場合はデフォルト設定)
        
    Returns:
        AY38910エミュレータインスタンス
    """
    return create_ay38910_core(config)


# ライブラリ初期化時のメッセージ (デバッグモードでのみ表示)
import os
if os.environ.get('PYPSGEMU_DEBUG'):
    print(f"PyPSGEmu v{__version__} - AY-3-8910 PSG Emulator")
    print(f"Author: {__author__}")
    print(f"License: {__license__}")
