"""
YC INTELLIGENCE — Multi-Source Startup Opportunity Scraper
=============================================================
Scrapes multiple data sources to build a comprehensive startup
opportunity intelligence database.

SETUP:
    pip3 install requests pandas praw beautifulsoup4 pytrends

USAGE:
    python3 multi_scraper.py                # Run all scrapers
    python3 multi_scraper.py --source reddit    # Run one source
    python3 multi_scraper.py --source producthunt
    python3 multi_scraper.py --source github
    python3 multi_scraper.py --source trends
    python3 multi_scraper.py --source hn
    python3 multi_scraper.py --source patents
    python3 multi_scraper.py --source g2

Available sources:
    yc          - Y Combinator company directory (5,690+ companies)
    producthunt - Top Product Hunt launches (trending products)
    reddit      - Pain points from startup/business subreddits
    github      - Trending repos and most-requested features
    trends      - Google Trends for startup-related categories
    hn          - Hacker News top stories and Show HN posts
    patents     - USPTO patent application trends
    g2          - Software review categories and ratings
    crunchbase  - Crunchbase funding data (basic/free tier)
"""

import requests
import pandas as pd
import json
import os
import time
import argparse
from datetime import datetime, timedelta
from bs4 import BeautifulSoup


OUTPUT_DIR = "./opportunity_data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "YC-Intelligence-Bot/1.0 (Startup Research Platform)"
}


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Y COMBINATOR (already built, but included for completeness)
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_yc():
    print("\n  📡 Scraping Y Combinator...")
    try:
        r = requests.get("https://yc-oss.github.io/api/companies/all.json", timeout=60)
        r.raise_for_status()
        companies = r.json()
        path = os.path.join(OUTPUT_DIR, "yc_companies.json")
        with open(path, "w") as f:
            json.dump(companies, f, indent=2)
        print(f"  ✓ YC: {len(companies)} companies saved")
        return companies
    except Exception as e:
        print(f"  ⚠ YC failed: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# 2. PRODUCT HUNT (via unofficial API / web scrape)
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_producthunt():
    print("\n  🚀 Scraping Product Hunt...")
    all_products = []

    # Scrape the Product Hunt daily/weekly top products
    urls = [
        "https://www.producthunt.com/topics/artificial-intelligence",
        "https://www.producthunt.com/topics/saas",
        "https://www.producthunt.com/topics/developer-tools",
        "https://www.producthunt.com/topics/fintech",
        "https://www.producthunt.com/topics/health-and-fitness",
        "https://www.producthunt.com/topics/productivity",
        "https://www.producthunt.com/topics/marketing",
    ]

    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
            topic = url.split("/topics/")[-1]

            # Extract product cards from the page
            scripts = soup.find_all("script", {"type": "application/json"})
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    # Try to find product data in Next.js props
                    text = json.dumps(data)
                    if "tagline" in text and "name" in text:
                        all_products.append({
                            "source": "producthunt",
                            "topic": topic,
                            "raw_data": text[:2000],
                            "scraped_at": datetime.now().isoformat()
                        })
                except:
                    pass
            time.sleep(1)
        except Exception as e:
            print(f"    ⚠ PH topic {url} failed: {e}")

    # Also get the API-accessible leaderboard
    try:
        # Product Hunt GraphQL endpoint (public queries)
        graphql_url = "https://www.producthunt.com/frontend/graphql"
        query = {
            "operationName": "HomePage",
            "variables": {"cursor": None},
            "query": "query HomePage($cursor: String) { homefeed(after: $cursor, first: 20) { edges { node { id name tagline votesCount commentsCount topics { edges { node { name } } } } } } }"
        }
        r = requests.post(graphql_url, json=query, headers={**HEADERS, "Content-Type": "application/json"}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            edges = data.get("data", {}).get("homefeed", {}).get("edges", [])
            for edge in edges:
                node = edge.get("node", {})
                topics = [t["node"]["name"] for t in node.get("topics", {}).get("edges", [])]
                all_products.append({
                    "source": "producthunt",
                    "name": node.get("name", ""),
                    "tagline": node.get("tagline", ""),
                    "votes": node.get("votesCount", 0),
                    "comments": node.get("commentsCount", 0),
                    "topics": topics,
                    "scraped_at": datetime.now().isoformat()
                })
    except Exception as e:
        print(f"    ⚠ PH API failed: {e}")

    path = os.path.join(OUTPUT_DIR, "producthunt.json")
    with open(path, "w") as f:
        json.dump(all_products, f, indent=2)
    print(f"  ✓ Product Hunt: {len(all_products)} products saved")
    return all_products


# ═══════════════════════════════════════════════════════════════════════════════
# 3. REDDIT — Pain points and opportunities from business subreddits
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_reddit():
    print("\n  💬 Scraping Reddit pain points...")
    all_posts = []

    subreddits = [
        "smallbusiness", "entrepreneur", "SaaS", "startups",
        "manufacturing", "qualitycontrol", "machinists",
        "webdev", "cscareerquestions", "devops",
        "healthcare", "nursing", "teachers",
        "realestateinvesting", "PropertyManagement",
        "fintech", "personalfinance",
    ]

    # Reddit JSON API (no auth needed for public subreddits)
    for sub in subreddits:
        for sort in ["top", "hot"]:
            try:
                url = f"https://www.reddit.com/r/{sub}/{sort}.json?limit=50&t=month"
                r = requests.get(url, headers={**HEADERS, "User-Agent": "YC-Intel/1.0"}, timeout=15)
                if r.status_code == 200:
                    data = r.json()
                    posts = data.get("data", {}).get("children", [])
                    for post in posts:
                        d = post.get("data", {})
                        all_posts.append({
                            "source": "reddit",
                            "subreddit": sub,
                            "title": d.get("title", ""),
                            "selftext": (d.get("selftext", "") or "")[:500],
                            "score": d.get("score", 0),
                            "num_comments": d.get("num_comments", 0),
                            "url": f"https://reddit.com{d.get('permalink', '')}",
                            "created": datetime.fromtimestamp(d.get("created_utc", 0)).isoformat(),
                            "flair": d.get("link_flair_text", ""),
                            "scraped_at": datetime.now().isoformat()
                        })
                time.sleep(2)  # Reddit rate limit
            except Exception as e:
                print(f"    ⚠ r/{sub}/{sort} failed: {e}")

    # Filter for pain-point keywords
    pain_keywords = ["frustrated", "problem", "struggle", "hate", "wish", "need", "looking for",
                     "alternative", "replacement", "broken", "expensive", "slow", "manual",
                     "waste", "inefficient", "complain", "help me", "any solution", "recommend"]

    pain_posts = [p for p in all_posts if any(kw in (p["title"] + " " + p["selftext"]).lower() for kw in pain_keywords)]

    path = os.path.join(OUTPUT_DIR, "reddit_all.json")
    with open(path, "w") as f:
        json.dump(all_posts, f, indent=2)

    path2 = os.path.join(OUTPUT_DIR, "reddit_pain_points.json")
    with open(path2, "w") as f:
        json.dump(pain_posts, f, indent=2)

    print(f"  ✓ Reddit: {len(all_posts)} posts total, {len(pain_posts)} pain points")
    return all_posts


# ═══════════════════════════════════════════════════════════════════════════════
# 4. GITHUB — Trending repos and most-requested features
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_github():
    print("\n  🐙 Scraping GitHub trends...")
    all_repos = []

    # GitHub trending API (unofficial)
    languages = ["python", "javascript", "typescript", "rust", "go", ""]
    for lang in languages:
        try:
            url = f"https://api.github.com/search/repositories?q=created:>{(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')}"
            if lang:
                url += f"+language:{lang}"
            url += "&sort=stars&order=desc&per_page=50"

            r = requests.get(url, headers={**HEADERS, "Accept": "application/vnd.github.v3+json"}, timeout=15)
            if r.status_code == 200:
                items = r.json().get("items", [])
                for repo in items:
                    all_repos.append({
                        "source": "github",
                        "name": repo.get("full_name", ""),
                        "description": repo.get("description", ""),
                        "stars": repo.get("stargazers_count", 0),
                        "forks": repo.get("forks_count", 0),
                        "language": repo.get("language", ""),
                        "topics": repo.get("topics", []),
                        "created": repo.get("created_at", ""),
                        "url": repo.get("html_url", ""),
                        "scraped_at": datetime.now().isoformat()
                    })
            time.sleep(2)
        except Exception as e:
            print(f"    ⚠ GitHub {lang} failed: {e}")

    # Also get trending topics
    try:
        url = "https://api.github.com/search/topics?q=is:featured&sort=created&order=desc&per_page=50"
        r = requests.get(url, headers={**HEADERS, "Accept": "application/vnd.github.mercy-preview+json"}, timeout=15)
        if r.status_code == 200:
            topics = r.json().get("items", [])
            for t in topics:
                all_repos.append({
                    "source": "github_topic",
                    "name": t.get("name", ""),
                    "description": t.get("short_description", ""),
                    "featured": t.get("featured", False),
                    "scraped_at": datetime.now().isoformat()
                })
    except Exception as e:
        print(f"    ⚠ GitHub topics failed: {e}")

    path = os.path.join(OUTPUT_DIR, "github_trending.json")
    with open(path, "w") as f:
        json.dump(all_repos, f, indent=2)
    print(f"  ✓ GitHub: {len(all_repos)} repos/topics saved")
    return all_repos


# ═══════════════════════════════════════════════════════════════════════════════
# 5. HACKER NEWS — Top stories and Show HN launches
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_hackernews():
    print("\n  🔶 Scraping Hacker News...")
    all_stories = []

    # HN has a clean public API
    endpoints = {
        "top": "https://hacker-news.firebaseio.com/v0/topstories.json",
        "best": "https://hacker-news.firebaseio.com/v0/beststories.json",
        "show": "https://hacker-news.firebaseio.com/v0/showstories.json",
        "ask": "https://hacker-news.firebaseio.com/v0/askstories.json",
    }

    for category, url in endpoints.items():
        try:
            r = requests.get(url, timeout=15)
            story_ids = r.json()[:50]  # Top 50 per category

            for sid in story_ids:
                try:
                    sr = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=10)
                    story = sr.json()
                    if story:
                        all_stories.append({
                            "source": "hackernews",
                            "category": category,
                            "title": story.get("title", ""),
                            "url": story.get("url", ""),
                            "score": story.get("score", 0),
                            "comments": story.get("descendants", 0),
                            "by": story.get("by", ""),
                            "time": datetime.fromtimestamp(story.get("time", 0)).isoformat(),
                            "type": story.get("type", ""),
                            "scraped_at": datetime.now().isoformat()
                        })
                except:
                    pass
                time.sleep(0.1)  # Be nice to the API
        except Exception as e:
            print(f"    ⚠ HN {category} failed: {e}")

    # Filter for startup/product launches
    launch_keywords = ["show hn", "launch", "built", "shipping", "open source", "introducing",
                       "startup", "saas", "ai", "tool", "platform", "api"]
    launches = [s for s in all_stories if any(kw in s["title"].lower() for kw in launch_keywords)]

    path = os.path.join(OUTPUT_DIR, "hackernews_all.json")
    with open(path, "w") as f:
        json.dump(all_stories, f, indent=2)

    path2 = os.path.join(OUTPUT_DIR, "hackernews_launches.json")
    with open(path2, "w") as f:
        json.dump(launches, f, indent=2)

    print(f"  ✓ Hacker News: {len(all_stories)} stories, {len(launches)} launches")
    return all_stories


# ═══════════════════════════════════════════════════════════════════════════════
# 6. GOOGLE TRENDS — Rising search terms for startup categories
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_google_trends():
    print("\n  📈 Scraping Google Trends...")
    all_trends = []

    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl='en-US', tz=360)

        # Categories relevant to startup opportunities
        keyword_groups = [
            ["AI software", "automation tool", "no-code platform", "AI agent", "workflow automation"],
            ["quality control software", "manufacturing AI", "defect detection", "visual inspection AI"],
            ["property management software", "landlord tool", "tenant screening AI"],
            ["clinical trial software", "healthcare AI", "patient matching"],
            ["supply chain AI", "inventory management AI", "procurement automation"],
            ["corporate training AI", "employee learning platform", "skills assessment AI"],
            ["cybersecurity AI", "compliance automation", "SOC2 automation"],
            ["legal AI", "contract analysis AI", "document review AI"],
        ]

        for keywords in keyword_groups:
            try:
                pytrends.build_payload(keywords, cat=0, timeframe='today 12-m', geo='US')
                interest = pytrends.interest_over_time()

                if not interest.empty:
                    for kw in keywords:
                        if kw in interest.columns:
                            avg_interest = interest[kw].mean()
                            recent_interest = interest[kw].tail(4).mean()
                            trend = "rising" if recent_interest > avg_interest * 1.2 else "stable" if recent_interest > avg_interest * 0.8 else "declining"

                            all_trends.append({
                                "source": "google_trends",
                                "keyword": kw,
                                "avg_interest_12m": round(avg_interest, 1),
                                "recent_interest_4w": round(recent_interest, 1),
                                "trend": trend,
                                "growth_pct": round((recent_interest - avg_interest) / max(avg_interest, 1) * 100, 1),
                                "scraped_at": datetime.now().isoformat()
                            })
                time.sleep(3)  # Google rate limits aggressively
            except Exception as e:
                print(f"    ⚠ Trends group failed: {e}")
                time.sleep(10)

        # Also get related queries for top terms
        try:
            pytrends.build_payload(["AI startup", "SaaS startup", "startup idea"], timeframe='today 12-m', geo='US')
            related = pytrends.related_queries()
            for kw, data in related.items():
                if data.get("rising") is not None:
                    for _, row in data["rising"].head(10).iterrows():
                        all_trends.append({
                            "source": "google_trends_related",
                            "parent_keyword": kw,
                            "related_query": row.get("query", ""),
                            "value": row.get("value", 0),
                            "scraped_at": datetime.now().isoformat()
                        })
        except Exception as e:
            print(f"    ⚠ Related queries failed: {e}")

    except ImportError:
        print("    ⚠ pytrends not installed. Run: pip3 install pytrends")
    except Exception as e:
        print(f"    ⚠ Google Trends failed: {e}")

    path = os.path.join(OUTPUT_DIR, "google_trends.json")
    with open(path, "w") as f:
        json.dump(all_trends, f, indent=2)
    print(f"  ✓ Google Trends: {len(all_trends)} data points saved")
    return all_trends


