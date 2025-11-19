# RuuviTag Logger auf Raspberry Pi Zero 2W

## 🚀 Perfekt geeignet für dauerhaften Betrieb!

Der Pi Zero 2W ist sogar **ideal** für dieses Projekt:
- ✅ Eingebautes Bluetooth 4.2 BLE
- ✅ WiFi für Web-Dashboard-Zugriff
- ✅ Sehr geringer Stromverbrauch (~2-3W)
- ✅ Klein und diskret platzierbar
- ✅ Günstig für dedizierte Sensorstationen

## 📋 Setup-Anleitung

### 1. Raspberry Pi OS vorbereiten
```bash
# Auf dem Pi Zero 2W:
sudo apt update
sudo apt upgrade -y

# Bluetooth-Tools installieren
sudo apt install bluetooth bluez python3-pip python3-venv git -y

# Python Virtual Environment erstellen
cd ~
mkdir ruuvi_logger
cd ruuvi_logger
python3 -m venv venv
source venv/bin/activate
```

### 2. Python-Abhängigkeiten installieren
```bash
# Im Virtual Environment:
pip install bleak flask

# Testen ob Bluetooth funktioniert:
python3 -c "import bleak; print('✅ BLE Support verfügbar')"
```

### 3. Projektdateien übertragen

**Option A: Via SCP vom Pi 5:**
```bash
# Auf dem Pi 5 (im ruuviLog Verzeichnis):
scp -r * pi@[PI_ZERO_IP]:~/ruuvi_logger/
```

**Option B: Via GitHub/USB oder direkt kopieren**

### 4. Bluetooth-Berechtigungen einrichten
```bash
# Benutzer zur bluetooth-Gruppe hinzufügen:
sudo usermod -a -G bluetooth $USER

# Nach Neuanmeldung/Neustart testen:
hciconfig
```

### 5. System für headless Betrieb optimieren

#### Systemd Services erstellen:
```bash
# Logger Service
sudo tee /etc/systemd/system/ruuvi-logger.service << EOF
[Unit]
Description=RuuviTag BLE Logger
After=bluetooth.service network.target
Wants=bluetooth.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/ruuvi_logger
Environment=PATH=/home/pi/ruuvi_logger/venv/bin
ExecStart=/home/pi/ruuvi_logger/venv/bin/python3 ruuvi_logger_db.py --min-interval 10
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Web-Server Service
sudo tee /etc/systemd/system/ruuvi-web.service << EOF
[Unit]
Description=RuuviTag Web Dashboard
After=network.target ruuvi-logger.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/ruuvi_logger
Environment=PATH=/home/pi/ruuvi_logger/venv/bin
ExecStart=/home/pi/ruuvi_logger/venv/bin/python3 web_server.py --host 0.0.0.0
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

#### Services aktivieren:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ruuvi-logger.service
sudo systemctl enable ruuvi-web.service
sudo systemctl start ruuvi-logger.service
sudo systemctl start ruuvi-web.service

# Status prüfen:
sudo systemctl status ruuvi-logger.service
sudo systemctl status ruuvi-web.service
```

## ⚡ Performance-Optimierungen für Pi Zero 2W

### 1. Angepasste Logger-Einstellungen
```bash
# Längere Intervalle für weniger CPU-Last:
python3 ruuvi_logger_db.py --min-interval 15.0

# Oder in der Service-Datei anpassen
```

### 2. Web-Server Optimierung
Für bessere Performance auf dem Pi Zero 2W:

```python
# In web_server.py am Ende der main() Funktion:
app.run(
    host=args.host, 
    port=args.port, 
    debug=False,  # Debug aus für bessere Performance
    threaded=True,
    processes=1   # Nur ein Prozess auf Pi Zero
)
```

### 3. Datenbank-Bereinigung automatisieren
```bash
# Cron-Job für wöchentliche Bereinigung alter Daten:
crontab -e

# Folgende Zeile hinzufügen (jeden Sonntag um 3 Uhr):
0 3 * * 0 /home/pi/ruuvi_logger/venv/bin/python3 -c "from database import RuuviDatabase; db = RuuviDatabase('/home/pi/ruuvi_logger/ruuvi_data.db'); db.cleanup_old_data(30)"
```

## 🌐 Zugriff auf das Dashboard

Nach dem Setup können Sie von jedem Gerät im Netzwerk zugreifen:
```
http://[PI_ZERO_IP]:5000
```

**IP-Adresse finden:**
```bash
hostname -I
```

## 🔧 Troubleshooting Pi Zero 2W

### Bluetooth-Probleme:
```bash
# Bluetooth-Status prüfen:
sudo systemctl status bluetooth
hciconfig -a

# Bluetooth neu starten:
sudo systemctl restart bluetooth
```

### Performance-Monitoring:
```bash
# CPU und RAM überwachen:
htop

# Service-Logs anzeigen:
journalctl -u ruuvi-logger.service -f
journalctl -u ruuvi-web.service -f
```

### Häufige Anpassungen:
1. **Längere Log-Intervalle** (--min-interval 15-30)
2. **Kleinere Batch-Sizes** in der Datenbank
3. **Weniger Chart-Updates** im Frontend (60s statt 30s)

## 💡 Produktions-Tipps

### Stromsparen:
```bash
# HDMI ausschalten (wenn headless):
sudo tvservice -o

# USB-Power reduzieren:
echo '1-1' | sudo tee /sys/bus/usb/drivers/usb/unbind
```

### Monitoring:
```bash
# Temperatur überwachen:
vcgencmd measure_temp

# System-Status:
df -h  # Speicherplatz
free -h  # RAM-Nutzung
```

## 🎯 Vorteile Pi Zero 2W vs Pi 5

| Feature | Pi Zero 2W | Pi 5 |
|---------|------------|------|
| **Stromverbrauch** | ~2-3W ⭐ | ~8-15W |
| **Größe** | 65×30mm ⭐ | 85×56mm |
| **Preis** | ~15€ ⭐ | ~100€ |
| **BLE Performance** | Identisch ✅ | Identisch ✅ |
| **Web-Performance** | Gut | Exzellent ⭐ |
| **24/7 Betrieb** | Perfekt ⭐ | Überdimensioniert |

**➡️ Der Pi Zero 2W ist sogar die bessere Wahl für dauerhafte RuuviTag-Stationen!**