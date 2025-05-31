"""Utility helpers shared across the Browser Use project."""  # module docstring describing utilities

from .offline import is_offline, qerrors, offline_guard  # expose offline helpers for reuse, including decorator

__all__ = ["is_offline", "qerrors", "offline_guard"]  # defined exports for convenience including offline decorator
