"""
デバッグエンジン実装

ブレークポイント、ステップ実行、状態監視などの
デバッグ機能を提供するエンジン
"""

from typing import Dict, Any, Optional, Callable, List
from enum import Enum, auto
from dataclasses import dataclass
from ..api.device import AY38910Device
from ..core.types import RegisterAccessError, InvalidValueError


class DebugState(Enum):
    """デバッグ状態"""
    RUNNING = auto()      # 通常実行中
    PAUSED = auto()       # 一時停止中
    STEP_MODE = auto()    # ステップ実行モード
    BREAKPOINT_HIT = auto() # ブレークポイントヒット


@dataclass
class BreakpointCondition:
    """ブレークポイント条件"""
    register: int
    condition: Optional[str] = None  # 条件式（例: "== 0x80", "> 100"）
    enabled: bool = True
    hit_count: int = 0
    
    def evaluate(self, value: int) -> bool:
        """条件を評価"""
        if not self.enabled:
            return False
        
        if self.condition is None:
            return True  # 無条件ブレーク
        
        try:
            # 簡単な条件式の評価
            condition = self.condition.strip()
            
            if condition.startswith('=='):
                target = int(condition[2:].strip(), 0)
                return value == target
            elif condition.startswith('!='):
                target = int(condition[2:].strip(), 0)
                return value != target
            elif condition.startswith('>='):
                target = int(condition[2:].strip(), 0)
                return value >= target
            elif condition.startswith('<='):
                target = int(condition[2:].strip(), 0)
                return value <= target
            elif condition.startswith('>'):
                target = int(condition[1:].strip(), 0)
                return value > target
            elif condition.startswith('<'):
                target = int(condition[1:].strip(), 0)
                return value < target
            else:
                # 単純な値比較
                target = int(condition, 0)
                return value == target
                
        except (ValueError, IndexError):
            return False


