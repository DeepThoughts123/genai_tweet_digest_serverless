"""CDK stack defining the classifier's AWS resources.

The module is import-safe when *aws_cdk* is absent so that local unit tests can
run without AWS dependencies.
"""
from __future__ import annotations

import os
from typing import Any

try:
    import aws_cdk as cdk  # type: ignore
    from aws_cdk import (  # type: ignore
        aws_ecs as ecs,
        aws_ecs_patterns as ecs_patterns,
        aws_ecr_assets as ecr_assets,
        aws_sqs as sqs,
        aws_dynamodb as dynamodb,
    )
except ImportError:  # pragma: no cover – allow code import without CDK
    cdk = None  # type: ignore


class ClassifierStack:  # noqa: D101 – simplified when CDK unavailable
    def __init__(self, scope: Any, stack_id: str, **kwargs):  # type: ignore
        if cdk is None:
            raise ImportError("aws_cdk is not installed – deploy tooling required")
        super().__init__()


if cdk is not None:  # pragma: no cover – only executed when CDK present

    class ClassifierStack(cdk.Stack):  # type: ignore
        def __init__(self, scope: cdk.App, stack_id: str, **kwargs):  # type: ignore
            super().__init__(scope, stack_id, **kwargs)

            # SQS queue
            queue = sqs.Queue(self, "ClassificationQueue",
                               visibility_timeout=cdk.Duration.seconds(30))

            # DynamoDB table
            table = dynamodb.Table(
                self,
                "TweetTopicsTable",
                partition_key=dynamodb.Attribute(name="tweet_id", type=dynamodb.AttributeType.STRING),
                billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
                removal_policy=cdk.RemovalPolicy.DESTROY,
            )

            # Build Docker image asset
            image = ecr_assets.DockerImageAsset(
                self, "ClassifierImage", directory=".")

            # Fargate service + cluster
            cluster = ecs.Cluster(self, "ClassifierCluster")
            task_def = ecs.FargateTaskDefinition(self, "TaskDef")
            container = task_def.add_container(
                "ClassifierContainer",
                image=ecs.ContainerImage.from_docker_image_asset(image),
                logging=ecs.LogDrivers.aws_logs(stream_prefix="Classifier"),
                environment={
                    "QUEUE_URL": queue.queue_url,
                    "DDB_TABLE": table.table_name,
                },
            )
            container.add_port_mappings(ecs.PortMapping(container_port=8080))

            ecs_patterns.ApplicationLoadBalancedFargateService(
                self,
                "Service",
                cluster=cluster,
                task_definition=task_def,
                assign_public_ip=True,
                desired_count=1,
            )

            # Permissions
            queue.grant_consume_messages(task_def.task_role)
            table.grant_write_data(task_def.task_role)

            # --- Outputs ---
            cdk.CfnOutput(self, "QueueUrl", value=queue.queue_url)
            cdk.CfnOutput(self, "TableName", value=table.table_name) 