#!/usr/bin/env python3
"""
RuuviTag BLE Logger with Database
Scans for RuuviTag sensors and logs data to SQLite database
"""

import argparse
import asyncio
import datetime as dt
import os
import signal
import struct
import sys
import time
from typing import Optional, Dict, Any

from bleak import BleakScanner
from bleak.backends.scanner import AdvertisementData
from database import RuuviDatabase

RUUVI_COMPANY_ID = 0x0499  # Ruuvi Innovations Ltd.


def parse_ruuvi_df5(data: bytes) -> Optional[Dict[str, Any]]:
    """
    Parse RuuviTag Data Format 5 (RAWv2).
    
    Args:
        data: Raw manufacturer data bytes
        
    Returns:
        Dictionary with parsed sensor data or None if invalid
    """
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


async def database_writer_task(db: RuuviDatabase, queue: "asyncio.Queue[Dict[str, Any]]", stop_event: asyncio.Event):
    """
    Write sensor data to database.
    
    Args:
        db: Database instance
        queue: Queue containing sensor readings
        stop_event: Event to signal shutdown
    """
    batch_size = 10
    batch_timeout = 5.0  # seconds
    batch = []
    last_batch_time = time.time()
    
    while not stop_event.is_set() or not queue.empty():
        try:
            # Try to get item with timeout
            try:
                item = await asyncio.wait_for(queue.get(), timeout=0.5)
                batch.append(item)
                queue.task_done()
            except asyncio.TimeoutError:
                item = None
            
            # Check if we should write batch
            should_write = (
                len(batch) >= batch_size or 
                (batch and time.time() - last_batch_time >= batch_timeout) or
                (stop_event.is_set() and batch)
            )
            
            if should_write:
                try:
                    if len(batch) == 1:
                        db.insert_reading(batch[0])
                        print(f"Logged: {batch[0]['address']} - {batch[0]['temperature_c']}°C, {batch[0]['humidity_percent']}%, {batch[0]['pressure_hpa']}hPa")
                    else:
                        db.insert_multiple_readings(batch)
                        print(f"Logged batch of {len(batch)} readings")
                    
                    batch.clear()
                    last_batch_time = time.time()
                    
                except Exception as e:
                    print(f"Database error: {e}")
                    batch.clear()  # Clear batch to prevent infinite retry
                    
        except Exception as e:
            print(f"Writer task error: {e}")
            await asyncio.sleep(1)


async def run_logger(db_path: str, adapter: Optional[str], min_interval: float, verbose: bool = False):
    """
    Run the BLE logger.
    
    Args:
        db_path: Path to SQLite database
        adapter: Bluetooth adapter to use
        min_interval: Minimum interval between logs per device
        verbose: Enable verbose logging
    """
    # Initialize database
    db = RuuviDatabase(db_path)
    
    # Print initial database stats
    stats = db.get_database_stats()
    print(f"Database: {db_path}")
    print(f"Existing records: {stats['total_records']}")
    print(f"Database size: {stats['file_size_mb']} MB")
    print(f"Unique devices: {stats['unique_devices']}")
    if stats['last_record']:
        print(f"Last record: {stats['last_record']}")
    print()
    
    queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=1000)
    stop_event = asyncio.Event()

    # Handle clean shutdown on Ctrl+C / SIGTERM
    def _signal_handler():
        print("\nShutdown signal received...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            # On some platforms (e.g., Windows), signals unsupported in this way
            pass

    last_logged_at: Dict[str, float] = {}
    device_counters: Dict[str, int] = {}

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

        now = time.time()
        mac = device.address
        
        # Rate limiting per device
        if min_interval > 0:
            last = last_logged_at.get(mac, 0)
            if now - last < min_interval:
                return
            last_logged_at[mac] = now

        # Count readings per device
        device_counters[mac] = device_counters.get(mac, 0) + 1

        # Prepare database row
        row = {
            "timestamp": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
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
        
        # Add to queue (non-blocking)
        try:
            queue.put_nowait(row)
            
            if verbose:
                print(f"Queued: {mac} - T={parsed['temperature_c']}°C H={parsed['humidity_percent']}% P={parsed['pressure_hpa']}hPa RSSI={adv.rssi}dBm")
                
        except asyncio.QueueFull:
            print("Warning: Queue full, dropping reading")

    # Initialize scanner
    scanner = BleakScanner(detection_callback, adapter=adapter)
    
    # Start database writer task
    writer = asyncio.create_task(database_writer_task(db, queue, stop_event))
    
    # Status reporting task
    async def status_reporter():
        """Report status periodically"""
        while not stop_event.is_set():
            await asyncio.sleep(60)  # Report every minute
            if device_counters:
                total_readings = sum(device_counters.values())
                print(f"Status: {len(device_counters)} devices, {total_readings} total readings, queue size: {queue.qsize()}")
                if verbose:
                    for addr, count in device_counters.items():
                        print(f"  {addr}: {count} readings")
    
    status_task = asyncio.create_task(status_reporter())
    
    try:
        await scanner.start()
        print(f"🔍 Scanning for RuuviTags on {adapter or 'default adapter'}")
        print(f"📁 Logging to database: {db_path}")
        print(f"⏱️  Minimum interval: {min_interval}s per device")
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
        
        print("💾 Finishing database writes...")
        stop_event.set()
        await queue.join()  # Wait for all items to be processed
        await writer
        
        print("📊 Cancelling status reporter...")
        status_task.cancel()
        try:
            await status_task
        except asyncio.CancelledError:
            pass
        
        # Final statistics
        print("\n📈 Session Summary:")
        if device_counters:
            total_readings = sum(device_counters.values())
            print(f"  Devices discovered: {len(device_counters)}")
            print(f"  Total readings logged: {total_readings}")
            print(f"  Devices and readings:")
            for addr, count in sorted(device_counters.items(), key=lambda x: x[1], reverse=True):
                print(f"    {addr}: {count}")
        else:
            print("  No RuuviTag devices found")
        
        # Final database stats
        final_stats = db.get_database_stats()
        print(f"  Database records: {final_stats['total_records']}")
        print(f"  Database size: {final_stats['file_size_mb']} MB")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="RuuviTag BLE logger with SQLite database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 ruuvi_logger_db.py
  python3 ruuvi_logger_db.py --db /path/to/sensors.db --min-interval 10
  python3 ruuvi_logger_db.py --adapter hci0 --verbose
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
        help="Bluetooth adapter (e.g., hci0). Default: system default"
    )
    parser.add_argument(
        "--min-interval", 
        type=float, 
        default=5.0, 
        help="Minimum seconds between logs per device (default: 5.0)"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.min_interval < 0:
        print("Error: min-interval must be >= 0")
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
        asyncio.run(run_logger(args.db, args.adapter, args.min_interval, args.verbose))
    except KeyboardInterrupt:
        pass  # Handled gracefully in run_logger
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()