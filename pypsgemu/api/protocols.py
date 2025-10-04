"""
統一デバイスAPIプロトコル定義

device_if_api_requirements.mdに基づく標準プロトコル定義
"""

from typing import Protocol, Dict, Any, Optional, Tuple
from abc import abstractmethod


class DeviceConfig(Protocol):
    """デバイス設定の基底プロトコル"""
    device_id: str


class Device(Protocol):
    """
    全てのエミュレート対象デバイスが実装すべき基本プロトコル
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """デバイスの人間が読める名前"""
        ...
    
    @abstractmethod
    def reset(self) -> None:
        """デバイスをパワーオンリセット状態にする"""
        ...
    
    @abstractmethod
    def tick(self, master_cycles: int) -> int:
        """
        指定されたマスターサイクル数だけデバイスの状態を進め、
        実際に消費したサイクル数を返す
        """
        ...
    
    @abstractmethod
    def read(self, address: int) -> int:
        """
        デバイスのメモリマップ空間から1バイトを読み出す
        addressはデバイスのベースアドレスからのオフセット
        """
        ...
    
    @abstractmethod
    def write(self, address: int, value: int) -> None:
        """
        デバイスのメモリマップ空間に1バイトを書き込む
        addressはデバイスのベースアドレスからのオフセット
        """
        ...
    
    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        """
        デバイスの現在の内部状態をシリアライズ可能な辞書として返す
        """
        ...
    
    @abstractmethod
    def set_state(self, state: Dict[str, Any]) -> None:
        """
        辞書からデバイスの内部状態を復元する
        """
        ...


class AudioDevice(Protocol):
    """
    オーディオ出力機能を持つデバイスのプロトコル
    """
    
    @abstractmethod
    def get_audio_buffer(self, samples: int) -> bytes:
        """
        生成されたオーディオサンプルのバッファを返す
        フォーマットはデバイス設定の一部として定義される
        """
        ...


class SystemBus(Protocol):
    """
    システムバス管理プロトコル
    """
    
    @abstractmethod
    def map_device(self, device: Device, base_address: int, size: int) -> None:
        """デバイスをシステムアドレス空間にマッピング"""
        ...
    
    @abstractmethod
    def read(self, address: int) -> int:
        """システムアドレスから読み込み"""
        ...
    
    @abstractmethod
    def write(self, address: int, value: int) -> None:
        """システムアドレスに書き込み"""
        ...
    
    @abstractmethod
    def _resolve_address(self, address: int) -> Tuple[Optional[Device], int]:
        """アドレスを対象デバイスと相対アドレスに解決"""
        ...


class InterruptLine:
    """割り込み線識別子"""
    pass


class InterruptVector:
    """CPUに渡される割り込み情報"""
    
    def __init__(self, vector_address: int, line: InterruptLine):
        self.vector_address = vector_address
        self.line = line


class InterruptController(Protocol):
    """
    割り込み管理プロトコル
    """
    
    @abstractmethod
    def request(self, line: InterruptLine) -> None:
        """割り込み要求をアサート"""
        ...
    
    @abstractmethod
    def clear(self, line: InterruptLine) -> None:
        """割り込み要求をクリア"""
        ...
    
    @abstractmethod
    def is_pending(self) -> bool:
        """保留中の割り込みがあるかチェック"""
        ...
    
    @abstractmethod
    def acknowledge(self) -> Optional[InterruptVector]:
        """最優先割り込みを処理対象として返す"""
        ...


# エラークラス
class AddressError(Exception):
    """アドレス解決エラー"""
    pass


class DeviceError(Exception):
    """デバイス操作エラー"""
    pass
