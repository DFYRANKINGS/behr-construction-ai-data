#!/usr/bin/env python3
import os
import pandas as pd
import json
from pathlib import Path

# PATHS MATCHING YOUR STRUCTURE
BASE_DIR = Path(__file__).parent.parent
SCHEMA_DIR = BASE_DIR / "schemas"
TRAINING_DIR = BASE_DIR / "llm-training"
CSV_PATH = BASE_DIR / "main" / "client-data.csv"

def generate_files():
    print("🚀 Generating files for client...")
    
    try:
        # 1. Load data
        df = pd.read_csv(CSV_PATH)
        
        # 2. Create FAQ Schema (goes to schemas/faqs/)
        faq_path = SCHEMA_DIR / "faqs" / "faqs.json"
        faq_path.parent.mkdir(exist_ok=True)
        with open(faq_path, 'w') as f:
            json.dump({
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f"About {row['client_name']}'s services",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": row['services']
                        }
                    } for _, row in df.iterrows()
                ]
            }, f, indent=2)

        # 3. Create LLM Training (goes to llm-training/)
        training_path = TRAINING_DIR / "llm.txt"
        training_path.parent.mkdir(exist_ok=True)
        with open(training_path, 'w') as f:
            f.write(f"Client: {df.iloc[0]['client_name']}\n")
            f.write(f"Services: {df.iloc[0]['services']}\n")

        print(f"✅ Generated:\n- {faq_path}\n- {training_path}")
        return True

    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

if __name__ == "__main__":
    exit(0 if generate_files() else 1)
