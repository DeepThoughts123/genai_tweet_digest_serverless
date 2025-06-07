"""Persistence store abstractions for classifier results."""
from __future__ import annotations

import logging
from typing import List, Protocol

try:
    import boto3  # type: ignore
except ImportError:  # pragma: no cover
    boto3 = None  # type: ignore


class Store(Protocol):
    def put_batch(self, results: List[dict]): ...


class DynamoDBStore:
    """Batch-writes classifier results to a DynamoDB table."""

    def __init__(self, table_name: str, client=None):
        if client is None:
            if boto3 is None:
                raise ImportError("boto3 is required for DynamoDBStore")
            client = boto3.resource("dynamodb")
        self._table = client.Table(table_name)

    def put_batch(self, results: List[dict]):  # noqa: D401
        # DynamoDB batch_writer handles retries automatically
        with self._table.batch_writer() as batch:
            for item in results:
                batch.put_item(Item=item)
        logging.debug("Persisted %d items to DynamoDB", len(results)) 