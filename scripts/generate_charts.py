#!/usr/bin/env python3
"""Generate bank-focused, company-level charts and business insights."""

from __future__ import annotations

from pathlib import Path
import re

import pandas as pd
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CHARTS_DIR = BASE_DIR / "charts"
README_PATH = BASE_DIR / "README.md"

BELEDCHI_COMPANIES = DATA_DIR / "beledchi_az_companies.csv"
BELEDCHI_REVIEWS = DATA_DIR / "beledchi_az_feedbacks.csv"
BILDIR_DATA = DATA_DIR / "bildir_az_data.csv"

MIN_REVIEWS = 20

STOPWORDS = {
    "ve", "də", "da", "bu", "o", "mən", "men", "biz", "siz", "onlar",
    "bir", "iki", "üç", "uc", "dörd", "dord", "beş", "bes",
    "ilə", "ile", "amma", "ki", "çox", "cox", "heç", "hec",
    "üçün", "ucun", "olan", "olar", "olur", "deyil", "var", "yox",
    "bank", "banka", "banklar", "banki", "bankda", "bankdan",
    "and", "the", "a", "an", "to", "for", "of", "in", "on",
    "is", "are", "was", "were", "it", "this", "that", "with",
}


def _to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _norm_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    lowered = name.lower()
    cleaned = re.sub(r"[^a-z0-9]+", "", lowered)
    return cleaned


def load_data():
    companies = pd.read_csv(BELEDCHI_COMPANIES)
    reviews = pd.read_csv(BELEDCHI_REVIEWS)
    bildir = pd.read_csv(BILDIR_DATA)
    return companies, reviews, bildir


def filter_banks(companies: pd.DataFrame, reviews: pd.DataFrame, bildir: pd.DataFrame):
    comp = companies.copy()
    comp["category_name"] = comp["category_name"].fillna("")
    banks_companies = comp[
        (comp["category_slug"] == "bank")
        | (comp["category_name"].str.lower() == "banklar")
    ].copy()

    reviews = reviews.copy()
    reviews["company_slug"] = reviews["company_slug"].fillna("")
    reviews["slug"] = reviews["company_slug"].str.strip("/")

    bank_slugs = set(banks_companies["slug"].dropna())
    bank_reviews = reviews[reviews["slug"].isin(bank_slugs)].copy()

    bildir = bildir.copy()
    bildir["category"] = bildir["category"].fillna("")
    bildir_banks = bildir[bildir["category"].str.contains("Bank", case=False, na=False)].copy()

    return banks_companies, bank_reviews, bildir_banks


def build_company_metrics(banks_companies, bank_reviews, bildir_banks):
    banks_companies = banks_companies.copy()
    bank_reviews = bank_reviews.copy()
    bildir_banks = bildir_banks.copy()

    banks_companies["name"] = banks_companies["name"].fillna("")
    slug_to_name = banks_companies.set_index("slug")["name"].to_dict()
    bank_reviews["bank_name"] = bank_reviews["slug"].map(slug_to_name).fillna(bank_reviews["slug"])
    bank_reviews["rating"] = _to_numeric(bank_reviews["rating"]).fillna(0)

    review_stats = (
        bank_reviews.groupby("bank_name")["rating"]
        .agg(review_count="count", avg_rating="mean")
        .reset_index()
    )
    review_stats["name_key"] = review_stats["bank_name"].apply(_norm_name)

    bank_reviews["low_rating"] = bank_reviews["rating"].isin([1, 2]).astype(int)
    low_stats = (
        bank_reviews.groupby("bank_name")["low_rating"]
        .mean()
        .reset_index()
        .rename(columns={"low_rating": "low_share"})
    )
    low_stats["name_key"] = low_stats["bank_name"].apply(_norm_name)

    bildir_banks["name"] = bildir_banks["name"].fillna("")
    bildir_banks["overall_rating"] = _to_numeric(bildir_banks["overall_rating"])
    bildir_banks["total_reviews"] = _to_numeric(bildir_banks["total_reviews"]).fillna(0).astype(int)
    overall_stats = bildir_banks[["name", "overall_rating", "total_reviews"]].copy()
    overall_stats.rename(columns={"overall_rating": "avg_rating"}, inplace=True)
    overall_stats["name_key"] = overall_stats["name"].apply(_norm_name)

    combined = pd.merge(
        overall_stats,
        review_stats,
        on="name_key",
        how="outer",
        suffixes=("_overall", "_review"),
    )

    combined = pd.merge(combined, low_stats[["name_key", "low_share"]], on="name_key", how="left")

    combined["name"] = combined["name"].fillna(combined["bank_name"]).fillna("")
    combined["reviews_overall"] = combined["total_reviews"].fillna(0).astype(int)
    combined["reviews_review"] = combined["review_count"].fillna(0).astype(int)
    combined["reviews_total"] = combined["reviews_overall"] + combined["reviews_review"]

    combined["rating_overall"] = combined["avg_rating_overall"].fillna(pd.NA)
    combined["rating_review"] = combined["avg_rating_review"].fillna(pd.NA)

    def weighted_rating(row):
        parts = []
        if pd.notna(row["rating_overall"]) and row["reviews_overall"] > 0:
            parts.append((row["rating_overall"], row["reviews_overall"]))
        if pd.notna(row["rating_review"]) and row["reviews_review"] > 0:
            parts.append((row["rating_review"], row["reviews_review"]))
        if not parts:
            return pd.NA
        total = sum(w for _, w in parts)
        return sum(r * w for r, w in parts) / total

    combined["rating_weighted"] = combined.apply(weighted_rating, axis=1)
    combined["has_overall"] = combined["reviews_overall"] > 0
    combined["has_review"] = combined["reviews_review"] > 0

    combined = combined[combined["reviews_total"] > 0].copy()
    combined.sort_values("reviews_total", ascending=False, inplace=True)

    return combined, bank_reviews


