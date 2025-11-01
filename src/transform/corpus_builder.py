"""Corpus builder that transforms raw issues to JSONL format."""

import json
import os
from pathlib import Path
from typing import Iterator, List, Optional

import boto3
from botocore.exceptions import ClientError

from src.config.settings import settings
from src.models.issue import Issue
from src.transform.prompts import PromptBuilder
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CorpusBuilder:
    """Build LLM corpus from raw Jira issues."""

    def __init__(
        self,
        input_dir: Optional[str] = None,
        output_path: str = "data/corpus/jira_corpus.jsonl",
        projects: Optional[List[str]] = None,
    ):
        """Initialize corpus builder.

        Args:
            input_dir: Input directory (S3 prefix or local path)
            output_path: Output JSONL file path
            projects: Optional list of projects to filter
        """
        self.input_dir = input_dir or f"s3://{settings.aws_s3_bucket}/raw/"
        self.output_path = output_path
        self.projects = projects
        self.s3_client = None
        self._init_s3()

    def _init_s3(self):
        """Initialize S3 client if needed."""
        if self.input_dir.startswith("s3://"):
            try:
                session = boto3.Session(
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    region_name=settings.aws_region,
                )
                s3_kwargs = {"endpoint_url": settings.aws_s3_endpoint_url} if settings.aws_s3_endpoint_url else {}
                self.s3_client = session.client("s3", **s3_kwargs)
                logger.info("S3 client initialized for corpus building")
            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {e}")

    def build(self) -> int:
        """Build corpus from input directory.

        Returns:
            Number of issues processed
        """
        logger.info(f"Building corpus from {self.input_dir} to {self.output_path}")

        # Create output directory
        output_path = Path(self.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        count = 0
        with open(self.output_path, "w", encoding="utf-8") as f:
            for issue in self._iterate_issues():
                try:
                    # Build all derived tasks (summarization, classification, QnA) plus metadata
                    issue_data = PromptBuilder.build_all_tasks(issue)

                    # Only write if we have meaningful content
                    if issue_data.get("description") or issue_data.get("comments"):
                        f.write(json.dumps(issue_data, ensure_ascii=False, default=str) + "\n")
                        count += 1
                    else:
                        logger.debug(f"Skipping {issue.key} (no content)")

                except Exception as e:
                    logger.warning(f"Error processing {issue.key}: {e}")
                    continue

        logger.info(f"Corpus built: {count} issues written to {self.output_path}")
        return count

    def _iterate_issues(self) -> Iterator[Issue]:
        """Iterate over issues from input directory."""
        if self.input_dir.startswith("s3://"):
            yield from self._iterate_s3_issues()
        else:
            yield from self._iterate_local_issues()

    def _iterate_local_issues(self) -> Iterator[Issue]:
        """Iterate over issues from local directory."""
        input_path = Path(self.input_dir)
        if not input_path.exists():
            logger.error(f"Input directory does not exist: {self.input_dir}")
            return

        # Find all JSON files
        json_files = list(input_path.rglob("*.json"))

        logger.info(f"Found {len(json_files)} JSON files in {self.input_dir}")

        for json_file in json_files:
            # Extract project from path (if in subdirectory) or from filename
            project = json_file.parent.name
            
            # Handle files at root level (fallback for old structure)
            if not project or project == "raw" or project == input_path.name:
                # Extract project from filename (e.g., "HADOOP-125.json" -> "HADOOP")
                filename_stem = json_file.stem  # Gets filename without extension
                if "-" in filename_stem:
                    project = filename_stem.split("-")[0]
                else:
                    # Try to get from JSON data itself
                    try:
                        with open(json_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            project = data.get("project") or data.get("fields", {}).get("project", {}).get("key", "")
                            if not project and "key" in data:
                                key = data["key"]
                                if "-" in key:
                                    project = key.split("-")[0]
                    except Exception:
                        project = "unknown"
            
            # Filter by projects if specified
            if self.projects and project not in self.projects:
                continue

            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    issue = Issue.from_jira_api(data)
                    # Ensure project is set correctly
                    if not issue.project and project:
                        issue.project = project
                    yield issue
            except Exception as e:
                logger.warning(f"Error reading {json_file}: {e}")
                continue

    def _iterate_s3_issues(self) -> Iterator[Issue]:
        """Iterate over issues from S3."""
        if not self.s3_client:
            logger.error("S3 client not available")
            return

        # Parse S3 path
        # Format: s3://bucket/prefix/
        parts = self.input_dir.replace("s3://", "").split("/", 1)
        bucket = parts[0]
        prefix = parts[1] if len(parts) > 1 else ""

        logger.info(f"Listing objects in s3://{bucket}/{prefix}")

        paginator = self.s3_client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

        count = 0
        for page in pages:
            for obj in page.get("Contents", []):
                key = obj["Key"]

                # Filter by projects
                if self.projects:
                    project = key.split("/")[1] if "/" in key else None
                    if project not in self.projects:
                        continue

                # Only process JSON files
                if not key.endswith(".json"):
                    continue

                try:
                    response = self.s3_client.get_object(Bucket=bucket, Key=key)
                    data = json.loads(response["Body"].read().decode("utf-8"))
                    issue = Issue.from_jira_api(data)
                    yield issue
                    count += 1

                    if count % 100 == 0:
                        logger.info(f"Processed {count} issues from S3")

                except ClientError as e:
                    logger.warning(f"S3 error reading {key}: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Error processing {key}: {e}")
                    continue

        logger.info(f"Total issues processed from S3: {count}")

