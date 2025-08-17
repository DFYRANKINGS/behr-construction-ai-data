#!/usr/bin/env python3
import os
import pandas as pd
import json
from datetime import datetime
from typing import Dict, List, Optional

# Configuration
INPUT_CSV = "client-data.csv"
OUTPUT_DIR = "outputs"
REQUIRED_COLUMNS = [
    'client_name', 'website', 'category', 'description',
    'phone', 'hours', 'services', 'faqs', 'locations'
]

class FileGenerationError(Exception):
    """Custom exception for file generation failures"""
    pass

def validate_csv_structure(df: pd.DataFrame) -> None:
    """Validate the CSV has the expected structure"""
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise FileGenerationError(
            f"CSV missing required columns: {', '.join(missing_cols)}"
        )
    
    if len(df) == 0:
        raise FileGenerationError("CSV contains no data rows")
    
    print("✅ CSV structure validation passed")

def log_generation_step(step_name: str):
    """Decorator to log step execution"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            print(f"\n🔹 Starting {step_name} generation...")
            try:
                result = func(*args, **kwargs)
                print(f"✅ {step_name} generated successfully")
                return result
            except Exception as e:
                print(f"❌ Failed to generate {step_name}: {str(e)}")
                raise
        return wrapper
    return decorator

@log_generation_step("FAQ schema")
def generate_faq_schema(df: pd.DataFrame) -> Dict:
    """Generate FAQ schema.json from CSV data"""
    faqs = []
    
    for _, row in df.iterrows():
        if pd.notna(row['faqs']):
            for qna in str(row['faqs']).split('|'):
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
    
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": faqs
    }

@log_generation_step("Company schema")
def generate_company_schema(df: pd.DataFrame) -> Dict:
    """Generate company schema.json from CSV data"""
    if len(df) > 1:
        raise FileGenerationError("Expected single row for company data")
    
    row = df.iloc[0]
    return {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": row['client_name'],
        "url": row['website'],
        "description": row['description'],
        "telephone": row['phone'],
        "openingHours": row['hours'],
        "department": {
            "@type": "Organization",
            "name": row['client_name']
        }
    }

@log_generation_step("QnA training")
def generate_qna_training(df: pd.DataFrame) -> List[Dict]:
    """Generate QnA training data for LLMs"""
    qna_pairs = []
    
    for _, row in df.iterrows():
        if pd.notna(row['faqs']):
            for qna in str(row['faqs']).split('|'):
                if ':' in qna:
                    question, answer = qna.split(':', 1)
                    qna_pairs.append({
                        "question": question.strip(),
                        "answer": answer.strip(),
                        "metadata": {
                            "source": row['client_name'],
                            "category": row['category']
                        }
                    })
    
    return qna_pairs

def save_to_file(data, filename: str) -> None:
    """Save data to JSON file with error handling"""
    output_path = os.path.join(OUTPUT_DIR, filename)
    try:
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Saved: {output_path}")
    except IOError as e:
        raise FileGenerationError(f"Failed to save {filename}: {str(e)}")

def main():
    print(f"🚀 Starting file generation at {datetime.now()}")
    
    try:
        # 1. Setup and validation
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        df = pd.read_csv(INPUT_CSV)
        validate_csv_structure(df)
        
        # 2. Generate all files
        save_to_file(generate_faq_schema(df), "faq-schema.json")
        save_to_file(generate_company_schema(df), "company-schema.json")
        save_to_file(generate_qna_training(df), "qna-training.json")
        
        # Add additional generators here...
        
        print("\n🎉 All files generated successfully!")
        return True
        
    except FileGenerationError as e:
        print(f"\n❌ Critical error: {str(e)}")
        return False
    except Exception as e:
        print(f"\n⚠️ Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