# ═══════════════════════════════════════════════════════════════════════════════
# 7. CRUNCHBASE — Basic company/funding data (free tier)
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_crunchbase():
    print("\n  💰 Scraping Crunchbase (public data)...")
    all_companies = []

    # Crunchbase doesn't have a free API, but we can scrape their public pages
    categories = [
        "artificial-intelligence", "machine-learning", "saas",
        "fintech", "health-care", "manufacturing",
        "cybersecurity", "developer-tools", "real-estate",
        "education", "supply-chain", "logistics",
    ]

    for cat in categories:
        try:
            url = f"https://www.crunchbase.com/discover/organization.companies/field/organizations/categories/{cat}"
            r = requests.get(url, headers={
                **HEADERS,
                "Accept": "text/html",
                "Accept-Language": "en-US,en;q=0.9"
            }, timeout=15)

            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                # Try to extract data from the page
                scripts = soup.find_all("script")
                for script in scripts:
                    if script.string and "window.__NEXT_DATA__" in (script.string or ""):
                        try:
                            json_str = script.string.split("window.__NEXT_DATA__ = ")[1].split("</script>")[0].rstrip(";")
                            data = json.loads(json_str)
                            all_companies.append({
                                "source": "crunchbase",
                                "category": cat,
                                "raw_data": str(data)[:3000],
                                "scraped_at": datetime.now().isoformat()
                            })
                        except:
                            pass

            time.sleep(2)
        except Exception as e:
            print(f"    ⚠ Crunchbase {cat} failed: {e}")

    path = os.path.join(OUTPUT_DIR, "crunchbase.json")
    with open(path, "w") as f:
        json.dump(all_companies, f, indent=2)
    print(f"  ✓ Crunchbase: {len(all_companies)} categories scraped")
    return all_companies


