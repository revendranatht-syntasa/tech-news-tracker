"""
News Pipeline - A modular RSS feed processing and semantic search system.
"""

from .pipeline import NewsPipeline
from .config import AppConfig, FeedConfig

__version__ = "0.1.0"

__all__ = [
    "NewsPipeline",
    "AppConfig",
    "FeedConfig",
]