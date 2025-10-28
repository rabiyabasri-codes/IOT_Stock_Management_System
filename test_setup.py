#!/usr/bin/env python3
"""
Test script for IoT Stock Monitor setup
This script verifies that all components are working correctly
"""

import requests
import json
import sys
import time
from datetime import datetime

def test_api_connection():
    """Test connection to CoinGecko API"""
    print("🔍 Testing CoinGecko API connection...")
    
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': 'bitcoin,ethereum',
            'vs_currencies': 'usd',
            'include_24hr_change': 'true'
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ CoinGecko API connection successful!")
            print(f"   Bitcoin: ${data['bitcoin']['usd']:.2f} ({data['bitcoin']['usd_24h_change']:.2f}%)")
            print(f"   Ethereum: ${data['ethereum']['usd']:.2f} ({data['ethereum']['usd_24h_change']:.2f}%)")
            return True
        else:
            print(f"❌ API request failed with status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ API connection failed: {e}")
        return False

def test_flask_app():
    """Test if Flask app is running"""
    print("\n🔍 Testing Flask application...")
    
    try:
        response = requests.get("http://localhost:5000", timeout=5)
        
        if response.status_code == 200:
            print("✅ Flask application is running!")
            return True
        else:
            print(f"❌ Flask app returned status: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Flask application is not running")
        print("   Start it with: python app.py")
        return False
    except Exception as e:
        print(f"❌ Flask test failed: {e}")
        return False

def test_websocket_connection():
    """Test WebSocket connection"""
    print("\n🔍 Testing WebSocket connection...")
    
    try:
        import socketio
        
        sio = socketio.Client()
        
        @sio.event
        def connect():
            print("✅ WebSocket connection successful!")
            sio.disconnect()
        
        @sio.event
        def disconnect():
            print("   WebSocket disconnected")
        
        sio.connect('http://localhost:5000')
        sio.wait()
        return True
        
    except ImportError:
        print("⚠️  python-socketio not installed, skipping WebSocket test")
        return True
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        return False

def test_coin_list():
    """Test fetching coin list"""
    print("\n🔍 Testing coin list API...")
    
    try:
        response = requests.get("http://localhost:5000/api/coins", timeout=10)
        
        if response.status_code == 200:
            coins = response.json()
            print(f"✅ Coin list API working! Found {len(coins)} coins")
            if coins:
                print(f"   Example: {coins[0]['name']} (${coins[0]['current_price']})")
            return True
        else:
            print(f"❌ Coin list API failed with status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Coin list test failed: {e}")
        return False

def test_settings_api():
    """Test settings API"""
    print("\n🔍 Testing settings API...")
    
    try:
        # Test GET
        response = requests.get("http://localhost:5000/api/settings", timeout=5)
        
        if response.status_code == 200:
            settings = response.json()
            print("✅ Settings GET API working!")
            print(f"   Current threshold: {settings.get('threshold', 'Not set')}")
            print(f"   Selected coins: {len(settings.get('selected_coins', []))}")
            
            # Test POST
            test_settings = {
                'threshold': 5.0,
                'selected_coins': ['bitcoin', 'ethereum'],
                'invested_coins': ['bitcoin']
            }
            
            response = requests.post(
                "http://localhost:5000/api/settings",
                json=test_settings,
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            
            if response.status_code == 200:
                print("✅ Settings POST API working!")
                return True
            else:
                print(f"❌ Settings POST failed with status: {response.status_code}")
                return False
        else:
            print(f"❌ Settings GET failed with status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Settings API test failed: {e}")
        return False

def check_dependencies():
    """Check if all required packages are installed"""
    print("🔍 Checking Python dependencies...")
    
    required_packages = [
        'flask',
        'flask_socketio', 
        'requests',
        'python_socketio',
        'python_engineio',
        'websocket_client',
        'python_dotenv',
        'schedule'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - not installed")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Install them with: pip install -r requirements.txt")
        return False
    else:
        print("✅ All dependencies are installed!")
        return True

def main():
    """Run all tests"""
    print("🚀 IoT Stock Monitor - Setup Test")
    print("=" * 50)
    
    tests = [
        ("Dependencies", check_dependencies),
        ("CoinGecko API", test_api_connection),
        ("Flask App", test_flask_app),
        ("WebSocket", test_websocket_connection),
        ("Coin List API", test_coin_list),
        ("Settings API", test_settings_api)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your setup is ready to go!")
        print("\nNext steps:")
        print("1. Configure your ESP32 with the provided code")
        print("2. Update WiFi credentials in esp32_code.ino")
        print("3. Upload the code to your ESP32")
        print("4. Open http://localhost:5000 in your browser")
        print("5. Configure your monitoring settings")
    else:
        print("⚠️  Some tests failed. Please fix the issues above.")
        print("\nCommon solutions:")
        print("- Install missing packages: pip install -r requirements.txt")
        print("- Start Flask app: python app.py")
        print("- Check your internet connection")
        print("- Verify firewall settings")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
