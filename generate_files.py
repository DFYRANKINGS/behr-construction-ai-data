import pandas as pd
import json
import os

def main():
    # Read client data
    try:
        df = pd.read_csv('client-data.csv')
    except FileNotFoundError:
        print("❌ Error: client-data.csv not found")
        return

    # Generate services.json
    services = [s for s in df['services'].iloc[0].split('|') if s]
    os.makedirs('schemas', exist_ok=True)
    with open('schemas/services.json', 'w') as f:
        json.dump(services, f, indent=2)
    
    print("✅ Generated schemas/services.json")

if __name__ == "__main__":
    main()