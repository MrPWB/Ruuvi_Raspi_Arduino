#!/bin/bash
# Ruuvi Scanner Service - Quick Installation Script
# Installiert den Ruuvi Format 6 Scanner als systemd Service

set -e

echo "=========================================="
echo "Ruuvi Scanner Service - Installation"
echo "=========================================="
echo ""

# Variablen
BASE_DIR="/home/hellhammer/github/Ruuvi_Raspi_Arduino"
VENV_DIR="$BASE_DIR/venv"
RUUVI_DIR="$BASE_DIR/RuuviAir"
SERVICE_FILE="ruuvi-scanner.service"
PYTHON_BIN="$VENV_DIR/bin/python3"

# Prüfe ob das Verzeichnis existiert
if [ ! -d "$BASE_DIR" ]; then
    echo "❌ Fehler: Verzeichnis $BASE_DIR existiert nicht!"
    exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Fehler: Virtual Environment $VENV_DIR existiert nicht!"
    echo "Erstelle venv mit: python3 -m venv $VENV_DIR"
    exit 1
fi

echo "✓ Verzeichnisse gefunden"

# Prüfe ob Python-Dateien existieren
if [ ! -f "$RUUVI_DIR/ruuvi_format6_scanner.py" ]; then
    echo "❌ Fehler: Scanner-Skript nicht gefunden!"
    exit 1
fi

echo "✓ Scanner-Skript gefunden"

# Installiere Dependencies in venv
echo ""
echo "Installiere Python-Dependencies in venv..."
source "$VENV_DIR/bin/activate"
pip install bleak --quiet
deactivate
echo "✓ Dependencies installiert"

# Setze Bluetooth-Berechtigungen
echo ""
echo "Setze Bluetooth-Berechtigungen für Python..."
sudo setcap cap_net_raw,cap_net_admin+eip "$PYTHON_BIN"
echo "✓ Berechtigungen gesetzt"

# Kopiere Service-Datei
echo ""
echo "Installiere systemd Service..."
if [ -f "$RUUVI_DIR/$SERVICE_FILE" ]; then
    sudo cp "$RUUVI_DIR/$SERVICE_FILE" /etc/systemd/system/
    sudo chmod 644 /etc/systemd/system/$SERVICE_FILE
    echo "✓ Service-Datei kopiert"
else
    echo "❌ Fehler: Service-Datei nicht gefunden!"
    echo "Bitte stelle sicher, dass $SERVICE_FILE in $RUUVI_DIR liegt"
    exit 1
fi

# Systemd neu laden
echo ""
echo "Lade systemd-Konfiguration neu..."
sudo systemctl daemon-reload
echo "✓ Systemd neu geladen"

# Service aktivieren
echo ""
echo "Aktiviere Service für Autostart..."
sudo systemctl enable ruuvi-scanner.service
echo "✓ Service aktiviert"

# Service starten
echo ""
echo "Starte Ruuvi Scanner Service..."
sudo systemctl start ruuvi-scanner.service
sleep 2
echo "✓ Service gestartet"

# Status prüfen
echo ""
echo "=========================================="
echo "Service-Status:"
echo "=========================================="
sudo systemctl status ruuvi-scanner.service --no-pager -l

echo ""
echo "=========================================="
echo "Installation abgeschlossen! ✓"
echo "=========================================="
echo ""
echo "Nützliche Befehle:"
echo ""
echo "  Status anzeigen:"
echo "    sudo systemctl status ruuvi-scanner.service"
echo ""
echo "  Logs verfolgen:"
echo "    sudo journalctl -u ruuvi-scanner.service -f"
echo ""
echo "  Service stoppen:"
echo "    sudo systemctl stop ruuvi-scanner.service"
echo ""
echo "  Service neustarten:"
echo "    sudo systemctl restart ruuvi-scanner.service"
echo ""
echo "  Datenbank abfragen:"
echo "    cd $RUUVI_DIR"
echo "    python3 query_ruuvi_format6.py --latest 10"
echo ""
