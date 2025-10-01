#!/bin/bash

# Deployment script for PriceTracker
# Performs clean installation by removing previous version

set -e

echo "🧹 Cleaning up previous installation..."

# Stop and remove old service if it exists
sudo systemctl stop price-tracker 2>/dev/null || echo "   Service wasn't running"
sudo systemctl disable price-tracker 2>/dev/null || echo "   Service wasn't enabled"
sudo rm -f /etc/systemd/system/price-tracker.service

# Remove old installation
sudo rm -rf /opt/price-tracker

# Reload systemd
sudo systemctl daemon-reload

echo "🚀 Starting fresh installation..."

# Run the main setup script
./setup.sh

echo ""
echo "✅ Fresh installation completed!"
echo ""
echo "🔧 Configuration checklist:"
echo ""
echo "1. Add your API keys:"
echo "   sudo nano /opt/price-tracker/.env"
echo ""
echo "2. Test notifications:"
echo "   sudo -u price-tracker /opt/price-tracker/venv/bin/python /opt/price-tracker/main.py --test-notifications"
echo ""
echo "3. Test price scraping:"
echo "   sudo -u price-tracker /opt/price-tracker/venv/bin/python /opt/price-tracker/main.py --run-once"
echo ""
echo "4. Start the service:"
echo "   sudo cp /opt/price-tracker/price-tracker.service /etc/systemd/system/"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable price-tracker"
echo "   sudo systemctl start price-tracker"
echo ""
echo "5. Monitor logs:"
echo "   sudo journalctl -u price-tracker -f"
echo ""
echo "🎯 Now sit back and let your server hunt for CPU deals while you do... whatever it is humans do."
