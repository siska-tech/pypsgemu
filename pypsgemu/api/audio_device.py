"""
AY-3-8910 オーディオデバイス実装

AudioDevice プロトコルに特化したAY-3-8910実装
"""

from typing import Dict, Any
from .protocols import AudioDevice, DeviceError
from .device import AY38910Device
from ..core.device_config import AY38910Config


class AY38910AudioDevice(AudioDevice):
    """
    AY-3-8910オーディオデバイス実装
    
    AudioDeviceプロトコルに特化したAY-3-8910の実装。
    音声出力機能に焦点を当てた軽量なインターフェイスを提供する。
    """
    
    def __init__(self, config: AY38910Config) -> None:
        """
        オーディオデバイス初期化
        
        Args:
            config: AY-3-8910設定オブジェクト
        """
        # 内部でAY38910Deviceを使用
        self._device = AY38910Device(config)
        self._config = config
        
        # オーディオ固有の設定
        self._sample_format = 'int16'  # 16ビット符号付き整数
        self._channels = 1  # モノラル
        self._bytes_per_sample = 2  # 16ビット = 2バイト
        
        if config.enable_debug:
            print(f"[DEBUG] AY38910AudioDevice initialized")
            print(f"[DEBUG] Sample rate: {config.sample_rate} Hz")
            print(f"[DEBUG] Format: {self._sample_format}, Channels: {self._channels}")
    
    @property
    def name(self) -> str:
        """デバイス名取得"""
        return f"{self._device.name} (Audio)"
    
    @property
    def sample_rate(self) -> int:
        """サンプルレート取得"""
        return self._config.sample_rate
    
    @property
    def sample_format(self) -> str:
        """サンプルフォーマット取得"""
        return self._sample_format
    
    @property
    def channels(self) -> int:
        """チャンネル数取得"""
        return self._channels
    
    @property
    def bytes_per_sample(self) -> int:
        """サンプルあたりのバイト数取得"""
        return self._bytes_per_sample
    
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
        return self._device.get_audio_buffer(samples)
    
    def get_audio_info(self) -> Dict[str, Any]:
        """
        オーディオ情報取得
        
        Returns:
            オーディオ設定情報辞書
        """
        return {
            'sample_rate': self.sample_rate,
            'sample_format': self.sample_format,
            'channels': self.channels,
            'bytes_per_sample': self.bytes_per_sample,
            'bit_depth': 16,
            'endianness': 'little',
            'signed': True
        }
    
    def get_buffer_info(self, samples: int) -> Dict[str, Any]:
        """
        バッファ情報取得
        
        Args:
            samples: サンプル数
            
        Returns:
            バッファ情報辞書
        """
        buffer_size = samples * self.bytes_per_sample * self.channels
        duration_ms = (samples / self.sample_rate) * 1000
        
        return {
            'samples': samples,
            'buffer_size_bytes': buffer_size,
            'duration_ms': duration_ms,
            'channels': self.channels,
            'bytes_per_sample': self.bytes_per_sample
        }
    
    def reset_audio(self) -> None:
        """
        オーディオ関連の状態をリセット
        """
        self._device.reset()
        
        if self._config.enable_debug:
            print(f"[DEBUG] {self.name} audio reset completed")
    
    def set_volume_scale(self, scale: float) -> None:
        """
        音量スケールを設定
        
        Args:
            scale: 音量スケール (0.0-1.0)
            
        Raises:
            DeviceError: スケール値が無効な場合
        """
        if not (0.0 <= scale <= 1.0):
            raise DeviceError(f"Volume scale must be in range [0.0, 1.0], got {scale}")
        
        # 設定を更新（実際の実装では設定オブジェクトを変更）
        if hasattr(self._config, 'volume_scale'):
            self._config.volume_scale = scale
        
        if self._config.enable_debug:
            print(f"[DEBUG] Volume scale set to {scale}")
    
    def get_channel_outputs(self) -> Dict[str, float]:
        """
        各チャンネルの個別出力を取得
        
        Returns:
            チャンネル別出力辞書 {'A': value, 'B': value, 'C': value}
        """
        try:
            outputs = self._device.get_core().get_channel_outputs()
            return {
                'A': outputs[0],
                'B': outputs[1], 
                'C': outputs[2]
            }
        except Exception as e:
            raise DeviceError(f"Channel outputs retrieval failed: {e}") from e
    
    def get_mixed_output(self) -> float:
        """
        ミックス済み音声出力を取得
        
        Returns:
            正規化された音声出力 (-1.0〜1.0)
        """
        try:
            return self._device.get_core().get_mixed_output()
        except Exception as e:
            raise DeviceError(f"Mixed output retrieval failed: {e}") from e
    
    def tick_audio(self, master_cycles: int) -> int:
        """
        オーディオ処理のためのTick実行
        
        Args:
            master_cycles: 実行するマスタークロックサイクル数
            
        Returns:
            実際に消費されたサイクル数
            
        Raises:
            DeviceError: サイクル数が無効な場合
        """
        return self._device.tick(master_cycles)
    
    def write_register(self, address: int, value: int) -> None:
        """
        レジスタ書き込み（オーディオ制御用）
        
        Args:
            address: レジスタアドレス (0-15)
            value: 書き込み値 (0-255)
            
        Raises:
            DeviceError: 無効なアドレスまたは値の場合
        """
        self._device.write(address, value)
    
    def read_register(self, address: int) -> int:
        """
        レジスタ読み込み（オーディオ状態確認用）
        
        Args:
            address: レジスタアドレス (0-15)
            
        Returns:
            レジスタ値 (0-255)
            
        Raises:
            DeviceError: 無効なアドレスの場合
        """
        return self._device.read(address)
    
    def get_device(self) -> AY38910Device:
        """
        内部のAY38910Deviceインスタンスを取得
        
        Returns:
            AY38910Device: 内部デバイスインスタンス
            
        Note:
            完全なデバイス機能が必要な場合に使用
        """
        return self._device
    
    def get_config(self) -> AY38910Config:
        """
        デバイス設定を取得
        
        Returns:
            AY38910Config: デバイス設定
        """
        return self._config
    
    def __str__(self) -> str:
        """文字列表現"""
        return f"AY38910AudioDevice({self.sample_rate}Hz, {self.sample_format})"
    
    def __repr__(self) -> str:
        """詳細文字列表現"""
        return (f"AY38910AudioDevice(sample_rate={self.sample_rate}, "
                f"format={self.sample_format}, channels={self.channels})")


# ファクトリ関数

def create_audio_device(config: AY38910Config = None) -> AY38910AudioDevice:
    """
    AY38910AudioDeviceを作成
    
    Args:
        config: デバイス設定 (Noneの場合はデフォルト作成)
        
    Returns:
        AY38910AudioDeviceインスタンス
    """
    if config is None:
        from ..core.device_config import create_default_config
        config = create_default_config()
    
    return AY38910AudioDevice(config)


def create_audio_device_with_sample_rate(sample_rate: int) -> AY38910AudioDevice:
    """
    指定サンプルレートでAY38910AudioDeviceを作成
    
    Args:
        sample_rate: サンプルレート (Hz)
        
    Returns:
        AY38910AudioDeviceインスタンス
    """
    from ..core.device_config import create_default_config
    config = create_default_config()
    config.sample_rate = sample_rate
    
    return AY38910AudioDevice(config)
