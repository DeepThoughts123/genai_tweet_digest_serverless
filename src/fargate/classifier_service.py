"""Fargate classifier service – polls SQS, classifies tweets, persists results.

This version is designed for local unit testing with in-memory stubs; the
production entrypoint wires real SQS/DynamoDB clients.
"""
from __future__ import annotations

import json
import logging
from typing import List
from dataclasses import asdict

from shared.classification.classifier import HierarchicalClassifier
from shared.classification.llm_client import LLMClient
from shared.queue import InMemoryQueue, SQSQueue
from shared.store import Store

from shared.taxonomy import get_registry


class InMemoryStore:
    """Very small stub of a persistence layer for unit tests."""

    def __init__(self):
        self.items: List[dict] = []

    def put_batch(self, results: List[dict]):  # noqa: D401
        self.items.extend(results)


class ClassifierService:  # noqa: D101
    _BATCH_SIZE = 10

    def __init__(self, queue, store: Store, classifier: HierarchicalClassifier):
        self._queue = queue
        self._store = store
        self._classifier = classifier

    def process_once(self):  # noqa: D401
        messages = self._queue.fetch_batch(max_messages=self._BATCH_SIZE)
        if not messages:
            return 0
        results = []
        for msg in messages:
            body = json.loads(msg["Body"])
            tweet_id = body["tweet_id"]
            text = body["text"]
            try:
                result = self._classifier.classify(tweet_id, text)
                results.append(asdict(result))
                self._queue.ack(msg["ReceiptHandle"])
            except Exception as exc:  # noqa: BLE001 – capture and log
                logging.exception("Failed to classify tweet %s: %s", tweet_id, exc)
        if results:
            self._store.put_batch(results)
            logging.info("Processed %d tweets", len(results))
        return len(results)

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------
    @classmethod
    def from_env(cls):  # noqa: D401
        """Build a service instance based on environment variables.

        Falls back to in-memory stubs when required env vars are absent so the
        service can still run locally without AWS credentials.
        """
        from shared import env
        from shared.store import DynamoDBStore  # local import to avoid heavy deps in tests

        queue_url = env.get("QUEUE_URL")
        ddb_table = env.get("DDB_TABLE")

        queue = SQSQueue(queue_url) if queue_url else InMemoryQueue()
        store = DynamoDBStore(ddb_table) if ddb_table else InMemoryStore()

        llm_client = LLMClient(api_key=env.get("OPENAI_API_KEY") or None)
        classifier = HierarchicalClassifier(llm_client)
        return cls(queue, store, classifier) 