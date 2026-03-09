"""
YC INTELLIGENCE — Mega Data Scraper
======================================
Scrapes every free public data source for startup opportunity signals.

SETUP:
    pip3 install requests pandas beautifulsoup4

USAGE:
    python3 mega_scraper.py              # Run all
    python3 mega_scraper.py --source sbir  # Run one
"""

import requests
import json
import os
import time
import argparse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

OUTPUT_DIR = "./opportunity_data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

H = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

def save(name, data):
    path = os.path.join(OUTPUT_DIR, f"{name}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return len(data)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. SBIR/STTR AWARDS — US government small business innovation grants
#    Shows where federal R&D money is flowing
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_sbir():
    print("\n  🏛️ Scraping SBIR/STTR grants...")
    items = []

    keywords = [
        "artificial intelligence", "machine learning", "computer vision",
        "manufacturing automation", "quality control", "supply chain",
        "healthcare AI", "clinical trial", "cybersecurity",
        "property management", "construction technology",
        "education technology", "fintech", "autonomous systems",
        "robotics", "natural language processing", "drug discovery",
    ]

    for kw in keywords:
        try:
            url = "https://www.sbir.gov/api/awards.json"
            params = {"keyword": kw, "rows": 25, "start": 0}
            r = requests.get(url, params=params, headers=H, timeout=15)
            if r.status_code == 200:
                data = r.json()
                awards = data if isinstance(data, list) else data.get("results", data.get("awards", []))
                if isinstance(awards, list):
                    for a in awards[:25]:
                        items.append({
                            "source": "sbir",
                            "keyword": kw,
                            "title": a.get("award_title", a.get("title", "")),
                            "abstract": (a.get("abstract", "") or "")[:400],
                            "agency": a.get("agency", ""),
                            "amount": a.get("award_amount", a.get("amount", "")),
                            "year": a.get("award_year", a.get("year", "")),
                            "company": a.get("firm", a.get("company", "")),
                            "scraped_at": datetime.now().isoformat()
                        })
            time.sleep(0.5)
        except Exception as e:
            print(f"    ⚠ SBIR '{kw[:20]}' failed: {e}")

    count = save("sbir_grants", items)
    print(f"  ✓ SBIR: {count} grants saved")
    return items


# ═══════════════════════════════════════════════════════════════════════════════
# 2. BLS — Bureau of Labor Statistics (labor shortages, wage growth)
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_bls():
    print("\n  📊 Scraping BLS labor data...")
    items = []

    # BLS public API — employment by industry
    # Series IDs for major sectors
    series = {
        "CES3000000001": "Manufacturing",
        "CES5000000001": "Financial Activities",
        "CES6000000001": "Professional & Business Services",
        "CES6500000001": "Education & Health Services",
        "CES7000000001": "Leisure & Hospitality",
        "CES5051100001": "Information/Tech",
        "CES3100000001": "Construction",
        "CES4000000001": "Trade/Transport/Utilities",
        "CES9000000001": "Government",
    }

    try:
        url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
        payload = {
            "seriesid": list(series.keys()),
            "startyear": "2023",
            "endyear": "2026"
        }
        r = requests.post(url, json=payload, timeout=30)
        if r.status_code == 200:
            data = r.json()
            for result in data.get("Results", {}).get("series", []):
                sid = result.get("seriesID", "")
                sector = series.get(sid, sid)
                values = result.get("data", [])
                for v in values[:12]:  # Last 12 data points
                    items.append({
                        "source": "bls",
                        "sector": sector,
                        "series_id": sid,
                        "year": v.get("year", ""),
                        "period": v.get("periodName", ""),
                        "value": v.get("value", ""),
                        "scraped_at": datetime.now().isoformat()
                    })
    except Exception as e:
        print(f"    ⚠ BLS API failed: {e}")

    # Also scrape BLS news releases for labor shortage data
    try:
        r = requests.get("https://www.bls.gov/news.release/jolts.nr0.htm", headers=H, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            text = soup.get_text()[:3000]
            items.append({
                "source": "bls_jolts",
                "type": "job_openings_report",
                "summary": text[:2000],
                "scraped_at": datetime.now().isoformat()
            })
    except:
        pass

    count = save("bls_labor", items)
    print(f"  ✓ BLS: {count} data points saved")
    return items


# ═══════════════════════════════════════════════════════════════════════════════
# 3. ARXIV — Trending research papers (signals what tech is about to go commercial)
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_arxiv():
    print("\n  🔬 Scraping ArXiv research trends...")
    items = []

    categories = [
        ("cs.AI", "Artificial Intelligence"),
        ("cs.CV", "Computer Vision"),
        ("cs.LG", "Machine Learning"),
        ("cs.CL", "NLP / Language Models"),
        ("cs.RO", "Robotics"),
        ("cs.CR", "Cryptography & Security"),
        ("cs.SE", "Software Engineering"),
        ("cs.HC", "Human-Computer Interaction"),
        ("q-bio.QM", "Quantitative Biology"),
        ("econ.GN", "Economics"),
        ("stat.ML", "Statistics/ML"),
    ]

    for cat_id, cat_name in categories:
        try:
            url = f"http://export.arxiv.org/api/query?search_query=cat:{cat_id}&sortBy=submittedDate&sortOrder=descending&max_results=30"
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                root = ET.fromstring(r.text)
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                entries = root.findall("atom:entry", ns)
                for entry in entries:
                    title = entry.find("atom:title", ns)
                    summary = entry.find("atom:summary", ns)
                    published = entry.find("atom:published", ns)
                    items.append({
                        "source": "arxiv",
                        "category": cat_name,
                        "category_id": cat_id,
                        "title": (title.text.strip() if title is not None else ""),
                        "abstract": (summary.text.strip()[:400] if summary is not None else ""),
                        "published": (published.text if published is not None else ""),
                        "scraped_at": datetime.now().isoformat()
                    })
            time.sleep(1)
        except Exception as e:
            print(f"    ⚠ ArXiv {cat_name} failed: {e}")

    count = save("arxiv_papers", items)
    print(f"  ✓ ArXiv: {count} papers saved")
    return items


# ═══════════════════════════════════════════════════════════════════════════════
# 4. SEC EDGAR — Public company risk factors and competitive threats
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_sec():
    print("\n  📑 Scraping SEC EDGAR filings...")
    items = []

    # EDGAR full-text search API
    search_terms = [
        "artificial intelligence risk",
        "machine learning competitive",
        "automation threat",
        "cybersecurity challenge",
        "supply chain disruption",
        "labor shortage manufacturing",
        "healthcare technology investment",
        "quality control automation",
    ]

    for term in search_terms:
        try:
            url = "https://efts.sec.gov/LATEST/search-index"
            params = {"q": term, "dateRange": "custom", "startdt": "2025-01-01", "enddt": "2026-12-31", "forms": "10-K", "hits.hits.total": 10}
            
            # Use EDGAR full text search
            search_url = f"https://efts.sec.gov/LATEST/search-index?q=%22{requests.utils.quote(term)}%22&forms=10-K&dateRange=custom&startdt=2025-01-01&enddt=2026-03-08"
            r = requests.get(search_url, headers={**H, "Accept": "application/json"}, timeout=15)
            
            if r.status_code != 200:
                # Try alternate EDGAR API
                search_url = f"https://efts.sec.gov/LATEST/search-index?q={requests.utils.quote(term)}&forms=10-K"
                r = requests.get(search_url, headers=H, timeout=15)

            if r.status_code == 200:
                try:
                    data = r.json()
                    hits = data.get("hits", {}).get("hits", [])
                    for hit in hits[:10]:
                        src = hit.get("_source", {})
                        items.append({
                            "source": "sec_edgar",
                            "search_term": term,
                            "company": src.get("display_names", [""])[0] if src.get("display_names") else "",
                            "form_type": src.get("form_type", ""),
                            "filing_date": src.get("file_date", ""),
                            "description": src.get("display_description", "")[:300],
                            "scraped_at": datetime.now().isoformat()
                        })
                except:
                    pass
            time.sleep(1)
        except Exception as e:
            print(f"    ⚠ SEC '{term[:25]}' failed: {e}")

    # Also get EDGAR company filings for major tech companies
    tickers = ["AAPL", "GOOGL", "MSFT", "AMZN", "META", "NVDA", "TSLA", "CRM"]
    for ticker in tickers:
        try:
            url = f"https://data.sec.gov/submissions/CIK{ticker}.json"
            r = requests.get(url, headers={**H, "Accept": "application/json"}, timeout=10)
            if r.status_code != 200:
                # Try by company name search
                url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company={ticker}&type=10-K&dateb=&owner=include&count=5&search_text=&action=getcompany"
                r = requests.get(url, headers=H, timeout=10)
        except:
            pass

    count = save("sec_filings", items)
    print(f"  ✓ SEC EDGAR: {count} filings saved")
    return items


# ═══════════════════════════════════════════════════════════════════════════════
# 5. NIH REPORTER — Medical research funding
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_nih():
    print("\n  🏥 Scraping NIH research funding...")
    items = []

    search_terms = [
        "artificial intelligence healthcare",
        "machine learning clinical",
        "computer vision medical imaging",
        "drug discovery AI",
        "clinical trial optimization",
        "digital health",
        "remote patient monitoring",
        "mental health technology",
        "genomics AI",
        "medical device innovation",
    ]

    for term in search_terms:
        try:
            url = "https://api.reporter.nih.gov/v2/projects/search"
            payload = {
                "criteria": {
                    "advanced_text_search": {
                        "operator": "and",
                        "search_field": "projecttitle,terms",
                        "search_text": term
                    },
                    "fiscal_years": [2025, 2026]
                },
                "offset": 0,
                "limit": 20,
                "sort_field": "award_amount",
                "sort_order": "desc"
            }
            r = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
            if r.status_code == 200:
                data = r.json()
                results = data.get("results", [])
                for proj in results:
                    items.append({
                        "source": "nih",
                        "search_term": term,
                        "title": proj.get("project_title", ""),
                        "abstract": (proj.get("abstract_text", "") or "")[:400],
                        "organization": proj.get("organization", {}).get("org_name", ""),
                        "award_amount": proj.get("award_amount", 0),
                        "fiscal_year": proj.get("fiscal_year", ""),
                        "agency": proj.get("agency_ic_fundings", [{}])[0].get("name", "") if proj.get("agency_ic_fundings") else "",
                        "scraped_at": datetime.now().isoformat()
                    })
            time.sleep(0.5)
        except Exception as e:
            print(f"    ⚠ NIH '{term[:25]}' failed: {e}")

    count = save("nih_funding", items)
    print(f"  ✓ NIH: {count} projects saved")
    return items


# ═══════════════════════════════════════════════════════════════════════════════
# 6. GRANTS.GOV — Federal grant opportunities
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_grants_gov():
    print("\n  🇺🇸 Scraping Grants.gov opportunities...")
    items = []

    keywords = [
        "artificial intelligence", "machine learning", "automation",
        "manufacturing innovation", "small business technology",
        "healthcare innovation", "cybersecurity", "clean energy",
        "supply chain resilience", "workforce development technology",
    ]

    for kw in keywords:
        try:
            url = "https://www.grants.gov/grantsws/rest/opportunities/search/"
            params = {"keyword": kw, "oppStatuses": "posted", "rows": 15}
            r = requests.get(url, params=params, headers=H, timeout=15)
            if r.status_code == 200:
                data = r.json()
                opps = data.get("oppHits", [])
                for opp in opps:
                    items.append({
                        "source": "grants_gov",
                        "keyword": kw,
                        "title": opp.get("title", opp.get("oppTitle", "")),
                        "agency": opp.get("agency", opp.get("agencyName", "")),
                        "close_date": opp.get("closeDate", ""),
                        "award_ceiling": opp.get("awardCeiling", ""),
                        "description": opp.get("description", opp.get("synopsis", ""))[:300] if opp.get("description") or opp.get("synopsis") else "",
                        "scraped_at": datetime.now().isoformat()
                    })
            time.sleep(1)
        except Exception as e:
            print(f"    ⚠ Grants.gov '{kw[:20]}' failed: {e}")

    count = save("grants_gov", items)
    print(f"  ✓ Grants.gov: {count} opportunities saved")
    return items


# ═══════════════════════════════════════════════════════════════════════════════
# 7. KAGGLE — Competitions and datasets (what problems people pay to solve)
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_kaggle():
    print("\n  📊 Scraping Kaggle competitions & datasets...")
    items = []

    # Kaggle has a public meta API for competitions
    try:
        url = "https://www.kaggle.com/api/v1/competitions/list"
        r = requests.get(url, headers=H, timeout=15)
        if r.status_code == 200:
            comps = r.json() if isinstance(r.json(), list) else []
            for comp in comps[:50]:
                items.append({
                    "source": "kaggle_competition",
                    "title": comp.get("title", comp.get("ref", "")),
                    "description": (comp.get("description", "") or "")[:300],
                    "reward": comp.get("reward", ""),
                    "category": comp.get("category", ""),
                    "deadline": comp.get("deadline", ""),
                    "team_count": comp.get("teamCount", 0),
                    "scraped_at": datetime.now().isoformat()
                })
    except Exception as e:
        print(f"    ⚠ Kaggle API failed: {e}")

    # Scrape Kaggle datasets page
    try:
        url = "https://www.kaggle.com/datasets?sort=votes&fileType=all"
        r = requests.get(url, headers=H, timeout=15)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            scripts = soup.find_all("script")
            for script in scripts:
                text = script.string or ""
                if "datasetTitle" in text or "dataset" in text.lower():
                    items.append({
                        "source": "kaggle_datasets",
                        "raw": text[:2000],
                        "scraped_at": datetime.now().isoformat()
                    })
    except Exception as e:
        print(f"    ⚠ Kaggle datasets failed: {e}")

    count = save("kaggle", items)
    print(f"  ✓ Kaggle: {count} items saved")
    return items


# ═══════════════════════════════════════════════════════════════════════════════
# 8. WIKIPEDIA — List of unicorn startups
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_unicorns():
    print("\n  🦄 Scraping unicorn startup data...")
    items = []

    try:
        # Wikipedia API for unicorn list
        url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "parse",
            "page": "List_of_unicorn_startup_companies",
            "prop": "wikitext",
            "format": "json"
        }
        r = requests.get(url, params=params, headers=H, timeout=15)
        if r.status_code == 200:
            data = r.json()
            wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")
            
            # Parse the wikitext table rows
            lines = wikitext.split("\n")
            for line in lines:
                if line.startswith("|-") or not line.startswith("|"):
                    continue
                cells = line.split("||")
                if len(cells) >= 3:
                    items.append({
                        "source": "wikipedia_unicorns",
                        "raw": line[:500],
                        "scraped_at": datetime.now().isoformat()
                    })
    except Exception as e:
        print(f"    ⚠ Wikipedia unicorns failed: {e}")

    # Also try CB Insights unicorn list via Google cache
    try:
        url = "https://en.wikipedia.org/w/api.php"
        params = {"action": "parse", "page": "List_of_unicorn_startup_companies", "prop": "text", "format": "json"}
        r = requests.get(url, params=params, headers=H, timeout=15)
        if r.status_code == 200:
            html = r.json().get("parse", {}).get("text", {}).get("*", "")
            soup = BeautifulSoup(html, "html.parser")
            tables = soup.find_all("table", class_="wikitable")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows[1:]:  # Skip header
                    cells = row.find_all(["td", "th"])
                    if len(cells) >= 4:
                        items.append({
                            "source": "wikipedia_unicorns",
                            "company": cells[0].get_text(strip=True),
                            "valuation": cells[1].get_text(strip=True) if len(cells) > 1 else "",
                            "date_joined": cells[2].get_text(strip=True) if len(cells) > 2 else "",
                            "country": cells[3].get_text(strip=True) if len(cells) > 3 else "",
                            "industry": cells[4].get_text(strip=True) if len(cells) > 4 else "",
                            "scraped_at": datetime.now().isoformat()
                        })
    except Exception as e:
        print(f"    ⚠ Wikipedia table parse failed: {e}")

    count = save("unicorns", items)
    print(f"  ✓ Unicorns: {count} companies saved")
    return items


# ═══════════════════════════════════════════════════════════════════════════════
# 9. AWS MARKETPLACE — SaaS tools selling on cloud
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_aws_marketplace():
    print("\n  ☁️ Scraping AWS Marketplace...")
    items = []

    categories = [
        "machine-learning", "security", "business-applications",
        "iot", "financial-services", "healthcare",
        "industrial", "media", "developer-tools",
    ]

    for cat in categories:
        try:
            url = f"https://aws.amazon.com/marketplace/search/results?category={cat}&FULFILLMENT_OPTION_TYPE=SAAS&ref_=header_nav_dm_saas"
            r = requests.get(url, headers=H, timeout=15)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                # Extract product listings
                cards = soup.find_all(["div", "article"], class_=lambda x: x and ("card" in str(x).lower() or "product" in str(x).lower() or "listing" in str(x).lower()))
                for card in cards[:20]:
                    title = card.find(["h2", "h3", "a"])
                    desc = card.find("p") or card.find("span")
                    items.append({
                        "source": "aws_marketplace",
                        "category": cat,
                        "name": title.get_text(strip=True) if title else "",
                        "description": (desc.get_text(strip=True) if desc else "")[:200],
                        "scraped_at": datetime.now().isoformat()
                    })

                # Also check for structured data
                scripts = soup.find_all("script", {"type": "application/json"})
                for script in scripts:
                    try:
                        data = json.loads(script.string)
                        text = json.dumps(data)
                        if "product" in text.lower() and len(text) > 100:
                            items.append({
                                "source": "aws_marketplace",
                                "category": cat,
                                "raw": text[:2000],
                                "scraped_at": datetime.now().isoformat()
                            })
                    except:
                        pass
            time.sleep(1)
        except Exception as e:
            print(f"    ⚠ AWS {cat} failed: {e}")

    count = save("aws_marketplace", items)
    print(f"  ✓ AWS Marketplace: {count} items saved")
    return items


# ═══════════════════════════════════════════════════════════════════════════════
# 10. DEV.TO — Developer blog posts about tools they wish existed
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_devto():
    print("\n  ✍️ Scraping DEV.to articles...")
    items = []

    # DEV.to has a public API
    tags = ["ai", "machinelearning", "saas", "startup", "devops",
            "automation", "productivity", "opensource", "webdev", "cloud"]

    for tag in tags:
        try:
            url = f"https://dev.to/api/articles?tag={tag}&top=30&per_page=30"
            r = requests.get(url, headers=H, timeout=15)
            if r.status_code == 200:
                articles = r.json()
                for art in articles:
                    items.append({
                        "source": "devto",
                        "tag": tag,
                        "title": art.get("title", ""),
                        "description": art.get("description", "")[:200],
                        "reactions": art.get("positive_reactions_count", 0),
                        "comments": art.get("comments_count", 0),
                        "url": art.get("url", ""),
                        "published": art.get("published_at", ""),
                        "tags": art.get("tag_list", []),
                        "scraped_at": datetime.now().isoformat()
                    })
            time.sleep(0.5)
        except Exception as e:
            print(f"    ⚠ DEV.to {tag} failed: {e}")

    count = save("devto_articles", items)
    print(f"  ✓ DEV.to: {count} articles saved")
    return items


# ═══════════════════════════════════════════════════════════════════════════════
# 11. CENSUS BUSINESS DATA — Number of businesses by industry
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_census():
    print("\n  🏢 Scraping Census business data...")
    items = []

    try:
        # Census County Business Patterns API
        url = "https://api.census.gov/data/2022/cbp"
        params = {
            "get": "ESTAB,EMP,PAYANN,NAICS2017_LABEL",
            "for": "us:*",
            "NAICS2017": "31-33,51,52,54,56,62,23,42,44-45,48-49,61,71,72,81,92",  # Major industry codes
        }
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            data = r.json()
            headers_row = data[0]
            for row in data[1:]:
                record = dict(zip(headers_row, row))
                items.append({
                    "source": "census",
                    "industry": record.get("NAICS2017_LABEL", ""),
                    "naics_code": record.get("NAICS2017", ""),
                    "establishments": record.get("ESTAB", ""),
                    "employees": record.get("EMP", ""),
                    "annual_payroll_thousands": record.get("PAYANN", ""),
                    "scraped_at": datetime.now().isoformat()
                })
    except Exception as e:
        print(f"    ⚠ Census API failed: {e}")

    count = save("census_business", items)
    print(f"  ✓ Census: {count} industry records saved")
    return items


# ═══════════════════════════════════════════════════════════════════════════════
# 12. WORLD BANK — Global economic indicators by sector
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_worldbank():
    print("\n  🌍 Scraping World Bank indicators...")
    items = []

    indicators = {
        "NV.IND.MANF.ZS": "Manufacturing % of GDP",
        "NV.SRV.TOTL.ZS": "Services % of GDP",
        "GB.XPD.RSDV.GD.ZS": "R&D Expenditure % of GDP",
        "IT.NET.USER.ZS": "Internet Users %",
        "SL.UEM.TOTL.ZS": "Unemployment Rate",
        "NY.GDP.MKTP.KD.ZG": "GDP Growth Rate",
        "FP.CPI.TOTL.ZG": "Inflation Rate",
        "IC.BUS.NREG": "New Business Registrations",
    }

    countries = "USA;CHN;GBR;DEU;IND;JPN;KOR;ISR;SGP;BRA"

    for code, name in indicators.items():
        try:
            url = f"https://api.worldbank.org/v2/country/{countries}/indicator/{code}?date=2020:2025&format=json&per_page=100"
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                data = r.json()
                if len(data) > 1:
                    for record in data[1] or []:
                        if record.get("value") is not None:
                            items.append({
                                "source": "worldbank",
                                "indicator": name,
                                "indicator_code": code,
                                "country": record.get("country", {}).get("value", ""),
                                "year": record.get("date", ""),
                                "value": record.get("value"),
                                "scraped_at": datetime.now().isoformat()
                            })
            time.sleep(0.3)
        except Exception as e:
            print(f"    ⚠ WB {name} failed: {e}")

    count = save("worldbank", items)
    print(f"  ✓ World Bank: {count} data points saved")
    return items


# ═══════════════════════════════════════════════════════════════════════════════
# 13. MEDIUM/DEV BLOGS — "Someone should build" type posts via search
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_blog_ideas():
    print("\n  💡 Scraping startup idea posts...")
    items = []

    # HN Algolia search for "someone should build" type content
    searches = [
        "someone should build",
        "why doesn't exist",
        "I wish there was",
        "startup idea",
        "million dollar idea",
        "looking for a tool that",
        "frustrated with",
        "show hn",
        "built this because",
        "scratching my own itch",
    ]

    for q in searches:
        try:
            url = f"https://hn.algolia.com/api/v1/search?query={requests.utils.quote(q)}&tags=story&hitsPerPage=20&numericFilters=points>10"
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                hits = r.json().get("hits", [])
                for hit in hits:
                    items.append({
                        "source": "hn_ideas",
                        "search": q,
                        "title": hit.get("title", ""),
                        "url": hit.get("url", ""),
                        "points": hit.get("points", 0),
                        "comments": hit.get("num_comments", 0),
                        "date": hit.get("created_at", ""),
                        "scraped_at": datetime.now().isoformat()
                    })
            time.sleep(0.5)
        except Exception as e:
            print(f"    ⚠ HN search '{q[:20]}' failed: {e}")

    count = save("blog_ideas", items)
    print(f"  ✓ Blog ideas: {count} posts saved")
    return items


# ═══════════════════════════════════════════════════════════════════════════════
# 14. GITHUB ISSUES — Most-requested features in popular repos
# ═══════════════════════════════════════════════════════════════════════════════
def scrape_github_issues():
    print("\n  🐛 Scraping GitHub most-wanted features...")
    items = []

    # Search for highly upvoted feature requests
    queries = [
        "label:enhancement label:feature-request sort:reactions-+1-desc",
        "label:\"help wanted\" sort:reactions-+1-desc",
        "\"feature request\" sort:reactions-+1-desc",
    ]

    for q in queries:
        try:
            url = f"https://api.github.com/search/issues?q={requests.utils.quote(q)}&sort=reactions-+1&order=desc&per_page=30"
            r = requests.get(url, headers={**H, "Accept": "application/vnd.github.v3+json"}, timeout=15)
            if r.status_code == 200:
                issues = r.json().get("items", [])
                for issue in issues:
                    items.append({
                        "source": "github_issues",
                        "title": issue.get("title", ""),
                        "repo": issue.get("repository_url", "").split("/repos/")[-1] if issue.get("repository_url") else "",
                        "reactions": issue.get("reactions", {}).get("total_count", 0),
                        "thumbs_up": issue.get("reactions", {}).get("+1", 0),
                        "comments": issue.get("comments", 0),
                        "state": issue.get("state", ""),
                        "url": issue.get("html_url", ""),
                        "created": issue.get("created_at", ""),
                        "labels": [l.get("name", "") for l in issue.get("labels", [])],
                        "scraped_at": datetime.now().isoformat()
                    })
            time.sleep(2)
        except Exception as e:
            print(f"    ⚠ GH issues failed: {e}")

    count = save("github_issues", items)
    print(f"  ✓ GitHub Issues: {count} feature requests saved")
    return items


# ═══════════════════════════════════════════════════════════════════════════════
# MASTER RUNNER
# ═══════════════════════════════════════════════════════════════════════════════
ALL_SCRAPERS = {
    "sbir": scrape_sbir,
    "bls": scrape_bls,
    "arxiv": scrape_arxiv,
    "sec": scrape_sec,
    "nih": scrape_nih,
    "grants": scrape_grants_gov,
    "kaggle": scrape_kaggle,
    "unicorns": scrape_unicorns,
    "aws": scrape_aws_marketplace,
    "devto": scrape_devto,
    "census": scrape_census,
    "worldbank": scrape_worldbank,
    "ideas": scrape_blog_ideas,
    "gh_issues": scrape_github_issues,
}

def run_all():
    print("=" * 65)
    print("  YC INTELLIGENCE — Mega Data Scraper")
    print(f"  {len(ALL_SCRAPERS)} sources · {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 65)

    results = {}
    for name, func in ALL_SCRAPERS.items():
        try:
            data = func()
            results[name] = len(data) if data else 0
        except Exception as e:
            print(f"  ⚠ {name} CRASHED: {e}")
            results[name] = 0

    # Update master summary
    summary_path = os.path.join(OUTPUT_DIR, "scrape_summary.json")
    summary = {}
    if os.path.exists(summary_path):
        with open(summary_path) as f:
            summary = json.load(f)

    if "sources" not in summary:
        summary["sources"] = {}

    summary["mega_scraped_at"] = datetime.now().isoformat()
    summary["sources"].update(results)
    summary["total_data_points"] = sum(summary["sources"].values())

    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 65)
    print("  MEGA SCRAPE COMPLETE")
    print("=" * 65)
    total = 0
    for source, count in sorted(results.items(), key=lambda x: -x[1]):
        bar = "█" * min(count // 5, 40)
        print(f"  {source:<15} {count:>6} items  {bar}")
        total += count
    print(f"\n  New data: {total:,} items across {len(results)} sources")
    print(f"  Saved to: {OUTPUT_DIR}/")
    print(f"\n  Run  python3 multi_analyzer.py  for full cross-source analysis")
    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=str, choices=list(ALL_SCRAPERS.keys()))
    args = parser.parse_args()

    if args.source:
        ALL_SCRAPERS[args.source]()
    else:
        run_all()
