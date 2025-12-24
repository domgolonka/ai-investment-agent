"""
Analysis module for storing and retrieving analysis history.

This module provides persistence capabilities for stock analysis results,
enabling portfolio creation from past analyzed stocks.
"""

from .history import AnalysisRecord, AnalysisHistoryStorage, AnalysisHistoryError

__all__ = [
    "AnalysisRecord",
    "AnalysisHistoryStorage",
    "AnalysisHistoryError",
]
