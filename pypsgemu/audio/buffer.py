"""
音声バッファ管理モジュール

AY-3-8910エミュレータの音声出力用循環バッファを提供します。
リアルタイム音声再生のためのサンプルバッファ管理機能を実装しています。
"""

import threading
from typing import Optional, List
import numpy as np
from ..core.types import AY38910Error


class AudioBufferError(AY38910Error):
    """音声バッファ関連のエラー"""
    pass


class AudioBuffer:
    """音声サンプル用循環バッファ
    
    リアルタイム音声再生のためのスレッドセーフな循環バッファを提供します。
    プロデューサー（サンプル生成）とコンシューマー（音声出力）間の
    データ受け渡しを効率的に行います。
    """
    
    def __init__(self, size: int, channels: int = 1, dtype=np.float32):
        """AudioBufferを初期化
        
        Args:
            size: バッファサイズ（サンプル数）
            channels: チャンネル数（1=モノラル、2=ステレオ）
            dtype: サンプルデータ型
            
        Raises:
            AudioBufferError: 無効なパラメータが指定された場合
        """
        if size <= 0:
            raise AudioBufferError(f"Buffer size must be positive, got {size}")
        if channels not in (1, 2):
            raise AudioBufferError(f"Channels must be 1 or 2, got {channels}")
        
        self._size = size
        self._channels = channels
        self._dtype = dtype
        
        # 循環バッファ
        if channels == 1:
            self._buffer = np.zeros(size, dtype=dtype)
        else:
            self._buffer = np.zeros((size, channels), dtype=dtype)
        
        # バッファ制御変数
        self._write_pos = 0
        self._read_pos = 0
        self._available_samples = 0
        
        # スレッド同期
        self._lock = threading.RLock()
        self._not_empty = threading.Condition(self._lock)
        self._not_full = threading.Condition(self._lock)
        
        # 統計情報
        self._underruns = 0
        self._overruns = 0
        self._total_written = 0
        self._total_read = 0
    
    @property
    def size(self) -> int:
        """バッファサイズを取得"""
        return self._size
    
    @property
    def channels(self) -> int:
        """チャンネル数を取得"""
        return self._channels
    
    @property
    def dtype(self):
        """データ型を取得"""
        return self._dtype
    
    def get_available_samples(self) -> int:
        """利用可能なサンプル数を取得
        
        Returns:
            読み取り可能なサンプル数
        """
        with self._lock:
            return self._available_samples
    
    def get_free_space(self) -> int:
        """空き容量を取得
        
        Returns:
            書き込み可能なサンプル数
        """
        with self._lock:
            return self._size - self._available_samples
    
    def is_empty(self) -> bool:
        """バッファが空かどうかを確認
        
        Returns:
            バッファが空の場合True
        """
        with self._lock:
            return self._available_samples == 0
    
    def is_full(self) -> bool:
        """バッファが満杯かどうかを確認
        
        Returns:
            バッファが満杯の場合True
        """
        with self._lock:
            return self._available_samples >= self._size
    
    def write(self, samples: np.ndarray, timeout: Optional[float] = None) -> int:
        """サンプルをバッファに書き込み
        
        Args:
            samples: 書き込むサンプルデータ
            timeout: タイムアウト時間（秒）、Noneで無制限
            
        Returns:
            実際に書き込まれたサンプル数
            
        Raises:
            AudioBufferError: データ形式が不正な場合
        """
        if samples.size == 0:
            return 0
        
        # データ形式チェック
        if self._channels == 1:
            if samples.ndim != 1:
                raise AudioBufferError(f"Expected 1D array for mono, got {samples.ndim}D")
            samples_to_write = len(samples)
        else:
            if samples.ndim != 2 or samples.shape[1] != self._channels:
                raise AudioBufferError(
                    f"Expected ({self._channels},) shape for stereo, got {samples.shape}"
                )
            samples_to_write = samples.shape[0]
        
        with self._not_full:
            # 空きスペースを待つ
            while self.get_free_space() == 0:
                if not self._not_full.wait(timeout):
                    return 0  # タイムアウト
            
            # 書き込み可能なサンプル数を計算
            free_space = self.get_free_space()
            write_count = min(samples_to_write, free_space)
            
            if write_count == 0:
                return 0
            
            # 循環バッファに書き込み
            if self._channels == 1:
                self._write_mono_samples(samples[:write_count])
            else:
                self._write_stereo_samples(samples[:write_count])
            
            self._available_samples += write_count
            self._total_written += write_count
            
            # オーバーラン検出
            if write_count < samples_to_write:
                self._overruns += 1
            
            # 読み取り待ちスレッドに通知
            self._not_empty.notify_all()
            
            return write_count
    
    def read(self, count: int, timeout: Optional[float] = None) -> Optional[np.ndarray]:
        """サンプルをバッファから読み取り
        
        Args:
            count: 読み取るサンプル数
            timeout: タイムアウト時間（秒）、Noneで無制限
            
        Returns:
            読み取ったサンプルデータ、タイムアウト時はNone
        """
        if count <= 0:
            return np.array([], dtype=self._dtype)
        
        with self._not_empty:
            # データが利用可能になるまで待つ
            while self._available_samples == 0:
                if not self._not_empty.wait(timeout):
                    return None  # タイムアウト
            
            # 読み取り可能なサンプル数を計算
            available = self._available_samples
            read_count = min(count, available)
            
            if read_count == 0:
                return np.array([], dtype=self._dtype)
            
            # 循環バッファから読み取り
            if self._channels == 1:
                result = self._read_mono_samples(read_count)
            else:
                result = self._read_stereo_samples(read_count)
            
            self._available_samples -= read_count
            self._total_read += read_count
            
            # アンダーラン検出
            if read_count < count:
                self._underruns += 1
            
            # 書き込み待ちスレッドに通知
            self._not_full.notify_all()
            
            return result
    
    def _write_mono_samples(self, samples: np.ndarray) -> None:
        """モノラルサンプルを循環バッファに書き込み"""
        count = len(samples)
        end_pos = self._write_pos + count
        
        if end_pos <= self._size:
            # 一度に書き込み可能
            self._buffer[self._write_pos:end_pos] = samples
        else:
            # バッファ境界をまたぐ場合
            first_part = self._size - self._write_pos
            self._buffer[self._write_pos:] = samples[:first_part]
            self._buffer[:count - first_part] = samples[first_part:]
        
        self._write_pos = end_pos % self._size
    
    def _write_stereo_samples(self, samples: np.ndarray) -> None:
        """ステレオサンプルを循環バッファに書き込み"""
        count = samples.shape[0]
        end_pos = self._write_pos + count
        
        if end_pos <= self._size:
            # 一度に書き込み可能
            self._buffer[self._write_pos:end_pos] = samples
        else:
            # バッファ境界をまたぐ場合
            first_part = self._size - self._write_pos
            self._buffer[self._write_pos:] = samples[:first_part]
            self._buffer[:count - first_part] = samples[first_part:]
        
        self._write_pos = end_pos % self._size
    
    def _read_mono_samples(self, count: int) -> np.ndarray:
        """モノラルサンプルを循環バッファから読み取り"""
        result = np.zeros(count, dtype=self._dtype)
        end_pos = self._read_pos + count
        
        if end_pos <= self._size:
            # 一度に読み取り可能
            result[:] = self._buffer[self._read_pos:end_pos]
        else:
            # バッファ境界をまたぐ場合
            first_part = self._size - self._read_pos
            result[:first_part] = self._buffer[self._read_pos:]
            result[first_part:] = self._buffer[:count - first_part]
        
        self._read_pos = end_pos % self._size
        return result
    
    def _read_stereo_samples(self, count: int) -> np.ndarray:
        """ステレオサンプルを循環バッファから読み取り"""
        result = np.zeros((count, self._channels), dtype=self._dtype)
        end_pos = self._read_pos + count
        
        if end_pos <= self._size:
            # 一度に読み取り可能
            result[:] = self._buffer[self._read_pos:end_pos]
        else:
            # バッファ境界をまたぐ場合
            first_part = self._size - self._read_pos
            result[:first_part] = self._buffer[self._read_pos:]
            result[first_part:] = self._buffer[:count - first_part]
        
        self._read_pos = end_pos % self._size
        return result
    
    def clear(self) -> None:
        """バッファをクリア"""
        with self._lock:
            self._write_pos = 0
            self._read_pos = 0
            self._available_samples = 0
            self._buffer.fill(0)
            
            # 待機中のスレッドに通知
            self._not_empty.notify_all()
            self._not_full.notify_all()
    
    def get_audio_buffer(self, count: int = None) -> Optional[np.ndarray]:
        """音声バッファの内容を取得（デバッグ・可視化用）
        
        Args:
            count: 取得するサンプル数（Noneで全バッファ）
            
        Returns:
            バッファ内容のコピー
        """
        with self._lock:
            if count is None:
                count = self._available_samples
            
            if count <= 0 or self._available_samples == 0:
                if self._channels == 1:
                    return np.array([], dtype=self._dtype)
                else:
                    return np.array([], dtype=self._dtype).reshape(0, self._channels)
            
            # 実際に取得するサンプル数
            actual_count = min(count, self._available_samples)
            
            # 循環バッファから読み取り（コピー）
            if self._channels == 1:
                result = self._peek_mono_samples(actual_count)
            else:
                result = self._peek_stereo_samples(actual_count)
            
            return result
    
    def _peek_mono_samples(self, count: int) -> np.ndarray:
        """モノラルサンプルを循環バッファから覗き見（読み取り位置は変更しない）"""
        result = np.zeros(count, dtype=self._dtype)
        read_pos = self._read_pos
        end_pos = read_pos + count
        
        if end_pos <= self._size:
            # 一度に読み取り可能
            result[:] = self._buffer[read_pos:end_pos]
        else:
            # バッファ境界をまたぐ場合
            first_part = self._size - read_pos
            result[:first_part] = self._buffer[read_pos:]
            result[first_part:] = self._buffer[:count - first_part]
        
        return result
    
    def _peek_stereo_samples(self, count: int) -> np.ndarray:
        """ステレオサンプルを循環バッファから覗き見（読み取り位置は変更しない）"""
        result = np.zeros((count, self._channels), dtype=self._dtype)
        read_pos = self._read_pos
        end_pos = read_pos + count
        
        if end_pos <= self._size:
            # 一度に読み取り可能
            result[:] = self._buffer[read_pos:end_pos]
        else:
            # バッファ境界をまたぐ場合
            first_part = self._size - read_pos
            result[:first_part] = self._buffer[read_pos:]
            result[first_part:] = self._buffer[:count - first_part]
        
        return result
    
    def get_buffer_utilization_history(self, samples: int = 100) -> List[float]:
        """バッファ利用率の履歴を取得（最適化用）
        
        Args:
            samples: 履歴サンプル数
            
        Returns:
            利用率履歴のリスト
        """
        # 簡易実装：現在の利用率のみ返す（将来的に履歴機能を追加可能）
        with self._lock:
            current_utilization = self._available_samples / self._size
            return [current_utilization] * min(samples, 1)
    
    def optimize_buffer_size(self, target_latency_ms: float, sample_rate: int) -> int:
        """最適なバッファサイズを計算
        
        Args:
            target_latency_ms: 目標レイテンシ（ミリ秒）
            sample_rate: サンプルレート
            
        Returns:
            推奨バッファサイズ
        """
        # 目標レイテンシに基づく基本サイズ
        base_size = int(sample_rate * target_latency_ms / 1000.0)
        
        # 2の累乗に調整（効率的なメモリアクセスのため）
        optimal_size = 1
        while optimal_size < base_size:
            optimal_size *= 2
        
        # 最小・最大制限
        optimal_size = max(64, min(optimal_size, 16384))
        
        return optimal_size
    
    def get_statistics(self) -> dict:
        """バッファ統計情報を取得
        
        Returns:
            統計情報辞書
        """
        with self._lock:
            return {
                'size': self._size,
                'channels': self._channels,
                'available_samples': self._available_samples,
                'free_space': self.get_free_space(),
                'utilization': self._available_samples / self._size,
                'underruns': self._underruns,
                'overruns': self._overruns,
                'total_written': self._total_written,
                'total_read': self._total_read,
                'write_pos': self._write_pos,
                'read_pos': self._read_pos,
                'memory_usage_bytes': self._buffer.nbytes,
                'efficiency_score': self._calculate_efficiency_score()
            }
    
    def _calculate_efficiency_score(self) -> float:
        """バッファ効率スコアを計算（0.0-1.0）"""
        if self._total_written == 0:
            return 1.0
        
        # アンダーラン・オーバーランの影響を考慮
        error_rate = (self._underruns + self._overruns) / max(1, self._total_written // self._size)
        efficiency = max(0.0, 1.0 - error_rate * 0.1)  # エラー1回につき10%減点
        
        return efficiency
    
    def reset_statistics(self) -> None:
        """統計情報をリセット"""
        with self._lock:
            self._underruns = 0
            self._overruns = 0
            self._total_written = 0
            self._total_read = 0


def create_audio_buffer(sample_rate: int, buffer_duration: float = 0.1, 
                       channels: int = 1) -> AudioBuffer:
    """標準的な音声バッファを作成
    
    Args:
        sample_rate: サンプルレート（Hz）
        buffer_duration: バッファ持続時間（秒）
        channels: チャンネル数
        
    Returns:
        AudioBufferインスタンス
    """
    buffer_size = int(sample_rate * buffer_duration)
    return AudioBuffer(buffer_size, channels)
