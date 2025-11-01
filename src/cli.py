"""CLI entrypoint for scraping and transformation."""

import argparse
import sys

from prometheus_client import start_http_server

from src.config.settings import settings
from src.scraper.settings import SCRAPY_SETTINGS
from src.transform.corpus_builder import CorpusBuilder
from src.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


def setup_prometheus():
    """Start Prometheus metrics server."""
    if settings.prometheus_enabled:
        try:
            start_http_server(settings.prometheus_port)
            logger.info(f"Prometheus metrics server started on port {settings.prometheus_port}")
        except Exception as e:
            logger.warning(f"Failed to start Prometheus server: {e}")


def cmd_scrape(args: argparse.Namespace) -> int:
    """Scrape Jira issues.

    Args:
        args: CLI arguments

    Returns:
        Exit code
    """
    from scrapy.cmdline import execute
    from scrapy.utils.project import get_project_settings

    # Merge Scrapy settings
    scrapy_settings = get_project_settings()
    scrapy_settings.update(SCRAPY_SETTINGS)
    scrapy_settings.set("VALIDATION_STRICT_MODE", settings.validation_strict_mode)

    # Build Scrapy command
    scrapy_args = ["scrapy", "crawl", "jira"]

    # Add project arguments
    if args.projects:
        scrapy_args.extend(["-a", f"projects={','.join(args.projects)}"])

    if args.start_date:
        scrapy_args.extend(["-a", f"start_date={args.start_date}"])

    if args.max_issues:
        scrapy_args.extend(["-a", f"max_issues={args.max_issues}"])

    logger.info(f"Starting scraper with args: {' '.join(scrapy_args[2:])}")

    try:
        execute(scrapy_args, settings=scrapy_settings)
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1
    except Exception as e:
        logger.error(f"Scraper error: {e}")
        return 1


def cmd_transform(args: argparse.Namespace) -> int:
    """Transform raw issues to corpus.

    Args:
        args: CLI arguments

    Returns:
        Exit code
    """
    try:
        builder = CorpusBuilder(
            input_dir=args.input_dir,
            output_path=args.output,
            projects=args.projects,
        )

        count = builder.build()
        logger.info(f"Successfully built corpus with {count} issues")
        return 0

    except Exception as e:
        logger.error(f"Transform error: {e}")
        return 1


def main() -> int:
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Jira LLM Corpus Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Scrape command
    scrape_parser = subparsers.add_parser("scrape", help="Scrape Jira issues")
    scrape_parser.add_argument(
        "--projects",
        nargs="+",
        help="Project keys (e.g., HADOOP SPARK KAFKA)",
        default=None,
    )
    scrape_parser.add_argument(
        "--start-date",
        type=str,
        help="Start date (YYYY-MM-DD), defaults to last update",
        default=None,
    )
    scrape_parser.add_argument(
        "--max-issues",
        type=int,
        help="Maximum issues per project",
        default=None,
    )

    # Transform command
    transform_parser = subparsers.add_parser("transform", help="Build corpus from raw issues")
    transform_parser.add_argument(
        "--output",
        type=str,
        default="data/corpus/jira_corpus.jsonl",
        help="Output JSONL file path",
    )
    transform_parser.add_argument(
        "--input-dir",
        type=str,
        default=None,
        help="Input directory (S3 prefix or local path)",
    )
    transform_parser.add_argument(
        "--projects",
        nargs="+",
        help="Filter by project keys",
        default=None,
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Setup logging
    setup_logging()

    # Setup Prometheus
    setup_prometheus()

    # Execute command
    if args.command == "scrape":
        return cmd_scrape(args)
    elif args.command == "transform":
        return cmd_transform(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())

