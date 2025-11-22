# Ruuvi Air → ThingSpeak Integration

Automatischer Upload deiner Ruuvi Air Sensordaten zu ThingSpeak Cloud.

## ⚡ Quick Start (3 Schritte)

### 1. ThingSpeak Channel erstellen

1. Gehe zu [thingspeak.com](https://thingspeak.com) und erstelle einen Account
2. Erstelle einen neuen Channel mit 8 Fields:
   - Field 1: Temperature (°C)
   - Field 2: Humidity (%)
   - Field 3: Pressure (Pa)
   - Field 4: PM2.5 (µg/m³)
   - Field 5: CO2 (ppm)
   - Field 6: VOC Index
   - Field 7: NOX Index
   - Field 8: Luminosity (lux)
3. Kopiere den **Write API Key**

### 2. Setup ausführen

```bash
cd /home/hellhammer/github/Ruuvi_Raspi_Arduino/RuuviAir
chmod +x setup_thingspeak.sh
./setup_thingspeak.sh
```

Das Script:
- Installiert `requests` 
- Testet die ThingSpeak-Verbindung
- Konfiguriert den systemd Service
- Startet den Upload

### 3. Fertig!

Deine Daten werden jetzt automatisch hochgeladen! 🎉

Siehe sie hier: [thingspeak.com/channels](https://thingspeak.com/channels)

## 📱 Features

✅ Automatischer Upload alle 15 Sekunden (konfigurierbar)  
✅ Duplikate-Vermeidung  
✅ Fehler-Behandlung  
✅ Offline-Queue mit Mittelung  
✅ Statistiken im Log  
✅ Systemd Service Integration  

## 🎯 Verwendung

### Manuell starten

```bash
# Mit API Key als Parameter
python3 ruuvi_format6_thingspeak.py --thingspeak-key YOUR_KEY

# Mit Umgebungsvariable
export THINGSPEAK_API_KEY="YOUR_KEY"
python3 ruuvi_format6_thingspeak.py

# Intervall anpassen (10 Sekunden)
python3 ruuvi_format6_thingspeak.py --thingspeak-key YOUR_KEY --thingspeak-interval 10
```

### Als Service

```bash
# Status
sudo systemctl status ruuvi-thingspeak.service

# Logs live
sudo journalctl -u ruuvi-thingspeak.service -f

# Neustart
sudo systemctl restart ruuvi-thingspeak.service
```

## 📊 Upload-Intervalle

| Intervall | Account Typ | Empfohlung |
|-----------|-------------|------------|
| 20s       | Free        | Sehr sicher |
| 15s       | Free        | Empfohlen ✓ |
| 10s       | Paid/Free*  | Schnell |
| 5s        | Paid        | Sehr schnell |

*Bei Free Account mit 10s werden Daten gemittelt

## 🔧 Konfiguration

### API Key ändern

```bash
sudo nano /etc/systemd/system/ruuvi-thingspeak.service
```

Ändere:
```ini
Environment="THINGSPEAK_API_KEY=NEW_API_KEY"
```

Dann:
```bash
sudo systemctl daemon-reload
sudo systemctl restart ruuvi-thingspeak.service
```

### Intervall ändern

In der Service-Datei:
```ini
ExecStart=.../ruuvi_format6_thingspeak.py --no-debug --thingspeak-interval 10
```

## 📈 Monitoring

### Logs

```bash
# Letzte 50 Zeilen
sudo journalctl -u ruuvi-thingspeak.service -n 50

# Live mit Filtern
sudo journalctl -u ruuvi-thingspeak.service -f | grep ThingSpeak

# Nur Fehler
sudo journalctl -u ruuvi-thingspeak.service -p err
```

### Statistiken

Die Logs zeigen Upload-Stats:
```
[ThingSpeak] ✓ Upload successful (Total: 42, Errors: 0)

STATISTICS
Total BLE devices: 15
Ruuvi devices: 1
Format 6 devices: 1
ThingSpeak uploads: 2
ThingSpeak errors: 0
```

## 🛠️ Troubleshooting

### Upload schlägt fehl

```bash
# Test-Upload
python3 thingspeak_integration.py YOUR_API_KEY

# Internet prüfen
ping -c 3 api.thingspeak.com

# Service neu starten
sudo systemctl restart ruuvi-thingspeak.service
```

### "Rate limit exceeded"

→ Erhöhe `--thingspeak-interval` auf mindestens 15

### Keine Daten im Channel

```bash
# Logs prüfen
sudo journalctl -u ruuvi-thingspeak.service -n 100

# API Key prüfen
echo $THINGSPEAK_API_KEY

# Ruuvi-Erkennung testen
python3 test_bluetooth.py
```

## 📚 Dokumentation

- **[THINGSPEAK_SETUP.md](THINGSPEAK_SETUP.md)** - Vollständige Setup-Anleitung
- **[thingspeak_integration.py](thingspeak_integration.py)** - API-Modul
- **[ruuvi_format6_thingspeak.py](ruuvi_format6_thingspeak.py)** - Scanner mit Upload

## 📱 Mobile Apps

ThingSpeak hat offizielle Apps:
- iOS: "ThingView" im App Store
- Android: "ThingView" auf Google Play

## 🔗 Links

- ThingSpeak: https://thingspeak.com
- Docs: https://www.mathworks.com/help/thingspeak/
- Channel: https://thingspeak.com/channels (nach Login)

## 💡 Tipps

### Daten sparen

Nur bei Änderungen uploaden:
```python
# TODO: Implementierung mit Delta-Check
```

### Mehrere Sensoren

Erstelle für jeden Sensor einen eigenen Channel

### Visualisierung

ThingSpeak bietet:
- Automatische Charts
- MATLAB-Integration
- Webhook/Alerts
- Public Sharing

### Backup

Du hast jetzt:
- ✓ Lokale SQLite-Datenbank
- ✓ Cloud-Backup auf ThingSpeak

## ⚙️ Erweiterte Optionen

### Nur bestimmte Felder hochladen

Editiere `thingspeak_integration.py` und kommentiere Fields aus

### Custom Upload-Logik

Implementiere eigene `ThingSpeakUploader`-Klasse

### Mehrere Channels

Erstelle mehrere Uploader-Instanzen

---

**Viel Erfolg mit deinem Cloud-Monitoring!** ☁️📊
