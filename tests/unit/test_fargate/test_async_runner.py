import asyncio
import json

import pytest

from src.fargate import async_runner as ar
from src.fargate.classifier_service import InMemoryQueue, InMemoryStore, ClassifierService
from shared.classification.llm_client import LLMClient
from tests.unit.test_shared.test_classifier import StubBackend
from shared.classification.classifier import HierarchicalClassifier


@pytest.mark.asyncio
async def test_run_loop_processes_messages():
    # Build stub service
    l1_json = json.dumps({"level1": "Breakthrough Research", "confidence": 0.9})
    l2_json = json.dumps({"level2": ["Training Methods"], "confidence": 0.8})
    llm = LLMClient(backend=StubBackend([l1_json, l2_json]))
    queue = InMemoryQueue()
    store = InMemoryStore()
    service = ClassifierService(queue, store, HierarchicalClassifier(llm))

    # enqueue one message
    queue.send({"tweet_id": "t1", "text": "LoRA news"})

    stop_event = asyncio.Event()

    # schedule stop after small delay
    async def _stop():
        await asyncio.sleep(0.2)
        stop_event.set()

    await asyncio.gather(ar._run_loop(service, stop_event, idle_sleep=0.05), _stop())

    assert len(store.items) == 1 