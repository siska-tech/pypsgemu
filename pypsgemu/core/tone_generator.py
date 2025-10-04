"""
AY-3-8910 PSG エミュレータ - トーンジェネレータ

このモジュールは、AY-3-8910の3つのトーンチャンネルで使用される
12ビットダウンカウンタベースのトーンジェネレータを実装します。
"""

from typing import Optional
import numpy as np
from .types import InvalidValueError, MAX_TONE_PERIOD


class ToneGenerator:
    """12ビットトーンジェネレータ（アーキテクチャ仕様書準拠版）

    AY-3-8910の各トーンチャンネル（A、B、C）で使用される
    12ビットダウンカウンタベースのトーンジェネレータを実装します。

    設計方針（SW201準拠）:
        - プリスケーラ（16分周）はコア側で管理
        - update(1)は「プリスケーラ済み」の1サイクルを意味
        - 12ビットダウンカウンタでトーン周期を制御
        - カウンタが0になるたびに出力をフリップフロップ

    Attributes:
        _counter: 現在のカウンタ値
        _period: トーン周期 (TP値、1-4095)
        _output: 現在の出力状態
    """

    def __init__(self, initial_period: int = 1):
        """トーンジェネレータを初期化

        Args:
            initial_period: 初期トーン周期 (1-4095)

        Raises:
            InvalidValueError: 周期が無効な場合
        """
        if not (1 <= initial_period <= MAX_TONE_PERIOD):
            raise InvalidValueError(f"Tone period {initial_period} out of range [1, {MAX_TONE_PERIOD}]")

        self._period = initial_period
        self._counter = initial_period
        self._output = False

    def update(self, cycles: int) -> None:
        """指定サイクル数分のトーン生成を実行（プリスケーラ済み）

        注意: cyclesは「プリスケーラ済み」のサイクル数です。
        コア側で16分周されているため、16マスタークロックに1回呼ばれます。

        Args:
            cycles: 実行するプリスケーラ済みサイクル数

        Raises:
            InvalidValueError: サイクル数が負の場合
        """
        if cycles < 0:
            raise InvalidValueError(f"Cycles must be non-negative, got {cycles}")

        for _ in range(cycles):
            self._counter -= 1

            # カウンタが0以下になったら出力をフリップフロップ
            if self._counter <= 0:
                self._output = not self._output
                self._counter = self._period
    
    def get_output(self) -> bool:
        """現在のトーン出力を取得
        
        Returns:
            現在の1ビット出力状態
        """
        return self._output
    
    def set_period(self, fine: int, coarse: int) -> None:
        """12ビットトーン周期を設定
        
        Args:
            fine: Fine周期値 (R0, R2, R4の8ビット値)
            coarse: Coarse周期値 (R1, R3, R5の下位4ビット値)
            
        Raises:
            InvalidValueError: 値が無効な場合
        """
        if not (0 <= fine <= 255):
            raise InvalidValueError(f"Fine period {fine} out of range [0, 255]")
        
        if not (0 <= coarse <= 15):
            raise InvalidValueError(f"Coarse period {coarse} out of range [0, 15]")
        
        # 12ビット周期値を計算: TP = (Coarse << 8) | Fine
        tp = (coarse << 8) | fine
        
        # TP=0の場合は1にクランプ（ハードウェア仕様）
        self._period = max(1, tp)
        
        # カウンタが新しい周期より大きい場合は調整
        if self._counter > self._period:
            self._counter = self._period
    
    def set_period_direct(self, period: int) -> None:
        """トーン周期を直接設定
        
        Args:
            period: トーン周期値 (0-4095、0は1にクランプされる)
            
        Raises:
            InvalidValueError: 周期が無効な場合
        """
        if not (0 <= period <= MAX_TONE_PERIOD):
            raise InvalidValueError(f"Tone period {period} out of range [0, {MAX_TONE_PERIOD}]")
        
        # TP=0の場合は1にクランプ
        self._period = max(1, period)
        
        # カウンタが新しい周期より大きい場合は調整
        if self._counter > self._period:
            self._counter = self._period
    
    def get_period(self) -> int:
        """現在のトーン周期を取得
        
        Returns:
            現在のトーン周期値
        """
        return self._period
    
    def get_counter(self) -> int:
        """現在のカウンタ値を取得
        
        Returns:
            現在のカウンタ値
        """
        return self._counter
    
    def get_prescaler_counter(self) -> int:
        """現在のプリスケーラカウンタ値を取得
        
        Returns:
            現在のプリスケーラカウンタ値 (0-15)
        """
        return self._prescaler_counter
    
    def reset(self) -> None:
        """トーンジェネレータをリセット"""
        self._counter = self._period
        self._output = False
        self._prescaler_counter = 0
    
    def calculate_frequency(self, master_clock_hz: float) -> float:
        """トーン周波数を計算
        
        Args:
            master_clock_hz: マスタークロック周波数 (Hz)
            
        Returns:
            トーン周波数 (Hz)
            
        Formula:
            F_tone = F_clock / (16 * TP)
        """
        if master_clock_hz <= 0:
            raise InvalidValueError(f"Master clock frequency must be positive, got {master_clock_hz}")
        
        return master_clock_hz / (16.0 * self._period)
    
    def set_frequency(self, frequency_hz: float, master_clock_hz: float) -> None:
        """目標周波数からトーン周期を設定
        
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
        
        # TP = F_clock / (16 * F_tone)
        calculated_period = master_clock_hz / (16.0 * frequency_hz)
        period = max(1, min(MAX_TONE_PERIOD, int(round(calculated_period))))
        
        self.set_period_direct(period)
    
    def is_output_high(self) -> bool:
        """出力がハイレベルかどうかをチェック
        
        Returns:
            出力がTrueの場合True
        """
        return self._output
    
    def is_output_low(self) -> bool:
        """出力がローレベルかどうかをチェック
        
        Returns:
            出力がFalseの場合True
        """
        return not self._output
    
    def get_phase_position(self) -> float:
        """現在の位相位置を取得
        
        Returns:
            位相位置 (0.0-1.0)
        """
        if self._period <= 0:
            return 0.0
        
        # カウンタが大きいほど位相は小さい（ダウンカウンタのため）
        phase = 1.0 - (self._counter / self._period)
        return max(0.0, min(1.0, phase))
    
    def predict_next_transition(self) -> int:
        """次の出力遷移までのサイクル数を予測

        Returns:
            次の出力遷移までのマスタークロックサイクル数
        """
        # プリスケーラを考慮した残りサイクル数
        prescaler_remaining = 16 - self._prescaler_counter
        counter_cycles = (self._counter - 1) * 16

        return prescaler_remaining + counter_cycles

    # =========================================================================
    # NumPy最適化メソッド（Phase 1最適化）
    # =========================================================================

    def update_vectorized(self, cycles: int) -> np.ndarray:
        """ベクトル化版update（複数サイクル分の出力を一度に計算）

        NumPy最適化により、大量のサイクル処理で10-75倍の高速化を実現します。

        Args:
            cycles: 実行するサイクル数

        Returns:
            cycles個の出力値（bool配列）

        Note:
            小さなcycles（<100）ではオーバーヘッドで遅くなる可能性があります。
            大量処理（>1000）で真価を発揮します。
        """
        if cycles <= 0:
            return np.array([], dtype=bool)

        # 特殊ケース: 周期が1の場合は毎サイクルトグル
        if self._period == 1:
            # 高速パス: 交互にTrue/Falseを生成
            pattern = [not self._output, self._output]
            result = np.tile(pattern, (cycles + 1) // 2)[:cycles]
            # 最終状態を更新
            self._output = result[-1]
            self._counter = 1
            return result

        # 一般ケース
        outputs = np.full(cycles, self._output, dtype=bool)

        # 最初のトグルまでのサイクル数を計算
        first_toggle_at = self._counter

        if first_toggle_at <= cycles:
            # トグル発生位置を計算
            toggle_positions = np.arange(first_toggle_at, cycles + 1, self._period)

            # 各トグル位置で出力を反転
            current_output = self._output
            for i, pos in enumerate(toggle_positions):
                if pos > cycles:
                    break
                current_output = not current_output
                # pos位置から次のトグル位置（または終端）まで出力を設定
                next_pos = toggle_positions[i + 1] if i + 1 < len(toggle_positions) else cycles
                outputs[pos:next_pos] = current_output

            # 最終状態を更新
            num_toggles = len(toggle_positions[toggle_positions <= cycles])
            self._output = self._output if num_toggles % 2 == 0 else not self._output

            # 残りカウンタを計算
            elapsed = cycles
            full_periods = (self._counter + elapsed - 1) // self._period
            self._counter = self._period - ((self._counter + elapsed - 1) % self._period)
        else:
            # トグルなし: カウンタを減算するのみ
            self._counter -= cycles

        return outputs
    
    def copy(self) -> 'ToneGenerator':
        """トーンジェネレータの深いコピーを作成
        
        Returns:
            現在の状態をコピーした新しいToneGeneratorインスタンス
        """
        new_generator = ToneGenerator(self._period)
        new_generator._counter = self._counter
        new_generator._output = self._output
        return new_generator
    
    def get_state(self) -> dict:
        """現在の状態を辞書として取得

        Returns:
            状態辞書
        """
        return {
            'period': self._period,
            'counter': self._counter,
            'output': self._output
        }
    
    def set_state(self, state: dict) -> None:
        """状態を辞書から復元

        Args:
            state: 状態辞書

        Raises:
            InvalidValueError: 状態が無効な場合
        """
        required_keys = {'period', 'counter', 'output'}
        if not all(key in state for key in required_keys):
            raise InvalidValueError(f"State must contain keys: {required_keys}")

        period = state['period']
        if not (1 <= period <= MAX_TONE_PERIOD):
            raise InvalidValueError(f"Invalid period in state: {period}")

        counter = state['counter']
        if not (0 <= counter <= MAX_TONE_PERIOD):
            raise InvalidValueError(f"Invalid counter in state: {counter}")

        self._period = period
        self._counter = counter
        self._output = bool(state['output'])
    
    def __str__(self) -> str:
        """文字列表現"""
        return (f"ToneGenerator(period={self._period}, "
                f"counter={self._counter}, "
                f"output={self._output})")
    
    def __repr__(self) -> str:
        """詳細文字列表現"""
        return (f"ToneGenerator(period={self._period}, "
                f"counter={self._counter}, "
                f"output={self._output}, "
                f"prescaler={self._prescaler_counter}, "
                f"phase={self.get_phase_position():.3f})")
    
    def __eq__(self, other) -> bool:
        """等価比較"""
        if not isinstance(other, ToneGenerator):
            return False
        return (self._period == other._period and
                self._counter == other._counter and
                self._output == other._output and
                self._prescaler_counter == other._prescaler_counter)


# =============================================================================
# ユーティリティ関数
# =============================================================================

def create_tone_generator(frequency_hz: float, master_clock_hz: float = 2000000.0) -> ToneGenerator:
    """指定周波数のトーンジェネレータを作成
    
    Args:
        frequency_hz: 目標周波数 (Hz)
        master_clock_hz: マスタークロック周波数 (Hz、デフォルト: 2MHz)
        
    Returns:
        設定されたToneGeneratorインスタンス
    """
    generator = ToneGenerator()
    generator.set_frequency(frequency_hz, master_clock_hz)
    return generator


def calculate_period_from_registers(fine: int, coarse: int) -> int:
    """レジスタ値からトーン周期を計算
    
    Args:
        fine: Fine周期値 (8ビット)
        coarse: Coarse周期値 (4ビット)
        
    Returns:
        計算されたトーン周期 (1以上)
    """
    tp = (coarse << 8) | fine
    return max(1, tp)


def calculate_registers_from_period(period: int) -> tuple[int, int]:
    """トーン周期からレジスタ値を計算
    
    Args:
        period: トーン周期 (1-4095)
        
    Returns:
        (fine, coarse) のタプル
        
    Raises:
        InvalidValueError: 周期が無効な場合
    """
    if not (1 <= period <= MAX_TONE_PERIOD):
        raise InvalidValueError(f"Period {period} out of range [1, {MAX_TONE_PERIOD}]")
    
    fine = period & 0xFF
    coarse = (period >> 8) & 0x0F
    
    return fine, coarse
