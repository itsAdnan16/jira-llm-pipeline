"""Redis utilities for rate limiting and state management."""

import time
from typing import Optional

import redis
from redis.exceptions import RedisError

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


def get_redis_client() -> redis.Redis:
    """Get Redis client instance."""
    try:
        client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        # Test connection
        client.ping()
        return client
    except RedisError as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise


class RedisRateLimiter:
    """Token bucket rate limiter using Redis."""

    def __init__(
        self,
        redis_client: redis.Redis,
        key_prefix: str = "jira:ratelimit:",
        rps: float = 0.28,
        burst: int = 1,
    ):
        """Initialize rate limiter.

        Args:
            redis_client: Redis client instance
            key_prefix: Prefix for Redis keys
            rps: Requests per second
            burst: Burst size (max tokens)
        """
        self.redis = redis_client
        self.key_prefix = key_prefix
        self.rps = rps
        self.burst = burst
        self.tokens_per_second = 1.0 / rps if rps > 0 else 0

    def _get_key(self, identifier: str) -> str:
        """Get Redis key for identifier."""
        return f"{self.key_prefix}{identifier}"

    def acquire(self, identifier: str, wait: bool = True) -> bool:
        """Acquire a token from the rate limiter.

        Args:
            identifier: Unique identifier (e.g., project key)
            wait: If True, wait until token is available

        Returns:
            True if token acquired, False otherwise
        """
        key = self._get_key(identifier)

        try:
            now = time.time()

            # Use Lua script for atomic operations
            lua_script = """
            local key = KEYS[1]
            local now = tonumber(ARGV[1])
            local tokens_per_second = tonumber(ARGV[2])
            local burst = tonumber(ARGV[3])
            
            local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
            local tokens = tonumber(bucket[1]) or burst
            local last_refill = tonumber(bucket[2]) or now
            
            -- Refill tokens
            local elapsed = now - last_refill
            local new_tokens = math.min(burst, tokens + elapsed * tokens_per_second)
            
            if new_tokens >= 1.0 then
                new_tokens = new_tokens - 1.0
                redis.call('HMSET', key, 'tokens', new_tokens, 'last_refill', now)
                redis.call('EXPIRE', key, 3600)
                return {1, 0}  -- acquired, wait_time
            else
                redis.call('HSET', key, 'last_refill', now)
                redis.call('EXPIRE', key, 3600)
                local wait_time = (1.0 - new_tokens) / tokens_per_second
                return {0, wait_time}  -- not acquired, wait_time
            end
            """

            result = self.redis.eval(
                lua_script,
                1,
                key,
                now,
                self.tokens_per_second,
                self.burst,
            )

            acquired = result[0] == 1
            wait_time = result[1]

            if acquired:
                return True
            elif wait and wait_time > 0:
                logger.debug(
                    f"Rate limit wait for {identifier}: {wait_time:.2f}s",
                    extra={"extra_fields": {"wait_time": wait_time, "identifier": identifier}},
                )
                time.sleep(wait_time)
                # Retry once after waiting
                return self.acquire(identifier, wait=False)
            else:
                return False

        except RedisError as e:
            logger.warning(f"Redis error in rate limiter: {e}, allowing request")
            # Fail open: allow request if Redis is unavailable
            return True

    def get_last_update(self, project: str) -> Optional[float]:
        """Get last update timestamp for a project.

        Args:
            project: Project key

        Returns:
            Unix timestamp or None
        """
        key = f"jira:last_update:{project}"
        try:
            value = self.redis.get(key)
            return float(value) if value else None
        except (RedisError, ValueError):
            return None

    def set_last_update(self, project: str, timestamp: float) -> None:
        """Set last update timestamp for a project.

        Args:
            project: Project key
            timestamp: Unix timestamp
        """
        key = f"jira:last_update:{project}"
        try:
            self.redis.set(key, str(timestamp))
        except RedisError as e:
            logger.warning(f"Failed to update last_update for {project}: {e}")

    def is_duplicate(self, issue_key: str) -> bool:
        """Check if issue has been processed.

        Args:
            issue_key: Issue key (e.g., "HADOOP-1234")

        Returns:
            True if duplicate
        """
        key = f"jira:processed:{issue_key}"
        try:
            return self.redis.exists(key) > 0
        except RedisError:
            return False

    def mark_processed(self, issue_key: str, ttl: int = 86400 * 30) -> None:
        """Mark issue as processed.

        Args:
            issue_key: Issue key
            ttl: Time to live in seconds (default: 30 days)
        """
        key = f"jira:processed:{issue_key}"
        try:
            self.redis.setex(key, ttl, "1")
        except RedisError as e:
            logger.warning(f"Failed to mark {issue_key} as processed: {e}")

