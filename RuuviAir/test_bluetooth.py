#!/usr/bin/env python3
"""
Bluetooth Environment Test
Quick check if Bluetooth scanning will work
"""

import asyncio
import sys

async def test_bluetooth():
    """Test Bluetooth environment"""
    
    print("\n" + "="*60)
    print("BLUETOOTH ENVIRONMENT TEST")
    print("="*60 + "\n")
    
    errors = []
    warnings = []
    
    # Test 1: Python version
    print("1. Checking Python version...")
    if sys.version_info >= (3, 7):
        print(f"   ✓ Python {sys.version.split()[0]} (OK)")
    else:
        print(f"   ✗ Python {sys.version.split()[0]} (need 3.7+)")
        errors.append("Python version too old")
    
    # Test 2: Import bleak
    print("\n2. Checking bleak library...")
    try:
        import bleak
        if hasattr(bleak, '__version__'):
            print(f"   ✓ Bleak {bleak.__version__} installed")
        else:
            print(f"   ✓ Bleak installed (version info not available)")
    except ImportError:
        print(f"   ✗ Bleak not found")
        errors.append("Bleak not installed - run: pip3 install bleak")
        return errors, warnings
    
    # Test 3: BLE Scanner
    print("\n3. Testing BLE scanner...")
    try:
        from bleak import BleakScanner
        devices = await BleakScanner.discover(timeout=5.0, return_adv=False)
        print(f"   ✓ Scanner works - found {len(devices)} device(s)")
        
        if len(devices) == 0:
            warnings.append("No BLE devices found - check if Bluetooth is enabled")
        
        # Show first few devices
        if devices:
            print("\n   First detected devices:")
            for i, device in enumerate(devices[:3]):
                print(f"   - {device.name or 'Unknown'} ({device.address})")
            if len(devices) > 3:
                print(f"   ... and {len(devices) - 3} more")
                
    except Exception as e:
        print(f"   ✗ Scanner failed: {e}")
        errors.append(f"BLE Scanner error: {e}")
        
        # Try to give helpful advice
        error_str = str(e).lower()
        if "permission" in error_str or "access" in error_str:
            warnings.append("Try running with: sudo python3 test_bluetooth.py")
        if "adapter" in error_str or "bluetooth" in error_str:
            warnings.append("Check Bluetooth status: sudo systemctl status bluetooth")
    
    # Test 4: Check for Ruuvi devices
    print("\n4. Quick scan for Ruuvi devices (10 seconds)...")
    try:
        from bleak import BleakScanner
        from bleak.backends.device import BLEDevice
        from bleak.backends.scanner import AdvertisementData
        
        ruuvi_found = []
        
        def detection_callback(device: BLEDevice, advertisement_data: AdvertisementData):
            if 0x0499 in advertisement_data.manufacturer_data:
                ruuvi_found.append({
                    'name': device.name,
                    'address': device.address,
                    'rssi': advertisement_data.rssi if hasattr(advertisement_data, 'rssi') else None,
                    'data': advertisement_data.manufacturer_data[0x0499]
                })
        
        scanner = BleakScanner(detection_callback=detection_callback)
        await scanner.start()
        await asyncio.sleep(10)
        await scanner.stop()
        
        if ruuvi_found:
            print(f"   ✓ Found {len(ruuvi_found)} Ruuvi device(s):")
            for ruuvi in ruuvi_found:
                format_byte = ruuvi['data'][0] if len(ruuvi['data']) > 0 else None
                format_name = {
                    0x03: "Format 3 (RAWv1)",
                    0x05: "Format 5 (RAWv2)",
                    0xE1: "Format E1 (Extended v1)"
                }.get(format_byte, f"Unknown format 0x{format_byte:02X}" if format_byte else "Unknown")
                
                print(f"   - {ruuvi['name'] or 'Unknown'} ({ruuvi['address']})")
                print(f"     RSSI: {ruuvi['rssi']} dBm, Format: {format_name}")
                
                if format_byte != 0xE1:
                    warnings.append(f"Device {ruuvi['address']} uses format 0x{format_byte:02X}, not E1")
        else:
            print(f"   ⚠ No Ruuvi devices found")
            warnings.append("No Ruuvi devices detected - check device is on and nearby")
            
    except Exception as e:
        print(f"   ✗ Ruuvi scan failed: {e}")
        errors.append(f"Ruuvi scan error: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    if not errors and not warnings:
        print("\n✓ All tests passed! Your system is ready for Ruuvi scanning.")
        print("\nYou can now run:")
        print("  sudo python3 ruuvi_e1_scanner.py")
    else:
        if errors:
            print("\n✗ ERRORS found:")
            for error in errors:
                print(f"  - {error}")
        
        if warnings:
            print("\n⚠ WARNINGS:")
            for warning in warnings:
                print(f"  - {warning}")
        
        print("\nRecommended actions:")
        if any("Bleak" in e for e in errors):
            print("  1. Install bleak: pip3 install bleak")
        if any("permission" in w.lower() or "sudo" in w.lower() for w in warnings):
            print("  2. Run with sudo: sudo python3 test_bluetooth.py")
        if any("bluetooth" in w.lower() for w in warnings):
            print("  3. Enable Bluetooth: sudo systemctl start bluetooth")
        if any("format" in w.lower() for w in warnings):
            print("  4. Change Ruuvi format to E1 in Ruuvi Station app")
    
    print("="*60 + "\n")
    
    return errors, warnings


async def main():
    """Main function"""
    try:
        errors, warnings = await test_bluetooth()
        
        # Exit code: 0 = success, 1 = warnings, 2 = errors
        if errors:
            sys.exit(2)
        elif warnings:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n\nTest interrupted.")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())
