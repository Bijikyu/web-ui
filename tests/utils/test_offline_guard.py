import sys  #// allow src imports
import asyncio  #// used for async test
sys.path.append('.')  #// include project root
from src.utils.offline import offline_guard  #// decorator under test


def test_offline_guard_preserves_metadata(monkeypatch):
    """Ensure name and docstring survive wrapping."""  #// verify sync functions
    monkeypatch.delenv("CODEX", raising=False)  #// start online

    @offline_guard('mock')
    def sample():
        """doc string"""  #// baseline doc
        return 'real'

    assert sample.__name__ == 'sample'  #// name intact
    assert sample.__doc__ == 'doc string'  #// docstring intact
    monkeypatch.setenv('CODEX', 'True')  #// enable offline mode
    assert sample() == 'mock'  #// decorator returns mock offline
    monkeypatch.delenv('CODEX', raising=False)  #// cleanup


import pytest  #// pytest for asyncio marker


@pytest.mark.asyncio
async def test_offline_guard_preserves_metadata_async(monkeypatch):
    """Async functions should keep metadata."""  #// verify async path
    monkeypatch.delenv('CODEX', raising=False)  #// start online

    @offline_guard('mock')
    async def async_fn():
        """async doc"""  #// baseline async doc
        return 'real'

    assert async_fn.__name__ == 'async_fn'  #// name intact
    assert async_fn.__doc__ == 'async doc'  #// docstring intact
    monkeypatch.setenv('CODEX', 'True')  #// enable offline mode
    assert await async_fn() == 'mock'  #// decorator returns mock offline
    monkeypatch.delenv('CODEX', raising=False)  #// cleanup
