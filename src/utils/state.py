"""File-based state management for resume functionality and deduplication."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Set

from src.utils.logger import get_logger

logger = get_logger(__name__)


class FileStateManager:
    """Simple file-based state manager for resume and deduplication."""

    def __init__(self, state_dir: str = "data/state"):
        """Initialize state manager.
        
        Args:
            state_dir: Directory to store state files
        """
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._last_update_file = self.state_dir / "last_updates.json"
        self._processed_file = self.state_dir / "processed_issues.json"
        self._last_updates: dict[str, float] = self._load_last_updates()
        self._processed_issues: Set[str] = self._load_processed_issues()

    def _load_last_updates(self) -> dict[str, float]:
        """Load last update timestamps from file."""
        if not self._last_update_file.exists():
            return {}
        try:
            with open(self._last_update_file, "r") as f:
                data = json.load(f)
                return {k: float(v) for k, v in data.items()}
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load last updates: {e}")
            return {}

    def _save_last_updates(self) -> None:
        """Save last update timestamps to file."""
        try:
            with open(self._last_update_file, "w") as f:
                json.dump(self._last_updates, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save last updates: {e}")

    def _load_processed_issues(self) -> Set[str]:
        """Load processed issues from file."""
        if not self._processed_file.exists():
            return set()
        try:
            with open(self._processed_file, "r") as f:
                data = json.load(f)
                return set(data.get("issues", []))
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load processed issues: {e}")
            return set()

    def _save_processed_issues(self) -> None:
        """Save processed issues to file."""
        try:
            # Keep only last 10000 issues to avoid huge files
            issues_list = list(self._processed_issues)
            if len(issues_list) > 10000:
                issues_list = issues_list[-10000:]
            
            with open(self._processed_file, "w") as f:
                json.dump({"issues": issues_list}, f)
        except IOError as e:
            logger.error(f"Failed to save processed issues: {e}")

    def get_last_update(self, project: str) -> Optional[datetime]:
        """Get last update timestamp for a project.
        
        Args:
            project: Project key
            
        Returns:
            Datetime of last update or None
        """
        timestamp = self._last_updates.get(project)
        if timestamp:
            return datetime.fromtimestamp(timestamp)
        return None

    def set_last_update(self, project: str, timestamp: datetime) -> None:
        """Set last update timestamp for a project.
        
        Args:
            project: Project key
            timestamp: Datetime of last update
        """
        # Validate project is not empty
        if not project or not project.strip():
            logger.warning(f"Skipping set_last_update for empty project (timestamp: {timestamp})")
            return
        
        self._last_updates[project] = timestamp.timestamp()
        self._save_last_updates()
        logger.debug(f"Updated last_update for {project}: {timestamp}")

    def is_duplicate(self, issue_key: str) -> bool:
        """Check if issue has been processed.
        
        Args:
            issue_key: Issue key (e.g., "HADOOP-1234")
            
        Returns:
            True if duplicate
        """
        return issue_key in self._processed_issues

    def mark_processed(self, issue_key: str) -> None:
        """Mark issue as processed.
        
        Args:
            issue_key: Issue key
        """
        self._processed_issues.add(issue_key)
        # Periodically save (every 100 issues)
        if len(self._processed_issues) % 100 == 0:
            self._save_processed_issues()

    def flush(self) -> None:
        """Flush all state to disk."""
        self._save_last_updates()
        self._save_processed_issues()

