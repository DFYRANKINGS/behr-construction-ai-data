#!/usr/bin/env python3
import os
import pandas as pd
import json

# PATHS THAT MATCH YOUR STRUCTURE
INPUT_CSV = "main/client-data.csv"  # Your CSV location
SCHEMA_DIR = "schemas/faqs"        # Your FAQ folder
TRAINING_DIR = "llm-training"      # Your LLM folder

def generate_files():
    print("⚡ Generating files...")
    
    # 1. Load data
    df = pd.read_csv(INPUT_CSV)
    client_name = df.iloc[0]['client_name']
    
    # 2. Create FAQ schema
    os.makedirs(SCHEMA_DIR, exist_ok=True)
    with open(f"{SCHEMA_DIR}/faqs.json", 'w') as f:
        json.dump({
            "client": client_name,
            "faqs": df['faqs'].tolist() 
        }, f, indent=2)
    
    # 3. Create LLM training
    os.makedirs(TRAINING_DIR, exist_ok=True)
    with open(f"{TRAINING_DIR}/llm.txt", 'w') as f:
        f.write(f"Client: {client_name}\nServices: {df.iloc[0]['services']}")
    
    print(f"✅ Generated files in:\n- {SCHEMA_DIR}\n- {TRAINING_DIR}")

if __name__ == "__main__":
    generate_files()
