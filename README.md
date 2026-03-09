# YC Startup Intelligence Platform

An AI-powered pipeline that scrapes Y Combinator's company directory
and uses Claude to analyze startup opportunities, identify whitespace,
and generate fundable startup ideas.

---

## Quick Start

### Step 1: Install dependencies

```bash
pip install requests pandas anthropic
```

### Step 2: Scrape YC data

```bash
python yc_scraper.py
```

This hits YC's Algolia search API (the same one their website uses)
and downloads every company in their directory. Output goes to `./yc_data/`.

You'll get:
- `yc_companies.csv` — spreadsheet-friendly format
- `yc_companies.json` — for feeding into Claude
- `scrape_log.txt` — metadata about the scrape

### Step 3: Set your Claude API key

```bash
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

Get a key at https://console.anthropic.com

### Step 4: Run analysis

```bash
# Full report (sector landscape, whitespace, ideas, failure patterns)
python yc_analyzer.py

# Focus on a specific sector
python yc_analyzer.py --sector "AI"

# Evaluate a startup idea
python yc_analyzer.py --idea "AI-powered legal contract analysis"

# Interactive chat mode
python yc_analyzer.py --chat

# Ask a single question
python yc_analyzer.py --question "What sector should I build in for 2025?"
```

Reports are saved to `./yc_analysis/`.

---

## How it works

```
ycombinator.com/companies
        │
        ▼
   yc_scraper.py          Fetches all ~5000+ companies via Algolia API
        │
        ▼
   yc_data/*.json          Structured data: name, sector, batch, status,
   yc_data/*.csv           team size, one-liner, stage, location, etc.
        │
        ▼
   yc_analyzer.py          Sends data to Claude with analysis prompts
        │
        ▼
   Claude API              Finds patterns, identifies gaps, generates ideas
        │
        ▼
   yc_analysis/*.txt       Reports with fundability scores and recommendations
```

---

## What Claude analyzes

- **Sector trends** — which industries are growing/shrinking in recent batches
- **Success patterns** — what IPO'd companies have in common
- **Failure patterns** — characteristics of companies that shut down
- **Whitespace** — underserved markets YC hasn't funded enough
- **Startup ideas** — specific, scored ideas with comparable companies
- **Idea evaluation** — test your idea against the full YC dataset

---

## Keeping data fresh

Re-run the scraper periodically to catch new batches:

```bash
# Add to crontab for weekly updates
0 9 * * 1 cd /path/to/project && python yc_scraper.py
```

---

## Troubleshooting

**Scraper returns 0 companies?**
YC may have rotated their Algolia API keys. Open `ycombinator.com/companies`
in your browser, open DevTools > Network tab, filter for "algolia", and
copy the new `X-Algolia-Application-Id` and `X-Algolia-API-Key` values
into `yc_scraper.py`.

**Claude analysis is slow?**
The full report makes 4 API calls. Each takes 15-30 seconds.
Use `--question` for faster single-question analysis.

**Token limits?**
The analyzer limits context to 500 companies by default.
Adjust `MAX_COMPANIES_IN_CONTEXT` in `yc_analyzer.py` if needed.
