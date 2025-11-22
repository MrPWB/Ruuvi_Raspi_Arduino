# Ruuvi Scanner Service Installation

Diese Anleitung zeigt, wie du den Ruuvi Scanner als systemd Service installierst, damit er automatisch beim Systemstart läuft.

## 1. Service-Datei kopieren

```bash
# Service-Datei an den richtigen Ort kopieren
sudo cp ruuvi-scanner.service /etc/systemd/system/

# Oder direkt erstellen
sudo nano /etc/systemd/system/ruuvi-scanner.service
```

## 2. Berechtigungen setzen

```bash
# Bluetooth-Berechtigungen für Python in der venv
sudo setcap cap_net_raw,cap_net_admin+eip /home/hellhammer/github/Ruuvi_Raspi_Arduino/venv/bin/python3

# Datei-Berechtigungen
sudo chmod 644 /etc/systemd/system/ruuvi-scanner.service
```

## 3. Service aktivieren und starten

```bash
# Systemd neu laden
sudo systemctl daemon-reload

# Service aktivieren (automatischer Start beim Booten)
sudo systemctl enable ruuvi-scanner.service

# Service starten
sudo systemctl start ruuvi-scanner.service
```

## 4. Status prüfen

```bash
# Status anzeigen
sudo systemctl status ruuvi-scanner.service

# Sollte ausgeben:
# ● ruuvi-scanner.service - Ruuvi Format 6 BLE Scanner
#      Loaded: loaded (/etc/systemd/system/ruuvi-scanner.service; enabled)
#      Active: active (running) since ...
```

## 5. Logs ansehen

```bash
# Live-Logs verfolgen
sudo journalctl -u ruuvi-scanner.service -f

# Letzte 100 Zeilen
sudo journalctl -u ruuvi-scanner.service -n 100

# Logs seit heute
sudo journalctl -u ruuvi-scanner.service --since today

# Logs der letzten Stunde
sudo journalctl -u ruuvi-scanner.service --since "1 hour ago"
```

## 6. Service verwalten

```bash
# Service stoppen
sudo systemctl stop ruuvi-scanner.service

# Service neustarten
sudo systemctl restart ruuvi-scanner.service

# Service deaktivieren (kein Autostart mehr)
sudo systemctl disable ruuvi-scanner.service

# Service-Konfiguration neu laden (nach Änderungen)
sudo systemctl daemon-reload
sudo systemctl restart ruuvi-scanner.service
```

## Troubleshooting

### Service startet nicht

```bash
# Detaillierte Fehlerausgabe
sudo systemctl status ruuvi-scanner.service -l

# Journal mit Fehlern
sudo journalctl -xe -u ruuvi-scanner.service
```

### Bluetooth-Probleme

```bash
# Bluetooth-Status prüfen
sudo systemctl status bluetooth

# Bluetooth neu starten
sudo systemctl restart bluetooth

# Service danach neu starten
sudo systemctl restart ruuvi-scanner.service
```

### Berechtigungen fehlen

```bash
# Python-Berechtigungen prüfen
getcap /home/hellhammer/github/Ruuvi_Raspi_Arduino/venv/bin/python3

# Falls leer, Berechtigungen setzen:
sudo setcap cap_net_raw,cap_net_admin+eip /home/hellhammer/github/Ruuvi_Raspi_Arduino/venv/bin/python3
```

### Datenbank-Speicherort

Der Service speichert die Datenbank hier:
```
/home/hellhammer/github/Ruuvi_Raspi_Arduino/RuuviAir/ruuvi_data.db
```

Du kannst die Datenbank abfragen mit:
```bash
cd /home/hellhammer/github/Ruuvi_Raspi_Arduino/RuuviAir
python3 query_ruuvi_format6.py --latest 10
```

## Service-Konfiguration anpassen

Falls du Anpassungen brauchst, editiere die Service-Datei:

```bash
sudo nano /etc/systemd/system/ruuvi-scanner.service
```

