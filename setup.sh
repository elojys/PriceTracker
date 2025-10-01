#!/bin/bash

# PriceTracker Setup Script for Ubuntu 24.04 LTS
# Automated installation for multi-platform price monitoring

set -e

echo "🚀 Setting up PriceTracker on your server..."

# Update system packages
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python 3 and required packages
echo "🐍 Installing Python 3 and required packages..."
sudo apt install -y python3 python3-pip python3-venv python3-full curl wget git

# Install system dependencies for web scraping
echo "🔧 Installing system dependencies..."
sudo apt install -y chromium-browser

# Create application directory
APP_DIR="/opt/price-tracker"
echo "📁 Creating application directory: $APP_DIR"
sudo mkdir -p $APP_DIR

# Create dedicated user for the service
echo "👤 Creating price-tracker user..."
sudo useradd -r -s /bin/false -d $APP_DIR price-tracker || echo "User already exists"

# Copy application files
echo "📋 Copying application files..."
sudo cp -r . $APP_DIR/
cd $APP_DIR

# Set proper ownership
sudo chown -R price-tracker:price-tracker $APP_DIR

# Create Python virtual environment
echo "🔨 Creating Python virtual environment..."
sudo -u price-tracker python3 -m venv $APP_DIR/venv

# Install Python dependencies
echo "📦 Installing Python dependencies..."
sudo -u price-tracker $APP_DIR/venv/bin/pip install --upgrade pip
sudo -u price-tracker $APP_DIR/venv/bin/pip install -r $APP_DIR/requirements.txt

# Create logs directory
echo "📁 Creating logs directory..."
sudo mkdir -p $APP_DIR/logs
sudo chown price-tracker:price-tracker $APP_DIR/logs

# Create .env file from template
echo "⚙️ Creating environment configuration..."
sudo cp $APP_DIR/.env.example $APP_DIR/.env
sudo chown price-tracker:price-tracker $APP_DIR/.env

echo "
🎉 Setup completed successfully!

📝 Next steps:

1. Edit the configuration files:
   - Edit $APP_DIR/.env with your API keys and settings
   - Edit $APP_DIR/products.json with the products you want to monitor

2. Test the application:
   cd $APP_DIR
   sudo -u price-tracker $APP_DIR/venv/bin/python main.py --test-notifications
   sudo -u price-tracker $APP_DIR/venv/bin/python main.py --run-once

3. Set up the systemd service:
   sudo cp $APP_DIR/price-tracker.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable price-tracker
   sudo systemctl start price-tracker

4. Monitor logs:
   sudo journalctl -u price-tracker -f

🔧 Configuration files:
   - $APP_DIR/.env (API keys and settings)
   - $APP_DIR/products.json (products to monitor)

📚 View README.md for detailed instructions!
"
