"""
GarageSwarm Memory System

Provides multi-tier memory architecture for learning and context retention:
- Short-term: Redis-based session context
- Long-term: Vector database for semantic search (future)
- Relational: Graph database for entity relationships (future)
"""

from .short_term import ShortTermMemory, get_short_term_memory
from .types import MemoryEvent, MemoryItem, MemoryEventType

__all__ = [
    "ShortTermMemory",
    "get_short_term_memory",
    "MemoryEvent",
    "MemoryItem",
    "MemoryEventType",
]
