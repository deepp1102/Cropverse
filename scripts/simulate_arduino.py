"""
Arduino Sensor Simulator
========================
Simulates Arduino device sending sensor data to the API.

This script generates realistic sensor readings and sends them
to the /api/arduino/data endpoint every few seconds.

Usage:
    python scripts/simulate_arduino.py
    python scripts/simulate_arduino.py --mode critical  # Trigger alerts
"""

import requests
import random
import time
import argparse
from datetime import datetime


# API endpoint (change if deployed to Firebase)
API_URL = "http://localhost:8080/api/arduino/data"


def generate_normal_reading():
    """Generate normal sensor readings (no alerts)."""
    return {
        "device_id": "ARDUINO_001",
        "temperature": round(random.uniform(20.0, 30.0), 2),  # 20-30°C (optimal)
        "humidity": round(random.uniform(50.0, 70.0), 2),      # 50-70% (optimal)
        "methane": random.randint(50, 150),                    # 50-150 PPM (safe)
        "other_gases": random.randint(100, 300)                # 100-300 PPM (safe)
    }


def generate_warning_reading():
    """Generate readings that trigger warning alerts."""
    return {
        "device_id": "ARDUINO_001",
        "temperature": round(random.uniform(32.0, 34.0), 2),  # Warning range
        "humidity": round(random.uniform(75.0, 78.0), 2),      # Warning range
        "methane": random.randint(200, 280),                   # Warning range
        "other_gases": random.randint(400, 600)
    }


def generate_critical_reading():
    """Generate readings that trigger critical alerts."""
    return {
        "device_id": "ARDUINO_001",
        "temperature": round(random.uniform(36.0, 45.0), 2),  # Critical!
        "humidity": round(random.uniform(85.0, 95.0), 2),      # Critical!
        "methane": random.randint(320, 500),                   # Critical! (fan activates)
        "other_gases": random.randint(700, 900)
    }


def send_reading(data):
    """
    Send sensor reading to API.
    
    Args:
        data: Dictionary with sensor readings
        
    Returns:
        Response from API
    """
    try:
        print(f"\n{'='*60}")
        print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📤 Sending reading to {API_URL}")
        print(f"📊 Data: {data}")
        
        response = requests.post(API_URL, json=data, timeout=10)
        
        print(f"✅ Status Code: {response.status_code}")
        
        if response.status_code == 201:
            result = response.json()
            print(f"✅ Response: {result.get('message', 'Success')}")
            
            # Check exhaust fan status
            fan_status = result.get('exhaust_fan_status', 'OFF')
            if fan_status == 'ON':
                print(f"💨 EXHAUST FAN ACTIVATED!")
            else:
                print(f"💨 Exhaust fan: {fan_status}")
            
            # Check for alerts
            alerts = result.get('alerts_triggered', [])
            if alerts:
                print(f"🚨 ALERTS TRIGGERED: {len(alerts)}")
                for alert in alerts:
                    emoji = "🚨" if alert['type'] == 'critical' else "⚠️"
                    print(f"   {emoji} {alert['message']}")
            else:
                print(f"✅ No alerts - all values normal")
                
        else:
            print(f"❌ Error: {response.text}")
            
        return response
        
    except requests.exceptions.ConnectionError:
        print(f"❌ CONNECTION ERROR: Cannot reach {API_URL}")
        print(f"   Make sure Flask server is running!")
        print(f"   Run: python functions/main.py")
        return None
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None


def run_simulator(mode='normal', interval=5, count=None):
    """
    Run the Arduino simulator.
    
    Args:
        mode: 'normal', 'warning', 'critical', or 'mixed'
        interval: Seconds between readings
        count: Number of readings to send (None = infinite)
    """
    print("=" * 60)
    print("🌱 CropVerse Arduino Simulator")
    print("=" * 60)
    print(f"Mode: {mode.upper()}")
    print(f"Interval: {interval} seconds")
    print(f"Count: {'Infinite' if count is None else count}")
    print(f"Target: {API_URL}")
    print("=" * 60)
    print("\nPress Ctrl+C to stop\n")
    
    reading_num = 0
    
    try:
        while True:
            reading_num += 1
            
            # Generate reading based on mode
            if mode == 'normal':
                data = generate_normal_reading()
            elif mode == 'warning':
                data = generate_warning_reading()
            elif mode == 'critical':
                data = generate_critical_reading()
            elif mode == 'mixed':
                # Randomly choose: 60% normal, 30% warning, 10% critical
                rand = random.random()
                if rand < 0.6:
                    data = generate_normal_reading()
                elif rand < 0.9:
                    data = generate_warning_reading()
                else:
                    data = generate_critical_reading()
            else:
                data = generate_normal_reading()
            
            # Send reading
            send_reading(data)
            
            # Check if we've reached count limit
            if count is not None and reading_num >= count:
                print(f"\n✅ Sent {count} readings. Stopping simulator.")
                break
            
            # Wait before next reading
            print(f"\n⏳ Waiting {interval} seconds...")
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print(f"\n\n⏹️  Simulator stopped by user")
        print(f"📊 Total readings sent: {reading_num}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Arduino Sensor Simulator')
    parser.add_argument(
        '--mode',
        choices=['normal', 'warning', 'critical', 'mixed'],
        default='normal',
        help='Type of readings to generate'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=5,
        help='Seconds between readings (default: 5)'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=None,
        help='Number of readings to send (default: infinite)'
    )
    parser.add_argument(
        '--url',
        type=str,
        default='http://localhost:8080/api/arduino/data',
        help='API endpoint URL'
    )
    
    args = parser.parse_args()
    
    # Update API URL if provided
    if args.url:
        API_URL = args.url
    
    run_simulator(mode=args.mode, interval=args.interval, count=args.count)