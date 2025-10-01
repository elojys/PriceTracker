from typing import List, Optional, Dict, Any
from pydantic import BaseModel, HttpUrl, validator
from datetime import datetime


class Product(BaseModel):
    """Model for a product to monitor"""
    name: str
    url: HttpUrl
    target_price: Optional[float] = None
    price_selector: str = ".price-large"  # CSS selector for price element
    platform: str = "prisjakt"  # Platform: 'prisjakt' or 'blocket'
    min_price: Optional[float] = None  # Minimum price filter (for Blocket)
    max_price: Optional[float] = None  # Maximum price filter (for Blocket)
    
    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Product name cannot be empty')
        return v.strip()
    
    @validator('platform')
    def validate_platform(cls, v):
        valid_platforms = ['prisjakt', 'blocket']
        if v not in valid_platforms:
            raise ValueError(f'Platform must be one of {valid_platforms}')
        return v


class PriceRecord(BaseModel):
    """Model for a price record"""
    product_name: str
    current_price: float
    previous_price: Optional[float] = None
    timestamp: datetime
    url: str
    price_dropped: bool = False
    target_price_reached: bool = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class NotificationConfig(BaseModel):
    """Model for notification configuration"""
    method: str  # 'pushbullet', 'sms', or 'both'
    pushbullet_api_key: Optional[str] = None
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    recipient_phone_number: Optional[str] = None
    
    @validator('method')
    def validate_notification_method(cls, v):
        valid_methods = ['pushbullet', 'sms', 'both']
        if v not in valid_methods:
            raise ValueError(f'Method must be one of {valid_methods}')
        return v
