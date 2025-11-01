# Test Commands for Data Generation

## Quick Test (Recommended for First Run)

### Step 1: Scrape a small number of issues
```powershell
# Activate virtual environment
.\venv\Scripts\activate

# Scrape 5 issues from HADOOP project (quick test)
python -m src.cli scrape --projects HADOOP --max-issues 5
```

### Step 2: Transform to corpus
```powershell
# Build corpus from the scraped issues
python -m src.cli transform --output data/corpus/test_corpus.jsonl --input-dir data/raw --projects HADOOP
```

### Step 3: Verify the output
```powershell
# Check how many issues were processed
Get-Content data\corpus\test_corpus.jsonl | Measure-Object -Line

# View first issue (pretty formatted)
python -c "import json; print(json.dumps(json.loads(open('data/corpus/test_corpus.jsonl', 'r', encoding='utf-8').readline()), indent=2))"
```

---

## Full Test with All 3 Projects

### Option 1: Test with limits (faster)
```powershell
# Scrape 10 issues from each of 3 projects
python -m src.cli scrape --projects HADOOP SPARK KAFKA --max-issues 10

# Build corpus from all projects
python -m src.cli transform --output data/corpus/jira_corpus.jsonl
```

### Option 2: Full scrape (takes longer)
```powershell
# Scrape all issues from all 3 projects
python -m src.cli scrape --projects HADOOP SPARK KAFKA

# Build corpus
python -m src.cli transform --output data/corpus/jira_corpus.jsonl
```

---

## One-Liner Quick Test

```powershell
# Scrape 3 issues and transform in one go (after activating venv)
python -m src.cli scrape --projects HADOOP --max-issues 3; python -m src.cli transform --output data/corpus/quick_test.jsonl --input-dir data/raw
```

---

## Verify Results

### Check scraped files
```powershell
# Count scraped files
(Get-ChildItem -Path data\raw -Recurse -Filter *.json).Count

# List files by project
Get-ChildItem -Path data\raw -Directory | ForEach-Object { Write-Host "$($_.Name): $((Get-ChildItem $_.FullName -Filter *.json).Count) files" }
```

### Check corpus file
```powershell
# Count lines in corpus (each line = 1 issue)
(Get-Content data\corpus\test_corpus.jsonl | Measure-Object -Line).Lines

# View structure of first issue
python -c "import json; data = json.loads(open('data/corpus/test_corpus.jsonl', 'r', encoding='utf-8').readline()); print('Keys:', list(data.keys())); print('Project:', data['metadata']['project']); print('Has tasks:', 'tasks' in data)"
```

---

## Example Output

After running the test commands, you should see:

**Scraping output:**
```
INFO: Starting scraper with args: projects=HADOOP max_issues=5
INFO: Project HADOOP: Found 5000+ issues, processing 5 (startAt=0)
INFO: Successfully stored issue: HADOOP-125
INFO: Successfully stored issue: HADOOP-129
...
```

**Transformation output:**
```
INFO: Building corpus from data/raw to data/corpus/test_corpus.jsonl
INFO: Found 5 JSON files in data/raw
INFO: Corpus built: 5 issues written to data/corpus/test_corpus.jsonl
INFO: Successfully built corpus with 5 issues
```

---

## Troubleshooting

### If scraping fails:
```powershell
# Check logs for errors
# Increase delay if rate limited
$env:SCRAPY_DOWNLOAD_DELAY="5.0"
python -m src.cli scrape --projects HADOOP --max-issues 3
```

### If transformation returns 0 issues:
```powershell
# Check if files exist
Get-ChildItem -Path data\raw -Recurse -Filter *.json

# Check file structure
python -c "import json; print(json.dumps(json.load(open('data/raw/HADOOP/HADOOP-125.json')), indent=2))"
```

---

## Recommended Test Sequence

1. **Start small**: `python -m src.cli scrape --projects HADOOP --max-issues 3`
2. **Verify files**: Check `data/raw/HADOOP/` directory has 3 JSON files
3. **Transform**: `python -m src.cli transform --output data/corpus/test.jsonl`
4. **Check output**: Verify `data/corpus/test.jsonl` has 3 lines
5. **Expand**: Increase to 10, then 50, then all issues

