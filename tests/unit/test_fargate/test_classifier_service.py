import json

from shared.classification.classifier import HierarchicalClassifier
from shared.classification.llm_client import LLMClient
from shared.classification.prompt_builder import PromptBuilder
from src.fargate.classifier_service import ClassifierService, InMemoryQueue, InMemoryStore

from tests.unit.test_shared.test_classifier import StubBackend  # reuse stub


def build_service():
    # prepare stub LLM backend always returns same categories
    l1_json = json.dumps({"level1": "Breakthrough Research", "confidence": 0.9})
    l2_json = json.dumps({"level2": ["Training Methods"], "confidence": 0.8})
    backend = StubBackend([l1_json, l2_json])
    llm = LLMClient(backend=backend)
    classifier = HierarchicalClassifier(llm)

    queue = InMemoryQueue()
    store = InMemoryStore()
    service = ClassifierService(queue, store, classifier)
    return service, queue, store


def test_service_processes_messages():
    service, queue, store = build_service()

    # enqueue two tweets
    queue.send({"tweet_id": "t1", "text": "New LoRA trick"})
    queue.send({"tweet_id": "t2", "text": "Scaling laws update"})

    processed = service.process_once()
    assert processed == 2
    assert len(store.items) == 2
    ids = {item["tweet_id"] for item in store.items}
    assert ids == {"t1", "t2"}
    for item in store.items:
        assert item["level1"] == "Breakthrough Research" 