from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import DataRequired
import requests
import json
import time
import threading
from datetime import datetime
import os
from dotenv import load_dotenv
from flask_cors import CORS

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['CORS_HEADERS'] = 'Content-Type'
app.secret_key = 'your_secret_key_here'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables to store user settings and market data
user_settings = {
    'threshold': 0,
    'selected_coins': [],
    'invested_coins': []
}

market_data = {}
esp32_connected = False

# CoinGecko API configuration
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"

class MarketMonitor:
    def __init__(self):
        self.running = False
        self.thread = None
    
    def start_monitoring(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._monitor_loop)
            self.thread.daemon = True
            self.thread.start()
    
    def stop_monitoring(self):
        self.running = False
    
    def _monitor_loop(self):
        while self.running:
            try:
                self._fetch_market_data()
                self._analyze_and_send_signals()
                time.sleep(10)  # Update every 10 seconds
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(30)  # Wait longer on error
    
    def _fetch_market_data(self):
        global market_data
        
        if not user_settings['selected_coins']:
            return
        
        try:
            # Get current prices for selected coins
            coin_ids = ','.join(user_settings['selected_coins'])
            url = f"{COINGECKO_API_URL}/simple/price"
            params = {
                'ids': coin_ids,
                'vs_currencies': 'usd',
                'include_24hr_change': 'true'
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                market_data = response.json()
                print(f"Market data updated: {market_data}")
            else:
                print(f"API request failed: {response.status_code}")
                
        except Exception as e:
            print(f"Error fetching market data: {e}")
    
    def _analyze_and_send_signals(self):
        global market_data, user_settings
        
        if not market_data or not user_settings['selected_coins']:
            return
        
        signals = {}
        
        for coin in user_settings['selected_coins']:
            if coin in market_data:
                current_price = market_data[coin]['usd']
                price_change_24h = market_data[coin].get('usd_24h_change', 0)
                
                # Determine LED color based on logic
                if coin in user_settings['invested_coins']:
                    # Blue for invested coins
                    led_color = 'blue'
                    signal = 'invested'
                elif price_change_24h > user_settings['threshold']:
                    # Green for positive change above threshold
                    led_color = 'green'
                    signal = 'up'
                elif price_change_24h < -user_settings['threshold']:
                    # Red for negative change below threshold
                    led_color = 'red'
                    signal = 'down'
                else:
                    # No significant change
                    led_color = 'off'
                    signal = 'neutral'
                
                signals[coin] = {
                    'price': current_price,
                    'change_24h': price_change_24h,
                    'led_color': led_color,
                    'signal': signal,
                    'timestamp': datetime.now().isoformat()
                }
        
        # Send signals to frontend and ESP32
        socketio.emit('market_update', {
            'signals': signals,
            'market_data': market_data
        })
        
        # Send to ESP32 if connected
        if esp32_connected:
            self._send_to_esp32(signals)
    
    def _send_to_esp32(self, signals):
        # This will be implemented when we add ESP32 communication
        print(f"Sending to ESP32: {signals}")

# Initialize market monitor
market_monitor = MarketMonitor()

class AdminLoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        print(f"Error rendering template: {e}")
        return f"""
        <html>
            <body>
                <h1>Crypto Monitor</h1>
                <p>Error: Could not load template. Make sure templates folder exists.</p>
                <p>Details: {str(e)}</p>
            </body>
        </html>
        """

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    form = AdminLoginForm()
    return render_template('admin_login.html', form=form)

@app.route('/api/settings', methods=['POST'])
def update_settings():
    global user_settings
    
    data = request.json
    user_settings.update({
        'threshold': float(data.get('threshold', 0)),
        'selected_coins': data.get('selected_coins', []),
        'invested_coins': data.get('invested_coins', [])
    })
    
    # Start monitoring if we have coins selected
    if user_settings['selected_coins'] and not market_monitor.running:
        market_monitor.start_monitoring()
    
    return jsonify({'status': 'success', 'settings': user_settings})

@app.route('/api/settings', methods=['GET'])
def get_settings():
    return jsonify(user_settings)

@app.route('/api/coins')
def get_available_coins():
    try:
        # Get list of popular cryptocurrencies
        url = f"{COINGECKO_API_URL}/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 50,
            'page': 1
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            coins = response.json()
            return jsonify([{
                'id': coin['id'],
                'name': coin['name'],
                'symbol': coin['symbol'].upper(),
                'current_price': coin['current_price']
            } for coin in coins])
        else:
            return jsonify([])
    except Exception as e:
        print(f"Error fetching coins: {e}")
        return jsonify([])

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('connected', {'status': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('esp32_connect')
def handle_esp32_connect():
    global esp32_connected
    esp32_connected = True
    print('ESP32 connected')
    emit('esp32_status', {'connected': True})

@socketio.on('esp32_disconnect')
def handle_esp32_disconnect():
    global esp32_connected
    esp32_connected = False
    print('ESP32 disconnected')
    emit('esp32_status', {'connected': False})

if __name__ == '__main__':
    try:
        print("Starting IoT Stock Monitor Application...")
        print("Access the application at: http://localhost:6000")
        print("Press Ctrl+C to stop the server")
        socketio.run(app, debug=True, host='0.0.0.0', port=6000, allow_unsafe_werkzeug=True)
    except Exception as e:
        print(f"Error starting server: {e}")
        print("Make sure port 6000 is not in use")
        print("Try running 'netstat -ano | findstr 6000' to check if the port is in use")
