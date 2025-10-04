"""
サンプル生成モジュール

AY-3-8910エミュレータコアから音声サンプルを生成します。
エミュレータのtick駆動実行と音声出力のサンプルレート変換を行います。
"""

import numpy as np
from typing import Optional, Tuple
from ..core.ay38910 import AY38910Core
from ..core.types import AY38910Error
from .high_quality_pipeline import HighQualityAudioPipeline, OptimizedAudioPipeline


class SampleGeneratorError(AY38910Error):
    """サンプル生成関連のエラー"""
    pass


class SampleGenerator:
    """AY-3-8910エミュレータコア用サンプル生成器
    
    エミュレータコアのtick駆動実行から音声サンプルを生成します。
    エミュレータの内部クロックと音声出力のサンプルレートの
    変換を効率的に行います。
    """
    
    def __init__(self, core: AY38910Core, sample_rate: int, 
                 output_channels: int = 1, output_gain: float = 1.0,
                 high_quality: bool = False):
        """SampleGeneratorを初期化
        
        Args:
            core: AY-3-8910エミュレータコア
            sample_rate: 出力サンプルレート（Hz）
            output_channels: 出力チャンネル数（1=モノラル、2=ステレオ）
            output_gain: 出力ゲイン（0.0-1.0）
            high_quality: 高品質音声パイプラインを使用するかどうか
            
        Raises:
            SampleGeneratorError: 無効なパラメータが指定された場合
        """
        if sample_rate <= 0:
            raise SampleGeneratorError(f"Sample rate must be positive, got {sample_rate}")
        if output_channels not in (1, 2):
            raise SampleGeneratorError(f"Output channels must be 1 or 2, got {output_channels}")
        if not (0.0 <= output_gain <= 1.0):
            raise SampleGeneratorError(f"Output gain must be 0.0-1.0, got {output_gain}")
        
        self._core = core
        self._sample_rate = sample_rate
        self._output_channels = output_channels
        self._output_gain = output_gain
        self._high_quality = high_quality
        
        # 高品質パイプラインの初期化
        if high_quality:
            self._audio_pipeline = OptimizedAudioPipeline(sample_rate)
        else:
            self._audio_pipeline = None
        
        # エミュレータクロック周波数を取得（フルクロック周波数を使用）
        self._emulator_clock = core.get_config().clock_frequency
        
        # サンプル生成用の累積カウンタ
        self._tick_accumulator = 0.0
        self._ticks_per_sample = self._emulator_clock / sample_rate
        
        # 統計情報
        self._samples_generated = 0
        self._ticks_executed = 0
        
        # デバッグ情報
        self._debug_enabled = core.get_config().enable_debug
    
    @property
    def sample_rate(self) -> int:
        """出力サンプルレートを取得"""
        return self._sample_rate
    
    @property
    def output_channels(self) -> int:
        """出力チャンネル数を取得"""
        return self._output_channels
    
    @property
    def output_gain(self) -> float:
        """出力ゲインを取得"""
        return self._output_gain
    
    @output_gain.setter
    def output_gain(self, gain: float) -> None:
        """出力ゲインを設定
        
        Args:
            gain: 新しいゲイン値（0.0-1.0）
            
        Raises:
            SampleGeneratorError: 無効なゲイン値の場合
        """
        if not (0.0 <= gain <= 1.0):
            raise SampleGeneratorError(f"Output gain must be 0.0-1.0, got {gain}")
        self._output_gain = gain
    
    def generate_samples(self, count: int) -> np.ndarray:
        """指定された数のサンプルを生成

        Args:
            count: 生成するサンプル数

        Returns:
            生成されたサンプルデータ
            - モノラル: shape=(count,)
            - ステレオ: shape=(count, 2)
        """
        if count <= 0:
            if self._output_channels == 1:
                return np.array([], dtype=np.float32)
            else:
                return np.array([], dtype=np.float32).reshape(0, 2)

        # サンプル配列を準備
        if self._output_channels == 1:
            samples = np.zeros(count, dtype=np.float32)
        else:
            samples = np.zeros((count, 2), dtype=np.float32)

        # サンプルごとに正確に生成（仕様準拠）
        for i in range(count):
            # 累積カウンタで正確なタイミング管理
            self._tick_accumulator += self._ticks_per_sample
            ticks_to_execute = int(self._tick_accumulator)
            self._tick_accumulator -= ticks_to_execute

            # エミュレータを実行
            if ticks_to_execute > 0:
                consumed = self._core.tick(ticks_to_execute)
                self._ticks_executed += consumed

            # 現在の出力を取得
            mixed_output = self._core.get_mixed_output()
            sample_value = mixed_output * self._output_gain

            # 高品質パイプラインで処理
            if self._high_quality and self._audio_pipeline:
                # ステレオ出力の場合、左右チャンネルを同じ値で処理
                if self._output_channels == 2:
                    left_sample, right_sample = self._audio_pipeline.process_samples(
                        sample_value, sample_value
                    )
                    samples[i, 0] = left_sample
                    samples[i, 1] = right_sample
                else:
                    # モノラル出力の場合
                    processed_samples = self._audio_pipeline.process_samples_batch(
                        np.array([sample_value], dtype=np.float32)
                    )
                    samples[i] = processed_samples[0] if len(processed_samples) > 0 else sample_value
            else:
                # 通常の処理
                if self._output_channels == 1:
                    samples[i] = sample_value
                else:
                    samples[i, 0] = sample_value
                    samples[i, 1] = sample_value

        self._samples_generated += count
        return samples
    
    def generate_samples_with_timing(self, count: int) -> Tuple[np.ndarray, dict]:
        """タイミング情報付きでサンプルを生成
        
        Args:
            count: 生成するサンプル数
            
        Returns:
            (サンプルデータ, タイミング情報辞書)
        """
        import time
        start_time = time.perf_counter()
        
        samples = self.generate_samples(count)
        
        end_time = time.perf_counter()
        generation_time = end_time - start_time
        
        timing_info = {
            'generation_time': generation_time,
            'samples_per_second': count / generation_time if generation_time > 0 else 0,
            'real_time_factor': (count / self._sample_rate) / generation_time if generation_time > 0 else 0,
            'ticks_per_sample': self._ticks_per_sample,
            'tick_accumulator': self._tick_accumulator
        }
        
        return samples, timing_info
    
    def reset_timing(self) -> None:
        """タイミング状態をリセット"""
        self._tick_accumulator = 0.0
    
    def get_core(self) -> AY38910Core:
        """エミュレータコアを取得
        
        Returns:
            AY38910Coreインスタンス
        """
        return self._core
    
    def get_statistics(self) -> dict:
        """統計情報を取得
        
        Returns:
            統計情報辞書
        """
        return {
            'sample_rate': self._sample_rate,
            'output_channels': self._output_channels,
            'output_gain': self._output_gain,
            'emulator_clock': self._emulator_clock,
            'ticks_per_sample': self._ticks_per_sample,
            'tick_accumulator': self._tick_accumulator,
            'samples_generated': self._samples_generated,
            'ticks_executed': self._ticks_executed,
            'average_ticks_per_sample': (
                self._ticks_executed / self._samples_generated 
                if self._samples_generated > 0 else 0
            )
        }
    
    def reset_statistics(self) -> None:
        """統計情報をリセット"""
        self._samples_generated = 0
        self._ticks_executed = 0


