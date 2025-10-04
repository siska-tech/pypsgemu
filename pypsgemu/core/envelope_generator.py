"""
AY-3-8910 PSG エミュレータ - エンベロープジェネレータ

このモジュールは、AY-3-8910のエンベロープジェネレータを実装します。
16種類のエンベロープ形状をサポートし、16ビット周期制御と4ビット音量レベルを提供します。
AYUMI実装に準拠した完全なエンベロープ機能を提供します。
"""

from typing import Optional, List
from .types import (
    InvalidValueError, 
    MAX_ENVELOPE_PERIOD, 
    MAX_VOLUME_LEVEL,
    ENVELOPE_HOLD,
    ENVELOPE_ALTERNATE,
    ENVELOPE_ATTACK,
    ENVELOPE_CONTINUE
)


class EnvelopeGenerator:
    """エンベロープジェネレータ（AYUMI準拠版）

    AY-3-8910のエンベロープジェネレータを実装します。
    16ビット周期カウンタと4ビット音量カウンタを使用して、
    16種類のエンベロープ形状を生成します。

    設計方針（AYUMI準拠）:
        - プリスケーラ（256分周）はコア側で管理
        - update(1)は「プリスケーラ済み」の1サイクルを意味
        - 16ビットダウンカウンタでエンベロープ周期を制御
        - カウンタが0になるたびに4ビット音量レベルを更新
        - R13レジスタの4ビットで形状を制御
        - セグメント自動遷移と状態リセット機能

    Attributes:
        _counter: 現在のカウンタ値
        _period: エンベロープ周期 (EP値、1-65535)
        _level: 現在の音量レベル (0-15)
        _shape: エンベロープ形状 (R13の下位4ビット)
        _current_segment: 現在のセグメント (0または1)
        _envelope_counter: エンベロープカウンタ
        _envelope_period: エンベロープ周期
    """
    
    # AYUMI準拠の16種類のエンベロープ形状定義
    ENVELOPE_SHAPES = {
        0:  "\\_________ (減衰→無音ホールド)",
        1:  "\\_________ (減衰→無音ホールド)",
        2:  "\\_________ (減衰→無音ホールド)",
        3:  "\\_________ (減衰→無音ホールド)",
        4:  "/_________ (アタック→無音ホールド)",
        5:  "/_________ (アタック→無音ホールド)",
        6:  "/_________ (アタック→無音ホールド)",
        7:  "/_________ (アタック→無音ホールド)",
        8:  "\\\\\\\\\\\\\\ (連続減衰)",
        9:  "\\_________ (減衰→無音ホールド)",
        10: "\\/\\/\\/\\/\\/ (三角波・減衰開始)",
        11: "\\^^^^^^^^^ (減衰→最大音量ホールド)",
        12: "/|/|/|/|/| (連続アタック)",
        13: "/^^^^^^^^^ (アタック→最大音量ホールド)",
        14: "/\\/\\/\\/\\/ (三角波・アタック開始)",
        15: "/_________ (アタック→無音ホールド)"
    }
    
    # AYUMI準拠のエンベロープ関数テーブル
    # 各形状は2つのセグメント関数を持つ
    ENVELOPE_FUNCTIONS = [
        # Shape 0-3: 減衰→ホールド
        ('slide_down', 'hold_bottom'),
        ('slide_down', 'hold_bottom'),
        ('slide_down', 'hold_bottom'),
        ('slide_down', 'hold_bottom'),
        # Shape 4-7: アタック→ホールド
        ('slide_up', 'hold_bottom'),
        ('slide_up', 'hold_bottom'),
        ('slide_up', 'hold_bottom'),
        ('slide_up', 'hold_bottom'),
        # Shape 8: 連続減衰
        ('slide_down', 'slide_down'),
        # Shape 9: 減衰→ホールド
        ('slide_down', 'hold_bottom'),
        # Shape 10: 三角波（減衰開始）
        ('slide_down', 'slide_up'),
        # Shape 11: 減衰→最大音量ホールド
        ('slide_down', 'hold_top'),
        # Shape 12: 連続アタック
        ('slide_up', 'slide_up'),
        # Shape 13: アタック→最大音量ホールド
        ('slide_up', 'hold_top'),
        # Shape 14: 三角波（アタック開始）
        ('slide_up', 'slide_down'),
        # Shape 15: アタック→ホールド
        ('slide_up', 'hold_bottom')
    ]
    
    def __init__(self, initial_period: int = 1, initial_shape: int = 0):
        """エンベロープジェネレータを初期化（AYUMI準拠）
        
        Args:
            initial_period: 初期エンベロープ周期 (1-65535)
            initial_shape: 初期エンベロープ形状 (0-15)
            
        Raises:
            InvalidValueError: パラメータが無効な場合
        """
        if not (1 <= initial_period <= MAX_ENVELOPE_PERIOD):
            raise InvalidValueError(f"Envelope period {initial_period} out of range [1, {MAX_ENVELOPE_PERIOD}]")
        
        if not (0 <= initial_shape <= 15):
            raise InvalidValueError(f"Envelope shape {initial_shape} out of range [0, 15]")
        
        self._period = initial_period
        self._counter = initial_period
        self._shape = initial_shape
        
        # AYUMI準拠の状態変数
        self._current_segment = 0
        self._envelope_counter = 0
        self._envelope_period = 1
        self._level = 31  # 初期レベル（AYUMI準拠）

        # 形状状態を初期化
        self._reset_shape_state()

    def _reset_shape_state(self) -> None:
        """形状状態をリセット（AYUMI準拠）"""
        # AYUMI準拠の初期化
        self._current_segment = 0
        self._envelope_counter = 0
        self._envelope_period = 1
        self._level = 31  # 初期レベルは31（AYUMI準拠）
    
    def _slide_down(self) -> None:
        """減衰セグメント（AYUMI準拠）"""
        self._level -= 1
        if self._level < 0:
            self._current_segment ^= 1  # セグメント切り替え
            self._reset_segment()  # リセット時に適切な値が設定される
    
    def _slide_up(self) -> None:
        """アタックセグメント（AYUMI準拠）"""
        self._level += 1
        if self._level > 31:
            self._current_segment ^= 1  # セグメント切り替え
            self._reset_segment()  # リセット時に適切な値が設定される
    
    def _hold_bottom(self) -> None:
        """無音レベルホールド（AYUMI準拠）"""
        self._level = 0
    
    def _hold_top(self) -> None:
        """最大音量レベルホールド（AYUMI準拠）"""
        self._level = 31
    
    def _reset_segment(self) -> None:
        """セグメントリセット（AYUMI準拠）"""
        func_name = self.ENVELOPE_FUNCTIONS[self._shape][self._current_segment]
        if func_name in ['slide_down', 'hold_top']:
            self._level = 31  # 最大値にリセット
        else:
            self._level = 0   # 最小値にリセット

    def update(self, cycles: int) -> None:
        """指定サイクル数分のエンベロープ生成を実行（AYUMI準拠）

        注意: cyclesは「プリスケーラ済み」のサイクル数です。
        コア側で256分周されているため、256マスタークロックに1回呼ばれます。

        Args:
            cycles: 実行するプリスケーラ済みサイクル数

        Raises:
            InvalidValueError: サイクル数が負の場合
        """
        if cycles < 0:
            raise InvalidValueError(f"Cycles must be non-negative, got {cycles}")

        for _ in range(cycles):
            self._envelope_counter += 1
            if self._envelope_counter >= self._envelope_period:
                # 現在のセグメントの関数を実行
                func_name = self.ENVELOPE_FUNCTIONS[self._shape][self._current_segment]
                if func_name == 'slide_down':
                    self._slide_down()
                elif func_name == 'slide_up':
                    self._slide_up()
                elif func_name == 'hold_bottom':
                    self._hold_bottom()
                elif func_name == 'hold_top':
                    self._hold_top()
                self._envelope_counter = 0
    
    def set_envelope_period(self, period: int) -> None:
        """エンベロープ周期を設定（AYUMI準拠）
        
        Args:
            period: エンベロープ周期値 (1-65535)
        """
        if not (1 <= period <= MAX_ENVELOPE_PERIOD):
            raise InvalidValueError(f"Envelope period {period} out of range [1, {MAX_ENVELOPE_PERIOD}]")
        
        self._envelope_period = period
        self._envelope_counter = 0
    
    def get_level(self) -> int:
        """現在のエンベロープレベルを取得（AYUMI準拠）
        
        Returns:
            現在の音量レベル (0-31)
        """
        return self._level
    
    def get_current_segment(self) -> int:
        """現在のセグメントを取得
        
        Returns:
            現在のセグメント (0または1)
        """
        return self._current_segment
    
    def get_envelope_counter(self) -> int:
        """現在のエンベロープカウンタを取得
        
        Returns:
            現在のエンベロープカウンタ値
        """
        return self._envelope_counter
    
    def set_period(self, fine: int, coarse: int) -> None:
        """16ビットエンベロープ周期を設定（AYUMI準拠）
        
        Args:
            fine: Fine周期値 (R11の8ビット値)
            coarse: Coarse周期値 (R12の8ビット値)
            
        Raises:
            InvalidValueError: 値が無効な場合
        """
        if not (0 <= fine <= 255):
            raise InvalidValueError(f"Fine period {fine} out of range [0, 255]")
        
        if not (0 <= coarse <= 255):
            raise InvalidValueError(f"Coarse period {coarse} out of range [0, 255]")
        
        # 16ビット周期値を計算: EP = (Coarse << 8) | Fine
        ep = (coarse << 8) | fine
        
        # EP=0の場合は1にクランプ（ハードウェア仕様）
        self._period = max(1, ep)
        self._counter = self._period
        
        # エンベロープ周期も設定
        self.set_envelope_period(self._period)
    
    def set_period_direct(self, period: int) -> None:
        """エンベロープ周期を直接設定（AYUMI準拠）
        
        Args:
            period: エンベロープ周期値 (0-65535、0は1にクランプされる)
            
        Raises:
            InvalidValueError: 周期が無効な場合
        """
        if not (0 <= period <= MAX_ENVELOPE_PERIOD):
            raise InvalidValueError(f"Envelope period {period} out of range [0, {MAX_ENVELOPE_PERIOD}]")
        
        # EP=0の場合は1にクランプ
        self._period = max(1, period)
        self._counter = self._period
        
        # エンベロープ周期も設定
        self.set_envelope_period(self._period)
    
    def set_shape(self, shape: int) -> None:
        """エンベロープ形状を設定（AYUMI準拠）
        
        Args:
            shape: エンベロープ形状値 (R13の下位4ビット、0-15)
            
        Raises:
            InvalidValueError: 形状が無効な場合
        """
        if not (0 <= shape <= 15):
            raise InvalidValueError(f"Envelope shape {shape} out of range [0, 15]")
        
        self._shape = shape
        self._reset_shape_state()
    
    def get_shape(self) -> int:
        """現在のエンベロープ形状を取得
        
        Returns:
            現在のエンベロープ形状値
        """
        return self._shape
    
    def get_period(self) -> int:
        """現在のエンベロープ周期を取得
        
        Returns:
            現在のエンベロープ周期値
        """
        return self._period
    
    def get_counter(self) -> int:
        """現在のカウンタ値を取得
        
        Returns:
            現在のカウンタ値
        """
        return self._counter
    
    
    
    def reset(self) -> None:
        """エンベロープジェネレータをリセット（AYUMI準拠）"""
        self._counter = self._period
        self._envelope_counter = self._envelope_period
        self._reset_shape_state()
    
    def calculate_frequency(self, master_clock_hz: float) -> float:
        """エンベロープ周波数を計算
        
        Args:
            master_clock_hz: マスタークロック周波数 (Hz)
            
        Returns:
            エンベロープ周波数 (Hz)
            
        Formula:
            F_env = F_clock / (256 * EP)
        """
        if master_clock_hz <= 0:
            raise InvalidValueError(f"Master clock frequency must be positive, got {master_clock_hz}")
        
        return master_clock_hz / (256.0 * self._period)
    
    def set_frequency(self, frequency_hz: float, master_clock_hz: float) -> None:
        """目標周波数からエンベロープ周期を設定
        
        Args:
            frequency_hz: 目標周波数 (Hz)
            master_clock_hz: マスタークロック周波数 (Hz)
            
        Raises:
            InvalidValueError: 周波数が無効な場合
        """
        if frequency_hz <= 0:
            raise InvalidValueError(f"Frequency must be positive, got {frequency_hz}")
        
        if master_clock_hz <= 0:
            raise InvalidValueError(f"Master clock frequency must be positive, got {master_clock_hz}")
        
        # EP = F_clock / (256 * F_env)
        calculated_period = master_clock_hz / (256.0 * frequency_hz)
        period = max(1, min(MAX_ENVELOPE_PERIOD, int(round(calculated_period))))
        
        self.set_period_direct(period)
    
    def get_shape_description(self) -> str:
        """現在の形状の説明を取得
        
        Returns:
            形状の説明文字列
        """
        return self.ENVELOPE_SHAPES.get(self._shape, "Unknown shape")
    
    def predict_next_transition(self) -> int:
        """次のレベル更新までのサイクル数を予測
        
        Returns:
            次のレベル更新までのマスタークロックサイクル数
        """
        # プリスケーラを考慮した残りサイクル数
        prescaler_remaining = 256 - self._prescaler_counter
        counter_cycles = (self._counter - 1) * 256
        
        return prescaler_remaining + counter_cycles
    
    def generate_envelope_sequence(self, length: int) -> List[int]:
        """エンベロープシーケンスを生成（状態は変更しない）
        
        Args:
            length: 生成するシーケンスの長さ
            
        Returns:
            エンベロープレベルのリスト
        """
        # 現在の状態を保存
        saved_state = self.get_state()
        
        # シーケンスを生成
        sequence = []
        for _ in range(length):
            sequence.append(self._level)
            self._update_envelope_level()
        
        # 状態を復元
        self.set_state(saved_state)
        
        return sequence
    
    def copy(self) -> 'EnvelopeGenerator':
        """エンベロープジェネレータの深いコピーを作成
        
        Returns:
            現在の状態をコピーした新しいEnvelopeGeneratorインスタンス
        """
        new_generator = EnvelopeGenerator(self._period, self._shape)
        new_generator._counter = self._counter
        new_generator._level = self._level
        new_generator._holding = self._holding
        new_generator._attacking = self._attacking
        new_generator._alternating = self._alternating
        new_generator._continuing = self._continuing
        new_generator._shape_cycle = self._shape_cycle
        return new_generator
    
    def get_state(self) -> dict:
        """現在の状態を辞書として取得（AYUMI準拠）
        
        Returns:
            状態辞書
        """
        return {
            'period': self._period,
            'counter': self._counter,
            'level': self._level,
            'shape': self._shape,
            'current_segment': self._current_segment,
            'envelope_counter': self._envelope_counter,
            'envelope_period': self._envelope_period
        }
    
    def set_state(self, state: dict) -> None:
        """状態を辞書から復元（AYUMI準拠）
        
        Args:
            state: 状態辞書
            
        Raises:
            InvalidValueError: 状態が無効な場合
        """
        required_keys = {
            'period', 'counter', 'level', 'shape',
            'current_segment', 'envelope_counter', 'envelope_period'
        }
        if not all(key in state for key in required_keys):
            raise InvalidValueError(f"State must contain keys: {required_keys}")
        
        period = state['period']
        if not (1 <= period <= MAX_ENVELOPE_PERIOD):
            raise InvalidValueError(f"Invalid period in state: {period}")
        
        level = state['level']
        if not (0 <= level <= 31):  # AYUMI準拠: 0-31
            raise InvalidValueError(f"Invalid level in state: {level}")
        
        shape = state['shape']
        if not (0 <= shape <= 15):
            raise InvalidValueError(f"Invalid shape in state: {shape}")
        
        self._period = period
        self._counter = state['counter']
        self._level = level
        self._shape = shape
        self._current_segment = state['current_segment']
        self._envelope_counter = state['envelope_counter']
        self._envelope_period = state['envelope_period']
    
    def __str__(self) -> str:
        """文字列表現（AYUMI準拠）"""
        return (f"EnvelopeGenerator(period={self._period}, "
                f"level={self._level}, "
                f"shape={self._shape}, "
                f"segment={self._current_segment})")
    
    def __repr__(self) -> str:
        """詳細文字列表現（AYUMI準拠）"""
        return (f"EnvelopeGenerator(period={self._period}, "
                f"counter={self._counter}, "
                f"level={self._level}, "
                f"shape={self._shape}, "
                f"segment={self._current_segment}, "
                f"env_counter={self._envelope_counter})")
    
    def __eq__(self, other) -> bool:
        """等価比較（AYUMI準拠）"""
        if not isinstance(other, EnvelopeGenerator):
            return False
        return (self._period == other._period and
                self._counter == other._counter and
                self._level == other._level and
                self._shape == other._shape and
                self._current_segment == other._current_segment and
                self._envelope_counter == other._envelope_counter and
                self._envelope_period == other._envelope_period)


