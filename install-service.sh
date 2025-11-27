#!/bin/bash

# ============================================
# OCI Admin Panel - Service Installer
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

INSTALL_DIR="/root/oci-admin-panel"
SERVICE_NAME="oci-panel"

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════╗"
echo "║   OCI Admin Panel - Service Installer      ║"
echo "╚════════════════════════════════════════════╝"
echo -e "${NC}"

# Check root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Please run as root${NC}"
    exit 1
fi

# Check if directory exists
if [ ! -d "$INSTALL_DIR" ]; then
    echo -e "${RED}❌ Directory $INSTALL_DIR not found${NC}"
    exit 1
fi

cd "$INSTALL_DIR"

# Create venv if not exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Install packages
echo -e "${YELLOW}Installing Python packages...${NC}"
source venv/bin/activate
pip install flask flask-socketio python-socketio oci pyTelegramBotAPI python-dotenv simple-websocket -q

# Create accounts directory
mkdir -p accounts

# Create .env if not exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating configuration...${NC}"
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

# Copy service file
echo -e "${YELLOW}Installing systemd service...${NC}"
cp oci-panel.service /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

# Enable service
systemctl enable $SERVICE_NAME

echo -e "${GREEN}"
echo "╔════════════════════════════════════════════╗"
echo "║         ✅ Installation Complete!          ║"
echo "╚════════════════════════════════════════════╝"
echo -e "${NC}"

IP_ADDR=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo -e "${CYAN}Commands:${NC}"
echo ""
echo -e "  ${GREEN}Start:${NC}    systemctl start $SERVICE_NAME"
echo -e "  ${RED}Stop:${NC}     systemctl stop $SERVICE_NAME"
echo -e "  ${YELLOW}Restart:${NC}  systemctl restart $SERVICE_NAME"
echo -e "  ${CYAN}Status:${NC}   systemctl status $SERVICE_NAME"
echo -e "  ${CYAN}Logs:${NC}     journalctl -u $SERVICE_NAME -f"
echo ""
echo -e "${CYAN}Access:${NC}   http://$IP_ADDR:5000"
echo -e "${CYAN}Login:${NC}    admin / admin123"
echo ""

read -p "Start service now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    systemctl start $SERVICE_NAME
    echo -e "${GREEN}✅ Service started!${NC}"
    systemctl status $SERVICE_NAME --no-pager
fi
