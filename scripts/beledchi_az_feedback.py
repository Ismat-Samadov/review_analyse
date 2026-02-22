"""
Scraper for beledci.az feedback/reviews.
Scrapes all pages (1–106) and saves to data/feedbacks.csv.

Usage:
    python scripts/feedback.py
    python scripts/feedback.py --start 1 --end 106 --delay 1.0
"""

import argparse
import csv
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://beledci.az"
OUTPUT_PATH = Path(__file__).parent.parent / "data" / "feedbacks.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "az,en;q=0.9",
}

CSV_FIELDS = [
    "review_id",
    "reviewer_name",
    "company_name",
    "company_slug",
    "company_url",
    "rating",
    "review_text",
    "review_url",
    "has_images",
    "page",
]


def get_last_page(session: requests.Session) -> int:
    """Fetch page 1 and extract the last page number from pagination."""
    resp = session.get(f"{BASE_URL}/?page=1", headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    last = soup.select_one("div.pagination span.last a")
    if last and last.get("href"):
        m = re.search(r"page=(\d+)", last["href"])
        if m:
            return int(m.group(1))
    return 1


def parse_rating(review_div) -> int:
    """Count filled stars in a review div."""
    filled = review_div.select("div.review-rating img[src*='star_filled.svg']")
    return len(filled)


def parse_review(div, page: int) -> dict | None:
    """Extract all fields from a single div.review element."""
    # Review ID from paragraph id attribute: id="r-6949"
    review_p = div.select_one("p.review-text")
    if not review_p:
        return None

    rid_raw = review_p.get("id", "")
    review_id = rid_raw.replace("r-", "") if rid_raw else ""

    # Reviewer name
    author_strong = div.select_one("div.review-author-info strong")
    reviewer_name = author_strong.get_text(strip=True) if author_strong else ""

    # Company name and slug
    company_a = div.select_one("div.review-author-info span.review-author-subline a")
    company_name = company_a.get_text(strip=True) if company_a else ""
    company_slug = company_a["href"] if company_a else ""
    company_url = f"{BASE_URL}{company_slug}" if company_slug else ""

    # Rating
    rating = parse_rating(div)

    # Review text
    review_text = review_p.get_text(strip=True)

    # Review URL
    review_url = f"{BASE_URL}{company_slug}/{review_id}" if company_slug and review_id else ""

    # Has images
    attachments = div.select("ul.attachments li a")
    has_images = len(attachments) > 0

    return {
        "review_id": review_id,
        "reviewer_name": reviewer_name,
        "company_name": company_name,
        "company_slug": company_slug,
        "company_url": company_url,
        "rating": rating,
        "review_text": review_text,
        "review_url": review_url,
        "has_images": has_images,
        "page": page,
    }


def scrape_page(session: requests.Session, page: int) -> list[dict]:
    """Fetch a single listing page and return list of review dicts."""
    url = f"{BASE_URL}/?page={page}"
    resp = session.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    reviews = []
    for div in soup.select("div.review"):
        row = parse_review(div, page)
        if row:
            reviews.append(row)
    return reviews


def scrape_all(start: int, end: int, delay: float) -> None:
    """Scrape pages start..end (inclusive) and write to CSV."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with requests.Session() as session, open(
        OUTPUT_PATH, "w", newline="", encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()

        total_rows = 0
        for page in range(start, end + 1):
            try:
                rows = scrape_page(session, page)
            except requests.RequestException as e:
                print(f"  [ERROR] page {page}: {e}")
                rows = []

            writer.writerows(rows)
            f.flush()
            total_rows += len(rows)
            print(f"  page {page:>4}/{end}  →  {len(rows):>2} reviews  (total: {total_rows})")

            if page < end and delay > 0:
                time.sleep(delay)

    print(f"\nDone. {total_rows} reviews saved to {OUTPUT_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape beledci.az reviews")
    parser.add_argument("--start", type=int, default=1, help="First page (default: 1)")
    parser.add_argument("--end", type=int, default=0, help="Last page (default: auto-detect)")
    parser.add_argument(
        "--delay", type=float, default=0.5, help="Seconds between requests (default: 0.5)"
    )
    args = parser.parse_args()

    with requests.Session() as session:
        last_page = get_last_page(session) if args.end == 0 else args.end

    print(f"Scraping pages {args.start}–{last_page} with {args.delay}s delay …")
    scrape_all(args.start, last_page, args.delay)


if __name__ == "__main__":
    main()
