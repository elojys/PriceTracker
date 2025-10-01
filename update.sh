#!/bin/bash

# Update script for PriceTracker
# Updates existing installation while preserving configuration and price history

set -e

echo "🔄 Updating PriceTracker installation..."
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# If script is downloaded standalone, clone the repo
if [ ! -f "$SCRIPT_DIR/main.py" ]; then
    echo "📥 Source files not found locally, cloning from GitHub..."
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    git clone https://github.com/elojys/PriceTracker.git
    SCRIPT_DIR="$TEMP_DIR/PriceTracker"
    echo "   Cloned to: $SCRIPT_DIR"
fi

echo "📂 Using source files from: $SCRIPT_DIR"

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
sudo cp "$SCRIPT_DIR/main.py" "$INSTALL_DIR/"
sudo cp "$SCRIPT_DIR/scraper.py" "$INSTALL_DIR/"
sudo cp "$SCRIPT_DIR/models.py" "$INSTALL_DIR/"
sudo cp "$SCRIPT_DIR/notification_service.py" "$INSTALL_DIR/"
sudo cp "$SCRIPT_DIR/storage.py" "$INSTALL_DIR/"

# Update service file and install it
sudo cp "$SCRIPT_DIR/price-tracker.service" "$INSTALL_DIR/"
sudo cp "$SCRIPT_DIR/price-tracker.service" /etc/systemd/system/

# Update requirements if they changed
sudo cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/"

# Copy debug script if it exists
if [ -f "$SCRIPT_DIR/debug_blocket.py" ]; then
    sudo cp "$SCRIPT_DIR/debug_blocket.py" "$INSTALL_DIR/"
fi

# Update virtual environment if requirements changed
echo "🔧 Updating Python dependencies..."

# Check if virtual environment exists and is working
if [ -d "$INSTALL_DIR/venv" ] && [ -f "$INSTALL_DIR/venv/bin/pip" ]; then
    echo "   Found existing virtual environment"
    # Fix permissions first
    sudo chown -R price-tracker:price-tracker "$INSTALL_DIR/venv"
    
    # Test if pip works
    if sudo -u price-tracker "$INSTALL_DIR/venv/bin/pip" --version >/dev/null 2>&1; then
        echo "   Virtual environment is working, updating packages..."
        sudo -u price-tracker "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" --upgrade
    else
        echo "   Virtual environment is broken, recreating..."
        sudo rm -rf "$INSTALL_DIR/venv"
        sudo python3 -m venv "$INSTALL_DIR/venv"
        sudo chown -R price-tracker:price-tracker "$INSTALL_DIR/venv"
        sudo -u price-tracker "$INSTALL_DIR/venv/bin/pip" install --upgrade pip
        sudo -u price-tracker "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
    fi
else
    echo "   Creating new virtual environment..."
    sudo rm -rf "$INSTALL_DIR/venv" 2>/dev/null || true
    sudo python3 -m venv "$INSTALL_DIR/venv"
    sudo chown -R price-tracker:price-tracker "$INSTALL_DIR/venv"
    sudo -u price-tracker "$INSTALL_DIR/venv/bin/pip" install --upgrade pip
    sudo -u price-tracker "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
fi

# Restore configuration and data
echo "🔙 Restoring configuration and data..."
if [ -f "$BACKUP_DIR/.env" ]; then
    sudo cp "$BACKUP_DIR/.env" "$INSTALL_DIR/"
    echo "   ✅ Restored .env file"
else
    echo "   ⚠️  No .env file to restore"
fi

if [ -f "$BACKUP_DIR/products.json" ]; then
    sudo cp "$BACKUP_DIR/products.json" "$INSTALL_DIR/"
    echo "   ✅ Restored products.json"
else
    echo "   ⚠️  No products.json to restore"
fi

if [ -f "$BACKUP_DIR/price_history.json" ]; then
    sudo cp "$BACKUP_DIR/price_history.json" "$INSTALL_DIR/"
    echo "   ✅ Restored price_history.json"
else
    echo "   ℹ️  No price_history.json to restore (will be created on first run)"
fi

# Fix permissions for all files
echo "🔧 Fixing file permissions..."
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

# Test configuration before starting service
echo "🧪 Testing configuration..."
if sudo -u price-tracker "$INSTALL_DIR/venv/bin/python" -c "
import sys
sys.path.insert(0, '$INSTALL_DIR')
try:
    from models import Product
    from storage import Storage
    print('✅ Python modules load correctly')
except Exception as e:
    print(f'❌ Module loading failed: {e}')
    exit(1)
"; then
    echo "   Configuration test passed"
else
    echo "   ⚠️  Configuration test failed, but continuing..."
fi

# Start the service
echo "🚀 Starting price-tracker service..."
sudo systemctl start price-tracker
sudo systemctl enable price-tracker

# Check service status
sleep 3
if sudo systemctl is-active price-tracker --quiet; then
    echo ""
    echo "✅ Update completed successfully!"
    if [ "$MIGRATE_FROM_OLD" = true ]; then
        echo "   ✅ Successfully migrated from prisjakt-scraper to price-tracker"
    fi
    echo "   📊 Service is running and enabled"
    echo "   📝 Check logs: sudo journalctl -u price-tracker -f"
else
    echo ""
    echo "⚠️  Update completed but service may have issues"
    echo "   🔍 Check status: sudo systemctl status price-tracker"
    echo "   📋 Check logs: sudo journalctl -u price-tracker -n 20"
    echo "   🧪 Test manually: sudo -u price-tracker $INSTALL_DIR/venv/bin/python $INSTALL_DIR/main.py --test-notifications"
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

# Clean up temporary directory if we created one
if [[ "$SCRIPT_DIR" == /tmp/* ]] && [ -d "$SCRIPT_DIR" ]; then
    echo "🧹 Cleaning up temporary files..."
    rm -rf "$(dirname "$SCRIPT_DIR")"
fi