#!/bin/bash
# Run full pipeline: scrape + transform

set -e

PROJECTS="${1:-HADOOP SPARK KAFKA}"
OUTPUT="${2:-data/corpus/jira_corpus.jsonl}"

echo "=== Step 1: Scraping Jira issues ==="
python -m src.cli scrape --projects $PROJECTS

echo ""
echo "=== Step 2: Building corpus ==="
python -m src.cli transform --output "$OUTPUT"

echo ""
echo "=== Pipeline complete ==="
echo "Corpus available at: $OUTPUT"

