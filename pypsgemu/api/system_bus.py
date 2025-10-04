"""
AY-3-8910 システムバス実装

SystemBus プロトコルに準拠したシステムバス実装
"""

from typing import Dict, Any, Optional, Tuple, List
from .protocols import SystemBus, Device, AddressError, DeviceError


class DeviceMapping:
    """デバイスマッピング情報"""
    
    def __init__(self, device: Device, base_address: int, size: int):
        self.device = device
        self.base_address = base_address
        self.size = size
        self.end_address = base_address + size - 1
    
    def contains_address(self, address: int) -> bool:
        """指定アドレスがこのマッピング範囲に含まれるかチェック"""
        return self.base_address <= address <= self.end_address
    
    def get_relative_address(self, address: int) -> int:
        """グローバルアドレスを相対アドレスに変換"""
        if not self.contains_address(address):
            raise AddressError(f"Address 0x{address:04X} not in range [0x{self.base_address:04X}, 0x{self.end_address:04X}]")
        return address - self.base_address
    
    def __str__(self) -> str:
        return f"DeviceMapping({self.device.name}, 0x{self.base_address:04X}-0x{self.end_address:04X})"


class AY38910SystemBus(SystemBus):
    """
    AY-3-8910システムバス実装
    
    SystemBusプロトコルに準拠したシステムバス実装。
    複数のデバイスをアドレス空間にマッピングし、
    アドレス解決とルーティングを行う。
    """
    
    def __init__(self, enable_debug: bool = False) -> None:
        """
        システムバス初期化
        
        Args:
            enable_debug: デバッグ出力を有効にするか
        """
        self._mappings: List[DeviceMapping] = []
        self._enable_debug = enable_debug
        
        # 統計情報
        self._stats = {
            'read_count': 0,
            'write_count': 0,
            'address_errors': 0,
            'device_errors': 0
        }
        
        if enable_debug:
            print("[DEBUG] AY38910SystemBus initialized")
    
    def map_device(self, device: Device, base_address: int, size: int) -> None:
        """
        デバイスをシステムアドレス空間にマッピング
        
        Args:
            device: マッピングするデバイス
            base_address: ベースアドレス
            size: マッピングサイズ（バイト数）
            
        Raises:
            DeviceError: マッピングが重複する場合
        """
        if size <= 0:
            raise DeviceError(f"Mapping size must be positive, got {size}")
        
        if base_address < 0:
            raise DeviceError(f"Base address must be non-negative, got {base_address}")
        
        # 重複チェック
        new_mapping = DeviceMapping(device, base_address, size)
        
        for existing in self._mappings:
            # 範囲の重複をチェック
            if (new_mapping.base_address <= existing.end_address and
                new_mapping.end_address >= existing.base_address):
                raise DeviceError(
                    f"Address range overlap: new mapping 0x{new_mapping.base_address:04X}-0x{new_mapping.end_address:04X} "
                    f"overlaps with existing {existing}"
                )
        
        # マッピングを追加
        self._mappings.append(new_mapping)
        
        # アドレス順にソート（検索効率のため）
        self._mappings.sort(key=lambda m: m.base_address)
        
        if self._enable_debug:
            print(f"[DEBUG] Device mapped: {device.name} at 0x{base_address:04X}-0x{new_mapping.end_address:04X}")
    
    def unmap_device(self, device: Device) -> bool:
        """
        デバイスのマッピングを削除
        
        Args:
            device: 削除するデバイス
            
        Returns:
            削除に成功した場合True
        """
        original_count = len(self._mappings)
        self._mappings = [m for m in self._mappings if m.device != device]
        
        removed = len(self._mappings) < original_count
        
        if removed and self._enable_debug:
            print(f"[DEBUG] Device unmapped: {device.name}")
        
        return removed
    
    def read(self, address: int) -> int:
        """
        システムアドレスから読み込み
        
        Args:
            address: システムアドレス
            
        Returns:
            読み込み値 (0-255)
            
        Raises:
            AddressError: アドレスが無効な場合
            DeviceError: デバイス操作が失敗した場合
        """
        self._stats['read_count'] += 1
        
        try:
            device, relative_addr = self._resolve_address(address)
            
            if device is None:
                self._stats['address_errors'] += 1
                raise AddressError(f"No device mapped at address 0x{address:04X}")
            
            value = device.read(relative_addr)
            
            if self._enable_debug:
                print(f"[DEBUG] Bus read: 0x{address:04X} -> {device.name}[0x{relative_addr:02X}] = 0x{value:02X}")
            
            return value
            
        except AddressError:
            raise
        except Exception as e:
            self._stats['device_errors'] += 1
            raise DeviceError(f"Read failed at address 0x{address:04X}: {e}") from e
    
    def write(self, address: int, value: int) -> None:
        """
        システムアドレスに書き込み
        
        Args:
            address: システムアドレス
            value: 書き込み値 (0-255)
            
        Raises:
            AddressError: アドレスが無効な場合
            DeviceError: デバイス操作が失敗した場合
        """
        if not (0 <= value <= 255):
            raise DeviceError(f"Write value {value} out of range [0, 255]")
        
        self._stats['write_count'] += 1
        
        try:
            device, relative_addr = self._resolve_address(address)
            
            if device is None:
                self._stats['address_errors'] += 1
                raise AddressError(f"No device mapped at address 0x{address:04X}")
            
            if self._enable_debug:
                print(f"[DEBUG] Bus write: 0x{address:04X} -> {device.name}[0x{relative_addr:02X}] = 0x{value:02X}")
            
            device.write(relative_addr, value)
            
        except AddressError:
            raise
        except Exception as e:
            self._stats['device_errors'] += 1
            raise DeviceError(f"Write failed at address 0x{address:04X}: {e}") from e
    
    def _resolve_address(self, address: int) -> Tuple[Optional[Device], int]:
        """
        アドレスを対象デバイスと相対アドレスに解決
        
        Args:
            address: システムアドレス
            
        Returns:
            (デバイス, 相対アドレス) のタプル
            デバイスが見つからない場合は (None, 0)
        """
        for mapping in self._mappings:
            if mapping.contains_address(address):
                relative_addr = mapping.get_relative_address(address)
                return mapping.device, relative_addr
        
        return None, 0
    
    def get_mappings(self) -> List[Dict[str, Any]]:
        """
        現在のデバイスマッピング情報を取得
        
        Returns:
            マッピング情報のリスト
        """
        return [
            {
                'device_name': mapping.device.name,
                'base_address': mapping.base_address,
                'end_address': mapping.end_address,
                'size': mapping.size,
                'address_range': f"0x{mapping.base_address:04X}-0x{mapping.end_address:04X}"
            }
            for mapping in self._mappings
        ]
    
    def get_device_at_address(self, address: int) -> Optional[Device]:
        """
        指定アドレスにマッピングされているデバイスを取得
        
        Args:
            address: システムアドレス
            
        Returns:
            デバイス（見つからない場合はNone）
        """
        device, _ = self._resolve_address(address)
        return device
    
    def get_stats(self) -> Dict[str, Any]:
        """
        システムバス統計情報を取得
        
        Returns:
            統計情報辞書
        """
        return {
            'mappings_count': len(self._mappings),
            'read_count': self._stats['read_count'],
            'write_count': self._stats['write_count'],
            'total_operations': self._stats['read_count'] + self._stats['write_count'],
            'address_errors': self._stats['address_errors'],
            'device_errors': self._stats['device_errors'],
            'error_rate': (self._stats['address_errors'] + self._stats['device_errors']) / 
                         max(1, self._stats['read_count'] + self._stats['write_count'])
        }
    
    def reset_stats(self) -> None:
        """統計情報をリセット"""
        self._stats = {
            'read_count': 0,
            'write_count': 0,
            'address_errors': 0,
            'device_errors': 0
        }
        
        if self._enable_debug:
            print("[DEBUG] SystemBus stats reset")
    
    def dump_memory_map(self) -> str:
        """
        メモリマップの文字列表現を生成
        
        Returns:
            メモリマップの文字列
        """
        if not self._mappings:
            return "Memory Map: (empty)"
        
        lines = ["Memory Map:"]
        lines.append("-" * 60)
        lines.append(f"{'Address Range':<20} {'Size':<8} {'Device':<20}")
        lines.append("-" * 60)
        
        for mapping in self._mappings:
            address_range = f"0x{mapping.base_address:04X}-0x{mapping.end_address:04X}"
            size_str = f"{mapping.size}B"
            lines.append(f"{address_range:<20} {size_str:<8} {mapping.device.name:<20}")
        
        lines.append("-" * 60)
        
        return "\n".join(lines)
    
    def validate_mappings(self) -> List[str]:
        """
        マッピングの整合性を検証
        
        Returns:
            検証エラーのリスト（エラーがない場合は空リスト）
        """
        errors = []
        
        # 重複チェック
        for i, mapping1 in enumerate(self._mappings):
            for j, mapping2 in enumerate(self._mappings[i+1:], i+1):
                if (mapping1.base_address <= mapping2.end_address and
                    mapping1.end_address >= mapping2.base_address):
                    errors.append(
                        f"Address overlap between {mapping1.device.name} "
                        f"(0x{mapping1.base_address:04X}-0x{mapping1.end_address:04X}) and "
                        f"{mapping2.device.name} (0x{mapping2.base_address:04X}-0x{mapping2.end_address:04X})"
                    )
        
        # アドレス範囲の妥当性チェック
        for mapping in self._mappings:
            if mapping.base_address > mapping.end_address:
                errors.append(f"Invalid address range for {mapping.device.name}: "
                            f"base (0x{mapping.base_address:04X}) > end (0x{mapping.end_address:04X})")
        
        return errors
    
    def __str__(self) -> str:
        """文字列表現"""
        return f"AY38910SystemBus({len(self._mappings)} mappings)"
    
    def __repr__(self) -> str:
        """詳細文字列表現"""
        return f"AY38910SystemBus(mappings={len(self._mappings)}, debug={self._enable_debug})"


# ファクトリ関数

def create_system_bus(enable_debug: bool = False) -> AY38910SystemBus:
    """
    AY38910SystemBusを作成
    
    Args:
        enable_debug: デバッグ出力を有効にするか
        
    Returns:
        AY38910SystemBusインスタンス
    """
    return AY38910SystemBus(enable_debug)


def create_simple_system(device: Device, base_address: int = 0x0000, 
                        size: int = 16, enable_debug: bool = False) -> AY38910SystemBus:
    """
    単一デバイス用の簡単なシステムバスを作成
    
    Args:
        device: マッピングするデバイス
        base_address: ベースアドレス
        size: マッピングサイズ
        enable_debug: デバッグ出力を有効にするか
        
    Returns:
        設定済みのAY38910SystemBusインスタンス
    """
    bus = AY38910SystemBus(enable_debug)
    bus.map_device(device, base_address, size)
    return bus
