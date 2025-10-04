"""
PyPSGEmu - デバッグ機能

このモジュールは、AY-3-8910エミュレータのデバッグ機能を提供します。

主要コンポーネント:
- DebugEngine: デバッグエンジン（ブレークポイント、ステップ実行）
- RegisterViewer: レジスタ表示・解析
- WaveformViewer: 波形表示（将来実装）
- EnvelopeViewer: エンベロープ表示（将来実装）
"""

from .engine import DebugEngine, DebugState, BreakpointCondition
from .register_viewer import RegisterViewer, RegisterInfo

__all__ = [
    'DebugEngine', 'DebugState', 'BreakpointCondition',
    'RegisterViewer', 'RegisterInfo'
]
