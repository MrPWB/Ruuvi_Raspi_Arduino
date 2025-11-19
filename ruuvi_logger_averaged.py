#!/usr/bin/env python3
"""
RuuviTag BLE Logger with Averaging
Collects multiple samples and logs averaged values at configurable intervals
"""

import argparse
import asyncio
import datetime as dt
import os
import signal
import struct
import sys
import time
from typing import Optional, Dict, Any, List
from collections import defaultdict, deque
import statistics

from bleak import BleakScanner
from bleak.backends.scanner import AdvertisementData
from database import RuuviDatabase

RUUVI_COMPANY_ID = 0x0499  # Ruuvi Innovations Ltd.


class DeviceBuffer:
    """Buffer for collecting and averaging sensor readings per device"""
    
    def __init__(self, max_samples: int = 20):
        self.max_samples = max_samples
        self.readings = deque(maxlen=max_samples)
        self.last_logged = 0
        
    def add_reading(self, reading: Dict[str, Any]):
        """Add a reading to the buffer"""
        reading['timestamp_raw'] = time.time()
        self.readings.append(reading)
        
    def get_averaged_reading(self) -> Optional[Dict[str, Any]]:
        """Calculate averaged reading from all samples in buffer"""
        if not self.readings:
            return None
            
        # Get the most recent reading as template
        latest = self.readings[-1]
        
        # Fields to average (numeric values only)
        avg_fields = [
            'temperature_c', 'humidity_percent', 'pressure_hpa',
            'acc_g_x', 'acc_g_y', 'acc_g_z', 'battery_mv', 
            'tx_power_dbm', 'rssi_dbm'
        ]
        
        # Calculate averages
        averaged = {}
        for field in avg_fields:
            values = [r[field] for r in self.readings if r.get(field) is not None]
            if values:
                averaged[field] = round(statistics.mean(values), 2)
            else:
                averaged[field] = None
        
        # Use latest values for non-averaged fields
        result = {
            "timestamp": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "address": latest["address"],
            "ruuvi_mac": latest["ruuvi_mac"],
            "movement_counter": latest["movement_counter"],
            "measurement_sequence": latest["measurement_sequence"],
            **averaged
        }
        
        # Add sampling metadata
        result['sample_count'] = len(self.readings)
        result['sample_period_seconds'] = round(self.readings[-1]['timestamp_raw'] - self.readings[0]['timestamp_raw'], 1)
        
        return result
        
    def clear(self):
        """Clear the buffer"""
        self.readings.clear()
        self.last_logged = time.time()


def parse_ruuvi_df5(data: bytes) -> Optional[Dict[str, Any]]:
    """Parse RuuviTag Data Format 5 (RAWv2)"""
    if not data or len(data) < 24 or data[0] != 0x05:
        return None

    try:
        temp_raw, hum_raw, pres_raw, acc_x_raw, acc_y_raw, acc_z_raw, pwr_raw, movement, seq = struct.unpack_from(
            ">hHHhhhHBH", data, 1
        )
        mac_bytes = data[18:24]
    except struct.error:
        return None

    # Handle "not available" sentinels (per spec)
    temp_c = None if temp_raw == -32768 else temp_raw / 200.0
    humidity = None if hum_raw == 0xFFFF else hum_raw / 400.0
    pressure_hpa = None if pres_raw == 0xFFFF else (pres_raw + 50000) / 100.0

    acc_x = None if acc_x_raw == -32768 else acc_x_raw / 1000.0
    acc_y = None if acc_y_raw == -32768 else acc_y_raw / 1000.0
    acc_z = None if acc_z_raw == -32768 else acc_z_raw / 1000.0

    battery_mv = (pwr_raw >> 5) + 1600
    tx_power_dbm = -40 + 2 * (pwr_raw & 0x1F)

    ruuvi_mac = ":".join(f"{b:02X}" for b in mac_bytes)

    return {
        "temperature_c": temp_c,
        "humidity_percent": humidity,
        "pressure_hpa": pressure_hpa,
        "acc_g_x": acc_x,
        "acc_g_y": acc_y,
        "acc_g_z": acc_z,
        "battery_mv": battery_mv,
        "tx_power_dbm": tx_power_dbm,
        "movement_counter": movement,
        "measurement_sequence": seq,
        "ruuvi_mac": ruuvi_mac,
    }


