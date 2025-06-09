#!/usr/bin/env python
"""End-to-end pipeline driver.

This CLI lets you run the *fetch → capture → classify → persist* flow locally
or against real AWS infrastructure depending on available environment
variables.

Example (local-only run):

    python scripts/run_pipeline.py --accounts karpathy openai \
        --days 7 --max 3 --output run_artifacts

Example (AWS run):

    export QUEUE_URL=... DDB_TABLE=... S3_BUCKET=...
    python scripts/run_pipeline.py --accounts karpathy --aws
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from datetime import datetime
from typing import List

from shared import env
from shared.queue import InMemoryQueue, SQSQueue
from shared.store import DynamoDBStore
from src.fargate.classifier_service import InMemoryStore
from shared.taxonomy import get_registry
from src.fargate.classifier_service import ClassifierService

# Heavy imports only if needed
if True:  # noqa: D401 – keep formatting
    from shared.tweet_services import TweetFetcher
    from shared.visual_tweet_capture_service import (
        VisualTweetCaptureService,
        capture_twitter_account_visuals,
    )


def parse_args() -> argparse.Namespace:  # noqa: D401
    p = argparse.ArgumentParser(description="Run tweet pipeline end-to-end")
    p.add_argument("--accounts", nargs="+", required=True, help="Twitter handles without @")
    p.add_argument("--days", type=int, default=7, help="Look-back window (days)")
    p.add_argument("--max", type=int, default=20, help="Max tweets per account")
    p.add_argument("--output", default="run_artifacts", help="Local output folder for artifacts")
    p.add_argument("--aws", action="store_true", help="Use AWS SQS/DynamoDB if env vars present")
    return p.parse_args()


def ensure_dir(path: pathlib.Path):  # noqa: D401
    path.mkdir(parents=True, exist_ok=True)


def main():  # noqa: D401
    args = parse_args()
    out_dir = pathlib.Path(args.output)
    ensure_dir(out_dir)

    fetcher = TweetFetcher()
    
    # Always instantiate capture_service
    # In AWS mode, it will use the S3_BUCKET from env vars
    # In local mode, it saves to the filesystem
    s3_bucket = env.get("S3_BUCKET", "local") if args.aws else "local"
    capture_service = VisualTweetCaptureService(s3_bucket=s3_bucket, zoom_percent=60)

    # queue / store selection
    if args.aws and env.get("QUEUE_URL"):
        queue = SQSQueue(env.get("QUEUE_URL"))
    else:
        queue = InMemoryQueue()

    if args.aws and env.get("DDB_TABLE"):
        store = DynamoDBStore(env.get("DDB_TABLE"))
    else:
        store = InMemoryStore()

    classifier_service = ClassifierService(queue, store, ClassifierService.from_env()._classifier)  # type: ignore  # pylint: disable=protected-access

    for acct in args.accounts:
        print(f"=== Processing @{acct} ===")
        # The capture service will fetch tweets, so we don't need to call fetcher directly.
        enriched_results = capture_service.capture_account_content(
            acct, days_back=args.days, max_tweets=args.max
        )
        (out_dir / f"{acct}_enriched_results.json").write_text(json.dumps(enriched_results, indent=2))
        
        # The enriched_results is a dict with 'captured_items' array
        if enriched_results.get("success") and "captured_items" in enriched_results:
            for item in enriched_results["captured_items"]:
                if "metadata_s3_location" in item:
                    print(f"Enqueuing: {item['metadata_s3_location']}")
                    queue.send_message({"s3_metadata_path": item["metadata_s3_location"]})

    # Process queue until empty
    # In AWS mode, this local processing loop is only for confirmation.
    # The Fargate service will be the primary consumer.
    while not args.aws and classifier_service.process_once() > 0:
        pass

    # Dump in-memory results if local
    if isinstance(store, InMemoryStore):
        out_file = out_dir / "classified.json"
        out_file.write_text(json.dumps(store.items, indent=2, default=str))
        print(f"Results written to {out_file}")

    print("Pipeline run complete.")


if __name__ == "__main__":
    sys.exit(main()) 