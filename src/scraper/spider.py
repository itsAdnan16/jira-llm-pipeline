"""Scrapy spider for Jira issue scraping."""

import json
from datetime import datetime, timedelta
from typing import Iterator, List, Optional
from urllib.parse import urlencode, urljoin

import scrapy
from scrapy.http import Request, Response

from src.config.settings import settings
from src.utils.logger import get_logger
from src.utils.state import FileStateManager

logger = get_logger(__name__)


class JiraSpider(scrapy.Spider):
    """Spider for scraping Jira issues."""

    name = "jira"
    allowed_domains = ["issues.apache.org"]

    def __init__(
        self,
        projects: Optional[str] = None,
        start_date: Optional[str] = None,
        max_issues: Optional[int] = None,
        *args,
        **kwargs,
    ):
        """Initialize spider.

        Args:
            projects: Comma-separated list of project keys
            start_date: Start date in YYYY-MM-DD format
            max_issues: Maximum issues per project
        """
        super().__init__(*args, **kwargs)
        self.projects = (
            [p.strip() for p in projects.split(",")] if projects else settings.jira_projects
        )
        self.start_date = start_date
        self.max_issues = int(max_issues) if max_issues else None
        self.state_manager = FileStateManager()
        logger.info("File-based state manager initialized")

    async def start(self):
        """Generate initial requests for each project (Scrapy 2.13+ async method)."""
        for project in self.projects:
            # Get last update timestamp or use start_date
            last_update = None
            if not self.start_date:
                last_update = self.state_manager.get_last_update(project)
                if last_update:
                    logger.info(f"Resuming {project} from {last_update}")

            if not last_update and self.start_date:
                try:
                    last_update = datetime.strptime(self.start_date, "%Y-%m-%d")
                except ValueError:
                    logger.warning(f"Invalid start_date format: {self.start_date}, using default")
                    last_update = datetime.now() - timedelta(days=30)
            
            # If no date specified at all, start from beginning (no date filter)
            # This allows scraping all historical issues

            # Start with search API
            jql = self._build_jql(project, last_update)
            url = self._build_search_url(jql, start_at=0)
            
            logger.debug(f"Querying {project} with JQL: {jql}")
            logger.debug(f"URL: {url}")

            yield Request(
                url=url,
                callback=self.parse_search_results,
                meta={"project": project, "start_at": 0},
                dont_filter=True,
            )

    def _build_jql(self, project: str, updated_since: Optional[datetime] = None) -> str:
        """Build JQL query for project."""
        jql = f"project = {project}"
        if updated_since:
            jql += f' AND updated >= "{updated_since.strftime("%Y-%m-%d")}"'
        jql += " ORDER BY updated ASC"
        return jql

    def _build_search_url(self, jql: str, start_at: int = 0, max_results: int = 50) -> str:
        """Build Jira search API URL."""
        # Ensure base_url doesn't have trailing slash for proper path construction
        base_url = settings.jira_base_url.rstrip('/')
        api_path = "/rest/api/2/search"
        # Check if base_url already contains /jira in the path
        if '/jira' in base_url or base_url.endswith('jira'):
            # Already has /jira, just append the API path
            full_url = f"{base_url}{api_path}"
        else:
            # Construct full URL using urljoin
            full_url = urljoin(f"{base_url}/", api_path.lstrip('/'))
        # Fields as comma-separated string (Apache Jira format)
        fields_str = ",".join([
            "summary",
            "description",
            "created",
            "updated",
            "status",
            "priority",
            "assignee",
            "reporter",
            "issuetype",
            "resolution",
            "resolutiondate",
            "comment",
        ])
        params = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
            "fields": fields_str,
            "expand": "renderedFields,names",
        }
        return f"{full_url}?{urlencode(params, doseq=False)}"

    def _build_issue_url(self, issue_key: str) -> str:
        """Build Jira issue API URL."""
        # Ensure base_url doesn't have trailing slash for proper path construction
        base_url = settings.jira_base_url.rstrip('/')
        api_path = "/rest/api/2/issue"
        # Check if base_url already contains /jira in the path
        if '/jira' in base_url or base_url.endswith('jira'):
            # Already has /jira, just append the API path
            full_url = f"{base_url}{api_path}"
        else:
            # Construct full URL using urljoin
            full_url = urljoin(f"{base_url}/", api_path.lstrip('/'))
        # Fields as comma-separated string (Apache Jira format)
        fields_str = ",".join([
            "summary",
            "description",
            "created",
            "updated",
            "status",
            "priority",
            "assignee",
            "reporter",
            "issuetype",
            "resolution",
            "resolutiondate",
            "comment",
        ])
        params = {
            "fields": fields_str,
            "expand": "renderedFields,names",
        }
        return f"{full_url}/{issue_key}?{urlencode(params, doseq=False)}"

    def parse_search_results(self, response: Response) -> Iterator[Request]:
        """Parse search results and yield issue requests."""
        # Log response details for debugging
        if response.status != 200:
            logger.error(
                f"API request failed with status {response.status}: {response.url}\n"
                f"Response body (first 500 chars): {response.text[:500]}"
            )
            return
        
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to parse search results: {e}\n"
                f"URL: {response.url}\n"
                f"Response status: {response.status}\n"
                f"Response body (first 500 chars): {response.text[:500]}"
            )
            return

        project = response.meta["project"]
        start_at = response.meta["start_at"]
        issues = data.get("issues", [])
        total = data.get("total", 0)

        logger.info(
            f"Project {project}: Found {total} issues, processing {len(issues)} "
            f"(startAt={start_at})",
            extra={"extra_fields": {"project": project, "total": total, "start_at": start_at}},
        )

        # Yield requests for each issue
        for issue_data in issues:
            issue_key = issue_data.get("key")
            if issue_key:
                issue_url = self._build_issue_url(issue_key)
                yield Request(
                    url=issue_url,
                    callback=self.parse_issue,
                    meta={"project": project, "issue_key": issue_key},
                    errback=self.handle_error,
                )

        # Pagination
        max_results = data.get("maxResults", 50)
        next_start_at = start_at + len(issues)

        if self.max_issues and next_start_at >= self.max_issues:
            logger.info(f"Reached max_issues limit for {project}")
            return

        if next_start_at < total:
            jql = self._build_jql(project)
            next_url = self._build_search_url(jql, start_at=next_start_at, max_results=max_results)

            yield Request(
                url=next_url,
                callback=self.parse_search_results,
                meta={"project": project, "start_at": next_start_at},
                dont_filter=True,
            )

    def parse_issue(self, response: Response) -> dict:
        """Parse individual issue."""
        try:
            data = json.loads(response.text)
            project = response.meta["project"]
            issue_key = response.meta["issue_key"]

            logger.debug(f"Parsed issue: {issue_key}")

            # Return raw issue data for pipelines to process
            return data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse issue {response.meta.get('issue_key')}: {e}")
            return {}

    def handle_error(self, failure):
        """Handle request errors."""
        request = failure.request
        logger.error(
            f"Request failed: {request.url}",
            extra={"extra_fields": {"url": request.url, "error": str(failure.value)}},
        )

