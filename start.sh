#!/bin/bash

# ============================================
# OCI Admin Panel - Quick Start Script
# ============================================

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${CYAN}🚀 OCI Admin Panel - Quick Start${NC}"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Always check and install packages
echo -e "${YELLOW}Checking packages...${NC}"
pip install flask flask-socketio python-socketio oci pyTelegramBotAPI python-dotenv simple-websocket -q 2>/dev/null

if [ $? -ne 0 ]; then
    echo -e "${RED}Package installation failed. Trying with --break-system-packages...${NC}"
    pip install flask flask-socketio python-socketio oci pyTelegramBotAPI python-dotenv simple-websocket --break-system-packages -q
fi

# Create accounts directory
mkdir -p accounts

# Create .env if not exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating default configuration...${NC}"
    SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
    cat > .env << EOF
WEB_USERNAME=admin
WEB_PASSWORD=admin123
SECRET_KEY=$SECRET_KEY
ACCOUNTS_DIR=./accounts
WEB_HOST=0.0.0.0
WEB_PORT=5000
EOF
fi

# Get IP
IP_ADDR=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo ""
echo -e "${GREEN}✅ Ready!${NC}"
echo -e "${CYAN}🌐 Access: http://$IP_ADDR:5000${NC}"
echo -e "${CYAN}👤 Login: admin / admin123${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Start
python app.py
