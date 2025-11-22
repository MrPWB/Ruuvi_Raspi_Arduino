#!/usr/bin/env python3
"""
Ruuvi BLE Format 6 Data Scanner with ThingSpeak Integration
Scans for Ruuvi devices and uploads data to ThingSpeak cloud
"""

import asyncio
import struct
import sqlite3
import sys
import math
import os
from datetime import datetime
from typing import Optional, Dict, Any
from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

# Import ThingSpeak integration
from thingspeak_integration import ThingSpeakUploader, ThingSpeakQueue

# Ruuvi Manufacturer ID
RUUVI_MANUFACTURER_ID = 0x0499

# Format 6 identifier
FORMAT_6 = 0x06

# Debug mode
DEBUG = True


class RuuviFormat6Decoder:
    """Decoder for Ruuvi Format 6 data"""
    
    @staticmethod
    def decode_luminosity(code: int) -> Optional[float]:
        """Decode logarithmic luminosity value"""
        if code == 255:
            return None
        MAX_VALUE = 65535
        MAX_CODE = 254
        DELTA = math.log(MAX_VALUE + 1) / MAX_CODE
        return math.exp(code * DELTA) - 1
    
    @staticmethod
    def decode(data: bytes) -> Optional[Dict[str, Any]]:
        """Decode Ruuvi Format 6 data"""
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
        
        # PM 2.5
        pm2_5_raw = struct.unpack('>H', data[7:9])[0]
        result['pm2_5'] = None if pm2_5_raw == 65535 else pm2_5_raw * 0.1
        
        # CO2
        co2_raw = struct.unpack('>H', data[9:11])[0]
        result['co2'] = None if co2_raw == 65535 else co2_raw
        
        # VOC
        voc_high = data[11]
        voc_low_bit = (data[16] >> 6) & 0x01
        voc_raw = (voc_high << 1) | voc_low_bit
        result['voc'] = None if voc_raw == 511 else voc_raw
        
        # NOX
        nox_high = data[12]
        nox_low_bit = (data[16] >> 7) & 0x01
        nox_raw = (nox_high << 1) | nox_low_bit
        result['nox'] = None if nox_raw == 511 else nox_raw
        
        # Luminosity
        luminosity_code = data[13]
        result['luminosity'] = RuuviFormat6Decoder.decode_luminosity(luminosity_code)
        
        # Sequence
        result['measurement_sequence'] = data[15]
        
        # Flags
        result['calibration_in_progress'] = bool(data[16] & 0x01)
        
        # Short MAC
        mac_bytes = data[17:20]
        if mac_bytes == b'\xff\xff\xff':
            result['mac_short'] = None
        else:
            result['mac_short'] = ':'.join(f'{b:02X}' for b in mac_bytes)
        
        return result


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
                mac TEXT,
                temperature REAL,
                humidity REAL,
                pressure INTEGER,
                pm2_5 REAL,
                co2 INTEGER,
                voc INTEGER,
                nox INTEGER,
                luminosity REAL,
                measurement_sequence INTEGER,
                calibration_in_progress INTEGER,
                rssi INTEGER
            )
        ''')
        
        try:
            cursor.execute('ALTER TABLE ruuvi_measurements ADD COLUMN mac_short TEXT')
            self.conn.commit()
        except sqlite3.OperationalError:
            pass
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON ruuvi_measurements(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_mac ON ruuvi_measurements(mac)')
        
        self.conn.commit()
    
    def insert_measurement(self, data: Dict[str, Any], rssi: int, mac_full: str):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO ruuvi_measurements (
                timestamp, mac, mac_short, temperature, humidity, pressure,
                pm2_5, co2, voc, nox, luminosity, measurement_sequence, 
                calibration_in_progress, rssi
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['timestamp'], mac_full, data.get('mac_short'),
            data.get('temperature'), data.get('humidity'), data.get('pressure'),
            data.get('pm2_5'), data.get('co2'), data.get('voc'), data.get('nox'),
            data.get('luminosity'), data.get('measurement_sequence'),
            1 if data.get('calibration_in_progress') else 0, rssi
        ))
        self.conn.commit()
    
    def close(self):
        self.conn.close()


class RuuviScanner:
    """BLE scanner for Ruuvi devices with ThingSpeak integration"""
    
    def __init__(self, db: RuuviDatabase, thingspeak: Optional[ThingSpeakQueue] = None):
        self.db = db
        self.decoder = RuuviFormat6Decoder()
        self.thingspeak = thingspeak
        self.last_sequences = {}
        self.device_count = 0
        self.ruuvi_count = 0
        self.format6_count = 0
    
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
            return False
    
    def detection_callback(self, device: BLEDevice, advertisement_data: AdvertisementData):
        """Callback for BLE device detection"""
        self.device_count += 1
        
        if DEBUG:
            print(f"\n[DEBUG] Device #{self.device_count}: {device.name or 'Unknown'} ({device.address})")
            print(f"[DEBUG] RSSI: {advertisement_data.rssi if hasattr(advertisement_data, 'rssi') else 'N/A'} dBm")
        
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
                print(f"[DEBUG] ✗ Not Format 6")
            return
        
        self.format6_count += 1
        
        if DEBUG:
            print(f"[DEBUG] ✓ Format 6 successfully decoded!")
        
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
        
        # Store in database
        self.db.insert_measurement(decoded, rssi, mac)
        
        # Upload to ThingSpeak
        if self.thingspeak:
            self.thingspeak.add(decoded)
        
        # Print measurement
        print(f"\n{'='*60}")
        print(f"[{decoded['timestamp']}] Ruuvi Air: {mac}")
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
        if decoded.get('nox') is not None:
            print(f"  NOX: {decoded['nox']}")
        if decoded.get('luminosity') is not None:
            print(f"  Luminosity: {decoded['luminosity']:.2f} lux")
        print(f"{'='*60}\n")
    
    async def scan(self, duration: Optional[float] = None):
        """Start scanning"""
        if not await self.check_bluetooth():
            return
        
        scanner = BleakScanner(detection_callback=self.detection_callback)
        
        print("Starting Ruuvi Format 6 scanner with ThingSpeak...")
        if self.thingspeak:
            interval = self.thingspeak.uploader.interval
            print(f"ThingSpeak upload interval: {interval} seconds")
        print("Press Ctrl+C to stop\n")
        
        await scanner.start()
        try:
            counter = 0
            while True:
                await asyncio.sleep(1)
                counter += 1
                
                # Process ThingSpeak queue
                if self.thingspeak and counter % 1 == 0:  # Check every second
                    if self.thingspeak.process():
                        stats = self.thingspeak.uploader.get_stats()
                        print(f"[ThingSpeak] ✓ Upload successful (Total: {stats['uploads']}, Errors: {stats['errors']})")
                
                # Print statistics every 30 seconds
                if counter % 30 == 0:
                    print(f"\n{'='*60}")
                    print(f"STATISTICS (after {counter}s)")
                    print(f"{'='*60}")
                    print(f"Total BLE devices: {self.device_count}")
                    print(f"Ruuvi devices: {self.ruuvi_count}")
                    print(f"Format 6 devices: {self.format6_count}")
                    if self.thingspeak:
                        stats = self.thingspeak.uploader.get_stats()
                        print(f"ThingSpeak uploads: {stats['uploads']}")
                        print(f"ThingSpeak errors: {stats['errors']}")
                    print(f"{'='*60}\n")
                    
        except KeyboardInterrupt:
            print("\nStopping...")
            await scanner.stop()


async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Ruuvi Format 6 Scanner with ThingSpeak')
    parser.add_argument('--no-debug', action='store_true', help='Disable debug')
    parser.add_argument('--db', default='ruuvi_data.db', help='Database path')
    parser.add_argument('--thingspeak-key', help='ThingSpeak Write API Key')
    parser.add_argument('--thingspeak-interval', type=int, default=15, 
                       help='ThingSpeak upload interval in seconds (default: 15)')
    args = parser.parse_args()
    
    global DEBUG
    DEBUG = not args.no_debug
    
    if DEBUG:
        print("\n" + "="*60)
        print("RUUVI FORMAT 6 SCANNER WITH THINGSPEAK")
        print("="*60 + "\n")
    
    # Initialize ThingSpeak
    thingspeak_queue = None
    if args.thingspeak_key:
        print(f"✓ ThingSpeak enabled (interval: {args.thingspeak_interval}s)")
        uploader = ThingSpeakUploader(args.thingspeak_key, interval=args.thingspeak_interval)
        thingspeak_queue = ThingSpeakQueue(uploader)
    else:
        # Try to get from environment
        api_key = os.getenv('THINGSPEAK_API_KEY')
        if api_key:
            print(f"✓ ThingSpeak enabled from environment (interval: {args.thingspeak_interval}s)")
            uploader = ThingSpeakUploader(api_key, interval=args.thingspeak_interval)
            thingspeak_queue = ThingSpeakQueue(uploader)
        else:
            print("ℹ ThingSpeak disabled (no API key provided)")
            print("  Use --thingspeak-key YOUR_KEY or set THINGSPEAK_API_KEY environment variable")
    
    # Initialize database
    db = RuuviDatabase(args.db)
    
    try:
        scanner = RuuviScanner(db, thingspeak_queue)
        await scanner.scan()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        db.close()
        print("Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
