"""Pluggable publishing targets.

The "publish everywhere" button fans a story out to every enabled target. Each
target implements the Publisher interface. Add WhatsApp/Instagram/newsletter
adapters here without touching the pipeline.
"""
from .base import Publisher, PublishResult, get_publisher, available_targets

__all__ = ["Publisher", "PublishResult", "get_publisher", "available_targets"]
