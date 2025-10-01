#!/usr/bin/env python3
"""
PriceTracker - Multi-Platform Price Monitoring System

A web scraper that monitors prices on Prisjakt.nu and Blocket.se,
sending notifications when deals are found.

Author: PriceTracker
"""

import os
import sys
import json
import logging
import argparse
import time
from typing import List, Dict, Any
from datetime import datetime, timedelta
import schedule
from dotenv import load_dotenv

# Import our modules
from models import Product, PriceRecord, NotificationConfig
from scraper import UnifiedScraper
from notification_service import NotificationService
from storage import PriceStorage


def setup_logging(log_level: str = "INFO", log_file: str = None):
    """Setup logging configuration"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file and log_file != "price_scraper.log":
        try:
            log_dir = os.path.dirname(log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            handlers.append(logging.FileHandler(log_file))
        except (PermissionError, OSError) as e:
            print(f"Warning: Cannot create log file {log_file}: {e}. Logging to stdout only.")
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=handlers
    )


def load_products(products_file: str = "products.json") -> List[Product]:
    """Load products from configuration file"""
    try:
        if not os.path.isabs(products_file):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            products_file = os.path.join(script_dir, products_file)
        
        with open(products_file, 'r', encoding='utf-8') as f:
            products_data = json.load(f)
        
        products = []
        for product_data in products_data:
            product = Product(**product_data)
            products.append(product)
        
        logging.info(f"Loaded {len(products)} products from {products_file}")
        return products
        
    except Exception as e:
        logging.error(f"Failed to load products from {products_file}: {e}")
        return []


def load_notification_config() -> NotificationConfig:
    """Load notification configuration from environment variables"""
    return NotificationConfig(
        method=os.getenv("NOTIFICATION_METHOD", "pushbullet"),
        pushbullet_api_key=os.getenv("PUSHBULLET_API_KEY"),
        twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
        twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
        twilio_phone_number=os.getenv("TWILIO_PHONE_NUMBER"),
        recipient_phone_number=os.getenv("RECIPIENT_PHONE_NUMBER")
    )


def should_notify(current_record: PriceRecord, previous_record: PriceRecord = None) -> bool:
    """Determine if a notification should be sent"""
    if current_record.target_price_reached:
        return True
    
    if previous_record and current_record.current_price < previous_record.current_price:
        current_record.price_dropped = True
        current_record.previous_price = previous_record.current_price
        return True
    
    if previous_record is None:
        return True
    
    return False


def scrape_and_notify():
    """Main scraping and notification function"""
    logger = logging.getLogger(__name__)
    logger.info("Starting price scraping cycle")
    
    try:
        products = load_products()
        if not products:
            logger.error("No products to monitor")
            return
        
        notification_config = load_notification_config()
        
        scraper = UnifiedScraper(
            user_agent=os.getenv("USER_AGENT"),
            max_retries=int(os.getenv("MAX_RETRIES", 3)),
            retry_delay=int(os.getenv("RETRY_DELAY_SECONDS", 5))
        )
        
        notification_service = NotificationService(notification_config)
        storage = PriceStorage()
        
        for product in products:
            logger.info(f"Processing {product.name}")
            previous_record = storage.get_latest_price(product.name)
            
            # Scrape current price
            current_record = scraper.scrape_product_price(product)
            
            if current_record is None:
                logger.warning(f"Failed to scrape price for {product.name}")
                continue
            
            storage.save_price_record(current_record)
            
            if should_notify(current_record, previous_record):
                logger.info(f"Sending notification for {product.name}")
                notification_service.send_notification(current_record)
            else:
                logger.info(f"No notification needed for {product.name}")
            
            time.sleep(2)
        
        scraper.close()
        logger.info("Completed price scraping cycle")
        
    except Exception as e:
        logger.error(f"Error in scraping cycle: {e}")


def test_scraper(url: str):
    """Test scraper on a specific URL"""
    print(f"Testing scraper on: {url}")
    
    scraper = UnifiedScraper()
    
    selectors = [
        ".price-large",
        ".price",
        ".current-price",
        ".product-price",
        "[data-testid*='price']",
        ".price-value"
    ]
    
    results = scraper.test_selectors(url, selectors)
    
    print("\nSelector test results:")
    for selector, result in results.items():
        print(f"  {selector}:")
        print(f"    Price found: {result['price']}")
        print(f"    Elements found: {result['elements_found']}")
        print(f"    Sample text: {result['sample_text']}")
        print()
    
    scraper.close()


def test_notifications():
    """Test notification services"""
    print("Testing notification services...")
    
    notification_config = load_notification_config()
    notification_service = NotificationService(notification_config)
    
    success = notification_service.send_test_notification()
    
    if success:
        print("✅ Test notification sent successfully!")
    else:
        print("❌ Failed to send test notification")


def run_once():
    """Run scraper once and exit"""
    print("Running scraper once...")
    scrape_and_notify()
    print("Scraping completed")


def run_scheduler():
    """Run scraper on schedule"""
    logger = logging.getLogger(__name__)
    interval_hours = int(os.getenv("SCRAPE_INTERVAL_HOURS", 24))
    
    logger.info(f"Scheduling scraper to run every {interval_hours} hours")
    
    schedule.every(interval_hours).hours.do(scrape_and_notify)
    
    scrape_and_notify()
    
    while True:
        schedule.run_pending()
        time.sleep(60)


def main():
    """Main function"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_file = os.path.join(script_dir, '.env')
    load_dotenv(env_file)
    
    parser = argparse.ArgumentParser(description="PriceTracker - Multi-Platform Price Monitor")
    parser.add_argument("--test-scraper", type=str, metavar="URL", 
                       help="Test scraper on a specific URL")
    parser.add_argument("--test-notifications", action="store_true",
                       help="Test notification services")
    parser.add_argument("--run-once", action="store_true",
                       help="Run scraper once and exit")
    parser.add_argument("--schedule", action="store_true",
                       help="Run scraper on schedule (default)")
    parser.add_argument("--log-level", default="INFO",
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Set logging level")
    
    args = parser.parse_args()
    
    setup_logging(
        log_level=args.log_level,
        log_file=os.getenv("LOG_FILE", "price_scraper.log")
    )
    
    if args.test_scraper:
        setup_logging(log_level=args.log_level, log_file=None)
        test_scraper(args.test_scraper)
    elif args.test_notifications:
        test_notifications()
    elif args.run_once:
        run_once()
    else:
        run_scheduler()


if __name__ == "__main__":
    main()
