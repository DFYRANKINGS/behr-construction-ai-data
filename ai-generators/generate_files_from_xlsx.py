#!/usr/bin/env python3
"""
generate_files_from_xlsx_UNIVERSAL.py

Goal:
- One generator that works for BOTH your legacy client-data.xlsx and the new AI-Visibility-Master-Template.xlsx.
- No more -1 / -2 duplicates on reruns (when using --clean OR when overwriting).
- Safe for GitHub Actions (no local commands needed).

Key behaviors:
- Sheet aliases: maps many sheet names -> canonical buckets (organization, services, team, press, awards, etc.)
- Deterministic filenames:
    - organization always writes schemas/organization/organization.json (overwrite)
    - everything else writes schemas/<bucket>/<slug>.json (overwrite)
    - help articles write schemas/help-articles/<slug>.md (overwrite)
- Optional: --clean deletes generated schema folders first (recommended for fixing existing -1 files)
"""

import os
import sys
import re
import json
import shutil
import argparse
from typing import Any, Dict, List, Optional

import pandas as pd


# -----------------------------
# Helpers
# -----------------------------
def slugify(text: Any) -> str:
    if text is None:
        return "untitled"
    text = str(text).strip()
    if not text:
        return "untitled"
    text = re.sub(r"[^a-zA-Z0-9\s-]", "", text)
    text = re.sub(r"[\s]+", "-", text.strip().lower())
    return text or "untitled"

def _is_blank(v: Any) -> bool:
    return v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == ""

def _as_str(v: Any) -> str:
    if _is_blank(v):
        return ""
    return str(v).strip()

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [str(c).strip() for c in df.columns]
    return df

def get_first(row, keys: List[str], default: Any = "") -> Any:
    for k in keys:
        if k in row and not _is_blank(row[k]):
            return row[k]
    return default

