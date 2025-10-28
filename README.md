# IoT Stock Monitor

A real-time cryptocurrency monitoring system that uses ESP32 hardware to provide visual and audio feedback based on market movements.

## Features

- **Real-time Market Data**: Fetches live cryptocurrency prices from CoinGecko API
- **Hardware Visualization**: ESP32 controls RGB LEDs and buzzer based on market signals
- **Smart LED Logic**:
  - 🔴 **Red LED**: Price drops below threshold
  - 🟢 **Green LED**: Price rises above threshold  
  - 🔵 **Blue LED**: You have invested in this coin
  - ⚫ **No LED**: Price change within threshold
- **Web Dashboard**: Beautiful real-time interface to monitor and configure
- **Buzzer Alerts**: Audio alerts for significant price changes
- **Multi-coin Support**: Monitor multiple cryptocurrencies simultaneously

## Hardware Requirements

### ESP32 Components
- ESP32 Development Board
- 3x LEDs (Red, Green, Blue) with 220Ω resistors
- 1x Buzzer (5V)
- Breadboard and jumper wires
- USB cable for programming

### Wiring Diagram
```
ESP32 Pin    Component
GPIO 2   →   Red LED (with 220Ω resistor to GND)
GPIO 4   →   Green LED (with 220Ω resistor to GND)  
GPIO 5   →   Blue LED (with 220Ω resistor to GND)
GPIO 18  →   Buzzer positive terminal
GND      →   Buzzer negative terminal, LED cathodes
```

## Software Setup

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Copy the example configuration
cp config.env.example .env

# Edit .env with your settings
# Update WiFi credentials and server IP
```

### 3. Run the Flask Application
```bash
python app.py
```

The web interface will be available at: `http://localhost:5000`

### 4. ESP32 Setup

#### Install Required Libraries
In Arduino IDE, install these libraries:
- `WebSocketsClient` by Markus Sattler
- `ArduinoJson` by Benoit Blanchon
- `ArduinoOTA` (included with ESP32 core)

#### Configure ESP32 Code
1. Open `esp32_code.ino` in Arduino IDE
2. Update WiFi credentials:
   ```cpp
   const char* ssid = "YOUR_WIFI_SSID";
   const char* password = "YOUR_WIFI_PASSWORD";
   ```
3. Update server IP:
   ```cpp
   const char* server_host = "YOUR_SERVER_IP";
   ```
4. Upload to ESP32

## Usage

### 1. Configure Monitoring
1. Open the web interface at `http://localhost:5000`
2. Set your threshold percentage (e.g., 5% for 5% price changes)
3. Select cryptocurrencies to monitor
4. Mark which coins you have invested in (for blue LED)
5. Click "Save Configuration"

### 2. Hardware Connection
1. Power on your ESP32
2. Ensure it connects to WiFi (check serial monitor)
3. The ESP32 should connect to your Flask server automatically
4. LEDs will start responding to market movements

### 3. Monitoring
- **Red LED**: Market is down (price dropped below threshold)
- **Green LED**: Market is up (price rose above threshold)
- **Blue LED**: You have invested in this coin
- **Buzzer**: Significant price changes (>5% by default)

## API Endpoints

### Web Interface
- `GET /` - Main dashboard
- `GET /api/coins` - List available cryptocurrencies
- `GET /api/settings` - Get current configuration
- `POST /api/settings` - Update configuration

### WebSocket Events
- `market_update` - Real-time market data and signals
- `esp32_connect` - ESP32 connection status
- `heartbeat` - ESP32 status updates

## Configuration Options

### Threshold Settings
- Set percentage threshold for price change detection
- Below threshold = Red LED
- Above threshold = Green LED
- Within threshold = No LED

### Coin Selection
- Choose from 50+ popular cryptocurrencies
- Monitor multiple coins simultaneously
- Mark invested coins for blue LED indication

### Hardware Settings
- Customize LED pins in ESP32 code
- Adjust buzzer sensitivity
- Configure update intervals

## Troubleshooting

### ESP32 Not Connecting
1. Check WiFi credentials in code
2. Verify server IP address
3. Check serial monitor for error messages
4. Ensure ESP32 and computer are on same network

### No Market Data
1. Check internet connection
2. Verify CoinGecko API is accessible
3. Check browser console for errors
4. Restart Flask application

### LEDs Not Working
1. Check wiring connections
2. Verify GPIO pin assignments
3. Test LEDs individually
4. Check power supply

### WebSocket Connection Issues
1. Check firewall settings
2. Verify port 5000 is open
3. Try different network
4. Check ESP32 serial output

## Advanced Features

### OTA Updates
The ESP32 supports Over-The-Air updates:
- Hostname: `ESP32-StockMonitor`
- Password: `stockmonitor123`
- Access via Arduino IDE or web interface

### Custom Alerts
Modify the buzzer logic in ESP32 code:
```cpp
if (abs(priceChange) > 5.0) {  // Change threshold
    triggerBuzzer();
}
```

### Multiple ESP32s
You can connect multiple ESP32 devices to monitor different coins or provide redundancy.

## Security Notes

- Change default OTA password
- Use HTTPS in production
- Implement authentication for web interface
- Secure your WiFi network

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source. Feel free to modify and distribute.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review serial monitor output
3. Check browser console for errors
4. Create an issue with detailed information

---

**Happy Trading! 📈📉**
