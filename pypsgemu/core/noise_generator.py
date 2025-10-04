"""
AY-3-8910 PSG エミュレータ - ノイズジェネレータ

このモジュールは、AY-3-8910のノイズチャンネルで使用される
17ビットLFSRベースのノイズジェネレータを実装します。
"""

from typing import Optional
from .types import InvalidValueError, MAX_NOISE_PERIOD
from ..utils.lfsr import LFSR


class NoiseGenerator:
    """17ビットLFSRノイズジェネレータ（アーキテクチャ仕様書準拠版）

    AY-3-8910のノイズチャンネルで使用される
    17ビットLFSRベースのノイズジェネレータを実装します。

    設計方針（SW201準拠）:
        - プリスケーラ（16分周）はコア側で管理
        - update(1)は「プリスケーラ済み」の1サイクルを意味
        - 5ビットダウンカウンタでノイズ周期を制御
        - カウンタが0になるたびに17ビットLFSRを更新
        - LFSRのビット0がノイズ出力となる

    Attributes:
        _lfsr: 17ビットLFSR
        _counter: 現在のカウンタ値
        _period: ノイズ周期 (NP値、1-31)
        _output: 現在の出力状態
    """

    def __init__(self, initial_period: int = 1, lfsr_seed: Optional[int] = None):
        """ノイズジェネレータを初期化

        Args:
            initial_period: 初期ノイズ周期 (1-31)
            lfsr_seed: LFSR初期値 (Noneの場合はAYUMI準拠のデフォルト値1)

        Raises:
            InvalidValueError: 周期が無効な場合
        """
        if not (1 <= initial_period <= MAX_NOISE_PERIOD):
            raise InvalidValueError(f"Noise period {initial_period} out of range [1, {MAX_NOISE_PERIOD}]")

        self._lfsr = LFSR(lfsr_seed)
        self._period = initial_period
        self._counter = 0  # AYUMI準拠: 初期カウンタは0
        self._output = self._lfsr.get_output()

    def update(self, cycles: int) -> None:
        """指定サイクル数分のノイズ生成を実行（プリスケーラ済み）

        注意: cyclesは「プリスケーラ済み」のサイクル数です。
        コア側で16分周されているため、16マスタークロックに1回呼ばれます。
        
        AYUMI準拠の実装では、ノイズ周期は内部で2倍されます。

        Args:
            cycles: 実行するプリスケーラ済みサイクル数

        Raises:
            InvalidValueError: サイクル数が負の場合
        """
        if cycles < 0:
            raise InvalidValueError(f"Cycles must be non-negative, got {cycles}")

        for _ in range(cycles):
            self._counter += 1

            # AYUMI準拠: ノイズ周期の2倍処理
            # カウンタが周期の2倍に達したらLFSRを更新
            if self._counter >= (self._period << 1):
                self._output = self._lfsr.step()
                self._counter = 0
    
    def get_output(self) -> bool:
        """現在のノイズ出力を取得
        
        Returns:
            現在の1ビット出力状態
        """
        return self._output
    
    def set_period(self, np: int) -> None:
        """5ビットノイズ周期を設定
        
        Args:
            np: ノイズ周期値 (R6の下位5ビット値、0-31)
            
        Raises:
            InvalidValueError: 値が無効な場合
        """
        if not (0 <= np <= MAX_NOISE_PERIOD):
            raise InvalidValueError(f"Noise period {np} out of range [0, {MAX_NOISE_PERIOD}]")
        
        # NP=0の場合は1にクランプ（ハードウェア仕様）
        self._period = max(1, np)
        
        # AYUMI準拠: カウンタを0にリセット
        self._counter = 0
    
    def get_period(self) -> int:
        """現在のノイズ周期を取得
        
        Returns:
            現在のノイズ周期値
        """
        return self._period
    
    def get_counter(self) -> int:
        """現在のカウンタ値を取得
        
        Returns:
            現在のカウンタ値
        """
        return self._counter
    
    
    def get_lfsr_state(self) -> int:
        """現在のLFSR状態を取得
        
        Returns:
            現在の17ビットLFSR値
        """
        return self._lfsr.get_value()
    
    def set_lfsr_state(self, value: int) -> None:
        """LFSR状態を設定
        
        Args:
            value: 新しいLFSR値
            
        Raises:
            InvalidValueError: 値が無効な場合
        """
        self._lfsr.set_value(value)
        self._output = self._lfsr.get_output()
    
    def reset(self, new_lfsr_seed: Optional[int] = None) -> None:
        """ノイズジェネレータをリセット

        Args:
            new_lfsr_seed: 新しいLFSRシード値 (Noneの場合は元の値を維持)
        """
        self._lfsr.reset(new_lfsr_seed)
        self._counter = 0  # AYUMI準拠: カウンタを0にリセット
        self._output = self._lfsr.get_output()
    
    def calculate_frequency(self, master_clock_hz: float) -> float:
        """ノイズ周波数を計算
        
        Args:
            master_clock_hz: マスタークロック周波数 (Hz)
            
        Returns:
            ノイズ周波数 (Hz)
            
        Formula:
            F_noise = F_clock / (16 * NP * 2)  # AYUMI準拠: 周期2倍処理
        """
        if master_clock_hz <= 0:
            raise InvalidValueError(f"Master clock frequency must be positive, got {master_clock_hz}")
        
        return master_clock_hz / (16.0 * self._period * 2)  # AYUMI準拠: 周期2倍処理
    
    def set_frequency(self, frequency_hz: float, master_clock_hz: float) -> None:
        """目標周波数からノイズ周期を設定
        
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
        
        # NP = F_clock / (16 * F_noise * 2)  # AYUMI準拠: 周期2倍処理
        calculated_period = master_clock_hz / (16.0 * frequency_hz * 2)
        period = max(1, min(MAX_NOISE_PERIOD, int(round(calculated_period))))
        
        self.set_period(period)
    
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
        
        # AYUMI準拠: カウンタが大きいほど位相は大きい（アップカウンタのため）
        phase = self._counter / (self._period << 1)  # 周期の2倍で正規化
        return max(0.0, min(1.0, phase))
    
    def predict_next_transition(self) -> int:
        """次のLFSR更新までのサイクル数を予測

        Returns:
            次のLFSR更新までのプリスケーラ済みサイクル数
        """
        # AYUMI準拠: 周期の2倍から現在のカウンタを引いた値
        return (self._period << 1) - self._counter
    
    def predict_next_output(self) -> bool:
        """次のLFSR更新後の出力を予測（状態は変更しない）
        
        Returns:
            次のLFSR更新後の出力値
        """
        return self._lfsr.predict_next_output()
    
    def generate_noise_sequence(self, length: int) -> list[bool]:
        """ノイズシーケンスを生成（状態は変更しない）
        
        Args:
            length: 生成するシーケンスの長さ
            
        Returns:
            ノイズビットのリスト
        """
        # 現在の状態を保存
        lfsr_copy = self._lfsr.copy()
        
        # シーケンスを生成
        sequence = []
        for _ in range(length):
            sequence.append(lfsr_copy.step())
        
        return sequence
    
    def copy(self) -> 'NoiseGenerator':
        """ノイズジェネレータの深いコピーを作成
        
        Returns:
            現在の状態をコピーした新しいNoiseGeneratorインスタンス
        """
        new_generator = NoiseGenerator(self._period)
        new_generator._lfsr = self._lfsr.copy()
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
            'output': self._output,
            
            'lfsr_value': self._lfsr.get_value(),
            'lfsr_cycle_count': self._lfsr.get_cycle_count()
        }
    
    def set_state(self, state: dict) -> None:
        """状態を辞書から復元
        
        Args:
            state: 状態辞書
            
        Raises:
            InvalidValueError: 状態が無効な場合
        """
        required_keys = {'period', 'counter', 'output', 'lfsr_value'}
        if not all(key in state for key in required_keys):
            raise InvalidValueError(f"State must contain keys: {required_keys}")
        
        period = state['period']
        if not (1 <= period <= MAX_NOISE_PERIOD):
            raise InvalidValueError(f"Invalid period in state: {period}")
        
        counter = state['counter']
        if not (0 <= counter <= MAX_NOISE_PERIOD):
            raise InvalidValueError(f"Invalid counter in state: {counter}")
        
        
        lfsr_value = state['lfsr_value']
        
        self._period = period
        self._counter = counter
        self._output = bool(state['output'])
        self._lfsr.set_value(lfsr_value)
        
        # LFSR cycle countが提供されている場合は復元
        if 'lfsr_cycle_count' in state:
            # LFSRのcycle_countは直接設定できないため、
            # 新しいLFSRを作成して状態を復元
            self._lfsr = LFSR(lfsr_value)
            # cycle_countの復元は簡易的な実装
            # 実際の用途では、より詳細な状態管理が必要な場合がある
    
    def get_lfsr_info(self) -> dict:
        """LFSR詳細情報を取得
        
        Returns:
            LFSR情報辞書
        """
        return {
            'value': self._lfsr.get_value(),
            'cycle_count': self._lfsr.get_cycle_count(),
            'bits_string': self._lfsr.get_bits_as_string(),
            'period_length': self._lfsr.get_period_length()
        }
    
    def __str__(self) -> str:
        """文字列表現"""
        return (f"NoiseGenerator(period={self._period}, "
                f"counter={self._counter}, "
                f"output={self._output}, "
                f"lfsr=0x{self._lfsr.get_value():05X})")
    
    def __repr__(self) -> str:
        """詳細文字列表現"""
        return (f"NoiseGenerator(period={self._period}, "
                f"counter={self._counter}, "
                f"output={self._output}, "
                f"lfsr=0x{self._lfsr.get_value():05X}, "
                f"phase={self.get_phase_position():.3f})")
    
    def __eq__(self, other) -> bool:
        """等価比較"""
        if not isinstance(other, NoiseGenerator):
            return False
        return (self._period == other._period and
                self._counter == other._counter and
                self._output == other._output and
                self._lfsr == other._lfsr)


# =============================================================================
# ユーティリティ関数
# =============================================================================

def create_noise_generator(frequency_hz: float, master_clock_hz: float = 2000000.0, 
                          lfsr_seed: Optional[int] = None) -> NoiseGenerator:
    """指定周波数のノイズジェネレータを作成
    
    Args:
        frequency_hz: 目標周波数 (Hz)
        master_clock_hz: マスタークロック周波数 (Hz、デフォルト: 2MHz)
        lfsr_seed: LFSR初期値 (Noneの場合はAYUMI準拠のデフォルト値1)
        
    Returns:
        設定されたNoiseGeneratorインスタンス
    """
    generator = NoiseGenerator(lfsr_seed=lfsr_seed)
    generator.set_frequency(frequency_hz, master_clock_hz)
    return generator


def calculate_noise_period_from_register(r6_value: int) -> int:
    """R6レジスタ値からノイズ周期を計算
    
    Args:
        r6_value: R6レジスタ値 (8ビット、下位5ビットのみ使用)
        
    Returns:
        計算されたノイズ周期 (1以上)
    """
    np = r6_value & 0x1F  # 下位5ビットのみ使用
    return max(1, np)


def test_lfsr_randomness(generator: NoiseGenerator, sample_size: int = 10000) -> dict:
    """LFSRのランダム性をテスト
    
    Args:
        generator: テスト対象のノイズジェネレータ
        sample_size: テストサンプル数
        
    Returns:
        ランダム性統計情報
    """
    sequence = generator.generate_noise_sequence(sample_size)
    
    # 基本統計
    ones_count = sum(sequence)
    zeros_count = sample_size - ones_count
    ones_ratio = ones_count / sample_size
    
    # 連続性テスト
    runs = []
    current_run = 1
    for i in range(1, len(sequence)):
        if sequence[i] == sequence[i-1]:
            current_run += 1
        else:
            runs.append(current_run)
            current_run = 1
    runs.append(current_run)
    
    return {
        'sample_size': sample_size,
        'ones_count': ones_count,
        'zeros_count': zeros_count,
        'ones_ratio': ones_ratio,
        'balance_score': abs(0.5 - ones_ratio),  # 0に近いほど良い
        'runs_count': len(runs),
        'average_run_length': sum(runs) / len(runs) if runs else 0,
        'max_run_length': max(runs) if runs else 0,
        'min_run_length': min(runs) if runs else 0
    }
