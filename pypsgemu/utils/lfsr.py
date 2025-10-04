"""
AY-3-8910 PSG エミュレータ - 線形帰還シフトレジスタ (LFSR)

このモジュールは、AY-3-8910のノイズジェネレータで使用される
17ビットLFSRの実装を提供します。
フィードバック多項式: x^17 + x^14 + 1 (AYUMI準拠)
"""

from typing import Optional
from ..core.types import InvalidValueError


class LFSR:
    """17ビット線形帰還シフトレジスタ
    
    AY-3-8910のノイズジェネレータで使用される17ビットLFSRを実装します。
    フィードバック多項式は x^17 + x^14 + 1 で、これはビット0とビット14のXORに対応します。
    AYUMI実装に準拠した正確な多項式を使用します。
    
    Attributes:
        _value: 現在のLFSR値 (17ビット)
        _initial_value: 初期値
        _cycle_count: 更新回数
    """
    
    # 17ビットLFSRの初期値（AYUMI準拠）
    # AYUMIでは初期値1を使用
    INITIAL_VALUE = 1  # AYUMI準拠の初期値
    
    # 17ビットマスク
    MASK_17BIT = 0x1FFFF
    
    # フィードバックタップ位置（AYUMI準拠）
    FEEDBACK_TAP_0 = 0   # ビット0
    FEEDBACK_TAP_14 = 14 # ビット14
    
    def __init__(self, initial_value: Optional[int] = None):
        """LFSRを初期化
        
        Args:
            initial_value: 初期値 (Noneの場合はデフォルト値0x12345を使用)
            
        Raises:
            InvalidValueError: 初期値が無効な場合
        """
        if initial_value is None:
            initial_value = self.INITIAL_VALUE
        
        if not (0 <= initial_value <= self.MASK_17BIT):
            raise InvalidValueError(f"LFSR initial value {initial_value} out of range [0, {self.MASK_17BIT}]")
        
        if initial_value == 0:
            raise InvalidValueError("LFSR initial value cannot be 0 (would lock up)")
        
        self._initial_value = initial_value
        self._value = initial_value
        self._cycle_count = 0
    
    def step(self) -> bool:
        """LFSRを1ステップ進める
        
        フィードバック多項式 x^17 + x^14 + 1 に基づいて、
        フィボナッチ型LFSRとして実装します。
        AYUMI実装に準拠した正確な多項式を使用します。
        
        Returns:
            更新後のビット0の値
        """
        # フィードバックビットを計算: bit(0) XOR bit(14)
        # ビット0（最下位ビット）とビット14をXOR
        bit_0 = self._value & 1
        bit_14 = (self._value >> 14) & 1
        feedback_bit = bit_0 ^ bit_14
        
        # 右シフトして新しいビットを最上位に挿入
        self._value = (self._value >> 1) | (feedback_bit << 16)
        
        # 17ビットマスクを適用
        self._value &= self.MASK_17BIT
        
        # サイクルカウントを更新
        self._cycle_count += 1
        
        # 新しいビット0を返す
        return bool(self._value & 1)
    
    def get_output(self) -> bool:
        """現在の出力ビット（ビット0）を取得
        
        AY-3-8910の仕様では、ノイズ出力はLFSRのビット0を使用します。
        
        Returns:
            現在のビット0の値
        """
        return bool(self._value & 1)
    
    def get_value(self) -> int:
        """現在のLFSR値を取得
        
        Returns:
            現在の17ビットLFSR値
        """
        return self._value
    
    def set_value(self, value: int) -> None:
        """LFSR値を設定
        
        Args:
            value: 新しいLFSR値
            
        Raises:
            InvalidValueError: 値が無効な場合
        """
        if not (0 <= value <= self.MASK_17BIT):
            raise InvalidValueError(f"LFSR value {value} out of range [0, {self.MASK_17BIT}]")
        
        if value == 0:
            raise InvalidValueError("LFSR value cannot be 0 (would lock up)")
        
        self._value = value
    
    def reset(self, new_initial_value: Optional[int] = None) -> None:
        """LFSRをリセット
        
        Args:
            new_initial_value: 新しい初期値 (Noneの場合は元の初期値を使用)
        """
        if new_initial_value is not None:
            if not (0 < new_initial_value <= self.MASK_17BIT):
                raise InvalidValueError(f"LFSR initial value {new_initial_value} out of range [1, {self.MASK_17BIT}]")
            self._initial_value = new_initial_value
        
        self._value = self._initial_value
        self._cycle_count = 0
    
    def get_cycle_count(self) -> int:
        """更新回数を取得
        
        Returns:
            step()が呼ばれた回数
        """
        return self._cycle_count
    
    def get_period_length(self) -> int:
        """LFSRの周期長を取得
        
        17ビットLFSRの最大周期長は 2^17 - 1 = 131071 です。
        
        Returns:
            理論上の最大周期長
        """
        return (1 << 17) - 1  # 2^17 - 1
    
    def is_at_initial_state(self) -> bool:
        """初期状態かどうかをチェック
        
        Returns:
            現在の値が初期値と同じ場合True
        """
        return self._value == self._initial_value and self._cycle_count > 0
    
    def get_bit(self, position: int) -> bool:
        """指定位置のビットを取得
        
        Args:
            position: ビット位置 (0-16)
            
        Returns:
            指定位置のビット値
            
        Raises:
            InvalidValueError: 位置が無効な場合
        """
        if not (0 <= position <= 16):
            raise InvalidValueError(f"Bit position {position} out of range [0, 16]")
        
        return bool((self._value >> position) & 1)
    
    def get_bits_as_string(self) -> str:
        """LFSR値をビット文字列として取得
        
        Returns:
            17ビットのビット文字列 (MSBが左端)
        """
        return format(self._value, '017b')
    
    def step_multiple(self, steps: int) -> bool:
        """複数ステップを一度に実行
        
        Args:
            steps: 実行するステップ数
            
        Returns:
            最後のステップ後のビット0の値
            
        Raises:
            InvalidValueError: ステップ数が負の場合
        """
        if steps < 0:
            raise InvalidValueError(f"Steps must be non-negative, got {steps}")
        
        output = self.get_output()
        for _ in range(steps):
            output = self.step()
        
        return output
    
    def predict_next_output(self) -> bool:
        """次のステップの出力を予測（状態は変更しない）
        
        Returns:
            次のステップでのビット0の値
        """
        # 現在の状態を保存
        saved_value = self._value
        saved_count = self._cycle_count
        
        # 1ステップ実行して結果を取得
        next_output = self.step()
        
        # 状態を復元
        self._value = saved_value
        self._cycle_count = saved_count
        
        return next_output
    
    def copy(self) -> 'LFSR':
        """LFSRの深いコピーを作成
        
        Returns:
            現在の状態をコピーした新しいLFSRインスタンス
        """
        new_lfsr = LFSR(self._initial_value)
        new_lfsr._value = self._value
        new_lfsr._cycle_count = self._cycle_count
        return new_lfsr
    
    def __str__(self) -> str:
        """文字列表現"""
        return f"LFSR(value=0x{self._value:05X}, cycle={self._cycle_count})"
    
    def __repr__(self) -> str:
        """詳細文字列表現"""
        return (f"LFSR(value=0x{self._value:05X}, "
                f"initial=0x{self._initial_value:05X}, "
                f"cycle={self._cycle_count}, "
                f"bits={self.get_bits_as_string()})")
    
    def __eq__(self, other) -> bool:
        """等価比較"""
        if not isinstance(other, LFSR):
            return False
        return (self._value == other._value and 
                self._initial_value == other._initial_value)


