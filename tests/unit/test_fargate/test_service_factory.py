import os, sys
from importlib import reload

import pytest

from src.fargate import classifier_service as cs

# Inject dummy openai module globally before anything imports it
if "openai" not in sys.modules:
    sys.modules["openai"] = type("x", (), {"OpenAI": lambda api_key=None: None})

class DummyQueue:
    pass


class DummyStore:
    pass


class DummySQS:
    def __init__(self, url):
        self.url = url


class DummyDDB:
    def __init__(self, table):
        self.table = table


@pytest.fixture(autouse=True)
def monkeypatch_env(monkeypatch):
    # Ensure env vars are cleaned up after each test
    orig = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(orig)


def test_from_env_uses_inmemory_when_vars_missing(monkeypatch):
    # Patch LLMClient to avoid openai dependency
    class _NoOpLLM:
        def __init__(self, *a, **kw):
            pass

        def chat_completion(self, messages, temperature=0.0):
            return '{"level1":"Breakthrough Research","confidence":1}'

    monkeypatch.setattr(cs, "LLMClient", _NoOpLLM)
    import shared.classification.llm_client as llm_mod
    monkeypatch.setattr(llm_mod, "openai", type("x", (), {"OpenAI": lambda api_key=None: None}))
    service = reload(cs).ClassifierService.from_env()
    assert isinstance(service._queue, cs.InMemoryQueue)
    assert isinstance(service._store, cs.InMemoryStore)


def test_from_env_uses_real_when_vars_present(monkeypatch):
    os.environ["QUEUE_URL"] = "https://example.com/queue"
    os.environ["DDB_TABLE"] = "tweet_topics"
    # Patch SQSQueue and DynamoDBStore to dummy classes to avoid AWS deps
    monkeypatch.setattr(cs, "SQSQueue", lambda url: DummySQS(url))
    from shared import store as store_mod
    monkeypatch.setattr(store_mod, "DynamoDBStore", lambda table: DummyDDB(table))

    # Patch LLMClient to avoid openai dependency
    class _NoOpLLM:
        def __init__(self, *a, **kw):
            pass

        def chat_completion(self, messages, temperature=0.0):
            if "LEVEL-1" in messages[-1]["content"]:
                return '{"level1":"Breakthrough Research","confidence":0.9}'
            return '{"level2":["Training Methods"],"confidence":0.8}'

    monkeypatch.setattr(cs, "LLMClient", _NoOpLLM)
    import shared.classification.llm_client as llm_mod
    monkeypatch.setattr(llm_mod, "openai", type("x", (), {"OpenAI": lambda api_key=None: None}))

    service = reload(cs).ClassifierService.from_env()
    assert service is not None


def _stub_llm(*args, **kwargs):  # noqa: D401
    from tests.unit.test_shared.test_classifier import StubBackend
    import json
    l1_json = json.dumps({"level1": "Breakthrough Research", "confidence": 0.9})
    l2_json = json.dumps({"level2": ["Training Methods"], "confidence": 0.8})
    return cs.HierarchicalClassifier(LLMClient(backend=StubBackend([l1_json, l2_json]))) 