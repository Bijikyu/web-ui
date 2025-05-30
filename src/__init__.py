"""Top-level package initialization for Browser Use application."""  # module docstring describing package purpose
try:
    from .webui import webui_manager  # (expose webui manager for tests)
except Exception:
    webui_manager = None  # (handle missing gradio)