# =============================================================================
# ユーティリティ関数
# =============================================================================

def create_envelope_generator(frequency_hz: float, shape: int, 
                            master_clock_hz: float = 2000000.0) -> EnvelopeGenerator:
    """指定周波数と形状のエンベロープジェネレータを作成
    
    Args:
        frequency_hz: 目標周波数 (Hz)
        shape: エンベロープ形状 (0-15)
        master_clock_hz: マスタークロック周波数 (Hz、デフォルト: 2MHz)
        
    Returns:
        設定されたEnvelopeGeneratorインスタンス
    """
    generator = EnvelopeGenerator(initial_shape=shape)
    generator.set_frequency(frequency_hz, master_clock_hz)
    return generator


def calculate_envelope_period_from_registers(fine: int, coarse: int) -> int:
    """レジスタ値からエンベロープ周期を計算
    
    Args:
        fine: Fine周期値 (8ビット)
        coarse: Coarse周期値 (8ビット)
        
    Returns:
        計算されたエンベロープ周期 (1以上)
    """
    ep = (coarse << 8) | fine
    return max(1, ep)


def calculate_registers_from_envelope_period(period: int) -> tuple[int, int]:
    """エンベロープ周期からレジスタ値を計算
    
    Args:
        period: エンベロープ周期 (1-65535)
        
    Returns:
        (fine, coarse) のタプル
        
    Raises:
        InvalidValueError: 周期が無効な場合
    """
    if not (1 <= period <= MAX_ENVELOPE_PERIOD):
        raise InvalidValueError(f"Period {period} out of range [1, {MAX_ENVELOPE_PERIOD}]")
    
    fine = period & 0xFF
    coarse = (period >> 8) & 0xFF
    
    return fine, coarse


def get_all_envelope_shapes() -> dict:
    """全エンベロープ形状の説明を取得
    
    Returns:
        形状番号をキー、説明を値とする辞書
    """
    return EnvelopeGenerator.ENVELOPE_SHAPES.copy()
