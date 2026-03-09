"""
YC STARTUP INTELLIGENCE — Step 2: Claude Analysis
====================================================
This script takes your scraped YC data and sends it to Claude
for deep startup opportunity analysis.

SETUP:
    pip install anthropic pandas

    # Set your API key:
    export ANTHROPIC_API_KEY="sk-ant-..."

USAGE:
    python yc_analyzer.py                    # Full analysis
    python yc_analyzer.py --sector "AI/ML"   # Sector-specific
    python yc_analyzer.py --idea "AI hiring"  # Evaluate an idea
    python yc_analyzer.py --chat              # Interactive mode
"""

import anthropic
import pandas as pd
import json
import argparse
import os
import sys
import time
from datetime import datetime


# ─── Configuration ────────────────────────────────────────────────────────────

DATA_DIR = "./yc_data"
OUTPUT_DIR = "./yc_analysis"
MODEL = "claude-sonnet-4-20250514"
MAX_COMPANIES_IN_CONTEXT = 150  # Keep under token limits
DELAY_BETWEEN_CALLS = 65  # Seconds to wait between API calls (rate limit)


# ─── Data Loading ─────────────────────────────────────────────────────────────

def load_yc_data():
    """Load scraped YC data from JSON or CSV."""
    json_path = os.path.join(DATA_DIR, "yc_companies.json")
    csv_path = os.path.join(DATA_DIR, "yc_companies.csv")

    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            data = json.load(f)
        print(f"  Loaded {len(data)} companies from {json_path}")
        return data
    elif os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        data = df.to_dict("records")
        print(f"  Loaded {len(data)} companies from {csv_path}")
        return data
    else:
        print("  ⚠ No data found. Run yc_scraper.py first.")
        sys.exit(1)


def prepare_context(companies, sector=None):
    """
    Prepare a condensed version of the data for Claude's context.
    We trim fields to keep token count manageable.
    """
    if sector:
        companies = [c for c in companies if sector.lower() in str(c.get("industry", "")).lower()
                     or sector.lower() in str(c.get("subindustry", "")).lower()
                     or sector.lower() in str(c.get("industries", "")).lower()]
        print(f"  Filtered to {len(companies)} companies in '{sector}'")

    # Trim to most useful fields (keep it lean for token limits)
    trimmed = []
    for c in companies[:MAX_COMPANIES_IN_CONTEXT]:
        trimmed.append({
            "name": c.get("name"),
            "one_liner": c.get("one_liner"),
            "industry": c.get("industry"),
            "batch": c.get("batch"),
            "status": c.get("status"),
            "team_size": c.get("team_size"),
            "tags": c.get("tags"),
            "top_company": c.get("top_company"),
        })

    return trimmed


def compute_stats(companies):
    """Compute aggregate statistics for the dataset."""
    df = pd.DataFrame(companies)
    stats = {
        "total_companies": len(df),
        "unique_batches": df["batch"].nunique() if "batch" in df else 0,
        "unique_industries": df["industry"].nunique() if "industry" in df else 0,
    }

    if "industry" in df.columns:
        stats["top_industries"] = df["industry"].value_counts().head(15).to_dict()

    if "status" in df.columns:
        stats["status_breakdown"] = df["status"].value_counts().to_dict()

    if "batch" in df.columns:
        stats["recent_batches"] = df["batch"].value_counts().head(10).to_dict()

    if "team_size" in df.columns:
        sizes = pd.to_numeric(df["team_size"], errors="coerce").dropna()
        if len(sizes) > 0:
            stats["team_size_median"] = float(sizes.median())
            stats["team_size_mean"] = round(float(sizes.mean()), 1)

    return stats


# ─── Claude Analysis ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a world-class Y Combinator startup analyst. You have deep expertise in:
- YC application strategies and what gets funded
- Startup market analysis and competitive landscapes  
- Identifying whitespace opportunities and emerging sectors
- Evaluating startup ideas for fundability and market timing

You're analyzing REAL data from the YC company directory. Be specific, cite actual companies 
from the data, and give bold, actionable insights — not vague platitudes.

When analyzing opportunities:
1. Reference specific companies in the dataset as evidence
2. Quantify everything (percentages, counts, trends)
3. Identify gaps — what's NOT being built that should be
4. Rate opportunities: Fundability (1-10), Market Timing (1-10), Competition Level (Low/Med/High)
5. Be opinionated — take a position on what someone should build

Format with clear sections and bold key insights."""


def analyze(client, companies, prompt, sector=None):
    """Send data + prompt to Claude and get analysis."""
    context = prepare_context(companies, sector)
    stats = compute_stats(companies)

    user_message = f"""Here is data from the Y Combinator company directory:

AGGREGATE STATISTICS:
{json.dumps(stats, indent=2)}

COMPANY DATA ({len(context)} companies):
{json.dumps(context, indent=2)}

---

ANALYSIS REQUEST:
{prompt}"""

    print("\n  Sending to Claude for analysis...")
    print("  (this may take 15-30 seconds)\n")

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    return response.content[0].text


# ─── Analysis Modes ──────────────────────────────────────────────────────────

def full_analysis(client, companies):
    """Run a comprehensive multi-section analysis."""
    prompts = [
        {
            "title": "SECTOR LANDSCAPE",
            "prompt": """Analyze the YC sector landscape:
