"""
音声ドライバモジュール

sounddeviceライブラリを使用したリアルタイム音声出力を提供します。
AY-3-8910エミュレータの音声をスピーカーから出力するための
コールバックベース音声再生システムを実装しています。
"""

import threading
import time
from typing import Optional, Callable, Dict, Any
import numpy as np

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    sd = None

from .buffer import AudioBuffer, create_audio_buffer
from .sample_generator import SampleGenerator, create_sample_generator
from ..core.ay38910 import AY38910Core
from ..core.types import AY38910Error, AudioDriverError


class AudioDriver:
    """リアルタイム音声出力ドライバ
    
    sounddeviceライブラリを使用してAY-3-8910エミュレータの
    音声をリアルタイムで出力します。コールバックベースの
    非同期音声再生を提供します。
    """
    
    def __init__(self, core: AY38910Core, sample_rate: int = 44100,
                 channels: int = 1, buffer_duration: float = 0.1,
                 device: Optional[int] = None, latency: Optional[float] = None):
        """AudioDriverを初期化
        
        Args:
            core: AY-3-8910エミュレータコア
            sample_rate: サンプルレート（Hz）
            channels: 出力チャンネル数（1=モノラル、2=ステレオ）
            buffer_duration: バッファ持続時間（秒）
            device: 音声デバイスID（Noneで自動選択）
            latency: 音声遅延（秒、Noneで自動）
            
        Raises:
            AudioDriverError: sounddeviceが利用できない場合
        """
        if not SOUNDDEVICE_AVAILABLE:
            raise AudioDriverError(
                "sounddevice library is not available. "
                "Install it with: pip install sounddevice"
            )
        
        self._core = core
        self._sample_rate = sample_rate
        self._channels = channels
        self._buffer_duration = buffer_duration
        self._device = device
        self._latency = latency
        
        # サンプル生成器を作成
        self._sample_generator = create_sample_generator(
            core, sample_rate, stereo=(channels == 2), output_gain=0.5
        )
        
        # 音声バッファを作成
        self._audio_buffer = create_audio_buffer(
            sample_rate, buffer_duration, channels
        )
        
        # 再生状態
        self._is_playing = False
        self._stream: Optional[sd.OutputStream] = None
        
        # バックグラウンド生成スレッド
        self._generator_thread: Optional[threading.Thread] = None
        self._stop_generation = threading.Event()
        
        # 統計情報
        self._callback_count = 0
        self._underrun_count = 0
        self._total_samples_played = 0
        self._start_time = 0.0
        
        # コールバック関数
        self._error_callback: Optional[Callable[[Exception], None]] = None
        self._status_callback: Optional[Callable[[str], None]] = None
        
        # デバッグ情報
        self._debug_enabled = core.get_config().enable_debug
        self._debug_info = {}
    
    @property
    def sample_rate(self) -> int:
        """サンプルレートを取得"""
        return self._sample_rate
    
    @property
    def channels(self) -> int:
        """チャンネル数を取得"""
        return self._channels
    
    @property
    def is_playing(self) -> bool:
        """再生中かどうかを確認"""
        return self._is_playing
    
    @property
    def sample_generator(self) -> SampleGenerator:
        """サンプル生成器を取得"""
        return self._sample_generator
    
    @property
    def audio_buffer(self) -> AudioBuffer:
        """音声バッファを取得"""
        return self._audio_buffer
    
    def set_error_callback(self, callback: Optional[Callable[[Exception], None]]) -> None:
        """エラーコールバックを設定
        
        Args:
            callback: エラー発生時に呼び出される関数
        """
        self._error_callback = callback
    
    def set_status_callback(self, callback: Optional[Callable[[str], None]]) -> None:
        """ステータスコールバックを設定
        
        Args:
            callback: ステータス変更時に呼び出される関数
        """
        self._status_callback = callback
    
    def start(self) -> None:
        """音声出力を開始
        
        Raises:
            AudioDriverError: 既に再生中の場合や初期化に失敗した場合
        """
        if self._is_playing:
            raise AudioDriverError("Audio driver is already playing")
        
        try:
            # 音声ストリームを作成
            self._stream = sd.OutputStream(
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype=np.float32,
                callback=self._audio_callback,
                device=self._device,
                latency=self._latency,
                blocksize=None  # sounddeviceに最適なブロックサイズを選択させる
            )
            
            # バックグラウンド生成スレッドを開始
            self._stop_generation.clear()
            self._generator_thread = threading.Thread(
                target=self._generation_loop,
                name="AudioSampleGenerator",
                daemon=True
            )
            
            # 統計情報をリセット
            self._reset_statistics()
            
            # ストリームを開始
            self._stream.start()
            self._generator_thread.start()
            
            self._is_playing = True
            self._start_time = time.time()
            
            if self._status_callback:
                self._status_callback("started")
            
            if self._debug_enabled:
                print(f"Audio driver started: {self._sample_rate}Hz, {self._channels}ch")
        
        except Exception as e:
            self._cleanup()
            error_msg = f"Failed to start audio driver: {e}"
            if self._error_callback:
                self._error_callback(AudioDriverError(error_msg))
            else:
                raise AudioDriverError(error_msg) from e
    
    def stop(self) -> None:
        """音声出力を停止"""
        if not self._is_playing:
            return
        
        self._is_playing = False
        
        # バックグラウンド生成を停止
        self._stop_generation.set()
        
        # ストリームを停止
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                if self._error_callback:
                    self._error_callback(e)
        
        # 生成スレッドの終了を待つ
        if self._generator_thread and self._generator_thread.is_alive():
            self._generator_thread.join(timeout=1.0)
        
        self._cleanup()
        
        if self._status_callback:
            self._status_callback("stopped")
        
        if self._debug_enabled:
            print("Audio driver stopped")
    
    def pause(self) -> None:
        """音声出力を一時停止"""
        if self._stream and self._is_playing:
            self._stream.stop()
            if self._status_callback:
                self._status_callback("paused")
    
    def resume(self) -> None:
        """音声出力を再開"""
        if self._stream and self._is_playing:
            self._stream.start()
            if self._status_callback:
                self._status_callback("resumed")
    
    def _audio_callback(self, outdata: np.ndarray, frames: int, 
                       time_info: Any, status: Any) -> None:
        """sounddevice音声コールバック
        
        Args:
            outdata: 出力バッファ
            frames: フレーム数
            time_info: タイミング情報
            status: ステータス情報
        """
        self._callback_count += 1
        
        try:
            # バッファからサンプルを読み取り
            samples = self._audio_buffer.read(frames, timeout=0.001)

            if samples is not None and len(samples) > 0:
                actual_frames = len(samples)

                if self._channels == 1:
                    outdata[:actual_frames, 0] = samples
                    if actual_frames < frames:
                        outdata[actual_frames:, 0] = 0
                else:
                    outdata[:actual_frames] = samples
                    if actual_frames < frames:
                        outdata[actual_frames:] = 0

                self._total_samples_played += actual_frames

                if actual_frames < frames:
                    self._underrun_count += 1
                    if self._debug_enabled:
                        print(f"Audio underrun #{self._underrun_count}: {actual_frames}/{frames}")
            else:
                # サンプルが全く取得できなかった
                outdata.fill(0)
                self._underrun_count += 1
                if self._debug_enabled:
                    print(f"Audio underrun #{self._underrun_count}: no samples")
        
        except Exception as e:
            # エラー発生時は無音を出力
            outdata.fill(0)
            if self._error_callback:
                self._error_callback(e)
    
    def _generation_loop(self) -> None:
        """バックグラウンドサンプル生成ループ"""
        # 生成チャンクサイズ（バッファサイズに応じて調整）
        max_chunk = self._audio_buffer.size // 4
        chunk_size = max(512, min(4096, max_chunk))
        
        while not self._stop_generation.is_set():
            try:
                # バッファに空きがある場合のみ生成
                free_space = self._audio_buffer.get_free_space()
                if free_space >= chunk_size:
                    # 実際に生成するサイズを調整（空きスペースを超えない）
                    actual_chunk = min(chunk_size, free_space)

                    # サンプルを生成
                    samples = self._sample_generator.generate_samples(actual_chunk)

                    # バッファに書き込み
                    written = self._audio_buffer.write(samples, timeout=0.01)

                    if written < len(samples) and self._debug_enabled:
                        print(f"Buffer overrun: wrote {written}/{len(samples)} samples")
                else:
                    # バッファが満杯の場合は少し待つ
                    time.sleep(0.001)
            
            except Exception as e:
                if self._error_callback:
                    self._error_callback(e)
                time.sleep(0.01)  # エラー時は少し待つ
    
    def _cleanup(self) -> None:
        """リソースをクリーンアップ"""
        self._stream = None
        self._generator_thread = None
        self._audio_buffer.clear()
    
    def _reset_statistics(self) -> None:
        """統計情報をリセット"""
        self._callback_count = 0
        self._underrun_count = 0
        self._total_samples_played = 0
        self._audio_buffer.reset_statistics()
        self._sample_generator.reset_statistics()
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得
        
        Returns:
            統計情報辞書
        """
        current_time = time.time()
        runtime = current_time - self._start_time if self._is_playing else 0
        
        stats = {
            'is_playing': self._is_playing,
            'sample_rate': self._sample_rate,
            'channels': self._channels,
            'runtime': runtime,
            'callback_count': self._callback_count,
            'underrun_count': self._underrun_count,
            'total_samples_played': self._total_samples_played,
            'samples_per_second': (
                self._total_samples_played / runtime if runtime > 0 else 0
            ),
            'underrun_rate': (
                self._underrun_count / self._callback_count 
                if self._callback_count > 0 else 0
            ),
            'buffer_stats': self._audio_buffer.get_statistics(),
            'generator_stats': self._sample_generator.get_statistics()
        }
        
        if self._debug_enabled:
            stats['debug_info'] = self._debug_info.copy()
        
        return stats
    
    def get_device_info(self) -> Dict[str, Any]:
        """音声デバイス情報を取得
        
        Returns:
            デバイス情報辞書
        """
        if not SOUNDDEVICE_AVAILABLE:
            return {'error': 'sounddevice not available'}
        
        try:
            default_device = sd.default.device
            device_info = sd.query_devices()
            
            return {
                'default_device': default_device,
                'current_device': self._device,
                'available_devices': device_info,
                'default_samplerate': sd.default.samplerate,
                'current_samplerate': self._sample_rate
            }
        except Exception as e:
            return {'error': str(e)}
    
    def __enter__(self):
        """コンテキストマネージャー開始"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャー終了"""
        self.stop()


