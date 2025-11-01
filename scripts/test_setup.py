#!/usr/bin/env python3
"""Test script to verify project setup and dependencies."""

import sys
import json
from pathlib import Path


def test_imports():
    """Test if all required modules can be imported."""
    print("Testing imports...")
    try:
        import scrapy
        print(f"✓ scrapy {scrapy.__version__}")
    except ImportError as e:
        print(f"✗ scrapy: {e}")
        return False

    try:
        import pydantic
        print(f"✓ pydantic {pydantic.__version__}")
    except ImportError as e:
        print(f"✗ pydantic: {e}")
        return False

    try:
        import boto3
        print(f"✓ boto3 {boto3.__version__}")
    except ImportError as e:
        print(f"✗ boto3: {e}")
        return False

    try:
        import redis
        print(f"✓ redis {redis.__version__}")
    except ImportError as e:
        print(f"✗ redis: {e}")
        return False

    try:
        import prometheus_client
        print(f"✓ prometheus_client")
    except ImportError as e:
        print(f"✗ prometheus_client: {e}")
        return False

    # Test project imports
    try:
        from src.config.settings import settings
        print(f"✓ src.config.settings")
    except Exception as e:
        print(f"✗ src.config.settings: {e}")
        return False

    try:
        from src.models.issue import Issue
        print(f"✓ src.models.issue")
    except Exception as e:
        print(f"✗ src.models.issue: {e}")
        return False

    try:
        from src.scraper.spider import JiraSpider
        print(f"✓ src.scraper.spider")
    except Exception as e:
        print(f"✗ src.scraper.spider: {e}")
        return False

    return True


def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")
    try:
        from src.config.settings import settings

        print(f"✓ Jira URL: {settings.jira_base_url}")
        print(f"✓ Projects: {settings.jira_projects}")
        print(f"✓ Redis URL: {settings.redis_url}")
        print(f"✓ S3 Bucket: {settings.aws_s3_bucket}")
        print(f"✓ Rate Limit: {settings.rate_limit_rps} req/sec")
        return True
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return False


def test_redis_connection():
    """Test Redis connection."""
    print("\nTesting Redis connection...")
    try:
        from src.utils.redis import get_redis_client

        client = get_redis_client()
        client.ping()
        print("✓ Redis connection successful")
        return True
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        print("  Make sure Redis is running: docker run -d -p 6379:6379 redis:7-alpine")
        return False


def test_models():
    """Test Pydantic models."""
    print("\nTesting Pydantic models...")
    try:
        from src.models.issue import Issue
        from datetime import datetime

        # Sample issue data
        issue_data = {
            "key": "HADOOP-1234",
            "fields": {
                "project": {"key": "HADOOP"},
                "summary": "Test issue",
                "description": "Test description",
                "created": "2024-01-15T10:30:00.000+0000",
                "updated": "2024-01-15T11:30:00.000+0000",
                "status": {"name": "Open"},
                "priority": {"name": "High"},
                "reporter": {"name": "testuser"},
                "issuetype": {"name": "Bug"},
                "comment": {"comments": []},
            },
        }

        issue = Issue.from_jira_api(issue_data)
        print(f"✓ Issue model created: {issue.key}")
        print(f"  Project: {issue.project}")
        print(f"  Summary: {issue.fields.summary}")

        # Test serialization
        issue_dict = issue.to_dict()
        assert "key" in issue_dict
        print("✓ Issue serialization works")

        return True
    except Exception as e:
        print(f"✗ Model test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_prompts():
    """Test prompt building."""
    print("\nTesting prompt building...")
    try:
        from src.models.issue import Issue, IssueFields, IssueComment
        from src.transform.prompts import PromptBuilder
        from datetime import datetime

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
                body="Fixed by applying patch. Root cause was...",
                created=datetime.now(),
            )
        ]

        issue = Issue(key="HADOOP-1234", project="HADOOP", fields=fields, comments=comments)

        instruction = PromptBuilder.build_instruction(issue)
        response = PromptBuilder.build_response(issue)
        alpaca = PromptBuilder.build_alpaca_format(issue)

        assert "instruction" in alpaca
        assert "response" in alpaca
        print("✓ Prompt building works")
        print(f"  Instruction length: {len(instruction)} chars")
        print(f"  Response length: {len(response)} chars")

        return True
    except Exception as e:
        print(f"✗ Prompt test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_scrapy_setup():
    """Test Scrapy configuration."""
    print("\nTesting Scrapy setup...")
    try:
        from scrapy.utils.project import get_project_settings

        settings = get_project_settings()
        print("✓ Scrapy settings loaded")
        print(f"  Download delay: {settings.get('DOWNLOAD_DELAY')}")
        print(f"  Concurrent requests: {settings.get('CONCURRENT_REQUESTS')}")
        return True
    except Exception as e:
        print(f"✗ Scrapy setup failed: {e}")
        return False


def test_directory_structure():
    """Test directory structure."""
    print("\nTesting directory structure...")
    required_dirs = [
        "src",
        "src/scraper",
        "src/scraper/pipelines",
        "src/transform",
        "src/models",
        "src/config",
        "src/utils",
        "data/raw",
        "data/corpus",
    ]

    all_exist = True
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"✓ {dir_path}")
        else:
            print(f"✗ {dir_path} (missing)")
            all_exist = False

    return all_exist


def test_sample_scrape():
    """Test a sample scrape (dry run)."""
    print("\nTesting sample scrape capability...")
    try:
        from src.scraper.spider import JiraSpider

        spider = JiraSpider(projects="HADOOP", max_issues=1)
        print(f"✓ Spider initialized: {spider.name}")
        print(f"  Projects: {spider.projects}")
        print(f"  Max issues: {spider.max_issues}")

        # Test JQL building
        from datetime import datetime, timedelta
        jql = spider._build_jql("HADOOP", datetime.now() - timedelta(days=7))
        print(f"  Sample JQL: {jql[:80]}...")

        return True
    except Exception as e:
        print(f"✗ Spider test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Jira LLM Pipeline - Setup Verification")
    print("=" * 60)

    results = {
        "Imports": test_imports(),
        "Configuration": test_config(),
        "Directory Structure": test_directory_structure(),
        "Pydantic Models": test_models(),
        "Prompt Building": test_prompts(),
        "Scrapy Setup": test_scrapy_setup(),
        "Spider Initialization": test_sample_scrape(),
    }

    # Redis is optional for basic tests
    redis_available = test_redis_connection()
    results["Redis Connection"] = redis_available

    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! The project is ready to use.")
        print("\nNext steps:")
        print("  1. Ensure Redis is running (if not already)")
        print("  2. Configure .env file with your settings")
        print("  3. Run: python -m src.cli scrape --projects HADOOP --max-issues 5")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")
        if not results["Redis Connection"]:
            print("\nNote: Redis connection failed, but this is optional for basic testing.")
            print("      You can still test models and prompts without Redis.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

