"""Scrapy middlewares for rate limiting, retry, and metrics."""

import time
from typing import Any, Optional

from prometheus_client import Counter, Histogram
from scrapy import Request, Spider
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.http import Response
from scrapy.utils.defer import deferred_from_coro

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Prometheus metrics
if settings.prometheus_enabled:
    issues_scraped_total = Counter(
        "jira_issues_scraped_total",
        "Total issues scraped",
        ["project"],
    )
    api_requests_total = Counter(
        "jira_api_requests_total",
        "Total API requests made",
        ["project", "status"],
    )
    rate_limit_wait = Histogram(
        "jira_rate_limit_wait_seconds",
        "Time spent waiting for rate limits",
        ["project"],
    )
    validation_errors = Counter(
        "jira_validation_errors",
        "Validation errors encountered",
        ["project", "error_type"],
    )
else:
    # Dummy metrics when Prometheus is disabled
    issues_scraped_total = None
    api_requests_total = None
    rate_limit_wait = None
    validation_errors = None


class RateLimitMiddleware:
    """Simple rate limiting middleware using Scrapy's download delay.
    
    Rate limiting is handled by Scrapy's built-in DOWNLOAD_DELAY setting.
    This middleware exists for compatibility and metrics collection.
    """

    def __init__(self):
        """Initialize rate limiter."""
        logger.info(f"Rate limiting via Scrapy DOWNLOAD_DELAY: {settings.scrapy_download_delay}s")

    def process_request(self, request: Request, spider: Spider) -> Optional[Any]:
        """Process request (rate limiting handled by Scrapy)."""
        # Rate limiting is handled by Scrapy's DOWNLOAD_DELAY setting
        # This middleware can be used for metrics collection if needed
        return None

    @staticmethod
    def _extract_project_from_url(url: str) -> Optional[str]:
        """Extract project key from Jira URL."""
        # URL format: https://issues.apache.org/jira/rest/api/2/issue/HADOOP-1234
        try:
            parts = url.split("/")
            issue_part = [p for p in parts if "-" in p and p[0].isalpha()][0]
            project = issue_part.split("-")[0]
            return project
        except (IndexError, AttributeError):
            return None


class RetryMiddleware(RetryMiddleware):
    """Enhanced retry middleware with exponential backoff."""

    def __init__(self, settings):
        """Initialize retry middleware."""
        super().__init__(settings)
        self.start_delay = getattr(settings, "retry_start_delay", 1.0)
        self.max_delay = getattr(settings, "retry_max_delay", 300.0)
        self.exponential_base = getattr(settings, "retry_exponential_base", 2.0)

    def process_response(
        self, request: Request, response: Response, spider: Spider
    ) -> Optional[Request]:
        """Process response and retry if needed."""
        # Check if we should retry
        if response.status in self.retry_http_codes:
            reason = f"HTTP {response.status}"
            # Check for Retry-After header (especially for 429)
            retry_after = None
            if response.status == 429:
                retry_after_header = response.headers.get("Retry-After")
                if retry_after_header:
                    try:
                        # Retry-After can be a number of seconds (int) or HTTP date string
                        retry_after = float(retry_after_header.decode("utf-8"))
                    except (ValueError, AttributeError):
                        # If it's a date string, we'd need to parse it, but for simplicity,
                        # we'll fall back to exponential backoff
                        logger.debug(f"Retry-After header value not a number: {retry_after_header}")
            
            return self._retry(request, reason, spider, retry_after=retry_after)

        # Call parent implementation
        return super().process_response(request, response, spider)

    def process_exception(
        self, request: Request, exception: Exception, spider: Spider
    ) -> Optional[Request]:
        """Process exception and retry if needed."""
        return self._retry(request, str(exception), spider, retry_after=None)

    def _retry(self, request: Request, reason: str, spider: Spider, retry_after: Optional[float] = None) -> Optional[Request]:
        """Retry request with exponential backoff or Retry-After header delay."""
        retry_times = request.meta.get("retry_times", 0) + 1

        if retry_times <= self.max_retry_times:
            # Use Retry-After header value if provided, otherwise exponential backoff
            if retry_after is not None:
                delay = min(float(retry_after), self.max_delay)
                logger.debug(
                    f"Retrying {request} (attempt {retry_times}/{self.max_retry_times}) "
                    f"after {delay:.2f}s (Retry-After header): {reason}",
                    extra={"extra_fields": {"retry_times": retry_times, "delay": delay, "reason": reason, "retry_after": True}},
                )
            else:
                # Calculate delay with exponential backoff
                delay = min(
                    self.start_delay * (self.exponential_base ** (retry_times - 1)),
                    self.max_delay,
                )
                logger.debug(
                    f"Retrying {request} (attempt {retry_times}/{self.max_retry_times}) "
                    f"after {delay:.2f}s (exponential backoff): {reason}",
                    extra={"extra_fields": {"retry_times": retry_times, "delay": delay, "reason": reason}},
                )

            retryreq = request.copy()
            retryreq.meta["retry_times"] = retry_times
            retryreq.meta["download_delay"] = delay
            retryreq.dont_filter = True
            return retryreq
        else:
            logger.error(f"Gave up retrying {request} after {retry_times} attempts: {reason}")
            return None


class MetricsMiddleware:
    """Middleware for Prometheus metrics collection."""

    def process_response(
        self, request: Request, response: Response, spider: Spider
    ) -> Optional[Response]:
        """Record metrics for response."""
        if not api_requests_total:
            return response

        project = request.meta.get("project") or RateLimitMiddleware._extract_project_from_url(
            request.url
        )
        status = str(response.status)

        api_requests_total.labels(project=project or "unknown", status=status).inc()

        return response

