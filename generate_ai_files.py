#!/usr/bin/env python3
import os
import pandas as pd
import json

# PATHS THAT MATCH YOUR STRUCTURE *EXACTLY*
INPUT_CSV = "main/client-data.csv"
SCHEMA_DIR = "schemas/faqs"
TRAINING_DIR = "llm-training"

def generate_files():
    print("⚡ Generating files...")
    try:
        # 1. Load data (will fail visibly if CSV is missing)
        df = pd.read_csv(INPUT_CSV)
        
        # 2. Create folders if they don't exist
        os.makedirs(SCHEMA_DIR, exist_ok=True)
        os.makedirs(TRAINING_DIR, exist_ok=True)
        
        # 3. Generate FAQ file
        with open(f"{SCHEMA_DIR}/faqs.json", 'w') as f:
            json.dump({
                "client": df.iloc[0]['client_name'],
                "services": df['services'].tolist(),
                "faqs": df['faqs'].tolist()
            }, f, indent=2)
        
        # 4. Generate LLM file
        with open(f"{TRAINING_DIR}/llm.txt", 'w') as f:
            f.write(f"CLIENT: {df.iloc[0]['client_name']}\n")
            f.write(f"LOCATIONS: {df.iloc[0]['locations']}\n")
        
        print(f"✅ Success! Check these folders:\n- {SCHEMA_DIR}\n- {TRAINING_DIR}")
        return True
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

if __name__ == "__main__":
    generate_files()
