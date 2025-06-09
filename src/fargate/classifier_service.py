"""Fargate classifier service – polls SQS, classifies tweets, persists results.

This version is designed for local unit testing with in-memory stubs; the
production entrypoint wires real SQS/DynamoDB clients.
"""
from __future__ import annotations

import json
import logging
from typing import List
from dataclasses import asdict
import boto3
from datetime import datetime
from pathlib import Path

from shared.classification.classifier import HierarchicalClassifier
from shared.classification.llm_client import LLMClient
from shared.queue import InMemoryQueue, SQSQueue
from shared.store import Store, DynamoDBStore

from shared.taxonomy import get_registry


class InMemoryStore:
    """Very small stub of a persistence layer for unit tests."""

    def __init__(self):
        self.items: List[dict] = []

    def put_batch(self, results: List[dict]):  # noqa: D401
        self.items.extend(results)


class ClassifierService:  # noqa: D101
    _BATCH_SIZE = 10

    def __init__(self, queue: SQSQueue, store: DynamoDBStore, classifier: HierarchicalClassifier):
        self._queue = queue
        self._store = store
        self._classifier = classifier
        self._s3_client = boto3.client("s3")

    def _download_metadata_from_s3(self, s3_path: str) -> dict:
        """Downloads and parses the enriched metadata JSON from S3."""
        if not s3_path.startswith("s3://"):
            # Handle local file path for testing
            local_path = Path("run_artifacts") / s3_path
            with open(local_path, "r") as f:
                return json.load(f)

        try:
            bucket, key = s3_path.replace("s3://", "").split("/", 1)
            response = self._s3_client.get_object(Bucket=bucket, Key=key)
            content = response["Body"].read().decode("utf-8")
            return json.loads(content)
        except Exception as e:
            logging.error(f"Failed to download or parse metadata from {s3_path}: {e}")
            raise

    def process_once(self) -> int:
        messages = self._queue.fetch_batch(max_messages=self._BATCH_SIZE)
        logging.info("Fetched %d messages from queue", len(messages))
        if not messages:
            return 0
        
        final_records = []
        for msg in messages:
            try:
                message_body = json.loads(msg["Body"])
                s3_metadata_path = message_body["s3_metadata_path"]
                
                logging.info("Downloading metadata %s", s3_metadata_path)
                enriched_data = self._download_metadata_from_s3(s3_metadata_path)
                
                # Extract tweet data from capture metadata structure
                tweet_id = enriched_data.get("tweet_id")
                tweet_text = enriched_data.get("tweet_metadata", {}).get("text", "")
                
                logging.info("Classifying tweet %s", tweet_id)
                classification_result = self._classifier.classify(
                    tweet_id=tweet_id,
                    tweet_text=tweet_text
                )
                
                # Build the final record with classification results
                final_record = {
                    "tweet_id": tweet_id,
                    "author_id": enriched_data.get("tweet_metadata", {}).get("author", {}).get("id"),
                    "author_username": enriched_data.get("tweet_metadata", {}).get("author", {}).get("username"),
                    "tweet_text": tweet_text,
                    "created_at": enriched_data.get("tweet_metadata", {}).get("created_at"),
                    "classification_result": {
                        "l1_topics": classification_result.level1.topics,
                        "l1_raw_response": classification_result.level1.raw_response,
                        "l2_topic": classification_result.level2.topic if classification_result.level2 else None,
                        "l2_raw_response": classification_result.level2.raw_response if classification_result.level2 else None,
                    },
                    "ai_models_used": {
                        "classification": classification_result.classification_model
                    },
                    "screenshot_s3_path": enriched_data.get("s3_screenshots", [None])[0] if enriched_data.get("s3_screenshots") else None,
                    "classified_at": datetime.now().isoformat()
                }
                
                final_records.append(final_record)
                self._queue.ack(msg["ReceiptHandle"])
                
            except Exception as exc:
                logging.exception("Failed to process message %s: %s", msg.get("MessageId", "N/A"), exc)

        if final_records:
            self._store.put_batch(final_records)
            logging.info("Processed and stored %d tweets", len(final_records))
            
        return len(final_records)

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