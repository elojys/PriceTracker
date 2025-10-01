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
    
    Handles searching Blocket for items and extracting prices from search results
    with price range filtering.
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
        """Scrape prices for Blocket search results"""
        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"Scraping Blocket for {product.name} (attempt {attempt + 1})")
                
                response = self.session.get(str(product.url), timeout=30)
                response.raise_for_status()
                
                self.logger.debug(f"Response status: {response.status_code}, content length: {len(response.content)}")
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Log some basic page info for debugging
                title = soup.title.string if soup.title else "No title"
                self.logger.debug(f"Page title: {title}")
                
                # Check if this might be a bot-detection page
                if "robot" in title.lower() or "captcha" in response.text.lower():
                    self.logger.warning(f"Possible bot detection page for {product.name}")
                
                # Extract all prices from search results
                prices = self._extract_search_result_prices(soup, product)
                
                if prices:
                    filtered_prices = []
                    for price in prices:
                        if self._is_price_in_range(price, product.min_price, product.max_price):
                            filtered_prices.append(price)
                    
                    if filtered_prices:
                        best_price = min(filtered_prices)
                        
                        target_price_reached = (
                            product.target_price is not None and 
                            best_price <= product.target_price
                        )
                        
                        price_record = PriceRecord(
                            product_name=product.name,
                            current_price=best_price,
                            timestamp=datetime.now(),
                            url=str(product.url),
                            target_price_reached=target_price_reached
                        )
                        
                        self.logger.info(f"Found {len(filtered_prices)} items in price range for {product.name}, best price: {best_price} SEK")
                        return price_record
                    else:
                        self.logger.info(f"Found {len(prices)} items for {product.name}, but none in specified price range")
                else:
                    self.logger.warning(f"Could not find any prices for {product.name}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    
            except requests.RequestException as e:
                self.logger.error(f"Request failed for {product.name}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
            except Exception as e:
                self.logger.error(f"Unexpected error scraping {product.name}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
        
        return None
    
    def _extract_search_result_prices(self, soup: BeautifulSoup, product: Product) -> List[float]:
        """Extract all prices from Blocket search results"""
        prices = []
        
        # More comprehensive list of price selectors for Blocket
        price_selectors = [
            '.item-price',
            '.search-item__price',
            '.price-container',
            '[data-testid="price"]',
            '.amount',
            '.price',
            '.listing-price',
            '.ad-price',
            '[class*="price"]',
            '[class*="Price"]',
            '.SearchItem-price',
            '.listitem-price',
            '.price-value',
            '.ad-item-price'
        ]
        
        self.logger.debug(f"Searching for prices with {len(price_selectors)} selectors")
        
        for selector in price_selectors:
            elements = soup.select(selector)
            if elements:
                self.logger.debug(f"Found {len(elements)} elements with selector: {selector}")
                for element in elements:
                    price_text = element.get_text(strip=True)
                    self.logger.debug(f"Price text from {selector}: '{price_text}'")
                    price = self._parse_price_text(price_text)
                    if price is not None:
                        prices.append(price)
                        self.logger.debug(f"Parsed price: {price}")

        # If no prices found with selectors, try text-based extraction
        if not prices:
            self.logger.debug("No prices found with selectors, trying text extraction")
            prices = self._extract_prices_from_text(soup)
        
        # Remove duplicates and sort
        prices = sorted(list(set(prices)))
        
        self.logger.info(f"Extracted {len(prices)} unique prices: {prices[:10]}")  # Show first 10
        return prices
    
    def _extract_prices_from_text(self, soup: BeautifulSoup) -> List[float]:
        """Extract prices from all text content (fallback method)"""
        prices = []
        
        text_content = soup.get_text()
        self.logger.debug(f"Searching text content (length: {len(text_content)})")
        
        # More comprehensive price patterns for Swedish prices
        price_patterns = [
            r'(\d{1,3}(?:\s\d{3})+)\s*kr',    # "3 997 kr" (space-separated thousands)
            r'(\d+)\s*kr',                    # "3997 kr" (no separators)
            r'kr\s*(\d{1,3}(?:\s\d{3})+)',    # "kr 3 997" (reversed)
            r'kr\s*(\d+)',                    # "kr 3997" (reversed, no separators)
            r'(\d+(?:,\d{3})+)\s*kr',         # "3,997 kr" (comma-separated)
            r'(\d+(?:\.\d{3})+)\s*kr',        # "3.997 kr" (dot-separated - some locales)
            r'(\d{4,6})\s*kr',                # 4-6 digit prices
        ]
        
        for i, pattern in enumerate(price_patterns):
            matches = re.finditer(pattern, text_content, re.IGNORECASE)
            pattern_prices = []
            for match in matches:
                price_text = match.group(1)
                price = self._parse_price_text(price_text)
                if price is not None:
                    pattern_prices.append(price)
                    prices.append(price)
            
            if pattern_prices:
                self.logger.debug(f"Pattern {i+1} found {len(pattern_prices)} prices: {pattern_prices[:5]}")
        
        self.logger.debug(f"Text extraction found {len(prices)} total prices")
        return prices
    
    def _parse_price_text(self, price_text: str) -> Optional[float]:
        """Parse price text into float value"""
        if not price_text:
            return None
        
        try:
            cleaned_text = re.sub(r'[^\d\s,.-]', '', price_text).strip()
            
            if not cleaned_text:
                return None
            
            if ' ' in cleaned_text:
                cleaned_text = cleaned_text.replace(' ', '')
            elif ',' in cleaned_text and '.' in cleaned_text:
                if cleaned_text.index(',') < cleaned_text.index('.'):
                    cleaned_text = cleaned_text.replace(',', '')
                else:
                    cleaned_text = cleaned_text.replace('.', '').replace(',', '.')
            elif ',' in cleaned_text:
                comma_pos = cleaned_text.rfind(',')
                if len(cleaned_text) - comma_pos <= 3:
                    cleaned_text = cleaned_text.replace(',', '.')
                else:
                    cleaned_text = cleaned_text.replace(',', '')
            
            price = float(cleaned_text)
            
            if 100 <= price <= 100000:
                return price
            else:
                return None
                
        except (ValueError, AttributeError):
            return None
    
    def _is_price_in_range(self, price: float, min_price: Optional[float], max_price: Optional[float]) -> bool:
        """Check if price is within specified range"""
        if min_price is not None and price < min_price:
            return False
        if max_price is not None and price > max_price:
            return False
        return True
    
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
