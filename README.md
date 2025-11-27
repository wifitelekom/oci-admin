# 🚀 OCI Admin Panel - Multi-Account Manager

Oracle Cloud "Out of Capacity" hatasını aşmak için geliştirilmiş, çoklu hesap destekli modern web yönetim paneli.

![Version](https://img.shields.io/badge/Version-2.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.8+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📋 İçindekiler

- [Özellikler](#-özellikler)
- [Gereksinimler](#-gereksinimler)
- [Kurulum](#-kurulum)
- [Kullanım](#-kullanım)
- [Yapılandırma](#%EF%B8%8F-yapılandırma)
- [API Endpoints](#-api-endpoints)
- [Desteklenen Bölgeler](#-desteklenen-bölgeler)
- [Sorun Giderme](#-sorun-giderme)
- [SSS](#-sss)

---

## ✨ Özellikler

### 🔥 Temel Özellikler

| Özellik | Açıklama |
|---------|----------|
| **Çoklu Hesap Desteği** | Sınırsız OCI hesabı ekleyebilme |
| **Bağımsız Bot Yönetimi** | Her hesap için ayrı bot çalıştırma |
| **Gerçek Zamanlı Loglar** | WebSocket ile anlık log takibi |
| **Telegram Bildirimleri** | Instance oluştuğunda anında bildirim |
| **Adaptif Bekleme Süresi** | Rate limit durumuna göre otomatik ayarlama |
| **Rastgele Bekleme** | Ban riskini azaltmak için rastgele aralıklar |

### 🎨 Arayüz Özellikleri

- Modern dark theme tasarım
- Glass-morphism efektleri
- Responsive (mobil uyumlu)
- Gerçek zamanlı durum güncellemeleri
- Kolay kullanımlı hesap yönetimi

### 🛡️ Güvenlik

- Şifreli admin girişi
- Session tabanlı kimlik doğrulama
- Güvenli API endpoint'leri

---

## 📦 Gereksinimler

- **İşletim Sistemi:** Linux (Ubuntu, Debian, CentOS, vb.)
- **Python:** 3.8 veya üzeri
- **RAM:** Minimum 512 MB
- **Disk:** Minimum 100 MB
- **Ağ:** İnternet bağlantısı

### Python Paketleri

```
flask
flask-socketio
python-socketio
oci
pyTelegramBotAPI
python-dotenv
simple-websocket
```

---

## 🔧 Kurulum

### Hızlı Kurulum (Önerilen)

```bash
# 1. Dosyaları /root/oci-admin-panel dizinine çıkar
cd /root/oci-admin-panel

# 2. Kurulum scriptini çalıştır
chmod +x install-service.sh
./install-service.sh

# 3. Servisi başlat
systemctl start oci-panel
```

### Manuel Kurulum

```bash
# 1. Dizine git
cd /root/oci-admin-panel

# 2. Virtual environment oluştur
python3 -m venv venv
source venv/bin/activate

# 3. Paketleri yükle
pip install flask flask-socketio python-socketio oci pyTelegramBotAPI python-dotenv simple-websocket

# 4. Dizinleri oluştur
mkdir -p accounts

# 5. Çalıştır
python app.py
```

### Systemd Servisi (Manuel)

```bash
# Service dosyasını oluştur
cat > /etc/systemd/system/oci-panel.service << 'EOF'
[Unit]
Description=OCI Admin Panel - Multi-Account Manager
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/oci-admin-panel
Environment="PATH=/root/oci-admin-panel/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/root/oci-admin-panel/venv/bin/python /root/oci-admin-panel/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Servisi etkinleştir ve başlat
systemctl daemon-reload
systemctl enable oci-panel
systemctl start oci-panel
```

---

## 🖥️ Kullanım

### Servis Komutları

| Komut | Açıklama |
|-------|----------|
| `systemctl start oci-panel` | Servisi başlat |
| `systemctl stop oci-panel` | Servisi durdur |
| `systemctl restart oci-panel` | Servisi yeniden başlat |
| `systemctl status oci-panel` | Servis durumunu göster |
| `systemctl enable oci-panel` | Otomatik başlatmayı etkinleştir |
| `systemctl disable oci-panel` | Otomatik başlatmayı devre dışı bırak |
| `journalctl -u oci-panel -f` | Canlı logları izle |
| `journalctl -u oci-panel -n 100` | Son 100 log satırını göster |

### Web Panel Erişimi

```
URL:       http://SUNUCU_IP:5000
Kullanıcı: admin
Şifre:     admin123
```

### İlk Kullanım Adımları

1. **Giriş Yap:** Web panele admin/admin123 ile giriş yap
2. **Şifre Değiştir:** Settings → Admin Credentials
3. **Hesap Ekle:** Accounts → Add Account
4. **OCI Bilgilerini Gir:**
   - Tenancy OCID
   - User OCID
   - Key Fingerprint
   - Private Key dosya yolu
   - Subnet OCID
   - Image OCID
   - SSH Public Key
5. **Bot'u Başlat:** Dashboard veya Accounts sayfasından "Start" butonuna tıkla

---

## ⚙️ Yapılandırma

### Ana Yapılandırma (.env)

```bash
# Admin Panel Ayarları
WEB_USERNAME=admin
WEB_PASSWORD=admin123
SECRET_KEY=rastgele-gizli-anahtar
ACCOUNTS_DIR=./accounts
WEB_HOST=0.0.0.0
WEB_PORT=5000
```

### Hesap Yapılandırması (accounts/account_xxx.env)

```bash
# Hesap Bilgisi
ACCOUNT_NAME=Hesabım

# OCI API Credentials
OCI_REGION=eu-frankfurt-1
OCI_TENANCY_ID=ocid1.tenancy.oc1..xxxxx
OCI_USER_ID=ocid1.user.oc1..xxxxx
OCI_KEY_FINGERPRINT=xx:xx:xx:xx:xx:xx:xx:xx
OCI_PRIVATE_KEY_FILENAME=/root/keys/private-key.pem

# Network
OCI_SUBNET_ID=ocid1.subnet.oc1..xxxxx
OCI_AVAILABILITY_DOMAIN=

# Instance Ayarları
OCI_SHAPE=VM.Standard.A1.Flex
OCI_OCPUS=4
OCI_MEMORY_IN_GBS=24
OCI_IMAGE_ID=ocid1.image.oc1..xxxxx
OCI_SSH_PUBLIC_KEY=ssh-rsa AAAA...
OCI_DISPLAY_NAME=my-instance

# Retry Ayarları
OCI_RETRY_INTERVAL=30
OCI_MIN_RETRY_INTERVAL=10
OCI_MAX_RETRY_INTERVAL=120

# Telegram (Opsiyonel)
TELEGRAM_BOT_API_KEY=123456789:ABC...
TELEGRAM_USER_ID=123456789
```

### Retry Ayarları Açıklaması

| Parametre | Varsayılan | Açıklama |
|-----------|------------|----------|
| `OCI_RETRY_INTERVAL` | 30 | Başlangıç bekleme süresi (saniye) |
| `OCI_MIN_RETRY_INTERVAL` | 10 | Minimum bekleme süresi (saniye) |
| `OCI_MAX_RETRY_INTERVAL` | 120 | Rate limit durumunda maksimum süre (saniye) |

> **Not:** Bekleme süreleri `MIN` ve mevcut `INTERVAL` arasında rastgele seçilir. Bu, ban riskini azaltır.

### Önerilen Retry Değerleri

| Profil | Initial | Min | Max | Açıklama |
|--------|---------|-----|-----|----------|
| Güvenli | 30 | 15 | 120 | Ban riski düşük |
| Normal | 20 | 10 | 90 | Dengeli |
| Agresif | 10 | 5 | 60 | Hızlı ama riskli |

---

## 🌍 Desteklenen Bölgeler

### Avrupa
| Bölge | Kod |
|-------|-----|
| Frankfurt | eu-frankfurt-1 |
| Amsterdam | eu-amsterdam-1 |
| Zurich | eu-zurich-1 |
| Madrid | eu-madrid-1 |
| Marseille | eu-marseille-1 |
| Milan | eu-milan-1 |
| Paris | eu-paris-1 |
| Stockholm | eu-stockholm-1 |

### Amerika
| Bölge | Kod |
|-------|-----|
| Ashburn | us-ashburn-1 |
| Phoenix | us-phoenix-1 |
| San Jose | us-sanjose-1 |
| Chicago | us-chicago-1 |
| Toronto | ca-toronto-1 |
| Montreal | ca-montreal-1 |
| Sao Paulo | sa-saopaulo-1 |
| Santiago | sa-santiago-1 |
| Vinhedo | sa-vinhedo-1 |

### Asya Pasifik
| Bölge | Kod |
|-------|-----|
| Tokyo | ap-tokyo-1 |
| Osaka | ap-osaka-1 |
| Seoul | ap-seoul-1 |
| Chuncheon | ap-chuncheon-1 |
| Singapore | ap-singapore-1 |
| Sydney | ap-sydney-1 |
| Melbourne | ap-melbourne-1 |
| Mumbai | ap-mumbai-1 |
| Hyderabad | ap-hyderabad-1 |

### Diğer
| Bölge | Kod |
|-------|-----|
| London | uk-london-1 |
| Cardiff | uk-cardiff-1 |
| Jeddah | me-jeddah-1 |
| Dubai | me-dubai-1 |
| Abu Dhabi | me-abudhabi-1 |
| Johannesburg | af-johannesburg-1 |
| Jerusalem | il-jerusalem-1 |

---

## 🔌 API Endpoints

### Genel

| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/api/status` | GET | Genel durum bilgisi |
| `/api/dashboard-stats` | GET | Dashboard istatistikleri |
| `/api/logs` | GET | Tüm hesapların logları |
| `/api/settings` | GET/POST | Panel ayarları |

### Hesap Yönetimi

| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/api/accounts` | GET | Tüm hesapları listele |
| `/api/accounts/create` | POST | Yeni hesap oluştur |
| `/api/accounts/<id>` | GET | Hesap detayları |
| `/api/accounts/<id>` | DELETE | Hesap sil |
| `/api/accounts/<id>/settings` | POST | Hesap ayarlarını güncelle |
| `/api/accounts/<id>/test` | GET | Bağlantı testi |

### Bot Kontrolü

| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/api/accounts/<id>/bot/start` | POST | Bot'u başlat |
| `/api/accounts/<id>/bot/stop` | POST | Bot'u durdur |
| `/api/bot/start-all` | POST | Tüm botları başlat |
| `/api/bot/stop-all` | POST | Tüm botları durdur |

### Kaynak Bilgileri

| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/api/accounts/<id>/instances` | GET | Instance listesi |
| `/api/accounts/<id>/storage` | GET | Storage kullanımı |
| `/api/accounts/<id>/compute` | GET | Compute limitleri |
| `/api/accounts/<id>/availability-domains` | GET | Availability Domain listesi |
| `/api/accounts/<id>/logs` | GET | Hesaba özel loglar |

---

## 🔧 Sorun Giderme

### Servis Başlamıyor

```bash
# Log kontrol et
journalctl -u oci-panel -n 50

# Manuel çalıştır
cd /root/oci-admin-panel
source venv/bin/activate
python app.py
```

### Port Zaten Kullanımda

```bash
# Portu kullanan işlemi bul
lsof -i :5000

# veya farklı port kullan (.env dosyasında)
WEB_PORT=8080
```

### OCI Bağlantı Hatası

1. Private key dosya yolunu kontrol et
2. Fingerprint'in doğru olduğundan emin ol
3. API key'in OCI Console'da aktif olduğunu kontrol et

### Rate Limit (429) Hatası

Retry ayarlarını artır:
```bash
OCI_RETRY_INTERVAL=60
OCI_MIN_RETRY_INTERVAL=30
OCI_MAX_RETRY_INTERVAL=180
```

### WebSocket Bağlantı Sorunu

```bash
# simple-websocket paketini yükle
source venv/bin/activate
pip install simple-websocket
systemctl restart oci-panel
```

---

## ❓ SSS

### OCI API Key nasıl oluşturulur?

1. OCI Console → Identity → Users → Kullanıcınız
2. API Keys → Add API Key
3. Generate API Key Pair seçin
4. Private key'i indirin
5. Fingerprint'i not edin

### Telegram Bot nasıl kurulur?

1. [@BotFather](https://t.me/BotFather)'a mesaj at
2. `/newbot` komutu ile yeni bot oluştur
3. Bot token'ı kaydet
4. [@userinfobot](https://t.me/userinfobot)'tan User ID'ni öğren
5. Panel'de bu bilgileri gir

### Image OCID nasıl bulunur?

1. [Oracle Images](https://docs.oracle.com/en-us/iaas/images/) sayfasına git
2. Bölgeni ve istediğin OS'i seç
3. OCID'yi kopyala

### Free Tier limitleri nedir?

| Kaynak | A1.Flex (ARM) | E2.1.Micro (AMD) |
|--------|---------------|------------------|
| OCPU | 4 | 2 (her biri 1/8) |
| RAM | 24 GB | 2 GB (her biri 1 GB) |
| Storage | 200 GB | 200 GB |
| Instance | 1-4 arası | 2 |

### Birden fazla instance oluşturabilir miyim?

Evet! Her hesap için ayrı `OCI_DISPLAY_NAME` kullanarak birden fazla bot çalıştırabilirsin.

---

## 📂 Dosya Yapısı

```
/root/oci-admin-panel/
├── app.py                 # Ana uygulama
├── requirements.txt       # Python bağımlılıkları
├── .env                   # Ana yapılandırma
├── start.sh              # Hızlı başlatma scripti
├── install-service.sh    # Servis kurulum scripti
├── oci-panel.service     # Systemd servis dosyası
├── accounts/             # Hesap .env dosyaları
│   ├── account_xxx.env
│   └── account_yyy.env
├── templates/            # HTML şablonları
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── accounts.html
│   ├── account_detail.html
│   ├── account_settings.html
│   ├── logs.html
│   └── settings.html
└── venv/                 # Python virtual environment
```

---

## 📄 Lisans

Bu proje MIT lisansı altında sunulmaktadır.

---

## ⚠️ Sorumluluk Reddi

Bu araç eğitim amaçlıdır. Oracle Cloud'un Hizmet Şartlarına uygun şekilde kullanın. Yazarlar herhangi bir kötüye kullanım veya ihlalden sorumlu değildir.

---

**Oracle Cloud Free Tier topluluğu için ❤️ ile yapıldı**
