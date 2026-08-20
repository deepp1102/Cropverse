"""
API Testing Script
==================
Tests all CropVerse API endpoints locally.

Usage:
    python scripts/test_api.py
"""

import requests
import json
from datetime import datetime, timedelta


BASE_URL = "http://localhost:8080"


def print_response(response, title):
    """Pretty print API response."""
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print(f"{'='*60}")
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        print(f"Response:\n{json.dumps(data, indent=2)}")
    except:
        print(f"Response: {response.text}")
    print(f"{'='*60}\n")


def test_health_check():
    """Test health check endpoint."""
    response = requests.get(f"{BASE_URL}/health")
    print_response(response, "Health Check")


def test_root():
    """Test root endpoint."""
    response = requests.get(f"{BASE_URL}/")
    print_response(response, "Root Endpoint")


def test_arduino_data():
    """Test Arduino data submission.""" 
    data = {
        "device_id": "TEST_ARDUINO_001",
        "temperature": 25.5,
        "humidity": 65.0,
        "methane": 100,
        "other_gases": 250
    }
    response = requests.post(f"{BASE_URL}/api/arduino/data", json=data)
    print_response(response, "Arduino Data Submission")


def test_dashboard_summary():
    """Test dashboard summary endpoint."""
    # FIXED: Changed from /api/dashboard/summary to /api/dashboard
    response = requests.get(f"{BASE_URL}/api/dashboard")
    print_response(response, "Dashboard Summary")


def test_dashboard_latest_readings():
    """Test latest readings endpoint."""
    # FIXED: Changed from /api/dashboard/latest-readings to /api/dashboard/readings
    response = requests.get(f"{BASE_URL}/api/dashboard/readings?limit=5")
    print_response(response, "Latest Readings (limit=5)")


def test_dashboard_recent_alerts():
    """Test recent alerts endpoint."""
    response = requests.get(f"{BASE_URL}/api/dashboard/alerts")
    print_response(response, "Recent Alerts")


def test_analytics_trends():
    """Test analytics trends endpoint."""
    response = requests.get(f"{BASE_URL}/api/analytics/trends?days=7")
    print_response(response, "Analytics Trends (7 days)")


def test_chatbot():
    """Test chatbot endpoint."""
    data = {
        "message": "What are the current sensor readings?",
        "user_id": "test_user_123"
    }
    response = requests.post(f"{BASE_URL}/api/chatbot/message", json=data)
    print_response(response, "Chatbot Response")


def run_all_tests():
    """Run all API tests."""
    print("\n" + "="*60)
    print("🧪 CropVerse API Test Suite")
    print("="*60)
    print(f"Target: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    try:
        # Basic endpoints
        test_root()
        test_health_check()
        
        # Arduino endpoint
        test_arduino_data()
        
        # Dashboard endpoints
        test_dashboard_summary()
        test_dashboard_latest_readings()
        test_dashboard_recent_alerts()
        
        # Analytics endpoint
        test_analytics_trends()
        
        # Chatbot endpoint
        test_chatbot()
        
        print("\n" + "="*60)
        print("✅ All tests completed!")
        print("="*60)
        
    except requests.exceptions.ConnectionError:
        print("\n" + "="*60)
        print("❌ CONNECTION ERROR")
        print("="*60)
        print(f"Cannot connect to {BASE_URL}")
        print("\nMake sure Flask server is running:")
        print("  cd functions")
        print("  python main.py")
        print("="*60)


if __name__ == '__main__':
    run_all_tests()