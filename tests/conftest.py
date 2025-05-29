import sys
import types

# Minimal stubs for optional browser_use package so UI imports don't fail
parents = ["browser_use", "browser_use.browser", "browser_use.agent"]
for pkg in parents:
    sys.modules.setdefault(pkg, types.ModuleType(pkg))

mods = [
    "browser_use.agent.views",
    "browser_use.browser.browser",
    "browser_use.browser.context",
    "browser_use.browser.views",
]
for name in mods:
    mod = sys.modules.setdefault(name, types.ModuleType(name))
    if name.endswith("agent.views"):
        setattr(mod, "AgentHistoryList", getattr(mod, "AgentHistoryList", type("AgentHistoryList", (), {})))
        setattr(mod, "AgentOutput", getattr(mod, "AgentOutput", type("AgentOutput", (), {})))
    elif name.endswith("browser.browser"):
        setattr(mod, "BrowserConfig", getattr(mod, "BrowserConfig", type("BrowserConfig", (), {})))
    elif name.endswith("browser.context"):
        setattr(mod, "BrowserContext", getattr(mod, "BrowserContext", type("BrowserContext", (), {})))
    elif name.endswith("browser.views"):
        setattr(mod, "BrowserState", getattr(mod, "BrowserState", type("BrowserState", (), {})))

def pytest_ignore_collect(path, config):  #(description of change & current functionality)
    if path.basename in {"test_webui_integration.py", "test_interface.py", "test_run_deep_research.py"}:  #(description of change & current functionality)
        from importlib.util import find_spec  #(description of change & current functionality)
        try:  #(description of change & current functionality)
            spec = find_spec("gradio")  #(description of change & current functionality)
        except ValueError:  #(description of change & current functionality)
            return True  #(description of change & current functionality)
        return spec is None  #(description of change & current functionality)
