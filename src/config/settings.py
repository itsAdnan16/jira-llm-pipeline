"""Application settings using pydantic-settings."""

from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Jira Configuration
    jira_base_url: str = Field(
        default="https://issues.apache.org/jira",
        description="Base URL for Jira instance",
    )
    jira_projects: List[str] = Field(
        default=["HADOOP", "SPARK", "KAFKA"],
        description="List of Jira project keys to scrape",
    )

    # AWS S3 Configuration
    aws_access_key_id: Optional[str] = Field(default=None, description="AWS access key")
    aws_secret_access_key: Optional[str] = Field(
        default=None, description="AWS secret key"
    )
    aws_region: str = Field(default="us-east-1", description="AWS region")
    aws_s3_bucket: str = Field(
        default="jira-llm-corpus", description="S3 bucket for raw storage"
    )
    aws_s3_endpoint_url: Optional[str] = Field(
        default=None, description="S3 endpoint URL (for LocalStack/testing)"
    )

    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )
    redis_rate_limit_key_prefix: str = Field(
        default="jira:ratelimit:", description="Redis key prefix for rate limiting"
    )

    # Rate Limiting
    rate_limit_rps: float = Field(
        default=0.28, description="Requests per second per project (~1 req/3.6 sec)"
    )
    rate_limit_burst: int = Field(
        default=1, description="Burst size for token bucket"
    )

    # Scrapy Settings
    scrapy_download_delay: float = Field(
        default=3.6, description="Download delay in seconds"
    )
    scrapy_randomize_download_delay: float = Field(
        default=0.5, description="Randomize download delay by this fraction"
    )
    scrapy_concurrent_requests: int = Field(
        default=1, description="Concurrent requests"
    )
    scrapy_concurrent_requests_per_domain: int = Field(
        default=1, description="Concurrent requests per domain"
    )

    # Retry Configuration
    retry_max_times: int = Field(default=5, description="Maximum retry attempts")
    retry_start_delay: float = Field(
        default=1.0, description="Initial retry delay in seconds"
    )
    retry_max_delay: float = Field(
        default=300.0, description="Maximum retry delay in seconds"
    )
    retry_exponential_base: float = Field(
        default=2.0, description="Exponential backoff base"
    )

    # Validation
    validation_strict_mode: bool = Field(
        default=False, description="Fail on validation errors vs skip"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="json", description="Log format: json or text"
    )

    # Prometheus
    prometheus_enabled: bool = Field(
        default=True, description="Enable Prometheus metrics"
    )
    prometheus_port: int = Field(default=9090, description="Prometheus metrics port")

    @field_validator("jira_projects", mode="before")
    @classmethod
    def parse_jira_projects(cls, v: any) -> List[str]:
        """Parse Jira projects from string or list."""
        if isinstance(v, str):
            return [p.strip() for p in v.split(",") if p.strip()]
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()


# Global settings instance
settings = Settings()

