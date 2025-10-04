"""
AY-3-8910 PSG エミュレータ - コア層

このモジュールは、AY-3-8910エミュレータのコア機能を提供します。
基本型定義、設定クラス、およびエミュレータコアを含みます。
"""

from .types import (
    # エラークラス
    AY38910Error,
    RegisterAccessError,
    InvalidValueError,
    AudioDriverError,
    
    # 状態クラス
    AY38910State,
    
    # 抽象基底クラス
    Device,
    AudioDevice,
    
    # 定数
    NUM_REGISTERS,
    NUM_TONE_CHANNELS,
    MAX_REGISTER_VALUE,
    MAX_TONE_PERIOD,
    MAX_NOISE_PERIOD,
    MAX_ENVELOPE_PERIOD,
    MAX_VOLUME_LEVEL,
    LFSR_INITIAL_VALUE,
    
    # レジスタアドレス定数
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
    REG_IO_PORT_A,
    REG_IO_PORT_B,
    
    # ミキサー制御ビット定数
    MIXER_TONE_A,
    MIXER_TONE_B,
    MIXER_TONE_C,
    MIXER_NOISE_A,
    MIXER_NOISE_B,
    MIXER_NOISE_C,
    MIXER_IO_A,
    MIXER_IO_B,
    
    # 音量制御ビット定数
    VOLUME_ENVELOPE_MODE,
    
    # エンベロープ形状ビット定数
    ENVELOPE_HOLD,
    ENVELOPE_ALTERNATE,
    ENVELOPE_ATTACK,
    ENVELOPE_CONTINUE,
)

from .device_config import (
    # 設定クラス
    AY38910Config,
    
    # プリセット設定関数
    create_default_config,
    create_high_quality_config,
    create_low_latency_config,
    create_debug_config,
    create_msx_config,
    create_amstrad_cpc_config,
)

from .tone_generator import (
    # トーンジェネレータクラス
    ToneGenerator,
    
    # ユーティリティ関数
    create_tone_generator,
    calculate_period_from_registers,
    calculate_registers_from_period,
)

from .noise_generator import (
    # ノイズジェネレータクラス
    NoiseGenerator,
    
    # ユーティリティ関数
    create_noise_generator,
    calculate_noise_period_from_register,
    test_lfsr_randomness,
)

from .envelope_generator import (
    # エンベロープジェネレータクラス
    EnvelopeGenerator,
    
    # ユーティリティ関数
    create_envelope_generator,
    calculate_envelope_period_from_registers,
    calculate_registers_from_envelope_period,
    get_all_envelope_shapes,
)

from .mixer import (
    # ミキサークラス
    Mixer,
    
    # ユーティリティ関数
    create_mixer,
    test_mixer_logic,
)

from .ay38910 import (
    # コアエミュレータクラス
    AY38910Core,
    
    # ファクトリ関数
    create_ay38910_core,
    create_debug_core,
)

# バージョン情報
__version__ = "0.1.0"

# パブリックAPI
__all__ = [
    # エラークラス
    "AY38910Error",
    "RegisterAccessError", 
    "InvalidValueError",
    "AudioDriverError",
    
    # 状態クラス
    "AY38910State",
    
    # 設定クラス
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
    
    # 定数
    "NUM_REGISTERS",
    "NUM_TONE_CHANNELS",
    "MAX_REGISTER_VALUE",
    "MAX_TONE_PERIOD",
    "MAX_NOISE_PERIOD", 
    "MAX_ENVELOPE_PERIOD",
    "MAX_VOLUME_LEVEL",
    "LFSR_INITIAL_VALUE",
    
    # レジスタアドレス定数
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
    "REG_IO_PORT_A",
    "REG_IO_PORT_B",
    
    # ミキサー制御ビット定数
    "MIXER_TONE_A",
    "MIXER_TONE_B",
    "MIXER_TONE_C",
    "MIXER_NOISE_A",
    "MIXER_NOISE_B",
    "MIXER_NOISE_C",
    "MIXER_IO_A",
    "MIXER_IO_B",
    
    # 音量制御ビット定数
    "VOLUME_ENVELOPE_MODE",
    
    # エンベロープ形状ビット定数
    "ENVELOPE_HOLD",
    "ENVELOPE_ALTERNATE",
    "ENVELOPE_ATTACK",
    "ENVELOPE_CONTINUE",
    
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
    
    # ミキサーファクトリ関数
    "create_mixer",
    
    # コアエミュレータファクトリ関数
    "create_ay38910_core",
    "create_debug_core",
    
    # ユーティリティ関数
    "calculate_period_from_registers",
    "calculate_registers_from_period",
    "calculate_noise_period_from_register",
    "calculate_envelope_period_from_registers",
    "calculate_registers_from_envelope_period",
    "get_all_envelope_shapes",
    "test_lfsr_randomness",
    "test_mixer_logic",
]
