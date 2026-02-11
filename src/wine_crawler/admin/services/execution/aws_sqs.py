# pyright: reportMissingTypeStubs=false
# pyright: reportUnnecessaryTypeIgnoreComment=false
# boto3 is an optional dependency, type stubs available via mypy-boto3-sqs
# Type ignores are necessary when boto3 is None or type stubs are missing

"""AWS SQS executor (submit jobs to SQS queue for worker processing)."""

from __future__ import annotations
import json
import logging
from typing import TYPE_CHECKING

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None  # pyright: ignore[reportAssignmentType]
    ClientError = Exception  # Fallback for type checking

if TYPE_CHECKING:
    from typing import Any

    from wine_crawler.admin.db.models import Job

    # boto3 types are optional - use Any if mypy-boto3-sqs is not installed
    SQSClient = Any  # type: ignore[misc]

logger = logging.getLogger(__name__)


class AWSSQSExecutor:
    """Submit jobs to AWS SQS for async processing by workers."""

    def __init__(self, queue_url: str, region_name: str = "us-east-1") -> None:
        # No parent class, so no super() call needed
        if boto3 is None:
            raise ImportError(
                "boto3 is required for AWS SQS executor. Install with: pip install boto3"
            )
        self.queue_url = queue_url
        # boto3.client returns Any without type stubs
        self.sqs: SQSClient = boto3.client("sqs", region_name=region_name)  # type: ignore[assignment]

    async def submit(self, job: Job) -> str:
        """Submit job to SQS queue.

        The worker (ECS Fargate task) will poll this queue and execute the job.
        """
        try:
            response = self.sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(
                    {
                        "job_id": job.id,
                        "site": job.site,
                        "rule_id": job.rule_id,
                        "limit_n": job.limit_n,
                        "headless": job.headless,
                    }
                ),
                MessageAttributes={
                    "site": {"StringValue": job.site, "DataType": "String"},
                    "status": {"StringValue": "pending", "DataType": "String"},
                },
            )
            logger.info("Job %s submitted to SQS (MessageId: %s)", job.id, response["MessageId"])
            return job.id
        except ClientError:
            logger.exception("Failed to submit job %s to SQS", job.id)
            raise
