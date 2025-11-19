# Ruuvi E1 BLE Scanner für Raspberry Pi

Dieses Python-Skript scannt nach Ruuvi-Geräten, die das E1-Datenformat über Bluetooth 5 übertragen, dekodiert die Daten und speichert sie in einer SQLite-Datenbank.

## Voraussetzungen

### Hardware
- Raspberry Pi mit Bluetooth 5.0+ (z.B. Raspberry Pi 4, Pi 5, oder Pi Zero 2 W)
- Ruuvi-Gerät mit E1-Format-Unterstützung

### Software
- Raspberry Pi OS (aktuell)
- Python 3.7 oder höher
- Bluetooth aktiviert

## Installation

### 1. System-Abhängigkeiten installieren

```bash
sudo apt-get update
sudo apt-get install -y python3-pip bluetooth bluez libbluetooth-dev
```

### 2. Python-Pakete installieren

```bash
pip3 install bleak
```

Oder mit einer requirements.txt:

```bash
pip3 install -r requirements.txt
```

### 3. Bluetooth-Berechtigungen

Für den Zugriff auf Bluetooth ohne root:

```bash
sudo setcap cap_net_raw,cap_net_admin+eip $(eval readlink -f `which python3`)
```

Oder das Skript mit sudo ausführen:

```bash
sudo python3 ruuvi_e1_scanner.py
```

## Verwendung

### Starten des Scanners

```bash
python3 ruuvi_e1_scanner.py
```

Das Skript läuft kontinuierlich und:
- Scannt nach Ruuvi-Geräten mit E1-Format
- Dekodiert alle Sensordaten
- Speichert sie in `ruuvi_data.db`
- Zeigt Messwerte in der Konsole an

### Beenden

Drücke `Ctrl+C` um den Scanner zu beenden.

## Datenbank

Die Daten werden in einer SQLite-Datenbank (`ruuvi_data.db`) gespeichert.

### Tabellen-Schema

```sql
CREATE TABLE ruuvi_measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    mac TEXT,
    temperature REAL,          -- °C
    humidity REAL,             -- %
    pressure INTEGER,          -- Pa
    pm1_0 REAL,               -- µg/m³
    pm2_5 REAL,               -- µg/m³
    pm4_0 REAL,               -- µg/m³
    pm10_0 REAL,              -- µg/m³
    co2 INTEGER,              -- ppm
    voc INTEGER,              -- Index (unitless)
    nox INTEGER,              -- Index (unitless)
    luminosity REAL,          -- lux
    measurement_sequence INTEGER,
    calibration_in_progress INTEGER,
    rssi INTEGER              -- dBm
)
```

## Beispiel-Abfragen

### Letzte 10 Messungen anzeigen

```bash
sqlite3 ruuvi_data.db "SELECT timestamp, temperature, humidity, pm2_5, co2 FROM ruuvi_measurements ORDER BY timestamp DESC LIMIT 10"
```

### Durchschnittswerte der letzten Stunde

```bash
sqlite3 ruuvi_data.db "SELECT 
    AVG(temperature) as avg_temp,
    AVG(humidity) as avg_humidity,
    AVG(co2) as avg_co2,
    AVG(pm2_5) as avg_pm25
FROM ruuvi_measurements 
WHERE datetime(timestamp) > datetime('now', '-1 hour')"
```

### Daten als CSV exportieren

```bash
sqlite3 -header -csv ruuvi_data.db "SELECT * FROM ruuvi_measurements" > export.csv
```

## Autostart beim Systemstart

### Systemd Service erstellen

1. Service-Datei erstellen:

```bash
sudo nano /etc/systemd/system/ruuvi-scanner.service
```

2. Inhalt einfügen:

```ini
[Unit]
Description=Ruuvi E1 BLE Scanner
After=bluetooth.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi
ExecStart=/usr/bin/python3 /home/pi/ruuvi_e1_scanner.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. Service aktivieren:

```bash
sudo systemctl enable ruuvi-scanner.service
sudo systemctl start ruuvi-scanner.service
```

4. Status prüfen:

```bash
sudo systemctl status ruuvi-scanner.service
```

## Gemessene Werte

Das E1-Format liefert folgende Sensordaten:

- **Temperatur**: -163.835°C bis +163.835°C (0.005°C Auflösung)
- **Luftfeuchtigkeit**: 0-100% (0.0025% Auflösung)
- **Luftdruck**: 50000-115534 Pa (1 Pa Auflösung)
- **Feinstaub** (PM1.0, PM2.5, PM4.0, PM10.0): 0-1000 µg/m³ (0.1 Auflösung)
- **CO2**: 0-40000 ppm
- **VOC Index**: 0-500 (Flüchtige organische Verbindungen)
- **NOX Index**: 0-500 (Stickoxide)
- **Helligkeit**: 0-144284 Lux (0.01 Auflösung)
- **RSSI**: Bluetooth-Signalstärke in dBm

## Fehlerbehebung

### "Permission denied" beim Bluetooth-Zugriff

```bash
sudo python3 ruuvi_e1_scanner.py
```

oder

```bash
sudo setcap cap_net_raw,cap_net_admin+eip $(eval readlink -f `which python3`)
```

### Keine Geräte gefunden

- Prüfe, ob Bluetooth aktiviert ist: `bluetoothctl power on`
- Prüfe, ob das Ruuvi-Gerät eingeschaltet ist
- Stelle sicher, dass das Gerät E1-Format sendet (Bluetooth 5.0)
- Prüfe die Reichweite

### "bleak not found"

```bash
pip3 install bleak
```

## Erweiterungen

Das Skript kann erweitert werden für:
- MQTT-Integration für Home Assistant
- InfluxDB-Export für Grafana-Visualisierung
- Alarme bei Grenzwertüberschreitungen
- Web-Dashboard
- Mehrere Sensoren gleichzeitig

## Lizenz

Freie Verwendung für private und kommerzielle Zwecke.

## Links

- [Ruuvi E1 Format Dokumentation](https://docs.ruuvi.com/communication/bluetooth-advertisements/data-format-e1)
- [Ruuvi Website](https://ruuvi.com)