class DebugEngine:
    """
    デバッグエンジン
    
    AY-3-8910エミュレータのデバッグ機能を提供する。
    ブレークポイント、ステップ実行、状態監視などをサポート。
    """
    
    def __init__(self, device: AY38910Device):
        """
        デバッグエンジン初期化
        
        Args:
            device: デバッグ対象のAY38910Device
        """
        self._device = device
        self._state = DebugState.RUNNING
        
        # ブレークポイント管理
        self._breakpoints: Dict[int, BreakpointCondition] = {}
        
        # ステップ実行制御
        self._step_count = 0
        self._step_target = 0
        
        # コールバック
        self._breakpoint_callback: Optional[Callable[[int, int], None]] = None
        self._step_callback: Optional[Callable[[], None]] = None
        
        # 実行統計
        self._stats = {
            'total_ticks': 0,
            'breakpoint_hits': 0,
            'steps_executed': 0,
            'register_watches': 0
        }
        
        # レジスタ監視
        self._register_watch: Dict[int, int] = {}  # {register: last_value}
        self._register_change_callback: Optional[Callable[[int, int, int], None]] = None
        
        print("[DEBUG] DebugEngine initialized")
    
    @property
    def state(self) -> DebugState:
        """現在のデバッグ状態を取得"""
        return self._state
    
    @property
    def device(self) -> AY38910Device:
        """デバッグ対象デバイスを取得"""
        return self._device
    
    def set_breakpoint(self, register: int, condition: str = None) -> None:
        """
        ブレークポイント設定
        
        Args:
            register: レジスタ番号 (0-15)
            condition: ブレーク条件（例: "== 0x80", "> 100"）
            
        Raises:
            RegisterAccessError: 無効なレジスタ番号の場合
        """
        if not (0 <= register <= 15):
            raise RegisterAccessError(f"無効なレジスタ番号: {register}")
        
        self._breakpoints[register] = BreakpointCondition(register, condition)
        
        print(f"[DEBUG] Breakpoint set on R{register}" + 
              (f" with condition '{condition}'" if condition else ""))
    
    def clear_breakpoint(self, register: int) -> bool:
        """
        ブレークポイント削除
        
        Args:
            register: レジスタ番号 (0-15)
            
        Returns:
            削除に成功した場合True
        """
        if register in self._breakpoints:
            del self._breakpoints[register]
            print(f"[DEBUG] Breakpoint cleared on R{register}")
            return True
        return False
    
    def clear_all_breakpoints(self) -> int:
        """
        全ブレークポイント削除
        
        Returns:
            削除されたブレークポイント数
        """
        count = len(self._breakpoints)
        self._breakpoints.clear()
        print(f"[DEBUG] All {count} breakpoints cleared")
        return count
    
    def enable_breakpoint(self, register: int, enabled: bool = True) -> bool:
        """
        ブレークポイントの有効/無効切り替え
        
        Args:
            register: レジスタ番号
            enabled: 有効にするかどうか
            
        Returns:
            操作に成功した場合True
        """
        if register in self._breakpoints:
            self._breakpoints[register].enabled = enabled
            status = "enabled" if enabled else "disabled"
            print(f"[DEBUG] Breakpoint on R{register} {status}")
            return True
        return False
    
    def should_break(self, register: int = None, value: int = None) -> bool:
        """
        ブレークポイント条件チェック
        
        Args:
            register: チェックするレジスタ番号
            value: レジスタ値
            
        Returns:
            ブレークすべき場合True
        """
        # ステップモードの場合
        if self._state == DebugState.STEP_MODE:
            return True
        
        # 特定レジスタのチェック
        if register is not None and value is not None:
            if register in self._breakpoints:
                bp = self._breakpoints[register]
                if bp.evaluate(value):
                    bp.hit_count += 1
                    self._stats['breakpoint_hits'] += 1
                    return True
        
        return False
    
    def step(self, count: int = 1) -> None:
        """
        ステップ実行開始
        
        Args:
            count: ステップ数（デフォルト: 1）
        """
        if count <= 0:
            raise InvalidValueError(f"Step count must be positive, got {count}")
        
        self._state = DebugState.STEP_MODE
        self._step_count = 0
        self._step_target = count
        
        print(f"[DEBUG] Step execution started: {count} steps")
    
    def continue_execution(self) -> None:
        """実行継続"""
        self._state = DebugState.RUNNING
        print("[DEBUG] Execution continued")
    
    def pause(self) -> None:
        """実行一時停止"""
        self._state = DebugState.PAUSED
        print("[DEBUG] Execution paused")
    
    def tick_with_debug(self, master_cycles: int) -> int:
        """
        デバッグ機能付きTick実行
        
        Args:
            master_cycles: 実行するマスタークロックサイクル数
            
        Returns:
            実際に消費されたサイクル数
        """
        if self._state == DebugState.PAUSED:
            return 0
        
        # レジスタ変更の監視
        self._check_register_changes()
        
        # デバイスのTick実行
        consumed = self._device.tick(master_cycles)
        self._stats['total_ticks'] += consumed
        
        # ステップモードの処理
        if self._state == DebugState.STEP_MODE:
            self._step_count += 1
            self._stats['steps_executed'] += 1
            
            if self._step_count >= self._step_target:
                self._state = DebugState.PAUSED
                print(f"[DEBUG] Step execution completed: {self._step_count} steps")
                
                if self._step_callback:
                    self._step_callback()
        
        return consumed
    
    def check_register_breakpoint(self, register: int, old_value: int, new_value: int) -> bool:
        """
        レジスタ書き込み時のブレークポイントチェック
        
        Args:
            register: レジスタ番号
            old_value: 変更前の値
            new_value: 変更後の値
            
        Returns:
            ブレークした場合True
        """
        if self.should_break(register, new_value):
            self._state = DebugState.BREAKPOINT_HIT
            print(f"[DEBUG] Breakpoint hit on R{register}: 0x{old_value:02X} -> 0x{new_value:02X}")
            
            if self._breakpoint_callback:
                self._breakpoint_callback(register, new_value)
            
            return True
        
        return False
    
    def _check_register_changes(self) -> None:
        """レジスタ変更の監視"""
        for register in range(16):
            try:
                current_value = self._device.read(register)
                
                if register in self._register_watch:
                    old_value = self._register_watch[register]
                    if current_value != old_value:
                        self._stats['register_watches'] += 1
                        
                        if self._register_change_callback:
                            self._register_change_callback(register, old_value, current_value)
                
                self._register_watch[register] = current_value
                
            except Exception:
                # レジスタ読み込みエラーは無視
                pass
    
    def add_register_watch(self, register: int) -> None:
        """
        レジスタ監視追加
        
        Args:
            register: 監視するレジスタ番号
        """
        if not (0 <= register <= 15):
            raise RegisterAccessError(f"無効なレジスタ番号: {register}")
        
        try:
            current_value = self._device.read(register)
            self._register_watch[register] = current_value
            print(f"[DEBUG] Register watch added: R{register}")
        except Exception as e:
            print(f"[DEBUG] Failed to add register watch: {e}")
    
    def remove_register_watch(self, register: int) -> bool:
        """
        レジスタ監視削除
        
        Args:
            register: レジスタ番号
            
        Returns:
            削除に成功した場合True
        """
        if register in self._register_watch:
            del self._register_watch[register]
            print(f"[DEBUG] Register watch removed: R{register}")
            return True
        return False
    
    def set_breakpoint_callback(self, callback: Callable[[int, int], None]) -> None:
        """ブレークポイントコールバック設定"""
        self._breakpoint_callback = callback
    
    def set_step_callback(self, callback: Callable[[], None]) -> None:
        """ステップ実行コールバック設定"""
        self._step_callback = callback
    
    def set_register_change_callback(self, callback: Callable[[int, int, int], None]) -> None:
        """レジスタ変更コールバック設定"""
        self._register_change_callback = callback
    
    def get_state(self) -> Dict[str, Any]:
        """デバッグエンジンの状態を取得"""
        return {
            'debug_state': self._state.name,
            'breakpoints': {
                reg: {
                    'condition': bp.condition,
                    'enabled': bp.enabled,
                    'hit_count': bp.hit_count
                }
                for reg, bp in self._breakpoints.items()
            },
            'step_info': {
                'current_count': self._step_count,
                'target_count': self._step_target,
                'in_step_mode': self._state == DebugState.STEP_MODE
            },
            'statistics': self._stats.copy(),
            'watched_registers': list(self._register_watch.keys())
        }
    
    def get_breakpoints(self) -> List[Dict[str, Any]]:
        """ブレークポイント一覧を取得"""
        return [
            {
                'register': reg,
                'condition': bp.condition,
                'enabled': bp.enabled,
                'hit_count': bp.hit_count
            }
            for reg, bp in self._breakpoints.items()
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        return self._stats.copy()
    
    def reset_stats(self) -> None:
        """統計情報をリセット"""
        self._stats = {
            'total_ticks': 0,
            'breakpoint_hits': 0,
            'steps_executed': 0,
            'register_watches': 0
        }
        
        # ブレークポイントのヒット数もリセット
        for bp in self._breakpoints.values():
            bp.hit_count = 0
        
        print("[DEBUG] Debug statistics reset")
    
    def __str__(self) -> str:
        """文字列表現"""
        return f"DebugEngine(state={self._state.name}, breakpoints={len(self._breakpoints)})"
    
    def __repr__(self) -> str:
        """詳細文字列表現"""
        return (f"DebugEngine(state={self._state.name}, "
                f"breakpoints={len(self._breakpoints)}, "
                f"device={self._device})")


# ファクトリ関数

def create_debug_engine(device: AY38910Device) -> DebugEngine:
    """
    DebugEngineを作成
    
    Args:
        device: デバッグ対象デバイス
        
    Returns:
        DebugEngineインスタンス
    """
    return DebugEngine(device)
