# 🚀 Oracle Cloud Instance Manager

Modern, feature-rich web admin panel for managing Oracle Cloud "Out of Capacity" instance spawning automation.

![Dashboard Preview](https://img.shields.io/badge/Status-Active-success)
![Python](https://img.shields.io/badge/Python-3.9+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Features

- 🎨 **Modern Dark UI** - Beautiful, responsive design with glass-morphism effects
- 📊 **Real-time Dashboard** - Live monitoring of instances, storage, and compute resources
- 🤖 **Bot Control** - Start/stop the spawning bot directly from the web interface
- 📝 **Live Logs** - Real-time log streaming via WebSocket
- ⚙️ **Settings Panel** - Easy configuration of OCI credentials and instance settings
- 📱 **Telegram Notifications** - Get notified when your instance is created
- 🔐 **Secure Authentication** - Password-protected admin panel
- 🐳 **Docker Ready** - Easy deployment with Docker and Docker Compose

## 🖥️ Screenshots

### Dashboard
- Real-time instance and resource monitoring
- Bot status and control
- Storage usage visualization
- Recent logs preview

### Instances
- List all OCI instances
- View instance details (shape, OCPUs, memory, status)
- Availability domains overview

### Logs
- Real-time log streaming
- Filter by log level
- Search functionality
- Auto-scroll toggle

### Settings
- OCI API credentials configuration
- Instance settings (shape, OCPUs, memory, image)
- Telegram notification setup
- Admin credential management

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone or download the files
git clone <repository-url>
cd oci-admin-panel

# Copy and configure environment
cp .env.example .env
nano .env  # Edit with your settings

# Run with Docker Compose
docker-compose up -d

# Access at http://localhost:5000
```

### Option 2: Manual Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
nano .env  # Edit with your settings

# Run the application
python app.py

# Access at http://localhost:5000
```

## ⚙️ Configuration

### OCI Setup

1. **Generate API Key**
   - Go to OCI Console → Identity → Users → Your User
   - Click "API Keys" → "Add API Key"
   - Download the private key and note the fingerprint

2. **Get Required OCIDs**
   - Tenancy OCID: OCI Console → Administration → Tenancy Details
   - User OCID: OCI Console → Identity → Users → Your User
   - Subnet OCID: OCI Console → Networking → Virtual Cloud Networks → Your VCN → Subnets

3. **Find Image OCID**
   - Visit: https://docs.oracle.com/en-us/iaas/images/
   - Select your region and desired OS image

### Telegram Setup (Optional)

1. Create a bot with [@BotFather](https://t.me/BotFather)
2. Get your User ID from [@userinfobot](https://t.me/userinfobot)
3. Enter both in the Settings → Telegram section

## 📁 Project Structure

```
oci-admin-panel/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── Dockerfile          # Docker build file
├── docker-compose.yml  # Docker Compose config
├── .env.example        # Environment template
├── .env                # Your configuration (gitignored)
├── config              # OCI config file (optional)
└── templates/
    ├── base.html       # Base template with sidebar
    ├── login.html      # Login page
    ├── dashboard.html  # Main dashboard
    ├── instances.html  # Instances management
    ├── logs.html       # Real-time logs
    └── settings.html   # Configuration page
```

## 🔒 Security Notes

- Change the default admin credentials immediately
- Use a strong `SECRET_KEY` in production
- Keep your OCI private key secure
- Consider using HTTPS with a reverse proxy (nginx/traefik)

## 🐳 Docker Commands

```bash
# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Restart
docker-compose restart
```

## 🛠️ Development

```bash
# Run in development mode
DEBUG=true python app.py

# The app will auto-reload on code changes
```

## 📝 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Get bot status |
| `/api/instances` | GET | List all instances |
| `/api/storage` | GET | Get storage info |
| `/api/compute` | GET | Get compute limits |
| `/api/availability-domains` | GET | List ADs |
| `/api/bot/start` | POST | Start the bot |
| `/api/bot/stop` | POST | Stop the bot |
| `/api/logs` | GET | Get recent logs |
| `/api/settings` | GET/POST | Get/update settings |

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This tool is for educational purposes. Use responsibly and in accordance with Oracle Cloud's Terms of Service. The authors are not responsible for any misuse or violations.

---

Made with ❤️ for the Oracle Cloud Free Tier community