Mögliche Anpassungen:

### Debug-Modus aktivieren
```ini
ExecStart=/home/hellhammer/github/Ruuvi_Raspi_Arduino/venv/bin/python3 /home/hellhammer/github/Ruuvi_Raspi_Arduino/RuuviAir/ruuvi_format6_scanner.py
```
(ohne `--no-debug`)

### Andere Datenbank verwenden
```ini
ExecStart=/home/hellhammer/github/Ruuvi_Raspi_Arduino/venv/bin/python3 /home/hellhammer/github/Ruuvi_Raspi_Arduino/RuuviAir/ruuvi_format6_scanner.py --no-debug --db /pfad/zur/datenbank.db
```

### Restart-Verhalten ändern
```ini
Restart=on-failure
RestartSec=5
```

Nach jeder Änderung:
```bash
sudo systemctl daemon-reload
sudo systemctl restart ruuvi-scanner.service
```

## Performance-Überwachung

```bash
# Speicherverbrauch anzeigen
systemctl status ruuvi-scanner.service | grep Memory

# CPU-Nutzung
top -p $(pgrep -f ruuvi_format6_scanner)

# Anzahl der Messungen in Datenbank
sqlite3 /home/hellhammer/github/Ruuvi_Raspi_Arduino/RuuviAir/ruuvi_data.db \
  "SELECT COUNT(*) FROM ruuvi_measurements"
```

## Backup der Datenbank

```bash
# Regelmäßiges Backup erstellen (z.B. in Crontab)
# Füge in crontab -e hinzu:

# Täglich um 3 Uhr morgens
0 3 * * * cp /home/hellhammer/github/Ruuvi_Raspi_Arduino/RuuviAir/ruuvi_data.db \
  /home/hellhammer/backups/ruuvi_data_$(date +\%Y\%m\%d).db

# Alte Backups löschen (älter als 30 Tage)
0 4 * * * find /home/hellhammer/backups/ruuvi_data_*.db -mtime +30 -delete
```

## Updates

Wenn du den Scanner-Code aktualisierst:

```bash
cd /home/hellhammer/github/Ruuvi_Raspi_Arduino
git pull

# Service neu starten
sudo systemctl restart ruuvi-scanner.service

# Logs prüfen
sudo journalctl -u ruuvi-scanner.service -f
```

## Git Integration

### .gitignore anpassen

Füge in `.gitignore` hinzu:
```
# Datenbank nicht ins Git
ruuvi_data.db
ruuvi_data.db-shm
ruuvi_data.db-wal

# Python
__pycache__/
*.py[cod]
*$py.class
venv/
```

### Service-Datei im Repository

Du kannst die Service-Datei im Git-Repository speichern:
```bash
cd /home/hellhammer/github/Ruuvi_Raspi_Arduino
mkdir -p systemd
cp /etc/systemd/system/ruuvi-scanner.service systemd/
git add systemd/ruuvi-scanner.service
git commit -m "Add systemd service configuration"
git push
```

## Monitoring mit systemd

```bash
# Service automatisch neustarten bei Abstürzen
# (ist bereits in der Service-Datei konfiguriert)

# Maximale Neustarts setzen
# In Service-Datei ergänzen:
[Unit]
StartLimitBurst=5
StartLimitIntervalSec=60

# = Maximal 5 Neustarts in 60 Sekunden
```

## Weitere Dienste integrieren

### MQTT-Integration (optional)
Falls du MQTT nutzen willst:

```bash
# MQTT-Bibliothek installieren
source /home/hellhammer/github/Ruuvi_Raspi_Arduino/venv/bin/activate
pip install paho-mqtt
```

### Telegraf/InfluxDB (optional)
Für professionelles Monitoring:

```bash
# Telegraf installieren
sudo apt-get install telegraf

# Konfiguration für SQLite-Export
# /etc/telegraf/telegraf.d/ruuvi.conf
```
