#!/bin/bash
# Git Commit Script - Ruuvi Air Scanner
# Kopiert alle neuen Dateien und committed sie ins Repository

set -e

echo "=========================================="
echo "Ruuvi Scanner - Git Commit"
echo "=========================================="
echo ""

# Pfade
REPO_DIR="/home/hellhammer/github/Ruuvi_Raspi_Arduino"
SOURCE_DIR="/mnt/user-data/outputs"

# Prüfe ob Repository existiert
if [ ! -d "$REPO_DIR/.git" ]; then
    echo "❌ Fehler: Git-Repository nicht gefunden in $REPO_DIR"
    exit 1
fi

cd "$REPO_DIR"

# Erstelle RuuviAir Verzeichnis falls es nicht existiert
mkdir -p RuuviAir

echo "Kopiere Dateien..."

# Hauptskripte
cp "$SOURCE_DIR/ruuvi_format6_scanner.py" RuuviAir/
cp "$SOURCE_DIR/ruuvi_universal_scanner.py" RuuviAir/
cp "$SOURCE_DIR/ruuvi_e1_scanner.py" RuuviAir/

# Query Tools
cp "$SOURCE_DIR/query_ruuvi_format6.py" RuuviAir/
cp "$SOURCE_DIR/query_ruuvi_data.py" RuuviAir/

# Test & Debug
cp "$SOURCE_DIR/test_bluetooth.py" RuuviAir/

# Service-Dateien
cp "$SOURCE_DIR/ruuvi-scanner.service" RuuviAir/
cp "$SOURCE_DIR/install_service.sh" RuuviAir/
cp "$SOURCE_DIR/uninstall_service.sh" RuuviAir/

# Dokumentation
cp "$SOURCE_DIR/README_FORMAT6.md" RuuviAir/
cp "$SOURCE_DIR/SERVICE_INSTALLATION.md" RuuviAir/
cp "$SOURCE_DIR/DEBUG_GUIDE.md" RuuviAir/
cp "$SOURCE_DIR/README.md" RuuviAir/

# Requirements
cp "$SOURCE_DIR/requirements.txt" RuuviAir/

# Gitignore
cp "$SOURCE_DIR/.gitignore" RuuviAir/

# Haupt-README (ins Root)
cp "$SOURCE_DIR/README_PROJECT.md" README.md

# Executable machen
chmod +x RuuviAir/install_service.sh
chmod +x RuuviAir/uninstall_service.sh
chmod +x RuuviAir/*.py

echo "✓ Dateien kopiert"

# Git Status
echo ""
echo "Git Status:"
git status --short

# Git add
echo ""
echo "Füge Dateien zu Git hinzu..."
git add RuuviAir/
git add README.md

# Git commit
echo ""
echo "Erstelle Commit..."
COMMIT_MSG="Add Ruuvi Air Format 6 Scanner with systemd service

- Add Format 6 BLE scanner for Ruuvi Air
- Add universal scanner supporting Format 6 and E1
- Add query tools for database analysis
- Add systemd service configuration
- Add installation and management scripts
- Add comprehensive documentation
- Add Bluetooth test tool
- Configure virtual environment support"

git commit -m "$COMMIT_MSG"

echo "✓ Commit erstellt"

# Zeige Commit
echo ""
echo "Letzter Commit:"
git log -1 --oneline

# Frage ob pushen
echo ""
read -p "Möchtest du zum Remote-Repository pushen? (j/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Jj]$ ]]; then
    echo "Pushe zum Remote..."
    git push
    echo "✓ Push erfolgreich"
else
    echo "Überspringe Push. Du kannst später manuell pushen mit:"
    echo "  git push"
fi

echo ""
echo "=========================================="
echo "Git Commit abgeschlossen! ✓"
echo "=========================================="
echo ""
echo "Dateien wurden committed:"
git diff --name-only HEAD~1 HEAD
echo ""
