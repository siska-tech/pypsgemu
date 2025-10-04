"""
状態スナップショット管理モジュール

AY-3-8910エミュレータの状態保存・復元機能を提供します。
レジスタ状態の保存・読込、「パッチ」管理機能を実装しています。
"""

import json
import os
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pathlib import Path
from ..core.types import AY38910Error, AY38910State
from ..api.device import Device


class StateManagerError(AY38910Error):
    """状態管理関連のエラー"""
    pass


class StateSnapshot:
    """状態スナップショット
    
    AY-3-8910の特定時点での状態を保存するクラス。
    レジスタ値、内部状態、メタデータを含みます。
    """
    
    def __init__(self, name: str, state: Dict[str, Any], metadata: Dict[str, Any] = None):
        """StateSnapshotを初期化
        
        Args:
            name: スナップショット名
            state: 保存する状態辞書
            metadata: メタデータ（作成日時、説明など）
        """
        self.name = name
        self.state = state.copy()
        self.metadata = metadata or {}
        
        # 自動メタデータ
        if 'created_at' not in self.metadata:
            self.metadata['created_at'] = datetime.now().isoformat()
        if 'version' not in self.metadata:
            self.metadata['version'] = '1.0'
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式にシリアライズ"""
        return {
            'name': self.name,
            'state': self.state,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StateSnapshot':
        """辞書からデシリアライズ"""
        return cls(
            name=data['name'],
            state=data['state'],
            metadata=data.get('metadata', {})
        )


class StatePatch:
    """状態パッチ
    
    状態の差分を表現するクラス。
    特定のレジスタのみの変更を効率的に管理します。
    """
    
    def __init__(self, name: str, register_changes: Dict[int, int], description: str = ""):
        """StatePatchを初期化
        
        Args:
            name: パッチ名
            register_changes: レジスタ変更辞書 {address: value}
            description: パッチの説明
        """
        self.name = name
        self.register_changes = register_changes.copy()
        self.description = description
        self.created_at = datetime.now().isoformat()
    
    def apply_to_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """状態にパッチを適用
        
        Args:
            state: 適用対象の状態
            
        Returns:
            パッチ適用後の状態
        """
        new_state = state.copy()
        
        # レジスタ変更を適用
        if 'registers' in new_state:
            registers = new_state['registers'].copy()
            for address, value in self.register_changes.items():
                if 0 <= address <= 15:
                    registers[address] = value
            new_state['registers'] = registers
        
        return new_state
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式にシリアライズ"""
        return {
            'name': self.name,
            'register_changes': self.register_changes,
            'description': self.description,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StatePatch':
        """辞書からデシリアライズ"""
        patch = cls(
            name=data['name'],
            register_changes=data['register_changes'],
            description=data.get('description', '')
        )
        patch.created_at = data.get('created_at', datetime.now().isoformat())
        return patch


class StateManager:
    """状態管理マネージャー
    
    AY-3-8910エミュレータの状態スナップショット機能を提供します。
    状態の保存・復元、パッチ管理、ファイルI/O処理を行います。
    """
    
    def __init__(self, base_directory: str = "states"):
        """StateManagerを初期化
        
        Args:
            base_directory: 状態ファイルの保存ディレクトリ
        """
        self.base_directory = Path(base_directory)
        self.base_directory.mkdir(exist_ok=True)
        
        # 内部管理
        self._snapshots: Dict[str, StateSnapshot] = {}
        self._patches: Dict[str, StatePatch] = {}
        self._current_snapshot: Optional[str] = None
        
        # 統計情報
        self._stats = {
            'snapshots_created': 0,
            'snapshots_loaded': 0,
            'patches_applied': 0,
            'files_saved': 0,
            'files_loaded': 0
        }
    
    def create_snapshot(self, device: Device, name: str, description: str = "") -> StateSnapshot:
        """デバイス状態のスナップショットを作成
        
        Args:
            device: 状態を取得するデバイス
            name: スナップショット名
            description: スナップショットの説明
            
        Returns:
            作成されたStateSnapshot
            
        Raises:
            StateManagerError: スナップショット作成に失敗した場合
        """
        try:
            # デバイスから状態を取得
            state = device.get_state()
            
            # メタデータを作成
            metadata = {
                'description': description,
                'device_name': getattr(device, 'name', 'Unknown'),
                'created_at': datetime.now().isoformat(),
                'version': '1.0'
            }
            
            # スナップショットを作成
            snapshot = StateSnapshot(name, state, metadata)
            
            # 内部管理に追加
            self._snapshots[name] = snapshot
            self._current_snapshot = name
            
            # 統計更新
            self._stats['snapshots_created'] += 1
            
            return snapshot
            
        except Exception as e:
            raise StateManagerError(f"Failed to create snapshot '{name}': {e}")
    
    def restore_snapshot(self, device: Device, name: str) -> None:
        """スナップショットをデバイスに復元
        
        Args:
            device: 復元対象のデバイス
            name: 復元するスナップショット名
            
        Raises:
            StateManagerError: 復元に失敗した場合
        """
        if name not in self._snapshots:
            raise StateManagerError(f"Snapshot '{name}' not found")
        
        try:
            snapshot = self._snapshots[name]
            device.set_state(snapshot.state)
            self._current_snapshot = name
            
        except Exception as e:
            raise StateManagerError(f"Failed to restore snapshot '{name}': {e}")
    
    def create_patch(self, name: str, register_changes: Dict[int, int], description: str = "") -> StatePatch:
        """レジスタ変更パッチを作成
        
        Args:
            name: パッチ名
            register_changes: レジスタ変更辞書 {address: value}
            description: パッチの説明
            
        Returns:
            作成されたStatePatch
            
        Raises:
            StateManagerError: パッチ作成に失敗した場合
        """
        # レジスタアドレスの検証
        for address in register_changes.keys():
            if not (0 <= address <= 15):
                raise StateManagerError(f"Invalid register address: {address}")
        
        # レジスタ値の検証
        for value in register_changes.values():
            if not (0 <= value <= 255):
                raise StateManagerError(f"Invalid register value: {value}")
        
        patch = StatePatch(name, register_changes, description)
        self._patches[name] = patch
        
        return patch
    
    def apply_patch(self, device: Device, patch_name: str) -> None:
        """パッチをデバイスに適用
        
        Args:
            device: 適用対象のデバイス
            patch_name: 適用するパッチ名
            
        Raises:
            StateManagerError: パッチ適用に失敗した場合
        """
        if patch_name not in self._patches:
            raise StateManagerError(f"Patch '{patch_name}' not found")
        
        try:
            patch = self._patches[patch_name]
            
            # レジスタ変更を適用
            for address, value in patch.register_changes.items():
                device.write_register(address, value)
            
            # 統計更新
            self._stats['patches_applied'] += 1
            
        except Exception as e:
            raise StateManagerError(f"Failed to apply patch '{patch_name}': {e}")
    
    def save_snapshot_to_file(self, snapshot_name: str, filename: str = None) -> str:
        """スナップショットをファイルに保存
        
        Args:
            snapshot_name: 保存するスナップショット名
            filename: 保存ファイル名（Noneで自動生成）
            
        Returns:
            保存されたファイルパス
            
        Raises:
            StateManagerError: 保存に失敗した場合
        """
        if snapshot_name not in self._snapshots:
            raise StateManagerError(f"Snapshot '{snapshot_name}' not found")
        
        if filename is None:
            filename = f"{snapshot_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = self.base_directory / filename
        
        try:
            snapshot = self._snapshots[snapshot_name]
            data = {
                'type': 'snapshot',
                'data': snapshot.to_dict()
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # 統計更新
            self._stats['files_saved'] += 1
            
            return str(filepath)
            
        except Exception as e:
            raise StateManagerError(f"Failed to save snapshot to '{filepath}': {e}")
    
    def load_snapshot_from_file(self, filepath: str) -> str:
        """ファイルからスナップショットを読み込み
        
        Args:
            filepath: 読み込むファイルパス
            
        Returns:
            読み込まれたスナップショット名
            
        Raises:
            StateManagerError: 読み込みに失敗した場合
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise StateManagerError(f"File not found: {filepath}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if data.get('type') != 'snapshot':
                raise StateManagerError(f"Invalid file format: {filepath}")
            
            snapshot = StateSnapshot.from_dict(data['data'])
            self._snapshots[snapshot.name] = snapshot
            
            # 統計更新
            self._stats['snapshots_loaded'] += 1
            self._stats['files_loaded'] += 1
            
            return snapshot.name
            
        except json.JSONDecodeError as e:
            raise StateManagerError(f"Invalid JSON in file '{filepath}': {e}")
        except Exception as e:
            raise StateManagerError(f"Failed to load snapshot from '{filepath}': {e}")
    
    def save_patch_to_file(self, patch_name: str, filename: str = None) -> str:
        """パッチをファイルに保存
        
        Args:
            patch_name: 保存するパッチ名
            filename: 保存ファイル名（Noneで自動生成）
            
        Returns:
            保存されたファイルパス
            
        Raises:
            StateManagerError: 保存に失敗した場合
        """
        if patch_name not in self._patches:
            raise StateManagerError(f"Patch '{patch_name}' not found")
        
        if filename is None:
            filename = f"patch_{patch_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = self.base_directory / filename
        
        try:
            patch = self._patches[patch_name]
            data = {
                'type': 'patch',
                'data': patch.to_dict()
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # 統計更新
            self._stats['files_saved'] += 1
            
            return str(filepath)
            
        except Exception as e:
            raise StateManagerError(f"Failed to save patch to '{filepath}': {e}")
    
    def load_patch_from_file(self, filepath: str) -> str:
        """ファイルからパッチを読み込み
        
        Args:
            filepath: 読み込むファイルパス
            
        Returns:
            読み込まれたパッチ名
            
        Raises:
            StateManagerError: 読み込みに失敗した場合
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise StateManagerError(f"File not found: {filepath}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if data.get('type') != 'patch':
                raise StateManagerError(f"Invalid file format: {filepath}")
            
            patch = StatePatch.from_dict(data['data'])
            self._patches[patch.name] = patch
            
            # 統計更新
            self._stats['files_loaded'] += 1
            
            return patch.name
            
        except json.JSONDecodeError as e:
            raise StateManagerError(f"Invalid JSON in file '{filepath}': {e}")
        except Exception as e:
            raise StateManagerError(f"Failed to load patch from '{filepath}': {e}")
    
    def list_snapshots(self) -> List[Dict[str, Any]]:
        """スナップショット一覧を取得
        
        Returns:
            スナップショット情報のリスト
        """
        snapshots = []
        for name, snapshot in self._snapshots.items():
            info = {
                'name': name,
                'description': snapshot.metadata.get('description', ''),
                'created_at': snapshot.metadata.get('created_at', ''),
                'device_name': snapshot.metadata.get('device_name', ''),
                'is_current': name == self._current_snapshot
            }
            snapshots.append(info)
        
        return sorted(snapshots, key=lambda x: x['created_at'], reverse=True)
    
    def list_patches(self) -> List[Dict[str, Any]]:
        """パッチ一覧を取得
        
        Returns:
            パッチ情報のリスト
        """
        patches = []
        for name, patch in self._patches.items():
            info = {
                'name': name,
                'description': patch.description,
                'created_at': patch.created_at,
                'register_count': len(patch.register_changes),
                'registers': list(patch.register_changes.keys())
            }
            patches.append(info)
        
        return sorted(patches, key=lambda x: x['created_at'], reverse=True)
    
    def delete_snapshot(self, name: str) -> None:
        """スナップショットを削除
        
        Args:
            name: 削除するスナップショット名
            
        Raises:
            StateManagerError: 削除に失敗した場合
        """
        if name not in self._snapshots:
            raise StateManagerError(f"Snapshot '{name}' not found")
        
        del self._snapshots[name]
        
        if self._current_snapshot == name:
            self._current_snapshot = None
    
    def delete_patch(self, name: str) -> None:
        """パッチを削除
        
        Args:
            name: 削除するパッチ名
            
        Raises:
            StateManagerError: 削除に失敗した場合
        """
        if name not in self._patches:
            raise StateManagerError(f"Patch '{name}' not found")
        
        del self._patches[name]
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得
        
        Returns:
            統計情報辞書
        """
        return {
            'snapshots_count': len(self._snapshots),
            'patches_count': len(self._patches),
            'current_snapshot': self._current_snapshot,
            'base_directory': str(self.base_directory),
            'stats': self._stats.copy()
        }
    
    def clear_all(self) -> None:
        """すべてのスナップショットとパッチをクリア"""
        self._snapshots.clear()
        self._patches.clear()
        self._current_snapshot = None


# =============================================================================
# ファクトリ関数
# =============================================================================

def create_state_manager(base_directory: str = "states") -> StateManager:
    """StateManagerを作成
    
    Args:
        base_directory: 状態ファイルの保存ディレクトリ
        
    Returns:
        StateManagerインスタンス
    """
    return StateManager(base_directory)


def create_quick_patch(name: str, register_address: int, value: int, description: str = "") -> StatePatch:
    """単一レジスタ変更の簡易パッチを作成
    
    Args:
        name: パッチ名
        register_address: レジスタアドレス
        value: 設定値
        description: パッチの説明
        
    Returns:
        StatePatchインスタンス
    """
    return StatePatch(name, {register_address: value}, description)
