"""Offline mode utilities and qerrors wrapper."""  # module docstring describing purpose

import logging  # handle debug logs centrally
import os  # env vars for offline detection
import asyncio  # check coroutine functions for decorator

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


def offline_guard(mock_return):
    """Return decorator that provides ``mock_return`` when offline."""  #// central offline wrapper
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                if is_offline():  # return mock object when CODEX True
                    logger.info(f"{func.__name__} mocked due to offline mode")
                    return mock_return
                return await func(*args, **kwargs)
            return async_wrapper
        else:
            def wrapper(*args, **kwargs):
                if is_offline():  # return mock object when CODEX True
                    logger.info(f"{func.__name__} mocked due to offline mode")
                    return mock_return
                return func(*args, **kwargs)
            return wrapper
    return decorator


__all__ = ["is_offline", "qerrors", "offline_guard"]  # export helpers

