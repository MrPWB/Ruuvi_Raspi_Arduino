# RuuviTag Web-Visualisierung System

Ein komplettes System zur Erfassung und Visualisierung von RuuviTag-Sensordaten mit Web-Dashboard.

## 🚀 Features

- **Real-time Datenerfassung** von RuuviTag-Sensoren via Bluetooth LE
- **SQLite-Datenbank** mit optimierter Concurrent-Access-Unterstützung
- **Web-Dashboard** mit interaktiven Charts und Live-Updates
- **Multi-Device-Support** für mehrere RuuviTags gleichzeitig
- **Responsive Design** für Desktop und Mobile
- **Auto-Refresh** mit konfigurierbaren Zeitintervallen

## 📋 Voraussetzungen

### Hardware
- Raspberry Pi (oder Linux-System mit Bluetooth LE)
- Ein oder mehrere RuuviTag-Sensoren

### Software
```bash
# Python 3.8+
python3 --version

# Bluetooth-Unterstützung
sudo apt update
sudo apt install bluetooth bluez python3-pip
```

## 🛠️ Installation

### 1. Python-Abhängigkeiten installieren
```bash
pip3 install bleak flask sqlite3
```

### 2. Projektstruktur erstellen
```
ruuvi_project/
├── database.py          # Datenbank-Management
├── ruuvi_logger_db.py   # Sensor-Logger
├── web_server.py        # Flask Web-Server
└── templates/
    └── dashboard.html   # Web-Dashboard
```

### 3. Dateien erstellen
Kopieren Sie die bereitgestellten Code-Dateien in die entsprechenden Verzeichnisse:

1. **database.py** - Datenbank-Management
2. **ruuvi_logger_db.py** - Modifizierter Logger für Datenbank
3. **web_server.py** - Flask Web-Server
4. **templates/dashboard.html** - HTML-Dashboard

### 4. Templates-Verzeichnis erstellen
```bash
mkdir templates
# Kopieren Sie dashboard.html in das templates/ Verzeichnis
```

## 🎯 Verwendung

### 1. Daten-Logger starten
```bash
# Einfacher Start mit Standardeinstellungen
python3 ruuvi_logger_db.py

# Mit benutzerdefinierten Einstellungen
python3 ruuvi_logger_db.py --db /pfad/zur/datenbank.db --min-interval 10.0

# Bluetooth-Adapter spezifizieren
python3 ruuvi_logger_db.py --adapter hci0
```

**Logger-Optionen:**
- `--db`: Pfad zur SQLite-Datenbankdatei (Standard: `ruuvi_data.db`)
- `--adapter`: Bluetooth-Adapter (Standard: System-Standard)
- `--min-interval`: Mindestabstand zwischen Logs pro Gerät in Sekunden (Standard: 5.0)

### 2. Web-Server starten
```bash
# In einem separaten Terminal
python3 web_server.py
```

Der Web-Server läuft standardmäßig auf:
- **Lokal:** http://localhost:5000
- **Netzwerk:** http://[IHRE-IP]:5000

### 3. Dashboard öffnen
Öffnen Sie einen Webbrowser und navigieren Sie zur URL des Web-Servers.

## 🔧 Systemd-Service (Optional)

Für dauerhaften Betrieb können Sie Systemd-Services erstellen:

### Logger-Service
```bash
sudo nano /etc/systemd/system/ruuvi-logger.service
```

```ini
[Unit]
Description=RuuviTag Logger
After=bluetooth.service
Wants=bluetooth.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/ruuvi_project
ExecStart=/usr/bin/python3 ruuvi_logger_db.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Web-Server-Service
```bash
sudo nano /etc/systemd/system/ruuvi-web.service
```

```ini
[Unit]
Description=RuuviTag Web Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/ruuvi_project
ExecStart=/usr/bin/python3 web_server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Services aktivieren
```bash
sudo systemctl daemon-reload
sudo systemctl enable ruuvi-logger.service
sudo systemctl enable ruuvi-web.service
sudo systemctl start ruuvi-logger.service
sudo systemctl start ruuvi-web.service

# Status prüfen
sudo systemctl status ruuvi-logger.service
sudo systemctl status ruuvi-web.service
```

## 📊 Dashboard-Features

### Geräte-Übersicht
- Live-Status aller erkannten RuuviTags
- Letzte Aktualisierung und Gesamt-Messungen
- Online/Offline-Indikator

### Interaktive Charts
- **Temperatur-Verlauf:** Multi-Device-Temperaturanzeige
- **Umgebungsdaten:** Luftfeuchtigkeit und Luftdruck
- **Zeitbereich-Auswahl:** 1h, 6h, 24h, 7 Tage
- **Geräte-Filter:** Einzelne Geräte oder alle anzeigen

### Auto-Refresh
- Automatische Aktualisierung alle 30 Sekunden
- Ein-/Ausschaltbar über UI
- Manuelle Refresh-Funktion

## 🛡️ Datenbank-Sicherheit

Das System verwendet SQLite mit WAL-Modus für optimierte Concurrent-Access:
- **Thread-safe** Datenbankoperationen
- **WAL-Modus** für bessere Schreib-/Lese-Performance
- **Automatische Indices** für bessere Query-Performance
- **Error-Handling** für Datenbank-Ausfälle

## 🔍 Troubleshooting

### Bluetooth-Probleme
```bash
# Bluetooth-Status prüfen
sudo systemctl status bluetooth

# Bluetooth neu starten
sudo systemctl restart bluetooth

# Verfügbare Adapter anzeigen
hciconfig
```

### Logger startet nicht
```bash
# Berechtigungen prüfen
sudo usermod -a -G bluetooth $USER

# Nach Neuanmeldung/Neustart:
python3 ruuvi_logger_db.py
```

### Web-Server nicht erreichbar
```bash
# Firewall prüfen (falls aktiviert)
sudo ufw allow 5000

# Port-Verwendung prüfen
netstat -tlnp | grep :5000
```

### Datenbank-Probleme
```bash
# Datenbank-Integrität prüfen
sqlite3 ruuvi_data.db "PRAGMA integrity_check;"

# Datenbank-Größe prüfen
ls -lh ruuvi_data.db
```

## 📈 Erweiterte Konfiguration

### Performance-Optimierung
- **min-interval anpassen:** Für häufigere/seltenere Logs
- **Datenbank-Bereinigung:** Alte Daten automatisch löschen
- **Index-Optimierung:** Zusätzliche Indices für spezielle Queries

### Netzwerk-Zugriff
```python
# In web_server.py für externen Zugriff:
app.run(host='0.0.0.0', port=5000, debug=False)
```

### Daten-Export
```python
# CSV-Export aus der Datenbank
import pandas as pd
import sqlite3

conn = sqlite3.connect('ruuvi_data.db')
df = pd.read_sql_query("SELECT * FROM sensor_data", conn)
df.to_csv('export.csv', index=False)
```

## 🆘 Support

Bei Problemen prüfen Sie:
1. Python-Version und Abhängigkeiten
2. Bluetooth-Funktionalität
3. RuuviTag-Batteriestatus
4. Systemlogs: `journalctl -u ruuvi-logger.service -f`

## 📝 Lizenz

Dieses Projekt steht unter der MIT-Lizenz.