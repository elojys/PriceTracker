import logging
from typing import Optional
from pushbullet import Pushbullet
from twilio.rest import Client
from models import NotificationConfig, PriceRecord


class NotificationService:
    """
    Service for sending notifications via multiple channels
    
    Supports Pushbullet and Twilio SMS notifications for price alerts.
    """
    
    def __init__(self, config: NotificationConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.pushbullet = None
        self.twilio_client = None
        
        if config.method in ['pushbullet', 'both']:
            if config.pushbullet_api_key:
                try:
                    self.pushbullet = Pushbullet(config.pushbullet_api_key)
                    self.logger.info("Pushbullet service initialized")
                except Exception as e:
                    self.logger.error(f"Failed to initialize Pushbullet: {e}")
        
        if config.method in ['sms', 'both']:
            if config.twilio_account_sid and config.twilio_auth_token:
                try:
                    self.twilio_client = Client(
                        config.twilio_account_sid, 
                        config.twilio_auth_token
                    )
                    self.logger.info("Twilio service initialized")
                except Exception as e:
                    self.logger.error(f"Failed to initialize Twilio: {e}")
    
    def send_notification(self, price_record: PriceRecord) -> bool:
        """Send notification about price update"""
        title, message = self._format_message(price_record)
        
        success = True
        
        if self.config.method in ['pushbullet', 'both'] and self.pushbullet:
            success &= self._send_pushbullet(title, message, price_record.url)
        if self.config.method in ['sms', 'both'] and self.twilio_client:
            success &= self._send_sms(f"{title}\n{message}")
        
        return success
    
    def _format_message(self, price_record: PriceRecord) -> tuple[str, str]:
        """Format notification message"""
        title = f"Price Update: {price_record.product_name}"
        
        message_parts = [
            f"Current price: {price_record.current_price} SEK"
        ]
        
        if price_record.previous_price:
            price_change = price_record.current_price - price_record.previous_price
            change_symbol = "📉" if price_change < 0 else "📈"
            message_parts.append(
                f"Previous price: {price_record.previous_price} SEK ({change_symbol} {price_change:+.2f} SEK)"
            )
        
        if price_record.target_price_reached:
            message_parts.append("🎯 TARGET PRICE REACHED!")
        elif price_record.price_dropped:
            message_parts.append("💰 Price dropped!")
        
        message_parts.append(f"Updated: {price_record.timestamp.strftime('%Y-%m-%d %H:%M')}")
        
        return title, "\n".join(message_parts)
    
    def _send_pushbullet(self, title: str, message: str, url: str) -> bool:
        """Send push notification via Pushbullet"""
        try:
            self.pushbullet.push_link(title, url, body=message)
            self.logger.info("Push notification sent successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send push notification: {e}")
            return False
    
    def _send_sms(self, message: str) -> bool:
        """Send SMS via Twilio"""
        try:
            self.twilio_client.messages.create(
                body=message[:1600],  # SMS character limit
                from_=self.config.twilio_phone_number,
                to=self.config.recipient_phone_number
            )
            self.logger.info("SMS sent successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send SMS: {e}")
            return False
    
    def send_test_notification(self) -> bool:
        """Send a test notification to verify configuration"""
        try:
            title = "Price Scraper Test"
            message = "This is a test notification from your Prisjakt price scraper!"
            
            success = True
            
            if self.config.method in ['pushbullet', 'both'] and self.pushbullet:
                success &= self._send_pushbullet(title, message, "https://prisjakt.nu")
            
            if self.config.method in ['sms', 'both'] and self.twilio_client:
                success &= self._send_sms(f"{title}\n{message}")
            
            return success
        except Exception as e:
            self.logger.error(f"Failed to send test notification: {e}")
            return False
