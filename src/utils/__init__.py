"""Utility helpers shared across the Browser Use project."""  # module docstring describing utilities

from .offline import is_offline, qerrors  # expose offline helpers for reuse

__all__ = ["is_offline", "qerrors"]  # defined exports for convenience
