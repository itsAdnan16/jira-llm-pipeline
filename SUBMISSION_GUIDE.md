# Submission Guide for Evaluation

## 📋 Pre-Submission Checklist

### ✅ Code Requirements
- [x] Scraper implemented (Scrapy-based)
- [x] Handles pagination and rate limits
- [x] Resume from last successful state
- [x] Error handling (retries, HTTP 429, 5xx, timeouts)
- [x] Data transformation to JSONL format
- [x] Derived tasks (summarization, classification, Q&A)
- [x] Supports 3 Apache Jira projects (HADOOP, SPARK, KAFKA)
- [x] Comprehensive README with setup instructions
- [x] Documentation of edge cases and design decisions

### ✅ Documentation
- [x] README.md with setup instructions
- [x] Architecture overview in README
- [x] Edge cases documented
- [x] Design decisions explained
- [x] Optimization strategies documented

### ✅ Testing
- [x] Test commands documented (TEST_COMMANDS.md)
- [x] Sample data generated successfully
- [x] Corpus transformation works correctly

---

## 🚀 Submission Steps

### Step 1: Initialize Git Repository (if not done)

```bash
# Initialize git repository
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: Jira LLM Corpus Pipeline"
```

### Step 2: Create GitHub Repository

1. Go to [GitHub](https://github.com/new)
2. Create a new repository (make it **Public** or ensure evaluators have access)
3. Name it something like: `jira-llm-pipeline` or `web-scraping-tutor-assignment`
4. **DO NOT** initialize with README, .gitignore, or license (we already have these)

### Step 3: Push to GitHub

```bash
# Add remote repository (replace YOUR_USERNAME and REPO_NAME)
git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### Step 4: Share Repository with Evaluators

The assignment requires sharing with:
- https://github.com/Naman-Bhalla/
- https://github.com/raun/

**Option A: Make Repository Public** (easiest)
- Go to repository Settings → Change visibility → Make public
- Share the repository URL with evaluators

**Option B: Add Collaborators**
- Go to repository Settings → Collaborators and teams
- Click "Add people"
- Add these GitHub usernames:
  - `Naman-Bhalla`
  - `raun`
- They will receive an invitation to access the repository

### Step 5: Share Repository URL

Send the repository URL to your evaluators:
```
https://github.com/YOUR_USERNAME/REPO_NAME
```

---

## 📝 What Evaluators Will Check

### 1. Code Quality
- ✅ Clean, readable code structure
- ✅ Proper error handling
- ✅ Configuration management
- ✅ Type hints and documentation

### 2. Functionality
- ✅ Can scrape issues from Apache Jira
- ✅ Handles edge cases (rate limits, failures, etc.)
- ✅ Transforms data to JSONL format
- ✅ Includes derived tasks

### 3. Documentation
- ✅ Clear setup instructions
- ✅ Architecture explanation
- ✅ Edge cases documented
- ✅ Design decisions explained

### 4. Testing
- ✅ Repository can be cloned and setup
- ✅ Commands work as documented
- ✅ Sample data can be generated

---

## 🧪 Quick Verification Before Submission

Run these commands to ensure everything works:

```powershell
# 1. Activate virtual environment
.\venv\Scripts\activate

# 2. Test scraping (small sample)
python -m src.cli scrape --projects HADOOP --max-issues 5

# 3. Test transformation
python -m src.cli transform --output data/corpus/test_submission.jsonl --input-dir data/raw

# 4. Verify output
python -c "import json; lines = open('data/corpus/test_submission.jsonl', 'r', encoding='utf-8').readlines(); print(f'Generated {len(lines)} issues'); print('Sample:', json.dumps(json.loads(lines[0])['metadata'], indent=2))"
```

---

## 📦 What to Include/Exclude

### ✅ Include in Repository:
- All source code (`src/`)
- Configuration files (`pyproject.toml`, `requirements.txt`, `scrapy.cfg`)
- Documentation (`README.md`, `TEST_COMMANDS.md`)
- Tests (`tests/`)
- Scripts (`scripts/`)
- Docker files (if using)
- `.gitignore`

### ❌ Exclude from Repository:
- `venv/` (virtual environment)
- `__pycache__/` (Python cache)
- `*.pyc` (compiled Python)
- Large data files (use `.gitignore` to exclude)
- `.env` files with sensitive credentials
- `data/raw/*.json` (can exclude, or include a few samples)
- `data/corpus/*.jsonl` (generated files)

**Note**: You may want to include a small sample of scraped data to demonstrate functionality. Create a `data/samples/` directory with 2-3 example issues.

---

## 📧 Submission Email Template

```
Subject: Web Scraping Tutor Assignment Submission

Dear Evaluators,

I have completed the Web Scraping Tutor Assignment. The codebase is available at:

GitHub Repository: https://github.com/YOUR_USERNAME/REPO_NAME

Key Features:
- Scrapes issues from Apache Jira (HADOOP, SPARK, KAFKA projects)
- Handles rate limits, retries, and edge cases
- Transforms data to JSONL format with derived tasks
- Comprehensive documentation and error handling

Quick Start:
1. Clone the repository
2. Run: python -m venv venv && venv\Scripts\activate
3. Run: pip install -e .
4. Test: python -m src.cli scrape --projects HADOOP --max-issues 3

Please let me know if you need any clarification.

Best regards,
[Your Name]
```

---

## 🔍 Final Checklist Before Submission

- [ ] Git repository initialized
- [ ] All code committed
- [ ] README.md is complete and accurate
- [ ] `.gitignore` excludes sensitive/unnecessary files
- [ ] Repository pushed to GitHub
- [ ] Repository shared with evaluators (Naman-Bhalla and raun)
- [ ] Tested that repository can be cloned and setup works
- [ ] Sample data or instructions for generating data included
- [ ] All assignment requirements met

---

## 🆘 Troubleshooting

### Issue: "Repository not found" when sharing
- Make sure repository is public OR
- Add evaluators as collaborators with read access

### Issue: Large files in repository
- Use `.gitignore` to exclude `data/raw/` and `data/corpus/`
- Consider Git LFS for large files if needed
- Or include only sample data files

### Issue: Setup doesn't work for evaluators
- Double-check `requirements.txt` is complete
- Verify `README.md` setup instructions are clear
- Test on a fresh environment yourself

---

**Good luck with your submission! 🚀**

