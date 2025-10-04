"""
PyPSGEmu - 統一デバイスAPI層

このモジュールは、統一デバイスAPIプロトコルに準拠した
AY-3-8910デバイス実装を提供します。

主要コンポーネント:
- AY38910Device: Device プロトコル実装
- AY38910AudioDevice: AudioDevice プロトコル実装  
- AY38910SystemBus: SystemBus プロトコル実装

プロトコル定義:
- Device, AudioDevice, SystemBus: 統一デバイスAPIプロトコル
- DeviceError, AddressError: API例外クラス

ファクトリ関数:
- create_device: AY38910Device作成
- create_audio_device: AY38910AudioDevice作成
- create_system_bus: AY38910SystemBus作成
- create_simple_system: 単一デバイスシステム作成
"""

# プロトコル定義
from .protocols import (
    Device, AudioDevice, SystemBus, DeviceConfig,
    InterruptController, InterruptLine, InterruptVector,
    DeviceError, AddressError
)

# 実装クラス
from .device import AY38910Device
from .audio_device import AY38910AudioDevice, create_audio_device, create_audio_device_with_sample_rate
from .system_bus import AY38910SystemBus, create_system_bus, create_simple_system

# ファクトリ関数
def create_device(config=None):
    """AY38910Deviceを作成"""
    if config is None:
        from ..core.device_config import create_default_config
        config = create_default_config()
    return AY38910Device(config)

def create_debug_device():
    """デバッグ機能付きAY38910Deviceを作成"""
    from ..core.device_config import create_debug_config
    config = create_debug_config()
    return AY38910Device(config)

__all__ = [
    # プロトコル
    'Device', 'AudioDevice', 'SystemBus', 'DeviceConfig',
    'InterruptController', 'InterruptLine', 'InterruptVector',
    'DeviceError', 'AddressError',
    
    # 実装クラス
    'AY38910Device', 'AY38910AudioDevice', 'AY38910SystemBus',
    
    # ファクトリ関数
    'create_device', 'create_debug_device',
    'create_audio_device', 'create_audio_device_with_sample_rate',
    'create_system_bus', 'create_simple_system'
]
