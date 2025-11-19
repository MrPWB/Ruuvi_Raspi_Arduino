#!/usr/bin/env python3
"""
Extended RuuviTag Database Management
Thread-safe SQLite database with sampling metadata support
"""

import sqlite3
import threading
from contextlib import contextmanager
from typing import List, Dict, Any
import datetime as dt
import os


class RuuviDatabaseExtended:
    """
    Extended thread-safe SQLite database manager for RuuviTag sensor data.
    Supports sampling metadata for averaged readings.
    """
    
    def __init__(self, db_path: str = "ruuvi_data.db"):
        """Initialize database connection with extended schema"""
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
    
    def _get_connection(self):
        """Get thread-local database connection"""
        if not hasattr(self._local, 'connection'):
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            # Enable WAL mode for better concurrent access
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=1000")
            conn.execute("PRAGMA temp_store=memory")
            conn.row_factory = sqlite3.Row
            self._local.connection = conn
        return self._local.connection
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database operations"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
    
    def _init_db(self):
        """Initialize database schema with extended fields"""
        with self.get_cursor() as cursor:
            # Check if we need to migrate existing schema
            cursor.execute("PRAGMA table_info(sensor_data)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if not columns:
                # Create new table with extended schema and UTC timestamps
                cursor.execute("""
                    CREATE TABLE sensor_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        address TEXT NOT NULL,
                        ruuvi_mac TEXT,
                        temperature_c REAL,
                        humidity_percent REAL,
                        pressure_hpa REAL,
                        acc_g_x REAL,
                        acc_g_y REAL,
                        acc_g_z REAL,
                        battery_mv INTEGER,
                        tx_power_dbm INTEGER,
                        movement_counter INTEGER,
                        measurement_sequence INTEGER,
                        rssi_dbm INTEGER,
                        sample_count INTEGER DEFAULT 1,
                        sample_period_seconds REAL DEFAULT 0,
                        created_at TEXT DEFAULT (datetime('now', 'utc'))
                    )
                """)
                print("✅ Created new table with UTC timestamps")
            else:
                # Add new columns if they don't exist
                if 'sample_count' not in columns:
                    cursor.execute("ALTER TABLE sensor_data ADD COLUMN sample_count INTEGER DEFAULT 1")
                    print("✅ Added sample_count column")
                
                if 'sample_period_seconds' not in columns:
                    cursor.execute("ALTER TABLE sensor_data ADD COLUMN sample_period_seconds REAL DEFAULT 0")
                    print("✅ Added sample_period_seconds column")
                
                # Fix created_at column to use UTC if it's using local time
                cursor.execute("PRAGMA table_info(sensor_data)")
                created_at_info = None
                for col in cursor.fetchall():
                    if col[1] == 'created_at':
                        created_at_info = col
                        break
                
                if created_at_info and 'utc' not in str(created_at_info[4]).lower():
                    print("⚠️  Warning: created_at column uses local time instead of UTC")
                    print("   Consider running: UPDATE sensor_data SET created_at = datetime(created_at, 'utc') WHERE created_at NOT LIKE '%Z'")
            
            # Create indices for better query performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON sensor_data(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_address ON sensor_data(address)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON sensor_data(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ruuvi_mac ON sensor_data(ruuvi_mac)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sample_count ON sensor_data(sample_count)")
            
            # Create composite index for common queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_address_created_at 
                ON sensor_data(address, created_at)
            """)
    
    def insert_reading(self, data: Dict[str, Any]):
        """Insert a single sensor reading with optional sampling metadata"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO sensor_data (
                    timestamp, address, ruuvi_mac, temperature_c, humidity_percent,
                    pressure_hpa, acc_g_x, acc_g_y, acc_g_z, battery_mv,
                    tx_power_dbm, movement_counter, measurement_sequence, rssi_dbm,
                    sample_count, sample_period_seconds
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['timestamp'], data['address'], data['ruuvi_mac'],
                data['temperature_c'], data['humidity_percent'], data['pressure_hpa'],
                data['acc_g_x'], data['acc_g_y'], data['acc_g_z'],
                data['battery_mv'], data['tx_power_dbm'],
                data['movement_counter'], data['measurement_sequence'], data['rssi_dbm'],
                data.get('sample_count', 1), data.get('sample_period_seconds', 0)
            ))
    
    def insert_multiple_readings(self, readings: List[Dict[str, Any]]):
        """Insert multiple sensor readings in a single transaction"""
        with self.get_cursor() as cursor:
            cursor.executemany("""
                INSERT INTO sensor_data (
                    timestamp, address, ruuvi_mac, temperature_c, humidity_percent,
                    pressure_hpa, acc_g_x, acc_g_y, acc_g_z, battery_mv,
                    tx_power_dbm, movement_counter, measurement_sequence, rssi_dbm,
                    sample_count, sample_period_seconds
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                (
                    reading['timestamp'], reading['address'], reading['ruuvi_mac'],
                    reading['temperature_c'], reading['humidity_percent'], reading['pressure_hpa'],
                    reading['acc_g_x'], reading['acc_g_y'], reading['acc_g_z'],
                    reading['battery_mv'], reading['tx_power_dbm'],
                    reading['movement_counter'], reading['measurement_sequence'], reading['rssi_dbm'],
                    reading.get('sample_count', 1), reading.get('sample_period_seconds', 0)
                ) for reading in readings
            ])
    
    def get_latest_readings(self, limit: int = 100) -> List[Dict]:
        """Get latest sensor readings from all devices"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM sensor_data 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_readings_by_timerange(self, hours: int = 24) -> List[Dict]:
        """Get readings from last X hours from all devices"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM sensor_data 
                WHERE created_at >= datetime('now', '-{} hours')
                ORDER BY created_at ASC
            """.format(hours))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_devices(self) -> List[Dict]:
        """Get list of all devices with latest data and statistics"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    address,
                    ruuvi_mac,
                    MAX(created_at) as last_seen,
                    COUNT(*) as total_readings,
                    AVG(temperature_c) as avg_temperature,
                    AVG(humidity_percent) as avg_humidity,
                    AVG(pressure_hpa) as avg_pressure,
                    MIN(battery_mv) as min_battery,
                    MAX(battery_mv) as max_battery,
                    AVG(sample_count) as avg_samples_per_reading,
                    SUM(sample_count) as total_samples
                FROM sensor_data 
                GROUP BY address, ruuvi_mac
                ORDER BY last_seen DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_device_data(self, address: str, hours: int = 24) -> List[Dict]:
        """Get data for specific device within timeframe"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM sensor_data 
                WHERE address = ? AND created_at >= datetime('now', '-{} hours')
                ORDER BY created_at ASC
            """.format(hours), (address,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_device_latest(self, address: str) -> Dict:
        """Get latest reading from specific device"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM sensor_data 
                WHERE address = ?
                ORDER BY created_at DESC 
                LIMIT 1
            """, (address,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_sampling_stats(self) -> Dict:
        """Get statistics about sampling (for averaged logger)"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_db_records,
                    SUM(sample_count) as total_raw_samples,
                    AVG(sample_count) as avg_samples_per_record,
                    MIN(sample_count) as min_samples,
                    MAX(sample_count) as max_samples,
                    AVG(sample_period_seconds) as avg_period_seconds
                FROM sensor_data
                WHERE sample_count > 0
            """)
            stats = dict(cursor.fetchone())
            
            # Calculate compression ratio
            if stats['total_raw_samples'] and stats['total_db_records']:
                stats['compression_ratio'] = round(stats['total_raw_samples'] / stats['total_db_records'], 1)
            else:
                stats['compression_ratio'] = 1.0
                
            return stats
    
    def cleanup_old_data(self, days: int = 30):
        """Remove data older than specified days"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                DELETE FROM sensor_data 
                WHERE created_at < datetime('now', '-{} days')
            """.format(days))
            return cursor.rowcount
    
    def get_database_stats(self) -> Dict:
        """Get comprehensive database statistics"""
        with self.get_cursor() as cursor:
            # Total size and record count
            cursor.execute("SELECT COUNT(*) as total_records FROM sensor_data")
            total_records = cursor.fetchone()['total_records']
            
            # Database file size
            file_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            
            # Date range
            cursor.execute("""
                SELECT 
                    MIN(created_at) as first_record,
                    MAX(created_at) as last_record
                FROM sensor_data
            """)
            date_range = cursor.fetchone()
            
            # Device statistics
            cursor.execute("SELECT COUNT(DISTINCT address) as unique_devices FROM sensor_data")
            unique_devices = cursor.fetchone()['unique_devices']
            
            # Sampling statistics (if using averaged logger)
            sampling_stats = self.get_sampling_stats() if total_records > 0 else {}
            
            return {
                'total_records': total_records,
                'file_size_bytes': file_size,
                'file_size_mb': round(file_size / (1024 * 1024), 2),
                'unique_devices': unique_devices,
                'first_record': date_range['first_record'],
                'last_record': date_range['last_record'],
                **sampling_stats
            }
    
    def close(self):
        """Close database connection"""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            delattr(self._local, 'connection')


# Backward compatibility alias
RuuviDatabase = RuuviDatabaseExtended


def main():
    """Test extended database functionality"""
    db = RuuviDatabaseExtended("test_extended.db")
    
    # Test averaged reading
    test_reading = {
        'timestamp': dt.datetime.utcnow().isoformat() + "Z",
        'address': "AA:BB:CC:DD:EE:FF",
        'ruuvi_mac': "FF:EE:DD:CC:BB:AA",
        'temperature_c': 22.5,
        'humidity_percent': 65.0,
        'pressure_hpa': 1013.25,
        'acc_g_x': 0.01,
        'acc_g_y': 0.02,
        'acc_g_z': 1.0,
        'battery_mv': 3000,
        'tx_power_dbm': -12,
        'movement_counter': 42,
        'measurement_sequence': 1234,
        'rssi_dbm': -45,
        'sample_count': 12,  # Averaged from 12 samples
        'sample_period_seconds': 60.0  # Over 60 seconds
    }
    
    # Insert test data
    print("Inserting test averaged reading...")
    db.insert_reading(test_reading)
    
    # Get statistics
    print("\nDatabase statistics:")
    stats = db.get_database_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Get sampling stats
    print("\nSampling statistics:")
    sampling_stats = db.get_sampling_stats()
    for key, value in sampling_stats.items():
        print(f"  {key}: {value}")
    
    print("\nExtended database test completed!")


if __name__ == '__main__':
    main()