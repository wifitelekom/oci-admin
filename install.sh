#!/bin/bash

# ============================================
# OCI Admin Panel - Installation Script
# ============================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Banner
echo -e "${PURPLE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║     ⚡ OCI Admin Panel - Multi-Account Manager ⚡        ║"
echo "║                                                           ║"
echo "║           Oracle Cloud Instance Controller                ║"
echo "║                      v2.0.0                               ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Running as root. Consider using a non-root user.${NC}"
fi

# Detect OS
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
    elif [ -f /etc/debian_version ]; then
        OS="debian"
    elif [ -f /etc/redhat-release ]; then
        OS="centos"
    else
        OS="unknown"
    fi
    echo -e "${CYAN}📦 Detected OS: $OS${NC}"
}

# Install dependencies based on OS
install_dependencies() {
    echo -e "\n${BLUE}📥 Installing system dependencies...${NC}"
    
    case $OS in
        ubuntu|debian)
            apt-get update -qq
            apt-get install -y -qq python3 python3-pip python3-venv git curl wget > /dev/null 2>&1
            ;;
        centos|rhel|fedora)
            yum install -y python3 python3-pip git curl wget > /dev/null 2>&1
            ;;
        alpine)
            apk add --no-cache python3 py3-pip git curl wget > /dev/null 2>&1
            ;;
        *)
            echo -e "${YELLOW}⚠️  Unknown OS. Please install Python 3, pip, and venv manually.${NC}"
            ;;
    esac
    
    echo -e "${GREEN}✅ System dependencies installed${NC}"
}

# Check Python version
check_python() {
    echo -e "\n${BLUE}🐍 Checking Python...${NC}"
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        echo -e "${GREEN}✅ Python $PYTHON_VERSION found${NC}"
        
        # Check if version is >= 3.8
        MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        
        if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 8 ]); then
            echo -e "${RED}❌ Python 3.8+ required. Found $PYTHON_VERSION${NC}"
            exit 1
        fi
    else
        echo -e "${RED}❌ Python 3 not found. Installing...${NC}"
        install_dependencies
    fi
}

# Setup installation directory
setup_directory() {
    echo -e "\n${BLUE}📁 Setting up installation directory...${NC}"
    
    INSTALL_DIR="${1:-/opt/oci-admin-panel}"
    
    if [ -d "$INSTALL_DIR" ]; then
        echo -e "${YELLOW}⚠️  Directory $INSTALL_DIR already exists.${NC}"
        read -p "Overwrite? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${RED}Installation cancelled.${NC}"
            exit 1
        fi
        rm -rf "$INSTALL_DIR"
    fi
    
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    
    echo -e "${GREEN}✅ Directory created: $INSTALL_DIR${NC}"
}

# Download or copy files
download_files() {
    echo -e "\n${BLUE}📥 Setting up application files...${NC}"
    
    # Check if we're running from the project directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    if [ -f "$SCRIPT_DIR/app.py" ]; then
        echo -e "${CYAN}   Copying files from local directory...${NC}"
        cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/" 2>/dev/null || true
        cp -r "$SCRIPT_DIR"/.env* "$INSTALL_DIR/" 2>/dev/null || true
    else
        echo -e "${CYAN}   Downloading from repository...${NC}"
        # If hosted on GitHub, download from there
        # For now, we'll create the files
        echo -e "${YELLOW}⚠️  Please copy the project files to $INSTALL_DIR${NC}"
    fi
    
    echo -e "${GREEN}✅ Files ready${NC}"
}

# Create virtual environment
create_venv() {
    echo -e "\n${BLUE}🔧 Creating virtual environment...${NC}"
    
    python3 -m venv venv
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip -q
    
    echo -e "${GREEN}✅ Virtual environment created${NC}"
}

# Install Python packages
install_packages() {
    echo -e "\n${BLUE}📦 Installing Python packages...${NC}"
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt -q
        echo -e "${GREEN}✅ Python packages installed${NC}"
    else
        echo -e "${YELLOW}⚠️  requirements.txt not found. Installing manually...${NC}"
        pip install flask flask-socketio python-socketio python-engineio oci pyTelegramBotAPI python-dotenv werkzeug simple-websocket -q
        echo -e "${GREEN}✅ Python packages installed${NC}"
    fi
}

# Create directories
create_directories() {
    echo -e "\n${BLUE}📁 Creating directories...${NC}"
    
    mkdir -p accounts
    mkdir -p logs
    
    echo -e "${GREEN}✅ Directories created${NC}"
}

# Create default .env file
create_env() {
    echo -e "\n${BLUE}⚙️  Creating configuration...${NC}"
    
    if [ ! -f ".env" ]; then
        SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
        
        cat > .env << EOF
# OCI Admin Panel Configuration
WEB_USERNAME=admin
WEB_PASSWORD=admin123
SECRET_KEY=$SECRET_KEY
ACCOUNTS_DIR=./accounts
WEB_HOST=0.0.0.0
WEB_PORT=5000
DEBUG=false
EOF
        echo -e "${GREEN}✅ Configuration file created${NC}"
    else
        echo -e "${CYAN}   Using existing .env file${NC}"
    fi
}

