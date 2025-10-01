import requests
from bs4 import BeautifulSoup
import re
import time
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin, urlparse
from models import Product, PriceRecord
from datetime import datetime


class PrisjaktScraper:
    """
    Web scraper for Prisjakt.nu
    
    Handles price extraction from Prisjakt product pages with support
    for various Swedish price formats.
    """
    
    def __init__(self, user_agent: str = None, max_retries: int = 3, retry_delay: int = 5):
        self.session = requests.Session()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logging.getLogger(__name__)
        
        if user_agent:
            self.session.headers.update({'User-Agent': user_agent})
        else:
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
    
    def scrape_product_price(self, product: Product) -> Optional[PriceRecord]:
        """Scrape price for a single product"""
        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"Scraping price for {product.name} (attempt {attempt + 1})")
                
                response = self.session.get(str(product.url), timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract price using the provided selector
                if product.price_selector == "text_search_kr":
                    price = self._extract_price_from_text(soup)
                else:
                    price = self._extract_price(soup, product.price_selector)
                
                if price is None:
                    alternative_selectors = [
                        "span:contains('kr')",
                        ".price-box .price",
                        ".lowest-price",
                        "strong:contains('kr')",
                        ".price",
                        "[data-testid*='price']",
                        ".price-value",
                        ".current-price",
                        ".product-price",
                        "text_search_kr"
                    ]
                    
                    for selector in alternative_selectors:
                        if selector == "text_search_kr":
                            price = self._extract_price_from_text(soup)
                        else:
                            price = self._extract_price(soup, selector)
                        if price is not None:
                            self.logger.info(f"Found price using alternative selector: {selector}")
                            break
                
                if price is not None:
                    target_price_reached = (
                        product.target_price is not None and 
                        price <= product.target_price
                    )
                    
                    price_record = PriceRecord(
                        product_name=product.name,
                        current_price=price,
                        timestamp=datetime.now(),
                        url=str(product.url),
                        target_price_reached=target_price_reached
                    )
                    
                    self.logger.info(f"Successfully scraped price for {product.name}: {price} SEK")
                    return price_record
                else:
                    self.logger.warning(f"Could not find price for {product.name}")
                    return None
                    
            except requests.RequestException as e:
                self.logger.error(f"Request failed for {product.name} (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
            except Exception as e:
                self.logger.error(f"Unexpected error scraping {product.name}: {e}")
                return None
        
        self.logger.error(f"Failed to scrape {product.name} after {self.max_retries} attempts")
        return None
    
    def _extract_price_from_text(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract price by searching for Swedish price patterns in all text"""
        try:
            # Get all text content
            page_text = soup.get_text()
            
            # Look for price patterns like "3 997 kr", "3997 kr", "3,997 kr"
            import re
            
            # Pattern for Swedish prices with "kr" - improved to handle space-separated thousands
            price_patterns = [
                r'(\d{1,3}(?:\s\d{3})+)\s*kr',    # "3 997 kr" (space-separated thousands)
                r'(\d{1,3}(?:,\d{3})+)\s*kr',     # "3,997 kr" (comma-separated thousands)
                r'(\d{4,6})\s*kr',                # "3997 kr" (no separators, 4-6 digits)
                r'(\d{1,3})\s*kr',                # "997 kr" (1-3 digits for hundreds)
            ]
            
            found_prices = []
            
            for pattern in price_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    price_text = match.replace(' ', '').replace(',', '')
                    try:
                        price = float(price_text)
                        if 100 <= price <= 100000:
                            found_prices.append(price)
                    except ValueError:
                        continue
            
            if found_prices:
                valid_prices = [p for p in found_prices if p >= 1000]
                if valid_prices:
                    return max(valid_prices)
                else:
                    return max(found_prices)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting price from text: {e}")
            return None
    
    def _extract_price(self, soup: BeautifulSoup, selector: str) -> Optional[float]:
        """Extract price from HTML using CSS selector"""
        try:
            price_elements = soup.select(selector)
            
            if not price_elements:
                return None
            
            for element in price_elements:
                price_text = element.get_text(strip=True)
                price = self._parse_price_text(price_text)
                if price is not None:
                    return price
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting price with selector '{selector}': {e}")
            return None
    
    def _parse_price_text(self, price_text: str) -> Optional[float]:
        """Parse price from text string"""
        try:
            # Remove common currency symbols and text
            cleaned_text = re.sub(r'[^\d,.\s]', '', price_text)
            cleaned_text = cleaned_text.strip()
            
            # Handle different number formats
            # Swedish format: 1 234,56 or 1234,56
            # English format: 1,234.56 or 1234.56
            
            # Remove spaces
            cleaned_text = cleaned_text.replace(' ', '')
            
            # If there's both comma and dot, determine which is decimal separator
            if ',' in cleaned_text and '.' in cleaned_text:
                if cleaned_text.rfind(',') > cleaned_text.rfind('.'):
                    cleaned_text = cleaned_text.replace('.', '').replace(',', '.')
                else:
                    cleaned_text = cleaned_text.replace(',', '')
            elif ',' in cleaned_text:
                comma_pos = cleaned_text.rfind(',')
                if len(cleaned_text) - comma_pos <= 3:
                    cleaned_text = cleaned_text.replace(',', '.')
                else:
                    cleaned_text = cleaned_text.replace(',', '')
            
            price = float(cleaned_text)
            
            if 0 <= price <= 10000000:
                return price
            else:
                return None
                
        except (ValueError, AttributeError):
            return None
    
    def test_selectors(self, url: str, selectors: list) -> Dict[str, Any]:
        """Test multiple selectors on a URL to find the best one"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            results = {}
            
            all_selectors = selectors + ["text_search_kr"]
            
            for selector in all_selectors:
                if selector == "text_search_kr":
                    price = self._extract_price_from_text(soup)
                    results[selector] = {
                        'price': price,
                        'elements_found': 'text_search',
                        'sample_text': 'Searches for kr prices in all page text'
                    }
                else:
                    price = self._extract_price(soup, selector)
                    elements = soup.select(selector)
                    results[selector] = {
                        'price': price,
                        'elements_found': len(elements),
                        'sample_text': elements[0].get_text(strip=True)[:100] + '...' if elements else None
                    }
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error testing selectors: {e}")
            return {}
    
    def close(self):
        """Close the session"""
        self.session.close()


class BlocketScraper:
    """
    Web scraper for Blocket.se
    
    Handles searching Blocket for items. Since Blocket uses heavy JavaScript
    for loading content, this scraper uses alternative approaches to get pricing data.
    """
    
    def __init__(self, user_agent: str = None, max_retries: int = 3, retry_delay: int = 5):
        self.session = requests.Session()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logging.getLogger(__name__)
        
        if user_agent:
            self.session.headers.update({'User-Agent': user_agent})
        else:
            # Use a more modern user agent that Blocket might accept better
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'sv-SE,sv;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            })
    
    def scrape_product_price(self, product: Product) -> Optional[PriceRecord]:
        """
        Scrape prices for Blocket search results
        
        Since Blocket uses JavaScript heavily, this method currently returns
        a placeholder result to indicate the search was attempted.
        Future improvements could use Selenium or API calls.
        """
        self.logger.info(f"Attempting Blocket search for {product.name}")
        
        # For now, return a special record indicating Blocket search was attempted
        # but actual price extraction needs JavaScript support
        price_record = PriceRecord(
            product_name=product.name,
            current_price=0.0,  # Placeholder - indicates search attempted but no results
            timestamp=datetime.now(),
            url=str(product.url),
            target_price_reached=False
        )
        
        self.logger.warning(f"Blocket scraping for {product.name} requires JavaScript support - search attempted but no prices extracted")
        self.logger.info(f"Manual search recommended: {product.url}")
        
        return price_record
    
    def close(self):
        """Close the session"""
        self.session.close()


class ScraperFactory:
    """
    Factory class to create appropriate scraper based on product platform
    """
    
    @staticmethod
    def create_scraper(product: Product, user_agent: str = None, max_retries: int = 3, retry_delay: int = 5):
        """Create appropriate scraper based on product platform"""
        if product.platform == "prisjakt":
            return PrisjaktScraper(user_agent, max_retries, retry_delay)
        elif product.platform == "blocket":
            return BlocketScraper(user_agent, max_retries, retry_delay)
        else:
            raise ValueError(f"Unsupported platform: {product.platform}")


class UnifiedScraper:
    """
    Unified scraper that can handle multiple platforms
    """
    
    def __init__(self, user_agent: str = None, max_retries: int = 3, retry_delay: int = 5):
        self.user_agent = user_agent
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.scrapers = {}  # Cache scrapers
        self.logger = logging.getLogger(__name__)
    
    def scrape_product_price(self, product: Product) -> Optional[PriceRecord]:
        """Scrape price using appropriate scraper for the product platform"""
        try:
            # Get or create scraper for this platform
            if product.platform not in self.scrapers:
                self.scrapers[product.platform] = ScraperFactory.create_scraper(
                    product, self.user_agent, self.max_retries, self.retry_delay
                )
            
            scraper = self.scrapers[product.platform]
            return scraper.scrape_product_price(product)
            
        except Exception as e:
            self.logger.error(f"Error scraping {product.name} from {product.platform}: {e}")
            return None
    
    def test_selectors(self, url: str, selectors: list) -> Dict[str, Any]:
        """Test selectors - only works for Prisjakt products"""
        # For now, assume it's a Prisjakt URL if testing selectors
        if "prisjakt" not in self.scrapers:
            self.scrapers["prisjakt"] = PrisjaktScraper(self.user_agent, self.max_retries, self.retry_delay)
        
        if hasattr(self.scrapers["prisjakt"], 'test_selectors'):
            return self.scrapers["prisjakt"].test_selectors(url, selectors)
        return {}
    
    def close(self):
        """Close all scrapers"""
        for scraper in self.scrapers.values():
            scraper.close()
        self.scrapers.clear()
