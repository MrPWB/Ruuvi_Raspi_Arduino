# Ruuvi Air Monitor - Raspberry Pi Scanner

Ein vollständiges Monitoring-System für Ruuvi Air Sensoren auf Raspberry Pi mit SQLite-Datenbank, automatischem Service-Betrieb und umfangreichen Analyse-Tools.

## 🎯 Features

- ✅ **Automatische BLE-Erkennung** von Ruuvi Air Sensoren (Format 6)
- ✅ **SQLite-Datenbank** für alle Messwerte mit Zeitstempel
- ✅ **Systemd Service** für automatischen Start beim Booten
- ✅ **Duplikat-Erkennung** über Measurement Sequence
- ✅ **Debug-Modus** für Fehlersuche
- ✅ **Query-Tools** für Datenanalyse und CSV-Export
- ✅ **Virtual Environment** Support
- ✅ **Umfassende Dokumentation**

## 📊 Gemessene Werte

Der Ruuvi Air (Format 6) liefert:

- 🌡️ **Temperatur** (-163.835°C bis +163.835°C, 0.005°C Auflösung)
- 💧 **Luftfeuchtigkeit** (0-100%, 0.0025% Auflösung)
- 🌪️ **Luftdruck** (50000-115534 Pa, 1 Pa Auflösung)
- 🏭 **PM2.5 Feinstaub** (0-1000 µg/m³, 0.1 Auflösung)
- 💨 **CO2** (0-40000 ppm)
- 🧪 **VOC Index** (0-500, Flüchtige organische Verbindungen)
- ⚗️ **NOX Index** (0-500, Stickoxide)
- 💡 **Helligkeit** (0-65535 Lux, logarithmisch kodiert)
- 📡 **RSSI** (Bluetooth-Signalstärke)

## 🚀 Quick Start

### 1. Repository klonen

```bash
cd /home/hellhammer/github
git clone <your-repo-url> Ruuvi_Raspi_Arduino
cd Ruuvi_Raspi_Arduino
```

### 2. Virtual Environment erstellen

```bash
python3 -m venv venv
source venv/bin/activate
pip install bleak
```

### 3. Test durchführen

```bash
cd RuuviAir
sudo python3 test_bluetooth.py
```

### 4. Scanner manuell starten

```bash
sudo python3 ruuvi_format6_scanner.py
```

### 5. Als Service installieren

```bash
chmod +x install_service.sh
./install_service.sh
```

## 📁 Projektstruktur

```
Ruuvi_Raspi_Arduino/
├── venv/                          # Virtual Environment
├── RuuviAir/
│   ├── ruuvi_format6_scanner.py   # Hauptscanner (Format 6)
│   ├── ruuvi_universal_scanner.py # Universal-Scanner (Format 6 + E1)
│   ├── query_ruuvi_format6.py     # Datenbank-Query-Tool
│   ├── test_bluetooth.py          # Bluetooth-Test-Tool
│   ├── ruuvi_data.db              # SQLite-Datenbank (erstellt automatisch)
│   ├── ruuvi-scanner.service      # Systemd Service-Datei
│   ├── install_service.sh         # Service-Installations-Script
│   ├── uninstall_service.sh       # Service-Deinstallations-Script
│   ├── README_FORMAT6.md          # Format 6 Dokumentation
│   ├── SERVICE_INSTALLATION.md    # Service-Installations-Guide
│   ├── DEBUG_GUIDE.md             # Debug-Anleitung
│   └── .gitignore                 # Git Ignore-Datei
└── README.md                      # Diese Datei
```

## 🔧 Verfügbare Scripts

### Scanner

- **`ruuvi_format6_scanner.py`** - Hauptscanner für Format 6 (Ruuvi Air)
- **`ruuvi_universal_scanner.py`** - Unterstützt Format 6 und E1
- **`ruuvi_e1_scanner.py`** - Speziell für Format E1 (Legacy)

### Tools

- **`test_bluetooth.py`** - Testet Bluetooth-Umgebung und findet Ruuvi-Geräte
- **`query_ruuvi_format6.py`** - Datenbank-Abfrage und Analyse-Tool

### Service-Management

- **`install_service.sh`** - Installiert den Scanner als systemd Service
- **`uninstall_service.sh`** - Entfernt den Service

## 📖 Dokumentation

- **[README_FORMAT6.md](README_FORMAT6.md)** - Vollständige Format 6 Dokumentation
- **[SERVICE_INSTALLATION.md](SERVICE_INSTALLATION.md)** - Service-Installation Guide
- **[DEBUG_GUIDE.md](DEBUG_GUIDE.md)** - Fehlerbehebung und Debug-Hilfe

## 💾 Datenbank-Abfragen

### Mit dem Query-Tool

```bash
# Letzte 10 Messungen
python3 query_ruuvi_format6.py --latest 10

# Statistiken der letzten 24 Stunden
python3 query_ruuvi_format6.py --stats 24

# Alle Geräte anzeigen
python3 query_ruuvi_format6.py --devices

# Export als CSV
python3 query_ruuvi_format6.py --export data.csv --hours 24
```

### Direkt mit SQLite

```bash
# Letzte Messung
sqlite3 ruuvi_data.db "SELECT * FROM ruuvi_measurements ORDER BY timestamp DESC LIMIT 1"

# Durchschnittswerte heute
sqlite3 ruuvi_data.db "SELECT 
    AVG(temperature) as temp,
    AVG(humidity) as humidity,
    AVG(co2) as co2
FROM ruuvi_measurements 
WHERE date(timestamp) = date('now')"
```

