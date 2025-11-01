"""Tests for validation pipeline."""

import pytest
from scrapy.exceptions import DropItem

from src.models.issue import Issue
from src.scraper.pipelines.validation import ValidationPipeline


def test_validation_pipeline_valid_issue():
    """Test validation with valid issue."""
    pipeline = ValidationPipeline(strict_mode=False)

    issue_data = {
        "key": "HADOOP-1234",
        "fields": {
            "project": {"key": "HADOOP"},
            "summary": "Test issue",
            "description": "Test description",
            "created": "2024-01-15T10:30:00.000+0000",
            "updated": "2024-01-15T11:30:00.000+0000",
            "status": {"name": "Open"},
            "priority": {"name": "High"},
            "reporter": {"name": "testuser"},
            "issuetype": {"name": "Bug"},
            "comment": {"comments": []},
        },
    }

    result = pipeline.process_item(issue_data, None)
    assert isinstance(result, Issue)
    assert result.key == "HADOOP-1234"


def test_validation_pipeline_invalid_issue():
    """Test validation with invalid issue (non-strict mode)."""
    pipeline = ValidationPipeline(strict_mode=False)

    issue_data = {
        "key": "HADOOP-1234",
        "fields": {
            # Missing required fields
            "project": {"key": "HADOOP"},
        },
    }

    with pytest.raises(DropItem):
        pipeline.process_item(issue_data, None)


def test_validation_pipeline_strict_mode():
    """Test validation with strict mode enabled."""
    pipeline = ValidationPipeline(strict_mode=True)

    issue_data = {
        "key": "HADOOP-1234",
        "fields": {
            # Missing required fields
            "project": {"key": "HADOOP"},
        },
    }

    with pytest.raises(Exception):  # Should raise validation error
        pipeline.process_item(issue_data, None)