def write_json(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

def write_md(path: str, title: str, slug: str, body: str, extra_frontmatter: Optional[Dict[str, Any]] = None) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    extra_frontmatter = extra_frontmatter or {}
    with open(path, "w", encoding="utf-8") as f:
        f.write("---\n")
        if title:
            f.write(f"title: {title}\n")
        f.write(f"slug: {slug}\n")
        for k, v in extra_frontmatter.items():
            if v is None or v == "":
                continue
            f.write(f"{k}: {v}\n")
        f.write("---\n\n")
        f.write(body or "")

def norm_sheet(name: str) -> str:
    # collapse whitespace and normalize
    return re.sub(r"\s+", " ", str(name).strip().lower())


# -----------------------------
# Canonical outputs
# -----------------------------
CANONICAL_OUTPUT = {
    "organization": "schemas/organization",
    "services": "schemas/services",
    "products": "schemas/products",
    "faqs": "schemas/faqs",
    "help_articles": "schemas/help-articles",
    "reviews": "schemas/reviews",
    "locations": "schemas/locations",
    "team": "schemas/team",
    "awards": "schemas/awards",
    "press": "schemas/press",
    "case_studies": "schemas/case-studies",
}

# -----------------------------
# Sheet aliases (legacy + new + legal)
# Add new sheet names here as needed.
# -----------------------------
SHEET_ALIASES = {
    "organization": [
        # NEW
        "Business Info", "Business information", "Organization", "Company", "Firm Info",
        # LEGACY
        "entity_info", "core_info", "Core Info", "Entity Info",
    ],
    "services": [
        # NEW / LEGAL / MEDICAL
        "Services", "Practice Areas", "Practice areas", "Service Areas", "Medical Specialties",
        # LEGACY variations
        "service", "services",
    ],
    "products": ["Products", "Product"],
    "faqs": ["FAQs", "FAQ", "Faqs", "Faq"],
    "help_articles": ["Help Articles", "Help articles", "Articles", "Guides", "Blog", "Help"],
    "reviews": ["Reviews", "Testimonials", "Review", "Testimonial"],
    "locations": ["Locations", "Offices", "Location", "Office"],
    "team": ["Team", "Lawyers", "Attorneys", "Providers", "Staff", "Legal Team"],
    "awards": [
        "Awards & Certifications", "Awards", "Certifications", "Accreditations", "Licenses",
        "Awards, Certifications, Accreditations",
    ],
    "press": [
        "Press/News Mentions", "Media Mentions", "Press", "News", "Media",
        # LEGACY sheet name you showed:
        "PressNews Mentions",
    ],
    "case_studies": ["Case Studies", "Case studies", "Matters", "Results"],
}


def build_alias_lookup() -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    for canon, aliases in SHEET_ALIASES.items():
        for a in aliases:
            lookup[norm_sheet(a)] = canon
    return lookup


def clean_generated_folders() -> None:
    print("🧹 --clean enabled: deleting generated schema folders before regeneration")
    for d in CANONICAL_OUTPUT.values():
        if os.path.isdir(d):
            shutil.rmtree(d)
            print(f"🗑️ Deleted folder: {d}")
        os.makedirs(d, exist_ok=True)


def dataframe_rows(df: pd.DataFrame):
    # yields (idx, row_series) for non-empty rows
    for idx, row in df.iterrows():
        if row.dropna().empty:
            continue
        yield idx, row


# -----------------------------
# Main
# -----------------------------
def main(input_file: str, clean: bool) -> None:
    print(f"📂 Opening Excel file: {input_file}")

    if not os.path.exists(input_file):
        print(f"❌ FATAL: Excel file not found at {input_file}")
        sys.exit(1)

    if clean:
        clean_generated_folders()

    try:
        xlsx = pd.ExcelFile(input_file)
        print(f"📄 Available sheets in workbook: {xlsx.sheet_names}")
    except Exception as e:
        print(f"❌ Failed to load Excel file: {e}")
        sys.exit(1)

    alias_lookup = build_alias_lookup()

    processed_any = False

    for actual_sheet in xlsx.sheet_names:
        canon = alias_lookup.get(norm_sheet(actual_sheet))
        if not canon:
            print(f"⚠️ Skipping unsupported sheet: {actual_sheet}")
            continue

        output_dir = CANONICAL_OUTPUT[canon]
        os.makedirs(output_dir, exist_ok=True)

        print(f"\n📄 Processing sheet: {actual_sheet}  →  {canon}  →  {output_dir}")

        df = xlsx.parse(actual_sheet)
        df = normalize_columns(df)

        if df.empty:
            print(f"⚠️ Sheet '{actual_sheet}' is empty — skipping")
            continue

        processed_count = 0

        # ----------------------------
        # ORGANIZATION (usually 1 row)
        # Always overwrite organization.json (never -1).
        # ----------------------------
        if canon == "organization":
            row_obj = None
            for _, r in df.iterrows():
                if not r.dropna().empty:
                    row_obj = r
                    break

            if row_obj is None:
                print("⚠️ No usable rows in organization sheet — skipping")
                continue

            row = row_obj
            business_name = _as_str(get_first(row, ["business_name", "entity_name", "name", "company_name", "firm_name"]))
            main_website_url = _as_str(get_first(row, ["main_website_url", "website", "url"]))
            logo_url = _as_str(get_first(row, ["logo_url", "logo", "logoUrl"]))
            short_description = _as_str(get_first(row, ["short_description", "description", "tagline"]))
            long_description = _as_str(get_first(row, ["long_description", "about", "about_text"]))

            same_as: List[str] = []
            for k in [
                "facebook_url", "instagram_url", "linkedin_url", "twitter_url", "x_url",
                "youtube_url", "tiktok_url", "pinterest_url", "yelp_url", "bbb_url",
                "avvo_url", "martindale_url", "other_profiles"
            ]:
                v = get_first(row, [k])
                if _is_blank(v):
                    continue
                vv = str(v).strip()
                if k == "other_profiles" and "," in vv:
                    for part in [p.strip() for p in vv.split(",") if p.strip()]:
                        same_as.append(part)
                else:
                    same_as.append(vv)

            org: Dict[str, Any] = {}
            for col in df.columns:
                v = row.get(col)
                if _is_blank(v):
                    continue
                if hasattr(v, "item"):
                    v = v.item()
                org[col] = v

            if business_name:
                org["entity_name"] = business_name
            if main_website_url:
                org["website"] = main_website_url
                org["url"] = main_website_url
            if logo_url:
                org["logo_url"] = logo_url
            if short_description and "description" not in org:
                org["description"] = short_description
            if long_description:
                org["about"] = long_description
            if same_as:
                org["sameAs"] = same_as

            path = os.path.join(output_dir, "organization.json")
            write_json(path, org)
            print(f"✅ Generated (overwrite): {path}")
            processed_any = True
            processed_count += 1
            print(f"📊 Total processed in '{actual_sheet}': {processed_count} items")
            continue

        # ----------------------------
        # HELP ARTICLES → Markdown (overwrite)
        # ----------------------------
        if canon == "help_articles":
            for idx, row in dataframe_rows(df):
                title = _as_str(get_first(row, ["title", "article_title", "name", "headline"]))
                slug = _as_str(get_first(row, ["slug", "article_slug"]))
                content = _as_str(get_first(row, ["article_content", "article", "content", "body", "markdown"]))

                if not slug:
                    slug = slugify(title) if title else f"article-{idx+1}"

                path = os.path.join(output_dir, f"{slugify(slug)}.md")  # overwrite
                write_md(
                    path=path,
                    title=title,
                    slug=slugify(slug),
                    body=content,
                    extra_frontmatter={"date": _as_str(get_first(row, ["date", "published_date", "publish_date"]))},
                )
                print(f"✅ Generated (overwrite): {path}")
                processed_count += 1
                processed_any = True

            print(f"📊 Total processed in '{actual_sheet}': {processed_count} items")
            continue

        # ----------------------------
        # FAQs → JSON (overwrite)
        # ----------------------------
        if canon == "faqs":
            for idx, row in dataframe_rows(df):
                question = _as_str(get_first(row, ["question", "q", "faq_question", "title"]))
                answer = _as_str(get_first(row, ["answer", "a", "faq_answer", "response", "content"]))
                slug = _as_str(get_first(row, ["slug", "faq_id", "id"]))

                if not question:
                    question = f"Untitled FAQ {idx+1}"
                if not slug:
                    slug = slugify(question)

                path = os.path.join(output_dir, f"{slugify(slug)}.json")  # overwrite
                write_json(path, {"question": question, "answer": answer})
                print(f"✅ Generated (overwrite): {path}")
                processed_count += 1
                processed_any = True

            print(f"📊 Total processed in '{actual_sheet}': {processed_count} items")
            continue

        # ----------------------------
        # SERVICES → JSON (overwrite)
        # ----------------------------
        if canon == "services":
            for idx, row in dataframe_rows(df):
                service_name = _as_str(get_first(row, ["service_name", "practice_area", "practice_area_name", "name", "title"]))
                slug = _as_str(get_first(row, ["slug", "service_id", "id"]))
                description = _as_str(get_first(row, ["description", "service_description", "summary"]))
                price_range = _as_str(get_first(row, ["price_range", "priceRange"]))

                if not service_name:
                    service_name = f"Service {idx+1}"
                if not slug:
                    slug = slugify(service_name)

                data: Dict[str, Any] = {"name": service_name, "description": description}
                if price_range:
                    data["priceRange"] = price_range

                # carry through any extra cols
                for col in df.columns:
                    if col in data:
                        continue
                    v = row.get(col)
                    if _is_blank(v):
                        continue
                    if hasattr(v, "item"):
                        v = v.item()
                    data[col] = v

                path = os.path.join(output_dir, f"{slugify(slug)}.json")  # overwrite
                write_json(path, data)
                print(f"✅ Generated (overwrite): {path}")
                processed_count += 1
                processed_any = True

            print(f"📊 Total processed in '{actual_sheet}': {processed_count} items")
            continue

        # ----------------------------
        # TEAM → JSON (overwrite)
        # ----------------------------
        if canon == "team":
            for idx, row in dataframe_rows(df):
                member_name = _as_str(get_first(row, ["member_name", "lawyer_name", "attorney_name", "name", "full_name"]))
                if not member_name:
                    fn = _as_str(get_first(row, ["first_name", "firstname"]))
                    ln = _as_str(get_first(row, ["last_name", "lastname"]))
                    member_name = " ".join([p for p in [fn, ln] if p]).strip()

                slug = _as_str(get_first(row, ["slug", "member_id", "lawyer_id", "id"]))
                role = _as_str(get_first(row, ["role", "title", "position"]))
                bio = _as_str(get_first(row, ["bio", "description", "about", "summary"]))

                if not member_name:
                    member_name = f"Member {idx+1}"
                if not slug:
                    slug = slugify(member_name)

                data: Dict[str, Any] = {"name": member_name, "role": role, "description": bio}
                for col in df.columns:
                    if col in data:
                        continue
                    v = row.get(col)
                    if _is_blank(v):
                        continue
                    if hasattr(v, "item"):
                        v = v.item()
                    data[col] = v

                path = os.path.join(output_dir, f"{slugify(slug)}.json")  # overwrite
                write_json(path, data)
                print(f"✅ Generated (overwrite): {path}")
                processed_count += 1
                processed_any = True

            print(f"📊 Total processed in '{actual_sheet}': {processed_count} items")
            continue

        # ----------------------------
        # REVIEWS → JSON (overwrite; normalize review -> review_body)
        # ----------------------------
        if canon == "reviews":
            for idx, row in dataframe_rows(df):
                title = _as_str(get_first(row, ["review_title", "title", "headline"]))
                body = _as_str(get_first(row, ["review_body", "review", "quote", "testimonial", "content"]))
                slug = _as_str(get_first(row, ["slug", "review_id", "id"]))
                rating = get_first(row, ["rating", "stars"])
                date = _as_str(get_first(row, ["date", "review_date"]))

                if not slug:
                    slug = slugify(title) if title else f"review-{idx+1}"

                data: Dict[str, Any] = {}
                for col in df.columns:
                    v = row.get(col)
                    if _is_blank(v):
                        continue
                    if hasattr(v, "item"):
                        v = v.item()
                    data[col] = v

                if title:
                    data["review_title"] = title
                if body:
                    data["review_body"] = body
                    data.setdefault("quote", body)
                if not _is_blank(rating):
                    data["rating"] = rating
                if date:
                    data["date"] = date

                path = os.path.join(output_dir, f"{slugify(slug)}.json")  # overwrite
                write_json(path, data)
                print(f"✅ Generated (overwrite): {path}")
                processed_count += 1
                processed_any = True

            print(f"📊 Total processed in '{actual_sheet}': {processed_count} items")
            continue

        # ----------------------------
        # LOCATIONS → JSON (overwrite; normalize postal/hours)
        # ----------------------------
        if canon == "locations":
            for idx, row in dataframe_rows(df):
                name = _as_str(get_first(row, ["location_name", "name", "office_name", "title"]))
                slug = _as_str(get_first(row, ["slug", "location_id", "id"]))
                if not slug:
                    slug = slugify(name) if name else f"location-{idx+1}"

                data: Dict[str, Any] = {}
                for col in df.columns:
                    v = row.get(col)
                    if _is_blank(v):
                        continue
                    if hasattr(v, "item"):
                        v = v.item()
                    data[col] = v

                address_postal = _as_str(get_first(row, ["address_postal", "postal", "zip", "postal_code", "address_postal_code"]))
                open_hours = _as_str(get_first(row, ["open_hours", "hours", "opening_hours"]))

                if address_postal:
                    data["address_postal_code"] = address_postal
                if open_hours:
                    data["hours"] = open_hours
                if name:
                    data.setdefault("location_name", name)

                path = os.path.join(output_dir, f"{slugify(slug)}.json")  # overwrite
                write_json(path, data)
                print(f"✅ Generated (overwrite): {path}")
                processed_count += 1
                processed_any = True

            print(f"📊 Total processed in '{actual_sheet}': {processed_count} items")
            continue

        # ----------------------------
        # GENERIC handler (press, awards, case studies, products, etc.) → JSON (overwrite)
        # ----------------------------
        for idx, row in dataframe_rows(df):
            id_field = _as_str(get_first(row, [
                "slug", "id",
                "service_id", "product_id", "faq_id", "review_id", "location_id",
                "case_id", "press_id",
                "name", "title", "headline"
            ]))
            if not id_field:
                id_field = f"item-{idx+1}"

            data: Dict[str, Any] = {}
            for col in df.columns:
                v = row.get(col)
                if _is_blank(v):
                    continue
                if hasattr(v, "item"):
                    v = v.item()
                data[col] = v

            if canon == "press":
                t = _as_str(get_first(row, ["title", "mention_title", "headline"]))
                if t:
                    data.setdefault("title", t)

            path = os.path.join(output_dir, f"{slugify(id_field)}.json")  # overwrite
            write_json(path, data)
            print(f"✅ Generated (overwrite): {path}")
            processed_count += 1
            processed_any = True

        print(f"📊 Total processed in '{actual_sheet}': {processed_count} items")

    if not processed_any:
        print("\n⚠️ No supported sheets were processed. Check sheet names vs aliases.")
        print("Supported sheet aliases include:", sorted({a for v in SHEET_ALIASES.values() for a in v}))
        sys.exit(2)

    print("\n🎉 All files generated successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate schema files from Excel (universal, no duplicates).")
    parser.add_argument("--input", type=str, default="templates/AI-Visibility-Master-Template.xlsx",
                        help="Path to input Excel file")
    parser.add_argument("--clean", action="store_true",
                        help="Delete generated schemas/* folders before regenerating (recommended to remove existing -1 files).")
    args = parser.parse_args()
    main(args.input, args.clean)
