# Zusätzliche Dependencies für Export-Features installieren

# Basis-Dependencies (bereits installiert)
# bleak>=1.0.0
# flask>=3.0.0

# Neue Dependencies für Export-Features:
pip3 install pandas openpyxl

# Alternative: Alle Dependencies auf einmal
# pip3 install bleak flask pandas openpyxl

# Oder als requirements.txt Datei:
cat > requirements_export.txt << EOF
bleak>=1.0.0
flask>=3.0.0
pandas>=1.3.0
openpyxl>=3.0.0
EOF

# Dann installieren mit:
# pip3 install -r requirements_export.txt