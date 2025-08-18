#!/usr/bin/env python3
import os
import pandas as pd
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
import requests
from time import sleep

# ========== CORE CONFIGURATION ==========
INPUT_CSV = "client-data.csv"
OUTPUT_DIR = "outputs"
SITEMAP_DIR = os.path.join(OUTPUT_DIR, "ai-sitemaps")
REQUIRED_COLUMNS = [
    'client_name', 'website', 'category', 'description',
    'phone', 'hours', 'services', 'faqs', 'locations'
]

# ========== UTILITIES ==========
def log_generation_step(step_name: str):
    """Track execution with timing"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            print(f"\n⏳ [START] {step_name}")
            start = datetime.now()
            try:
                result = func(*args, **kwargs)
                duration = (datetime.now() - start).total_seconds()
                print(f"✅ [COMPLETE] {step_name} ({duration:.2f}s)")
                return result
            except Exception as e:
                print(f"❌ [FAILED] {step_name}: {str(e)}")
                raise
        return wrapper
    return decorator

class FileGenerationError(Exception):
    """Custom exception for failures"""
    pass

# ========== CORE FUNCTIONALITY ==========
@log_generation_step("Validate CSV")
def validate_csv_structure(df: pd.DataFrame) -> bool:
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise FileGenerationError(f"Missing columns: {missing}")
    return True

@log_generation_step("Validate URL")
def validate_url(url: str) -> str:
    if not url.startswith(('http://', 'https://')):
        url = f'https://{url}'
    if not urlparse(url).netloc:
        raise FileGenerationError(f"Invalid URL: {url}")
    return url.rstrip('/')

@log_generation_step("Save File")
def save_to_file(data: dict, filename: str) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"📄 Saved {os.path.basename(path)} ({os.path.getsize(path)} bytes)")
    return path

# ========== GENERATORS ==========
@log_generation_step("FAQ Schema")
def generate_faq_schema(df: pd.DataFrame) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [{
            "@type": "Question",
            "name": q,
            "acceptedAnswer": {
                "@type": "Answer",
                "text": a
            }
        } for q, a in zip(df['faqs_questions'], df['faqs_answers'])]
    }

@log_generation_step("Company Schema")
def generate_company_schema(df: pd.DataFrame) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": df['category'].iloc[0],
        "name": df['client_name'].iloc[0],
        "description": df['description'].iloc[0],
        "openingHours": df['hours'].iloc[0],
        "telephone": df['phone'].iloc[0]
    }

@log_generation_step("QnA Training")
def generate_qna_training(df: pd.DataFrame) -> dict:
    return {
        "training_data": [{
            "input": f"What services does {row['client_name']} offer?",
            "output": row['services']
        } for _, row in df.iterrows()]
    }

# ========== MAIN EXECUTION ==========
def main():
    print(f"🚀 Starting generation at {datetime.now()}")
    print("="*60)
    
    try:
        # 1. Setup environment
        print(f"📂 Working in: {os.getcwd()}")
        print(f"🔍 Input CSV: {os.path.abspath(INPUT_CSV)}")
        
        # 2. Load and validate
        df = pd.read_csv(INPUT_CSV)
        base_url = validate_url(df.iloc[0]['website'])
        validate_csv_structure(df)
        
        # 3. Generate files
        save_to_file(generate_faq_schema(df), "faq-schema.json")
        save_to_file(generate_company_schema(df), "company-schema.json")
        save_to_file(generate_qna_training(df), "qna-training.json")
        
        print("\n" + "="*60)
        print("🎉 All files generated in outputs/ directory")
        return True
        
    except Exception as e:
        print(f"\n❌ Critical failure: {str(e)}")
        return False

if __name__ == "__main__":
    exit(0 if main() else 1)