def ensure_charts_dir():
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)


def save_chart(fig, filename):
    path = CHARTS_DIR / filename
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def chart_top_reviewed(companies: pd.DataFrame):
    top = companies.head(15)
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(top["name"][::-1], top["reviews_total"][::-1], color="#2563EB")
    ax.set_title("Top Banks by Total Review Volume")
    ax.set_xlabel("Total reviews (combined)")
    save_chart(fig, "bank_top_reviewed.png")


def chart_risk_matrix(companies: pd.DataFrame):
    df = companies.copy()
    df = df[df["low_share"].notna()]
    if df.empty:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, "No rating distribution data", ha="center", va="center")
        ax.axis("off")
        save_chart(fig, "bank_risk_matrix.png")
        return

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(df["reviews_total"], df["low_share"] * 100, alpha=0.7, color="#EF4444")
    ax.set_title("Reputation Risk Matrix")
    ax.set_xlabel("Total reviews (combined)")
    ax.set_ylabel("Low-rating share (1–2 stars, %)")
    save_chart(fig, "bank_risk_matrix.png")


def chart_competitive_ratings(companies: pd.DataFrame):
    df = companies.copy()
    df = df[df["reviews_total"] >= MIN_REVIEWS]
    df = df.dropna(subset=["rating_weighted"]).sort_values("rating_weighted", ascending=False).head(15)
    if df.empty:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, "No banks with sufficient reviews", ha="center", va="center")
        ax.axis("off")
        save_chart(fig, "bank_competitive_ratings.png")
        return

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(df["name"][::-1], df["rating_weighted"][::-1], color="#10B981")
    ax.set_title(f"Competitive Positioning (>= {MIN_REVIEWS} reviews)")
    ax.set_xlabel("Weighted average rating")
    ax.set_xlim(0, 5)
    save_chart(fig, "bank_competitive_ratings.png")


def chart_keyword_themes(bank_reviews: pd.DataFrame):
    if bank_reviews.empty:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, "No review text", ha="center", va="center")
        ax.axis("off")
        save_chart(fig, "bank_keyword_themes.png")
        return

    text = bank_reviews["review_text"].fillna("").str.lower().str.cat(sep=" ")
    tokens = re.findall(r"[a-z0-9ğüşöçıə]+", text)
    tokens = [t for t in tokens if len(t) >= 3 and t not in STOPWORDS]

    freq = pd.Series(tokens).value_counts().head(12)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(freq.index[::-1], freq.values[::-1], color="#8B5CF6")
    ax.set_title("Most Common Complaint Keywords")
    ax.set_xlabel("Mentions in reviews")
    save_chart(fig, "bank_keyword_themes.png")