# ═══════════════════════════════════════════════════════════════════════════════
# 8. USPTO PATENTS — Patent application trends
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_patents():
    print("\n  📜 Scraping USPTO patent trends...")
    all_patents = []

    # USPTO has a public API
    search_terms = [
        "artificial intelligence manufacturing",
        "machine learning quality control",
        "computer vision defect detection",
        "autonomous property management",
        "clinical trial patient matching",
        "supply chain prediction",
        "corporate training personalization",
    ]

    for term in search_terms:
        try:
            url = "https://developer.uspto.gov/ibd-api/v1/application/publications"
            params = {
                "searchText": term,
                "start": 0,
                "rows": 20,
                "largeTextSearchFlag": "N"
            }
            r = requests.get(url, params=params, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                data = r.json()
                results = data.get("results", [])
                for patent in results:
                    all_patents.append({
                        "source": "uspto",
                        "search_term": term,
                        "title": patent.get("inventionTitle", ""),
                        "abstract": (patent.get("abstractText", [""])[0] if isinstance(patent.get("abstractText"), list) else patent.get("abstractText", ""))[:500],
                        "filing_date": patent.get("filingDate", ""),
                        "applicant": patent.get("applicantName", ""),
                        "patent_number": patent.get("publicationReferenceDocumentNumber", ""),
                        "scraped_at": datetime.now().isoformat()
                    })
            time.sleep(1)
        except Exception as e:
            print(f"    ⚠ USPTO '{term}' failed: {e}")

    path = os.path.join(OUTPUT_DIR, "patents.json")
    with open(path, "w") as f:
        json.dump(all_patents, f, indent=2)
    print(f"  ✓ USPTO: {len(all_patents)} patents saved")
    return all_patents


# ═══════════════════════════════════════════════════════════════════════════════
# 9. INDIE HACKERS — Revenue data from bootstrapped startups
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_indiehackers():
    print("\n  🏗️ Scraping Indie Hackers...")
    all_products = []

    try:
        # IH product directory
        url = "https://www.indiehackers.com/products?sorting=highest-revenue"
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            scripts = soup.find_all("script")
            for script in scripts:
                text = script.string or ""
                if "revenue" in text.lower() and "product" in text.lower():
                    all_products.append({
                        "source": "indiehackers",
                        "raw_data": text[:5000],
                        "scraped_at": datetime.now().isoformat()
                    })
    except Exception as e:
        print(f"    ⚠ IndieHackers failed: {e}")

    # Also scrape IH interviews/posts via their feed
    try:
        url = "https://www.indiehackers.com/feed?sort=top"
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            titles = soup.find_all(["h2", "h3", "a"])
            for t in titles:
                text = t.get_text(strip=True)
                if len(text) > 20 and ("$" in text or "revenue" in text.lower() or "mrr" in text.lower()):
                    all_products.append({
                        "source": "indiehackers",
                        "title": text,
                        "scraped_at": datetime.now().isoformat()
                    })
    except Exception as e:
        print(f"    ⚠ IH feed failed: {e}")

    path = os.path.join(OUTPUT_DIR, "indiehackers.json")
    with open(path, "w") as f:
        json.dump(all_products, f, indent=2)
    print(f"  ✓ Indie Hackers: {len(all_products)} items saved")
    return all_products


# ═══════════════════════════════════════════════════════════════════════════════
# MASTER RUNNER
# ═══════════════════════════════════════════════════════════════════════════════
SCRAPERS = {
    "yc": scrape_yc,
    "producthunt": scrape_producthunt,
    "reddit": scrape_reddit,
    "github": scrape_github,
    "hn": scrape_hackernews,
    "trends": scrape_google_trends,
    "crunchbase": scrape_crunchbase,
    "patents": scrape_patents,
    "indiehackers": scrape_indiehackers,
}


def run_all():
    print("=" * 65)
    print("  YC INTELLIGENCE — Multi-Source Opportunity Scraper")
    print("=" * 65)

    results = {}
    for name, func in SCRAPERS.items():
        try:
            data = func()
            results[name] = len(data) if data else 0
        except Exception as e:
            print(f"  ⚠ {name} failed completely: {e}")
            results[name] = 0

    # Save summary
    summary = {
        "scraped_at": datetime.now().isoformat(),
        "sources": results,
        "total_data_points": sum(results.values()),
    }

    path = os.path.join(OUTPUT_DIR, "scrape_summary.json")
    with open(path, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 65)
    print("  SCRAPE COMPLETE")
    print("=" * 65)
    for source, count in results.items():
        bar = "█" * min(count // 10, 30)
        print(f"  {source:<15} {count:>6} items  {bar}")
    print(f"\n  Total: {sum(results.values())} data points across {len(results)} sources")
    print(f"  Saved to: {OUTPUT_DIR}/")
    print(f"\n  Next: Run  python3 multi_analyzer.py  for cross-source analysis")
    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-source startup opportunity scraper")
    parser.add_argument("--source", type=str, help="Run a specific scraper", choices=list(SCRAPERS.keys()))
    args = parser.parse_args()

    if args.source:
        SCRAPERS[args.source]()
    else:
        run_all()
