"""
レジスタビューア実装

AY-3-8910のレジスタ表示・解析機能を提供
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from ..api.device import AY38910Device
from ..core.types import RegisterAccessError


@dataclass
class RegisterInfo:
    """レジスタ情報"""
    address: int
    name: str
    value: int
    hex_value: str
    binary_value: str
    description: str
    decoded_info: Optional[Dict[str, Any]] = None


class RegisterViewer:
    """
    レジスタビューア
    
    AY-3-8910のレジスタ表示・解析機能を提供する。
    レジスタの詳細情報、デコード結果、関連情報などを表示。
    """
    
    def __init__(self, device: AY38910Device):
        """
        レジスタビューア初期化
        
        Args:
            device: 対象のAY38910Device
        """
        self._device = device
        
        # レジスタ名定義
        self._register_names = {
            0: "Tone A Fine Tune",
            1: "Tone A Coarse Tune", 
            2: "Tone B Fine Tune",
            3: "Tone B Coarse Tune",
            4: "Tone C Fine Tune",
            5: "Tone C Coarse Tune",
            6: "Noise Period",
            7: "Mixer Control",
            8: "Volume A",
            9: "Volume B",
            10: "Volume C",
            11: "Envelope Fine Tune",
            12: "Envelope Coarse Tune",
            13: "Envelope Shape",
            14: "I/O Port A",
            15: "I/O Port B"
        }
        
        # レジスタ説明
        self._register_descriptions = {
            0: "Channel A tone frequency (fine tune, 8 bits)",
            1: "Channel A tone frequency (coarse tune, 4 bits)",
            2: "Channel B tone frequency (fine tune, 8 bits)",
            3: "Channel B tone frequency (coarse tune, 4 bits)",
            4: "Channel C tone frequency (fine tune, 8 bits)",
            5: "Channel C tone frequency (coarse tune, 4 bits)",
            6: "Noise generator frequency (5 bits)",
            7: "Mixer control and I/O enable",
            8: "Channel A volume control",
            9: "Channel B volume control",
            10: "Channel C volume control",
            11: "Envelope frequency (fine tune, 8 bits)",
            12: "Envelope frequency (coarse tune, 8 bits)",
            13: "Envelope shape control",
            14: "I/O Port A data",
            15: "I/O Port B data"
        }
        
        print("[DEBUG] RegisterViewer initialized")
    
    def display_registers(self) -> str:
        """
        全レジスタ表示（16進数）
        
        Returns:
            レジスタ表示文字列
        """
        lines = []
        lines.append("AY-3-8910 Registers (Hexadecimal)")
        lines.append("=" * 50)
        
        for i in range(16):
            try:
                value = self._device.read(i)
                name = self._register_names.get(i, f"Register {i}")
                lines.append(f"R{i:02d}: 0x{value:02X} ({value:3d}) - {name}")
            except Exception as e:
                lines.append(f"R{i:02d}: ERROR - {e}")
        
        return "\n".join(lines)
    
    def display_registers_binary(self) -> str:
        """
        全レジスタ表示（2進数）
        
        Returns:
            レジスタ表示文字列（2進数）
        """
        lines = []
        lines.append("AY-3-8910 Registers (Binary)")
        lines.append("=" * 60)
        
        for i in range(16):
            try:
                value = self._device.read(i)
                name = self._register_names.get(i, f"Register {i}")
                lines.append(f"R{i:02d}: {value:08b} (0x{value:02X}) - {name}")
            except Exception as e:
                lines.append(f"R{i:02d}: ERROR - {e}")
        
        return "\n".join(lines)
    
    def decode_register(self, address: int) -> str:
        """
        レジスタデコード表示
        
        Args:
            address: レジスタアドレス (0-15)
            
        Returns:
            デコード結果文字列
            
        Raises:
            RegisterAccessError: 無効なアドレスの場合
        """
        if not (0 <= address <= 15):
            raise RegisterAccessError(f"Register address {address} out of range [0, 15]")
        
        try:
            value = self._device.read(address)
            name = self._register_names.get(address, f"Register {address}")
            description = self._register_descriptions.get(address, "No description")
            
            lines = []
            lines.append(f"Register R{address:02d} Decode")
            lines.append("-" * 30)
            lines.append(f"Name: {name}")
            lines.append(f"Value: 0x{value:02X} ({value}) = {value:08b}b")
            lines.append(f"Description: {description}")
            lines.append("")
            
            # レジスタ別の詳細デコード
            decoded_info = self._decode_register_details(address, value)
            if decoded_info:
                lines.append("Detailed Analysis:")
                for key, val in decoded_info.items():
                    lines.append(f"  {key}: {val}")
            
            return "\n".join(lines)
            
        except Exception as e:
            return f"Error decoding R{address:02d}: {e}"
    
    def _decode_register_details(self, address: int, value: int) -> Dict[str, Any]:
        """レジスタ別の詳細デコード"""
        
        if address in [0, 2, 4]:  # Tone Fine Tune
            channel = ['A', 'B', 'C'][address // 2]
            return {
                f"Channel {channel} Fine Tune": f"{value} (8-bit value)",
                "Effect": "Lower 8 bits of tone period"
            }
        
        elif address in [1, 3, 5]:  # Tone Coarse Tune
            channel = ['A', 'B', 'C'][(address - 1) // 2]
            coarse = value & 0x0F
            return {
                f"Channel {channel} Coarse Tune": f"{coarse} (4-bit value)",
                "Unused bits": f"Bits 7-4 = {(value >> 4):04b}b (ignored)",
                "Effect": "Upper 4 bits of tone period"
            }
        
        elif address == 6:  # Noise Period
            noise_period = value & 0x1F
            return {
                "Noise Period": f"{noise_period} (5-bit value)",
                "Unused bits": f"Bits 7-5 = {(value >> 5):03b}b (ignored)",
                "Frequency": f"Clock / (16 × {noise_period})" if noise_period > 0 else "Clock / 16"
            }
        
        elif address == 7:  # Mixer Control
            return self._decode_mixer_control(value)
        
        elif address in [8, 9, 10]:  # Volume
            channel = ['A', 'B', 'C'][address - 8]
            return self._decode_volume_register(value, channel)
        
        elif address in [11, 12]:  # Envelope Period
            part = "Fine" if address == 11 else "Coarse"
            return {
                f"Envelope {part} Tune": f"{value} (8-bit value)",
                "Effect": f"{'Lower' if address == 11 else 'Upper'} 8 bits of envelope period"
            }
        
        elif address == 13:  # Envelope Shape
            return self._decode_envelope_shape(value)
        
        elif address in [14, 15]:  # I/O Ports
            port = 'A' if address == 14 else 'B'
            return {
                f"I/O Port {port} Data": f"0x{value:02X}",
                "Bit pattern": f"{value:08b}b",
                "Note": "Actual I/O depends on mixer control register"
            }
        
        return {}
    
    def _decode_mixer_control(self, value: int) -> Dict[str, Any]:
        """ミキサー制御レジスタのデコード"""
        return {
            "Tone A Enable": "OFF" if (value & 0x01) else "ON",
            "Tone B Enable": "OFF" if (value & 0x02) else "ON", 
            "Tone C Enable": "OFF" if (value & 0x04) else "ON",
            "Noise A Enable": "OFF" if (value & 0x08) else "ON",
            "Noise B Enable": "OFF" if (value & 0x10) else "ON",
            "Noise C Enable": "OFF" if (value & 0x20) else "ON",
            "I/O Port A": "OUTPUT" if (value & 0x40) else "INPUT",
            "I/O Port B": "OUTPUT" if (value & 0x80) else "INPUT",
            "Binary": f"{value:08b}b"
        }
    
    def _decode_volume_register(self, value: int, channel: str) -> Dict[str, Any]:
        """音量レジスタのデコード"""
        envelope_mode = bool(value & 0x10)
        volume_level = value & 0x0F
        
        result = {
            f"Channel {channel} Volume Mode": "ENVELOPE" if envelope_mode else "FIXED",
            "Envelope bit (bit 4)": "1" if envelope_mode else "0"
        }
        
        if envelope_mode:
            result["Volume Control"] = "Controlled by envelope generator"
            result["Volume bits (3-0)"] = f"{volume_level} (ignored in envelope mode)"
        else:
            result["Volume Level"] = f"{volume_level}/15"
            result["Volume bits (3-0)"] = f"{volume_level:04b}b"
        
        return result
    
    def _decode_envelope_shape(self, value: int) -> Dict[str, Any]:
        """エンベロープ形状レジスタのデコード"""
        shape = value & 0x0F
        
        # エンベロープ形状の説明
        shape_descriptions = {
            0x00: "\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\  (single decay)",
            0x01: "\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\  (single decay)",
            0x02: "\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\  (single decay)",
            0x03: "\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\  (single decay)",
            0x04: "/|/|/|/|/|/|/|/|  (sawtooth)",
            0x05: "/|/|/|/|/|/|/|/|  (sawtooth)",
            0x06: "/|/|/|/|/|/|/|/|  (sawtooth)",
            0x07: "/|/|/|/|/|/|/|/|  (sawtooth)",
            0x08: "\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\  (single decay)",
            0x09: "\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\  (single decay)",
            0x0A: "\\/\\/\\/\\/\\/\\/\\/\\/  (triangle)",
            0x0B: "\\‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾  (decay then hold)",
            0x0C: "/|/|/|/|/|/|/|/|  (sawtooth)",
            0x0D: "/‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾  (attack then hold)",
            0x0E: "/\\/\\/\\/\\/\\/\\/\\/\\  (triangle)",
            0x0F: "/|/|/|/|/|/|/|/|  (sawtooth)"
        }
        
        return {
            "Shape Value": f"0x{shape:X} ({shape})",
            "Shape Pattern": shape_descriptions.get(shape, "Unknown"),
            "Continue (bit 3)": "1" if (shape & 0x08) else "0",
            "Attack (bit 2)": "1" if (shape & 0x04) else "0", 
            "Alternate (bit 1)": "1" if (shape & 0x02) else "0",
            "Hold (bit 0)": "1" if (shape & 0x01) else "0",
            "Unused bits": f"Bits 7-4 = {(value >> 4):04b}b (ignored)"
        }
    
    def get_register_value(self, address: int) -> int:
        """
        レジスタ値取得
        
        Args:
            address: レジスタアドレス (0-15)
            
        Returns:
            レジスタ値
            
        Raises:
            RegisterAccessError: 無効なアドレスの場合
        """
        if not (0 <= address <= 15):
            raise RegisterAccessError(f"Register address {address} out of range [0, 15]")
        
        return self._device.read(address)
    
    def get_register_info(self, address: int) -> RegisterInfo:
        """
        レジスタ情報取得
        
        Args:
            address: レジスタアドレス (0-15)
            
        Returns:
            RegisterInfo: レジスタ情報オブジェクト
            
        Raises:
            RegisterAccessError: 無効なアドレスの場合
        """
        if not (0 <= address <= 15):
            raise RegisterAccessError(f"Register address {address} out of range [0, 15]")
        
        try:
            value = self._device.read(address)
            name = self._register_names.get(address, f"Register {address}")
            description = self._register_descriptions.get(address, "No description")
            decoded_info = self._decode_register_details(address, value)
            
            return RegisterInfo(
                address=address,
                name=name,
                value=value,
                hex_value=f"0x{value:02X}",
                binary_value=f"{value:08b}b",
                description=description,
                decoded_info=decoded_info
            )
            
        except Exception as e:
            raise RegisterAccessError(f"Failed to get register info for R{address}: {e}")
    
    def get_all_registers_info(self) -> List[RegisterInfo]:
        """
        全レジスタ情報取得
        
        Returns:
            全レジスタのRegisterInfoリスト
        """
        registers = []
        
        for address in range(16):
            try:
                registers.append(self.get_register_info(address))
            except Exception as e:
                # エラーの場合はダミー情報を作成
                registers.append(RegisterInfo(
                    address=address,
                    name=f"Register {address}",
                    value=0,
                    hex_value="ERROR",
                    binary_value="ERROR",
                    description=f"Error: {e}"
                ))
        
        return registers
    
    def get_tone_info(self) -> Dict[str, Any]:
        """
        トーン情報取得
        
        Returns:
            全チャンネルのトーン情報
        """
        tone_info = {}
        
        for channel in range(3):
            channel_name = ['A', 'B', 'C'][channel]
            
            try:
                fine_reg = channel * 2
                coarse_reg = channel * 2 + 1
                
                fine = self._device.read(fine_reg)
                coarse = self._device.read(coarse_reg) & 0x0F
                
                period = (coarse << 8) | fine
                frequency = 0.0
                
                if period > 0:
                    # 仮のクロック周波数を使用（実際の値は設定から取得）
                    clock_freq = 1000000  # 1MHz
                    frequency = clock_freq / (16 * period)
                
                tone_info[channel_name] = {
                    'fine_tune': fine,
                    'coarse_tune': coarse,
                    'period': period,
                    'frequency_hz': frequency,
                    'registers': {
                        'fine': fine_reg,
                        'coarse': coarse_reg
                    }
                }
                
            except Exception as e:
                tone_info[channel_name] = {'error': str(e)}
        
        return tone_info
    
    def get_volume_info(self) -> Dict[str, Any]:
        """
        音量情報取得
        
        Returns:
            全チャンネルの音量情報
        """
        volume_info = {}
        
        for channel in range(3):
            channel_name = ['A', 'B', 'C'][channel]
            
            try:
                volume_reg = 8 + channel
                value = self._device.read(volume_reg)
                
                envelope_mode = bool(value & 0x10)
                volume_level = value & 0x0F
                
                volume_info[channel_name] = {
                    'register': volume_reg,
                    'raw_value': value,
                    'envelope_mode': envelope_mode,
                    'volume_level': volume_level,
                    'volume_percent': (volume_level / 15.0) * 100 if not envelope_mode else None
                }
                
            except Exception as e:
                volume_info[channel_name] = {'error': str(e)}
        
        return volume_info
    
    def __str__(self) -> str:
        """文字列表現"""
        return f"RegisterViewer(device={self._device.name})"
    
    def __repr__(self) -> str:
        """詳細文字列表現"""
        return f"RegisterViewer(device={self._device})"


# ファクトリ関数

def create_register_viewer(device: AY38910Device) -> RegisterViewer:
    """
    RegisterViewerを作成
    
    Args:
        device: 対象デバイス
        
    Returns:
        RegisterViewerインスタンス
    """
    return RegisterViewer(device)
