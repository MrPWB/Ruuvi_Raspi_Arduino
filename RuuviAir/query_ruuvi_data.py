#!/usr/bin/env python3
"""
Ruuvi Database Query Tool
Query and analyze stored Ruuvi E1 measurements
"""

import sqlite3
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any


class RuuviQuery:
    """Query tool for Ruuvi database"""
    
    def __init__(self, db_path: str = 'ruuvi_data.db'):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
    
    def get_latest(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get latest measurements
        
        Args:
            limit: Number of records to return
            
        Returns:
            List of measurement dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM ruuvi_measurements 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_by_mac(self, mac: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get measurements for specific MAC address
        
        Args:
            mac: MAC address
            limit: Number of records to return
            
        Returns:
            List of measurement dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM ruuvi_measurements 
            WHERE mac = ?
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (mac, limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_statistics(self, hours: int = 24, mac: str = None) -> Dict[str, Any]:
        """
        Get statistical summary
        
        Args:
            hours: Number of hours to look back
            mac: Optional MAC address filter
            
        Returns:
            Dictionary with statistics
        """
        cursor = self.conn.cursor()
        
        cutoff = datetime.now() - timedelta(hours=hours)
        cutoff_str = cutoff.isoformat()
        
        if mac:
            query = '''
                SELECT 
                    COUNT(*) as count,
                    AVG(temperature) as avg_temp,
                    MIN(temperature) as min_temp,
                    MAX(temperature) as max_temp,
                    AVG(humidity) as avg_humidity,
                    MIN(humidity) as min_humidity,
                    MAX(humidity) as max_humidity,
                    AVG(pressure) as avg_pressure,
                    AVG(pm1_0) as avg_pm1,
                    AVG(pm2_5) as avg_pm25,
                    AVG(pm4_0) as avg_pm4,
                    AVG(pm10_0) as avg_pm10,
                    AVG(co2) as avg_co2,
                    MIN(co2) as min_co2,
                    MAX(co2) as max_co2,
                    AVG(voc) as avg_voc,
                    AVG(nox) as avg_nox,
                    AVG(luminosity) as avg_luminosity,
                    MIN(luminosity) as min_luminosity,
                    MAX(luminosity) as max_luminosity,
                    AVG(rssi) as avg_rssi
                FROM ruuvi_measurements 
                WHERE timestamp > ? AND mac = ?
            '''
            cursor.execute(query, (cutoff_str, mac))
        else:
            query = '''
                SELECT 
                    COUNT(*) as count,
                    AVG(temperature) as avg_temp,
                    MIN(temperature) as min_temp,
                    MAX(temperature) as max_temp,
                    AVG(humidity) as avg_humidity,
                    MIN(humidity) as min_humidity,
                    MAX(humidity) as max_humidity,
                    AVG(pressure) as avg_pressure,
                    AVG(pm1_0) as avg_pm1,
                    AVG(pm2_5) as avg_pm25,
                    AVG(pm4_0) as avg_pm4,
                    AVG(pm10_0) as avg_pm10,
                    AVG(co2) as avg_co2,
                    MIN(co2) as min_co2,
                    MAX(co2) as max_co2,
                    AVG(voc) as avg_voc,
                    AVG(nox) as avg_nox,
                    AVG(luminosity) as avg_luminosity,
                    MIN(luminosity) as min_luminosity,
                    MAX(luminosity) as max_luminosity,
                    AVG(rssi) as avg_rssi
                FROM ruuvi_measurements 
                WHERE timestamp > ?
            '''
            cursor.execute(query, (cutoff_str,))
        
        return dict(cursor.fetchone())
    
    def get_devices(self) -> List[str]:
        """
        Get list of all MAC addresses in database
        
        Returns:
            List of MAC addresses
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT DISTINCT mac FROM ruuvi_measurements 
            WHERE mac IS NOT NULL
            ORDER BY mac
        ''')
        
        return [row['mac'] for row in cursor.fetchall()]
    
    def export_csv(self, filename: str, hours: int = None, mac: str = None):
        """
        Export data to CSV file
        
        Args:
            filename: Output CSV filename
            hours: Optional hours to look back
            mac: Optional MAC address filter
        """
        cursor = self.conn.cursor()
        
        query = 'SELECT * FROM ruuvi_measurements WHERE 1=1'
        params = []
        
        if hours:
            cutoff = datetime.now() - timedelta(hours=hours)
            query += ' AND timestamp > ?'
            params.append(cutoff.isoformat())
        
        if mac:
            query += ' AND mac = ?'
            params.append(mac)
        
        query += ' ORDER BY timestamp DESC'
        
        cursor.execute(query, params)
        
        # Write CSV
        with open(filename, 'w') as f:
            # Header
            columns = [description[0] for description in cursor.description]
            f.write(','.join(columns) + '\n')
            
            # Data
            for row in cursor.fetchall():
                values = [str(v) if v is not None else '' for v in row]
                f.write(','.join(values) + '\n')
        
        print(f"Exported to {filename}")
    
    def close(self):
        """Close database connection"""
        self.conn.close()


def print_measurements(measurements: List[Dict[str, Any]]):
    """Pretty print measurements"""
    if not measurements:
        print("No measurements found.")
        return
    
    for m in measurements:
        print(f"\n{'='*60}")
        print(f"Timestamp: {m['timestamp']}")
        print(f"MAC: {m['mac']}")
        print(f"RSSI: {m['rssi']} dBm")
        
        if m['temperature'] is not None:
            print(f"Temperature: {m['temperature']:.2f}°C")
        if m['humidity'] is not None:
            print(f"Humidity: {m['humidity']:.2f}%")
        if m['pressure'] is not None:
            print(f"Pressure: {m['pressure']} Pa ({m['pressure']/100:.1f} hPa)")
        
        if any(m.get(f'pm{x}') is not None for x in ['1_0', '2_5', '4_0', '10_0']):
            print("\nParticulate Matter:")
            if m['pm1_0'] is not None:
                print(f"  PM1.0: {m['pm1_0']:.1f} µg/m³")
            if m['pm2_5'] is not None:
                print(f"  PM2.5: {m['pm2_5']:.1f} µg/m³")
            if m['pm4_0'] is not None:
                print(f"  PM4.0: {m['pm4_0']:.1f} µg/m³")
            if m['pm10_0'] is not None:
                print(f"  PM10: {m['pm10_0']:.1f} µg/m³")
        
        if m['co2'] is not None:
            print(f"\nCO2: {m['co2']} ppm")
        
        if m['voc'] is not None:
            print(f"VOC Index: {m['voc']}")
        if m['nox'] is not None:
            print(f"NOX Index: {m['nox']}")
        
        if m['luminosity'] is not None:
            print(f"Luminosity: {m['luminosity']:.2f} lux")
        
        if m['calibration_in_progress']:
            print("\n⚠️  Calibration in progress")


def print_statistics(stats: Dict[str, Any], hours: int):
    """Pretty print statistics"""
    print(f"\n{'='*60}")
    print(f"Statistics for last {hours} hours")
    print(f"{'='*60}")
    print(f"\nTotal measurements: {stats['count']}")
    
    if stats['avg_temp'] is not None:
        print(f"\nTemperature:")
        print(f"  Average: {stats['avg_temp']:.2f}°C")
        print(f"  Min: {stats['min_temp']:.2f}°C")
        print(f"  Max: {stats['max_temp']:.2f}°C")
    
    if stats['avg_humidity'] is not None:
        print(f"\nHumidity:")
        print(f"  Average: {stats['avg_humidity']:.2f}%")
        print(f"  Min: {stats['min_humidity']:.2f}%")
        print(f"  Max: {stats['max_humidity']:.2f}%")
    
    if stats['avg_pressure'] is not None:
        print(f"\nPressure:")
        print(f"  Average: {stats['avg_pressure']:.0f} Pa ({stats['avg_pressure']/100:.1f} hPa)")
    
    if stats['avg_pm25'] is not None:
        print(f"\nParticulate Matter (Average):")
        if stats['avg_pm1'] is not None:
            print(f"  PM1.0: {stats['avg_pm1']:.1f} µg/m³")
        if stats['avg_pm25'] is not None:
            print(f"  PM2.5: {stats['avg_pm25']:.1f} µg/m³")
        if stats['avg_pm4'] is not None:
            print(f"  PM4.0: {stats['avg_pm4']:.1f} µg/m³")
        if stats['avg_pm10'] is not None:
            print(f"  PM10: {stats['avg_pm10']:.1f} µg/m³")
    
    if stats['avg_co2'] is not None:
        print(f"\nCO2:")
        print(f"  Average: {stats['avg_co2']:.0f} ppm")
        print(f"  Min: {stats['min_co2']:.0f} ppm")
        print(f"  Max: {stats['max_co2']:.0f} ppm")
    
    if stats['avg_voc'] is not None:
        print(f"\nAir Quality Indexes:")
        print(f"  VOC: {stats['avg_voc']:.0f}")
        if stats['avg_nox'] is not None:
            print(f"  NOX: {stats['avg_nox']:.0f}")
    
    if stats['avg_luminosity'] is not None:
        print(f"\nLuminosity:")
        print(f"  Average: {stats['avg_luminosity']:.2f} lux")
        print(f"  Min: {stats['min_luminosity']:.2f} lux")
        print(f"  Max: {stats['max_luminosity']:.2f} lux")
    
    if stats['avg_rssi'] is not None:
        print(f"\nSignal Strength:")
        print(f"  Average RSSI: {stats['avg_rssi']:.1f} dBm")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Query Ruuvi E1 database')
    
    parser.add_argument('--db', default='ruuvi_data.db', help='Database file path')
    parser.add_argument('--latest', type=int, metavar='N', help='Show latest N measurements')
    parser.add_argument('--stats', type=int, metavar='HOURS', help='Show statistics for last N hours')
    parser.add_argument('--devices', action='store_true', help='List all devices')
    parser.add_argument('--mac', help='Filter by MAC address')
    parser.add_argument('--export', metavar='FILE', help='Export to CSV file')
    parser.add_argument('--hours', type=int, help='Hours to look back for export')
    
    args = parser.parse_args()
    
    # Create query object
    query = RuuviQuery(args.db)
    
    try:
        if args.devices:
            # List devices
            devices = query.get_devices()
            print(f"\nFound {len(devices)} device(s):")
            for mac in devices:
                print(f"  {mac}")
        
        elif args.latest:
            # Show latest measurements
            if args.mac:
                measurements = query.get_by_mac(args.mac, args.latest)
            else:
                measurements = query.get_latest(args.latest)
            print_measurements(measurements)
        
        elif args.stats:
            # Show statistics
            stats = query.get_statistics(args.stats, args.mac)
            print_statistics(stats, args.stats)
        
        elif args.export:
            # Export to CSV
            query.export_csv(args.export, args.hours, args.mac)
        
        else:
            # Default: show latest 5 measurements
            measurements = query.get_latest(5)
            print_measurements(measurements)
    
    finally:
        query.close()


if __name__ == "__main__":
    main()
