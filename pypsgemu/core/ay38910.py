"""
AY-3-8910 PSG エミュレータ - コアエミュレータ

このモジュールは、AY-3-8910の完全なエミュレーションを提供する
コアエミュレータクラスを実装します。
"""

from typing import Dict, Any, List, Optional
from .types import (
    AY38910State, Device, AudioDevice,
    RegisterAccessError, InvalidValueError,
    NUM_REGISTERS, NUM_TONE_CHANNELS,
    REG_TONE_A_FINE, REG_TONE_A_COARSE,
    REG_TONE_B_FINE, REG_TONE_B_COARSE,
    REG_TONE_C_FINE, REG_TONE_C_COARSE,
    REG_NOISE_PERIOD, REG_MIXER_CONTROL,
    REG_VOLUME_A, REG_VOLUME_B, REG_VOLUME_C,
    REG_ENVELOPE_FINE, REG_ENVELOPE_COARSE, REG_ENVELOPE_SHAPE,
    REG_IO_PORT_A, REG_IO_PORT_B
)
from .device_config import AY38910Config
from .tone_generator import ToneGenerator
from .noise_generator import NoiseGenerator
from .envelope_generator import EnvelopeGenerator
from .mixer import Mixer
from ..utils.volume_table import VolumeTable


class AY38910Core(Device, AudioDevice):
    """AY-3-8910 コアエミュレータ
    
    AY-3-8910チップの完全なエミュレーションを提供します。
    Tick駆動実行モデルを使用し、正確なタイミングでハードウェアを模倣します。
    
    主な機能:
    - 16個のレジスタ管理
    - 3チャンネルトーンジェネレータ
    - 17ビットLFSRノイズジェネレータ
    - エンベロープジェネレータ
    - チャンネルミキサー
    - リアルタイム音声出力
    
    Attributes:
        _config: エミュレータ設定
        _state: 内部状態
        _tone_generators: 3チャンネルのトーンジェネレータ
        _noise_generator: ノイズジェネレータ
        _envelope_generator: エンベロープジェネレータ
        _mixer: チャンネルミキサー
        _volume_table: 音量変換テーブル
    """
    
    def __init__(self, config: AY38910Config):
        """AY38910Coreを初期化
        
        Args:
            config: エミュレータ設定
        """
        self._config = config
        self._state = AY38910State()
        
        # ジェネレータインスタンス作成
        self._tone_generators = [ToneGenerator() for _ in range(NUM_TONE_CHANNELS)]
        self._noise_generator = NoiseGenerator()
        self._envelope_generator = EnvelopeGenerator()
        
        # ジェネレータの状態をコア状態に同期
        self._state.noise_output = self._noise_generator.get_output()
        self._state.lfsr_value = self._noise_generator.get_lfsr_state()
        
        # ミキサーと音量テーブル
        self._volume_table = VolumeTable()
        self._mixer = Mixer(self._volume_table)
        
        # デバッグ情報
        self._debug_info = {
            'total_ticks': 0,
            'register_writes': 0,
            'register_reads': 0,
            'last_output': 0.0
        }
        
        # パフォーマンス監視（最適化用）
        self._performance_stats = {
            'tick_time_total': 0.0,
            'tick_count': 0,
            'avg_tick_time': 0.0,
            'memory_usage_bytes': 0,
            'cpu_efficiency': 1.0
        }
    
    @property
    def name(self) -> str:
        """デバイス名を取得"""
        return "AY-3-8910 PSG"
    
    def reset(self) -> None:
        """エミュレータをリセット"""
        # 状態をリセット
        self._state = AY38910State()
        
        # 全ジェネレータをリセット
        for generator in self._tone_generators:
            generator.reset()
        
        self._noise_generator.reset()
        self._envelope_generator.reset()
        
        # デバッグ情報をリセット
        self._debug_info = {
            'total_ticks': 0,
            'register_writes': 0,
            'register_reads': 0,
            'last_output': 0.0
        }
        
        if self._config.enable_debug:
            print(f"[DEBUG] {self.name} reset completed")
    
    def tick(self, master_cycles: int) -> int:
        """Tick駆動実行（アーキテクチャ仕様書準拠版）

        仕様書準拠: SW201 L386-403（アーキテクチャ設計書）

        設計方針（上位文書に準拠）:
            - コア側が16分周/256分周プリスケーラを管理
            - ジェネレータはプリスケーラを持たず、update(1)で1カウント実行
            - 16マスタークロックに1回トーン/ノイズ更新
            - 256マスタークロックに1回エンベロープ更新

        Args:
            master_cycles: 実行するマスタークロックサイクル数

        Returns:
            実際に消費されたサイクル数

        Raises:
            InvalidValueError: サイクル数が無効な場合
        """
        if master_cycles < 0:
            raise InvalidValueError(f"master_cycles must be non-negative, got {master_cycles}")

        if master_cycles == 0:
            return 0

        consumed_cycles = 0

        for _ in range(master_cycles):
            # マスタークロックカウンタをインクリメント
            self._state.master_clock_counter += 1

            # プリスケーラ処理（16分周）
            if self._state.master_clock_counter % 16 == 0:
                self._update_tone_generators()
                self._update_noise_generator()

            # エンベロープ更新（256分周）
            if self._state.master_clock_counter % 256 == 0:
                self._update_envelope_generator()

            consumed_cycles += 1

        # デバッグ情報更新
        if self._config.enable_debug:
            self._debug_info['total_ticks'] += consumed_cycles

        return consumed_cycles

    def _update_tone_generators(self) -> None:
        """トーンジェネレータ更新（仕様準拠版）

        ジェネレータのpublicメソッドを使用し、カプセル化を維持。
        """
        for i in range(NUM_TONE_CHANNELS):
            self._tone_generators[i].update(1)
            self._state.tone_outputs[i] = self._tone_generators[i].get_output()

    def _update_noise_generator(self) -> None:
        """ノイズジェネレータ更新（仕様準拠版）

        ジェネレータのpublicメソッドを使用し、カプセル化を維持。
        """
        self._noise_generator.update(1)
        self._state.noise_output = self._noise_generator.get_output()
        self._state.lfsr_value = self._noise_generator.get_lfsr_state()

    def _update_envelope_generator(self) -> None:
        """エンベロープジェネレータ更新（仕様準拠版）

        ジェネレータのpublicメソッドを使用し、カプセル化を維持。
        """
        self._envelope_generator.update(1)
        self._state.envelope_level = self._envelope_generator.get_level()

    def _update_generators_inline(self, registers: List[int]) -> None:
        """ジェネレータ更新のインライン版（旧実装、後方互換性のため保持）"""
        # トーンジェネレータ更新（ループ展開）
        for i in range(NUM_TONE_CHANNELS):
            fine_reg = i * 2
            coarse_reg = i * 2 + 1

            # レジスタ値を直接使用（プロパティアクセス回避）
            fine = registers[fine_reg]
            coarse = registers[coarse_reg] & 0x0F

            # ジェネレータ更新
            self._tone_generators[i].set_period(fine, coarse)
            self._tone_generators[i].update(1)
            self._state.tone_outputs[i] = self._tone_generators[i].get_output()

        # ノイズジェネレータ更新
        noise_period = registers[REG_NOISE_PERIOD] & 0x1F
        self._noise_generator.set_period(noise_period)
        self._noise_generator.update(1)
        self._state.noise_output = self._noise_generator.get_output()
        self._state.lfsr_value = self._noise_generator.get_lfsr_state()

        # エンベロープジェネレータ更新
        self._envelope_generator.update(1)
        self._state.envelope_level = self._envelope_generator.get_level()
    
    def _update_tone_generators(self) -> None:
        """トーンジェネレータを更新"""
        for i in range(NUM_TONE_CHANNELS):
            # レジスタから周期値を取得
            fine_reg = i * 2  # R0, R2, R4
            coarse_reg = i * 2 + 1  # R1, R3, R5
            
            fine = self._state.registers[fine_reg]
            coarse = self._state.registers[coarse_reg] & 0x0F  # 下位4ビットのみ
            
            # 周期を設定
            self._tone_generators[i].set_period(fine, coarse)
            
            # 1サイクル実行
            self._tone_generators[i].update(1)
            
            # 出力を状態に保存
            self._state.tone_outputs[i] = self._tone_generators[i].get_output()
    
    def _update_tone_generators_optimized(self) -> None:
        """トーンジェネレータを更新（最適化版）"""
        registers = self._state.registers
        tone_outputs = self._state.tone_outputs
        
        # ループ展開による最適化
        for i in range(NUM_TONE_CHANNELS):
            fine_reg = i * 2
            coarse_reg = i * 2 + 1
            
            fine = registers[fine_reg]
            coarse = registers[coarse_reg] & 0x0F
            
            generator = self._tone_generators[i]
            generator.set_period(fine, coarse)
            generator.update(1)
            tone_outputs[i] = generator.get_output()
    
    def _update_noise_generator(self) -> None:
        """ノイズジェネレータを更新"""
        # R6からノイズ周期を取得（下位5ビット）
        noise_period = self._state.registers[REG_NOISE_PERIOD] & 0x1F
        
        # 周期が変更された場合のみ設定（カウンタリセットを防ぐ）
        if self._noise_generator.get_period() != noise_period:
            self._noise_generator.set_period(noise_period)
        
        # 1サイクル実行
        self._noise_generator.update(1)
        
        # 出力を状態に保存
        self._state.noise_output = self._noise_generator.get_output()
        self._state.lfsr_value = self._noise_generator.get_lfsr_state()
    
    def _update_noise_generator_optimized(self) -> None:
        """ノイズジェネレータを更新（最適化版・インライン化）"""
        # インライン化: NoiseGeneratorのupdate(1)ロジックを直接実装
        # これにより二重プリスケーラ問題を回避
        noise_gen = self._noise_generator
        noise_gen._prescaler_counter += 1

        if noise_gen._prescaler_counter >= 16:
            noise_gen._prescaler_counter = 0
            noise_gen._counter -= 1

            if noise_gen._counter <= 0:
                # LFSR更新
                noise_gen._output = noise_gen._lfsr.step()
                noise_gen._counter = noise_gen._period

        self._state.noise_output = noise_gen._output
        self._state.lfsr_value = noise_gen._lfsr.get_value()
    
    def _update_envelope_generator(self) -> None:
        """エンベロープジェネレータを更新"""
        # 1サイクル実行（周期と形状は既に設定済み）
        self._envelope_generator.update(1)
        
        # 出力を状態に保存
        self._state.envelope_level = self._envelope_generator.get_level()
    
    def _update_envelope_generator_optimized(self) -> None:
        """エンベロープジェネレータを更新（最適化版）"""
        self._envelope_generator.update(1)
        
        self._state.envelope_level = self._envelope_generator.get_level()
    
    def read_register(self, address: int) -> int:
        """レジスタ読み込み
        
        Args:
            address: レジスタアドレス (0-15)
            
        Returns:
            レジスタ値 (0-255)
            
        Raises:
            RegisterAccessError: 無効なアドレスの場合
        """
        if not (0 <= address <= 15):
            raise RegisterAccessError(f"Register address {address} out of range [0, 15]")
        
        value = self._state.registers[address]
        
        # デバッグ情報更新
        self._debug_info['register_reads'] += 1
        
        if self._config.enable_debug:
            print(f"[DEBUG] Read R{address} = 0x{value:02X}")
        
        return value
    
    def write_register(self, address: int, value: int) -> None:
        """レジスタ書き込み
        
        Args:
            address: レジスタアドレス (0-15)
            value: 書き込み値 (0-255)
            
        Raises:
            RegisterAccessError: 無効なアドレスの場合
            InvalidValueError: 無効な値の場合
        """
        if not (0 <= address <= 15):
            raise RegisterAccessError(f"Register address {address} out of range [0, 15]")
        
        if not (0 <= value <= 255):
            raise InvalidValueError(f"Register value {value} out of range [0, 255]")
        
        # レジスタに書き込み
        old_value = self._state.registers[address]
        self._state.registers[address] = value
        
        # デバッグ情報更新
        self._debug_info['register_writes'] += 1
        
        if self._config.enable_debug:
            print(f"[DEBUG] Write R{address} = 0x{value:02X} (was 0x{old_value:02X})")
        
        # ブレークポイントチェック
        if address in self._config.breakpoint_registers:
            if self._config.enable_debug:
                print(f"[DEBUG] Breakpoint hit on R{address} write")
        
        # 特定レジスタの即座更新処理
        self._handle_register_write(address, value)
    
    def _handle_register_write(self, address: int, value: int) -> None:
        """レジスタ書き込み後の処理（Phase 1拡張）

        Args:
            address: レジスタアドレス
            value: 書き込み値

        Phase 1最適化: レジスタ書き込み時にのみ周期を更新する。
        tick()内では周期更新を行わず、関数呼び出しコストを削減。
        """
        # トーン周期レジスタ (R0-R5)
        if 0 <= address <= 5:
            channel = address // 2
            fine = self._state.registers[channel * 2]
            coarse = self._state.registers[channel * 2 + 1] & 0x0F
            self._tone_generators[channel].set_period(fine, coarse)

        # ノイズ周期レジスタ (R6)
        elif address == REG_NOISE_PERIOD:
            noise_period = value & 0x1F
            self._noise_generator.set_period(noise_period)

        # エンベロープ周期レジスタ (R11, R12) の場合、周期を更新
        elif address == REG_ENVELOPE_FINE or address == REG_ENVELOPE_COARSE:
            fine = self._state.registers[REG_ENVELOPE_FINE]
            coarse = self._state.registers[REG_ENVELOPE_COARSE]
            self._envelope_generator.set_period(fine, coarse)

        # エンベロープ形状レジスタ (R13) の場合、即座にリセット
        elif address == REG_ENVELOPE_SHAPE:
            shape = value & 0x0F
            self._envelope_generator.set_shape(shape)

            # エンベロープ形状変更時は状態をリセット
            self._state.envelope_level = self._envelope_generator.get_level()
    
    def get_mixed_output(self) -> float:
        """ミックス済み音声出力を取得
        
        Returns:
            正規化された音声出力 (-1.0〜1.0)
        """
        # ミキサー制御レジスタ (R7)
        mixer_control = self._state.registers[REG_MIXER_CONTROL]
        
        # 音量レジスタ (R8-R10)
        volume_registers = [
            self._state.registers[REG_VOLUME_A],
            self._state.registers[REG_VOLUME_B],
            self._state.registers[REG_VOLUME_C]
        ]
        
        # ミキサーで最終出力を生成
        output = self._mixer.get_mixed_output(
            self._state.tone_outputs,
            self._state.noise_output,
            mixer_control,
            volume_registers,
            self._state.envelope_level
        )
        
        # 全体音量スケールを適用
        output *= self._config.volume_scale
        
        # デバッグ情報更新（条件付き）
        if self._config.enable_debug:
            self._debug_info['last_output'] = output
        
        return output
    
    def get_mixed_output_optimized(self) -> float:
        """ミックス済み音声出力を取得（最適化版）
        
        Returns:
            正規化された音声出力 (-1.0〜1.0)
        """
        # レジスタアクセスを最小化
        registers = self._state.registers
        mixer_control = registers[REG_MIXER_CONTROL]
        
        # 音量レジスタを直接参照
        volume_a = registers[REG_VOLUME_A]
        volume_b = registers[REG_VOLUME_B]
        volume_c = registers[REG_VOLUME_C]
        
        # ミキサーで最終出力を生成（リスト作成を回避）
        output = self._mixer.get_mixed_output_direct(
            self._state.tone_outputs[0], self._state.tone_outputs[1], self._state.tone_outputs[2],
            self._state.noise_output,
            mixer_control,
            volume_a, volume_b, volume_c,
            self._state.envelope_level
        )
        
        # 全体音量スケールを適用
        return output * self._config.volume_scale
    
    def get_channel_outputs(self) -> List[float]:
        """各チャンネルの個別出力を取得
        
        Returns:
            List[float]: 各チャンネルの出力値 [A, B, C]
        """
        # ミキサー制御レジスタ (R7)
        mixer_control = self._state.registers[REG_MIXER_CONTROL]
        
        # 音量レジスタ (R8-R10)
        volume_registers = [
            self._state.registers[REG_VOLUME_A],
            self._state.registers[REG_VOLUME_B],
            self._state.registers[REG_VOLUME_C]
        ]
        
        # 各チャンネルの個別出力を取得
        mixed_channels, volume_outputs = self._mixer.get_channel_outputs(
            self._state.tone_outputs,
            self._state.noise_output,
            mixer_control,
            volume_registers,
            self._state.envelope_level
        )
        
        # 音量スケールを適用
        outputs = [output * self._config.volume_scale for output in volume_outputs]
        
        return outputs
    
    def set_sample_rate(self, sample_rate: int) -> None:
        """サンプルレートを設定
        
        Args:
            sample_rate: 新しいサンプルレート
        """
        # 設定を更新（実際の設定オブジェクトは変更しない）
        if self._config.enable_debug:
            print(f"[DEBUG] Sample rate change requested: {sample_rate} Hz")
    
    def get_state(self) -> Dict[str, Any]:
        """現在の状態を取得
        
        Returns:
            状態辞書
        """
        state_dict = self._state.to_dict()
        
        # ジェネレータの状態を追加
        state_dict['tone_generator_states'] = [
            gen.get_state() for gen in self._tone_generators
        ]
        state_dict['noise_generator_state'] = self._noise_generator.get_state()
        state_dict['envelope_generator_state'] = self._envelope_generator.get_state()
        
        # デバッグ情報を追加
        state_dict['debug_info'] = self._debug_info.copy()
        
        return state_dict
    
    def set_state(self, state: Dict[str, Any]) -> None:
        """状態を復元
        
        Args:
            state: 状態辞書
            
        Raises:
            InvalidValueError: 状態が無効な場合
        """
        # 基本状態のみを抽出してAY38910Stateを復元
        basic_state = {}
        for key in ['registers', 'selected_register', 'master_clock_counter',
                   'tone_counters', 'noise_counter', 'envelope_counter',
                   'tone_outputs', 'noise_output', 'envelope_level',
                   'lfsr_value', 'envelope_holding', 'envelope_attacking',
                   'envelope_alternating', 'envelope_continuing']:
            if key in state:
                basic_state[key] = state[key]
        
        self._state = AY38910State.from_dict(basic_state)
        
        # ジェネレータの状態を復元
        if 'tone_generator_states' in state:
            for i, gen_state in enumerate(state['tone_generator_states']):
                if i < len(self._tone_generators):
                    self._tone_generators[i].set_state(gen_state)
        
        if 'noise_generator_state' in state:
            self._noise_generator.set_state(state['noise_generator_state'])
        
        if 'envelope_generator_state' in state:
            self._envelope_generator.set_state(state['envelope_generator_state'])
        
        # デバッグ情報を復元
        if 'debug_info' in state:
            self._debug_info.update(state['debug_info'])
        
        if self._config.enable_debug:
            print(f"[DEBUG] State restored successfully")
    
    def get_register_info(self, address: int) -> Dict[str, Any]:
        """レジスタ詳細情報を取得
        
        Args:
            address: レジスタアドレス
            
        Returns:
            レジスタ情報辞書
        """
        if not (0 <= address <= 15):
            raise RegisterAccessError(f"Register address {address} out of range [0, 15]")
        
        value = self._state.registers[address]
        
        # レジスタ名とタイプを決定
        register_names = {
            0: "Tone A Fine", 1: "Tone A Coarse",
            2: "Tone B Fine", 3: "Tone B Coarse", 
            4: "Tone C Fine", 5: "Tone C Coarse",
            6: "Noise Period", 7: "Mixer Control",
            8: "Volume A", 9: "Volume B", 10: "Volume C",
            11: "Envelope Fine", 12: "Envelope Coarse", 13: "Envelope Shape",
            14: "I/O Port A", 15: "I/O Port B"
        }
        
        info = {
            'address': address,
            'name': register_names.get(address, "Unknown"),
            'value': value,
            'hex_value': f"0x{value:02X}",
            'binary_value': f"0b{value:08b}"
        }
        
        # 特定レジスタの詳細解析
        if address == REG_MIXER_CONTROL:
            info['mixer_analysis'] = self._mixer.analyze_mixer_control(value)
        elif address in [REG_VOLUME_A, REG_VOLUME_B, REG_VOLUME_C]:
            info['volume_analysis'] = self._mixer.analyze_volume_register(value)
        
        return info
    
    def get_channel_info(self, channel: int) -> Dict[str, Any]:
        """チャンネル詳細情報を取得
        
        Args:
            channel: チャンネル番号 (0-2)
            
        Returns:
            チャンネル情報辞書
        """
        if not (0 <= channel <= 2):
            raise InvalidValueError(f"Channel {channel} out of range [0, 2]")
        
        # トーン周期計算
        fine_reg = channel * 2
        coarse_reg = channel * 2 + 1
        fine = self._state.registers[fine_reg]
        coarse = self._state.registers[coarse_reg] & 0x0F
        tone_period = (coarse << 8) | fine
        
        # 音量レジスタ解析
        volume_reg = self._state.registers[REG_VOLUME_A + channel]
        volume_analysis = self._mixer.analyze_volume_register(volume_reg)
        
        # 周波数計算
        tone_frequency = 0.0
        if tone_period > 0:
            tone_frequency = self._config.effective_clock_frequency / tone_period
        
        return {
            'channel': channel,
            'channel_name': ['A', 'B', 'C'][channel],
            'tone_period': tone_period,
            'tone_frequency': tone_frequency,
            'tone_output': self._state.tone_outputs[channel],
            'volume_register': volume_reg,
            'volume_analysis': volume_analysis,
            'generator_state': self._tone_generators[channel].get_state()
        }
    
    def get_debug_info(self) -> Dict[str, Any]:
        """デバッグ情報を取得
        
        Returns:
            デバッグ情報辞書
        """
        return {
            'config': {
                'clock_frequency': self._config.clock_frequency,
                'effective_clock_frequency': self._config.effective_clock_frequency,
                'sample_rate': self._config.sample_rate,
                'enable_debug': self._config.enable_debug
            },
            'statistics': self._debug_info.copy(),
            'current_state': {
                'master_clock_counter': self._state.master_clock_counter,
                'tone_outputs': self._state.tone_outputs.copy(),
                'noise_output': self._state.noise_output,
                'envelope_level': self._state.envelope_level,
                'last_mixed_output': self._debug_info['last_output']
            }
        }
    
    def get_config(self) -> AY38910Config:
        """エミュレータ設定を取得
        
        Returns:
            AY38910Config: エミュレータ設定
        """
        return self._config
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """パフォーマンス統計を取得
        
        Returns:
            パフォーマンス統計辞書
        """
        # メモリ使用量を計算
        import sys
        memory_usage = sys.getsizeof(self._state) + sys.getsizeof(self._debug_info)
        memory_usage += sum(sys.getsizeof(gen) for gen in self._tone_generators)
        memory_usage += sys.getsizeof(self._noise_generator)
        memory_usage += sys.getsizeof(self._envelope_generator)
        memory_usage += sys.getsizeof(self._mixer)
        
        # 平均tick時間を計算
        if self._performance_stats['tick_count'] > 0:
            avg_time = self._performance_stats['tick_time_total'] / self._performance_stats['tick_count']
            self._performance_stats['avg_tick_time'] = avg_time
        
        self._performance_stats['memory_usage_bytes'] = memory_usage
        
        return self._performance_stats.copy()
    
    def reset_performance_stats(self) -> None:
        """パフォーマンス統計をリセット"""
        self._performance_stats = {
            'tick_time_total': 0.0,
            'tick_count': 0,
            'avg_tick_time': 0.0,
            'memory_usage_bytes': 0,
            'cpu_efficiency': 1.0
        }
    
    def optimize_for_performance(self) -> None:
        """パフォーマンス最適化設定を適用"""
        # デバッグ機能を無効化（パフォーマンス向上）
        if hasattr(self._config, 'enable_debug'):
            self._config.enable_debug = False
        
        # 統計情報収集を最小化（必要なキーは保持）
        self._debug_info = {
            'total_ticks': self._debug_info.get('total_ticks', 0),
            'register_writes': self._debug_info.get('register_writes', 0),
            'register_reads': self._debug_info.get('register_reads', 0),
            'last_output': self._debug_info.get('last_output', 0.0)
        }
    
    def __str__(self) -> str:
        """文字列表現"""
        return (f"AY38910Core(clock={self._config.clock_frequency/1000000:.1f}MHz, "
                f"ticks={self._debug_info['total_ticks']})")
    
    def __repr__(self) -> str:
        """詳細文字列表現"""
        return (f"AY38910Core(config={self._config}, "
                f"state={self._state}, "
                f"debug_info={self._debug_info})")


# =============================================================================
# ファクトリ関数
# =============================================================================

def create_ay38910_core(config: AY38910Config = None) -> AY38910Core:
    """AY38910Coreを作成
    
    Args:
        config: エミュレータ設定 (Noneの場合はデフォルト作成)
        
    Returns:
        AY38910Coreインスタンス
    """
    if config is None:
        from .device_config import create_default_config
        config = create_default_config()
    
    return AY38910Core(config)


def create_debug_core() -> AY38910Core:
    """デバッグ用AY38910Coreを作成
    
    Returns:
        デバッグ機能有効のAY38910Coreインスタンス
    """
    from .device_config import create_debug_config
    config = create_debug_config()
    return AY38910Core(config)
