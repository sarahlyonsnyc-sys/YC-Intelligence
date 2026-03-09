"""
YC STARTUP INTELLIGENCE — Step 1: Data Collection (v2)
========================================================
Uses the open-source YC API (yc-oss.github.io/api) to fetch
all Y Combinator companies. This is a free, community-maintained
mirror of the YC directory — no API keys needed.

SETUP:
    pip3 install requests pandas

USAGE:
    python3 yc_scraper.py
"""

import requests
import pandas as pd
import json
import os
from datetime import datetime


OUTPUT_DIR = "./yc_data"

# ─── The open-source YC API endpoints ─────────────────────────────────────────
BASE_URL = "https://yc-oss.github.io/api"
ALL_COMPANIES_URL = f"{BASE_URL}/companies/all.json"
TOP_COMPANIES_URL = f"{BASE_URL}/companies/top.json"


def fetch_all_companies():
    """Fetch every YC company from the open-source API."""
    print("=" * 60)
    print("  YC STARTUP INTELLIGENCE — Data Scraper v2")
    print("=" * 60)
    print()
    print("  Fetching all YC companies...")
    print(f"  Source: {ALL_COMPANIES_URL}")
    print()

    try:
        response = requests.get(ALL_COMPANIES_URL, timeout=60)
        response.raise_for_status()
        companies = response.json()
        print(f"  ✓ Downloaded {len(companies)} companies!")
        return companies
    except requests.exceptions.RequestException as e:
        print(f"  ⚠ Main endpoint failed: {e}")
        print("  Trying top companies endpoint...")

        try:
            response = requests.get(TOP_COMPANIES_URL, timeout=60)
            response.raise_for_status()
            companies = response.json()
            print(f"  ✓ Downloaded {len(companies)} top companies")
            return companies
        except requests.exceptions.RequestException as e2:
            print(f"  ⚠ That also failed: {e2}")
            return None


def fetch_by_batch():
    """
    Fallback: fetch companies batch by batch.
    YC batches follow the pattern: S05, W06, S06, ..., W25, S25, X25, F25, etc.
    """
    print("  Trying batch-by-batch fetch...")

    all_companies = []
    seasons = ["W", "S"]
    years = range(5, 27)  # 2005 to 2026

    batches = []
    for year in years:
        yr = f"{year:02d}"
        for season in seasons:
            batches.append(f"{season}{yr}")

    # Add X (spring) and F (fall) batches for recent years
    for yr in range(24, 27):
        batches.append(f"X{yr}")
        batches.append(f"F{yr}")

    for batch in batches:
        url = f"{BASE_URL}/batches/{batch.lower()}.json"
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                companies = response.json()
                if companies:
                    all_companies.extend(companies)
                    print(f"    {batch}: {len(companies)} companies")
        except Exception:
            pass

    print(f"\n  ✓ Total from batch fetch: {len(all_companies)} companies")
    return all_companies if all_companies else None


def save_data(companies):
    """Save to CSV and JSON."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Save JSON
    json_path = os.path.join(OUTPUT_DIR, "yc_companies.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(companies, f, indent=2, ensure_ascii=False)
    print(f"  ✓ Saved JSON: {json_path}")

    # Save CSV
    df = pd.DataFrame(companies)
    csv_path = os.path.join(OUTPUT_DIR, "yc_companies.csv")

    # Flatten any list/dict columns for CSV
    for col in df.columns:
        if df[col].apply(lambda x: isinstance(x, list)).any():
            df[col] = df[col].apply(lambda x: ", ".join(str(i) for i in x) if isinstance(x, list) else x)
        if df[col].apply(lambda x: isinstance(x, dict)).any():
            df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, dict) else x)

    df.to_csv(csv_path, index=False, encoding="utf-8")
    print(f"  ✓ Saved CSV:  {csv_path} ({len(df)} rows, {len(df.columns)} columns)")

    # Save scrape log
    log_path = os.path.join(OUTPUT_DIR, "scrape_log.txt")
    with open(log_path, "w") as f:
        f.write(f"YC Scrape Log\n{'=' * 40}\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n")
        f.write(f"Source: {ALL_COMPANIES_URL}\n")
        f.write(f"Total companies: {len(companies)}\n")
        f.write(f"Columns: {', '.join(df.columns.tolist())}\n")
    print(f"  ✓ Saved log:  {log_path}")

    return df


def print_summary(df):
    """Print a quick summary."""
    print()
    print("─" * 60)
    print("  SCRAPE SUMMARY")
    print("─" * 60)
    print(f"  Total companies: {len(df)}")
    print(f"  Data columns: {len(df.columns)}")

    if "batch" in df.columns:
        print(f"\n  Unique batches: {df['batch'].nunique()}")
        recent = sorted(df['batch'].dropna().unique(), reverse=True)[:8]
        print(f"  Most recent: {', '.join(recent)}")

    if "industry" in df.columns:
        print(f"\n  Top industries:")
        for industry, count in df['industry'].value_counts().head(10).items():
            bar = "█" * min(count // 20, 30)
            print(f"    {industry:<35} {count:>4}  {bar}")

    if "status" in df.columns:
        print(f"\n  Status breakdown:")
        for status, count in df['status'].value_counts().items():
            print(f"    {status}: {count}")

    if "top_company" in df.columns:
        top_count = df['top_company'].sum() if df['top_company'].dtype == bool else len(df[df['top_company'] == True])
        print(f"\n  YC Top Companies: {top_count}")

    print()
    print("=" * 60)
    print("  ✓ DONE — Data saved to ./yc_data/")
    print("  Next step: Run  python3 yc_analyzer.py")
    print("=" * 60)
    print()


if __name__ == "__main__":
    companies = fetch_all_companies()

    if not companies:
        companies = fetch_by_batch()

    if not companies:
        print("\n  ⚠ Could not fetch data from any source.")
        print("  Check your internet connection and try again.")
        exit(1)

    df = save_data(companies)
    print_summary(df)