1. Which sectors have the most companies and funding?
2. Which sectors are growing fastest (based on recent batches)?
3. Which sectors have the highest success rate?
4. Where is the market oversaturated?"""
        },
        {
            "title": "WHITESPACE OPPORTUNITIES",
            "prompt": """Identify the TOP 5 whitespace opportunities — sectors or problems that are 
UNDERREPRESENTED in YC's portfolio but have strong market tailwinds. For each:
- What's the opportunity?
- Why hasn't it been built yet?
- What would the ideal company look like?
- Fundability score (1-10)"""
        },
        {
            "title": "STARTUP IDEAS",
            "prompt": """Based on patterns in this data, generate 5 SPECIFIC startup ideas that would 
have the highest probability of YC acceptance AND funding success. For each:
- Company name and one-liner
- What sector and why now
- Business model
- Comparable YC companies
- Fundability: X/10, Market Timing: X/10, Competition: Low/Med/High"""
        },
        {
            "title": "FAILURE PATTERNS",
            "prompt": """Analyze companies that have shut down or appear inactive. What patterns emerge?
- Which sectors have the highest failure rates?
- What characteristics do failed companies share?
- What should founders avoid?"""
        },
    ]

    full_report = []
    full_report.append("=" * 70)
    full_report.append("  YC STARTUP INTELLIGENCE REPORT")
    full_report.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    full_report.append(f"  Companies analyzed: {len(companies)}")
    full_report.append("=" * 70)

    for i, section in enumerate(prompts):
        print(f"\n  [{i+1}/{len(prompts)}] Analyzing: {section['title']}...")

        # Retry logic for rate limits
        for attempt in range(3):
            try:
                result = analyze(client, companies, section["prompt"])
                break
            except Exception as e:
                if "rate_limit" in str(e).lower() or "429" in str(e):
                    wait = DELAY_BETWEEN_CALLS * (attempt + 1)
                    print(f"  ⏳ Rate limited. Waiting {wait}s before retry...")
                    time.sleep(wait)
                else:
                    result = f"Error: {e}"
                    break

        full_report.append(f"\n\n{'─' * 70}")
        full_report.append(f"  {section['title']}")
        full_report.append(f"{'─' * 70}\n")
        full_report.append(result)

        # Wait between sections to avoid rate limits
        if i < len(prompts) - 1:
            print(f"  ⏳ Waiting {DELAY_BETWEEN_CALLS}s before next analysis...")
            time.sleep(DELAY_BETWEEN_CALLS)

    report_text = "\n".join(full_report)

    # Save report
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    report_path = os.path.join(OUTPUT_DIR, f"yc_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt")
    with open(report_path, "w") as f:
        f.write(report_text)

    print(f"\n  ✓ Full report saved to: {report_path}")
    return report_text


def evaluate_idea(client, companies, idea):
    """Evaluate a specific startup idea against YC data."""
    prompt = f"""I'm considering building a startup around: "{idea}"

Based on the YC data, evaluate this idea:
1. How many similar companies already exist in YC? Name them.
2. Is this sector growing or declining in YC batches?
3. What's the competitive landscape like?
4. What angle would make this most fundable?
5. Rate: Fundability (1-10), Market Timing (1-10), Competition Level
6. Your honest recommendation: build this, pivot to X, or avoid?"""

    return analyze(client, companies, prompt)


def interactive_mode(client, companies):
    """Chat with Claude about the YC data interactively."""
    print("\n" + "=" * 60)
    print("  YC INTELLIGENCE — Interactive Analysis Mode")
    print("  Type your questions. Type 'quit' to exit.")
    print("=" * 60)

    history = []

    while True:
        try:
            user_input = input("\n  You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if user_input.lower() in ("quit", "exit", "q"):
            print("\n  Goodbye!")
            break

        if not user_input:
            continue

        context = prepare_context(companies)
        stats = compute_stats(companies)

        messages = history.copy()
        messages.append({
            "role": "user",
            "content": f"""[YC DATA CONTEXT: {len(context)} companies, stats: {json.dumps(stats)}]

{user_input}"""
        })

        print("\n  Claude is thinking...\n")

        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=messages,
        )

        answer = response.content[0].text
        print(f"  Claude: {answer}")

        # Keep conversation history
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": answer})


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="YC Startup Intelligence — Claude Analyzer")
    parser.add_argument("--sector", type=str, help="Focus analysis on a specific sector")
    parser.add_argument("--idea", type=str, help="Evaluate a specific startup idea")
    parser.add_argument("--chat", action="store_true", help="Interactive chat mode")
    parser.add_argument("--question", type=str, help="Ask a single question")
    args = parser.parse_args()

    # Check API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n  ⚠ ANTHROPIC_API_KEY not set.")
        print("  Run: export ANTHROPIC_API_KEY='sk-ant-...'")
        print("  Get your key at: console.anthropic.com\n")
        sys.exit(1)

    client = anthropic.Anthropic()
    companies = load_yc_data()

    print(f"\n  {'=' * 50}")
    print(f"  YC INTELLIGENCE ANALYZER")
    print(f"  {'=' * 50}")

    if args.chat:
        interactive_mode(client, companies)
    elif args.idea:
        result = evaluate_idea(client, companies, args.idea)
        print(f"\n{result}")
    elif args.question:
        result = analyze(client, companies, args.question, sector=args.sector)
        print(f"\n{result}")
    else:
        report = full_analysis(client, companies)
        print(f"\n{report}")


if __name__ == "__main__":
    main()
