import json
import os
from typing import List, Dict, Optional
from datetime import datetime
from models import Product, PriceRecord
import logging


class PriceStorage:
    """Simple JSON-based storage for price history"""
    
    def __init__(self, storage_file: str = "price_history.json"):
        if not os.path.isabs(storage_file):
            import sys
            if hasattr(sys.modules['__main__'], '__file__'):
                script_dir = os.path.dirname(os.path.abspath(sys.modules['__main__'].__file__))
                storage_file = os.path.join(script_dir, storage_file)
        
        self.storage_file = storage_file
        self.logger = logging.getLogger(__name__)
        self._ensure_storage_file()
    
    def _ensure_storage_file(self):
        """Create storage file if it doesn't exist"""
        if not os.path.exists(self.storage_file):
            with open(self.storage_file, 'w') as f:
                json.dump({}, f)
            self.logger.info(f"Created storage file: {self.storage_file}")
    
    def save_price_record(self, price_record: PriceRecord):
        """Save a price record to storage"""
        try:
            data = self._load_data()
            
            product_name = price_record.product_name
            if product_name not in data:
                data[product_name] = []
            
            # Add the new record
            record_dict = price_record.dict()
            record_dict['timestamp'] = price_record.timestamp.isoformat()
            data[product_name].append(record_dict)
            
            # Keep only last 100 records per product
            data[product_name] = data[product_name][-100:]
            
            self._save_data(data)
            self.logger.info(f"Saved price record for {product_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to save price record: {e}")
    
    def get_latest_price(self, product_name: str) -> Optional[PriceRecord]:
        """Get the latest price record for a product"""
        try:
            data = self._load_data()
            
            if product_name not in data or not data[product_name]:
                return None
            
            latest_record = data[product_name][-1]
            latest_record['timestamp'] = datetime.fromisoformat(latest_record['timestamp'])
            
            return PriceRecord(**latest_record)
            
        except Exception as e:
            self.logger.error(f"Failed to get latest price for {product_name}: {e}")
            return None
    
    def get_price_history(self, product_name: str, limit: int = 10) -> List[PriceRecord]:
        """Get price history for a product"""
        try:
            data = self._load_data()
            
            if product_name not in data:
                return []
            
            records = []
            for record_dict in data[product_name][-limit:]:
                record_dict['timestamp'] = datetime.fromisoformat(record_dict['timestamp'])
                records.append(PriceRecord(**record_dict))
            
            return records
            
        except Exception as e:
            self.logger.error(f"Failed to get price history for {product_name}: {e}")
            return []
    
    def get_all_products(self) -> List[str]:
        """Get list of all monitored products"""
        try:
            data = self._load_data()
            return list(data.keys())
        except Exception as e:
            self.logger.error(f"Failed to get product list: {e}")
            return []
    
    def _load_data(self) -> Dict:
        """Load data from storage file"""
        try:
            with open(self.storage_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load data: {e}")
            return {}
    
    def _save_data(self, data: Dict):
        """Save data to storage file"""
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save data: {e}")
    
    def export_to_csv(self, output_file: str = "price_history.csv"):
        """Export all price history to CSV"""
        try:
            import csv
            
            data = self._load_data()
            
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['product_name', 'current_price', 'previous_price', 
                             'timestamp', 'url', 'price_dropped', 'target_price_reached']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for product_name, records in data.items():
                    for record in records:
                        writer.writerow(record)
            
            self.logger.info(f"Exported price history to {output_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to export to CSV: {e}")
