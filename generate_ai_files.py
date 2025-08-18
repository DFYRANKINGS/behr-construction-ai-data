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

# ===== ADDED MISSING DECORATOR =====
def log_generation_step(step_name: str):
    """Decorator to log and track execution of generation steps"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            print(f"\n⏳ [STEP START] {step_name}")
            try:
                start_time = datetime.now()
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                print(f"✅ [STEP COMPLETE] {step_name} (took {duration:.2f}s)")
                return result
            except Exception as e:
                print(f"❌ [STEP FAILED] {step_name}: {str(e)}")
                raise
        return wrapper
    return decorator
# ===== END OF ADDED CODE =====

# Configuration
INPUT_CSV = "client-data.csv"
OUTPUT_DIR = "outputs"
SITEMAP_DIR = os.path.join(OUTPUT_DIR, "ai-sitemaps")
REQUIRED_COLUMNS = [
    'client_name', 'website', 'category', 'description',
    'phone', 'hours', 'services', 'faqs', 'locations'
]

# Search Engine Ping URLs
SEARCH_ENGINE_PING_URLS = {
    'google': 'https://www.google.com/ping?sitemap={sitemap_url}',
    'bing': 'https://www.bing.com/ping?sitemap={sitemap_url}',
    'yandex': 'https://webmaster.yandex.com/ping?sitemap={sitemap_url}',
    'ai_search': 'https://api.aisearch.com/v1/ping?sitemap={sitemap_url}'  # Example AI search
}

class FileGenerationError(Exception):
    """Custom exception for file generation failures"""
    pass

def validate_ai_endpoint(url: str) -> Tuple[bool, str]:
    """Validate if an AI endpoint actually exists and is accessible"""
    try:
        # First check if URL exists
        parsed = urlparse(url)
        if not all([parsed.scheme, parsed.netloc]):
            return False, "Invalid URL format"
        
        # Special validation for AI endpoints
        if '/ai/' in url:
            # Try HEAD request first
            try:
                response = requests.head(url, timeout=5, allow_redirects=True)
                if response.status_code == 200:
                    return True, "Endpoint accessible"
                
                # Try GET if HEAD not allowed
                response = requests.get(url, timeout=5, allow_redirects=True)
                if response.status_code == 200:
                    return True, "Endpoint accessible"
                
                return False, f"Endpoint returned {response.status_code}"
            except requests.exceptions.RequestException as e:
                return False, f"Connection failed: {str(e)}"
        
        return True, "URL valid"
    except Exception as e:
        return False, f"Validation error: {str(e)}"

def ping_search_engines(sitemap_url: str) -> None:
    """Ping all search engines about sitemap updates"""
    print(f"\n🔔 Pinging search engines about {sitemap_url}")
    
    for engine, ping_url in SEARCH_ENGINE_PING_URLS.items():
        try:
            url = ping_url.format(sitemap_url=sitemap_url)
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ Successfully pinged {engine}")
            else:
                print(f"⚠️ {engine} ping returned {response.status_code}")
            
            # Be polite to search engines
            sleep(1)
            
        except Exception as e:
            print(f"❌ Failed to ping {engine}: {str(e)}")

def update_or_create_sitemap(sitemap_path: str, urls: List[Dict]) -> bool:
    """Update existing sitemap or create new one with validation"""
    try:
        # Check if sitemap exists
        if os.path.exists(sitemap_path):
            # Parse existing sitemap
            tree = ET.parse(sitemap_path)
            root = tree.getroot()
            
            # Update existing URLs or add new ones
            existing_urls = {url.find('loc').text for url in root.findall('url')}
            updated = False
            
            for new_url in urls:
                if new_url['loc'] not in existing_urls:
                    url_elem = ET.SubElement(root, "url")
                    ET.SubElement(url_elem, "loc").text = new_url['loc']
                    ET.SubElement(url_elem, "lastmod").text = new_url.get('lastmod', datetime.now().isoformat())
                    ET.SubElement(url_elem, "changefreq").text = new_url.get('changefreq', 'weekly')
                    ET.SubElement(url_elem, "priority").text = new_url.get('priority', '0.7')
                    updated = True
                    print(f"Added new URL: {new_url['loc']}")
            
            if updated:
                tree.write(sitemap_path, encoding='utf-8', xml_declaration=True)
                print(f"Updated existing sitemap: {sitemap_path}")
                return True
            else:
                print(f"No updates needed for: {sitemap_path}")
                return False
                
        else:
            # Create new sitemap
            root = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
            for url in urls:
                url_elem = ET.SubElement(root, "url")
                ET.SubElement(url_elem, "loc").text = url['loc']
                ET.SubElement(url_elem, "lastmod").text = url.get('lastmod', datetime.now().isoformat())
                ET.SubElement(url_elem, "changefreq").text = url.get('changefreq', 'weekly')
                ET.SubElement(url_elem, "priority").text = url.get('priority', '0.7')
            
            tree = ET.ElementTree(root)
            tree.write(sitemap_path, encoding='utf-8', xml_declaration=True)
            print(f"Created new sitemap: {sitemap_path}")
            return True
            
    except Exception as e:
        raise FileGenerationError(f"Sitemap update failed: {str(e)}")

@log_generation_step("AI Sitemaps")
def generate_ai_sitemaps(df: pd.DataFrame, base_url: str) -> None:
    """Generate and update AI sitemaps with validation"""
    os.makedirs(SITEMAP_DIR, exist_ok=True)
    timestamp = datetime.now().isoformat()
    sitemap_updates = False
    
    # 1. Main AI Sitemap
    main_sitemap_path = os.path.join(SITEMAP_DIR, "ai-sitemap.xml")
    main_urls = [
        {
            'loc': f"{base_url}/ai-knowledge-base",
            'lastmod': timestamp,
            'changefreq': 'weekly',
            'priority': '0.8'
        },
        {
            'loc': f"{base_url}/ai-qna-endpoint",
            'lastmod': timestamp,
            'changefreq': 'daily'
        }
    ]
    
    if update_or_create_sitemap(main_sitemap_path, main_urls):
        sitemap_updates = True
    
    # 2. Specialized AI Sitemaps
    specialized_sitemaps = {
        "knowledge": {
            "urls": [
                f"{base_url}/ai/models",
                f"{base_url}/ai/training-data"
            ],
            "changefreq": "weekly"
        },
        "search": {
            "urls": [
                f"{base_url}/ai/search",
                f"{base_url}/ai/semantic-index"
            ],
            "changefreq": "daily"
        },
        "conversational": {
            "urls": [
                f"{base_url}/ai/chat",
                f"{base_url}/ai/assistant"
            ],
            "changefreq": "hourly"
        }
    }
    
    for sitemap_type, config in specialized_sitemaps.items():
        filename = f"ai-sitemap-{sitemap_type}.xml"
        filepath = os.path.join(SITEMAP_DIR, filename)
        
        urls = [{
            'loc': url,
            'lastmod': timestamp,
            'changefreq': config['changefreq'],
            'priority': '0.7'
        } for url in config['urls']]
        
        # Validate endpoints before adding to sitemap
        valid_urls = []
        for url in urls:
            is_valid, message = validate_ai_endpoint(url['loc'])
            if is_valid:
                valid_urls.append(url)
                print(f"✅ Validated AI endpoint: {url['loc']}")
            else:
                print(f"⚠️ Invalid AI endpoint ({url['loc']}): {message}")
        
        if valid_urls and update_or_create_sitemap(filepath, valid_urls):
            sitemap_updates = True
    
    # 3. Create sitemap index if updates occurred
    if sitemap_updates:
        sitemap_index_path = os.path.join(SITEMAP_DIR, "sitemap-index.xml")
        root = ET.Element("sitemapindex", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
        
        # Add all sitemaps to index
        for sitemap_file in os.listdir(SITEMAP_DIR):
            if sitemap_file.endswith('.xml') and sitemap_file != 'sitemap-index.xml':
                sitemap_elem = ET.SubElement(root, "sitemap")
                ET.SubElement(sitemap_elem, "loc").text = f"{base_url}/ai-sitemaps/{sitemap_file}"
                ET.SubElement(sitemap_elem, "lastmod").text = timestamp
        
        tree = ET.ElementTree(root)
        tree.write(sitemap_index_path, encoding='utf-8', xml_declaration=True)
        print(f"Created sitemap index at {sitemap_index_path}")
        
        # Ping search engines
        ping_search_engines(f"{base_url}/ai-sitemaps/sitemap-index.xml")

def main():
    print(f"🚀 Starting AI content generation at {datetime.now()}")
    
    try:
        # Setup and validation
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        df = pd.read_csv(INPUT_CSV)
        validate_csv_structure(df)
        
        base_url = validate_url(df.iloc[0]['website'])
        
        # Generate core files
        save_to_file(generate_faq_schema(df), "faq-schema.json")
        save_to_file(generate_company_schema(df), "company-schema.json")
        save_to_file(generate_qna_training(df), "qna-training.json")
        
        # Generate AI-specific files with validation
        generate_ai_sitemaps(df, base_url)
        generate_ai_knowledge(df)
        
        print("\n🎉 All AI content generated and validated successfully!")
        return True
        
    except FileGenerationError as e:
        print(f"\n❌ AI generation error: {str(e)}")
        return False
    except Exception as e:
        print(f"\n⚠️ Unexpected AI processing error: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