class StereoSampleGenerator(SampleGenerator):
    """ステレオ出力専用サンプル生成器
    
    AY-3-8910の3チャンネル出力を左右に分離してステレオ出力を生成します。
    """
    
    def __init__(self, core: AY38910Core, sample_rate: int, 
                 channel_mapping: str = "ABC", output_gain: float = 1.0):
        """StereoSampleGeneratorを初期化
        
        Args:
            core: AY-3-8910エミュレータコア
            sample_rate: 出力サンプルレート（Hz）
            channel_mapping: チャンネルマッピング（"ABC", "ACB", "BAC", "BCA", "CAB", "CBA"）
            output_gain: 出力ゲイン（0.0-1.0）
            
        Raises:
            SampleGeneratorError: 無効なパラメータが指定された場合
        """
        super().__init__(core, sample_rate, 2, output_gain)
        
        if channel_mapping not in ("ABC", "ACB", "BAC", "BCA", "CAB", "CBA"):
            raise SampleGeneratorError(f"Invalid channel mapping: {channel_mapping}")
        
        self._channel_mapping = channel_mapping
        self._setup_channel_routing()
    
    def _setup_channel_routing(self) -> None:
        """チャンネルルーティングを設定"""
        mapping = self._channel_mapping
        
        # 左チャンネル（L）と右チャンネル（R）の構成
        if mapping == "ABC":  # A=L, B+C=R
            self._left_channels = [0]
            self._right_channels = [1, 2]
        elif mapping == "ACB":  # A=L, C+B=R
            self._left_channels = [0]
            self._right_channels = [2, 1]
        elif mapping == "BAC":  # B=L, A+C=R
            self._left_channels = [1]
            self._right_channels = [0, 2]
        elif mapping == "BCA":  # B=L, C+A=R
            self._left_channels = [1]
            self._right_channels = [2, 0]
        elif mapping == "CAB":  # C=L, A+B=R
            self._left_channels = [2]
            self._right_channels = [0, 1]
        elif mapping == "CBA":  # C=L, B+A=R
            self._left_channels = [2]
            self._right_channels = [1, 0]
    
    def generate_samples(self, count: int) -> np.ndarray:
        """ステレオサンプルを生成
        
        Args:
            count: 生成するサンプル数
            
        Returns:
            ステレオサンプルデータ shape=(count, 2)
        """
        if count <= 0:
            return np.array([], dtype=np.float32).reshape(0, 2)
        
        samples = np.zeros((count, 2), dtype=np.float32)
        
        # 各サンプルを生成
        for i in range(count):
            # 必要なtick数を計算して実行
            self._tick_accumulator += self._ticks_per_sample
            ticks_to_execute = int(self._tick_accumulator)
            self._tick_accumulator -= ticks_to_execute
            
            # エミュレータを実行
            if ticks_to_execute > 0:
                consumed = self._core.tick(ticks_to_execute)
                self._ticks_executed += consumed
            
            # 各チャンネルの個別出力を取得
            channel_outputs = self._core.get_channel_outputs()
            
            # チャンネルマッピングに基づいてステレオ分離
            left_output = 0.0
            right_output = 0.0
            
            # 左チャンネルの合成
            for ch in self._left_channels:
                left_output += channel_outputs[ch]
            
            # 右チャンネルの合成
            for ch in self._right_channels:
                right_output += channel_outputs[ch]
            
            # ゲインを適用
            samples[i, 0] = left_output * self._output_gain
            samples[i, 1] = right_output * self._output_gain
        
        self._samples_generated += count
        return samples
    
    @property
    def channel_mapping(self) -> str:
        """チャンネルマッピングを取得"""
        return self._channel_mapping


def create_sample_generator(core: AY38910Core, sample_rate: int = 44100,
                          stereo: bool = False, output_gain: float = 0.5) -> SampleGenerator:
    """標準的なサンプル生成器を作成
    
    Args:
        core: AY-3-8910エミュレータコア
        sample_rate: サンプルレート（Hz）
        stereo: ステレオ出力を使用するかどうか
        output_gain: 出力ゲイン
        
    Returns:
        SampleGeneratorインスタンス
    """
    if stereo:
        return StereoSampleGenerator(core, sample_rate, "ABC", output_gain)
    else:
        return SampleGenerator(core, sample_rate, 1, output_gain)

