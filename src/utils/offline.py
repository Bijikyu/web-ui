"""Offline mode utilities and qerrors wrapper."""  # module docstring describing purpose

import logging
import os

logger = logging.getLogger(__name__)


def is_offline() -> bool:
    """Return ``True`` when running in Codex offline mode."""  #// check CODEX env
    return os.getenv("CODEX") == "True"  # CODEX=True triggers offline behavior


def qerrors_stub(error, context="", *extra_args):
    """Fallback qerrors implementation for offline mode."""  #// stub logs locally
    logger.error(f"{context}: {error}")  # log error when real qerrors unavailable


def qerrors(error, context="", *extra_args):
    """Call real qerrors when online, otherwise fallback."""  #// central wrapper
    if is_offline():
        qerrors_stub(error, context, *extra_args)  # skip real qerrors offline
    else:
        try:
            import qerrors as real_qerrors  # import lazily to avoid missing dep
            real_qerrors(error, context, *extra_args)
        except Exception:  # fall back if module missing or call fails
            qerrors_stub(error, context, *extra_args)


__all__ = ["is_offline", "qerrors"]  # export helpers

