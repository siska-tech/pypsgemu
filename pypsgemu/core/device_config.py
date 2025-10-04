"""
AY-3-8910 PSG エミュレータ - デバイス設定

このモジュールは、AY-3-8910エミュレータのデバイス設定クラスを提供します。
クロック周波数、サンプルレート、デバッグ設定などを管理します。
"""

from dataclasses import dataclass, field
from typing import List, Optional
from .types import Device, InvalidValueError


@dataclass
class AY38910Config:
    """AY-3-8910設定クラス
    
    AY-3-8910エミュレータの動作パラメータを定義します。
    
    Attributes:
        device_id: デバイス識別子
        clock_frequency: マスタークロック周波数 (Hz)
        sample_rate: 音声サンプルレート (Hz)
        channels: 音声チャンネル数 (通常は1: モノラル)
        dtype: 音声データ型 ('float32', 'int16', etc.)
        buffer_size: 音声バッファサイズ (サンプル数)
        enable_debug: デバッグモード有効化
        enable_visualization: 可視化機能有効化
        breakpoint_registers: ブレークポイント対象レジスタリスト
        volume_scale: 全体音量スケール (0.0-1.0)
        enable_envelope: エンベロープジェネレータ有効化
        enable_noise: ノイズジェネレータ有効化
        mame_compatibility: MAME互換モード
    """
    
    # 基本設定
    device_id: str = "ay38910"
    clock_frequency: float = 2000000.0  # 2MHz (標準的な値)
    
    # 音声設定
    sample_rate: int = 44100  # 44.1kHz
    channels: int = 1  # モノラル
    dtype: str = 'float32'
    buffer_size: int = 1024  # サンプル数
    
    # エミュレーション設定
    enable_debug: bool = False
    enable_visualization: bool = False
    breakpoint_registers: List[int] = field(default_factory=list)
    
    # 音声処理設定
    volume_scale: float = 1.0  # 全体音量 (0.0-1.0)
    
    # 機能有効化設定
    enable_envelope: bool = True
    enable_noise: bool = True
    
    # 互換性設定
    mame_compatibility: bool = True  # MAME準拠の動作
    
    def __post_init__(self):
        """初期化後の検証"""
        # クロック周波数の検証
        if self.clock_frequency <= 0:
            raise InvalidValueError(f"Clock frequency must be positive, got {self.clock_frequency}")
        
        if self.clock_frequency > 10000000:  # 10MHz上限
            raise InvalidValueError(f"Clock frequency too high: {self.clock_frequency} Hz")
        
        # サンプルレートの検証
        if self.sample_rate <= 0:
            raise InvalidValueError(f"Sample rate must be positive, got {self.sample_rate}")
        
        if self.sample_rate > 192000:  # 192kHz上限
            raise InvalidValueError(f"Sample rate too high: {self.sample_rate} Hz")
        
        # チャンネル数の検証
        if self.channels not in [1, 2]:
            raise InvalidValueError(f"Channels must be 1 or 2, got {self.channels}")
        
        # データ型の検証
        valid_dtypes = ['float32', 'float64', 'int16', 'int32']
        if self.dtype not in valid_dtypes:
            raise InvalidValueError(f"Invalid dtype '{self.dtype}', must be one of {valid_dtypes}")
        
        # バッファサイズの検証
        if self.buffer_size <= 0 or self.buffer_size > 8192:
            raise InvalidValueError(f"Buffer size must be in range [1, 8192], got {self.buffer_size}")
        
        # 音量スケールの検証
        if not (0.0 <= self.volume_scale <= 1.0):
            raise InvalidValueError(f"Volume scale must be in range [0.0, 1.0], got {self.volume_scale}")
        
        # ブレークポイントレジスタの検証
        for reg in self.breakpoint_registers:
            if not (0 <= reg <= 15):
                raise InvalidValueError(f"Breakpoint register {reg} out of range [0, 15]")
    
    @property
    def clock_divisor(self) -> int:
        """クロック分周比を計算
        
        AY-3-8910内部では、マスタークロックを16で分周した周波数で動作します。
        
        Returns:
            クロック分周比 (通常は16)
        """
        return 16
    
    @property
    def effective_clock_frequency(self) -> float:
        """実効クロック周波数を計算
        
        Returns:
            実効クロック周波数 (Hz)
        """
        return self.clock_frequency / self.clock_divisor
    
    @property
    def samples_per_tick(self) -> float:
        """1ティックあたりのサンプル数を計算
        
        Returns:
            1ティックあたりのサンプル数
        """
        return self.sample_rate / self.effective_clock_frequency
    
    def validate_register_address(self, address: int) -> None:
        """レジスタアドレスの妥当性を検証
        
        Args:
            address: レジスタアドレス
            
        Raises:
            InvalidValueError: 無効なアドレスの場合
        """
        if not (0 <= address <= 15):
            raise InvalidValueError(f"Register address {address} out of range [0, 15]")
    
    def validate_register_value(self, value: int) -> None:
        """レジスタ値の妥当性を検証
        
        Args:
            value: レジスタ値
            
        Raises:
            InvalidValueError: 無効な値の場合
        """
        if not (0 <= value <= 255):
            raise InvalidValueError(f"Register value {value} out of range [0, 255]")
    
    def copy(self) -> 'AY38910Config':
        """設定の深いコピーを作成
        
        Returns:
            コピーされた設定オブジェクト
        """
        return AY38910Config(
            device_id=self.device_id,
            clock_frequency=self.clock_frequency,
            sample_rate=self.sample_rate,
            channels=self.channels,
            dtype=self.dtype,
            buffer_size=self.buffer_size,
            enable_debug=self.enable_debug,
            enable_visualization=self.enable_visualization,
            breakpoint_registers=self.breakpoint_registers.copy(),
            volume_scale=self.volume_scale,
            enable_envelope=self.enable_envelope,
            enable_noise=self.enable_noise,
            mame_compatibility=self.mame_compatibility
        )
    
    def __str__(self) -> str:
        """文字列表現"""
        return (f"AY38910Config("
                f"clock={self.clock_frequency/1000000:.1f}MHz, "
                f"sample_rate={self.sample_rate}Hz, "
                f"channels={self.channels}, "
                f"dtype={self.dtype}, "
                f"debug={self.enable_debug})")


