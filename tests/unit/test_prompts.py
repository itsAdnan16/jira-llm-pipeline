"""Tests for prompt building."""

from datetime import datetime

from src.models.issue import Issue, IssueComment, IssueFields
from src.transform.prompts import PromptBuilder


def test_build_instruction():
    """Test instruction building."""
    fields = IssueFields(
        summary="Test issue",
        description="Test description",
        created=datetime.now(),
        updated=datetime.now(),
        status={"name": "Open"},
        issue_type={"name": "Bug"},
        priority={"name": "High"},
        reporter={},
    )

    issue = Issue(
        key="HADOOP-1234",
        project="HADOOP",
        fields=fields,
    )

    instruction = PromptBuilder.build_instruction(issue)
    assert "Test issue" in instruction
    assert "Test description" in instruction
    assert "Open" in instruction
    assert "Bug" in instruction


def test_build_response_with_comments():
    """Test response building with resolution comments."""
    fields = IssueFields(
        summary="Test issue",
        description="Test description",
        created=datetime.now(),
        updated=datetime.now(),
        status={"name": "Resolved"},
        reporter={},
    )

    comments = [
        IssueComment(
            id="1",
            author={"name": "developer"},
            body="This was fixed by applying patch XYZ. The root cause was...",
            created=datetime.now(),
        ),
        IssueComment(
            id="2",
            author={"name": "reviewer"},
            body="Looks good!",
            created=datetime.now(),
        ),
    ]

    issue = Issue(key="HADOOP-1234", project="HADOOP", fields=fields, comments=comments)

    response = PromptBuilder.build_response(issue)
    assert "fixed" in response.lower() or "patch" in response.lower()


def test_build_response_no_comments():
    """Test response building without resolution comments."""
    fields = IssueFields(
        summary="Test issue",
        description="Test description",
        created=datetime.now(),
        updated=datetime.now(),
        status={"name": "Open"},
        reporter={},
    )

    issue = Issue(key="HADOOP-1234", project="HADOOP", fields=fields, comments=[])

    response = PromptBuilder.build_response(issue)
    assert "No resolution" in response or "No resolution information" in response


def test_build_alpaca_format():
    """Test Alpaca format building."""
    fields = IssueFields(
        summary="Test issue",
        description="Test description",
        created=datetime.now(),
        updated=datetime.now(),
        status={"name": "Resolved"},
        reporter={},
    )

    comments = [
        IssueComment(
            id="1",
            author={"name": "developer"},
            body="Fixed by applying patch.",
            created=datetime.now(),
        ),
    ]

    issue = Issue(key="HADOOP-1234", project="HADOOP", fields=fields, comments=comments)

    alpaca = PromptBuilder.build_alpaca_format(issue)
    assert "instruction" in alpaca
    assert "response" in alpaca
    assert "input" in alpaca
    assert alpaca["input"] == ""


def test_clean_text():
    """Test text cleaning."""
    html_text = "<p>This is <b>bold</b> text</p>"
    cleaned = PromptBuilder._clean_text(html_text)
    assert "<" not in cleaned
    assert ">" not in cleaned
    assert "This is bold text" in cleaned

