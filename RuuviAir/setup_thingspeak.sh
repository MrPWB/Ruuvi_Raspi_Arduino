#!/bin/bash
# ThingSpeak Integration - Quick Setup
# Installiert und konfiguriert ThingSpeak-Upload für Ruuvi Scanner

set -e

echo "=========================================="
echo "ThingSpeak Integration - Setup"
echo "=========================================="
echo ""

# Pfade
BASE_DIR="/home/hellhammer/github/Ruuvi_Raspi_Arduino"
VENV_DIR="$BASE_DIR/venv"
RUUVI_DIR="$BASE_DIR/RuuviAir"

# Prüfe Verzeichnisse
if [ ! -d "$BASE_DIR" ]; then
    echo "❌ Fehler: Verzeichnis $BASE_DIR existiert nicht!"
    exit 1
fi

cd "$RUUVI_DIR"

# Installiere requests
echo "Installiere Python-Abhängigkeiten..."
source "$VENV_DIR/bin/activate"
pip install requests --quiet
echo "✓ Dependencies installiert"

# API Key abfragen
echo ""
echo "=========================================="
echo "ThingSpeak API Key Setup"
echo "=========================================="
echo ""
echo "Um fortzufahren, benötigst du:"
echo "  1. ThingSpeak Account (kostenlos): https://thingspeak.com"
echo "  2. Einen Channel mit 8 Fields erstellt"
echo "  3. Deinen Write API Key"
echo ""
echo "Anleitung: siehe THINGSPEAK_SETUP.md"
echo ""

read -p "Hast du einen ThingSpeak Account und API Key? (j/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Jj]$ ]]; then
    echo ""
    echo "Kein Problem! Setup-Schritte:"
    echo ""
    echo "1. Gehe zu https://thingspeak.com und erstelle einen Account"
    echo "2. Erstelle einen Channel:"
    echo "   - Field 1: Temperature (°C)"
    echo "   - Field 2: Humidity (%)"
    echo "   - Field 3: Pressure (Pa)"
    echo "   - Field 4: PM2.5 (µg/m³)"
    echo "   - Field 5: CO2 (ppm)"
    echo "   - Field 6: VOC Index"
    echo "   - Field 7: NOX Index"
    echo "   - Field 8: Luminosity (lux)"
    echo "3. Kopiere den Write API Key"
    echo "4. Führe dieses Script nochmal aus"
    echo ""
    exit 0
fi

echo ""
read -p "Gib deinen ThingSpeak Write API Key ein: " API_KEY

if [ -z "$API_KEY" ]; then
    echo "❌ Kein API Key eingegeben. Abbruch."
    exit 1
fi

# API Key testen
echo ""
echo "Teste ThingSpeak-Verbindung..."
if python3 thingspeak_integration.py "$API_KEY" | grep -q "Upload successful"; then
    echo "✓ ThingSpeak-Verbindung erfolgreich!"
else
    echo "❌ ThingSpeak-Test fehlgeschlagen. Prüfe deinen API Key."
    exit 1
fi

# Service-Datei erstellen/aktualisieren
echo ""
echo "Konfiguriere systemd Service..."

SERVICE_FILE="ruuvi-thingspeak.service"

# API Key in Service-Datei einsetzen
if [ -f "$SERVICE_FILE" ]; then
    # Backup erstellen
    cp "$SERVICE_FILE" "${SERVICE_FILE}.backup"
    
    # API Key einsetzen
    sed -i "s/YOUR_API_KEY_HERE/$API_KEY/" "$SERVICE_FILE"
    echo "✓ Service-Datei aktualisiert"
else
    echo "❌ Service-Datei nicht gefunden!"
    exit 1
fi

# Upload-Intervall abfragen
echo ""
echo "=========================================="
echo "Upload-Intervall konfigurieren"
echo "=========================================="
echo ""
echo "Welches Upload-Intervall möchtest du?"
echo "  1) 15 Sekunden (empfohlen für Free Accounts)"
echo "  2) 10 Sekunden (erfordert evtl. Paid Account)"
echo "  3) 20 Sekunden (sehr sicher)"
echo ""
read -p "Wähle (1-3): " INTERVAL_CHOICE

case $INTERVAL_CHOICE in
    1)
        INTERVAL=15
        ;;
    2)
        INTERVAL=10
        echo "⚠️  Warnung: 10 Sekunden kann Rate Limits bei Free Accounts auslösen!"
        ;;
    3)
        INTERVAL=20
        ;;
    *)
        INTERVAL=15
        echo "Ungültige Wahl, verwende Standard: 15 Sekunden"
        ;;
esac

# Intervall in Service einsetzen
sed -i "s/--thingspeak-interval [0-9]*/--thingspeak-interval $INTERVAL/" "$SERVICE_FILE"
echo "✓ Upload-Intervall: $INTERVAL Sekunden"

# Service installieren
echo ""
read -p "Service jetzt installieren und starten? (j/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Jj]$ ]]; then
    # Bluetooth-Berechtigungen
    echo "Setze Bluetooth-Berechtigungen..."
    sudo setcap cap_net_raw,cap_net_admin+eip "$VENV_DIR/bin/python3"
    
    # Service installieren
    echo "Installiere Service..."
    sudo cp "$SERVICE_FILE" /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable ruuvi-thingspeak.service
    sudo systemctl start ruuvi-thingspeak.service
    
    sleep 2
    
    # Status prüfen
    echo ""
    echo "Service-Status:"
    sudo systemctl status ruuvi-thingspeak.service --no-pager -l | head -20
    
    echo ""
    echo "✓ Service installiert und gestartet!"
else
    echo ""
    echo "Service wurde NICHT installiert."
    echo "Du kannst ihn später manuell installieren:"
    echo "  sudo cp $SERVICE_FILE /etc/systemd/system/"
    echo "  sudo systemctl daemon-reload"
    echo "  sudo systemctl enable ruuvi-thingspeak.service"
    echo "  sudo systemctl start ruuvi-thingspeak.service"
fi

# Zusammenfassung
echo ""
echo "=========================================="
echo "Setup abgeschlossen! ✓"
echo "=========================================="
echo ""
echo "Konfiguration:"
echo "  ThingSpeak API Key: ${API_KEY:0:8}..."
echo "  Upload-Intervall: $INTERVAL Sekunden"
echo ""
echo "Nützliche Befehle:"
echo ""
echo "  Logs live ansehen:"
echo "    sudo journalctl -u ruuvi-thingspeak.service -f"
echo ""
echo "  Service neu starten:"
echo "    sudo systemctl restart ruuvi-thingspeak.service"
echo ""
echo "  ThingSpeak Channel:"
echo "    https://thingspeak.com/channels"
echo ""
echo "Fertig! Deine Daten sollten jetzt zu ThingSpeak hochgeladen werden."
echo ""
