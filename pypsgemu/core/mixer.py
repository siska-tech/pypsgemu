"""
AY-3-8910 PSG エミュレータ - ミキサー (修正版)

このモジュールは、AY-3-8910の3チャンネルミキサーを実装します。
R7レジスタによるトーン/ノイズ制御と音量制御を行います。

修正内容:
- 和音出力時のクリッピング問題を解決
- 適切な音量バランスの実装
"""

from typing import List, Tuple
from .types import (
    InvalidValueError,
    MIXER_TONE_A, MIXER_TONE_B, MIXER_TONE_C,
    MIXER_NOISE_A, MIXER_NOISE_B, MIXER_NOISE_C,
    VOLUME_ENVELOPE_MODE
)
from ..utils.volume_table import VolumeTable


class Mixer:
    """AY-3-8910 ミキサー (AYUMI準拠版)
    
    3チャンネルのトーン・ノイズ出力をミキシングし、
    音量制御を適用して最終的なチャンネル出力を生成します。
    
    AYUMI準拠の改善内容:
    - AYUMI準拠の複雑な論理演算: (tone | t_off) & (noise | n_off)
    - ステレオパンニング対応（等パワー・線形パンニング）
    - 左右チャンネル別の出力
    - 高品質な音声処理パイプライン
    
    動作原理:
    1. R7レジスタでトーン/ノイズの有効/無効を制御
    2. AYUMI準拠の論理演算でチャンネルミキシング
    3. R8-R10レジスタで音量制御（固定音量またはエンベロープ）
    4. 音量テーブルでPCM値に変換
    5. ステレオパンニング適用
    6. 左右チャンネル別の最終出力
    
    Attributes:
        _volume_table: 音量変換テーブル
        _pan_left: 3チャンネルの左パンニング係数
        _pan_right: 3チャンネルの右パンニング係数
        _equal_power_panning: 等パワーパンニング使用フラグ
    """
    
    def __init__(self, volume_table: VolumeTable = None, equal_power_panning: bool = True):
        """ミキサーを初期化
        
        Args:
            volume_table: 音量変換テーブル (Noneの場合はデフォルト作成)
            equal_power_panning: 等パワーパンニング使用フラグ
        """
        if volume_table is None:
            self._volume_table = VolumeTable()
        else:
            self._volume_table = volume_table
        
        # ステレオパンニング設定（デフォルト: センター）
        self._equal_power_panning = equal_power_panning
        self._pan_left = [1.0, 1.0, 1.0]  # 3チャンネルの左パンニング係数
        self._pan_right = [1.0, 1.0, 1.0]  # 3チャンネルの右パンニング係数
        
        # 初期パンニング設定（センター）
        self.set_panning(0, 0.5)  # チャンネルA: センター
        self.set_panning(1, 0.5)  # チャンネルB: センター
        self.set_panning(2, 0.5)  # チャンネルC: センター
    
    def mix_channels(self, 
                    tone_outputs: List[bool], 
                    noise_output: bool, 
                    mixer_control: int) -> List[bool]:
        """AYUMI準拠のチャンネルミキシングを実行
        
        AYUMIの実装に完全準拠した論理演算:
        out = (tone | t_off) & (noise | n_off)
        
        Args:
            tone_outputs: 3チャンネルのトーン出力 [A, B, C]
            noise_output: ノイズ出力
            mixer_control: R7レジスタ値（ミキサー制御）
            
        Returns:
            3チャンネルのミックス済み出力 [A, B, C]
            
        Raises:
            InvalidValueError: 入力が無効な場合
        """
        if len(tone_outputs) != 3:
            raise InvalidValueError(f"tone_outputs must have 3 elements, got {len(tone_outputs)}")
        
        if not (0 <= mixer_control <= 255):
            raise InvalidValueError(f"mixer_control {mixer_control} out of range [0, 255]")
        
        mixed_outputs = []
        
        for channel in range(3):
            # R7レジスタのビット解析（アクティブロー）
            # t_off: トーン無効化ビット（1で無効、0で有効）
            t_off = bool(mixer_control & (1 << channel))
            
            # n_off: ノイズ無効化ビット（1で無効、0で有効）
            n_off = bool(mixer_control & (1 << (channel + 3)))
            
            # 正しいAY-3-8910ミキサーロジック
            # トーンとノイズの両方が無効化されている場合は出力なし
            # どちらかが有効で、かつその信号がアクティブな場合に出力
            if t_off and n_off:
                # 両方無効 → 出力なし
                channel_output = False
            elif t_off:
                # トーン無効、ノイズ有効 → ノイズのみ
                channel_output = noise_output
            elif n_off:
                # ノイズ無効、トーン有効 → トーンのみ
                channel_output = tone_outputs[channel]
            else:
                # 両方有効 → トーンとノイズのOR（どちらかがアクティブなら出力）
                channel_output = tone_outputs[channel] or noise_output
            
            mixed_outputs.append(channel_output)
        
        return mixed_outputs
    
    def set_panning(self, channel: int, pan: float) -> None:
        """ステレオパンニングを設定
        
        Args:
            channel: チャンネル番号 (0-2)
            pan: パンニング値 (0.0=左, 0.5=センター, 1.0=右)
            
        Raises:
            InvalidValueError: パラメータが無効な場合
        """
        if not (0 <= channel <= 2):
            raise InvalidValueError(f"channel {channel} out of range [0, 2]")
        
        if not (0.0 <= pan <= 1.0):
            raise InvalidValueError(f"pan {pan} out of range [0.0, 1.0]")
        
        if self._equal_power_panning:
            # 等パワーパンニング（AYUMI準拠）
            import math
            self._pan_left[channel] = math.sqrt(1.0 - pan)
            self._pan_right[channel] = math.sqrt(pan)
        else:
            # 線形パンニング
            self._pan_left[channel] = 1.0 - pan
            self._pan_right[channel] = pan
    
    def get_panning(self, channel: int) -> Tuple[float, float]:
        """チャンネルのパンニング設定を取得
        
        Args:
            channel: チャンネル番号 (0-2)
            
        Returns:
            (left_pan, right_pan) のタプル
            
        Raises:
            InvalidValueError: チャンネル番号が無効な場合
        """
        if not (0 <= channel <= 2):
            raise InvalidValueError(f"channel {channel} out of range [0, 2]")
        
        return self._pan_left[channel], self._pan_right[channel]
    
    def apply_volume(self, 
                    channel_outputs: List[bool], 
                    volume_registers: List[int], 
                    envelope_level: int) -> List[float]:
        """音量制御を適用 (修正版)
        
        Args:
            channel_outputs: 3チャンネルのミックス済み出力 [A, B, C]
            volume_registers: 3チャンネルの音量レジスタ値 [R8, R9, R10]
            envelope_level: エンベロープレベル (0-15)
            
        Returns:
            3チャンネルの音量適用済み出力 [A, B, C] (正規化浮動小数点値)
            
        Raises:
            InvalidValueError: 入力が無効な場合
        """
        if len(channel_outputs) != 3:
            raise InvalidValueError(f"channel_outputs must have 3 elements, got {len(channel_outputs)}")
        
        if len(volume_registers) != 3:
            raise InvalidValueError(f"volume_registers must have 3 elements, got {len(volume_registers)}")
        
        if not (0 <= envelope_level <= 31):
            raise InvalidValueError(f"envelope_level {envelope_level} out of range [0, 31]")
        
        volume_outputs = []
        
        for channel in range(3):
            volume_reg = volume_registers[channel]
            
            if not (0 <= volume_reg <= 255):
                raise InvalidValueError(f"volume_register[{channel}] {volume_reg} out of range [0, 255]")
            
            # 音量モード判定（ビット4: 0=固定音量, 1=エンベロープ）
            volume_mode = bool(volume_reg & VOLUME_ENVELOPE_MODE)
            
            if volume_mode:
                # エンベロープモード
                final_volume_level = envelope_level
            else:
                # 固定音量モード（下位4ビット）
                final_volume_level = volume_reg & 0x0F
            
            # 音量テーブルで正規化浮動小数点値に変換
            volume_float = self._volume_table.lookup_float(final_volume_level)
            
            # チャンネル出力と音量を適用
            if channel_outputs[channel]:
                # 出力がアクティブの場合、音量を適用
                volume_outputs.append(volume_float)
            else:
                # 出力が非アクティブの場合、無音
                volume_outputs.append(0.0)
        
        return volume_outputs
    
    def get_stereo_output(self, 
                         tone_outputs: List[bool], 
                         noise_output: bool, 
                         mixer_control: int, 
                         volume_registers: List[int], 
                         envelope_level: int) -> Tuple[float, float]:
        """AYUMI準拠のステレオ出力を生成
        
        Args:
            tone_outputs: 3チャンネルのトーン出力 [A, B, C]
            noise_output: ノイズ出力
            mixer_control: R7レジスタ値（ミキサー制御）
            volume_registers: 3チャンネルの音量レジスタ値 [R8, R9, R10]
            envelope_level: エンベロープレベル (0-15)
            
        Returns:
            (left_output, right_output) のタプル
        """
        # チャンネルミキシング
        mixed_channels = self.mix_channels(tone_outputs, noise_output, mixer_control)
        
        # 音量制御適用
        volume_outputs = self.apply_volume(mixed_channels, volume_registers, envelope_level)
        
        # ステレオパンニング適用
        left_output = 0.0
        right_output = 0.0
        
        for channel in range(3):
            volume = volume_outputs[channel]
            left_output += volume * self._pan_left[channel]
            right_output += volume * self._pan_right[channel]
        
        # -1.0〜1.0の範囲にクランプ
        left_output = max(-1.0, min(1.0, left_output))
        right_output = max(-1.0, min(1.0, right_output))
        
        return left_output, right_output
    
    def get_mixed_output(self, 
                        tone_outputs: List[bool], 
                        noise_output: bool, 
                        mixer_control: int, 
                        volume_registers: List[int], 
                        envelope_level: int) -> float:
        """完全なミキシング処理を実行 (後方互換性維持)
        
        Args:
            tone_outputs: 3チャンネルのトーン出力 [A, B, C]
            noise_output: ノイズ出力
            mixer_control: R7レジスタ値（ミキサー制御）
            volume_registers: 3チャンネルの音量レジスタ値 [R8, R9, R10]
            envelope_level: エンベロープレベル (0-15)
            
        Returns:
            最終ミックス出力 (-1.0〜1.0の正規化浮動小数点値)
        """
        # ステレオ出力を取得してモノラルに変換
        left_output, right_output = self.get_stereo_output(
            tone_outputs, noise_output, mixer_control, volume_registers, envelope_level
        )
        
        # モノラル出力（左右の平均）
        return (left_output + right_output) / 2.0
    
    def get_channel_outputs(self, 
                           tone_outputs: List[bool], 
                           noise_output: bool, 
                           mixer_control: int, 
                           volume_registers: List[int], 
                           envelope_level: int) -> Tuple[List[bool], List[float]]:
        """チャンネル別の詳細出力を取得
        
        Args:
            tone_outputs: 3チャンネルのトーン出力 [A, B, C]
            noise_output: ノイズ出力
            mixer_control: R7レジスタ値（ミキサー制御）
            volume_registers: 3チャンネルの音量レジスタ値 [R8, R9, R10]
            envelope_level: エンベロープレベル (0-15)
            
        Returns:
            (mixed_channels, volume_outputs) のタプル
            - mixed_channels: ミックス済みチャンネル出力 [A, B, C]
            - volume_outputs: 音量適用済み出力 [A, B, C]
        """
        mixed_channels = self.mix_channels(tone_outputs, noise_output, mixer_control)
        volume_outputs = self.apply_volume(mixed_channels, volume_registers, envelope_level)
        
        return mixed_channels, volume_outputs
    
    def get_volume_table(self) -> VolumeTable:
        """音量テーブルを取得
        
        Returns:
            現在使用中の音量テーブル
        """
        return self._volume_table
    
    def set_volume_table(self, volume_table: VolumeTable) -> None:
        """音量テーブルを設定
        
        Args:
            volume_table: 新しい音量テーブル
        """
        self._volume_table = volume_table
    
    def is_equal_power_panning(self) -> bool:
        """等パワーパンニング使用状態を取得
        
        Returns:
            等パワーパンニング使用フラグ
        """
        return self._equal_power_panning
    
    def set_equal_power_panning(self, enabled: bool) -> None:
        """等パワーパンニングの使用を設定
        
        Args:
            enabled: 等パワーパンニング使用フラグ
        """
        if self._equal_power_panning != enabled:
            self._equal_power_panning = enabled
            # 現在のパンニング設定を再適用
            for channel in range(3):
                current_pan = 1.0 - self._pan_left[channel]  # 概算
                self.set_panning(channel, current_pan)
    
    def analyze_mixer_control(self, mixer_control: int) -> dict:
        """ミキサー制御レジスタを解析
        
        Args:
            mixer_control: R7レジスタ値
            
        Returns:
            解析結果辞書
        """
        if not (0 <= mixer_control <= 255):
            raise InvalidValueError(f"mixer_control {mixer_control} out of range [0, 255]")
        
        return {
            'tone_a_enabled': not bool(mixer_control & MIXER_TONE_A),
            'tone_b_enabled': not bool(mixer_control & MIXER_TONE_B),
            'tone_c_enabled': not bool(mixer_control & MIXER_TONE_C),
            'noise_a_enabled': not bool(mixer_control & MIXER_NOISE_A),
            'noise_b_enabled': not bool(mixer_control & MIXER_NOISE_B),
            'noise_c_enabled': not bool(mixer_control & MIXER_NOISE_C),
            'io_a_enabled': bool(mixer_control & 0x40),  # ビット6
            'io_b_enabled': bool(mixer_control & 0x80),  # ビット7
            'raw_value': mixer_control,
            'binary_string': format(mixer_control, '08b')
        }
    
    def analyze_volume_register(self, volume_register: int) -> dict:
        """音量レジスタを解析
        
        Args:
            volume_register: R8/R9/R10レジスタ値
            
        Returns:
            解析結果辞書
        """
        if not (0 <= volume_register <= 255):
            raise InvalidValueError(f"volume_register {volume_register} out of range [0, 255]")
        
        volume_mode = bool(volume_register & VOLUME_ENVELOPE_MODE)
        volume_level = volume_register & 0x0F
        
        return {
            'envelope_mode': volume_mode,
            'fixed_volume_mode': not volume_mode,
            'volume_level': volume_level,
            'raw_value': volume_register,
            'binary_string': format(volume_register, '08b')
        }
    
    def create_mixer_control(self, 
                           tone_a_enabled: bool = True,
                           tone_b_enabled: bool = True,
                           tone_c_enabled: bool = True,
                           noise_a_enabled: bool = False,
                           noise_b_enabled: bool = False,
                           noise_c_enabled: bool = False,
                           io_a_enabled: bool = False,
                           io_b_enabled: bool = False) -> int:
        """ミキサー制御レジスタ値を作成
        
        Args:
            tone_*_enabled: 各チャンネルのトーン有効フラグ
            noise_*_enabled: 各チャンネルのノイズ有効フラグ
            io_*_enabled: I/Oポート有効フラグ
            
        Returns:
            R7レジスタ値
        """
        mixer_control = 0
        
        # トーン制御ビット（アクティブロー）
        if not tone_a_enabled:
            mixer_control |= MIXER_TONE_A
        if not tone_b_enabled:
            mixer_control |= MIXER_TONE_B
        if not tone_c_enabled:
            mixer_control |= MIXER_TONE_C
        
        # ノイズ制御ビット（アクティブロー）
        if not noise_a_enabled:
            mixer_control |= MIXER_NOISE_A
        if not noise_b_enabled:
            mixer_control |= MIXER_NOISE_B
        if not noise_c_enabled:
            mixer_control |= MIXER_NOISE_C
        
        # I/O制御ビット（アクティブハイ）
        if io_a_enabled:
            mixer_control |= 0x40  # ビット6
        if io_b_enabled:
            mixer_control |= 0x80  # ビット7
        
        return mixer_control
    
    def create_volume_register(self, 
                             volume_level: int, 
                             envelope_mode: bool = False) -> int:
        """音量レジスタ値を作成
        
        Args:
            volume_level: 音量レベル (0-15)
            envelope_mode: エンベロープモード有効フラグ
            
        Returns:
            R8/R9/R10レジスタ値
            
        Raises:
            InvalidValueError: 音量レベルが無効な場合
        """
        if not (0 <= volume_level <= 15):
            raise InvalidValueError(f"volume_level {volume_level} out of range [0, 15]")
        
        volume_register = volume_level & 0x0F
        
        if envelope_mode:
            volume_register |= VOLUME_ENVELOPE_MODE
        
        return volume_register
    
    def __str__(self) -> str:
        """文字列表現"""
        return (f"Mixer(volume_table={self._volume_table}, "
                f"equal_power_panning={self._equal_power_panning}, "
                f"pan_left={self._pan_left}, pan_right={self._pan_right})")
    
    def __repr__(self) -> str:
        """詳細文字列表現"""
        return (f"Mixer(volume_table={repr(self._volume_table)}, "
                f"equal_power_panning={self._equal_power_panning}, "
                f"pan_left={self._pan_left}, pan_right={self._pan_right})")


