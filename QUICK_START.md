# Quick Start Guide for Evaluators

## 🚀 Setup (2 minutes)

```bash
# 1. Clone repository
git clone https://github.com/YOUR_USERNAME/REPO_NAME.git
cd REPO_NAME

# 2. Create virtual environment
python -m venv venv

# 3. Activate (Windows)
venv\Scripts\activate
# OR (Linux/Mac)
source venv/bin/activate

# 4. Install dependencies
pip install -e .
```

## 🧪 Quick Test (3 minutes)

```bash
# Test scraping - scrape 3 issues
python -m src.cli scrape --projects HADOOP --max-issues 3

# Transform to corpus
python -m src.cli transform --output data/corpus/test.jsonl --input-dir data/raw

# Verify output
python -c "import json; lines = open('data/corpus/test.jsonl', 'r', encoding='utf-8').readlines(); print(f'✅ Generated {len(lines)} issues')"
```

## 📊 Expected Output

- **Scraping**: Should create JSON files in `data/raw/HADOOP/`
- **Transformation**: Should create `data/corpus/test.jsonl` with 3 lines
- Each line contains: metadata, description, comments, and tasks (summarization, classification, Q&A)

## 📖 Full Documentation

See `README.md` for complete documentation, architecture, and design decisions.

## 🔍 Key Features to Evaluate

1. **Scraping**: Handles pagination, rate limits, retries
2. **Resume**: Can resume from last state if interrupted
3. **Error Handling**: Graceful handling of HTTP 429, 5xx, timeouts
4. **Transformation**: Clean JSONL format with derived tasks
5. **Documentation**: Comprehensive README with examples

---

**Note**: For a full scrape of all 3 projects, run:
```bash
python -m src.cli scrape --projects HADOOP SPARK KAFKA
```

