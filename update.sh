#!/bin/bash

# Update script for PriceTracker
# Updates existing installation while preserving configuration and price history

set -e

echo "🔄 Updating PriceTracker installation..."
echo ""

# Check if installation exists (support both old and new names)
OLD_INSTALL="/opt/prisjakt-scraper"
NEW_INSTALL="/opt/price-tracker"

if [ -d "$OLD_INSTALL" ]; then
    INSTALL_DIR="$OLD_INSTALL"
    SERVICE_NAME="prisjakt-scraper"
    echo "📍 Found existing installation at $OLD_INSTALL"
    echo "   Will migrate to new PriceTracker structure"
elif [ -d "$NEW_INSTALL" ]; then
    INSTALL_DIR="$NEW_INSTALL"
    SERVICE_NAME="price-tracker"
    echo "📍 Found existing installation at $NEW_INSTALL"
else
    echo "❌ No existing installation found at $OLD_INSTALL or $NEW_INSTALL"
    echo "   Use setup.sh for fresh installation or deploy.sh for clean installation"
    exit 1
fi

# Backup configuration and data
echo "💾 Backing up configuration and data..."
BACKUP_DIR="/tmp/price-tracker-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup important files
sudo cp "$INSTALL_DIR/.env" "$BACKUP_DIR/" 2>/dev/null || echo "   No .env file to backup"
sudo cp "$INSTALL_DIR/products.json" "$BACKUP_DIR/" 2>/dev/null || echo "   No products.json to backup"  
sudo cp "$INSTALL_DIR/price_history.json" "$BACKUP_DIR/" 2>/dev/null || echo "   No price_history.json to backup"

echo "   Backup created at: $BACKUP_DIR"

# Stop service for update
echo "⏸️  Stopping $SERVICE_NAME service..."
sudo systemctl stop "$SERVICE_NAME" 2>/dev/null || echo "   Service wasn't running"

# If migrating from old installation, create new directory structure
if [ "$INSTALL_DIR" = "$OLD_INSTALL" ]; then
    echo "🔄 Migrating from prisjakt-scraper to price-tracker..."
    
    # Create price-tracker user if it doesn't exist
    if ! id "price-tracker" &>/dev/null; then
        echo "   Creating price-tracker user..."
        sudo useradd --system --no-create-home --shell /bin/false price-tracker
    fi
    
    # Create new directory
    sudo mkdir -p "$NEW_INSTALL"
    
    # Copy virtual environment if it exists
    if [ -d "$OLD_INSTALL/venv" ]; then
        sudo cp -r "$OLD_INSTALL/venv" "$NEW_INSTALL/"
    fi
    
    # Update installation directory for rest of script
    INSTALL_DIR="$NEW_INSTALL"
    
    # We'll clean up old installation at the end
    MIGRATE_FROM_OLD=true
else
    MIGRATE_FROM_OLD=false
fi

# Update code files
echo "📥 Updating application files..."

# Update Python files
sudo cp main.py "$INSTALL_DIR/"
sudo cp scraper.py "$INSTALL_DIR/"
sudo cp models.py "$INSTALL_DIR/"
sudo cp notification_service.py "$INSTALL_DIR/"
sudo cp storage.py "$INSTALL_DIR/"

# Update service file and install it
sudo cp price-tracker.service "$INSTALL_DIR/"
sudo cp price-tracker.service /etc/systemd/system/

# Update requirements if they changed
sudo cp requirements.txt "$INSTALL_DIR/"

# Update virtual environment if requirements changed
echo "🔧 Updating Python dependencies..."
if [ -d "$INSTALL_DIR/venv" ]; then
    # Fix permissions first
    sudo chown -R price-tracker:price-tracker "$INSTALL_DIR/venv"
    sudo -u price-tracker "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" --upgrade
else
    echo "   Creating new virtual environment..."
    sudo python3 -m venv "$INSTALL_DIR/venv"
    sudo chown -R price-tracker:price-tracker "$INSTALL_DIR/venv"
    sudo -u price-tracker "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
fi

# Restore configuration and data
echo "🔙 Restoring configuration and data..."
sudo cp "$BACKUP_DIR/.env" "$INSTALL_DIR/" 2>/dev/null || echo "   No .env to restore"
sudo cp "$BACKUP_DIR/products.json" "$INSTALL_DIR/" 2>/dev/null || echo "   No products.json to restore"
sudo cp "$BACKUP_DIR/price_history.json" "$INSTALL_DIR/" 2>/dev/null || echo "   No price_history.json to restore"

# Fix permissions
sudo chown -R price-tracker:price-tracker "$INSTALL_DIR/"

# Handle service migration
if [ "$MIGRATE_FROM_OLD" = true ]; then
    echo "🔄 Migrating service from prisjakt-scraper to price-tracker..."
    
    # Disable and remove old service
    sudo systemctl disable prisjakt-scraper 2>/dev/null || echo "   Old service wasn't enabled"
    sudo rm -f /etc/systemd/system/prisjakt-scraper.service
    
    # Clean up old installation directory (but keep backup)
    echo "🧹 Cleaning up old installation at $OLD_INSTALL..."
    sudo rm -rf "$OLD_INSTALL"
fi

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
    if [ "$MIGRATE_FROM_OLD" = true ]; then
        echo "   ✅ Successfully migrated from prisjakt-scraper to price-tracker"
    fi
    echo "   Service is running and enabled"
else
    echo ""
    echo "⚠️  Update completed but service may have issues"
    echo "   Check status: sudo systemctl status price-tracker"
    echo "   Check logs: sudo journalctl -u price-tracker -n 20"
fi

echo ""
echo "📊 Update summary:"
if [ "$MIGRATE_FROM_OLD" = true ]; then
    echo "   • Migrated from /opt/prisjakt-scraper to /opt/price-tracker"
    echo "   • Service renamed from prisjakt-scraper to price-tracker"
fi
echo "   • Configuration preserved from backup"
echo "   • Price history preserved"
echo "   • Service updated and restarted"
echo "   • Backup available at: $BACKUP_DIR"
echo ""
echo "🎯 Your price tracking continues with the latest features!"