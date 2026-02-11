#!/usr/bin/env python3
"""SQS Worker: Polls SQS queue and executes crawler jobs.

Usage:
    SQS_QUEUE_URL=https://sqs... python scripts/worker.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    sys.stderr.write("ERROR: boto3 required. Install with: pip install boto3\n")
    sys.exit(1)

from wine_crawler.admin.db.connection import Database
from wine_crawler.admin.db.models import Job
from wine_crawler.config import Settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def process_job(job: Job, db: Database) -> None:
    """Execute a crawler job.

    TODO: Integrate with actual crawler execution logic.
    """
    logger.info("Processing job %s (site=%s, rule_id=%s)", job.id, job.site, job.rule_id)

    # Update status to running
    await db.repos.jobs.update_status(job.id, "running")

    try:
        # TODO: Actual crawler execution
        # from wine_crawler.sites import get_crawler
        # crawler = get_crawler(job.site)
        # result = await crawler.crawl(...)

        # Simulate work
        await asyncio.sleep(2)

        # Update status to completed
        await db.repos.jobs.update_status(
            job.id,
            "completed",
            item_count=10,  # TODO: actual count
            output_path=f"/tmp/job-{job.id}.json",  # TODO: S3 path
        )
        logger.info("Job %s completed successfully", job.id)

    except Exception:
        logger.exception("Job %s failed", job.id)
        await db.repos.jobs.update_status(job.id, "failed", error="See logs")


async def worker_loop() -> None:
    """Main worker loop: poll SQS and process jobs."""
    queue_url = os.environ.get("SQS_QUEUE_URL")
    if not queue_url:
        raise ValueError("SQS_QUEUE_URL environment variable required")

    db_path = os.environ.get("ADMIN_DB_PATH", "/tmp/crawler-admin.db")
    settings = Settings()
    settings.admin_db_path = Path(db_path)

    sqs = boto3.client("sqs", region_name=os.environ.get("AWS_REGION", "us-east-1"))

    db = Database(settings.admin_db_path)
    await db.connect()
    logger.info("Worker started. Polling queue: %s", queue_url)

    try:
        while True:
            try:
                # Long polling (WaitTimeSeconds=20)
                response = sqs.receive_message(
                    QueueUrl=queue_url,
                    MaxNumberOfMessages=1,
                    WaitTimeSeconds=20,
                    MessageAttributeNames=["All"],
                )

                if "Messages" not in response:
                    continue

                for msg in response["Messages"]:
                    try:
                        body = json.loads(msg["Body"])
                        job_id = body["job_id"]

                        # Load job from DB
                        job = await db.repos.jobs.get(job_id)
                        if not job:
                            logger.warning("Job %s not found in DB, skipping", job_id)
                            sqs.delete_message(
                                QueueUrl=queue_url, ReceiptHandle=msg["ReceiptHandle"]
                            )
                            continue

                        # Process job
                        await process_job(job, db)

                        # Delete message after successful processing
                        sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=msg["ReceiptHandle"])

                    except Exception:
                        logger.exception("Error processing message")
                        # Message will become visible again after visibility timeout

            except ClientError:
                logger.exception("SQS error")
                await asyncio.sleep(5)  # Back off on errors

    except KeyboardInterrupt:
        logger.info("Worker shutting down...")
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(worker_loop())
