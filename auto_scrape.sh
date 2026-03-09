#!/bin/bash
# ─── YC Intelligence Auto-Scraper ────────────────────────────────────────────
# Runs weekly to pull fresh YC data and generate a new analysis report.
#
# SETUP (one-time):
#   1. Edit the paths below to match your setup
#   2. Make this script executable:  chmod +x auto_scrape.sh
#   3. Install the launchd plist (see bottom of this file)
#
# MANUAL RUN:
#   ./auto_scrape.sh
# ──────────────────────────────────────────────────────────────────────────────

# ── CONFIG — EDIT THESE ──────────────────────────────────────────────────────
PROJECT_DIR="$HOME/Documents/YC Intelligence"
PYTHON="/usr/bin/python3"
LOG_FILE="$PROJECT_DIR/auto_scrape.log"
# Set your API key here OR in your shell profile (~/.zshrc)
export ANTHROPIC_API_KEY="YOUR_KEY_HERE"
# ─────────────────────────────────────────────────────────────────────────────

cd "$PROJECT_DIR" || exit 1

echo "======================================" >> "$LOG_FILE"
echo "Auto-scrape started: $(date)" >> "$LOG_FILE"

# Step 1: Scrape fresh data
echo "Scraping YC data..." >> "$LOG_FILE"
$PYTHON yc_scraper.py >> "$LOG_FILE" 2>&1

if [ $? -ne 0 ]; then
    echo "ERROR: Scraper failed" >> "$LOG_FILE"
    exit 1
fi

# Step 2: Run analysis
echo "Running Claude analysis..." >> "$LOG_FILE"
$PYTHON yc_analyzer.py >> "$LOG_FILE" 2>&1

echo "Auto-scrape completed: $(date)" >> "$LOG_FILE"
echo "======================================" >> "$LOG_FILE"

# Optional: send yourself a notification (macOS)
osascript -e 'display notification "Fresh YC data and analysis ready!" with title "YC Intelligence"' 2>/dev/null
