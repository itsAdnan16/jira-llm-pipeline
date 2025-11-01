# Jira LLM Corpus Pipeline

A production-grade, fault-tolerant web scraping pipeline that extracts public issue data from Apache's Jira instance (defaults to 3 projects: HADOOP, SPARK, KAFKA), validates and transforms it, and outputs a clean JSONL corpus with derived tasks for LLM fine-tuning.

## Features

- **Fault-Tolerant Scraping**: Scrapy-based crawler with automatic retries, exponential backoff, and error handling
- **Resume Capability**: Automatically resumes from the last successful state if interrupted
- **Rate Limiting**: Built-in rate limiting to respect API limits (configurable delays)
- **Deduplication**: Tracks processed issues to avoid duplicates
- **Data Validation**: Pydantic v2 models with graceful error handling
- **Local Storage**: Saves data to local filesystem (no external dependencies required)
- **S3 Support**: Optional AWS S3 integration for cloud storage
- **JSONL Output**: Transforms raw issues into structured JSONL format for LLM training

## Requirements

- **Python 3.11+** (that's it!)

No Docker, Redis, or other external services required. The pipeline uses file-based state management.

## Quick Start

### 1. Setup Environment

```bash
# Clone the repository
git clone <repo-url>
cd scaler

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -e .
```

### 2. Run a Test Scrape

```bash
# Scrape 2 issues from HADOOP project as a test
python -m src.cli scrape --projects HADOOP --max-issues 2

# Check results
dir data\raw\HADOOP\  # Windows
ls data/raw/HADOOP/    # Linux/Mac
```

### 3. Build Corpus

```bash
# Transform raw issues into JSONL format
python -m src.cli transform --output data/corpus/jira_corpus.jsonl

# View the corpus
type data\corpus\jira_corpus.jsonl  # Windows
cat data/corpus/jira_corpus.jsonl   # Linux/Mac
```

## Architecture

```
┌─────────────┐
│  Jira API   │
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌──────────┐     ┌──────────┐
│   Scrapy    │────▶│   Local  │────▶│ Transform│
│   Spider    │     │  Storage │     │ Pipeline │
└──────┬──────┘     └──────────┘     └────┬─────┘
       │                                   │
       ▼                                   ▼
┌─────────────┐                      ┌──────────┐
│ File-Based  │                      │  JSONL   │
│ State Mgmt  │                      │  Corpus  │
│ (resume)    │                      └──────────┘
└─────────────┘
```

## CLI Commands

### Scrape Issues

Scrape issues from Apache Jira with automatic resume capability:

```bash
# Scrape all issues from specified projects
python -m src.cli scrape --projects HADOOP SPARK KAFKA

# Scrape with limits
python -m src.cli scrape --projects HADOOP --max-issues 100

# Scrape from a specific date
python -m src.cli scrape --projects HADOOP --start-date 2024-01-01
```

**Options:**
- `--projects`: Space-separated list of Jira project keys (default: HADOOP, SPARK, KAFKA)
- `--start-date`: Start date in YYYY-MM-DD format (default: last successful scrape)
- `--max-issues`: Maximum issues per project (default: unlimited)

**Resume Functionality:**
- The scraper automatically saves state to `data/state/last_updates.json`
- If interrupted, it resumes from the last processed timestamp
- Delete `data/state/` to start fresh

### Transform to JSONL

Convert raw scraped issues into JSONL format for LLM training:

```bash
# Transform all scraped issues
python -m src.cli transform --output data/corpus/jira_corpus.jsonl

# Transform specific projects
python -m src.cli transform --output data/corpus/hadoop.jsonl --projects HADOOP
```

**Options:**
- `--output`: Output JSONL file path (required)
- `--input-dir`: Input directory with raw JSON files (default: `data/raw/`)
- `--projects`: Filter by specific projects (optional)

## Configuration

Configuration is managed via environment variables or a `.env` file. See `src/config/settings.py` for all options.

**Key Settings (all optional with sensible defaults):**

```bash
# Jira Configuration
JIRA_BASE_URL=https://issues.apache.org/jira
JIRA_PROJECTS=HADOOP,SPARK,KAFKA

# Rate Limiting (seconds between requests)
SCRAPY_DOWNLOAD_DELAY=3.6

# Retry Configuration
RETRY_MAX_TIMES=5
RETRY_START_DELAY=1.0
RETRY_MAX_DELAY=300.0

# Optional: AWS S3 (for cloud storage)
AWS_S3_BUCKET=jira-llm-corpus
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret

# Logging
LOG_LEVEL=INFO
```

## How It Works

### 1. Data Scraping

The scraper uses **Jira's REST API** (not HTML scraping) for efficient, reliable data extraction:
- **Fetches issues** via Jira REST API (`/rest/api/2/search` and `/rest/api/2/issue`) with pagination support
- **Handles rate limits** using configurable delays (default: 3.6s between requests)
- **Resumes automatically** from the last successful timestamp per project
- **Handles errors** with exponential backoff retries for:
  - HTTP 429 (rate limit): Respects Retry-After headers when present
  - HTTP 5xx errors: Automatic retry with exponential backoff
  - Network timeouts: Configurable timeout handling
  - Empty or malformed responses: Graceful error logging

**Resume Mechanism:**
- Tracks last update timestamp per project in `data/state/last_updates.json`
- On restart, queries Jira for issues updated since last timestamp
- Automatically skips already-processed issues

**Deduplication:**
- Maintains a set of processed issue keys in `data/state/processed_issues.json`
- Skips issues that have already been scraped

### 2. Data Transformation

Transforms raw Jira JSON into structured JSONL format with derived tasks:

**Input:** Raw issue JSON files from `data/raw/{project}/{ISSUE-KEY}.json`

**Output:** JSONL file where each line contains issue metadata, description, comments, and **derived tasks** (summarization, classification, Q&A):

```json
{
  "metadata": {
    "issue_key": "HADOOP-1234",
    "project": "HADOOP",
    "title": "Issue summary",
    "status": "Resolved",
    "priority": "High",
    "reporter": "username",
    "assignee": "developer",
    "created": "2024-01-15T10:30:00Z",
    "updated": "2024-01-20T15:45:00Z",
    "resolution": "Fixed"
  },
  "description": "Full issue description as plain text",
  "comments": [
    {
      "author": "developer",
      "body": "Comment text as plain text",
      "created": "2024-01-16T12:00:00Z"
    }
  ],
  "tasks": {
    "summarization": {
      "task": "summarization",
      "input": "Issue description and comments...",
      "output": "Issue summary - Resolved: Fixed"
    },
    "classification": {
      "task": "classification",
      "input": "Title and description...",
      "output": "Type: Bug | Priority: High | Status: Resolved | Resolution: Fixed"
    },
    "qa": {
      "task": "qa",
      "question": "What is the issue with 'Issue summary' and how was it resolved?",
      "context": "Title: Issue summary\n\nDescription: ...",
      "answer": "Resolution details from comments..."
    }
  }
}
```

**Derived Tasks Explained:**
- **Summarization**: Takes issue description and comments as input, produces a concise summary
- **Classification**: Classifies issues by type, priority, status, and resolution
- **Q&A**: Generates question-answer pairs about the issue and its resolution

### 3. Optimization and Reliability

**Fault Tolerance:**
- Automatic retries with exponential backoff (up to 5 retries)
- Handles HTTP 429 (rate limit) by respecting Retry-After headers
- Skips invalid issues gracefully (logs error, continues)
- State persistence allows safe interruption and resume

**Error Handling:**
- Request failures: Retries with exponential backoff
- HTTP 429/5xx: Waits and retries
- Empty/malformed data: Logs warning, skips issue
- Validation errors: Logs error, optionally skips (controlled by `validation_strict_mode`)

**Efficiency:**
- Pagination handled automatically
- Concurrent requests limited to 1 per domain (configurable)
- Rate limiting via Scrapy's built-in DOWNLOAD_DELAY
- File-based deduplication (in-memory set, periodic disk writes)

## Directory Structure

```
scaler/
├── data/
│   ├── raw/              # Raw scraped issue JSON files
│   │   ├── HADOOP/
│   │   ├── SPARK/
│   │   └── KAFKA/
│   ├── state/             # Resume state and deduplication tracking
│   │   ├── last_updates.json
│   │   └── processed_issues.json
│   └── corpus/            # Transformed JSONL files
├── src/
│   ├── scraper/           # Scrapy spider and pipelines
│   ├── transform/         # JSONL transformation logic
│   ├── models/            # Pydantic data models
│   └── config/            # Configuration management
└── README.md
```

## Edge Cases Handled

1. **Rate Limiting (HTTP 429)**
   - Respects Retry-After header when present
   - Uses exponential backoff otherwise
   - Configurable delay between requests

2. **Network Failures**
   - Automatic retries with exponential backoff
   - Configurable retry attempts (default: 5)
   - Request timeouts handled gracefully

3. **Partial Data**
   - Missing fields handled with optional Pydantic fields
   - Empty descriptions/comments handled
   - Invalid dates parsed with fallbacks

4. **Interrupted Scrapes**
   - State saved periodically to disk
   - Resumes from last processed timestamp
   - Skips already-processed issues

5. **Duplicate Issues**
   - File-based deduplication
   - Checks before processing each issue
   - Handles updates to existing issues

6. **API Changes**
   - Graceful handling of missing fields
   - Validation errors logged but don't stop scraping
   - Flexible schema via Pydantic models

## Design Decisions

### Why File-Based State Instead of Redis?

- **Simplicity**: No external dependencies required
- **Portability**: Works out-of-the-box on any system
- **Persistence**: State survives restarts without setup
- **Sufficient**: For single-machine scraping, file-based is adequate

### Why Scrapy + REST API (vs HTML Scraping)?

- **Reliability**: REST API provides structured JSON data without parsing brittle HTML
- **Performance**: Direct API calls are faster and more efficient than HTML scraping
- **Maintainability**: API endpoints are more stable than HTML structure
- **Built-in features**: Pagination, retries, rate limiting, concurrency control
- **Mature**: Battle-tested framework with excellent error handling
- **Extensible**: Easy to add custom pipelines and middlewares

### Why Pydantic?

- **Validation**: Automatic data validation with clear error messages
- **Type safety**: Strong typing with IDE support
- **Flexibility**: Optional fields, custom validators, serialization

## Potential Future Improvements

1. **Distributed Scraping**: Add Redis/PostgreSQL for multi-machine coordination
2. **Incremental Comments**: Track individual comment updates, not just issue updates
3. **Parallel Projects**: Scrape multiple projects concurrently
4. **Real-time Monitoring**: Web dashboard for scrape progress
5. **S3 Direct Upload**: Stream issues directly to S3 during scraping
6. **Change Detection**: Track field-level changes in issues
7. **Backfill Strategy**: Intelligent backfilling of historical data

## Testing

```bash
# Run unit tests
pytest tests/unit/ -v

# Run integration tests (requires network)
pytest tests/integration/ -v

# Run setup verification
python scripts/test_setup.py
```

## Troubleshooting

### Issue: "Module not found" errors
```bash
# Make sure you installed in development mode
pip install -e .
```

### Issue: Scraper not resuming
- Check that `data/state/last_updates.json` exists and has timestamps
- Delete `data/state/` to start fresh

### Issue: Rate limit errors
- Increase `SCRAPY_DOWNLOAD_DELAY` in settings (default: 3.6s)
- Reduce `CONCURRENT_REQUESTS` (default: 1)

### Issue: Memory usage grows
- The deduplication set is kept in memory but periodically written to disk
- For very large scrapes (>100k issues), consider implementing a Bloom filter

## License

MIT
