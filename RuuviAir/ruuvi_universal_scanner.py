#!/usr/bin/env python3
"""
Universal Ruuvi BLE Scanner for Raspberry Pi
Supports both Format 6 (Ruuvi Air) and Format E1 (Extended)
Automatically detects and decodes the correct format
"""

import asyncio
import struct
import sqlite3
import sys
import math
from datetime import datetime
from typing import Optional, Dict, Any
from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

# Ruuvi Manufacturer ID
RUUVI_MANUFACTURER_ID = 0x0499

# Format identifiers
FORMAT_6 = 0x06
FORMAT_E1 = 0xE1

# Debug mode
DEBUG = True


class RuuviUniversalDecoder:
    """Universal decoder for Ruuvi formats"""
    
    @staticmethod
    def decode_luminosity_format6(code: int) -> Optional[float]:
        """Decode Format 6 logarithmic luminosity"""
        if code == 255:
            return None
        MAX_VALUE = 65535
        MAX_CODE = 254
        DELTA = math.log(MAX_VALUE + 1) / MAX_CODE
        return math.exp(code * DELTA) - 1
    
    @staticmethod
    def decode_format6(data: bytes) -> Optional[Dict[str, Any]]:
        """Decode Format 6 (20 bytes)"""
        if len(data) < 20 or data[0] != FORMAT_6:
            return None
        
        result = {'format': 'Format 6', 'timestamp': datetime.now().isoformat()}
        
        # Temperature
        temp_raw = struct.unpack('>h', data[1:3])[0]
        result['temperature'] = None if temp_raw == -32768 else temp_raw * 0.005
        
        # Humidity
        humidity_raw = struct.unpack('>H', data[3:5])[0]
        result['humidity'] = None if humidity_raw == 65535 else humidity_raw * 0.0025
        
        # Pressure
        pressure_raw = struct.unpack('>H', data[5:7])[0]
        result['pressure'] = None if pressure_raw == 65535 else pressure_raw + 50000
        
        # PM 2.5 only
        pm2_5_raw = struct.unpack('>H', data[7:9])[0]
        result['pm2_5'] = None if pm2_5_raw == 65535 else pm2_5_raw * 0.1
        
        # CO2
        co2_raw = struct.unpack('>H', data[9:11])[0]
        result['co2'] = None if co2_raw == 65535 else co2_raw
        
        # VOC (9 bits)
        voc_high = data[11]
        voc_low_bit = (data[16] >> 6) & 0x01
        voc_raw = (voc_high << 1) | voc_low_bit
        result['voc'] = None if voc_raw == 511 else voc_raw
        
        # NOX (9 bits)
        nox_high = data[12]
        nox_low_bit = (data[16] >> 7) & 0x01
        nox_raw = (nox_high << 1) | nox_low_bit
        result['nox'] = None if nox_raw == 511 else nox_raw
        
        # Luminosity (logarithmic)
        luminosity_code = data[13]
        result['luminosity'] = RuuviUniversalDecoder.decode_luminosity_format6(luminosity_code)
        
        # Sequence
        result['measurement_sequence'] = data[15]
        
        # Flags
        result['calibration_in_progress'] = bool(data[16] & 0x01)
        
        # Short MAC
        result['mac_short'] = ':'.join(f'{b:02X}' for b in data[17:20])
        
        return result
    
    @staticmethod
    def decode_format_e1(data: bytes) -> Optional[Dict[str, Any]]:
        """Decode Format E1 (40 bytes)"""
        if len(data) < 40 or data[0] != FORMAT_E1:
            return None
        
        result = {'format': 'Format E1', 'timestamp': datetime.now().isoformat()}
        
        # Temperature
        temp_raw = struct.unpack('>h', data[1:3])[0]
        result['temperature'] = None if temp_raw == -32768 else temp_raw * 0.005
        
        # Humidity
        humidity_raw = struct.unpack('>H', data[3:5])[0]
        result['humidity'] = None if humidity_raw == 65535 else humidity_raw * 0.0025
        
        # Pressure
        pressure_raw = struct.unpack('>H', data[5:7])[0]
        result['pressure'] = None if pressure_raw == 65535 else pressure_raw + 50000
        
        # PM values (all 4)
        pm1_raw = struct.unpack('>H', data[7:9])[0]
        result['pm1_0'] = None if pm1_raw == 65535 else pm1_raw * 0.1
        
        pm2_5_raw = struct.unpack('>H', data[9:11])[0]
        result['pm2_5'] = None if pm2_5_raw == 65535 else pm2_5_raw * 0.1
        
        pm4_raw = struct.unpack('>H', data[11:13])[0]
        result['pm4_0'] = None if pm4_raw == 65535 else pm4_raw * 0.1
        
        pm10_raw = struct.unpack('>H', data[13:15])[0]
        result['pm10_0'] = None if pm10_raw == 65535 else pm10_raw * 0.1
        
        # CO2
        co2_raw = struct.unpack('>H', data[15:17])[0]
        result['co2'] = None if co2_raw == 65535 else co2_raw
        
        # VOC (9 bits)
        voc_high = data[17]
        voc_low_bit = (data[28] >> 6) & 0x01
        voc_raw = (voc_high << 1) | voc_low_bit
        result['voc'] = None if voc_raw == 511 else voc_raw
        
        # NOX (9 bits)
        nox_high = data[18]
        nox_low_bit = (data[28] >> 7) & 0x01
        nox_raw = (nox_high << 1) | nox_low_bit
        result['nox'] = None if nox_raw == 511 else nox_raw
        
        # Luminosity (24-bit linear)
        luminosity_raw = struct.unpack('>I', b'\x00' + data[19:22])[0]
        result['luminosity'] = None if luminosity_raw == 16777215 else luminosity_raw * 0.01
        
        # Sequence (24-bit)
        seq_raw = struct.unpack('>I', b'\x00' + data[25:28])[0]
        result['measurement_sequence'] = None if seq_raw == 16777215 else seq_raw
        
        # Flags
        result['calibration_in_progress'] = bool(data[28] & 0x01)
        
        # Full MAC
        mac_bytes = data[34:40]
        if mac_bytes == b'\xff\xff\xff\xff\xff\xff':
            result['mac'] = None
        else:
            result['mac'] = ':'.join(f'{b:02X}' for b in mac_bytes)
        
        return result
    
    @staticmethod
    def decode(data: bytes) -> Optional[Dict[str, Any]]:
        """Auto-detect format and decode"""
        if len(data) < 1:
            return None
        
        format_byte = data[0]
        
        if format_byte == FORMAT_6:
            return RuuviUniversalDecoder.decode_format6(data)
        elif format_byte == FORMAT_E1:
            return RuuviUniversalDecoder.decode_format_e1(data)
        else:
            return None


