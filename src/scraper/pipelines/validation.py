"""Validation pipeline for Jira issues."""

from typing import Any

from scrapy import Item, Spider

from src.models.issue import Issue
from src.scraper.middlewares import validation_errors
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ValidationPipeline:
    """Validate and parse Jira issues using Pydantic models."""

    def __init__(self, strict_mode: bool = False):
        """Initialize validation pipeline.

        Args:
            strict_mode: If True, raise exceptions on validation errors
        """
        self.strict_mode = strict_mode

    @classmethod
    def from_crawler(cls, crawler):
        """Create pipeline from crawler settings."""
        strict_mode = crawler.settings.getbool("VALIDATION_STRICT_MODE", False)
        return cls(strict_mode=strict_mode)

    def process_item(self, item: Item, spider: Spider) -> Any:
        """Process and validate item."""
        try:
            # Convert dict item to Issue model
            if isinstance(item, dict):
                issue = Issue.from_jira_api(item)
            else:
                issue = item

            # Validate
            issue.model_validate(issue.model_dump())

            # Replace item with validated issue
            return issue

        except Exception as e:
            error_type = type(e).__name__
            project = item.get("fields", {}).get("project", {}).get("key", "unknown")
            issue_key = item.get("key", "unknown")

            if validation_errors:
                validation_errors.labels(project=project, error_type=error_type).inc()

            logger.warning(
                f"Validation error for {issue_key}: {error_type}: {e}",
                extra={"extra_fields": {"issue_key": issue_key, "project": project, "error": str(e)}},
            )

            if self.strict_mode:
                raise

            # Skip invalid items in non-strict mode
            from scrapy.exceptions import DropItem

            raise DropItem(f"Invalid issue {issue_key}: {e}")

