try:
    from .webui import webui_manager  # (expose webui manager for tests)
except Exception:
    webui_manager = None  # (handle missing gradio)
