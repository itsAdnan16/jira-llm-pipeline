"""Scrapy settings configuration."""

from src.config.settings import settings

# Keep SCRAPY_SETTINGS dict for CLI usage
SCRAPY_SETTINGS = {
    # Basic settings
    "BOT_NAME": "jira-scraper",
    "USER_AGENT": "jira-llm-pipeline/1.0 (+https://github.com/yourorg/jira-llm-pipeline)",
    "ROBOTSTXT_OBEY": False,  # Jira doesn't use robots.txt for API
    
    # Spider modules
    "SPIDER_MODULES": ["src.scraper"],

    # Download settings
    "DOWNLOAD_DELAY": settings.scrapy_download_delay,
    "RANDOMIZE_DOWNLOAD_DELAY": settings.scrapy_randomize_download_delay,
    "CONCURRENT_REQUESTS": settings.scrapy_concurrent_requests,
    "CONCURRENT_REQUESTS_PER_DOMAIN": settings.scrapy_concurrent_requests_per_domain,
    "CONCURRENT_REQUESTS_PER_IP": 1,

    # Retry settings
    "RETRY_ENABLED": True,
    "RETRY_TIMES": settings.retry_max_times,
    "RETRY_HTTP_CODES": [500, 502, 503, 504, 522, 524, 408, 429],
    "retry_start_delay": settings.retry_start_delay,
    "retry_max_delay": settings.retry_max_delay,
    "retry_exponential_base": settings.retry_exponential_base,

    # HTTP error handling
    "HTTPERROR_ALLOWED_CODES": [404, 429],  # 404 for missing issues, 429 for rate limit

    # Pipeline settings
    "ITEM_PIPELINES": {
        "src.scraper.pipelines.validation.ValidationPipeline": 300,
        "src.scraper.pipelines.storage.StoragePipeline": 400,
    },

    # Middleware settings
    "DOWNLOADER_MIDDLEWARES": {
        "src.scraper.middlewares.RateLimitMiddleware": 543,
        "src.scraper.middlewares.RetryMiddleware": 544,
        "src.scraper.middlewares.MetricsMiddleware": 545,
    },

    # Extensions
    "EXTENSIONS": {
        "scrapy.extensions.telnet.TelnetConsole": None,  # Disable telnet
    },

    # Logging
    "LOG_LEVEL": settings.log_level,
    "LOG_FORMAT": "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
}

# Also export as Scrapy settings variables for auto-discovery
BOT_NAME = SCRAPY_SETTINGS["BOT_NAME"]
USER_AGENT = SCRAPY_SETTINGS["USER_AGENT"]
ROBOTSTXT_OBEY = SCRAPY_SETTINGS["ROBOTSTXT_OBEY"]
SPIDER_MODULES = SCRAPY_SETTINGS["SPIDER_MODULES"]
DOWNLOAD_DELAY = SCRAPY_SETTINGS["DOWNLOAD_DELAY"]
RANDOMIZE_DOWNLOAD_DELAY = SCRAPY_SETTINGS["RANDOMIZE_DOWNLOAD_DELAY"]
CONCURRENT_REQUESTS = SCRAPY_SETTINGS["CONCURRENT_REQUESTS"]
CONCURRENT_REQUESTS_PER_DOMAIN = SCRAPY_SETTINGS["CONCURRENT_REQUESTS_PER_DOMAIN"]
CONCURRENT_REQUESTS_PER_IP = SCRAPY_SETTINGS["CONCURRENT_REQUESTS_PER_IP"]
RETRY_ENABLED = SCRAPY_SETTINGS["RETRY_ENABLED"]
RETRY_TIMES = SCRAPY_SETTINGS["RETRY_TIMES"]
RETRY_HTTP_CODES = SCRAPY_SETTINGS["RETRY_HTTP_CODES"]
HTTPERROR_ALLOWED_CODES = SCRAPY_SETTINGS["HTTPERROR_ALLOWED_CODES"]
ITEM_PIPELINES = SCRAPY_SETTINGS["ITEM_PIPELINES"]
DOWNLOADER_MIDDLEWARES = SCRAPY_SETTINGS["DOWNLOADER_MIDDLEWARES"]
EXTENSIONS = SCRAPY_SETTINGS["EXTENSIONS"]
LOG_LEVEL = SCRAPY_SETTINGS["LOG_LEVEL"]
LOG_FORMAT = SCRAPY_SETTINGS["LOG_FORMAT"]
