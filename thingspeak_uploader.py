#!/usr/bin/env python3
"""
RuuviTag ThingSpeak Uploader
Liest Daten aus der Datenbank und sendet sie an ThingSpeak
"""

import argparse
import time
import sys
import signal
from datetime import datetime
import requests
from database import RuuviDatabase

# ThingSpeak Configuration
THINGSPEAK_API_KEY = "B4KJSTHHHDT19JV3"
THINGSPEAK_BASE_URL = "https://api.thingspeak.com/update"
TARGET_MAC = "E3:28:3B:5A:5F:2C"

# ThingSpeak Rate Limits
# Free Account: Minimum 15 seconds between updates
MIN_UPDATE_INTERVAL = 15  # seconds


class ThingSpeakUploader:
    """Manages uploading RuuviTag data to ThingSpeak"""
    
    def __init__(self, db_path: str, api_key: str, target_mac: str, interval: int = 60):
        self.db = RuuviDatabase(db_path)
        self.api_key = api_key
        self.target_mac = target_mac.upper()
        self.interval = max(interval, MIN_UPDATE_INTERVAL)  # Enforce minimum interval
        self.running = True
        self.last_sequence = None
        self.upload_count = 0
        self.error_count = 0
        
        if self.interval < MIN_UPDATE_INTERVAL:
            print(f"⚠️  Warning: Interval adjusted to {MIN_UPDATE_INTERVAL}s (ThingSpeak free limit)")
    
    def get_latest_data(self):
        """Get latest data for target device from database"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        temperature_c,
                        humidity_percent,
                        pressure_hpa,
                        measurement_sequence,
                        created_at,
                        battery_mv,
                        rssi_dbm
                    FROM sensor_data 
                    WHERE address = ? OR ruuvi_mac = ?
                    ORDER BY created_at DESC 
                    LIMIT 1
                """, (self.target_mac, self.target_mac))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            print(f"❌ Database error: {e}")
            return None
    
    def upload_to_thingspeak(self, data):
        """Upload data to ThingSpeak"""
        if not data:
            return False
        
        # Check if this is new data (based on measurement_sequence)
        if self.last_sequence is not None:
            if data.get('measurement_sequence') == self.last_sequence:
                print(f"⏭️  Skipping duplicate data (sequence: {self.last_sequence})")
                return True
        
        try:
            # Prepare ThingSpeak payload
            # Field 1: Temperature
            # Field 2: Humidity
            # Field 3: Pressure
            payload = {
                'api_key': self.api_key,
                'field1': data.get('temperature_c'),
                'field2': data.get('humidity_percent'),
                'field3': data.get('pressure_hpa')
            }
            
            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}
            
            if len(payload) <= 1:  # Only api_key, no data
                print(f"⚠️  No valid data to upload")
                return False
            
            # Make request
            response = requests.get(THINGSPEAK_BASE_URL, params=payload, timeout=10)
            
            if response.status_code == 200:
                entry_id = response.text.strip()
                if entry_id != '0':
                    self.upload_count += 1
                    self.last_sequence = data.get('measurement_sequence')
                    
                    print(f"✅ Upload #{self.upload_count} successful (Entry ID: {entry_id})")
                    print(f"   🌡️  Temp: {data.get('temperature_c')}°C")
                    print(f"   💧 Humidity: {data.get('humidity_percent')}%")
                    print(f"   🔘 Pressure: {data.get('pressure_hpa')} hPa")
                    print(f"   🔋 Battery: {data.get('battery_mv')} mV")
                    print(f"   📡 RSSI: {data.get('rssi_dbm')} dBm")
                    return True
                else:
                    self.error_count += 1
                    print(f"❌ ThingSpeak returned 0 (rate limit or error)")
                    return False
            else:
                self.error_count += 1
                print(f"❌ HTTP Error {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            self.error_count += 1
            print(f"❌ Request timeout")
            return False
        except requests.exceptions.ConnectionError:
            self.error_count += 1
            print(f"❌ Connection error - check internet connection")
            return False
        except Exception as e:
            self.error_count += 1
            print(f"❌ Upload error: {e}")
            return False
    
    def verify_device_exists(self):
        """Check if target device exists in database"""
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) as count, 
                       MAX(created_at) as last_seen,
                       ruuvi_mac
                FROM sensor_data 
                WHERE address = ? OR ruuvi_mac = ?
            """, (self.target_mac, self.target_mac))
            
            result = cursor.fetchone()
            if result and result['count'] > 0:
                print(f"✅ Target device found in database")
                print(f"   MAC: {self.target_mac}")
                print(f"   RuuviTag MAC: {result['ruuvi_mac']}")
                print(f"   Total records: {result['count']}")
                print(f"   Last seen: {result['last_seen']}")
                return True
            else:
                print(f"❌ Target device {self.target_mac} not found in database")
                print(f"   Make sure the logger is running and collecting data from this device")
                return False
    
    def run(self):
        """Main upload loop"""
        print(f"🚀 ThingSpeak Uploader started")
        print(f"📡 Target device: {self.target_mac}")
        print(f"⏱️  Update interval: {self.interval}s")
        print(f"🔑 API Key: {self.api_key[:4]}...{self.api_key[-4:]}")
        print()
        
        # Verify device exists
        if not self.verify_device_exists():
            return
        
        print(f"\n🔄 Starting upload loop (Ctrl+C to stop)...\n")
        
        try:
            while self.running:
                start_time = time.time()
                
                # Get latest data
                data = self.get_latest_data()
                
                if data:
                    # Upload to ThingSpeak
                    self.upload_to_thingspeak(data)
                else:
                    print(f"⚠️  No data available for device {self.target_mac}")
                
                # Calculate sleep time
                elapsed = time.time() - start_time
                sleep_time = max(0, self.interval - elapsed)
                
                if self.running and sleep_time > 0:
                    print(f"⏳ Next update in {int(sleep_time)}s... (Total: {self.upload_count} uploads, {self.error_count} errors)")
                    time.sleep(sleep_time)
                    
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the uploader"""
        self.running = False
        print(f"\n📊 Final Statistics:")
        print(f"   Total uploads: {self.upload_count}")
        print(f"   Total errors: {self.error_count}")
        if self.upload_count > 0:
            success_rate = (self.upload_count / (self.upload_count + self.error_count)) * 100
            print(f"   Success rate: {success_rate:.1f}%")


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print("\n🛑 Received interrupt signal...")
    sys.exit(0)