def compute_business_insights(companies: pd.DataFrame, bank_reviews: pd.DataFrame):
    insights = {}

    total_banks = len(companies)
    insights["total_banks"] = total_banks

    top3 = companies.head(3)
    total_reviews = companies["reviews_total"].sum() if total_banks else 0
    insights["top3_share"] = (top3["reviews_total"].sum() / total_reviews * 100) if total_reviews else 0

    risk_df = companies[(companies["low_share"].notna()) & (companies["reviews_total"] >= MIN_REVIEWS)].copy()
    risk_df["risk_score"] = (risk_df["low_share"] * 100) * (risk_df["reviews_total"] ** 0.5)
    risk_df = risk_df.sort_values("risk_score", ascending=False)
    insights["top_risk_banks"] = list(risk_df.head(5)["name"])

    leaders = companies[(companies["reviews_total"] >= MIN_REVIEWS) & (companies["rating_weighted"].notna())]
    leaders = leaders.sort_values("rating_weighted", ascending=False).head(5)
    insights["top_rated_banks"] = list(leaders["name"])

    if bank_reviews.empty:
        insights["top_keywords"] = []
    else:
        text = bank_reviews["review_text"].fillna("").str.lower().str.cat(sep=" ")
        tokens = re.findall(r"[a-z0-9ğüşöçıə]+", text)
        tokens = [t for t in tokens if len(t) >= 3 and t not in STOPWORDS]
        insights["top_keywords"] = list(pd.Series(tokens).value_counts().head(5).index)

    return insights


def format_list(items):
    return ", ".join(items) if items else "N/A"


def write_readme(companies: pd.DataFrame, bank_reviews: pd.DataFrame, insights: dict):
    both_sources = int((companies["has_overall"] & companies["has_review"]).sum())

    top_bank_line = "Most reviewed bank: N/A"
    if not companies.empty:
        top_bank = companies.iloc[0]
        top_bank_line = f"Most reviewed bank: {top_bank['name']} ({int(top_bank['reviews_total'])} total reviews)"

    rating_range_line = "Rating range (weighted average): N/A"
    if companies["rating_weighted"].notna().any():
        max_rating = companies["rating_weighted"].max(skipna=True)
        min_rating = companies["rating_weighted"].min(skipna=True)
        rating_range_line = f"Rating range (weighted average): {min_rating:.2f} to {max_rating:.2f}"

    content = f"""# Bank Review Insights (Business-Focused)

This report aggregates bank review data at the **company level** and focuses on business value: reputation risk, customer experience, and competitive positioning.

**Overview**
- Total banks with reviews: {insights['total_banks']}
- Banks represented in multiple datasets: {both_sources}
- {top_bank_line}
- {rating_range_line}
- Review volume concentration: top 3 banks account for {insights['top3_share']:.1f}% of all bank reviews

## 1. Review Volume Concentration

![Top banks by reviews](charts/bank_top_reviewed.png)

**What this means**
- The top three banks hold {insights['top3_share']:.1f}% of all reviews, so reputation swings are driven by a small set of brands.
- Prioritizing CX improvements in these banks yields the highest impact on overall market sentiment.

## 2. Reputation Risk (Scale vs Low-Rating Share)

![Risk matrix](charts/bank_risk_matrix.png)

**What this means**
- Banks in the upper-right of the chart combine **high review volume** with **high 1–2 star share**, signaling the highest reputation risk.
- Highest-risk banks by this dataset: {format_list(insights['top_risk_banks'])}.

## 3. Competitive Positioning (Material Volume Only)

![Competitive ratings](charts/bank_competitive_ratings.png)

**What this means**
- Only banks with at least {MIN_REVIEWS} reviews are compared to avoid small-sample bias.
- Rating leaders in this group: {format_list(insights['top_rated_banks'])}.

## 4. Customer Experience Pain Points

![Keyword themes](charts/bank_keyword_themes.png)

**What this means**
- Most frequent complaint keywords indicate recurring operational issues: {format_list(insights['top_keywords'])}.
- These themes are candidates for process fixes, policy updates, or frontline training.

---

Generated by `scripts/generate_charts.py`.
"""

    README_PATH.write_text(content, encoding="utf-8")


def main():
    ensure_charts_dir()
    companies, reviews, bildir = load_data()
    banks_companies, bank_reviews, bildir_banks = filter_banks(companies, reviews, bildir)
    company_metrics, bank_reviews = build_company_metrics(banks_companies, bank_reviews, bildir_banks)

    plt.style.use("seaborn-v0_8-whitegrid")

    chart_top_reviewed(company_metrics)
    chart_risk_matrix(company_metrics)
    chart_competitive_ratings(company_metrics)
    chart_keyword_themes(bank_reviews)

    insights = compute_business_insights(company_metrics, bank_reviews)
    write_readme(company_metrics, bank_reviews, insights)


if __name__ == "__main__":
    main()
