"""
AY-3-8910 PSG エミュレータ - 基本型定義とエラークラス

このモジュールは、AY-3-8910エミュレータの基本的な型定義、
データクラス、およびエラークラスを提供します。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod


# =============================================================================
# エラークラス定義
# =============================================================================

class AY38910Error(Exception):
    """AY-3-8910エミュレータ基本例外"""
    pass


class RegisterAccessError(AY38910Error):
    """レジスタアクセスエラー
    
    無効なレジスタアドレスへのアクセス時に発生
    """
    pass


class InvalidValueError(AY38910Error):
    """無効な値エラー
    
    レジスタに無効な値を設定しようとした時に発生
    """
    pass


class AudioDriverError(AY38910Error):
    """音声ドライバエラー
    
    音声出力システムでエラーが発生した時に発生
    """
    pass


# =============================================================================
# 状態管理データクラス
# =============================================================================

@dataclass
class AY38910State:
    """AY-3-8910内部状態
    
    AY-3-8910チップの完全な内部状態を表現するデータクラス。
    エミュレータの状態保存・復元、デバッグ、テストに使用される。
    
    Attributes:
        registers: R0-R15の16個のレジスタ値 (0-255)
        selected_register: 現在選択されているレジスタ番号 (0-15)
        master_clock_counter: マスタークロックカウンタ
        tone_counters: 3チャンネルのトーンカウンタ (12ビット)
        noise_counter: ノイズジェネレータカウンタ (5ビット)
        envelope_counter: エンベロープカウンタ (16ビット)
        tone_outputs: 3チャンネルのトーン出力状態
        noise_output: ノイズ出力状態
        envelope_level: 現在のエンベロープレベル (AYUMI準拠: 0-31)
        lfsr_value: 17ビットLFSRの現在値
        envelope_holding: エンベロープホールド状態
        envelope_attacking: エンベロープアタック方向
        envelope_alternating: エンベロープ交互動作
        envelope_continuing: エンベロープ継続動作
    """
    # レジスタ状態
    registers: List[int] = field(default_factory=lambda: [0] * 16)
    selected_register: int = 0
    
    # 内部カウンタ
    master_clock_counter: int = 0
    tone_counters: List[int] = field(default_factory=lambda: [0] * 3)
    noise_counter: int = 0
    envelope_counter: int = 0
    
    # ジェネレータ状態
    tone_outputs: List[bool] = field(default_factory=lambda: [False] * 3)
    noise_output: bool = False
    envelope_level: int = 31  # 初期値は最大音量（AYUMI準拠）
    
    # LFSR状態 (17ビット、初期値は全ビット1)
    lfsr_value: int = 0x1FFFF
    
    # エンベロープ状態
    envelope_holding: bool = False
    envelope_attacking: bool = False
    envelope_alternating: bool = False
    envelope_continuing: bool = False
    
    def __post_init__(self):
        """初期化後の検証"""
        # レジスタ値の範囲チェック
        for i, reg_val in enumerate(self.registers):
            if not (0 <= reg_val <= 255):
                raise InvalidValueError(f"Register R{i} value {reg_val} out of range [0, 255]")
        
        # 選択レジスタの範囲チェック
        if not (0 <= self.selected_register <= 15):
            raise InvalidValueError(f"Selected register {self.selected_register} out of range [0, 15]")
        
        # トーンカウンタの範囲チェック (12ビット)
        for i, counter in enumerate(self.tone_counters):
            if not (0 <= counter <= 0xFFF):
                raise InvalidValueError(f"Tone counter {i} value {counter} out of range [0, 4095]")
        
        # ノイズカウンタの範囲チェック (5ビット)
        if not (0 <= self.noise_counter <= 0x1F):
            raise InvalidValueError(f"Noise counter {self.noise_counter} out of range [0, 31]")
        
        # エンベロープカウンタの範囲チェック (16ビット)
        if not (0 <= self.envelope_counter <= 0xFFFF):
            raise InvalidValueError(f"Envelope counter {self.envelope_counter} out of range [0, 65535]")
        
        # エンベロープレベルの範囲チェック (AYUMI準拠: 0-31)
        if not (0 <= self.envelope_level <= 31):
            raise InvalidValueError(f"Envelope level {self.envelope_level} out of range [0, 31]")
        
        # LFSR値の範囲チェック (17ビット)
        if not (0 <= self.lfsr_value <= 0x1FFFF):
            raise InvalidValueError(f"LFSR value {self.lfsr_value} out of range [0, 131071]")
    
    def copy(self) -> 'AY38910State':
        """状態の深いコピーを作成"""
        return AY38910State(
            registers=self.registers.copy(),
            selected_register=self.selected_register,
            master_clock_counter=self.master_clock_counter,
            tone_counters=self.tone_counters.copy(),
            noise_counter=self.noise_counter,
            envelope_counter=self.envelope_counter,
            tone_outputs=self.tone_outputs.copy(),
            noise_output=self.noise_output,
            envelope_level=self.envelope_level,
            lfsr_value=self.lfsr_value,
            envelope_holding=self.envelope_holding,
            envelope_attacking=self.envelope_attacking,
            envelope_alternating=self.envelope_alternating,
            envelope_continuing=self.envelope_continuing
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式にシリアライズ"""
        return {
            'registers': self.registers.copy(),
            'selected_register': self.selected_register,
            'master_clock_counter': self.master_clock_counter,
            'tone_counters': self.tone_counters.copy(),
            'noise_counter': self.noise_counter,
            'envelope_counter': self.envelope_counter,
            'tone_outputs': self.tone_outputs.copy(),
            'noise_output': self.noise_output,
            'envelope_level': self.envelope_level,
            'lfsr_value': self.lfsr_value,
            'envelope_holding': self.envelope_holding,
            'envelope_attacking': self.envelope_attacking,
            'envelope_alternating': self.envelope_alternating,
            'envelope_continuing': self.envelope_continuing
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AY38910State':
        """辞書からデシリアライズ"""
        return cls(**data)


# =============================================================================
# 抽象基底クラス
# =============================================================================

class Device(ABC):
    """デバイス抽象基底クラス"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """デバイス名"""
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """デバイスリセット"""
        pass
    
    @abstractmethod
    def tick(self, master_cycles: int) -> int:
        """Tick駆動実行"""
        pass


class AudioDevice(ABC):
    """音声デバイス抽象基底クラス"""
    
    @abstractmethod
    def get_mixed_output(self) -> float:
        """ミックス済み音声出力を取得"""
        pass
    
    @abstractmethod
    def set_sample_rate(self, sample_rate: int) -> None:
        """サンプルレートを設定"""
        pass


# =============================================================================
# 定数定義
# =============================================================================

# レジスタ定数
NUM_REGISTERS = 16
NUM_TONE_CHANNELS = 3
MAX_REGISTER_VALUE = 255
MAX_TONE_PERIOD = 0xFFF  # 12ビット
MAX_NOISE_PERIOD = 0x1F  # 5ビット
MAX_ENVELOPE_PERIOD = 0xFFFF  # 16ビット
MAX_VOLUME_LEVEL = 15  # 4ビット
LFSR_INITIAL_VALUE = 0x1FFFF  # 17ビット全て1

# レジスタアドレス定数
REG_TONE_A_FINE = 0
REG_TONE_A_COARSE = 1
REG_TONE_B_FINE = 2
REG_TONE_B_COARSE = 3
REG_TONE_C_FINE = 4
REG_TONE_C_COARSE = 5
REG_NOISE_PERIOD = 6
REG_MIXER_CONTROL = 7
REG_VOLUME_A = 8
REG_VOLUME_B = 9
REG_VOLUME_C = 10
REG_ENVELOPE_FINE = 11
REG_ENVELOPE_COARSE = 12
REG_ENVELOPE_SHAPE = 13
REG_IO_PORT_A = 14
REG_IO_PORT_B = 15

# ミキサー制御ビット定数
MIXER_TONE_A = 0x01
MIXER_TONE_B = 0x02
MIXER_TONE_C = 0x04
MIXER_NOISE_A = 0x08
MIXER_NOISE_B = 0x10
MIXER_NOISE_C = 0x20
MIXER_IO_A = 0x40
MIXER_IO_B = 0x80

# 音量制御ビット定数
VOLUME_ENVELOPE_MODE = 0x10  # ビット4: エンベロープモード

# エンベロープ形状ビット定数
ENVELOPE_HOLD = 0x01
ENVELOPE_ALTERNATE = 0x02
ENVELOPE_ATTACK = 0x04
ENVELOPE_CONTINUE = 0x08
