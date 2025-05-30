"""Expose WebUI manager when dependencies are available."""  # module docstring explaining conditional import
try:
    from . import webui_manager  # (expose manager module)
except Exception:
    webui_manager = None  # (handle missing deps)
