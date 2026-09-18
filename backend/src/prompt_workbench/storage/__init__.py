"""Storage abstraction: one Repository interface, swappable backends."""

from .base import Repository, matches
from .factory import Collections, build_repository
from .sqlite import SqliteRepository

__all__ = ["Repository", "matches", "build_repository", "Collections", "SqliteRepository"]