async def averaging_writer_task(
    db: RuuviDatabase, 
    device_buffers: Dict[str, DeviceBuffer], 
    stop_event: asyncio.Event,
    log_interval: float,
    verbose: bool
):
    """Write averaged sensor data to database at regular intervals"""
    
    while not stop_event.is_set():
        try:
            await asyncio.sleep(1)  # Check every second
            current_time = time.time()
            
            for device_mac, buffer in device_buffers.items():
                # Check if it's time to log this device
                if (current_time - buffer.last_logged) >= log_interval:
                    averaged_reading = buffer.get_averaged_reading()
                    
                    if averaged_reading:
                        try:
                            db.insert_reading(averaged_reading)
                            
                            if verbose:
                                print(f"Logged averaged: {device_mac} - "
                                      f"T={averaged_reading['temperature_c']}°C "
                                      f"H={averaged_reading['humidity_percent']}% "
                                      f"P={averaged_reading['pressure_hpa']}hPa "
                                      f"(from {averaged_reading['sample_count']} samples)")
                            else:
                                print(f"Logged: {device_mac} - "
                                      f"{averaged_reading['temperature_c']}°C, "
                                      f"{averaged_reading['humidity_percent']}%, "
                                      f"{averaged_reading['pressure_hpa']}hPa "
                                      f"({averaged_reading['sample_count']} samples)")
                            
                            buffer.clear()
                            
                        except Exception as e:
                            print(f"Database error for {device_mac}: {e}")
                            buffer.clear()  # Clear to prevent infinite retry
                    
        except Exception as e:
            print(f"Writer task error: {e}")
            await asyncio.sleep(5)


