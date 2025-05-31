import sys  # allow src imports
import asyncio  # run async functions
sys.path.append('.')  # include project root for imports
from src.utils.offline import offline_guard  # decorator under test


def test_offline_guard_sync(monkeypatch):
    """Decorator returns mock value offline and real value online."""  # docstring summarizing test
    called = {'flag': False}  # track function execution

    @offline_guard('mock')
    def sample(x):
        called['flag'] = True  # mark executed
        return x + 1  # return processed value

    monkeypatch.setenv('CODEX', 'True')  # enable offline mode
    result_off = sample(1)  # call while offline
    assert result_off == 'mock'  # wrapper should return mock
    assert called['flag'] is False  # function body skipped

    monkeypatch.setenv('CODEX', 'False')  # disable offline mode
    result_on = sample(1)  # call again online
    assert result_on == 2  # original function result
    assert called['flag'] is True  # function executed
    monkeypatch.delenv('CODEX', raising=False)  # cleanup env var


def test_offline_guard_async(monkeypatch):
    """Async decorated function should also mock offline calls."""  # docstring summarizing test
    called = {'flag': False}  # track execution

    @offline_guard('mock')
    async def sample(x):
        called['flag'] = True  # mark executed
        return x * 2  # return processed value

    monkeypatch.setenv('CODEX', 'True')  # enable offline mode
    result_off = asyncio.run(sample(3))  # invoke async wrapper offline
    assert result_off == 'mock'  # expect mock return
    assert called['flag'] is False  # body not executed

    monkeypatch.delenv('CODEX', raising=False)  # remove CODEX env
    result_on = asyncio.run(sample(3))  # call again online
    assert result_on == 6  # original result
    assert called['flag'] is True  # function executed
