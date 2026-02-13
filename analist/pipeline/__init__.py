"""
Upwork Extension Analysis Pipeline
===================================
Data Bridge & Flywheel Integration

P2.1: DataPipelineBridge - Watch upwork_dna/ for new exports
P2.2: DataFlywheel - Analyze current data and generate new keyword suggestions
"""

from .data_bridge import DataPipelineBridge
from .data_flywheel import DataFlywheel

__all__ = ['DataPipelineBridge', 'DataFlywheel']
