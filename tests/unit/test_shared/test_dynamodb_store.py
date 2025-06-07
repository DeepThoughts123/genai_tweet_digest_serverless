import uuid

import boto3
from moto import mock_aws

from shared.store import DynamoDBStore


@mock_aws
def test_dynamodb_store_put_batch():
    table_name = "tweet_topics_test"
    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    # create table
    ddb.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "tweet_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "tweet_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    store = DynamoDBStore(table_name, client=ddb)
    items = [
        {
            "tweet_id": str(uuid.uuid4()),
            "level1": "Breakthrough Research",
            "version": "v1",
        }
        for _ in range(3)
    ]
    store.put_batch(items)

    table = ddb.Table(table_name)
    resp = table.scan()
    assert resp["Count"] == 3 