class RuuviDatabase:
    """SQLite database handler for Ruuvi data"""
    
    def __init__(self, db_path: str = 'ruuvi_data.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.create_tables()
    
    def create_tables(self):
        """Create database tables if they don't exist"""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ruuvi_measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                format TEXT,
                mac TEXT,
                mac_short TEXT,
                temperature REAL,
                humidity REAL,
                pressure INTEGER,
                pm1_0 REAL,
                pm2_5 REAL,
                pm4_0 REAL,
                pm10_0 REAL,
                co2 INTEGER,
                voc INTEGER,
                nox INTEGER,
                luminosity REAL,
                measurement_sequence INTEGER,
                calibration_in_progress INTEGER,
                rssi INTEGER
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON ruuvi_measurements(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mac ON ruuvi_measurements(mac)')
        
        self.conn.commit()
    
    def insert_measurement(self, data: Dict[str, Any], rssi: int, mac_full: str):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO ruuvi_measurements (
                timestamp, format, mac, mac_short, temperature, humidity, pressure,
                pm1_0, pm2_5, pm4_0, pm10_0, co2, voc, nox,
                luminosity, measurement_sequence, calibration_in_progress, rssi
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['timestamp'], data.get('format'), mac_full, data.get('mac_short'),
            data.get('temperature'), data.get('humidity'), data.get('pressure'),
            data.get('pm1_0'), data.get('pm2_5'), data.get('pm4_0'), data.get('pm10_0'),
            data.get('co2'), data.get('voc'), data.get('nox'), data.get('luminosity'),
            data.get('measurement_sequence'),
            1 if data.get('calibration_in_progress') else 0, rssi
        ))
        self.conn.commit()
    
    def close(self):
        self.conn.close()


class RuuviScanner:
    """BLE scanner for Ruuvi devices"""
    
    def __init__(self, db: RuuviDatabase):
        self.db = db
        self.decoder = RuuviUniversalDecoder()
        self.last_sequences = {}
        self.device_count = 0
        self.ruuvi_count = 0
        self.format6_count = 0
        self.format_e1_count = 0
    
    async def check_bluetooth(self):
        """Check if Bluetooth adapter is available"""
        print("\n" + "="*60)
        print("BLUETOOTH SYSTEM CHECK")
        print("="*60)
        
        try:
            devices = await BleakScanner.discover(timeout=1.0, return_adv=False)
            print(f"✓ Bluetooth adapter is working")
            print(f"✓ Quick scan found {len(devices)} BLE device(s)")
            print(f"✓ Python version: {sys.version.split()[0]}")
            
            try:
                import bleak
                if hasattr(bleak, '__version__'):
                    print(f"✓ Bleak version: {bleak.__version__}")
                else:
                    print(f"✓ Bleak installed")
            except:
                print(f"✓ Bleak installed")
            
            print("="*60 + "\n")
            return True
            
        except Exception as e:
            print(f"✗ Bluetooth adapter check failed: {e}")
            print("\nTroubleshooting:")
            print("  1. Check if Bluetooth is enabled: bluetoothctl power on")
            print("  2. Try running with sudo: sudo python3 ruuvi_universal_scanner.py")
            print("  3. Check if bluetooth service is running: sudo systemctl status bluetooth")
            print("="*60 + "\n")
            return False
    
    def detection_callback(self, device: BLEDevice, advertisement_data: AdvertisementData):
        """Callback for BLE device detection"""
        self.device_count += 1
        
        if DEBUG:
            print(f"\n[DEBUG] Device #{self.device_count}: {device.name or 'Unknown'} ({device.address})")
            print(f"[DEBUG] RSSI: {advertisement_data.rssi if hasattr(advertisement_data, 'rssi') else 'N/A'} dBm")
            
            if advertisement_data.manufacturer_data:
                print(f"[DEBUG] Manufacturer data found:")
                for mfg_id, data in advertisement_data.manufacturer_data.items():
                    print(f"[DEBUG]   ID: 0x{mfg_id:04X} ({mfg_id})")
                    print(f"[DEBUG]   Data length: {len(data)} bytes")
                    print(f"[DEBUG]   Raw hex: {data.hex()}")
                    if len(data) > 0:
                        print(f"[DEBUG]   Format byte: 0x{data[0]:02X} ({data[0]})")
            else:
                print(f"[DEBUG] No manufacturer data")
        
        if RUUVI_MANUFACTURER_ID not in advertisement_data.manufacturer_data:
            if DEBUG:
                print(f"[DEBUG] Not a Ruuvi device")
            return
        
        self.ruuvi_count += 1
        mfg_data = advertisement_data.manufacturer_data[RUUVI_MANUFACTURER_ID]
        
        if DEBUG:
            print(f"[DEBUG] ✓ Ruuvi device detected!")
        
        decoded = self.decoder.decode(mfg_data)
        
        if decoded is None:
            if DEBUG:
                print(f"[DEBUG] ✗ Unknown or unsupported format: 0x{mfg_data[0]:02X}")
            return
        
        # Count formats
        if decoded['format'] == 'Format 6':
            self.format6_count += 1
        elif decoded['format'] == 'Format E1':
            self.format_e1_count += 1
        
        if DEBUG:
            print(f"[DEBUG] ✓ {decoded['format']} successfully decoded!")
        
        # Check duplicates
        mac = device.address
        seq = decoded.get('measurement_sequence')
        if seq is not None:
            if mac in self.last_sequences and self.last_sequences[mac] == seq:
                if DEBUG:
                    print(f"[DEBUG] Duplicate, skipping")
                return
            self.last_sequences[mac] = seq
        
        rssi = advertisement_data.rssi if hasattr(advertisement_data, 'rssi') else None
        self.db.insert_measurement(decoded, rssi, mac)
        
        # Print measurement
        print(f"\n{'='*60}")
        print(f"[{decoded['timestamp']}] {decoded['format']}: {mac}")
        print(f"{'='*60}")
        print(f"  RSSI: {rssi} dBm")
        if decoded.get('temperature') is not None:
            print(f"  Temperature: {decoded['temperature']:.2f}°C")
        if decoded.get('humidity') is not None:
            print(f"  Humidity: {decoded['humidity']:.2f}%")
        if decoded.get('pressure') is not None:
            print(f"  Pressure: {decoded['pressure']} Pa")
        if decoded.get('pm2_5') is not None:
            print(f"  PM2.5: {decoded['pm2_5']:.1f} µg/m³")
        if decoded.get('co2') is not None:
            print(f"  CO2: {decoded['co2']} ppm")
        if decoded.get('voc') is not None:
            print(f"  VOC: {decoded['voc']}")
        if decoded.get('luminosity') is not None:
            print(f"  Luminosity: {decoded['luminosity']:.2f} lux")
        print(f"{'='*60}\n")
    
    async def scan(self, duration: Optional[float] = None):
        """Start scanning"""
        if not await self.check_bluetooth():
            return
        
        scanner = BleakScanner(detection_callback=self.detection_callback)
        
        print("Starting Universal Ruuvi Scanner...")
        print("Supports: Format 6 (Ruuvi Air) and Format E1 (Extended)")
        print("Press Ctrl+C to stop\n")
        
        await scanner.start()
        try:
            counter = 0
            while True:
                await asyncio.sleep(10)
                counter += 10
                
                if counter % 30 == 0:
                    print(f"\n{'='*60}")
                    print(f"STATISTICS (after {counter}s)")
                    print(f"{'='*60}")
                    print(f"Total BLE devices: {self.device_count}")
                    print(f"Ruuvi devices: {self.ruuvi_count}")
                    print(f"Format 6: {self.format6_count}")
                    print(f"Format E1: {self.format_e1_count}")
                    print(f"{'='*60}\n")
                    
        except KeyboardInterrupt:
            print("\nStopping...")
            await scanner.stop()


async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Universal Ruuvi Scanner')
    parser.add_argument('--no-debug', action='store_true', help='Disable debug')
    parser.add_argument('--db', default='ruuvi_data.db', help='Database path')
    args = parser.parse_args()
    
    global DEBUG
    DEBUG = not args.no_debug
    
    if DEBUG:
        print("\n" + "="*60)
        print("UNIVERSAL RUUVI SCANNER")
        print("="*60)
        print("Auto-detects Format 6 and Format E1")
        print("="*60 + "\n")
    
    db = RuuviDatabase(args.db)
    
    try:
        scanner = RuuviScanner(db)
        await scanner.scan()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        db.close()
        print("Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
