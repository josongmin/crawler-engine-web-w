"""Execution services for different backends (local, AWS SQS, etc.)."""

from __future__ import annotations

from wine_crawler.admin.services.execution.aws_sqs import AWSSQSExecutor
from wine_crawler.admin.services.execution.local import LocalExecutor

__all__ = ["AWSSQSExecutor", "LocalExecutor"]
