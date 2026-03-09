"""
YC INTELLIGENCE — Multi-Source Opportunity Analyzer
=====================================================
Combines data from all scraped sources and uses Claude to
cross-reference patterns and find the best startup opportunities.

SETUP:
    pip3 install anthropic pandas
    export ANTHROPIC_API_KEY="sk-ant-..."

USAGE:
    python3 multi_analyzer.py              # Full cross-source analysis
    python3 multi_analyzer.py --quick      # Quick summary only
    python3 multi_analyzer.py --chat       # Interactive mode
"""

import anthropic
import json
import os
import sys
import time
import argparse
from datetime import datetime


DATA_DIR = "./opportunity_data"
OUTPUT_DIR = "./opportunity_analysis"
MODEL = "claude-sonnet-4-20250514"
DELAY = 65  # seconds between API calls


def load_source(filename):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return []


def build_context():
    """Load ALL sources and build a condensed context string."""
    context_parts = []
    total_items = 0

    # ── YC Companies ──────────────────────────────────────────────
    yc = load_source("yc_companies.json")
    if yc:
        total_items += len(yc)
        sectors = {}
        for c in yc:
            ind = c.get("industry", "Unknown")
            if ind not in sectors:
                sectors[ind] = {"total": 0, "active": 0}
            sectors[ind]["total"] += 1
            if c.get("status") == "Active":
                sectors[ind]["active"] += 1
        sector_summary = "\n".join([
            f"  {name}: {d['total']} companies, {round(d['active']/d['total']*100)}% active"
            for name, d in sorted(sectors.items(), key=lambda x: -x[1]["total"])[:12]
        ])
        context_parts.append(f"YC COMPANIES ({len(yc)} total):\n{sector_summary}")

    # ── Reddit Pain Points ────────────────────────────────────────
    pain_posts = load_source("reddit_pain_points.json")
    if pain_posts:
        total_items += len(pain_posts)
        top_pains = sorted(pain_posts, key=lambda x: x.get("score", 0), reverse=True)[:30]
        pain_summary = "\n".join([
            f"  [{p['subreddit']}] (score:{p['score']}) {p['title'][:100]}"
            for p in top_pains
        ])
        context_parts.append(f"REDDIT PAIN POINTS ({len(pain_posts)} posts, top 30):\n{pain_summary}")

    # ── GitHub Trending ───────────────────────────────────────────
    github = load_source("github_trending.json")
    if github:
        total_items += len(github)
        repos = [g for g in github if g.get("source") == "github"]
        top_repos = sorted(repos, key=lambda x: x.get("stars", 0), reverse=True)[:20]
        github_summary = "\n".join([
            f"  {r['name']} ({r['stars']} stars): {(r.get('description') or '')[:80]}"
            for r in top_repos
        ])
        context_parts.append(f"GITHUB TRENDING ({len(repos)} repos, top 20):\n{github_summary}")

    # ── Hacker News ───────────────────────────────────────────────
    hn = load_source("hackernews_launches.json")
    if hn:
        total_items += len(hn)
        top_hn = sorted(hn, key=lambda x: x.get("score", 0), reverse=True)[:20]
        hn_summary = "\n".join([
            f"  (score:{h['score']}) {h['title'][:100]}"
            for h in top_hn
        ])
        context_parts.append(f"HACKER NEWS LAUNCHES ({len(hn)} posts, top 20):\n{hn_summary}")

    # ── Google Trends ─────────────────────────────────────────────
    trends = load_source("google_trends.json")
    if trends:
        total_items += len(trends)
        rising = [t for t in trends if t.get("trend") == "rising" and t.get("source") == "google_trends"]
        trends_summary = "\n".join([
            f"  {t['keyword']}: +{t['growth_pct']}% growth"
            for t in sorted(rising, key=lambda x: -x.get("growth_pct", 0))[:15]
        ])
        context_parts.append(f"GOOGLE TRENDS (rising keywords):\n{trends_summary}")

    # ── Patents ───────────────────────────────────────────────────
    patents = load_source("patents.json")
    if patents:
        total_items += len(patents)
        patent_terms = {}
        for p in patents:
            term = p.get("search_term", "unknown")
            patent_terms[term] = patent_terms.get(term, 0) + 1
        patent_summary = "\n".join([
            f"  {term}: {count} recent patents"
            for term, count in sorted(patent_terms.items(), key=lambda x: -x[1])
        ])
        context_parts.append(f"PATENTS ({len(patents)} total):\n{patent_summary}")

    # ── Product Hunt ──────────────────────────────────────────────
    ph = load_source("producthunt.json")
    if ph:
        total_items += len(ph)
        products_with_votes = [p for p in ph if p.get("votes", 0) > 0]
        if products_with_votes:
            ph_summary = "\n".join([
                f"  {p['name']} ({p['votes']} votes): {p.get('tagline', '')[:80]}"
                for p in sorted(products_with_votes, key=lambda x: -x.get("votes", 0))[:15]
            ])
            context_parts.append(f"PRODUCT HUNT ({len(ph)} products, top by votes):\n{ph_summary}")

    # ══════════════════════════════════════════════════════════════
    # MEGA SCRAPER SOURCES (new)
    # ══════════════════════════════════════════════════════════════

    # ── SBIR/STTR Government Grants ───────────────────────────────
    sbir = load_source("sbir_grants.json")
    if sbir:
        total_items += len(sbir)
        kw_counts = {}
        for g in sbir:
            kw = g.get("keyword", "unknown")
            kw_counts[kw] = kw_counts.get(kw, 0) + 1
        sbir_summary = "\n".join([
            f"  {kw}: {count} grants"
            for kw, count in sorted(kw_counts.items(), key=lambda x: -x[1])[:15]
        ])
        top_grants = sorted(sbir, key=lambda x: float(str(x.get("amount", 0)).replace(",", "").replace("$", "") or 0), reverse=True)[:10]
        grant_examples = "\n".join([
            f"  ${g.get('amount', '?')} — {g.get('title', '')[:80]}"
            for g in top_grants if g.get("title")
        ])
        context_parts.append(f"SBIR/STTR GOVERNMENT GRANTS ({len(sbir)} awards):\nBy keyword:\n{sbir_summary}\nTop grants:\n{grant_examples}")

    # ── BLS Labor Data ────────────────────────────────────────────
    bls = load_source("bls_labor.json")
    if bls:
        total_items += len(bls)
        sector_data = {}
        for b in bls:
            if b.get("source") == "bls" and b.get("sector"):
                sector_data[b["sector"]] = b.get("value", "")
        bls_summary = "\n".join([f"  {s}: {v} (thousands employed)" for s, v in sector_data.items()])
        jolts = [b for b in bls if b.get("source") == "bls_jolts"]
        jolts_text = jolts[0].get("summary", "")[:300] if jolts else ""
        context_parts.append(f"BLS LABOR DATA ({len(bls)} data points):\nEmployment by sector:\n{bls_summary}\nJob openings report:\n  {jolts_text}")

    # ── ArXiv Research Papers ─────────────────────────────────────
    arxiv = load_source("arxiv_papers.json")
    if arxiv:
        total_items += len(arxiv)
        cat_counts = {}
        for p in arxiv:
            cat = p.get("category", "unknown")
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        arxiv_summary = "\n".join([f"  {cat}: {count} recent papers" for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1])])
        top_papers = arxiv[:15]
        paper_titles = "\n".join([f"  [{p.get('category','')}] {p.get('title','')[:90]}" for p in top_papers])
        context_parts.append(f"ARXIV RESEARCH ({len(arxiv)} papers):\nBy category:\n{arxiv_summary}\nRecent papers:\n{paper_titles}")

    # ── SEC EDGAR Filings ─────────────────────────────────────────
    sec = load_source("sec_filings.json")
    if sec:
        total_items += len(sec)
        sec_summary = "\n".join([
            f"  [{s.get('search_term','')}] {s.get('company','')}: {s.get('description','')[:80]}"
            for s in sec[:15]
        ])
        context_parts.append(f"SEC EDGAR FILINGS ({len(sec)} filings — public company risk factors):\n{sec_summary}")

    # ── NIH Research Funding ──────────────────────────────────────
    nih = load_source("nih_funding.json")
    if nih:
        total_items += len(nih)
        kw_counts = {}
        total_funding = 0
        for n in nih:
            kw = n.get("search_term", "unknown")
            kw_counts[kw] = kw_counts.get(kw, 0) + 1
            total_funding += float(n.get("award_amount", 0) or 0)
        nih_summary = "\n".join([f"  {kw}: {count} projects" for kw, count in sorted(kw_counts.items(), key=lambda x: -x[1])])
        context_parts.append(f"NIH RESEARCH FUNDING ({len(nih)} projects, ${total_funding/1e6:.0f}M total):\n{nih_summary}")

    # ── Grants.gov Opportunities ──────────────────────────────────
    grants = load_source("grants_gov.json")
    if grants:
        total_items += len(grants)
        grant_summary = "\n".join([
            f"  [{g.get('keyword','')}] {g.get('title','')[:80]} — {g.get('agency','')}"
            for g in grants[:15]
        ])
        context_parts.append(f"GRANTS.GOV OPPORTUNITIES ({len(grants)} open grants):\n{grant_summary}")

    # ── Kaggle Competitions ───────────────────────────────────────
    kaggle = load_source("kaggle.json")
    if kaggle:
        total_items += len(kaggle)
        comps = [k for k in kaggle if k.get("source") == "kaggle_competition" and k.get("title")]
        if comps:
            kaggle_summary = "\n".join([
                f"  {k['title'][:70]} — {k.get('reward','no prize')} ({k.get('team_count',0)} teams)"
                for k in comps[:15]
            ])
            context_parts.append(f"KAGGLE COMPETITIONS ({len(comps)} active):\n{kaggle_summary}")

    # ── Unicorn Startups ──────────────────────────────────────────
    unicorns = load_source("unicorns.json")
    if unicorns:
        total_items += len(unicorns)
        named = [u for u in unicorns if u.get("company")]
        if named:
            industry_counts = {}
            for u in named:
                ind = u.get("industry", "Unknown")
                industry_counts[ind] = industry_counts.get(ind, 0) + 1
            uni_summary = "\n".join([f"  {ind}: {count} unicorns" for ind, count in sorted(industry_counts.items(), key=lambda x: -x[1])[:15]])
            context_parts.append(f"UNICORN STARTUPS ({len(named)} billion-dollar companies):\nBy industry:\n{uni_summary}")

    # ── AWS Marketplace ───────────────────────────────────────────
    aws = load_source("aws_marketplace.json")
    if aws:
        total_items += len(aws)
        cat_counts = {}
        for a in aws:
            cat = a.get("category", "unknown")
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        aws_summary = "\n".join([f"  {cat}: {count} products" for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1])])
        context_parts.append(f"AWS MARKETPLACE ({len(aws)} SaaS products):\n{aws_summary}")

    # ── DEV.to Articles ───────────────────────────────────────────
    devto = load_source("devto_articles.json")
    if devto:
        total_items += len(devto)
        top_articles = sorted(devto, key=lambda x: x.get("reactions", 0), reverse=True)[:15]
        devto_summary = "\n".join([
            f"  ({a.get('reactions',0)} reactions) [{a.get('tag','')}] {a.get('title','')[:80]}"
            for a in top_articles
        ])
        context_parts.append(f"DEV.TO DEVELOPER ARTICLES ({len(devto)} articles, top by reactions):\n{devto_summary}")

    # ── Census Business Data ──────────────────────────────────────
    census = load_source("census_business.json")
    if census:
        total_items += len(census)
        census_summary = "\n".join([
            f"  {c.get('industry','')}: {c.get('establishments','')} establishments, {c.get('employees','')} employees"
            for c in census[:12]
        ])
        context_parts.append(f"US CENSUS BUSINESS DATA ({len(census)} industries):\n{census_summary}")

    # ── World Bank Indicators ─────────────────────────────────────
    wb = load_source("worldbank.json")
    if wb:
        total_items += len(wb)
        # Get latest values per indicator per country
        indicators = {}
        for w in wb:
            key = f"{w.get('indicator','')} ({w.get('country','')})"
            indicators[key] = w.get("value", "")
        wb_summary = "\n".join([f"  {k}: {v}" for k, v in list(indicators.items())[:20]])
        context_parts.append(f"WORLD BANK ECONOMIC INDICATORS ({len(wb)} data points):\n{wb_summary}")

    # ── Blog/HN Startup Ideas ─────────────────────────────────────
    ideas = load_source("blog_ideas.json")
    if ideas:
        total_items += len(ideas)
        top_ideas = sorted(ideas, key=lambda x: x.get("points", 0), reverse=True)[:20]
        ideas_summary = "\n".join([
            f"  ({i.get('points',0)} pts) {i.get('title','')[:90]}"
            for i in top_ideas
        ])
        context_parts.append(f"STARTUP IDEAS FROM HN ({len(ideas)} posts, top by points):\n{ideas_summary}")

    # ── GitHub Feature Requests ───────────────────────────────────
    gh_issues = load_source("github_issues.json")
    if gh_issues:
        total_items += len(gh_issues)
        top_issues = sorted(gh_issues, key=lambda x: x.get("thumbs_up", 0), reverse=True)[:15]
        issues_summary = "\n".join([
            f"  ({i.get('thumbs_up',0)} upvotes) [{i.get('repo','')}] {i.get('title','')[:80]}"
            for i in top_issues
        ])
        context_parts.append(f"GITHUB FEATURE REQUESTS ({len(gh_issues)} issues, top by upvotes):\n{issues_summary}")

    # ── Software Reviews / AlternativeTo ──────────────────────────
    reviews = load_source("software_reviews.json")
    if reviews:
        total_items += len(reviews)
        reddit_reviews = [r for r in reviews if r.get("source") == "reddit_software" and r.get("title")]
        if reddit_reviews:
            review_summary = "\n".join([
                f"  (score:{r.get('score',0)}) {r.get('title','')[:90]}"
                for r in sorted(reddit_reviews, key=lambda x: x.get("score", 0), reverse=True)[:15]
            ])
            context_parts.append(f"SOFTWARE ALTERNATIVES SOUGHT ({len(reviews)} items):\n{review_summary}")

    # ── Funding Data / TechCrunch ─────────────────────────────────
    funding = load_source("funding_data.json")
    if funding:
        total_items += len(funding)
        tc = [f for f in funding if f.get("source") == "techcrunch" and f.get("title")]
        if tc:
            funding_summary = "\n".join([f"  {f['title'][:100]}" for f in tc[:15]])
            context_parts.append(f"RECENT FUNDING ROUNDS ({len(tc)} from TechCrunch):\n{funding_summary}")

    # ── Stack Overflow ────────────────────────────────────────────
    so = load_source("stackoverflow.json")
    if so:
        total_items += len(so)
        top_q = sorted(so, key=lambda x: x.get("views", 0), reverse=True)[:15]
        so_summary = "\n".join([
            f"  ({q.get('views',0)} views) [{q.get('tag','')}] {q.get('title','')[:80]}"
            for q in top_q
        ])
        context_parts.append(f"STACKOVERFLOW TOP QUESTIONS ({len(so)} questions, by views):\n{so_summary}")

    # ── Jobs Data ─────────────────────────────────────────────────
    jobs = load_source("jobs_data.json")
    if jobs:
        if isinstance(jobs, dict):
            job_list = jobs.get("jobs", [])
            cat_counts = jobs.get("category_counts", {})
        else:
            job_list = jobs
            cat_counts = {}
        total_items += len(job_list)
        if cat_counts:
            jobs_summary = "\n".join([f"  {cat}: {count} postings" for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1])])
            context_parts.append(f"JOB MARKET SIGNALS ({len(job_list)} postings):\nTop hiring categories:\n{jobs_summary}")

    # ── Indie Hackers ─────────────────────────────────────────────
    ih = load_source("indiehackers.json")
    if ih:
        total_items += len(ih)
        titled = [i for i in ih if i.get("title")]
        if titled:
            ih_summary = "\n".join([
                f"  ({i.get('points', i.get('score', 0))}) {i.get('title','')[:90]}"
                for i in sorted(titled, key=lambda x: x.get("points", x.get("score", 0)), reverse=True)[:15]
            ])
            context_parts.append(f"INDIE HACKER / BOOTSTRAPPED DATA ({len(ih)} items):\n{ih_summary}")

    print(f"  📊 Total data points loaded: {total_items:,} across {len(context_parts)} sources")
    return "\n\n".join(context_parts)


