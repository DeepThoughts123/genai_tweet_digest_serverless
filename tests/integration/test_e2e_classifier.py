import os
import json
import time

import boto3
import pytest
from moto import mock_aws

from shared.classification.llm_client import LLMClient
from src.fargate.classifier_service import ClassifierService


class _NoOpLLM:
    """Stub LLMClient that returns deterministic JSON."""

    def chat_completion(self, messages, temperature: float = 0.0):  # noqa: D401
        if "LEVEL-1" in messages[-1]["content"]:
            return '{"level1":"Breakthrough Research","confidence":"0.95"}'
        return '{"level2":["Training Methods"],"confidence":"0.9"}'


@pytest.mark.integration  # mark so CI can skip unless explicitly enabled
@mock_aws
def test_end_to_end_classifier():
    # Setup moto AWS environment
    os.environ["AWS_REGION"] = "us-east-1"

    sqs = boto3.client("sqs", region_name="us-east-1")
    queue_url = sqs.create_queue(QueueName="classification_requests")[
        "QueueUrl"
    ]

    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    table_name = "tweet_topics"
    ddb.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "tweet_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "tweet_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    # Env vars for service factory
    os.environ["QUEUE_URL"] = queue_url
    os.environ["DDB_TABLE"] = table_name

    # Patch LLMClient globally to avoid real API call
    import src.fargate.classifier_service as cs

    cs.LLMClient = lambda api_key=None: _NoOpLLM()  # type: ignore

    service = ClassifierService.from_env()

    # enqueue message
    tweet_body = {"tweet_id": "t123", "text": "New LoRA trick"}
    sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(tweet_body))

    # Process until table populated or timeout
    deadline = time.time() + 5
    while time.time() < deadline:
        if service.process_once() > 0:
            break
        time.sleep(0.5)

    table = ddb.Table(table_name)
    items = table.scan()["Items"]
    assert len(items) == 1
    assert items[0]["tweet_id"] == "t123"
    assert items[0]["level1"] == "Breakthrough Research" 