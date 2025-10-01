# PriceTracker

Personal price monitoring tool that automatically checks Prisjakt.nu and Blocket.se for product deals. Built to stop manually checking if computer parts finally dropped in price.

## How it works

This tool monitors product prices across two Swedish platforms: Prisjakt (retail prices) and Blocket (used market). It scrapes prices at regular intervals, compares them against your target prices, and sends Pushbullet notifications when deals are found.

For Prisjakt, it tracks specific product pages. For Blocket, it searches for keywords and filters results by price range to avoid overpriced or suspicious listings. The tool runs as a background service on Linux, storing price history in JSON files and handling Swedish price formats automatically.

Configure products in `products.json`, set your notification preferences in `.env`, and let it run. It's designed for personal use to automate the tedious task of manually checking prices.

## Setup

```bash
git clone <repo-url>
cd PriceTracker
chmod +x setup.sh && ./setup.sh
sudo nano /opt/price-tracker/.env  # Add Pushbullet API key
sudo systemctl start price-tracker
```

*For detailed deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md)*

## Configuration

**products.json:**
```json
[
  {
    "name": "AMD Ryzen 7 7800X3D",
    "url": "https://www.prisjakt.nu/produkt.php?p=8053700",
    "target_price": 4000,
    "platform": "prisjakt"
  },
  {
    "name": "7800X3D Used",
    "url": "https://www.blocket.se/annonser/hela_sverige?q=7800x3d",
    "target_price": 3500,
    "platform": "blocket",
    "min_price": 2000,
    "max_price": 5000
  }
]
```

**Environment (.env):**
```bash
PUSHBULLET_API_KEY=your_key_here
SCRAPE_INTERVAL_HOURS=12
```

## Usage

```bash
python main.py --run-once         # Test run
python main.py --test-notifications  # Test alerts
sudo journalctl -u price-tracker -f  # View logs
```

Requires Linux and Python 3.8+. Get a free Pushbullet API key for notifications.

*For deployment, troubleshooting, and advanced configuration, see [DEPLOYMENT.md](DEPLOYMENT.md)*