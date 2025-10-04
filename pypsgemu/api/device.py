"""
AY-3-8910 統一デバイスAPI実装

Device プロトコルに準拠したAY-3-8910デバイス実装
"""

from typing import Dict, Any
from .protocols import Device, AudioDevice, DeviceError
from ..core.ay38910 import AY38910Core
from ..core.device_config import AY38910Config


class AY38910Device(Device, AudioDevice):
    """
    AY-3-8910デバイス実装
    
    統一デバイスAPIのDevice及びAudioDeviceプロトコルに準拠した
    AY-3-8910の実装。既存のAY38910Coreをラップして統一APIを提供する。
    """
    
    def __init__(self, config: AY38910Config) -> None:
        """
        デバイス初期化
        
        Args:
            config: AY-3-8910設定オブジェクト
        """
        self._core = AY38910Core(config)
        self._config = config
        
        # レジスタアドレスマッピング
        # AY-3-8910は16個のレジスタ（0-15）を持つ
        self._register_count = 16
        
        if config.enable_debug:
            print(f"[DEBUG] AY38910Device initialized: {self.name}")
    
    @property
    def name(self) -> str:
        """デバイス名取得"""
        return "AY-3-8910 PSG"
    
    def reset(self) -> None:
        """デバイスリセット"""
        self._core.reset()
        
        if self._config.enable_debug:
            print(f"[DEBUG] {self.name} reset completed")
    
    def tick(self, master_cycles: int) -> int:
        """
        Tick駆動実行
        
        Args:
            master_cycles: 実行するマスタークロックサイクル数
            
        Returns:
            実際に消費されたサイクル数
            
        Raises:
            DeviceError: サイクル数が無効な場合
        """
        if master_cycles < 0:
            raise DeviceError(f"master_cycles must be non-negative, got {master_cycles}")
        
        try:
            return self._core.tick(master_cycles)
        except Exception as e:
            raise DeviceError(f"Tick execution failed: {e}") from e
    
    def read(self, address: int) -> int:
        """
        レジスタ読み込み
        
        Args:
            address: レジスタアドレス (0-15)
            
        Returns:
            レジスタ値 (0-255)
            
        Raises:
            DeviceError: 無効なアドレスの場合
        """
        if not (0 <= address < self._register_count):
            raise DeviceError(f"Register address {address} out of range [0, {self._register_count-1}]")
        
        try:
            return self._core.read_register(address)
        except Exception as e:
            raise DeviceError(f"Register read failed at address {address}: {e}") from e
    
    def write(self, address: int, value: int) -> None:
        """
        レジスタ書き込み
        
        Args:
            address: レジスタアドレス (0-15)
            value: 書き込み値 (0-255)
            
        Raises:
            DeviceError: 無効なアドレスまたは値の場合
        """
        if not (0 <= address < self._register_count):
            raise DeviceError(f"Register address {address} out of range [0, {self._register_count-1}]")
        
        if not (0 <= value <= 255):
            raise DeviceError(f"Register value {value} out of range [0, 255]")
        
        try:
            self._core.write_register(address, value)
        except Exception as e:
            raise DeviceError(f"Register write failed at address {address}: {e}") from e
    
    def get_state(self) -> Dict[str, Any]:
        """
        状態シリアライズ
        
        Returns:
            デバイスの完全な内部状態を含む辞書
        """
        try:
            state = self._core.get_state()
            
            # API準拠のため、追加のメタデータを含める
            state['device_type'] = 'AY-3-8910'
            state['api_version'] = '1.0'
            state['register_count'] = self._register_count
            
            return state
        except Exception as e:
            raise DeviceError(f"State serialization failed: {e}") from e
    
    def set_state(self, state: Dict[str, Any]) -> None:
        """
        状態復元
        
        Args:
            state: get_stateで取得した状態辞書
            
        Raises:
            DeviceError: 状態が無効な場合
        """
        # 基本的な検証
        if not isinstance(state, dict):
            raise DeviceError("State must be a dictionary")
        
        # デバイスタイプの検証
        if state.get('device_type') != 'AY-3-8910':
            raise DeviceError(f"Invalid device type: {state.get('device_type')}")
        
        try:
            self._core.set_state(state)
            
            if self._config.enable_debug:
                print(f"[DEBUG] {self.name} state restored successfully")
        except Exception as e:
            raise DeviceError(f"State restoration failed: {e}") from e
    
    def get_audio_buffer(self, samples: int) -> bytes:
        """
        オーディオバッファ取得
        
        Args:
            samples: 要求するサンプル数
            
        Returns:
            オーディオサンプルのバイトバッファ
            フォーマット: 16ビット符号付きリトルエンディアン、モノラル
            
        Raises:
            DeviceError: サンプル数が無効な場合
        """
        if samples < 0:
            raise DeviceError(f"Sample count must be non-negative, got {samples}")
        
        if samples == 0:
            return bytes()
        
        try:
            # サンプルを生成
            audio_samples = []
            
            for _ in range(samples):
                # 1サンプル分の時間進行
                # サンプルレートに基づいてクロックサイクル数を計算
                cycles_per_sample = int(self._config.effective_clock_frequency / self._config.sample_rate)
                
                # デバイスを進行
                self._core.tick(cycles_per_sample)
                
                # 音声出力を取得
                output = self._core.get_mixed_output()
                
                # -1.0〜1.0の範囲を16ビット符号付き整数に変換
                sample_value = int(output * 32767)
                sample_value = max(-32768, min(32767, sample_value))
                
                audio_samples.append(sample_value)
            
            # バイトバッファに変換（リトルエンディアン）
            buffer = bytearray()
            for sample in audio_samples:
                # 16ビット符号付きリトルエンディアン
                buffer.extend(sample.to_bytes(2, byteorder='little', signed=True))
            
            return bytes(buffer)
            
        except Exception as e:
            raise DeviceError(f"Audio buffer generation failed: {e}") from e
    
    # 追加のヘルパーメソッド（統一API外）
    
    def get_core(self) -> AY38910Core:
        """
        内部のAY38910Coreインスタンスを取得
        
        Returns:
            AY38910Core: 内部コアインスタンス
            
        Note:
            これは統一API外のヘルパーメソッドです。
            デバッグや詳細制御が必要な場合にのみ使用してください。
        """
        return self._core
    
    def get_config(self) -> AY38910Config:
        """
        デバイス設定を取得
        
        Returns:
            AY38910Config: デバイス設定
        """
        return self._config
    
    def get_register_info(self, address: int) -> Dict[str, Any]:
        """
        レジスタ詳細情報を取得
        
        Args:
            address: レジスタアドレス
            
        Returns:
            レジスタ情報辞書
            
        Raises:
            DeviceError: 無効なアドレスの場合
        """
        if not (0 <= address < self._register_count):
            raise DeviceError(f"Register address {address} out of range [0, {self._register_count-1}]")
        
        try:
            return self._core.get_register_info(address)
        except Exception as e:
            raise DeviceError(f"Register info retrieval failed: {e}") from e
    
    def get_channel_info(self, channel: int) -> Dict[str, Any]:
        """
        チャンネル詳細情報を取得
        
        Args:
            channel: チャンネル番号 (0-2)
            
        Returns:
            チャンネル情報辞書
            
        Raises:
            DeviceError: 無効なチャンネルの場合
        """
        if not (0 <= channel <= 2):
            raise DeviceError(f"Channel {channel} out of range [0, 2]")
        
        try:
            return self._core.get_channel_info(channel)
        except Exception as e:
            raise DeviceError(f"Channel info retrieval failed: {e}") from e
    
    def __str__(self) -> str:
        """文字列表現"""
        return f"AY38910Device({self.name})"
    
    def __repr__(self) -> str:
        """詳細文字列表現"""
        return f"AY38910Device(name='{self.name}', config={self._config})"
