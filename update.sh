#!/bin/bash

# Update script for PriceTracker
# Updates existing installation while preserving configuration and price history

set -e

echo "🔄 Updating PriceTracker installation..."
echo ""

# Check if installation exists
if [ ! -d "/opt/price-tracker" ]; then
    echo "❌ No existing installation found at /opt/price-tracker"
    echo "   Use setup.sh for fresh installation or deploy.sh for clean installation"
    exit 1
fi

# Backup configuration and data
echo "💾 Backing up configuration and data..."
BACKUP_DIR="/tmp/price-tracker-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup important files
sudo cp /opt/price-tracker/.env "$BACKUP_DIR/" 2>/dev/null || echo "   No .env file to backup"
sudo cp /opt/price-tracker/products.json "$BACKUP_DIR/" 2>/dev/null || echo "   No products.json to backup"  
sudo cp /opt/price-tracker/price_history.json "$BACKUP_DIR/" 2>/dev/null || echo "   No price_history.json to backup"

echo "   Backup created at: $BACKUP_DIR"

# Stop service for update
echo "⏸️  Stopping price-tracker service..."
sudo systemctl stop price-tracker 2>/dev/null || echo "   Service wasn't running"

# Update code files
echo "📥 Updating application files..."

# Update Python files
sudo cp main.py /opt/price-tracker/
sudo cp scraper.py /opt/price-tracker/
sudo cp models.py /opt/price-tracker/
sudo cp notification_service.py /opt/price-tracker/
sudo cp storage.py /opt/price-tracker/

# Update service file
sudo cp price-tracker.service /opt/price-tracker/
sudo cp price-tracker.service /etc/systemd/system/

# Update requirements if they changed
sudo cp requirements.txt /opt/price-tracker/

# Update virtual environment if requirements changed
echo "🔧 Updating Python dependencies..."
sudo -u price-tracker /opt/price-tracker/venv/bin/pip install -r /opt/price-tracker/requirements.txt --upgrade

# Restore configuration and data
echo "🔙 Restoring configuration and data..."
sudo cp "$BACKUP_DIR/.env" /opt/price-tracker/ 2>/dev/null || echo "   No .env to restore"
sudo cp "$BACKUP_DIR/products.json" /opt/price-tracker/ 2>/dev/null || echo "   No products.json to restore"
sudo cp "$BACKUP_DIR/price_history.json" /opt/price-tracker/ 2>/dev/null || echo "   No price_history.json to restore"

# Fix permissions
sudo chown -R price-tracker:price-tracker /opt/price-tracker/

# Reload systemd and restart service
echo "🔄 Reloading systemd and starting service..."
sudo systemctl daemon-reload
sudo systemctl start price-tracker
sudo systemctl enable price-tracker

# Check service status
sleep 2
if sudo systemctl is-active price-tracker --quiet; then
    echo ""
    echo "✅ Update completed successfully!"
    echo "   Service is running and enabled"
else
    echo ""
    echo "⚠️  Update completed but service may have issues"
    echo "   Check status: sudo systemctl status price-tracker"
    echo "   Check logs: sudo journalctl -u price-tracker -n 20"
fi

echo ""
echo "📊 Update summary:"
echo "   • Configuration preserved from backup"
echo "   • Price history preserved"
echo "   • Service updated and restarted"
echo "   • Backup available at: $BACKUP_DIR"
echo ""
echo "🎯 Your price tracking continues with the latest features!"