# Ruuvi Format 6 BLE Scanner für Raspberry Pi

Dieses Python-Skript scannt nach Ruuvi Air-Geräten, die das Format 6-Datenformat über Bluetooth übertragen, dekodiert die Daten und speichert sie in einer SQLite-Datenbank.

**Format 6** ist das Bluetooth 4 kompatible Format für Ruuvi Air Geräte und enthält:
- Temperatur, Luftfeuchtigkeit, Luftdruck
- PM2.5 Feinstaub
- CO2, VOC, NOX Luftqualitätswerte
- Helligkeit (logarithmisch kodiert)

## Voraussetzungen

### Hardware
- Raspberry Pi mit Bluetooth 4.0+ (funktioniert auf allen modernen Raspberry Pis)
- Ruuvi Air mit Format 6

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
sudo python3 ruuvi_format6_scanner.py
```

## Verwendung

### Starten des Scanners

```bash
sudo python3 ruuvi_format6_scanner.py
```

Das Skript läuft kontinuierlich und:
- Scannt nach Ruuvi Air-Geräten mit Format 6
- Dekodiert alle Sensordaten
- Speichert sie in `ruuvi_data.db`
- Zeigt Messwerte in der Konsole an
- Zeigt alle 30 Sekunden Statistiken

### Debug-Modus ausschalten

Wenn du die vielen Debug-Ausgaben nicht brauchst:

```bash
sudo python3 ruuvi_format6_scanner.py --no-debug
```

### Beenden

Drücke `Ctrl+C` um den Scanner zu beenden.

## Datenbank

Die Daten werden in einer SQLite-Datenbank (`ruuvi_data.db`) gespeichert.

### Tabellen-Schema

```sql
CREATE TABLE ruuvi_measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    mac TEXT,                  -- Volle MAC-Adresse vom BLE
    mac_short TEXT,            -- Kurze MAC (letzte 3 Bytes)
    temperature REAL,          -- °C
    humidity REAL,             -- %
    pressure INTEGER,          -- Pa
    pm2_5 REAL,               -- µg/m³
    co2 INTEGER,              -- ppm
    voc INTEGER,              -- Index (unitless)
    nox INTEGER,              -- Index (unitless)
    luminosity REAL,          -- lux
    measurement_sequence INTEGER,
    calibration_in_progress INTEGER,
    rssi INTEGER              -- dBm
)
```

## Daten abfragen

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
# Letzte 10 Messungen
sqlite3 ruuvi_data.db "SELECT timestamp, temperature, humidity, pm2_5, co2 FROM ruuvi_measurements ORDER BY timestamp DESC LIMIT 10"

# Durchschnittswerte der letzten Stunde
sqlite3 ruuvi_data.db "SELECT 
    AVG(temperature) as avg_temp,
    AVG(humidity) as avg_humidity,
    AVG(co2) as avg_co2,
    AVG(pm2_5) as avg_pm25
FROM ruuvi_measurements 
WHERE datetime(timestamp) > datetime('now', '-1 hour')"
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
Description=Ruuvi Format 6 BLE Scanner
After=bluetooth.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi
ExecStart=/usr/bin/python3 /home/pi/ruuvi_format6_scanner.py --no-debug
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

5. Logs ansehen:

```bash
sudo journalctl -u ruuvi-scanner.service -f
```

## Gemessene Werte (Format 6)

- **Temperatur**: -163.835°C bis +163.835°C (0.005°C Auflösung)
- **Luftfeuchtigkeit**: 0-100% (0.0025% Auflösung)
- **Luftdruck**: 50000-115534 Pa (1 Pa Auflösung)
- **Feinstaub PM2.5**: 0-1000 µg/m³ (0.1 Auflösung)
- **CO2**: 0-40000 ppm
- **VOC Index**: 0-500 (Flüchtige organische Verbindungen)
- **NOX Index**: 0-500 (Stickoxide)
- **Helligkeit**: 0-65535 Lux (logarithmisch kodiert)
- **RSSI**: Bluetooth-Signalstärke in dBm

## Debug-Ausgaben

Im Debug-Modus siehst du:

```
[DEBUG] Device #1: Ruuvi Air (AA:BB:CC:DD:EE:FF)
[DEBUG] RSSI: -65 dBm
[DEBUG] Manufacturer data found:
[DEBUG]   ID: 0x0499 (1177)
[DEBUG]   Data length: 20 bytes
[DEBUG]   Raw hex: 06170c5668c79e007000c90501d9cd004c884f
[DEBUG]   Format byte: 0x06 (6)
[DEBUG] ✓ Ruuvi device detected!
[DEBUG] Data format byte: 0x06
[DEBUG] ✓ Format 6 successfully decoded!

============================================================
[2025-01-22 15:30:45] Ruuvi Air: AA:BB:CC:DD:EE:FF
============================================================
  RSSI: -65 dBm
  Temperature: 21.50°C
  Humidity: 45.25%
  Pressure: 101325 Pa (1013.3 hPa)
  PM2.5: 12.3 µg/m³
  CO2: 450 ppm
  VOC Index: 95
  NOX Index: 2
  Luminosity: 245.50 lux
  Sequence: 42
============================================================
```

## Fehlerbehebung

### "Permission denied" beim Bluetooth-Zugriff

```bash
sudo python3 ruuvi_format6_scanner.py
```

### Keine Geräte gefunden

```bash
# Bluetooth prüfen
sudo systemctl status bluetooth

# Bluetooth aktivieren
bluetoothctl power on

# Manueller Scan
sudo hcitool lescan
```

### Falsches Format erkannt?

Das Skript zeigt dir, welches Format dein Gerät verwendet:

```
[DEBUG] ✗ Not Format 6 (expected 0x06, got 0x05)
[DEBUG] This is likely Format 5 (RAWv2)
```

**Format 6** = `0x06` = Ruuvi Air (Bluetooth 4 kompatibel)  
**Format 5** = `0x05` = Ältere RuuviTags  
**Format E1** = `0xE1` = Ruuvi Air Extended (nur Bluetooth 5)

## Unterschied Format 6 vs E1

| Feature | Format 6 | Format E1 |
|---------|----------|-----------|
| Bluetooth | 4.0+ | 5.0+ |
| Datengröße | 20 Bytes | 40 Bytes |
| PM Werte | Nur PM2.5 | PM1.0, PM2.5, PM4.0, PM10.0 |
| Helligkeit | 8-bit logarithmisch | 24-bit linear |
| MAC | 3 Bytes | 6 Bytes |

**Empfehlung:** Verwende Format 6 für maximale Kompatibilität mit älteren Geräten.

## Erweiterungen

Mögliche Erweiterungen:
- MQTT-Integration für Home Assistant
- InfluxDB-Export für Grafana
- Web-Dashboard mit Flask
- Alarme bei Grenzwerten (z.B. CO2 > 1000 ppm)

## Beispiel: CO2 Alarm

```python
# In detection_callback hinzufügen:
if decoded.get('co2') and decoded['co2'] > 1000:
    print("⚠️  WARNUNG: CO2 über 1000 ppm! Lüften empfohlen!")
```

## Lizenz

Freie Verwendung für private und kommerzielle Zwecke.

## Links

- [Ruuvi Format 6 Dokumentation](https://docs.ruuvi.com/communication/bluetooth-advertisements/data-format-6)
- [Ruuvi Website](https://ruuvi.com)
