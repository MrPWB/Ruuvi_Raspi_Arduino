# ThingSpeak Integration - Setup Guide

Diese Anleitung zeigt dir, wie du deine Ruuvi Air Daten automatisch zu ThingSpeak hochlädst.

## 🌐 Was ist ThingSpeak?

ThingSpeak ist eine IoT-Cloud-Plattform von MathWorks, die:
- Sensordaten sammelt und visualisiert
- REST API für einfachen Upload bereitstellt
- Kostenlose und kostenpflichtige Accounts anbietet
- Mobile Apps für iOS/Android hat
- MATLAB-Integration bietet

## 📊 ThingSpeak Channel Setup

### 1. Account erstellen

1. Gehe zu [https://thingspeak.com](https://thingspeak.com)
2. Klicke auf "Sign Up"
3. Erstelle einen kostenlosen Account

### 2. Channel erstellen

1. Nach Login: "Channels" → "My Channels" → "New Channel"
2. Fülle die Channel-Informationen aus:

```
Name: Ruuvi Air Monitor
Description: Environmental monitoring with Ruuvi Air sensor

Field 1: Temperature (°C)
Field 2: Humidity (%)
Field 3: Pressure (Pa)
Field 4: PM2.5 (µg/m³)
Field 5: CO2 (ppm)
Field 6: VOC Index
Field 7: NOX Index
Field 8: Luminosity (lux)
```

3. Klicke "Save Channel"

### 3. API Key holen

1. Im Channel → Tab "API Keys"
2. Kopiere den **Write API Key** (z.B. `ABCD1234EFGH5678`)

**⚠️ WICHTIG:** Teile diesen Key niemals öffentlich!

## 🚀 Installation

### 1. Dependencies installieren

```bash
cd /home/hellhammer/github/Ruuvi_Raspi_Arduino
source venv/bin/activate
pip install requests
```

### 2. ThingSpeak-Modul testen

```bash
cd RuuviAir
python3 thingspeak_integration.py YOUR_API_KEY
```

Du solltest sehen:
```
✓ Upload successful!
  Uploads: 1
  Check your channel: https://thingspeak.com/channels/YOUR_CHANNEL
```

## 🎯 Verwendung

### Variante 1: Manueller Start mit Parameter

```bash
python3 ruuvi_format6_thingspeak.py --thingspeak-key YOUR_API_KEY
```

### Variante 2: Mit Umgebungsvariable

```bash
export THINGSPEAK_API_KEY="YOUR_API_KEY"
python3 ruuvi_format6_thingspeak.py
```

### Variante 3: Upload-Intervall anpassen

```bash
# Alle 15 Sekunden (Free Account Limit)
python3 ruuvi_format6_thingspeak.py --thingspeak-key YOUR_KEY --thingspeak-interval 15

# Alle 10 Sekunden (erfordert Paid Account)
python3 ruuvi_format6_thingspeak.py --thingspeak-key YOUR_KEY --thingspeak-interval 10
```

## 🔧 Als Service installieren

### 1. Service-Datei anpassen

```bash
sudo nano /etc/systemd/system/ruuvi-thingspeak.service
```

Setze deinen API Key:
```ini
Environment="THINGSPEAK_API_KEY=YOUR_ACTUAL_API_KEY_HERE"
```

Falls du einen Paid Account hast und 10 Sekunden Intervall willst:
```ini
ExecStart=/home/hellhammer/github/Ruuvi_Raspi_Arduino/venv/bin/python3 /home/hellhammer/github/Ruuvi_Raspi_Arduino/RuuviAir/ruuvi_format6_thingspeak.py --no-debug --thingspeak-interval 10
```

### 2. Service installieren

```bash
# Service-Datei kopieren
sudo cp ruuvi-thingspeak.service /etc/systemd/system/

# Bluetooth-Berechtigungen
sudo setcap cap_net_raw,cap_net_admin+eip /home/hellhammer/github/Ruuvi_Raspi_Arduino/venv/bin/python3

# Service aktivieren
sudo systemctl daemon-reload
sudo systemctl enable ruuvi-thingspeak.service
sudo systemctl start ruuvi-thingspeak.service
```

### 3. Status prüfen

```bash
sudo systemctl status ruuvi-thingspeak.service
```

### 4. Logs ansehen

```bash
# Live-Logs
sudo journalctl -u ruuvi-thingspeak.service -f

# Letzte 50 Zeilen
sudo journalctl -u ruuvi-thingspeak.service -n 50
```

## 📊 ThingSpeak Dashboard

### Daten ansehen

1. Gehe zu [https://thingspeak.com](https://thingspeak.com)
2. "Channels" → "My Channels"
3. Wähle deinen Channel
4. Sieh dir die Grafiken an!

### Mobile App

ThingSpeak hat Apps für iOS und Android:
- iOS: [ThingSpeak im App Store](https://apps.apple.com/app/thingview/id1284878805)
- Android: [ThingView auf Google Play](https://play.google.com/store/apps/details?id=com.cinetica_tech.thingview)

## ⚙️ Konfiguration

### Rate Limits

| Account Typ | Min. Intervall | Max. Updates/Tag |
|-------------|----------------|------------------|
| Free        | 15 Sekunden    | 3 Million        |
| Paid        | Beliebig       | Unbegrenzt       |

### Intervall-Empfehlungen

```bash
# Conservative (Safe für alle Accounts)
--thingspeak-interval 20

# Normal (Free Account Limit)
--thingspeak-interval 15

# Schnell (Paid Account nötig)
--thingspeak-interval 10

# Sehr schnell (nur für Tests)
--thingspeak-interval 5
```

**Hinweis:** Bei Intervallen < 15 Sekunden mit Free Account werden Daten gemittelt hochgeladen!

## 🔍 Monitoring

### Upload-Statistiken

Die Logs zeigen Upload-Statistiken:

```
[ThingSpeak] ✓ Upload successful (Total: 42, Errors: 0)

STATISTICS (after 30s)
==============================================================
Total BLE devices: 15
Ruuvi devices: 1
Format 6 devices: 1
ThingSpeak uploads: 2
ThingSpeak errors: 0
==============================================================
```

### ThingSpeak Channel Status

Im Channel → Tab "Status":
- Entry ID (letzte Messung)
- Anzahl Einträge
- Letztes Update

## 🛠️ Troubleshooting

### Upload schlägt fehl

```bash
# Test-Upload manuell
python3 thingspeak_integration.py YOUR_API_KEY

# Prüfe API Key
echo $THINGSPEAK_API_KEY

# Prüfe Internet-Verbindung
ping -c 3 api.thingspeak.com
```

### "HTTP 400 Bad Request"

- API Key ist falsch
- Channel existiert nicht
- Feldnamen stimmen nicht überein

### "Rate limit exceeded"

- Du sendest zu schnell für einen Free Account
- Erhöhe `--thingspeak-interval` auf mindestens 15

### Keine Daten im Channel

```bash
# Prüfe ob Scanner läuft
sudo systemctl status ruuvi-thingspeak.service

# Prüfe Logs
sudo journalctl -u ruuvi-thingspeak.service -n 100

# Prüfe ob Ruuvi erkannt wird
python3 test_bluetooth.py
```

## 📈 Erweiterte Features

### MATLAB Integration

ThingSpeak bietet MATLAB-Integration für:
- Datenanalyse
- Berechnungen
- Alerts
- Visualisierungen

Siehe: [ThingSpeak MATLAB Docs](https://www.mathworks.com/help/thingspeak/)

### Webhooks & Alerts

1. Im Channel → Tab "Apps" → "React"
2. Erstelle Alerts bei Schwellwerten
3. Z.B.: Email wenn CO2 > 1000 ppm

### Public/Private Channels

Standardmäßig ist dein Channel privat. Du kannst ihn öffentlich machen:
- Channel Settings → "Make Public"
- Teile den Link mit anderen

### Data Export

ThingSpeak erlaubt CSV/JSON/XML Export:
- Channel → "Data Import/Export"
- API für automatischen Export

## 🔐 Sicherheit

### API Key schützen

**NIEMALS** den API Key ins Git committen!

```bash
# In .gitignore hinzufügen
echo "*.env" >> .gitignore
echo "thingspeak_config.py" >> .gitignore

# API Key in separater Datei
echo "THINGSPEAK_API_KEY=YOUR_KEY" > .env
```

### Service-Datei verschlüsseln

Für extra Sicherheit:

```bash
# API Key verschlüsseln
echo -n "YOUR_KEY" | base64

# In Service verwenden (mit Decoder-Script)
```

## 📊 Alternative zu ThingSpeak

Falls ThingSpeak nicht passt:

- **Adafruit IO**: Ähnlich wie ThingSpeak
- **InfluxDB Cloud**: Professionelles Time-Series DB
- **Grafana Cloud**: Visualisierung + Alerting
- **Home Assistant**: Lokale Lösung
- **Arduino IoT Cloud**: Arduino-Integration

## 💡 Tipps & Tricks

### Mehrere Sensoren

```python
# Für jeden Sensor einen eigenen Channel erstellen
# Oder: Field-Namen mit Sensor-ID versehen
```

### Datenreduktion

```python
# Nur wichtige Werte hochladen
# z.B. nur wenn sich CO2 um >50 ppm ändert
```

### Backup

```python
# Lokal in SQLite + ThingSpeak = doppelt gesichert
```

### Visualisierung

1. ThingSpeak Charts anpassen
2. Public View erstellen
3. Embed-Code für Website nutzen

## 📞 Support

- ThingSpeak Docs: https://www.mathworks.com/help/thingspeak/
- ThingSpeak Forum: https://www.mathworks.com/matlabcentral/
- GitHub Issues: Für Probleme mit dem Scanner

## ✅ Checkliste

- [ ] ThingSpeak Account erstellt
- [ ] Channel mit 8 Fields erstellt
- [ ] Write API Key kopiert
- [ ] `requests` installiert
- [ ] Test-Upload erfolgreich
- [ ] Service konfiguriert
- [ ] Service läuft
- [ ] Daten erscheinen im Channel
- [ ] Mobile App installiert
- [ ] Dashboard angepasst

Viel Erfolg mit deinem Ruuvi Air Monitoring! 🎉
