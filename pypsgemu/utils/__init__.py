"""
PyPSGEmu ユーティリティ層

このモジュールは、AY-3-8910エミュレータで使用される
ユーティリティクラスと関数を提供します。
"""

from .volume_table import (
    # VolumeTableクラス
    VolumeTable,
    
    # ファクトリ関数
    create_mame_volume_table,
    create_linear_volume_table,
    create_custom_volume_table,
    create_exponential_volume_table,
)

from .lfsr import (
    # LFSRクラス
    LFSR,
    
    # ユーティリティ関数
    create_default_lfsr,
    create_lfsr_with_seed,
    test_lfsr_period,
    generate_noise_sequence,
)

# バージョン情報
__version__ = "0.1.0"

# パブリックAPI
__all__ = [
    # VolumeTableクラス
    "VolumeTable",
    
    # VolumeTable ファクトリ関数
    "create_mame_volume_table",
    "create_linear_volume_table", 
    "create_custom_volume_table",
    "create_exponential_volume_table",
    
    # LFSRクラス
    "LFSR",
    
    # LFSR ユーティリティ関数
    "create_default_lfsr",
    "create_lfsr_with_seed",
    "test_lfsr_period",
    "generate_noise_sequence",
]
