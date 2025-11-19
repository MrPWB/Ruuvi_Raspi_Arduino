#!/usr/bin/env python3
"""
Ruuvi BLE E1 Data Format Scanner for Raspberry Pi
Scans for Ruuvi devices broadcasting E1 format, decodes the data and stores it in SQLite database.
"""

import asyncio
import struct
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any
from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

# Ruuvi Manufacturer ID
RUUVI_MANUFACTURER_ID = 0x0499

# E1 Format identifier
E1_FORMAT = 0xE1


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
    
    def detection_callback(self, device: BLEDevice, advertisement_data: AdvertisementData):
        """
        Callback for BLE device detection
        
        Args:
            device: Detected BLE device
            advertisement_data: Advertisement data
        """
        # Check if this is a Ruuvi device
        if RUUVI_MANUFACTURER_ID not in advertisement_data.manufacturer_data:
            return
        
        # Get manufacturer data
        mfg_data = advertisement_data.manufacturer_data[RUUVI_MANUFACTURER_ID]
        
        # Decode E1 format
        decoded = self.decoder.decode(mfg_data)
        
        if decoded is None:
            return
        
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
        scanner = BleakScanner(detection_callback=self.detection_callback)
        
        print("Starting Ruuvi E1 scanner...")
        print("Press Ctrl+C to stop\n")
        
        if duration:
            await scanner.start()
            await asyncio.sleep(duration)
            await scanner.stop()
        else:
            # Continuous scanning
            await scanner.start()
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping scanner...")
                await scanner.stop()


async def main():
    """Main function"""
    # Initialize database
    db = RuuviDatabase('ruuvi_data.db')
    
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