## 🔄 Service-Verwaltung

```bash
# Status anzeigen
sudo systemctl status ruuvi-scanner.service

# Logs live verfolgen
sudo journalctl -u ruuvi-scanner.service -f

# Service stoppen
sudo systemctl stop ruuvi-scanner.service

# Service neustarten
sudo systemctl restart ruuvi-scanner.service

# Autostart deaktivieren
sudo systemctl disable ruuvi-scanner.service
```

## 🛠️ Voraussetzungen

### Hardware

- Raspberry Pi mit Bluetooth 4.0+ (Pi 4, Pi 5, Pi Zero 2 W)
- Ruuvi Air Sensor mit Format 6

### Software

- Raspberry Pi OS (aktuell)
- Python 3.7+
- Bluetooth aktiviert

### Python-Pakete

- `bleak>=0.21.0`

## 🔌 Installation von Abhängigkeiten

```bash
# System-Pakete
sudo apt-get update
sudo apt-get install -y python3-pip bluetooth bluez libbluetooth-dev

# Python-Pakete (in venv)
source venv/bin/activate
pip install bleak
```

## 📈 Monitoring & Analytics

### Performance

```bash
# Anzahl Messungen
sqlite3 ruuvi_data.db "SELECT COUNT(*) FROM ruuvi_measurements"

# Datenbank-Größe
du -h ruuvi_data.db

# Service-Speicher
systemctl status ruuvi-scanner.service | grep Memory
```

### Backup

```bash
# Manuelle Datenbank-Sicherung
cp ruuvi_data.db ruuvi_data_$(date +%Y%m%d).db

# Automatisches Backup (in crontab -e)
0 3 * * * cp /home/hellhammer/github/Ruuvi_Raspi_Arduino/RuuviAir/ruuvi_data.db \
  /home/hellhammer/backups/ruuvi_$(date +\%Y\%m\%d).db
```

## 🐛 Troubleshooting

### Bluetooth-Probleme

```bash
# Bluetooth-Status prüfen
sudo systemctl status bluetooth

# Bluetooth neu starten
sudo systemctl restart bluetooth

# Geräte scannen
sudo hcitool lescan
```

### Berechtigungs-Probleme

```bash
# Python-Berechtigungen setzen
sudo setcap cap_net_raw,cap_net_admin+eip /home/hellhammer/github/Ruuvi_Raspi_Arduino/venv/bin/python3

# Prüfen
getcap /home/hellhammer/github/Ruuvi_Raspi_Arduino/venv/bin/python3
```

### Service startet nicht

```bash
# Detaillierte Logs
sudo journalctl -xe -u ruuvi-scanner.service

# Service-Status
sudo systemctl status ruuvi-scanner.service -l

# Systemd-Konfiguration neu laden
sudo systemctl daemon-reload
```

## 🔐 Sicherheit

Der Service läuft mit eingeschränkten Berechtigungen:

- Läuft als User `hellhammer` (nicht root)
- `NoNewPrivileges=true`
- `PrivateTmp=true`
- Nur minimale Bluetooth-Berechtigungen via capabilities

## 🌐 Integration

### Home Assistant

```yaml
# configuration.yaml
sensor:
  - platform: command_line
    name: Ruuvi Temperature
    command: "sqlite3 /home/hellhammer/github/Ruuvi_Raspi_Arduino/RuuviAir/ruuvi_data.db \"SELECT temperature FROM ruuvi_measurements ORDER BY timestamp DESC LIMIT 1\""
    unit_of_measurement: "°C"
```

### MQTT (optional)

```bash
# MQTT-Support hinzufügen
source venv/bin/activate
pip install paho-mqtt
```

### Grafana/InfluxDB (optional)

Exportiere Daten nach InfluxDB für professionelle Visualisierung.

## 📊 Datenbank-Schema

```sql
CREATE TABLE ruuvi_measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    mac TEXT,
    mac_short TEXT,
    temperature REAL,
    humidity REAL,
    pressure INTEGER,
    pm2_5 REAL,
    co2 INTEGER,
    voc INTEGER,
    nox INTEGER,
    luminosity REAL,
    measurement_sequence INTEGER,
    calibration_in_progress INTEGER,
    rssi INTEGER
)
```

## 🔄 Updates

```bash
cd /home/hellhammer/github/Ruuvi_Raspi_Arduino
git pull
sudo systemctl restart ruuvi-scanner.service
```

## 📝 Lizenz

Freie Verwendung für private und kommerzielle Zwecke.

## 🔗 Links

- [Ruuvi Format 6 Dokumentation](https://docs.ruuvi.com/communication/bluetooth-advertisements/data-format-6)
- [Ruuvi Website](https://ruuvi.com)
- [Bleak Library](https://github.com/hbldh/bleak)

## 🤝 Support

Bei Problemen siehe:
1. [DEBUG_GUIDE.md](DEBUG_GUIDE.md) für Fehlerbehebung
2. [SERVICE_INSTALLATION.md](SERVICE_INSTALLATION.md) für Service-Details
3. GitHub Issues

## ✨ Features in Planung

- [ ] Web-Dashboard
- [ ] MQTT-Integration
- [ ] Multi-Sensor Support
- [ ] Alarme bei Grenzwerten
- [ ] Grafana-Dashboard
- [ ] REST API
