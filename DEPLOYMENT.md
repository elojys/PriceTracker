# PriceTracker Deployment Guide

Complete deployment instructions for PriceTracker with multi-platform support (Prisjakt + Blocket).

## Prerequisites

- Linux server (Ubuntu 24.04+ recommended)
- Root or sudo access
- Internet connection

## Fresh Installation

```bash
# Clone the repository
git clone <repository-url>
cd PriceTracker

# Run automated setup
chmod +x setup.sh deploy.sh
./setup.sh

# Configure API keys
sudo nano /opt/price-tracker/.env
# Add: PUSHBULLET_API_KEY=your_key_here

# Start the service
sudo cp /opt/price-tracker/price-tracker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable price-tracker
sudo systemctl start price-tracker
```

## Updating Existing Installation

```bash
# Stop service
sudo systemctl stop price-tracker

# Backup configuration
sudo cp /opt/price-tracker/products.json /opt/price-tracker/products.json.backup
sudo cp /opt/price-tracker/.env /opt/price-tracker/.env.backup

# Update files
sudo cp -r /path/to/updated/files/* /opt/price-tracker/
sudo chown -R price-tracker:price-tracker /opt/price-tracker

# Update and restart service
sudo cp /opt/price-tracker/price-tracker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start price-tracker
```

## Configuration Files

### Environment Variables (.env)

```bash
# Notification settings
PUSHBULLET_API_KEY=your_key_here
SCRAPE_INTERVAL_HOURS=12

# Optional SMS (costs money)
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+1234567890
RECIPIENT_PHONE_NUMBER=+0987654321

# Advanced settings
MAX_RETRIES=3
RETRY_DELAY_SECONDS=5
LOG_LEVEL=INFO
```

### Product Configuration (products.json)

The system supports both Prisjakt (retail) and Blocket (used market):

**Prisjakt products:**
```json
{
  "name": "AMD Ryzen 7 7800X3D",
  "url": "https://www.prisjakt.nu/produkt.php?p=8053700",
  "target_price": 4000,
  "platform": "prisjakt",
  "price_selector": "text_search_kr"
}
```

**Blocket searches:**
```json
{
  "name": "7800X3D Used",
  "url": "https://www.blocket.se/annonser/hela_sverige?q=7800x3d",
  "target_price": 3500,
  "platform": "blocket",
  "min_price": 2000,
  "max_price": 5000,
  "price_selector": ".item-price"
}
```

## Verification

## Verification & Testing

```bash
# Test the installation
sudo -u price-tracker /opt/price-tracker/venv/bin/python /opt/price-tracker/main.py --run-once

# Test notifications
sudo -u price-tracker /opt/price-tracker/venv/bin/python /opt/price-tracker/main.py --test-notifications

# Check service status
sudo systemctl status price-tracker

# Monitor logs
sudo journalctl -u price-tracker -f
```

## Troubleshooting

**Service won't start:**
```bash
sudo journalctl -u price-tracker --no-pager
```

**Permission issues:**
```bash
sudo chown -R price-tracker:price-tracker /opt/price-tracker
```

**Network/scraping issues:**
- Increase `MAX_RETRIES` and `RETRY_DELAY_SECONDS` in `.env`
- Test specific URLs: `python main.py --test-scraper "https://example.com"`

**Rollback if needed:**
```bash
sudo systemctl stop price-tracker
sudo cp /opt/price-tracker/products.json.backup /opt/price-tracker/products.json
sudo cp /opt/price-tracker/.env.backup /opt/price-tracker/.env
sudo systemctl start price-tracker
```

## Non-Ubuntu/Debian Systems

The setup script uses `apt`. For other distros, install manually:

**Arch Linux:**
```bash
sudo pacman -S python python-pip python-virtualenv
```

**Fedora:**
```bash
sudo dnf install python3 python3-pip python3-virtualenv
```

Then create venv and install requirements.txt manually.