"""Storage pipeline for saving issues to S3."""

import json
from datetime import datetime
from typing import Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from scrapy import Item, Spider

from src.config.settings import settings
from src.models.issue import Issue
from src.scraper.middlewares import issues_scraped_total
from src.utils.logger import get_logger
from src.utils.state import FileStateManager

logger = get_logger(__name__)


class StoragePipeline:
    """Store validated issues to S3 and mark as processed."""

    def __init__(self):
        """Initialize storage pipeline."""
        self.s3_client = None
        self.state_manager = FileStateManager()
        self._init_s3()

    def _init_s3(self):
        """Initialize S3 client."""
        try:
            # Try to create S3 client with explicit credentials if provided
            # Otherwise, let boto3 use default credential chain (env vars, AWS config, etc.)
            if settings.aws_access_key_id and settings.aws_secret_access_key:
                session = boto3.Session(
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    region_name=settings.aws_region,
                )
            else:
                # Use default credential chain
                session = boto3.Session(region_name=settings.aws_region)
            
            s3_kwargs = {"endpoint_url": settings.aws_s3_endpoint_url} if settings.aws_s3_endpoint_url else {}
            self.s3_client = session.client("s3", **s3_kwargs)
            logger.info("S3 client initialized (will attempt S3 storage)")
        except Exception as e:
            logger.warning(f"Failed to initialize S3 client: {e}, will use local storage")
            # In development, can fall back to local storage
            self.s3_client = None

    def process_item(self, item: Item, spider: Spider) -> Any:
        """Process and store item."""
        if not isinstance(item, Issue):
            logger.error(f"Expected Issue, got {type(item)}")
            return item

        # Ensure project is set (fallback to extracting from key)
        project = item.project
        if not project:
            if "-" in item.key:
                project = item.key.split("-")[0]
            else:
                logger.error(f"Cannot determine project for {item.key}")
                from scrapy.exceptions import DropItem
                raise DropItem(f"Missing project: {item.key}")
        
        # Update item.project if it was empty
        if not item.project:
            item.project = project

        # Check for duplicates
        if self.state_manager.is_duplicate(item.key):
            logger.debug(f"Skipping duplicate issue: {item.key}")
            from scrapy.exceptions import DropItem

            raise DropItem(f"Duplicate issue: {item.key}")

        # Store to S3 or local storage
        s3_key = f"raw/{project}/{item.key}.json"
        issue_dict = item.to_dict()
        # Ensure project field is correct in saved data
        issue_dict["project"] = project

        if self.s3_client:
            # Try to upload to S3
            try:
                self.s3_client.put_object(
                    Bucket=settings.aws_s3_bucket,
                    Key=s3_key,
                    Body=json.dumps(issue_dict, indent=2, default=str),
                    ContentType="application/json",
                )
                logger.debug(f"Stored {item.key} to s3://{settings.aws_s3_bucket}/{s3_key}")
            except NoCredentialsError:
                logger.warning(f"AWS credentials not available, falling back to local storage for {item.key}")
                # Disable S3 client for future attempts
                self.s3_client = None
                # Fall through to local storage
                self._store_locally(item, issue_dict)
            except ClientError as e:
                logger.error(f"S3 error storing {item.key}: {e}, falling back to local storage")
                self._store_locally(item, issue_dict)
        else:
            # Fallback to local storage
            self._store_locally(item, issue_dict)

        # Mark as processed
        self.state_manager.mark_processed(item.key)

        # Update last_update timestamp (use validated project)
        self.state_manager.set_last_update(project, item.fields.updated)

        # Record metrics
        if issues_scraped_total:
            issues_scraped_total.labels(project=project).inc()

        logger.info(f"Successfully stored issue: {item.key}")
        
        return item

    def _store_locally(self, item: Issue, issue_dict: dict):
        """Store issue to local filesystem."""
        import os

        # Use project from issue_dict which has been validated
        project = issue_dict.get("project", item.project)
        if not project:
            # Fallback: extract from key
            project = item.key.split("-")[0] if "-" in item.key else "unknown"
            issue_dict["project"] = project

        local_path = f"data/raw/{project}/{item.key}.json"
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(issue_dict, f, indent=2, default=str)
        logger.debug(f"Stored {item.key} to {local_path}")

