#!/usr/bin/env python3
"""
Ruuvi BLE E1 Data Format Scanner for Raspberry Pi
Scans for Ruuvi devices broadcasting E1 format, decodes the data and stores it in SQLite database.
"""

import asyncio
import struct
import sqlite3
import sys
from datetime import datetime
from typing import Optional, Dict, Any
from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

# Ruuvi Manufacturer ID
RUUVI_MANUFACTURER_ID = 0x0499

# E1 Format identifier
E1_FORMAT = 0xE1

# Debug mode
DEBUG = True


class RuuviE1Decoder:
    """Decoder for Ruuvi E1 data format"""
    
    @staticmethod
    def decode(data: bytes) -> Optional[Dict[str, Any]]:
        """
        Decode Ruuvi E1 format data
        
        Args:
            data: Raw manufacturer data bytes
            
        Returns:
            Dictionary with decoded values or None if invalid
        """
        if len(data) < 40:
            return None
            
        # Check format byte
        if data[0] != E1_FORMAT:
            return None
        
        result = {
            'format': 'E1',
            'timestamp': datetime.now().isoformat()
        }
        
        # Temperature (bytes 1-2): signed 16bit, 0.005°C resolution
        temp_raw = struct.unpack('>h', data[1:3])[0]
        result['temperature'] = None if temp_raw == -32768 else temp_raw * 0.005
        
        # Humidity (bytes 3-4): unsigned 16bit, 0.0025% resolution
        humidity_raw = struct.unpack('>H', data[3:5])[0]
        result['humidity'] = None if humidity_raw == 65535 else humidity_raw * 0.0025
        
        # Pressure (bytes 5-6): unsigned 16bit, 1 Pa resolution, -50000 Pa offset
        pressure_raw = struct.unpack('>H', data[5:7])[0]
        result['pressure'] = None if pressure_raw == 65535 else pressure_raw + 50000
        
        # PM 1.0 (bytes 7-8): unsigned 16bit, 0.1 ug/m³ resolution
        pm1_raw = struct.unpack('>H', data[7:9])[0]
        result['pm1_0'] = None if pm1_raw == 65535 else pm1_raw * 0.1
        
        # PM 2.5 (bytes 9-10): unsigned 16bit, 0.1 ug/m³ resolution
        pm2_5_raw = struct.unpack('>H', data[9:11])[0]
        result['pm2_5'] = None if pm2_5_raw == 65535 else pm2_5_raw * 0.1
        
        # PM 4.0 (bytes 11-12): unsigned 16bit, 0.1 ug/m³ resolution
        pm4_raw = struct.unpack('>H', data[11:13])[0]
        result['pm4_0'] = None if pm4_raw == 65535 else pm4_raw * 0.1
        
        # PM 10.0 (bytes 13-14): unsigned 16bit, 0.1 ug/m³ resolution
        pm10_raw = struct.unpack('>H', data[13:15])[0]
        result['pm10_0'] = None if pm10_raw == 65535 else pm10_raw * 0.1
        
        # CO2 (bytes 15-16): unsigned 16bit, 1 ppm resolution
        co2_raw = struct.unpack('>H', data[15:17])[0]
        result['co2'] = None if co2_raw == 65535 else co2_raw
        
        # VOC (byte 17 + flags bit 6): 9 bit unsigned
        voc_high = data[17]
        voc_low_bit = (data[28] >> 6) & 0x01
        voc_raw = (voc_high << 1) | voc_low_bit
        result['voc'] = None if voc_raw == 511 else voc_raw
        
        # NOX (byte 18 + flags bit 7): 9 bit unsigned
        nox_high = data[18]
        nox_low_bit = (data[28] >> 7) & 0x01
        nox_raw = (nox_high << 1) | nox_low_bit
        result['nox'] = None if nox_raw == 511 else nox_raw
        
        # Luminosity (bytes 19-21): 24bit unsigned, 0.01 lux resolution
        luminosity_raw = struct.unpack('>I', b'\x00' + data[19:22])[0]
        result['luminosity'] = None if luminosity_raw == 16777215 else luminosity_raw * 0.01
        
        # Reserved bytes 22-24 (skip)
        
        # Measurement sequence (bytes 25-27): 24bit unsigned
        seq_raw = struct.unpack('>I', b'\x00' + data[25:28])[0]
        result['measurement_sequence'] = None if seq_raw == 16777215 else seq_raw
        
        # Flags (byte 28)
        flags = data[28]
        result['calibration_in_progress'] = bool(flags & 0x01)
        
        # MAC address (bytes 34-39)
        mac_bytes = data[34:40]
        if mac_bytes == b'\xff\xff\xff\xff\xff\xff':
            result['mac'] = None
        else:
            result['mac'] = ':'.join(f'{b:02X}' for b in mac_bytes)
        
        return result


