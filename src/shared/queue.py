"""Queue abstraction for classification service.

The real implementation uses AWS SQS via *boto3*, but tests can inject a simple
in-memory stub.
"""
from __future__ import annotations

import json
import logging
from typing import Any, List, Protocol, Sequence

try:
    import boto3  # type: ignore
except ImportError:  # pragma: no cover
    boto3 = None  # type: ignore


class Message(Protocol):
    body: str
    receipt_handle: str  # noqa: N815 – mimic boto3 attr name


class QueueClient(Protocol):
    def receive_messages(self, MaxNumberOfMessages: int, WaitTimeSeconds: int) -> Sequence[Message]: ...  # noqa: E501

    def delete_message(self, ReceiptHandle: str) -> None: ...


class SQSQueue:
    """Thin wrapper around boto3 SQS Queue resource."""

    def __init__(self, queue_url: str):
        if boto3 is None:
            raise ImportError("boto3 required for SQSQueue")
        self._client = boto3.client("sqs")
        self._url = queue_url

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def fetch_batch(self, max_messages: int = 10, wait_seconds: int = 1) -> List[dict]:
        response = self._client.receive_message(
            QueueUrl=self._url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=wait_seconds,
        )
        msgs = response.get("Messages", [])
        logging.debug("Fetched %d messages", len(msgs))
        return msgs

    def ack(self, receipt_handle: str) -> None:
        self._client.delete_message(QueueUrl=self._url, ReceiptHandle=receipt_handle)


class InMemoryQueue:
    """Simple FIFO queue for unit tests."""

    def __init__(self):
        self._items: List[str] = []

    def send(self, body: dict):  # noqa: D401 – non-boto
        self._items.append(json.dumps(body))

    def fetch_batch(self, max_messages: int = 10, wait_seconds: int = 0) -> List[dict]:
        batch = self._items[:max_messages]
        self._items = self._items[max_messages:]
        # produce fake message dicts
        return [
            {
                "Body": body,
                "ReceiptHandle": f"rh-{idx}",
            }
            for idx, body in enumerate(batch)
        ]

    def ack(self, receipt_handle: str):  # noqa: D401 – do nothing
        pass 