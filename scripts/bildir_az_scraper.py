#!/usr/bin/env python3
"""
bildir.az Company Scraper
Scrapes all companies from bildir.az/sirketler/ and their detail pages.
Output: data/data.csv

Selectors verified against live HTML (2026-02).
"""

import csv
import time
import logging
import os
import re

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_URL   = "https://www.bildir.az"
LIST_URL   = f"{BASE_URL}/sirketler/"
OUTPUT_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "data.csv")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "az,en-US;q=0.9,en;q=0.8",
}

REQUEST_DELAY = 1.2   # seconds between requests
MAX_RETRIES   = 3
TIMEOUT       = 15

# Domains that belong to bildir.az itself (filter out from social/website)
BILDIR_DOMAINS = {"bildir.az", "www.bildir.az", "facebook.com/bildir.az",
                  "instagram.com/bildir.az", "linkedin.com/company/bildir-az"}

CSV_FIELDS = [
    "slug",
    "name",
    "category",
    "founded",
    "description",
    "website",
    "facebook",
    "instagram",
    "linkedin",
    "youtube",
    "twitter",
    "overall_rating",
    "total_reviews",
    "response_rate_pct",
    "resolved_complaints_pct",
    "customer_loyalty_pct",
    "star5_pct",
    "star4_pct",
    "star3_pct",
    "star2_pct",
    "star1_pct",
    "profile_url",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------
session = requests.Session()
session.headers.update(HEADERS)


def get(url: str):
    """Fetch a URL with retries; return BeautifulSoup or None on failure."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as exc:
            log.warning("Attempt %d/%d failed for %s: %s", attempt, MAX_RETRIES, url, exc)
            if attempt < MAX_RETRIES:
                time.sleep(REQUEST_DELAY * attempt)
    log.error("Giving up on %s", url)
    return None


# ---------------------------------------------------------------------------
# Listing page – collect slugs
# ---------------------------------------------------------------------------
def get_total_pages(soup: BeautifulSoup) -> int:
    max_page = 1
    for a in soup.select("a[href*='page=']"):
        m = re.search(r"page=(\d+)", a.get("href", ""))
        if m:
            max_page = max(max_page, int(m.group(1)))
    return max_page


def parse_listing_page(soup: BeautifulSoup) -> list:
    companies = []
    for anchor in soup.select("a.company-wrapper"):
        href = anchor.get("href", "").strip("/")
        slug = href.split("/")[-1] if href else ""
        if not slug:
            continue
        companies.append({"slug": slug})
    return companies


def collect_all_slugs() -> list:
    log.info("Fetching page 1 to detect total pages …")
    soup = get(f"{LIST_URL}?page=1")
    if soup is None:
        log.error("Could not fetch listing page 1.")
        return []

    total = get_total_pages(soup)
    log.info("Total pages detected: %d", total)

    all_companies = list(parse_listing_page(soup))
    time.sleep(REQUEST_DELAY)

    for page in range(2, total + 1):
        log.info("Listing page %d/%d …", page, total)
        s = get(f"{LIST_URL}?page={page}")
        if s:
            all_companies.extend(parse_listing_page(s))
        time.sleep(REQUEST_DELAY)

    log.info("Collected %d company slugs.", len(all_companies))
    return all_companies


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
BILDIR_SOCIAL = {
    "facebook.com/bildir",
    "instagram.com/bildir",
    "linkedin.com/company/bildir",
}


def is_bildir_link(url: str) -> bool:
    """Return True if the URL belongs to bildir.az itself."""
    lower = url.lower()
    if "bildir.az" in lower and not any(
        s in lower for s in ["facebook.com", "instagram.com", "linkedin.com",
                              "twitter.com", "youtube.com"]
    ):
        return True
    return any(s in lower for s in BILDIR_SOCIAL)


def pct_from_style(style: str) -> str:
    """Extract percentage value from CSS style like 'width: 22.7%'."""
    m = re.search(r"([\d.]+)%", style)
    return m.group(1) if m else ""


# ---------------------------------------------------------------------------
# Company detail page
# ---------------------------------------------------------------------------
def parse_company_page(slug: str) -> dict:
    url = f"{BASE_URL}/{slug}/"
    soup = get(url)
    data = {f: "" for f in CSV_FIELDS}
    data["slug"] = slug
    data["profile_url"] = url

    if soup is None:
        return data

    # ---- Name -------------------------------------------------------
    name_div = soup.select_one("#company-name h1")
    if name_div:
        span = name_div.find("span", class_="title-span")
        if span:
            span.decompose()
        data["name"] = name_div.get_text(strip=True)

    # ---- Category (from breadcrumb) ---------------------------------
    crumb = soup.select_one(".breadcrumb")
    if crumb:
        links = crumb.select("a")
        # breadcrumb: Ana Səhifə > Şirkətlər > Category > (company)
        if len(links) >= 3:
            data["category"] = links[-1].get_text(strip=True)

    # ---- Rating -----------------------------------------------------
    rating_el = soup.select_one(".star-rating__result span")
    if rating_el:
        data["overall_rating"] = rating_el.get_text(strip=True).replace(",", ".")

    # ---- Total reviews ----------------------------------------------
    rev_stat = soup.select_one("#review-statistics")
    if rev_stat:
        m = re.search(r"(\d+)\s*rəy", rev_stat.get_text())
        if m:
            data["total_reviews"] = m.group(1)

    # ---- Response rate, resolved, loyalty ---------------------------
    reply_el = soup.select_one(".reply-percent h6")
    if reply_el:
        data["response_rate_pct"] = reply_el.get_text(strip=True).replace("%", "").strip()

    solved_el = soup.select_one(".solved-complaints h6")
    if solved_el:
        data["resolved_complaints_pct"] = solved_el.get_text(strip=True).replace("%", "").strip()

    loyalty_el = soup.select_one(".customer-loyalty h6")
    if loyalty_el:
        data["customer_loyalty_pct"] = loyalty_el.get_text(strip=True).replace("%", "").strip()

    # ---- Star distribution (5 progress bars in order 5→1) -----------
    bars = soup.select("div.jesus-progress")
    star_keys = ["star5_pct", "star4_pct", "star3_pct", "star2_pct", "star1_pct"]
    for i, bar in enumerate(bars[:5]):
        style = bar.get("style", "")
        data[star_keys[i]] = pct_from_style(style)

    # ---- Description and Founded ------------------------------------
    desc_el = soup.select_one("p.short")
    if desc_el:
        desc_text = desc_el.get_text(strip=True)
        data["description"] = desc_text
        # Extract founded date: "10 yanvar 1992" or just year
        m = re.search(r"\d{1,2}\s+\w+\s+\d{4}", desc_text)
        if m:
            data["founded"] = m.group(0)
        else:
            m2 = re.search(r"\b(19|20)\d{2}\b", desc_text)
            if m2:
                data["founded"] = m2.group(0)

    # ---- Website ----------------------------------------------------
    container = soup.select_one(".company-about-container")
    if container:
        for a in container.find_all("a", href=True):
            href = a["href"]
            if not href.startswith("http"):
                continue
            if "bildir.az" in href:
                continue
            if any(s in href.lower() for s in ["facebook", "instagram",
                                                "linkedin", "twitter", "youtube"]):
                continue
            data["website"] = href
            break

    # ---- Social links (only real company links) ---------------------
    social_targets = {
        "facebook": "facebook",
        "instagram": "instagram",
        "linkedin": "linkedin",
        "youtube":  "youtube",
        "twitter":  "twitter",
    }
    if container:
        for a in container.find_all("a", href=True):
            href = a["href"]
            if is_bildir_link(href):
                continue
            for platform, key in social_targets.items():
                if platform in href.lower() and not data[key]:
                    data[key] = href

    return data


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

    # Step 1: Collect all slugs
    stubs = collect_all_slugs()
    if not stubs:
        log.error("No companies found – aborting.")
        return

    # Deduplicate preserving order
    seen = set()
    unique = []
    for s in stubs:
        if s["slug"] not in seen:
            seen.add(s["slug"])
            unique.append(s)
    log.info("Unique companies after dedup: %d", len(unique))

    # Step 2: Scrape detail pages, write CSV incrementally
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()

        for idx, stub in enumerate(unique, 1):
            slug = stub["slug"]
            log.info("[%d/%d] Scraping %s …", idx, len(unique), slug)
            detail = parse_company_page(slug)
            writer.writerow(detail)
            fh.flush()
            time.sleep(REQUEST_DELAY)

    log.info("Done! CSV saved to: %s", OUTPUT_CSV)


if __name__ == "__main__":
    main()