def create_audio_driver(core: AY38910Core, sample_rate: int = 44100,
                       stereo: bool = False, buffer_duration: float = 0.1) -> AudioDriver:
    """標準的な音声ドライバを作成
    
    Args:
        core: AY-3-8910エミュレータコア
        sample_rate: サンプルレート（Hz）
        stereo: ステレオ出力を使用するかどうか
        buffer_duration: バッファ持続時間（秒）
        
    Returns:
        AudioDriverインスタンス
    """
    channels = 2 if stereo else 1
    return AudioDriver(core, sample_rate, channels, buffer_duration)


def list_audio_devices() -> Dict[str, Any]:
    """利用可能な音声デバイスを一覧表示
    
    Returns:
        デバイス情報辞書
    """
    if not SOUNDDEVICE_AVAILABLE:
        return {'error': 'sounddevice not available'}
    
    try:
        devices = sd.query_devices()
        default_device = sd.default.device
        
        return {
            'devices': devices,
            'default_input': default_device[0] if isinstance(default_device, tuple) else None,
            'default_output': default_device[1] if isinstance(default_device, tuple) else default_device,
            'default_samplerate': sd.default.samplerate
        }
    except Exception as e:
        return {'error': str(e)}


def test_audio_system() -> Dict[str, Any]:
    """音声システムをテスト
    
    Returns:
        テスト結果辞書
    """
    results = {
        'sounddevice_available': SOUNDDEVICE_AVAILABLE,
        'numpy_available': True,  # numpyは必須依存関係なので常にTrue
    }
    
    if SOUNDDEVICE_AVAILABLE:
        try:
            # デバイス情報を取得
            devices = sd.query_devices()
            results['device_count'] = len(devices)
            results['default_device'] = sd.default.device
            results['default_samplerate'] = sd.default.samplerate
            
            # 短いテスト音を生成して再生
            test_duration = 0.1  # 100ms
            test_freq = 440.0    # A4
            test_samplerate = 44100
            
            t = np.linspace(0, test_duration, int(test_samplerate * test_duration))
            test_signal = 0.1 * np.sin(2 * np.pi * test_freq * t)
            
            # テスト再生
            sd.play(test_signal, test_samplerate)
            sd.wait()  # 再生完了まで待機
            
            results['test_playback'] = 'success'
        
        except Exception as e:
            results['test_playback'] = f'failed: {e}'
    else:
        results['error'] = 'sounddevice not available'
    
    return results