class RuuviDatabase:
    """SQLite database handler for Ruuvi data"""
    
    def __init__(self, db_path: str = 'ruuvi_data.db'):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
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
        
        # Create index on timestamp for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON ruuvi_measurements(timestamp)
        ''')
        
        # Create index on MAC address
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_mac 
            ON ruuvi_measurements(mac)
        ''')
        
        self.conn.commit()
    
    def insert_measurement(self, data: Dict[str, Any], rssi: int):
        """
        Insert a measurement into the database
        
        Args:
            data: Decoded measurement data
            rssi: Signal strength
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO ruuvi_measurements (
                timestamp, mac, temperature, humidity, pressure,
                pm1_0, pm2_5, pm4_0, pm10_0, co2, voc, nox,
                luminosity, measurement_sequence, calibration_in_progress, rssi
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['timestamp'],
            data.get('mac'),
            data.get('temperature'),
            data.get('humidity'),
            data.get('pressure'),
            data.get('pm1_0'),
            data.get('pm2_5'),
            data.get('pm4_0'),
            data.get('pm10_0'),
            data.get('co2'),
            data.get('voc'),
            data.get('nox'),
            data.get('luminosity'),
            data.get('measurement_sequence'),
            1 if data.get('calibration_in_progress') else 0,
            rssi
        ))
        self.conn.commit()
    
    def close(self):
        """Close database connection"""
        self.conn.close()


class RuuviScanner:
    """BLE scanner for Ruuvi devices"""
    
    def __init__(self, db: RuuviDatabase):
        """
        Initialize scanner
        
        Args:
            db: Database handler
        """
        self.db = db
        self.decoder = RuuviE1Decoder()
        self.last_sequences = {}  # Track last sequence per MAC to avoid duplicates
        self.device_count = 0  # Count all detected devices
        self.ruuvi_count = 0   # Count Ruuvi devices
        self.e1_count = 0      # Count E1 format devices
    
    async def check_bluetooth(self):
        """Check if Bluetooth adapter is available and working"""
        print("\n" + "="*60)
        print("BLUETOOTH SYSTEM CHECK")
        print("="*60)
        
        try:
            # Try to get available adapters
            devices = await BleakScanner.discover(timeout=1.0, return_adv=False)
            print(f"✓ Bluetooth adapter is working")
            print(f"✓ Quick scan found {len(devices)} BLE device(s)")
            
            # Check Python version
            print(f"✓ Python version: {sys.version.split()[0]}")
            
            # Check bleak version
            import bleak
            print(f"✓ Bleak version: {bleak.__version__}")
            
            print("="*60 + "\n")
            return True
            
        except Exception as e:
            print(f"✗ Bluetooth adapter check failed: {e}")
            print("\nTroubleshooting:")
            print("  1. Check if Bluetooth is enabled: bluetoothctl power on")
            print("  2. Try running with sudo: sudo python3 ruuvi_e1_scanner.py")
            print("  3. Check if bluetooth service is running: sudo systemctl status bluetooth")
            print("="*60 + "\n")
            return False
    
    def detection_callback(self, device: BLEDevice, advertisement_data: AdvertisementData):
        """
        Callback for BLE device detection
        
        Args:
            device: Detected BLE device
            advertisement_data: Advertisement data
        """
        self.device_count += 1
        
        if DEBUG:
            print(f"\n[DEBUG] Device #{self.device_count}: {device.name or 'Unknown'} ({device.address})")
            print(f"[DEBUG] RSSI: {advertisement_data.rssi if hasattr(advertisement_data, 'rssi') else 'N/A'} dBm")
            
            # Show all manufacturer data
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
            
            # Show service UUIDs
            if advertisement_data.service_uuids:
                print(f"[DEBUG] Service UUIDs: {advertisement_data.service_uuids}")
        
        # Check if this is a Ruuvi device
        if RUUVI_MANUFACTURER_ID not in advertisement_data.manufacturer_data:
            if DEBUG:
                print(f"[DEBUG] Not a Ruuvi device (no 0x0499 manufacturer ID)")
            return
        
        self.ruuvi_count += 1
        
        # Get manufacturer data
        mfg_data = advertisement_data.manufacturer_data[RUUVI_MANUFACTURER_ID]
        
        if DEBUG:
            print(f"[DEBUG] ✓ Ruuvi device detected!")
            print(f"[DEBUG] Data format byte: 0x{mfg_data[0]:02X}")
        
        # Decode E1 format
        decoded = self.decoder.decode(mfg_data)
        
        if decoded is None:
            if DEBUG:
                if mfg_data[0] != E1_FORMAT:
                    print(f"[DEBUG] ✗ Not E1 format (expected 0xE1, got 0x{mfg_data[0]:02X})")
                    print(f"[DEBUG] This is likely format {mfg_data[0]} (Format 3=RAWv1, Format 5=RAWv2)")
                else:
                    print(f"[DEBUG] ✗ E1 format but decode failed (data too short?)")
            return
        
        self.e1_count += 1
        
        if DEBUG:
            print(f"[DEBUG] ✓ E1 format successfully decoded!")
        
        # Check if this is a duplicate based on measurement sequence
        mac = decoded.get('mac') or device.address
        seq = decoded.get('measurement_sequence')
        
        if seq is not None:
            if mac in self.last_sequences and self.last_sequences[mac] == seq:
                return  # Skip duplicate
            self.last_sequences[mac] = seq
        
        # Get RSSI
        rssi = advertisement_data.rssi if hasattr(advertisement_data, 'rssi') else None
        
        # Store in database
        self.db.insert_measurement(decoded, rssi)
        
        # Print to console
        print(f"\n[{decoded['timestamp']}] Ruuvi Device: {mac}")
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
            print(f"  VOC Index: {decoded['voc']}")
        if decoded.get('luminosity') is not None:
            print(f"  Luminosity: {decoded['luminosity']:.2f} lux")
        if decoded.get('calibration_in_progress'):
            print(f"  ⚠️  Calibration in progress")
    
    async def scan(self, duration: Optional[float] = None):
        """
        Start scanning for Ruuvi devices
        
        Args:
            duration: Scan duration in seconds (None for continuous)
        """
        # Check Bluetooth first
        if not await self.check_bluetooth():
            return
        
        scanner = BleakScanner(detection_callback=self.detection_callback)
        
        print("Starting Ruuvi E1 scanner...")
        print("DEBUG MODE: All BLE devices will be shown")
        print("Press Ctrl+C to stop\n")
        
        if duration:
            await scanner.start()
            await asyncio.sleep(duration)
            await scanner.stop()
        else:
            # Continuous scanning with periodic statistics
            await scanner.start()
            try:
                counter = 0
                while True:
                    await asyncio.sleep(10)
                    counter += 10
                    
                    # Print statistics every 30 seconds
                    if counter % 30 == 0:
                        print(f"\n{'='*60}")
                        print(f"SCAN STATISTICS (after {counter} seconds)")
                        print(f"{'='*60}")
                        print(f"Total BLE devices detected: {self.device_count}")
                        print(f"Ruuvi devices found: {self.ruuvi_count}")
                        print(f"E1 format devices: {self.e1_count}")
                        print(f"{'='*60}\n")
                        
            except KeyboardInterrupt:
                print("\nStopping scanner...")
                print(f"\nFinal statistics:")
                print(f"  Total BLE devices: {self.device_count}")
                print(f"  Ruuvi devices: {self.ruuvi_count}")
                print(f"  E1 format devices: {self.e1_count}")
                await scanner.stop()


async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Ruuvi E1 BLE Scanner')
    parser.add_argument('--no-debug', action='store_true', help='Disable debug output')
    parser.add_argument('--db', default='ruuvi_data.db', help='Database file path')
    args = parser.parse_args()
    
    # Set debug mode
    global DEBUG
    DEBUG = not args.no_debug
    
    if DEBUG:
        print("\n" + "="*60)
        print("RUUVI E1 SCANNER - DEBUG MODE ENABLED")
        print("="*60)
        print("All BLE devices will be shown with detailed information.")
        print("To disable debug output, run with: --no-debug")
        print("="*60 + "\n")
    
    # Initialize database
    db = RuuviDatabase(args.db)
    
    try:
        # Create scanner
        scanner = RuuviScanner(db)
        
        # Start scanning (continuous until Ctrl+C)
        await scanner.scan()
        
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        db.close()
        print("Database closed. Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())