# Create systemd service
create_service() {
    echo -e "\n${BLUE}🔧 Creating systemd service...${NC}"
    
    read -p "Create systemd service for auto-start? (y/n): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cat > /etc/systemd/system/oci-admin-panel.service << EOF
[Unit]
Description=OCI Admin Panel - Multi-Account Manager
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
ExecStart=$INSTALL_DIR/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
        
        systemctl daemon-reload
        systemctl enable oci-admin-panel
        
        echo -e "${GREEN}✅ Systemd service created and enabled${NC}"
        echo -e "${CYAN}   Use: systemctl start oci-admin-panel${NC}"
    fi
}

# Configure firewall
configure_firewall() {
    echo -e "\n${BLUE}🔥 Configuring firewall...${NC}"
    
    read -p "Open port 5000 in firewall? (y/n): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if command -v ufw &> /dev/null; then
            ufw allow 5000/tcp > /dev/null 2>&1
            echo -e "${GREEN}✅ UFW: Port 5000 opened${NC}"
        elif command -v firewall-cmd &> /dev/null; then
            firewall-cmd --permanent --add-port=5000/tcp > /dev/null 2>&1
            firewall-cmd --reload > /dev/null 2>&1
            echo -e "${GREEN}✅ Firewalld: Port 5000 opened${NC}"
        elif command -v iptables &> /dev/null; then
            iptables -A INPUT -p tcp --dport 5000 -j ACCEPT
            echo -e "${GREEN}✅ iptables: Port 5000 opened${NC}"
        else
            echo -e "${YELLOW}⚠️  No firewall detected${NC}"
        fi
    fi
}

# Set credentials
set_credentials() {
    echo -e "\n${BLUE}🔐 Setting admin credentials...${NC}"
    
    read -p "Set custom admin username? (y/n): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Username: " NEW_USERNAME
        read -s -p "Password: " NEW_PASSWORD
        echo
        
        sed -i "s/WEB_USERNAME=.*/WEB_USERNAME=$NEW_USERNAME/" .env
        sed -i "s/WEB_PASSWORD=.*/WEB_PASSWORD=$NEW_PASSWORD/" .env
        
        echo -e "${GREEN}✅ Credentials updated${NC}"
    else
        echo -e "${CYAN}   Using default: admin / admin123${NC}"
    fi
}

# Print completion message
print_completion() {
    IP_ADDR=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")
    
    echo -e "\n${GREEN}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║                                                           ║"
    echo "║          ✅ Installation Complete!                        ║"
    echo "║                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    echo -e "${CYAN}📍 Installation Directory:${NC} $INSTALL_DIR"
    echo -e "${CYAN}🌐 Access URL:${NC} http://$IP_ADDR:5000"
    echo -e "${CYAN}👤 Default Login:${NC} admin / admin123"
    echo ""
    echo -e "${YELLOW}📋 Quick Commands:${NC}"
    echo ""
    echo -e "   ${PURPLE}Start manually:${NC}"
    echo "   cd $INSTALL_DIR && source venv/bin/activate && python app.py"
    echo ""
    
    if [ -f /etc/systemd/system/oci-admin-panel.service ]; then
        echo -e "   ${PURPLE}Using systemd:${NC}"
        echo "   systemctl start oci-admin-panel"
        echo "   systemctl stop oci-admin-panel"
        echo "   systemctl status oci-admin-panel"
        echo "   journalctl -u oci-admin-panel -f"
        echo ""
    fi
    
    echo -e "${YELLOW}📝 Next Steps:${NC}"
    echo "   1. Access the web panel at http://$IP_ADDR:5000"
    echo "   2. Login with admin credentials"
    echo "   3. Go to 'Accounts' and add your OCI accounts"
    echo "   4. Configure OCI API credentials for each account"
    echo "   5. Start the bots!"
    echo ""
}

# Start application
start_app() {
    echo -e "\n${BLUE}🚀 Starting application...${NC}"
    
    read -p "Start the application now? (y/n): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ -f /etc/systemd/system/oci-admin-panel.service ]; then
            systemctl start oci-admin-panel
            echo -e "${GREEN}✅ Service started${NC}"
        else
            echo -e "${CYAN}Starting in foreground mode...${NC}"
            echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
            echo ""
            source venv/bin/activate
            python app.py
        fi
    fi
}

# Main installation function
main() {
    detect_os
    
    # Check if we should install dependencies
    if [ "$1" != "--skip-deps" ]; then
        check_python
    fi
    
    # Get installation directory
    if [ -n "$2" ]; then
        INSTALL_DIR="$2"
    else
        read -p "Installation directory [/opt/oci-admin-panel]: " INSTALL_DIR
        INSTALL_DIR="${INSTALL_DIR:-/opt/oci-admin-panel}"
    fi
    
    setup_directory "$INSTALL_DIR"
    download_files
    create_venv
    install_packages
    create_directories
    create_env
    set_credentials
    
    # Only create service if running as root
    if [ "$EUID" -eq 0 ]; then
        create_service
        configure_firewall
    fi
    
    print_completion
    start_app
}

# Run main function
main "$@"
