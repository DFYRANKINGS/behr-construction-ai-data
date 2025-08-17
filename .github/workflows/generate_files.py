#!/usr/bin/env python3
import os
import pandas as pd
from datetime import datetime
import json

# Configuration
INPUT_CSV = "client-data.csv"
OUTPUT_DIR = "outputs"

def main():
    print(f"Starting file generation at {datetime.now()}")
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    try:
        # 1. Load and validate CSV
        df = pd.read_csv(INPUT_CSV)
        print("CSV loaded successfully")
        print(df.head())
        
        # 2. Generate FAQ Schema
        generate_faq_schema(df)
        
        # 3. Generate Company Schema
        generate_company_schema(df)
        
        # 4. Generate other files
        # ... add your other generation functions
        
        print("All files generated successfully")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise  # This will fail the GitHub Action

def generate_faq_schema(df):
    """Generate FAQ schema.json from CSV data"""
    faqs = []
    
    # Extract FAQ data (adjust based on your CSV structure)
    if 'faqs' in df.columns:
        for entry in df['faqs']:
            if pd.notna(entry):
                for qna in entry.split('|'):
                    if ':' in qna:
                        question, answer = qna.split(':', 1)
                        faqs.append({
                            "@type": "Question",
                            "name": question.strip(),
                            "acceptedAnswer": {
                                "@type": "Answer",
                                "text": answer.strip()
                            }
                        })
    
    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": faqs
    }
    
    output_path = os.path.join(OUTPUT_DIR, "faq-schema.json")
    with open(output_path, 'w') as f:
        json.dump(schema, f, indent=2)
    print(f"Generated FAQ schema at {output_path}")

def generate_company_schema(df):
    """Generate company schema.json from CSV data"""
    # Implement based on your CSV structure
    pass

if __name__ == "__main__":
    main()