def call_claude(client, system, prompt):
    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def full_analysis(client):
    context = build_context()

    if not context:
        print("  ⚠ No data found. Run multi_scraper.py first.")
        sys.exit(1)

    print(f"\n  Context built: {len(context)} characters across multiple sources")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    system = f"""You are a world-class startup opportunity analyst. You have access to data from MULTIPLE sources:

{context}

Your job is to CROSS-REFERENCE these sources to find startup opportunities where:
1. YC has few/no companies (whitespace)
2. Reddit shows strong pain points (demand signal)
3. GitHub shows developer interest (technical feasibility)
4. Google Trends shows rising searches (market timing)
5. Patent filings show R&D investment (technology readiness)
6. Product Hunt/HN shows early traction (validation)

Be extremely specific. Cite data from multiple sources. Give actionable recommendations."""

    report = []
    report.append("=" * 70)
    report.append("  MULTI-SOURCE STARTUP OPPORTUNITY REPORT")
    report.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("=" * 70)

    sections = [
        {
            "title": "CROSS-SOURCE SIGNAL MAP",
            "prompt": """Map the strongest signals across ALL sources:

1. What topics appear in 3+ sources simultaneously? (e.g., mentioned in Reddit pain points AND GitHub trending AND Google Trends rising)
2. What pain points on Reddit have NO corresponding YC companies addressing them?
3. What's trending on GitHub/HN that hasn't been commercialized yet?
4. What Google Trends keywords are rising fastest with no major startup serving them?

Create a signal strength matrix. Format with **bold**."""
        },
        {
            "title": "TOP 10 OPPORTUNITIES (CROSS-REFERENCED)",
            "prompt": """Based on cross-referencing ALL sources, identify the TOP 10 startup opportunities.

For each opportunity:
1. **Opportunity name** (specific, not generic)
2. **Signal sources**: Which of the data sources support this? (YC whitespace + Reddit pain + GitHub trend + Google rising + Patent activity)
3. **Signal strength**: How many sources confirm this? (1-6)
4. **Pain point evidence**: What specific Reddit posts or HN comments validate this?
5. **Competition check**: How many YC companies already address this?
6. **Market timing**: Is Google Trends rising or falling for this category?
7. **Fundability score**: 1-10

Rank by cross-source signal strength. The best opportunities appear in the MOST sources simultaneously."""
        },
        {
            "title": "CONTRARIAN OPPORTUNITIES",
            "prompt": """Find 5 CONTRARIAN opportunities — things most people are ignoring but the data suggests they shouldn't be:

1. Areas where Reddit complaints are HIGH but YC/VC interest is LOW
2. GitHub repos with explosive growth that VCs haven't noticed
3. Patent filings suggesting technology breakthroughs in unsexy industries
4. Google Trends showing rising demand in categories with declining startup activity

These are the "ugly duckling" opportunities. Be bold and specific."""
        },
        {
            "title": "FINAL VERDICT: THE #1 OPPORTUNITY",
            "prompt": """Based on all the cross-referenced data, what is the SINGLE BEST startup opportunity right now?

Include:
- Company name suggestion and one-liner
- Which data sources support this (list all signals)
- Why this beats every other opportunity
- 30-day action plan for a solo founder with AI tools
- Fundability: X/10, Timing: X/10, Signal Strength: X/6 sources
- One bold paragraph: why this is THE startup to build"""
        }
    ]

    for i, section in enumerate(sections):
        print(f"\n  [{i+1}/{len(sections)}] Analyzing: {section['title']}...")
        try:
            result = call_claude(client, system, section["prompt"])
            report.append(f"\n\n{'─' * 70}")
            report.append(f"  {section['title']}")
            report.append(f"{'─' * 70}\n")
            report.append(result)
        except Exception as e:
            if "rate_limit" in str(e).lower() or "429" in str(e):
                print(f"  ⏳ Rate limited. Waiting {DELAY}s...")
                time.sleep(DELAY)
                try:
                    result = call_claude(client, system, section["prompt"])
                    report.append(f"\n\n{'─' * 70}")
                    report.append(f"  {section['title']}")
                    report.append(f"{'─' * 70}\n")
                    report.append(result)
                except Exception as e2:
                    report.append(f"\n  Error: {e2}")
            else:
                report.append(f"\n  Error: {e}")

        if i < len(sections) - 1:
            print(f"  ⏳ Waiting {DELAY}s...")
            time.sleep(DELAY)

    report_text = "\n".join(report)
    report_path = os.path.join(OUTPUT_DIR, f"opportunity_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt")
    with open(report_path, "w") as f:
        f.write(report_text)

    print(f"\n  ✓ Report saved to: {report_path}")
    print(f"\n{report_text}")


def interactive(client):
    context = build_context()
    system = f"""You are a startup opportunity analyst with multi-source data:\n\n{context}\n\nAnswer questions using data from ALL sources. Cross-reference when possible."""

    print("\n  💬 Interactive mode. Type 'quit' to exit.\n")
    history = []

    while True:
        try:
            q = input("  You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in ("quit", "exit", "q"):
            break
        if not q:
            continue

        messages = history + [{"role": "user", "content": q}]
        print("\n  Thinking...\n")
        response = client.messages.create(model=MODEL, max_tokens=1500, system=system, messages=messages)
        answer = response.content[0].text
        print(f"  Claude: {answer}\n")
        history.append({"role": "user", "content": q})
        history.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chat", action="store_true")
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n  ⚠ Set ANTHROPIC_API_KEY first")
        sys.exit(1)

    client = anthropic.Anthropic()

    if args.chat:
        interactive(client)
    else:
        full_analysis(client)
