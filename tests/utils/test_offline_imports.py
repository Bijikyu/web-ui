import asyncio
import importlib
import sys
import types


def stub_module(name, attrs=None):
    """Insert a dummy module with optional attributes."""  #// creates stub module to satisfy imports
    mod = types.ModuleType(name)  #// actual module replacement
    if attrs:
        for key, val in attrs.items():
            setattr(mod, key, val)  #// attach given attributes
    sys.modules[name] = mod  #// register stub in sys.modules
    return mod


def restore_modules(saved):
    """Restore original modules after test run."""  #// ensure cleanup of sys.modules
    for name, module in saved.items():
        if module is not None:
            sys.modules[name] = module  #// put back original module
        else:
            sys.modules.pop(name, None)  #// remove stub if module absent




def test_browser_launch_offline(monkeypatch):
    """Import browser_launch with missing playwright and verify defaults."""  #// ensures import works when dependency absent
    monkeypatch.setenv("CODEX", "True")  #// enable offline mode
    saved = {n: sys.modules.pop(n, None) for n in ["playwright", "playwright.async_api", "src.utils.browser_launch"]}
    stub_module("playwright.async_api", {"async_playwright": lambda: None})  #// minimal stub for import
    mod = importlib.import_module("src.utils.browser_launch")  #// import target module
    path, args = mod.build_browser_launch_options({})  #// call util with defaults
    assert path is None  #// default path when not using own browser
    assert args == ["--window-size=1280,1100"]  #// expected default args
    monkeypatch.delenv("CODEX", raising=False)  #// cleanup env var
    restore_modules(saved)  #// restore original modules


def test_llm_provider_offline(monkeypatch):
    """Ensure llm_provider functions return mocked data when offline."""  #// verify offline path
    monkeypatch.setenv("CODEX", "True")  #// enable offline mode
    modules = [
        "openai", "langchain_openai", "langchain_ollama", "langchain_anthropic",
        "langchain_mistralai", "langchain_google_genai", "langchain_ibm",
        "langchain_aws", "pydantic", "langchain_core.globals",
        "langchain_core.language_models.base", "langchain_core.load",
        "langchain_core.messages", "langchain_core.outputs",
        "langchain_core.output_parsers.base", "langchain_core.runnables",
        "langchain_core.tools", "src.utils.llm_provider"
    ]
    saved = {n: sys.modules.pop(n, None) for n in modules}

    class Dummy:
        def __init__(self, *a, **k):
            self.kwargs = k  #// store kwargs for inspection

    stub_module("openai", {"OpenAI": Dummy})  #// stub OpenAI class
    stub_module("langchain_openai", {"ChatOpenAI": Dummy, "AzureChatOpenAI": Dummy})  #// stub openai chat classes
    stub_module("langchain_ollama", {"ChatOllama": Dummy})  #// stub ollama class
    stub_module("langchain_anthropic", {"ChatAnthropic": Dummy})  #// stub anthropic class
    stub_module("langchain_mistralai", {"ChatMistralAI": Dummy})  #// stub mistral class
    stub_module("langchain_google_genai", {"ChatGoogleGenerativeAI": Dummy})  #// stub google class
    stub_module("langchain_ibm", {"ChatWatsonx": Dummy})  #// stub ibm class
    stub_module("langchain_aws", {"ChatBedrock": Dummy})  #// stub aws class
    stub_module("pydantic", {"SecretStr": Dummy})  #// stub SecretStr
    stub_module("langchain_core.globals", {"get_llm_cache": lambda: None})  #// stub cache util
    stub_module(
        "langchain_core.language_models.base",
        {"BaseLanguageModel": Dummy, "LangSmithParams": Dummy, "LanguageModelInput": list},
    )  #// stub base classes
    stub_module("langchain_core.load", {"dumpd": lambda *a, **k: {}, "dumps": lambda *a, **k: ""})  #// stub dumps

    class Message:
        def __init__(self, content=""):
            self.content = content  #// store message content

    stub_module(
        "langchain_core.messages",
        {
            "AIMessage": Message,
            "SystemMessage": Message,
            "AnyMessage": Message,
            "BaseMessage": Message,
            "BaseMessageChunk": Message,
            "HumanMessage": Message,
            "convert_to_messages": lambda x: x,
            "message_chunk_to_message": lambda x: x,
        },
    )  #// stub message classes
    stub_module(
        "langchain_core.outputs",
        {
            "ChatGeneration": Dummy,
            "ChatGenerationChunk": Dummy,
            "ChatResult": Dummy,
            "LLMResult": Dummy,
            "RunInfo": Dummy,
        },
    )  #// stub output types
    stub_module("langchain_core.output_parsers.base", {"OutputParserLike": Dummy})  #// stub parser
    stub_module("langchain_core.runnables", {"Runnable": Dummy, "RunnableConfig": Dummy})  #// stub runnables
    stub_module("langchain_core.tools", {"BaseTool": Dummy})  #// stub tool base

    llm_provider = importlib.import_module("src.utils.llm_provider")  #// import target module
    assert llm_provider.is_offline()  #// CODEX=True triggers offline mode
    model = llm_provider.DeepSeekR1ChatOpenAI()  #// instantiate provider
    result = asyncio.run(model.ainvoke([llm_provider.HumanMessage("hi")]))  #// call ainvoke offline
    assert result.content == "mock response"  #// expect mocked message
    assert result.reasoning_content == "mock reasoning"  #// expect mocked reasoning
    monkeypatch.delenv("CODEX", raising=False)  #// cleanup env var
    restore_modules(saved)  #// restore original modules
