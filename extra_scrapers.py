"""
YC INTELLIGENCE — Additional Data Sources (Gap Fillers)
=========================================================
These scrapers use free APIs, public datasets, and alternative
approaches to get data from sources that block direct scraping.

SETUP:
    pip3 install requests pandas beautifulsoup4

USAGE:
    python3 extra_scrapers.py              # Run all
    python3 extra_scrapers.py --source ph   # Run one
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

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


# ═══════════════════════════════════════════════════════════════════════════════
# 1. PRODUCT HUNT — via their official GraphQL API
#    Get your token at: https://api.producthunt.com/v2/docs
#    Set: export PH_TOKEN="your_token_here"
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_producthunt_api():
    print("\n  🚀 Scraping Product Hunt (API)...")
    token = os.environ.get("PH_TOKEN", "")

    if not token:
        print("    No PH_TOKEN set. Trying public feed instead...")
        return scrape_producthunt_rss()

    all_products = []
    url = "https://api.producthunt.com/v2/api/graphql"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Get top posts from the last 30 days
    queries = [
        # Today's top
        '{ posts(order: VOTES, first: 50) { edges { node { id name tagline votesCount commentsCount createdAt topics { edges { node { name } } } website } } } }',
        # Featured
        '{ posts(featured: true, first: 50) { edges { node { id name tagline votesCount commentsCount createdAt topics { edges { node { name } } } website } } } }',
    ]

    for query in queries:
        try:
            r = requests.post(url, json={"query": query}, headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json()
                edges = data.get("data", {}).get("posts", {}).get("edges", [])
                for edge in edges:
                    node = edge["node"]
                    topics = [t["node"]["name"] for t in node.get("topics", {}).get("edges", [])]
                    all_products.append({
                        "source": "producthunt",
                        "name": node.get("name", ""),
                        "tagline": node.get("tagline", ""),
                        "votes": node.get("votesCount", 0),
                        "comments": node.get("commentsCount", 0),
                        "topics": topics,
                        "website": node.get("website", ""),
                        "created": node.get("createdAt", ""),
                        "scraped_at": datetime.now().isoformat()
                    })
            else:
                print(f"    ⚠ PH API returned {r.status_code}: {r.text[:200]}")
            time.sleep(1)
        except Exception as e:
            print(f"    ⚠ PH API query failed: {e}")

    # Deduplicate by name
    seen = set()
    unique = []
    for p in all_products:
        if p["name"] not in seen:
            seen.add(p["name"])
            unique.append(p)

    path = os.path.join(OUTPUT_DIR, "producthunt.json")
    with open(path, "w") as f:
        json.dump(unique, f, indent=2)
    print(f"  ✓ Product Hunt: {len(unique)} products saved")
    return unique


def scrape_producthunt_rss():
    """Fallback: scrape PH via their RSS/Atom feed."""
    all_products = []
    try:
        # PH has an RSS feed
        r = requests.get("https://www.producthunt.com/feed", headers=HEADERS, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "xml")
            items = soup.find_all("item") or soup.find_all("entry")
            for item in items:
                title = item.find("title")
                desc = item.find("description") or item.find("summary") or item.find("content")
                link = item.find("link")
                all_products.append({
                    "source": "producthunt_rss",
                    "name": title.get_text(strip=True) if title else "",
                    "tagline": (desc.get_text(strip=True) if desc else "")[:200],
                    "url": link.get_text(strip=True) if link else (link.get("href", "") if link else ""),
                    "scraped_at": datetime.now().isoformat()
                })
    except Exception as e:
        print(f"    ⚠ PH RSS failed: {e}")

    path = os.path.join(OUTPUT_DIR, "producthunt.json")
    with open(path, "w") as f:
        json.dump(all_products, f, indent=2)
    print(f"  ✓ Product Hunt (RSS): {len(all_products)} products saved")
    return all_products


# ═══════════════════════════════════════════════════════════════════════════════
# 2. CRUNCHBASE — via free alternatives (OpenVC, public datasets)
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_funding_data():
    print("\n  💰 Scraping funding data (public sources)...")
    all_funding = []

    # Source 1: TechCrunch RSS for recent funding rounds
    try:
        r = requests.get("https://techcrunch.com/category/startups/feed/", headers=HEADERS, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "xml")
            items = soup.find_all("item")
            for item in items:
                title = item.find("title")
                desc = item.find("description")
                link = item.find("link")
                pub_date = item.find("pubDate")
                title_text = title.get_text(strip=True) if title else ""

                # Filter for funding-related articles
                funding_keywords = ["raises", "funding", "series", "seed", "million", "billion", "valuation", "round"]
                if any(kw in title_text.lower() for kw in funding_keywords):
                    all_funding.append({
                        "source": "techcrunch",
                        "title": title_text,
                        "description": (desc.get_text(strip=True) if desc else "")[:300],
                        "url": link.get_text(strip=True) if link else "",
                        "date": pub_date.get_text(strip=True) if pub_date else "",
                        "scraped_at": datetime.now().isoformat()
                    })
    except Exception as e:
        print(f"    ⚠ TechCrunch RSS failed: {e}")

    # Source 2: Pitchwall / OpenVC for recent deals
    try:
        r = requests.get("https://openvc.app/api/deals?limit=100", headers=HEADERS, timeout=15)
        if r.status_code == 200:
            deals = r.json() if isinstance(r.json(), list) else r.json().get("deals", [])
            for deal in deals[:100]:
                all_funding.append({
                    "source": "openvc",
                    "company": deal.get("company", deal.get("name", "")),
                    "amount": deal.get("amount", ""),
                    "stage": deal.get("stage", deal.get("round", "")),
                    "sector": deal.get("sector", deal.get("industry", "")),
                    "date": deal.get("date", ""),
                    "scraped_at": datetime.now().isoformat()
                })
    except Exception as e:
        print(f"    ⚠ OpenVC failed: {e}")

    # Source 3: Hacker News "Who is Hiring" threads
    try:
        # Search for recent hiring threads
        url = "https://hn.algolia.com/api/v1/search?query=who+is+hiring&tags=story&hitsPerPage=5"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            hits = r.json().get("hits", [])
            for hit in hits:
                story_id = hit.get("objectID")
                # Get comments (each comment = a company hiring)
                cr = requests.get(f"https://hn.algolia.com/api/v1/items/{story_id}", timeout=15)
                if cr.status_code == 200:
                    children = cr.json().get("children", [])[:100]
                    for child in children:
                        text = child.get("text", "")
                        if text and len(text) > 50:
                            all_funding.append({
                                "source": "hn_hiring",
                                "text": text[:500],
                                "date": child.get("created_at", ""),
                                "scraped_at": datetime.now().isoformat()
                            })
                time.sleep(1)
    except Exception as e:
        print(f"    ⚠ HN hiring failed: {e}")

    path = os.path.join(OUTPUT_DIR, "funding_data.json")
    with open(path, "w") as f:
        json.dump(all_funding, f, indent=2)
    print(f"  ✓ Funding data: {len(all_funding)} items saved")
    return all_funding


# ═══════════════════════════════════════════════════════════════════════════════
# 3. GOOGLE PATENTS — More reliable than USPTO API
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_google_patents():
    print("\n  📜 Scraping Google Patents...")
    all_patents = []

    search_terms = [
        "artificial intelligence quality control",
        "machine learning manufacturing defect",
        "computer vision inspection system",
        "autonomous property management system",
        "AI clinical trial matching",
        "predictive supply chain",
        "personalized corporate training AI",
        "automated compliance monitoring",
        "AI agent workflow automation",
        "real-time anomaly detection manufacturing",
    ]

    for term in search_terms:
        try:
            # Google Patents has a public search endpoint
            url = f"https://patents.google.com/xhr/query?url=q%3D{requests.utils.quote(term)}%26num%3D20%26oq%3D{requests.utils.quote(term)}"
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                data = r.json()
                results = data.get("results", {}).get("cluster", [])
                for cluster in results:
                    for result in cluster.get("result", []):
                        patent = result.get("patent", {})
                        all_patents.append({
                            "source": "google_patents",
                            "search_term": term,
                            "title": patent.get("title", ""),
                            "abstract": patent.get("abstract", "")[:300],
                            "publication_date": patent.get("publication_date", ""),
                            "assignee": patent.get("assignee_original", ""),
                            "patent_id": patent.get("publication_number", ""),
                            "scraped_at": datetime.now().isoformat()
                        })
            time.sleep(2)
        except Exception as e:
            print(f"    ⚠ Google Patents '{term[:30]}' failed: {e}")

    # Fallback: scrape patent HTML pages
    if len(all_patents) == 0:
        print("    Trying HTML scrape fallback...")
        for term in search_terms[:5]:
            try:
                url = f"https://patents.google.com/?q={requests.utils.quote(term)}&num=10"
                r = requests.get(url, headers=HEADERS, timeout=15)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")
                    articles = soup.find_all("article") or soup.find_all("search-result-item")
                    for art in articles:
                        title_el = art.find("h3") or art.find("span", class_="title")
                        if title_el:
                            all_patents.append({
                                "source": "google_patents_html",
                                "search_term": term,
                                "title": title_el.get_text(strip=True),
                                "scraped_at": datetime.now().isoformat()
                            })
                time.sleep(2)
            except:
                pass

    path = os.path.join(OUTPUT_DIR, "patents.json")
    with open(path, "w") as f:
        json.dump(all_patents, f, indent=2)
    print(f"  ✓ Patents: {len(all_patents)} saved")
    return all_patents


# ═══════════════════════════════════════════════════════════════════════════════
# 4. G2/CAPTERRA SOFTWARE REVIEWS — via alternative sources
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_software_reviews():
    print("\n  ⭐ Scraping software review data...")
    all_reviews = []

    # Source 1: AlternativeTo — what people are looking for alternatives to
    categories = [
        "project-management", "crm", "accounting", "email-marketing",
        "help-desk", "hr-software", "inventory-management",
        "quality-management", "manufacturing-execution", "supply-chain",
    ]

    for cat in categories:
        try:
            url = f"https://alternativeto.net/category/{cat}/"
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                items = soup.find_all("div", class_="app-listing") or soup.find_all("a", class_="app-header")

                # Also look for any structured data
                scripts = soup.find_all("script", {"type": "application/ld+json"})
                for script in scripts:
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, list):
                            for item in data:
                                all_reviews.append({
                                    "source": "alternativeto",
                                    "category": cat,
                                    "data": str(item)[:500],
                                    "scraped_at": datetime.now().isoformat()
                                })
                        elif isinstance(data, dict):
                            all_reviews.append({
                                "source": "alternativeto",
                                "category": cat,
                                "data": str(data)[:500],
                                "scraped_at": datetime.now().isoformat()
                            })
                    except:
                        pass

                # Get titles of alternatives
                for item in soup.find_all(["h2", "h3"]):
                    text = item.get_text(strip=True)
                    if len(text) > 3 and len(text) < 100:
                        all_reviews.append({
                            "source": "alternativeto",
                            "category": cat,
                            "name": text,
                            "scraped_at": datetime.now().isoformat()
                        })
            time.sleep(1)
        except Exception as e:
            print(f"    ⚠ AlternativeTo {cat} failed: {e}")

    # Source 2: Reddit software recommendation threads
    software_subs = ["software", "selfhosted", "webdev", "sysadmin"]
    for sub in software_subs:
        try:
            url = f"https://www.reddit.com/r/{sub}/search.json?q=alternative+OR+replacement+OR+recommend&restrict_sr=1&sort=top&t=month&limit=25"
            r = requests.get(url, headers={"User-Agent": "YC-Intel/1.0"}, timeout=15)
            if r.status_code == 200:
                posts = r.json().get("data", {}).get("children", [])
                for post in posts:
                    d = post.get("data", {})
                    all_reviews.append({
                        "source": "reddit_software",
                        "subreddit": sub,
                        "title": d.get("title", ""),
                        "selftext": (d.get("selftext", "") or "")[:300],
                        "score": d.get("score", 0),
                        "num_comments": d.get("num_comments", 0),
                        "scraped_at": datetime.now().isoformat()
                    })
            time.sleep(2)
        except Exception as e:
            print(f"    ⚠ Reddit r/{sub} search failed: {e}")

    path = os.path.join(OUTPUT_DIR, "software_reviews.json")
    with open(path, "w") as f:
        json.dump(all_reviews, f, indent=2)
    print(f"  ✓ Software reviews: {len(all_reviews)} items saved")
    return all_reviews


# ═══════════════════════════════════════════════════════════════════════════════
# 5. INDIE HACKERS — via Google search results
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_indiehackers_google():
    print("\n  🏗️ Scraping Indie Hackers (via search)...")
    all_items = []

    # Use HN Algolia to find IH content shared on HN
    try:
        searches = [
            "indiehackers.com revenue",
            "indiehackers.com MRR",
            "indiehackers.com profitable",
            "indie hacker revenue",
            "bootstrapped SaaS revenue",
        ]
        for q in searches:
            url = f"https://hn.algolia.com/api/v1/search?query={requests.utils.quote(q)}&tags=story&hitsPerPage=20"
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                hits = r.json().get("hits", [])
                for hit in hits:
                    all_items.append({
                        "source": "indiehackers_via_hn",
                        "title": hit.get("title", ""),
                        "url": hit.get("url", ""),
                        "points": hit.get("points", 0),
                        "comments": hit.get("num_comments", 0),
                        "date": hit.get("created_at", ""),
                        "scraped_at": datetime.now().isoformat()
                    })
            time.sleep(1)
    except Exception as e:
        print(f"    ⚠ HN search for IH failed: {e}")

    # Also search for revenue milestones on Reddit
    try:
        url = "https://www.reddit.com/r/SaaS/search.json?q=MRR+OR+revenue+OR+ARR&restrict_sr=1&sort=top&t=year&limit=50"
        r = requests.get(url, headers={"User-Agent": "YC-Intel/1.0"}, timeout=15)
        if r.status_code == 200:
            posts = r.json().get("data", {}).get("children", [])
            for post in posts:
                d = post.get("data", {})
                all_items.append({
                    "source": "reddit_saas_revenue",
                    "title": d.get("title", ""),
                    "selftext": (d.get("selftext", "") or "")[:400],
                    "score": d.get("score", 0),
                    "num_comments": d.get("num_comments", 0),
                    "scraped_at": datetime.now().isoformat()
                })
        time.sleep(2)
    except Exception as e:
        print(f"    ⚠ Reddit SaaS revenue failed: {e}")

    path = os.path.join(OUTPUT_DIR, "indiehackers.json")
    with open(path, "w") as f:
        json.dump(all_items, f, indent=2)
    print(f"  ✓ Indie Hackers data: {len(all_items)} items saved")
    return all_items


# ═══════════════════════════════════════════════════════════════════════════════
# 6. STACKOVERFLOW — Most upvoted unanswered questions (developer pain)
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_stackoverflow():
    print("\n  📚 Scraping Stack Overflow trends...")
    all_questions = []

    # SO has a great public API
    tags = [
        "machine-learning", "computer-vision", "automation",
        "manufacturing", "quality-assurance", "devops",
        "saas", "api", "cloud", "kubernetes",
        "artificial-intelligence", "deep-learning",
    ]

    for tag in tags:
        try:
            url = f"https://api.stackexchange.com/2.3/questions?order=desc&sort=votes&tagged={tag}&site=stackoverflow&pagesize=20&filter=withbody"
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                items = r.json().get("items", [])
                for q in items:
                    all_questions.append({
                        "source": "stackoverflow",
                        "tag": tag,
                        "title": q.get("title", ""),
                        "score": q.get("score", 0),
                        "views": q.get("view_count", 0),
                        "answers": q.get("answer_count", 0),
                        "is_answered": q.get("is_answered", False),
                        "link": q.get("link", ""),
                        "creation_date": datetime.fromtimestamp(q.get("creation_date", 0)).isoformat(),
                        "scraped_at": datetime.now().isoformat()
                    })
            time.sleep(1)
        except Exception as e:
            print(f"    ⚠ SO {tag} failed: {e}")

    # Sort by views to find most-demanded topics
    all_questions.sort(key=lambda x: x.get("views", 0), reverse=True)

    path = os.path.join(OUTPUT_DIR, "stackoverflow.json")
    with open(path, "w") as f:
        json.dump(all_questions, f, indent=2)
    print(f"  ✓ Stack Overflow: {len(all_questions)} questions saved")
    return all_questions


# ═══════════════════════════════════════════════════════════════════════════════
# 7. JOBS DATA — What companies are hiring for (demand signal)
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_jobs():
    print("\n  💼 Scraping job market signals...")
    all_jobs = []

    # HN Who is Hiring (monthly, very high signal)
    try:
        url = "https://hn.algolia.com/api/v1/search?query=who+is+hiring&tags=story&hitsPerPage=3"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            hits = r.json().get("hits", [])
            for hit in hits:
                story_id = hit.get("objectID")
                cr = requests.get(f"https://hn.algolia.com/api/v1/items/{story_id}", timeout=15)
                if cr.status_code == 200:
                    children = cr.json().get("children", [])[:150]
                    for child in children:
                        text = child.get("text", "") or ""
                        if len(text) > 50:
                            # Extract keywords
                            text_lower = text.lower()
                            categories = []
                            if "ai" in text_lower or "machine learning" in text_lower:
                                categories.append("AI/ML")
                            if "devops" in text_lower or "infrastructure" in text_lower:
                                categories.append("DevOps")
                            if "security" in text_lower or "cybersecurity" in text_lower:
                                categories.append("Security")
                            if "health" in text_lower or "medical" in text_lower:
                                categories.append("Healthcare")
                            if "fintech" in text_lower or "finance" in text_lower:
                                categories.append("Fintech")
                            if "manufacturing" in text_lower or "hardware" in text_lower:
                                categories.append("Manufacturing")
                            if "remote" in text_lower:
                                categories.append("Remote")

                            all_jobs.append({
                                "source": "hn_hiring",
                                "text": text[:400],
                                "categories": categories,
                                "date": child.get("created_at", ""),
                                "scraped_at": datetime.now().isoformat()
                            })
                time.sleep(1)
    except Exception as e:
        print(f"    ⚠ HN hiring failed: {e}")

    # Count categories
    cat_counts = {}
    for job in all_jobs:
        for cat in job.get("categories", []):
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

    path = os.path.join(OUTPUT_DIR, "jobs_data.json")
    with open(path, "w") as f:
        json.dump({"jobs": all_jobs, "category_counts": cat_counts}, f, indent=2)
    print(f"  ✓ Jobs: {len(all_jobs)} postings, top categories: {dict(sorted(cat_counts.items(), key=lambda x: -x[1])[:5])}")
    return all_jobs


# ═══════════════════════════════════════════════════════════════════════════════
# MASTER RUNNER
# ═══════════════════════════════════════════════════════════════════════════════
SCRAPERS = {
    "ph": scrape_producthunt_api,
    "funding": scrape_funding_data,
    "patents": scrape_google_patents,
    "reviews": scrape_software_reviews,
    "indie": scrape_indiehackers_google,
    "stackoverflow": scrape_stackoverflow,
    "jobs": scrape_jobs,
}

def run_all():
    print("=" * 65)
    print("  YC INTELLIGENCE — Extra Data Sources")
    print("=" * 65)

    results = {}
    for name, func in SCRAPERS.items():
        try:
            data = func()
            results[name] = len(data) if data else 0
        except Exception as e:
            print(f"  ⚠ {name} failed: {e}")
            results[name] = 0

    # Merge with existing summary
    summary_path = os.path.join(OUTPUT_DIR, "scrape_summary.json")
    if os.path.exists(summary_path):
        with open(summary_path) as f:
            summary = json.load(f)
    else:
        summary = {"sources": {}}

    summary["extra_scraped_at"] = datetime.now().isoformat()
    summary["sources"].update(results)
    summary["total_data_points"] = sum(summary["sources"].values())

    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 65)
    print("  EXTRA SCRAPE COMPLETE")
    print("=" * 65)
    for source, count in results.items():
        bar = "█" * min(count // 5, 30)
        print(f"  {source:<15} {count:>6} items  {bar}")
    print(f"\n  Total new: {sum(results.values())} data points")
    print(f"  Run  python3 multi_analyzer.py  to analyze everything")
    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=str, choices=list(SCRAPERS.keys()))
    args = parser.parse_args()

    if args.source:
        SCRAPERS[args.source]()
    else:
        run_all()
