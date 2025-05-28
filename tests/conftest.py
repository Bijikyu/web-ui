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