def test_thingspeak_connection(api_key):
    """Test ThingSpeak API connection"""
    print("🧪 Testing ThingSpeak connection...")
    
    try:
        payload = {
            'api_key': api_key,
            'field1': 20.0,  # Test temperature
            'field2': 50.0,  # Test humidity
            'field3': 1013.0  # Test pressure
        }
        
        response = requests.get(THINGSPEAK_BASE_URL, params=payload, timeout=10)
        
        if response.status_code == 200 and response.text.strip() != '0':
            print(f"✅ ThingSpeak connection successful (Entry ID: {response.text.strip()})")
            return True
        else:
            print(f"❌ ThingSpeak connection failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Upload RuuviTag data to ThingSpeak",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default: Upload every 60 seconds
  python3 thingspeak_uploader.py
  
  # Custom interval (minimum 15s for free ThingSpeak)
  python3 thingspeak_uploader.py --interval 30
  
  # Use different database
  python3 thingspeak_uploader.py --db /path/to/ruuvi_data.db
  
  # Test connection only
  python3 thingspeak_uploader.py --test

ThingSpeak Channel: https://thingspeak.com/channels/YOUR_CHANNEL_ID
        """
    )
    
    parser.add_argument(
        "--db",
        default="ruuvi_data.db",
        help="Path to SQLite database (default: ruuvi_data.db)"
    )
    
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help=f"Upload interval in seconds (minimum {MIN_UPDATE_INTERVAL}, default: 60)"
    )
    
    parser.add_argument(
        "--api-key",
        default=THINGSPEAK_API_KEY,
        help="ThingSpeak API Write Key"
    )
    
    parser.add_argument(
        "--mac",
        default=TARGET_MAC,
        help="Target device MAC address"
    )
    
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test ThingSpeak connection and exit"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Test mode
    if args.test:
        success = test_thingspeak_connection(args.api_key)
        sys.exit(0 if success else 1)
    
    # Validate arguments
    if args.interval < MIN_UPDATE_INTERVAL:
        print(f"⚠️  Warning: Interval {args.interval}s is below ThingSpeak free limit ({MIN_UPDATE_INTERVAL}s)")
        print(f"   Adjusting to {MIN_UPDATE_INTERVAL}s")
        args.interval = MIN_UPDATE_INTERVAL
    
    # Create and run uploader
    try:
        uploader = ThingSpeakUploader(
            db_path=args.db,
            api_key=args.api_key,
            target_mac=args.mac,
            interval=args.interval
        )
        
        uploader.run()
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()