# =============================================================================
# プリセット設定
# =============================================================================

def create_default_config() -> AY38910Config:
    """デフォルト設定を作成
    
    Returns:
        デフォルト設定オブジェクト
    """
    return AY38910Config()


def create_high_quality_config() -> AY38910Config:
    """高品質設定を作成
    
    Returns:
        高品質設定オブジェクト (96kHz, float64)
    """
    return AY38910Config(
        sample_rate=96000,
        dtype='float64',
        buffer_size=2048
    )


def create_low_latency_config() -> AY38910Config:
    """低遅延設定を作成
    
    Returns:
        低遅延設定オブジェクト (小さなバッファサイズ)
    """
    return AY38910Config(
        buffer_size=256,
        sample_rate=48000
    )


def create_debug_config() -> AY38910Config:
    """デバッグ設定を作成
    
    Returns:
        デバッグ設定オブジェクト (デバッグ機能有効)
    """
    return AY38910Config(
        enable_debug=True,
        enable_visualization=True,
        breakpoint_registers=list(range(16))  # 全レジスタにブレークポイント
    )


def create_msx_config() -> AY38910Config:
    """MSX互換設定を作成
    
    MSXコンピュータで使用される典型的な設定
    
    Returns:
        MSX互換設定オブジェクト
    """
    return AY38910Config(
        clock_frequency=1789773.0,  # MSXのPSGクロック
        sample_rate=44100,
        mame_compatibility=True
    )


def create_amstrad_cpc_config() -> AY38910Config:
    """Amstrad CPC互換設定を作成
    
    Amstrad CPCで使用される典型的な設定
    
    Returns:
        Amstrad CPC互換設定オブジェクト
    """
    return AY38910Config(
        clock_frequency=1000000.0,  # 1MHz
        sample_rate=44100,
        mame_compatibility=True
    )
