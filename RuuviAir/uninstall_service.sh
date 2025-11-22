#!/bin/bash
# Ruuvi Scanner Service - Uninstallation Script
# Entfernt den Ruuvi Scanner Service

set -e

echo "=========================================="
echo "Ruuvi Scanner Service - Deinstallation"
echo "=========================================="
echo ""

SERVICE_NAME="ruuvi-scanner.service"

# Prüfe ob Service existiert
if ! systemctl list-unit-files | grep -q "$SERVICE_NAME"; then
    echo "❌ Service $SERVICE_NAME ist nicht installiert"
    exit 0
fi

# Service stoppen
echo "Stoppe Service..."
sudo systemctl stop $SERVICE_NAME 2>/dev/null || true
echo "✓ Service gestoppt"

# Service deaktivieren
echo "Deaktiviere Autostart..."
sudo systemctl disable $SERVICE_NAME 2>/dev/null || true
echo "✓ Autostart deaktiviert"

# Service-Datei entfernen
echo "Entferne Service-Datei..."
sudo rm -f /etc/systemd/system/$SERVICE_NAME
echo "✓ Service-Datei entfernt"

# Systemd neu laden
echo "Lade systemd neu..."
sudo systemctl daemon-reload
echo "✓ Systemd neu geladen"

# Systemd-Cache resetten
sudo systemctl reset-failed 2>/dev/null || true

echo ""
echo "=========================================="
echo "Deinstallation abgeschlossen! ✓"
echo "=========================================="
echo ""
echo "Hinweise:"
echo "  - Die Datenbank wurde NICHT gelöscht"
echo "  - Die Scanner-Skripte wurden NICHT gelöscht"
echo "  - Die venv wurde NICHT gelöscht"
echo ""
echo "Falls du alles entfernen möchtest:"
echo "  rm -rf /home/hellhammer/github/Ruuvi_Raspi_Arduino/RuuviAir/ruuvi_data.db"
echo ""
