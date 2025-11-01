"""Integration tests for scraper."""

import json
import os
from pathlib import Path

import pytest

from src.models.issue import Issue
from src.transform.corpus_builder import CorpusBuilder


@pytest.fixture
def sample_issue_data():
    """Sample Jira issue data."""
    return {
        "key": "HADOOP-1234",
        "fields": {
            "project": {"key": "HADOOP"},
            "summary": "Test issue",
            "description": "This is a test issue description",
            "created": "2024-01-15T10:30:00.000+0000",
            "updated": "2024-01-15T11:30:00.000+0000",
            "status": {"name": "Resolved"},
            "priority": {"name": "High"},
            "assignee": None,
            "reporter": {"name": "testuser", "displayName": "Test User"},
            "issuetype": {"name": "Bug"},
            "resolution": {"name": "Fixed"},
            "resolutiondate": "2024-01-15T12:00:00.000+0000",
            "comment": {
                "comments": [
                    {
                        "id": "12345",
                        "author": {"name": "developer", "displayName": "Developer"},
                        "body": "This was fixed by applying a patch. The root cause was a race condition.",
                        "created": "2024-01-15T12:00:00.000+0000",
                        "updated": "2024-01-15T12:00:00.000+0000",
                    }
                ]
            },
        },
    }


@pytest.fixture
def local_data_dir(tmp_path, sample_issue_data):
    """Create local data directory with sample issue."""
    data_dir = tmp_path / "data" / "raw" / "HADOOP"
    data_dir.mkdir(parents=True, exist_ok=True)

    issue_file = data_dir / "HADOOP-1234.json"
    with open(issue_file, "w") as f:
        json.dump(sample_issue_data, f)

    return str(tmp_path / "data" / "raw")


def test_corpus_builder_local(local_data_dir, tmp_path):
    """Test corpus builder with local files."""
    output_path = str(tmp_path / "corpus.jsonl")

    builder = CorpusBuilder(
        input_dir=local_data_dir,
        output_path=output_path,
        projects=["HADOOP"],
    )

    count = builder.build()
    assert count == 1

    # Verify output
    assert os.path.exists(output_path)
    with open(output_path, "r") as f:
        line = f.readline()
        data = json.loads(line)
        assert "instruction" in data
        assert "response" in data
        assert "input" in data


def test_issue_model_from_api(sample_issue_data):
    """Test Issue model parsing from API response."""
    issue = Issue.from_jira_api(sample_issue_data)

    assert issue.key == "HADOOP-1234"
    assert issue.project == "HADOOP"
    assert issue.fields.summary == "Test issue"
    assert len(issue.comments) == 1
    assert "race condition" in issue.comments[0].body.lower()


def test_issue_get_resolution_comments(sample_issue_data):
    """Test getting resolution comments."""
    issue = Issue.from_jira_api(sample_issue_data)

    resolution_comments = issue.get_resolution_comments()
    assert len(resolution_comments) >= 1
    assert any("fix" in c.body.lower() or "patch" in c.body.lower() for c in resolution_comments)

