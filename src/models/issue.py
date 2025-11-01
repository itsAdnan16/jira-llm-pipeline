"""Pydantic models for Jira issue data structures."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class IssueFields(BaseModel):
    """Jira issue fields."""

    summary: str
    description: Optional[str] = None
    created: datetime
    updated: datetime
    status: dict[str, Any] = Field(default_factory=dict)
    priority: dict[str, Any] = Field(default_factory=dict)
    assignee: Optional[dict[str, Any]] = None
    reporter: dict[str, Any] = Field(default_factory=dict)
    issue_type: dict[str, Any] = Field(alias="issuetype", default_factory=dict)
    resolution: Optional[dict[str, Any]] = None
    resolutiondate: Optional[datetime] = None
    comments: Optional[dict[str, Any]] = None

    @field_validator("created", "updated", mode="before")
    @classmethod
    def parse_datetime(cls, v: Any) -> datetime:
        """Parse Jira datetime string."""
        if isinstance(v, str):
            # Jira format: "2024-01-15T10:30:00.000+0000"
            return datetime.fromisoformat(v.replace("+0000", "+00:00"))
        return v

    @field_validator("resolutiondate", mode="before")
    @classmethod
    def parse_resolution_date(cls, v: Any) -> Optional[datetime]:
        """Parse resolution date."""
        if v is None:
            return None
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("+0000", "+00:00"))
        return v


class IssueComment(BaseModel):
    """Jira issue comment."""

    id: str
    author: dict[str, Any]
    body: str
    created: datetime
    updated: Optional[datetime] = None

    @field_validator("created", "updated", mode="before")
    @classmethod
    def parse_datetime(cls, v: Any) -> Optional[datetime]:
        """Parse Jira datetime string."""
        if v is None:
            return None
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("+0000", "+00:00"))
        return v

    def contains_resolution_keywords(self) -> bool:
        """Check if comment contains resolution-related keywords."""
        keywords = ["fix", "patch", "cause", "pr", "pull request", "solution", "resolved"]
        body_lower = self.body.lower()
        return any(keyword in body_lower for keyword in keywords)


class Issue(BaseModel):
    """Complete Jira issue model."""

    key: str
    project: str
    fields: IssueFields
    comments: list[IssueComment] = Field(default_factory=list)

    @classmethod
    def from_jira_api(cls, data: dict[str, Any]) -> "Issue":
        """Parse issue from Jira REST API response."""
        key = data["key"]
        project = data["fields"].get("project", {}).get("key", "")
        
        # Fallback: extract project from issue key if not found in fields
        # Format: "HADOOP-125" -> "HADOOP"
        if not project and "-" in key:
            project = key.split("-")[0]

        # Extract comments if present
        comments_data = data.get("fields", {}).get("comment", {}).get("comments", [])
        comments = [
            IssueComment(
                id=str(c.get("id", "")),
                author=c.get("author", {}),
                body=c.get("body", ""),
                created=c.get("created"),
                updated=c.get("updated"),
            )
            for c in comments_data
        ]

        return cls(
            key=key,
            project=project,
            fields=IssueFields(**data["fields"]),
            comments=comments,
        )

    def get_resolution_comments(self, limit: int = 3) -> list[IssueComment]:
        """Get top comments that likely contain resolution information."""
        resolution_comments = [
            c for c in self.comments if c.contains_resolution_keywords()
        ]
        # Sort by created date (newest first) and limit
        resolution_comments.sort(key=lambda x: x.created, reverse=True)
        return resolution_comments[:limit]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "key": self.key,
            "project": self.project,
            "fields": self.fields.model_dump(),
            "comments": [c.model_dump() for c in self.comments],
        }

