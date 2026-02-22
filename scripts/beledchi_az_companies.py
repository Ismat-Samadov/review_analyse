"""
Scraper for beledci.az company data.

Flow:
  1. Fetch each category page  → collect all company slugs + basic listing data
  2. Fetch each company profile → collect numeric rating + full category label

Output: data/companies.csv

Usage:
    python scripts/companies.py
    python scripts/companies.py --delay 0.5 --skip-profile
"""

import argparse
import csv
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://beledci.az"
OUTPUT_PATH = Path(__file__).parent.parent / "data" / "companies.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "az,en;q=0.9",
}

# All 16 categories from the aside block
CATEGORIES = [
    ("restaurant",       "Restoranlar"),
    ("tourism",          "Turizm"),
    ("electronics-store","Elektronika"),
    ("supermarket",      "Supermarketlər"),
    ("services",         "Xidmətlər"),
    ("bank",             "Banklar"),
    ("apparel-store",    "Geyim mağazaları"),
    ("carrier",          "Mobil operatorlar"),
    ("internet-provider","İnternet provayderlər"),
    ("taxi",             "Taksi"),
    ("beauty",           "Gözəllik və baxım"),
    ("clinics",          "Tibb mərkəzləri"),
    ("education",        "Tədris mərkəzləri"),
    ("hotel",            "Otellər"),
    ("cargo",            "Karqo"),
    ("entertainment",    "Əyləncə"),
]

CSV_FIELDS = [
    "slug",
    "name",
    "company_url",
    "category_slug",
    "category_name",
    "category_label",
    "rating_value",
    "rating_label",
    "rating_stars",
    "review_count",
    "photo_url",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def count_filled_stars(container) -> int:
    """Count filled star images inside a BeautifulSoup element."""
    return len(container.select("img[src*='star_filled.svg']"))


def parse_review_count(rate_p) -> int:
    """Extract integer from p.rate text like '(54)'."""
    if rate_p is None:
        return 0
    text = rate_p.get_text(strip=True)
    m = re.search(r"\d+", text)
    return int(m.group()) if m else 0


# ---------------------------------------------------------------------------
# Step 1 – scrape category listing pages
# ---------------------------------------------------------------------------

def scrape_category(session: requests.Session, cat_slug: str, cat_name: str) -> list[dict]:
    """Return list of basic company dicts from /cat/{cat_slug}."""
    url = f"{BASE_URL}/cat/{cat_slug}"
    resp = session.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    companies = []
    for card in soup.select("a.company-card"):
        slug = card.get("href", "").strip("/")
        if not slug:
            continue

        name_tag = card.select_one("strong")
        name = name_tag.get_text(strip=True) if name_tag else ""

        photo_tag = card.select_one("img.company-avatar")
        photo_url = photo_tag.get("src", "") if photo_tag else ""

        rating_div = card.select_one("div.category-page--item-rating")
        stars = count_filled_stars(rating_div) if rating_div else 0

        rating_desc = card.select_one("p.rating-description")
        rating_label = ""
        if rating_desc:
            text = rating_desc.get_text(separator=" ", strip=True)
            # "Reytinq: Aşağı" → "Aşağı"
            rating_label = text.replace("Reytinq:", "").strip()

        rate_p = card.select_one("p.rate")
        review_count = parse_review_count(rate_p)

        companies.append({
            "slug": slug,
            "name": name,
            "company_url": f"{BASE_URL}/{slug}",
            "category_slug": cat_slug,
            "category_name": cat_name,
            "category_label": "",      # filled in step 2
            "rating_value": "",        # filled in step 2
            "rating_label": rating_label,
            "rating_stars": stars,
            "review_count": review_count,
            "photo_url": photo_url,
        })

    return companies


def collect_all_companies(session: requests.Session, delay: float) -> list[dict]:
    """Scrape all category pages and deduplicate companies."""
    seen: dict[str, dict] = {}  # slug → row

    for cat_slug, cat_name in CATEGORIES:
        print(f"  category: {cat_name} (/cat/{cat_slug})")
        try:
            rows = scrape_category(session, cat_slug, cat_name)
        except requests.RequestException as e:
            print(f"    [ERROR] {e}")
            rows = []

        for row in rows:
            slug = row["slug"]
            if slug not in seen:
                seen[slug] = row
            # If already seen in another category, keep first occurrence
            # (companies appear to belong to one category only)

        print(f"    → {len(rows)} companies  (unique so far: {len(seen)})")
        time.sleep(delay)

    return list(seen.values())


# ---------------------------------------------------------------------------
# Step 2 – enrich with individual company profile pages
# ---------------------------------------------------------------------------

def fetch_company_profile(session: requests.Session, slug: str) -> dict:
    """Return {rating_value, category_label} from the company's own page."""
    url = f"{BASE_URL}/{slug}"
    resp = session.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Numeric rating: div.rate  → "1.0 / 5.0"
    rate_div = soup.select_one("div.company-general div.rate")
    rating_value = ""
    if rate_div:
        raw = rate_div.get_text(separator=" ", strip=True)
        m = re.search(r"[\d.]+", raw)
        rating_value = m.group() if m else ""

    # Full category label: a.company-category text
    cat_a = soup.select_one("a.company-category")
    category_label = cat_a.get_text(strip=True) if cat_a else ""

    return {"rating_value": rating_value, "category_label": category_label}


def enrich_companies(
    session: requests.Session, companies: list[dict], delay: float
) -> None:
    """In-place enrich each company dict with profile data."""
    total = len(companies)
    for i, row in enumerate(companies, 1):
        slug = row["slug"]
        try:
            profile = fetch_company_profile(session, slug)
            row.update(profile)
        except requests.RequestException as e:
            print(f"  [ERROR] {slug}: {e}")

        print(f"  [{i:>3}/{total}] {row['name']:<35} rating={row['rating_value']}")
        if i < total:
            time.sleep(delay)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape beledci.az company data")
    parser.add_argument(
        "--delay", type=float, default=0.5,
        help="Seconds between requests (default: 0.5)"
    )
    parser.add_argument(
        "--skip-profile", action="store_true",
        help="Skip individual company profile fetch (faster, less data)"
    )
    args = parser.parse_args()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with requests.Session() as session:
        # Step 1 – collect companies from category pages
        print("\n=== Step 1: Scraping category pages ===")
        companies = collect_all_companies(session, args.delay)
        print(f"\nTotal unique companies: {len(companies)}")

        # Step 2 – enrich with company profile pages
        if not args.skip_profile:
            print("\n=== Step 2: Fetching company profiles ===")
            enrich_companies(session, companies, args.delay)

    # Write CSV
    companies.sort(key=lambda r: (r["category_slug"], r["name"]))
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(companies)

    print(f"\nDone. {len(companies)} companies saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