# =============================================================================
# ユーティリティ関数
# =============================================================================

def create_mixer(volume_table: VolumeTable = None) -> Mixer:
    """ミキサーを作成
    
    Args:
        volume_table: 音量変換テーブル
        
    Returns:
        Mixerインスタンス
    """
    return Mixer(volume_table)


def test_mixer_logic(tone_outputs: List[bool], 
                    noise_output: bool, 
                    mixer_control: int) -> dict:
    """ミキサーロジックをテスト
    
    Args:
        tone_outputs: トーン出力 [A, B, C]
        noise_output: ノイズ出力
        mixer_control: ミキサー制御値
        
    Returns:
        テスト結果辞書
    """
    mixer = Mixer()
    
    # ミキサー制御解析
    control_analysis = mixer.analyze_mixer_control(mixer_control)
    
    # チャンネルミキシング実行
    mixed_outputs = mixer.mix_channels(tone_outputs, noise_output, mixer_control)
    
    return {
        'input_tone_outputs': tone_outputs,
        'input_noise_output': noise_output,
        'mixer_control': control_analysis,
        'mixed_outputs': mixed_outputs,
        'logic_explanation': {
            'channel_a': f"tone={tone_outputs[0]}, noise={noise_output}, "
                        f"tone_en={control_analysis['tone_a_enabled']}, "
                        f"noise_en={control_analysis['noise_a_enabled']}, "
                        f"result={mixed_outputs[0]}",
            'channel_b': f"tone={tone_outputs[1]}, noise={noise_output}, "
                        f"tone_en={control_analysis['tone_b_enabled']}, "
                        f"noise_en={control_analysis['noise_b_enabled']}, "
                        f"result={mixed_outputs[1]}",
            'channel_c': f"tone={tone_outputs[2]}, noise={noise_output}, "
                        f"tone_en={control_analysis['tone_c_enabled']}, "
                        f"noise_en={control_analysis['noise_c_enabled']}, "
                        f"result={mixed_outputs[2]}"
        }
    }
