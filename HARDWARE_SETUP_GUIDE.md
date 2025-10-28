# 🔧 ESP32 Hardware Setup Guide

## 📋 Required Components

### ESP32 Development Board
- ESP32 DevKit V1 or similar
- USB cable for programming and power

### LEDs (3x)
- 1x Red LED (5mm)
- 1x Green LED (5mm) 
- 1x Blue LED (5mm)
- 3x 220Ω resistors (for LED current limiting)

### Buzzer
- 1x Active Buzzer (5V)
- 1x 1kΩ resistor (optional, for volume control)

### Additional Components
- Breadboard (optional, for prototyping)
- Jumper wires
- Power supply (5V/2A recommended)

## 🔌 Wiring Diagram

```
ESP32 Pin    →    Component
─────────────────────────────────
GPIO 2       →    Red LED + 220Ω resistor to GND
GPIO 4       →    Green LED + 220Ω resistor to GND  
GPIO 5       →    Blue LED + 220Ω resistor to GND
GPIO 18      →    Buzzer positive terminal
GND          →    Buzzer negative terminal + LED cathodes
3.3V         →    Power for components (if needed)
```

## 📐 Detailed Connections

### LED Connections
```
Red LED:
- Anode (long leg) → GPIO 2
- Cathode (short leg) → 220Ω resistor → GND

Green LED:
- Anode (long leg) → GPIO 4
- Cathode (short leg) → 220Ω resistor → GND

Blue LED:
- Anode (long leg) → GPIO 5
- Cathode (short leg) → 220Ω resistor → GND
```

### Buzzer Connection
```
Active Buzzer:
- Positive terminal → GPIO 18
- Negative terminal → GND
```

## ⚙️ ESP32 Code Configuration

### 1. Update WiFi Credentials
In both `esp32_code.ino` and `esp32_enhanced.ino`:
```cpp
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
```

### 2. Update Server IP Address
```cpp
const char* server_host = "YOUR_COMPUTER_IP";  // e.g., "192.168.1.100"
```

### 3. Hardware Pin Configuration
The code is already configured with the correct pins:
```cpp
const int RED_LED_PIN = 2;
const int GREEN_LED_PIN = 4;
const int BLUE_LED_PIN = 5;
const int BUZZER_PIN = 18;
```

## 🚀 Upload Process

### 1. Install Required Libraries
In Arduino IDE, install these libraries:
- `WebSocketsClient` by Markus Sattler
- `ArduinoJson` by Benoit Blanchon
- `ArduinoOTA` (included with ESP32 core)

### 2. Board Configuration
- Board: "ESP32 Dev Module"
- Upload Speed: 115200
- CPU Frequency: 240MHz
- Flash Frequency: 80MHz
- Flash Mode: QIO
- Flash Size: 4MB
- Partition Scheme: Default 4MB

### 3. Upload Code
1. Connect ESP32 via USB
2. Select correct COM port
3. Upload `esp32_enhanced.ino` (recommended for full features)
4. Open Serial Monitor (115200 baud) to see connection status

## 🔍 Testing Hardware

### 1. Power On Test
When ESP32 starts, you should see:
- Built-in LED blinking (status indicator)
- Serial output showing WiFi connection
- WebSocket connection to server

### 2. LED Test
The LEDs will respond to market signals:
- **Red LED**: Market down (price below threshold)
- **Green LED**: Market up (price above threshold)
- **Blue LED**: You have invested in this coin
- **No LED**: Price within threshold range

### 3. Buzzer Test
Buzzer will sound for:
- Significant price changes (>5% by default)
- User-configured alerts
- System notifications

## 🎛️ Personalized Settings

The enhanced version supports:
- **LED Brightness**: 0-100% control
- **Buzzer Volume**: 0-100% control  
- **Buzzer Duration**: 100-10000ms
- **LED Blink Speed**: 100-2000ms
- **Enable/Disable**: Individual control for LEDs and buzzer

## 🔧 Troubleshooting

### ESP32 Not Connecting to WiFi
1. Check WiFi credentials in code
2. Ensure WiFi network is 2.4GHz (ESP32 doesn't support 5GHz)
3. Check signal strength
4. Try different WiFi network

### ESP32 Not Connecting to Server
1. Verify server IP address in code
2. Ensure Flask application is running
3. Check firewall settings
4. Verify server is accessible from ESP32's network

### LEDs Not Working
1. Check wiring connections
2. Verify resistor values (220Ω)
3. Test LEDs individually with multimeter
4. Check GPIO pin assignments

### Buzzer Not Working
1. Verify buzzer polarity
2. Check if buzzer is active (not passive)
3. Test with direct 5V connection
4. Verify GPIO 18 connection

### WebSocket Connection Issues
1. Check server logs for connection attempts
2. Verify WebSocket endpoint is accessible
3. Check network connectivity
4. Review ESP32 serial output for errors

## 📊 Expected Serial Output

```
Starting Enhanced IoT Stock Monitor...
Connecting to WiFi: YOUR_WIFI_SSID
WiFi connected!
IP address: 192.168.1.100
MAC address: 24:6F:28:XX:XX:XX
OTA Ready
WebSocket Connected
Sent connection message
```

## 🎯 Hardware Verification Checklist

- [ ] ESP32 powers on and connects to WiFi
- [ ] Serial monitor shows connection status
- [ ] WebSocket connects to Flask server
- [ ] Red LED responds to market down signals
- [ ] Green LED responds to market up signals  
- [ ] Blue LED responds to invested coin signals
- [ ] Buzzer sounds for significant price changes
- [ ] Personalized settings work (brightness, volume)
- [ ] OTA updates work (optional)
- [ ] System runs without errors

## 🔄 Maintenance

### Regular Checks
- Monitor serial output for errors
- Check WiFi connection stability
- Verify server connectivity
- Test LED and buzzer functionality

### Updates
- Update ESP32 code when server changes
- Monitor for new features
- Check for security updates
- Backup working configurations

## 📞 Support

If you encounter issues:
1. Check this guide first
2. Review serial monitor output
3. Verify all connections
4. Test components individually
5. Check server logs for errors

The system is designed to be robust and self-healing, but proper hardware setup is essential for optimal performance.