# =============================================================================
# ユーティリティ関数
# =============================================================================

def create_default_lfsr() -> LFSR:
    """デフォルトLFSRを作成
    
    Returns:
        初期値1のLFSRインスタンス（AYUMI準拠）
    """
    return LFSR()


def create_lfsr_with_seed(seed: int) -> LFSR:
    """指定されたシードでLFSRを作成
    
    Args:
        seed: シード値 (1-131071)
        
    Returns:
        指定されたシードのLFSRインスタンス
    """
    return LFSR(seed)


def test_lfsr_period(lfsr: LFSR, max_steps: int = 200000) -> int:
    """LFSRの実際の周期を測定（テスト用）
    
    Args:
        lfsr: テスト対象のLFSR
        max_steps: 最大測定ステップ数
        
    Returns:
        検出された周期長（max_stepsに達した場合は-1）
        
    Note:
        この関数はテスト・デバッグ用途のみに使用してください。
        実際の周期測定には時間がかかる場合があります。
    """
    initial_value = lfsr.get_value()
    lfsr.reset()
    
    for step in range(1, max_steps + 1):
        lfsr.step()
        if lfsr.get_value() == initial_value:
            return step
    
    return -1  # 周期が見つからなかった


def generate_noise_sequence(length: int, seed: Optional[int] = None) -> list[bool]:
    """ノイズシーケンスを生成
    
    Args:
        length: 生成するシーケンスの長さ
        seed: LFSRのシード値
        
    Returns:
        ノイズビットのリスト
    """
    lfsr = LFSR(seed) if seed is not None else create_default_lfsr()
    sequence = []
    
    for _ in range(length):
        sequence.append(lfsr.step())
    
    return sequence
