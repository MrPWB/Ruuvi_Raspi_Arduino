#!/usr/bin/env python3
"""
ThingSpeak Integration for Ruuvi Scanner
Uploads sensor data to ThingSpeak cloud platform
"""

import requests
import time
from typing import Dict, Any, Optional
from datetime import datetime


class ThingSpeakUploader:
    """
    ThingSpeak cloud uploader for Ruuvi sensor data
    
    ThingSpeak Field Mapping:
    - field1: Temperature (°C)
    - field2: Humidity (%)
    - field3: Pressure (Pa)
    - field4: PM2.5 (µg/m³)
    - field5: CO2 (ppm)
    - field6: VOC Index
    - field7: NOX Index
    - field8: Luminosity (lux)
    """
    
    def __init__(self, api_key: str, channel_id: str = None, interval: int = 15):
        """
        Initialize ThingSpeak uploader
        
        Args:
            api_key: ThingSpeak Write API Key
            channel_id: Optional channel ID (for logging)
            interval: Minimum seconds between uploads (default: 15 for free accounts)
        """
        self.api_key = api_key
        self.channel_id = channel_id
        self.interval = interval
        self.base_url = "https://api.thingspeak.com/update"
        self.last_upload = 0
        self.upload_count = 0
        self.error_count = 0
        
    def can_upload(self) -> bool:
        """Check if enough time has passed since last upload"""
        return (time.time() - self.last_upload) >= self.interval
    
    def upload(self, data: Dict[str, Any], force: bool = False) -> bool:
        """
        Upload sensor data to ThingSpeak
        
        Args:
            data: Dictionary with sensor data
            force: Force upload even if interval not reached
            
        Returns:
            True if upload successful, False otherwise
        """
        # Check rate limit
        if not force and not self.can_upload():
            return False
        
        try:
            # Prepare payload
            payload = {
                'api_key': self.api_key
            }
            
            # Map sensor data to ThingSpeak fields
            if data.get('temperature') is not None:
                payload['field1'] = f"{data['temperature']:.2f}"
            
            if data.get('humidity') is not None:
                payload['field2'] = f"{data['humidity']:.2f}"
            
            if data.get('pressure') is not None:
                payload['field3'] = str(data['pressure'])
            
            if data.get('pm2_5') is not None:
                payload['field4'] = f"{data['pm2_5']:.1f}"
            
            if data.get('co2') is not None:
                payload['field5'] = str(data['co2'])
            
            if data.get('voc') is not None:
                payload['field6'] = str(data['voc'])
            
            if data.get('nox') is not None:
                payload['field7'] = str(data['nox'])
            
            if data.get('luminosity') is not None:
                payload['field8'] = f"{data['luminosity']:.2f}"
            
            # Send POST request
            response = requests.post(
                self.base_url,
                data=payload,
                timeout=10
            )
            
            # Check response
            if response.status_code == 200:
                # ThingSpeak returns the entry ID on success
                entry_id = response.text.strip()
                if entry_id != '0':
                    self.last_upload = time.time()
                    self.upload_count += 1
                    return True
                else:
                    self.error_count += 1
                    print(f"[ThingSpeak] Upload failed: Invalid response (0)")
                    return False
            else:
                self.error_count += 1
                print(f"[ThingSpeak] Upload failed: HTTP {response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            self.error_count += 1
            print(f"[ThingSpeak] Upload timeout")
            return False
        except requests.exceptions.RequestException as e:
            self.error_count += 1
            print(f"[ThingSpeak] Upload error: {e}")
            return False
        except Exception as e:
            self.error_count += 1
            print(f"[ThingSpeak] Unexpected error: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get upload statistics"""
        return {
            'uploads': self.upload_count,
            'errors': self.error_count,
            'last_upload': datetime.fromtimestamp(self.last_upload).isoformat() if self.last_upload > 0 else None,
            'interval': self.interval
        }


class ThingSpeakQueue:
    """
    Queue-based uploader with averaging for high-frequency data
    Useful when sensor updates faster than ThingSpeak rate limit
    """
    
    def __init__(self, uploader: ThingSpeakUploader):
        """
        Initialize queue uploader
        
        Args:
            uploader: ThingSpeakUploader instance
        """
        self.uploader = uploader
        self.queue = []
        self.max_queue_size = 10
    
    def add(self, data: Dict[str, Any]):
        """Add data to queue"""
        self.queue.append(data)
        
        # Keep queue size limited
        if len(self.queue) > self.max_queue_size:
            self.queue.pop(0)
    
    def process(self) -> bool:
        """
        Process queue and upload averaged data if interval reached
        
        Returns:
            True if upload was performed
        """
        if not self.uploader.can_upload() or len(self.queue) == 0:
            return False
        
        # Calculate averages
        averaged = self._average_data()
        
        # Upload
        success = self.uploader.upload(averaged, force=True)
        
        if success:
            # Clear queue after successful upload
            self.queue.clear()
        
        return success
    
    def _average_data(self) -> Dict[str, Any]:
        """Calculate average values from queue"""
        if not self.queue:
            return {}
        
        # Numeric fields to average
        fields = ['temperature', 'humidity', 'pressure', 'pm2_5', 
                  'co2', 'voc', 'nox', 'luminosity']
        
        averaged = {}
        
        for field in fields:
            values = [d.get(field) for d in self.queue if d.get(field) is not None]
            if values:
                averaged[field] = sum(values) / len(values)
        
        # Keep latest timestamp
        averaged['timestamp'] = self.queue[-1].get('timestamp')
        
        return averaged


def test_thingspeak(api_key: str):
    """
    Test ThingSpeak connection
    
    Args:
        api_key: Your ThingSpeak Write API Key
    """
    print("\n" + "="*60)
    print("ThingSpeak Connection Test")
    print("="*60 + "\n")
    
    uploader = ThingSpeakUploader(api_key)
    
    # Test data
    test_data = {
        'temperature': 21.5,
        'humidity': 45.2,
        'pressure': 101325,
        'pm2_5': 12.3,
        'co2': 450,
        'voc': 95,
        'nox': 2,
        'luminosity': 245.5
    }
    
    print("Sending test data...")
    success = uploader.upload(test_data, force=True)
    
    if success:
        print("✓ Upload successful!")
        print(f"  Uploads: {uploader.upload_count}")
        print(f"  Check your channel: https://thingspeak.com/channels/{uploader.channel_id or 'YOUR_CHANNEL'}")
    else:
        print("✗ Upload failed")
        print(f"  Errors: {uploader.error_count}")
    
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 thingspeak_integration.py YOUR_API_KEY")
        print("\nGet your API key from: https://thingspeak.com/channels")
        sys.exit(1)
    
    test_thingspeak(sys.argv[1])