async def run_averaged_logger(
    db_path: str, 
    adapter: Optional[str], 
    scan_interval: float,
    log_interval: float,
    max_samples: int,
    verbose: bool = False
):
    """Run the averaged BLE logger"""
    
    # Initialize database
    db = RuuviDatabase(db_path)
    
    # Print configuration
    print(f"📊 RuuviTag Averaged Logger")
    print(f"Database: {db_path}")
    print(f"Scan interval: {scan_interval}s (how often we collect samples)")
    print(f"Log interval: {log_interval}s (how often we write to DB)")
    print(f"Max samples per device: {max_samples}")
    print(f"Expected samples per log: {int(log_interval / scan_interval)}")
    print()
    
    # Print initial database stats
    stats = db.get_database_stats()
    print(f"Existing records: {stats['total_records']}")
    print(f"Database size: {stats['file_size_mb']} MB")
    print(f"Unique devices: {stats['unique_devices']}")
    if stats['last_record']:
        print(f"Last record: {stats['last_record']}")
    print()
    
    stop_event = asyncio.Event()
    device_buffers: Dict[str, DeviceBuffer] = {}
    last_scan_per_device: Dict[str, float] = {}
    device_counters: Dict[str, int] = {}

    # Handle clean shutdown
    def _signal_handler():
        print("\nShutdown signal received...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            pass

    def detection_callback(device, adv: AdvertisementData):
        """Handle BLE advertisement detection"""
        # Check for Ruuvi manufacturer data
        mfg = adv.manufacturer_data.get(RUUVI_COMPANY_ID)
        if not mfg:
            return
            
        # Parse Ruuvi data
        parsed = parse_ruuvi_df5(mfg)
        if not parsed:
            return

        mac = device.address
        current_time = time.time()
        
        # Rate limiting per device for scanning
        if mac in last_scan_per_device:
            if (current_time - last_scan_per_device[mac]) < scan_interval:
                return
        last_scan_per_device[mac] = current_time

        # Initialize buffer for new device
        if mac not in device_buffers:
            device_buffers[mac] = DeviceBuffer(max_samples)
            print(f"🆕 New device detected: {mac} ({parsed['ruuvi_mac']})")

        # Add reading to device buffer
        reading = {
            "address": mac,
            "ruuvi_mac": parsed["ruuvi_mac"],
            "temperature_c": parsed["temperature_c"],
            "humidity_percent": parsed["humidity_percent"],
            "pressure_hpa": parsed["pressure_hpa"],
            "acc_g_x": parsed["acc_g_x"],
            "acc_g_y": parsed["acc_g_y"],
            "acc_g_z": parsed["acc_g_z"],
            "battery_mv": parsed["battery_mv"],
            "tx_power_dbm": parsed["tx_power_dbm"],
            "movement_counter": parsed["movement_counter"],
            "measurement_sequence": parsed["measurement_sequence"],
            "rssi_dbm": adv.rssi,
        }
        
        device_buffers[mac].add_reading(reading)
        device_counters[mac] = device_counters.get(mac, 0) + 1
        
        if verbose:
            buffer_size = len(device_buffers[mac].readings)
            print(f"Sample: {mac} - T={parsed['temperature_c']}°C "
                  f"RSSI={adv.rssi}dBm (buffer: {buffer_size}/{max_samples})")

    # Initialize scanner
    scanner = BleakScanner(detection_callback, adapter=adapter)
    
    # Start averaging writer task
    writer = asyncio.create_task(averaging_writer_task(
        db, device_buffers, stop_event, log_interval, verbose
    ))
    
    # Status reporting task
    async def status_reporter():
        """Report status periodically"""
        while not stop_event.is_set():
            await asyncio.sleep(300)  # Report every 5 minutes
            if device_buffers:
                total_samples = sum(device_counters.values())
                print(f"📊 Status: {len(device_buffers)} devices, "
                      f"{total_samples} total samples collected")
                
                if verbose:
                    for mac, buffer in device_buffers.items():
                        samples_in_buffer = len(buffer.readings)
                        total_samples_device = device_counters.get(mac, 0)
                        print(f"  {mac}: {total_samples_device} samples total, "
                              f"{samples_in_buffer} in buffer")
    
    status_task = asyncio.create_task(status_reporter())
    
    try:
        await scanner.start()
        print(f"🔍 Scanning for RuuviTags on {adapter or 'default adapter'}")
        print(f"⏱️  Collecting samples every {scan_interval}s")
        print(f"💾 Logging averaged values every {log_interval}s")
        print("📊 Press Ctrl+C to stop and view summary")
        print()
        
        # Main scanning loop
        while not stop_event.is_set():
            await asyncio.sleep(0.5)
            
    except Exception as e:
        print(f"Scanner error: {e}")
        
    finally:
        print("\n🛑 Stopping scanner...")
        await scanner.stop()
        
        print("💾 Writing final averages...")
        # Force write any remaining data
        for device_mac, buffer in device_buffers.items():
            averaged_reading = buffer.get_averaged_reading()
            if averaged_reading:
                try:
                    db.insert_reading(averaged_reading)
                    print(f"Final log: {device_mac} ({averaged_reading['sample_count']} samples)")
                except Exception as e:
                    print(f"Error writing final data for {device_mac}: {e}")
        
        stop_event.set()
        await writer
        
        status_task.cancel()
        try:
            await status_task
        except asyncio.CancelledError:
            pass
        
        # Final statistics
        print("\n📈 Session Summary:")
        if device_counters:
            total_samples = sum(device_counters.values())
            print(f"  Devices discovered: {len(device_counters)}")
            print(f"  Total samples collected: {total_samples}")
            print(f"  Average samples per device:")
            for mac, count in sorted(device_counters.items(), key=lambda x: x[1], reverse=True):
                ruuvi_mac = device_buffers[mac].readings[-1]['ruuvi_mac'] if device_buffers[mac].readings else mac
                print(f"    {ruuvi_mac}: {count} samples")
        else:
            print("  No RuuviTag devices found")
        
        # Final database stats
        final_stats = db.get_database_stats()
        print(f"  Database records: {final_stats['total_records']}")
        print(f"  Database size: {final_stats['file_size_mb']} MB")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="RuuviTag BLE logger with sample averaging",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default: scan every 5s, log every 60s
  python3 ruuvi_logger_averaged.py
  
  # Scan every 10s, log every 2 minutes
  python3 ruuvi_logger_averaged.py --scan-interval 10 --log-interval 120
  
  # High precision: scan every 2s, log every 30s
  python3 ruuvi_logger_averaged.py --scan-interval 2 --log-interval 30 --max-samples 20
  
  # Low frequency: scan every 30s, log every 10 minutes  
  python3 ruuvi_logger_averaged.py --scan-interval 30 --log-interval 600
        """
    )
    
    parser.add_argument(
        "--db", 
        default="ruuvi_data.db", 
        help="Path to SQLite database file (default: ruuvi_data.db)"
    )
    parser.add_argument(
        "--adapter", 
        default=None, 
        help="Bluetooth adapter (e.g., hci0)"
    )
    parser.add_argument(
        "--scan-interval", 
        type=float, 
        default=5.0, 
        help="Seconds between sample collections per device (default: 5.0)"
    )
    parser.add_argument(
        "--log-interval", 
        type=float, 
        default=60.0, 
        help="Seconds between database writes (default: 60.0)"
    )
    parser.add_argument(
        "--max-samples", 
        type=int, 
        default=20, 
        help="Maximum samples to keep in buffer per device (default: 20)"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.scan_interval <= 0 or args.log_interval <= 0:
        print("Error: intervals must be > 0")
        sys.exit(1)
        
    if args.log_interval < args.scan_interval:
        print("Warning: log-interval should be >= scan-interval for meaningful averaging")
    
    if args.max_samples < 1:
        print("Error: max-samples must be >= 1")
        sys.exit(1)
    
    # Create database directory if needed
    db_dir = os.path.dirname(os.path.abspath(args.db))
    if not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir)
            print(f"Created directory: {db_dir}")
        except Exception as e:
            print(f"Error creating directory {db_dir}: {e}")
            sys.exit(1)

    try:
        asyncio.run(run_averaged_logger(
            args.db, 
            args.adapter, 
            args.scan_interval,
            args.log_interval,
            args.max_samples,
            args.verbose
        ))
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()