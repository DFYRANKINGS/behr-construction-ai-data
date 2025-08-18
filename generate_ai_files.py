#!/usr/bin/env python3
import os
import pandas as pd
import json
from datetime import datetime
import xml.etree.ElementTree as ET

# CONFIGURATION (matches your template)
CLIENT_DIR = "behr-construction"  # Change to client folder name
SCHEMA_DIR = os.path.join(CLIENT_DIR, "schemas")
TRAINING_DIR = os.path.join(CLIENT_DIR, "training")
SITEMAP_DIR = os.path.join(CLIENT_DIR, "sitemaps")
INPUT_CSV = os.path.join(CLIENT_DIR, "client-data.csv")  # Path adjusted

def validate_data(df):
    required = ['client_name', 'website', 'services', 'faqs', 'locations']
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in CSV: {missing}")

def generate_faq_schema(df):
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [{
            "@type": "Question",
            "name": f"About {df['client_name'].iloc[0]}'s {service}",
            "acceptedAnswer": {"@type": "Answer", "text": answer}
        } for service, answer in zip(df['services'].str.split('|'), df['faqs'].str.split('|'))]
    }

def generate_llm_training(df):
    return {
        "training_data": [{
            "input": f"What locations does {df['client_name'].iloc[0]} serve?",
            "output": df['locations'].iloc[0]
        }]
    }

def main():
    print("🚀 Generating files for client...")
    try:
        # 1. Load data
        df = pd.read_csv(INPUT_CSV)
        validate_data(df)
        
        # 2. Create directories (if missing)
        os.makedirs(SCHEMA_DIR, exist_ok=True)
        os.makedirs(TRAINING_DIR, exist_ok=True)
        os.makedirs(SITEMAP_DIR, exist_ok=True)
        
        # 3. Generate files
        with open(f"{SCHEMA_DIR}/faq-schema.json", 'w') as f:
            json.dump(generate_faq_schema(df), f, indent=2)
        
        with open(f"{TRAINING_DIR}/llm-training.json", 'w') as f:
            json.dump(generate_llm_training(df), f, indent=2)
        
        print(f"✅ Success! Files generated in /{CLIENT_DIR}")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

if __name__ == "__main__":
    exit(0 if main() else 1)
