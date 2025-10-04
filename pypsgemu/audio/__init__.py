"""
PyPSGEmu Audio Layer

AY-3-8910エミュレータの音声出力機能を提供します。
リアルタイム音声再生、サンプル生成、音声バッファ管理を含みます。

主要コンポーネント:
- AudioBuffer: 循環バッファによる音声データ管理
- SampleGenerator: エミュレータコアからの音声サンプル生成
- AudioDriver: sounddeviceを使用したリアルタイム音声出力

使用例:
    ```python
    from pypsgemu.core import create_ay38910_core
    from pypsgemu.audio import create_audio_driver
    
    # エミュレータコアを作成
    core = create_ay38910_core()
    
    # 音声ドライバを作成して開始
    with create_audio_driver(core, stereo=True) as driver:
        # AY-3-8910レジスタを設定
        core.write_register(0, 0x00)  # チャンネルA周期（下位）
        core.write_register(1, 0x01)  # チャンネルA周期（上位）
        core.write_register(8, 0x0F)  # チャンネルA音量
        
        # 音声が再生される
        time.sleep(2.0)
    ```
"""

from .buffer import (
    AudioBuffer,
    AudioBufferError,
    create_audio_buffer
)

from .sample_generator import (
    SampleGenerator,
    StereoSampleGenerator,
    SampleGeneratorError,
    create_sample_generator
)

from .driver import (
    AudioDriver,
    create_audio_driver,
    list_audio_devices,
    test_audio_system,
    SOUNDDEVICE_AVAILABLE
)

from .high_quality_pipeline import (
    HighQualityAudioPipeline,
    OptimizedAudioPipeline,
    AudioPipelineError
)

from .performance_optimization import (
    OptimizedAudioPipeline,
    VectorizedOperations,
    CacheOptimization,
    MemoryPool,
    PerformanceProfiler,
    RealtimePerformanceMonitor,
    PerformanceBenchmark,
    OptimizationConfig,
    PerformanceMetrics,
    PerformanceError
)

# バージョン情報
__version__ = "1.0.0"

# 公開API
__all__ = [
    # バッファ関連
    "AudioBuffer",
    "AudioBufferError", 
    "create_audio_buffer",
    
    # サンプル生成関連
    "SampleGenerator",
    "StereoSampleGenerator",
    "SampleGeneratorError",
    "create_sample_generator",
    
    # ドライバ関連
    "AudioDriver",
    "create_audio_driver",
    "list_audio_devices",
    "test_audio_system",
    
    # 高品質パイプライン関連
    "HighQualityAudioPipeline",
    "AudioPipelineError",
    
    # 高度なパイプライン関連
    "AdvancedAudioPipeline",
    "AdvancedCubicInterpolator",
    "AdvancedDCRemovalFilter",
    "ParallelAudioProcessor",
    "BufferPool",
    "FrequencyResponseAnalyzer",
    
    # 性能最適化関連
    "OptimizedAudioPipeline",
    "VectorizedOperations",
    "CacheOptimization",
    "MemoryPool",
    "PerformanceProfiler",
    "RealtimePerformanceMonitor",
    "PerformanceBenchmark",
    "OptimizationConfig",
    "PerformanceMetrics",
    "PerformanceError",
    
    # ユーティリティ
    "create_simple_audio_system",
    "create_advanced_audio_system",
    "SOUNDDEVICE_AVAILABLE",
]


def create_simple_audio_system(core, sample_rate: int = 44100):
    """シンプルな音声システムを作成
    
    基本的なモノラル音声出力システムを作成します。
    
    Args:
        core: AY-3-8910エミュレータコア
        sample_rate: サンプルレート（Hz）
        
    Returns:
        AudioDriverインスタンス
    """
    return create_audio_driver(core, sample_rate, stereo=False)


def create_advanced_audio_system(core, sample_rate: int = 44100, 
                                stereo: bool = True, buffer_duration: float = 0.05):
    """高度な音声システムを作成
    
    低遅延のステレオ音声出力システムを作成します。
    
    Args:
        core: AY-3-8910エミュレータコア
        sample_rate: サンプルレート（Hz）
        stereo: ステレオ出力を使用するかどうか
        buffer_duration: バッファ持続時間（秒）
        
    Returns:
        AudioDriverインスタンス
    """
    return create_audio_driver(core, sample_rate, stereo, buffer_duration)


# 音声システム情報を取得
def get_audio_info():
    """音声システム情報を取得
    
    Returns:
        音声システム情報辞書
    """
    try:
        import sounddevice as sd
        sounddevice_available = True
        sounddevice_version = getattr(sd, '__version__', 'unknown')
    except ImportError:
        sounddevice_available = False
        sounddevice_version = None
    
    import numpy as np
    
    info = {
        'pypsgemu_audio_version': __version__,
        'sounddevice_available': sounddevice_available,
        'sounddevice_version': sounddevice_version,
        'numpy_version': np.__version__,
        'supported_sample_rates': [8000, 11025, 22050, 44100, 48000, 96000],
        'supported_channels': [1, 2],
        'default_sample_rate': 44100,
        'default_buffer_duration': 0.1,
    }
    
    if sounddevice_available:
        device_info = list_audio_devices()
        if 'error' not in device_info:
            info.update(device_info)
    
    return info


# モジュール初期化時の情報表示
def _show_initialization_info():
    """モジュール初期化情報を表示（デバッグ用）"""
    import os
    if os.environ.get('PYPSGEMU_DEBUG'):
        info = get_audio_info()
        print(f"PyPSGEmu Audio Layer v{info['pypsgemu_audio_version']}")
        print(f"sounddevice: {'available' if info['sounddevice_available'] else 'not available'}")
        if info['sounddevice_available']:
            print(f"Default sample rate: {info.get('default_samplerate', 'unknown')}")


# モジュール初期化
_show_initialization_info()

