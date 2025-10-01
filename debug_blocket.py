#!/usr/bin/env python3
"""
Debug script to inspect Blocket HTML structure
"""

import requests
from bs4 import BeautifulSoup
import re

def debug_blocket_page():
    url = "https://www.blocket.se/annonser/hela_sverige?q=7800x3d"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    print(f"🔍 Fetching: {url}")
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        print(f"✅ Page loaded successfully")
        print(f"📄 Title: {soup.title.string if soup.title else 'No title'}")
        print(f"📏 Content length: {len(response.content)} bytes")
        
        # Look for common price-related elements
        print("\n🔎 Searching for price-related elements...")
        
        # Common selectors to try
        selectors = [
            '.item-price',
            '.search-item__price', 
            '.price-container',
            '[data-testid="price"]',
            '.amount',
            '.price',
            '.listing-price',
            '.ad-price',
            '[class*="price"]',
            '[class*="Price"]'
        ]
        
        found_elements = False
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                print(f"  ✅ Found {len(elements)} elements with selector: {selector}")
                for i, elem in enumerate(elements[:3]):  # Show first 3
                    print(f"    {i+1}: {elem.get_text(strip=True)}")
                found_elements = True
            
        if not found_elements:
            print("  ❌ No elements found with common price selectors")
        
        # Look for text containing "kr"
        print("\n💰 Searching for text containing 'kr'...")
        text_content = soup.get_text()
        kr_matches = re.findall(r'.{0,20}\d+[.\s,]*kr.{0,20}', text_content, re.IGNORECASE)
        
        if kr_matches:
            print(f"  ✅ Found {len(kr_matches)} 'kr' price patterns:")
            for i, match in enumerate(kr_matches[:10]):  # Show first 10
                print(f"    {i+1}: {match.strip()}")
        else:
            print("  ❌ No 'kr' patterns found")
        
        # Look for any elements that might contain prices
        print("\n🧩 Looking for divs/spans that might contain prices...")
        all_divs_spans = soup.find_all(['div', 'span'])
        price_candidates = []
        
        for elem in all_divs_spans:
            text = elem.get_text(strip=True)
            if re.search(r'\d+.*kr', text, re.IGNORECASE):
                price_candidates.append((elem.get('class', []), text))
        
        if price_candidates:
            print(f"  ✅ Found {len(price_candidates)} potential price elements:")
            for i, (classes, text) in enumerate(price_candidates[:5]):
                print(f"    {i+1}: classes={classes}, text='{text}'")
        else:
            print("  ❌ No potential price elements found")
            
        # Check if this might be a JavaScript-heavy page
        scripts = soup.find_all('script')
        if len(scripts) > 5:
            print(f"\n⚠️  Page has {len(scripts)} script tags - might be JavaScript-heavy")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_blocket_page()