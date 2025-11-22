# Ruuvi Scanner - Debug Guide

## Quick Start mit Debug-Ausgaben

Das Skript hat jetzt umfangreiche Debug-Ausgaben eingebaut, die dir helfen herauszufinden, warum dein Ruuvi Air nicht erkannt wird.

### Skript starten

```bash
sudo python3 ruuvi_e1_scanner.py
```

Das Skript läuft standardmäßig im **DEBUG-Modus** und zeigt:

1. ✅ **Bluetooth System Check** beim Start
   - Adapter-Status
   - Python & Bleak Version
   - Anzahl erkannter Geräte

2. 🔍 **Alle BLE-Geräte** die erkannt werden
   - Name und MAC-Adresse
   - RSSI (Signalstärke)
   - Manufacturer ID
   - Rohdaten in Hex
   - Format-Byte

3. 📊 **Statistiken** alle 30 Sekunden
   - Gesamtzahl BLE-Geräte
   - Anzahl Ruuvi-Geräte
   - Anzahl E1-Format Geräte

## Was die Debug-Ausgaben bedeuten

### Beispiel 1: Ruuvi Air wird gefunden (E1 Format)

```
[DEBUG] Device #5: Ruuvi Air (CB:B8:33:4C:88:4F)
[DEBUG] RSSI: -65 dBm
[DEBUG] Manufacturer data found:
[DEBUG]   ID: 0x0499 (1177)
[DEBUG]   Data length: 40 bytes
[DEBUG]   Raw hex: e1170c5668c79e0065007004bd11ca00c90a0213e0ac3...
[DEBUG]   Format byte: 0xE1 (225)
[DEBUG] ✓ Ruuvi device detected!
[DEBUG] Data format byte: 0xE1
[DEBUG] ✓ E1 format successfully decoded!
```

### Beispiel 2: Ruuvi gefunden, aber falsches Format

```
[DEBUG] Device #3: Ruuvi (AA:BB:CC:DD:EE:FF)
[DEBUG] RSSI: -72 dBm
[DEBUG] Manufacturer data found:
[DEBUG]   ID: 0x0499 (1177)
[DEBUG]   Data length: 24 bytes
[DEBUG]   Raw hex: 0512fc5394c37c0004fffc040cac364200cdcbb8334c884f
[DEBUG]   Format byte: 0x05 (5)
[DEBUG] ✓ Ruuvi device detected!
[DEBUG] Data format byte: 0x05
[DEBUG] ✗ Not E1 format (expected 0xE1, got 0x05)
[DEBUG] This is likely format 5 (Format 3=RAWv1, Format 5=RAWv2)
```

**→ Das bedeutet:** Dein Ruuvi sendet im Format 5 (RAWv2), nicht E1!

### Beispiel 3: Anderes BLE-Gerät (kein Ruuvi)

```
[DEBUG] Device #2: My Phone (11:22:33:44:55:66)
[DEBUG] RSSI: -45 dBm
[DEBUG] Manufacturer data found:
[DEBUG]   ID: 0x004C (76)
[DEBUG]   Data length: 25 bytes
[DEBUG]   Raw hex: 1005031c6e1f59
[DEBUG]   Format byte: 0x10 (16)
[DEBUG] Not a Ruuvi device (no 0x0499 manufacturer ID)
```

**→ Das bedeutet:** Ein anderes BLE-Gerät (z.B. Apple mit 0x004C)

## Typische Probleme und Lösungen

### Problem 1: "Ruuvi gefunden, aber Format 5 statt E1"

**Ursache:** Dein Ruuvi Air sendet standardmäßig im Format 5 (RAWv2), nicht E1.

**Lösung:** Du musst das Format in den Ruuvi-Einstellungen umstellen:
1. Öffne die Ruuvi Station App
2. Wähle dein Gerät aus
3. Gehe zu "Settings" → "Data Format"
4. Wähle "E1 (Extended)" aus
5. Das Gerät muss Bluetooth 5 Extended Advertising unterstützen

**Alternative:** Ich kann dir auch ein Skript für Format 5 schreiben, wenn dein Gerät kein E1 unterstützt.

### Problem 2: "Bluetooth adapter check failed"

**Ursache:** Bluetooth-Dienst läuft nicht oder keine Berechtigungen.

**Lösungen:**
```bash
# Bluetooth-Status prüfen
sudo systemctl status bluetooth

# Bluetooth starten
sudo systemctl start bluetooth

# Mit sudo laufen lassen
sudo python3 ruuvi_e1_scanner.py

# Oder Berechtigungen setzen
sudo setcap cap_net_raw,cap_net_admin+eip $(eval readlink -f `which python3`)
```

### Problem 3: "Keine Geräte werden erkannt"

**Ursache:** Bluetooth-Scanner findet nichts.

**Lösungen:**
```bash
# Manueller Bluetooth-Scan
sudo hcitool lescan

# Adapter-Info
hciconfig

# bluetoothctl verwenden
bluetoothctl
> scan on
> list
```

### Problem 4: "Gerät wird gefunden, aber zu schwaches Signal"

**Hinweis:** RSSI sollte besser als -80 dBm sein.

**Lösungen:**
- Näher ans Gerät herangehen
- Batteriestand prüfen (schwache Batterie = schwaches Signal)
- Antenne am Raspberry Pi prüfen

## Debug-Modus ausschalten

Wenn alles funktioniert und du die vielen Ausgaben nicht mehr brauchst:

```bash
sudo python3 ruuvi_e1_scanner.py --no-debug
```

Dann siehst du nur noch die erfolgreichen E1-Messungen.

## Statistiken anschauen

Während der Scanner läuft, zeigt er alle 30 Sekunden Statistiken:

```
============================================================
SCAN STATISTICS (after 30 seconds)
============================================================
Total BLE devices detected: 47
Ruuvi devices found: 2
E1 format devices: 1
============================================================
```

## Live-Beispiel für erfolgreiche E1-Erkennung

```
[2025-01-22 10:45:23] Ruuvi Device: CB:B8:33:4C:88:4F
  RSSI: -65 dBm
  Temperature: 21.50°C
  Humidity: 45.25%
  Pressure: 101325 Pa
  PM2.5: 12.3 µg/m³
  CO2: 450 ppm
  VOC Index: 95
  Luminosity: 245.50 lux
```

## Support-Informationen sammeln

Wenn es nicht funktioniert, sammle diese Informationen:

```bash
# Python-Version
python3 --version

# Bleak-Version
pip3 show bleak

# Bluetooth-Status
sudo systemctl status bluetooth

# Adapter-Info
hciconfig

# Scanner-Output (erste 30 Sekunden)
sudo python3 ruuvi_e1_scanner.py | head -n 100
```

Sende mir diese Ausgaben und ich kann dir weiterhelfen!
