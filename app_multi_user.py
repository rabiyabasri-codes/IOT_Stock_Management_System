from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, PasswordField, FloatField, SelectMultipleField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length, NumberRange
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import requests
import json
import time
import threading
import os
from dotenv import load_dotenv
from sqlalchemy import event
from sqlalchemy.orm import Session
from wtforms import ValidationError

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///iot_stock_monitor.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Initialize extensions
db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# CoinGecko API configuration
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # User settings
    threshold = db.Column(db.Float, default=5.0)
    selected_coins = db.Column(db.Text)  # JSON string
    invested_coins = db.Column(db.Text)  # JSON string
    
    # Personalized output settings
    enable_led = db.Column(db.Boolean, default=True)
    enable_buzzer = db.Column(db.Boolean, default=True)
    led_brightness = db.Column(db.Integer, default=100)  # 0-100%
    buzzer_volume = db.Column(db.Integer, default=50)  # 0-100%
    buzzer_duration = db.Column(db.Integer, default=2000)  # milliseconds
    led_blink_speed = db.Column(db.Integer, default=500)  # milliseconds
    
    # ESP32 connection
    esp32_connected = db.Column(db.Boolean, default=False)
    esp32_last_seen = db.Column(db.DateTime)
    
    # Relationship to user coin selections
    coin_selections = db.relationship('UserCoinSelection', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_selected_coins(self):
        if self.selected_coins:
            return json.loads(self.selected_coins)
        return []
    
    def set_selected_coins(self, coins):
        self.selected_coins = json.dumps(coins)
    
    def get_invested_coins(self):
        if self.invested_coins:
            return json.loads(self.invested_coins)
        return []
    
    def set_invested_coins(self, coins):
        self.invested_coins = json.dumps(coins)

class Coin(db.Model):
    id = db.Column(db.String(50), primary_key=True)  # CoinGecko coin ID
    name = db.Column(db.String(100), nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    current_price = db.Column(db.Float, default=0.0)
    price_change_24h = db.Column(db.Float, default=0.0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Coin {self.symbol}: ${self.current_price}>'

class UserCoinSelection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    coin_id = db.Column(db.String(50), db.ForeignKey('coin.id'), nullable=False)
    threshold_price = db.Column(db.Float, nullable=False)  # User's price threshold for this coin (e.g., $50000 for Bitcoin)
    is_invested = db.Column(db.Boolean, default=False)  # Whether user has invested in this coin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure unique combination of user and coin
    __table_args__ = (db.UniqueConstraint('user_id', 'coin_id', name='unique_user_coin'),)
    
    def __repr__(self):
        return f'<UserCoinSelection: User {self.user_id}, Coin {self.coin_id}, Price Threshold ${self.threshold_price}>'

class MarketData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    coin_id = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    change_24h = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class UserActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)  # login, logout, settings_change, etc.
    description = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Database Event Listeners for Auto-Update
@event.listens_for(User, 'after_insert')
@event.listens_for(User, 'after_update')
def user_changed(mapper, connection, target):
    """Automatically notify all connected clients when user data changes"""
    try:
        with app.app_context():
            # Emit to all connected clients
            socketio.emit('user_updated', {
                'user_id': target.id,
                'username': target.username,
                'is_admin': target.is_admin,
                'timestamp': datetime.utcnow().isoformat()
            }, namespace='/')
            
            # Log the activity
            activity = UserActivity(
                user_id=target.id,
                activity_type='user_updated',
                description=f'User {target.username} data updated'
            )
            db.session.add(activity)
            db.session.commit()
    except Exception as e:
        print(f"Error in user_changed listener: {e}")

@event.listens_for(UserCoinSelection, 'after_insert')
@event.listens_for(UserCoinSelection, 'after_update')
@event.listens_for(UserCoinSelection, 'after_delete')
def coin_selection_changed(mapper, connection, target):
    """Automatically notify when coin selections change"""
    try:
        with app.app_context():
            # Get user info
            user = User.query.get(target.user_id)
            if user:
                # Emit to the specific user's room
                socketio.emit('coin_selection_updated', {
                    'user_id': target.user_id,
                    'coin_id': target.coin_id,
                    'threshold_price': target.threshold_price,
                    'is_invested': target.is_invested,
                    'timestamp': datetime.utcnow().isoformat()
                }, room=f'user_{target.user_id}')
                
                # Log the activity
                activity = UserActivity(
                    user_id=target.user_id,
                    activity_type='coin_selection_changed',
                    description=f'Coin selection updated for {target.coin_id}'
                )
                db.session.add(activity)
                db.session.commit()
    except Exception as e:
        print(f"Error in coin_selection_changed listener: {e}")

@event.listens_for(Coin, 'after_update')
def coin_price_updated(mapper, connection, target):
    """Automatically notify when coin prices are updated"""
    try:
        with app.app_context():
            # Emit to all connected clients
            socketio.emit('coin_price_updated', {
                'coin_id': target.id,
                'name': target.name,
                'symbol': target.symbol,
                'current_price': target.current_price,
                'price_change_24h': target.price_change_24h,
                'last_updated': target.last_updated.isoformat() if target.last_updated else None,
                'timestamp': datetime.utcnow().isoformat()
            }, namespace='/')
    except Exception as e:
        print(f"Error in coin_price_updated listener: {e}")

# Forms
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Repeat Password', validators=[DataRequired()])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class SettingsForm(FlaskForm):
    threshold = FloatField('Threshold (%)', validators=[DataRequired(), NumberRange(min=0.1, max=100)])
    selected_coins = SelectMultipleField('Select Cryptocurrencies', choices=[])
    invested_coins = SelectMultipleField('Invested Coins (Blue LED)', choices=[])
    
    # Personalized output settings
    enable_led = BooleanField('Enable LED Output')
    enable_buzzer = BooleanField('Enable Buzzer Output')
    led_brightness = FloatField('LED Brightness (%)', validators=[NumberRange(min=0, max=100)])
    buzzer_volume = FloatField('Buzzer Volume (%)', validators=[NumberRange(min=0, max=100)])
    buzzer_duration = FloatField('Buzzer Duration (ms)', validators=[NumberRange(min=100, max=10000)])
    led_blink_speed = FloatField('LED Blink Speed (ms)', validators=[NumberRange(min=100, max=2000)])
    
    submit = SubmitField('Save Settings')

# Global variables for market monitoring
market_monitors = {}  # user_id -> MarketMonitor instance
available_coins = []

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class MarketMonitor:
    def __init__(self, user_id):
        self.user_id = user_id
        self.running = False
        self.thread = None
        self.user = User.query.get(user_id)
    
    def start_monitoring(self):
        if not self.running and self.user:
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
                print(f"Error in monitoring loop for user {self.user_id}: {e}")
                time.sleep(30)
    
    def _fetch_market_data(self):
        if not self.user:
            return
        
        # Get user's selected coins from new database structure
        user_selections = UserCoinSelection.query.filter_by(user_id=self.user.id).all()
        if not user_selections:
            return
        
        try:
            # Get all unique coin IDs from user selections
            coin_ids = list(set([selection.coin_id for selection in user_selections]))
            
            if not coin_ids:
                return
            
            # Fetch real-time market data from CoinGecko API
            coin_ids_str = ','.join(coin_ids)
            url = f"{COINGECKO_API_URL}/simple/price"
            params = {
                'ids': coin_ids_str,
                'vs_currencies': 'usd',
                'include_24hr_change': 'true',
                'include_last_updated_at': 'true'
            }
            
            print(f"Fetching real-time market data for coins: {coin_ids_str}")
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                market_data = response.json()
                print(f"✅ Real-time market data received: {market_data}")
                
                # Update Coin table with latest prices
                for coin_id, data in market_data.items():
                    coin = Coin.query.get(coin_id)
                    if coin:
                        coin.current_price = data['usd']
                        coin.price_change_24h = data.get('usd_24h_change', 0)
                        coin.last_updated = datetime.utcnow()
                    else:
                        # Create new coin entry
                        coin = Coin(
                            id=coin_id,
                            name=coin_id.title(),  # Fallback name
                            symbol=coin_id.upper()[:4],  # Fallback symbol
                            current_price=data['usd'],
                            price_change_24h=data.get('usd_24h_change', 0),
                            last_updated=datetime.utcnow()
                        )
                        db.session.add(coin)
                    
                    # Store historical market data
                    market_record = MarketData(
                        coin_id=coin_id,
                        price=data['usd'],
                        change_24h=data.get('usd_24h_change', 0)
                    )
                    db.session.add(market_record)
                
                db.session.commit()
                print(f"✅ Market data updated for user {self.user.username}: {len(market_data)} coins")
                
                # Trigger signal analysis with new data
                self._analyze_and_send_signals()
                
            else:
                print(f"❌ API request failed: {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Error fetching market data for user {self.user.username}: {e}")
            import traceback
            traceback.print_exc()
    
    def _analyze_and_send_signals(self):
        if not self.user:
            return
        
        # Get user's coin selections with individual thresholds
        user_selections = UserCoinSelection.query.filter_by(user_id=self.user.id).all()
        
        if not user_selections:
            return
        
        # ESP32 connection check disabled for testing
        # if not self.user.esp32_connected:
        #     print(f"ESP32 not connected for user {self.user.username} - skipping signal analysis")
        #     return
        
        signals = {}
        
        # Get latest market data for all coins
        latest_data = {}
        user_selections = UserCoinSelection.query.filter_by(user_id=self.user.id).all()
        selected_coins = [selection.coin_id for selection in user_selections]
        for coin in selected_coins:
            latest = MarketData.query.filter_by(coin_id=coin).order_by(MarketData.timestamp.desc()).first()
            if latest:
                latest_data[coin] = {
                    'price': latest.price,
                    'change_24h': latest.change_24h
                }
        
        # Analyze each user's coin selection with their personal price threshold
        for selection in user_selections:
            coin_id = selection.coin_id
            user_price_threshold = selection.threshold_price
            is_invested = selection.is_invested
            
            if coin_id not in latest_data:
                continue
                
            data = latest_data[coin_id]
            current_price = data['price']
            price_change_24h = data['change_24h']
            
            # Determine LED color based on user's price threshold
            if is_invested:
                led_color = 'blue'
                signal = 'invested'
            elif current_price > user_price_threshold:
                led_color = 'green'
                signal = 'up'
            elif current_price < user_price_threshold:
                led_color = 'red'
                signal = 'down'
            else:
                led_color = 'off'
                signal = 'neutral'
            
            signals[coin_id] = {
                'signal': signal,
                'led_color': led_color,
                'price': current_price,
                'change_24h': price_change_24h,
                'user_price_threshold': user_price_threshold,
                'is_invested': is_invested,
                'timestamp': datetime.utcnow().isoformat(),
                'user_settings': {
                    'enable_led': self.user.enable_led,
                    'enable_buzzer': self.user.enable_buzzer,
                    'led_brightness': self.user.led_brightness,
                    'buzzer_volume': self.user.buzzer_volume,
                    'buzzer_duration': self.user.buzzer_duration,
                    'led_blink_speed': self.user.led_blink_speed
                }
            }
        
        # Send signals to user's room
        socketio.emit('market_update', {
            'signals': signals,
            'user_id': self.user_id
        }, room=f'user_{self.user_id}')
        
        # Send to ESP32 if connected
        if self.user.esp32_connected:
            self._send_to_esp32(signals)
    
    def _send_to_esp32(self, signals):
        # Send market signals to ESP32
        esp32_message = {
            'type': 'market_update',
            'signals': signals,
            'user_settings': {
                'enable_led': self.user.enable_led,
                'enable_buzzer': self.user.enable_buzzer,
                'led_brightness': self.user.led_brightness,
                'buzzer_volume': self.user.buzzer_volume,
                'buzzer_duration': self.user.buzzer_duration,
                'led_blink_speed': self.user.led_blink_speed
            }
        }
        
        # Send to ESP32 via WebSocket
        socketio.emit('esp32_command', esp32_message, room=f'user_{self.user_id}')
        print(f"Sending to ESP32 for user {self.user_id}: {esp32_message}")
    
    def send_personalized_settings(self):
        """Send current personalized settings to ESP32"""
        if self.user.esp32_connected:
            settings_message = {
                'type': 'user_settings',
                'user_settings': {
                    'enable_led': self.user.enable_led,
                    'enable_buzzer': self.user.enable_buzzer,
                    'led_brightness': self.user.led_brightness,
                    'buzzer_volume': self.user.buzzer_volume,
                    'buzzer_duration': self.user.buzzer_duration,
                    'led_blink_speed': self.user.led_blink_speed
                }
            }
            
            socketio.emit('esp32_command', settings_message, room=f'user_{self.user_id}')
            print(f"Sent personalized settings to ESP32 for user {self.user_id}: {settings_message}")

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin'))
        return redirect(url_for('dashboard'))
    return render_template('welcome.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin'))
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        # Check if fields are empty
        if not username or not password:
            flash('All fields are required', 'error')
            return render_template('welcome.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Log login activity
            activity = UserActivity(
                user_id=user.id,
                activity_type='login',
                description=f'User {user.username} logged in',
                ip_address=request.remote_addr
            )
            db.session.add(activity)
            db.session.commit()
            
            # Redirect based on user type
            if user.is_admin:
                flash(f'Welcome back, Admin {user.username}!', 'success')
                return redirect(url_for('admin'))
            else:
                flash(f'Welcome back, {user.username}!', 'success')
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('welcome.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for('admin'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data) and user.is_admin:
            login_user(user, remember=form.remember_me.data)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Log admin login activity
            activity = UserActivity(
                user_id=user.id,
                activity_type='admin_login',
                description=f'Admin {user.username} logged in',
                ip_address=request.remote_addr
            )
            db.session.add(activity)
            db.session.commit()
            
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Invalid admin credentials', 'error')
    
    return render_template('admin_login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin'))
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        is_admin = request.form.get('is_admin') == 'on'
        
        # Validation
        if not username or not email or not password:
            flash('All fields are required', 'error')
            return render_template('welcome.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('welcome.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('welcome.html')
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('welcome.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('welcome.html')
        
        # Create new user
        user = User(
            username=username,
            email=email,
            is_admin=is_admin,
            enable_led=True,
            enable_buzzer=True,
            led_brightness=80,
            buzzer_volume=70,
            buzzer_duration=1000,
            led_blink_speed=500
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Log registration activity
        activity = UserActivity(
            user_id=user.id,
            activity_type='register',
            description=f'User {user.username} registered',
            ip_address=request.remote_addr
        )
        db.session.add(activity)
        db.session.commit()
        
        flash(f'Account created successfully! Welcome, {user.username}!', 'success')
        login_user(user)
        
        # Redirect based on user type
        if user.is_admin:
            return redirect(url_for('admin'))
        else:
            return redirect(url_for('dashboard'))
    
    return render_template('welcome.html')

@app.route('/debug')
def debug():
    """Debug route to check current user status"""
    return jsonify({
        'is_authenticated': current_user.is_authenticated,
        'user_id': current_user.id if current_user.is_authenticated else None,
        'username': current_user.username if current_user.is_authenticated else None,
        'is_admin': current_user.is_admin if current_user.is_authenticated else None,
        'session_keys': list(session.keys())
    })

@app.route('/clear-session')
def clear_session():
    """Clear all session data - for debugging"""
    session.clear()
    logout_user()
    flash('Session cleared successfully', 'info')
    return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    # Log activity
    activity = UserActivity(
        user_id=current_user.id,
        activity_type='logout',
        description=f'User {current_user.username} logged out',
        ip_address=request.remote_addr
    )
    db.session.add(activity)
    db.session.commit()
    
    # Stop monitoring
    if current_user.id in market_monitors:
        market_monitors[current_user.id].stop_monitoring()
        del market_monitors[current_user.id]
    
    username = current_user.username
    is_admin = current_user.is_admin
    
    logout_user()
    
    if is_admin:
        flash(f'Admin {username} has been logged out successfully.', 'info')
        return redirect(url_for('index'))
    else:
        flash(f'User {username} has been logged out successfully.', 'info')
        return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        try:
            # Get form data
            selected_coins = request.form.getlist('selected_coins')
            price_thresholds = {}
            invested_coins = {}
            
            # Process each selected coin
            for coin_id in selected_coins:
                threshold_key = f'threshold_{coin_id}'
                invested_key = f'invested_{coin_id}'
                
                if threshold_key in request.form:
                    price_thresholds[coin_id] = float(request.form[threshold_key])
                
                if invested_key in request.form:
                    invested_coins[coin_id] = True
                else:
                    invested_coins[coin_id] = False
            
            # Clear existing selections
            UserCoinSelection.query.filter_by(user_id=current_user.id).delete()
            
            # Add new selections with price thresholds
            for coin_id in selected_coins:
                # Check if coin exists in database, if not create it
                coin = Coin.query.get(coin_id)
                if not coin:
                    # Fetch coin data from API
                    try:
                        url = f"{COINGECKO_API_URL}/coins/{coin_id}"
                        response = requests.get(url, timeout=10)
                        if response.status_code == 200:
                            coin_data = response.json()
                            coin = Coin(
                                id=coin_data['id'],
                                name=coin_data['name'],
                                symbol=coin_data['symbol'].upper(),
                                current_price=coin_data['market_data']['current_price']['usd'],
                                price_change_24h=coin_data['market_data']['price_change_percentage_24h']
                            )
                            db.session.add(coin)
                    except Exception as e:
                        print(f"Error fetching coin data for {coin_id}: {e}")
                        continue
                
                # Create user coin selection with price threshold
                user_selection = UserCoinSelection(
                    user_id=current_user.id,
                    coin_id=coin_id,
                    threshold_price=price_thresholds.get(coin_id, 50000.0),  # Default $50,000
                    is_invested=invested_coins.get(coin_id, False)
                )
                db.session.add(user_selection)
            
            # Update personalized output settings
            current_user.enable_led = request.form.get('enable_led') == 'on'
            current_user.enable_buzzer = request.form.get('enable_buzzer') == 'on'
            current_user.led_brightness = int(request.form.get('led_brightness', 80))
            current_user.buzzer_volume = int(request.form.get('buzzer_volume', 70))
            current_user.buzzer_duration = int(request.form.get('buzzer_duration', 1000))
            current_user.led_blink_speed = int(request.form.get('led_blink_speed', 500))
            
            db.session.commit()
            
            # Log activity
            activity = UserActivity(
                user_id=current_user.id,
                activity_type='settings_update',
                description=f'User {current_user.username} updated settings',
                ip_address=request.remote_addr
            )
            db.session.add(activity)
            db.session.commit()
            
            # Start/restart monitoring
            if current_user.id in market_monitors:
                market_monitors[current_user.id].stop_monitoring()
            
            if selected_coins:
                market_monitors[current_user.id] = MarketMonitor(current_user.id)
                market_monitors[current_user.id].start_monitoring()
            
            flash('Settings saved successfully!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            print(f"Error saving settings: {e}")
            flash('Error saving settings. Please try again.', 'error')
    
    return render_template('settings_new.html')

@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    activities = UserActivity.query.order_by(UserActivity.timestamp.desc()).limit(50).all()
    market_data = MarketData.query.order_by(MarketData.timestamp.desc()).limit(20).all()
    
    return render_template('admin.html', users=users, activities=activities, market_data=market_data)

# API Routes
@app.route('/api/coins')
def get_available_coins():
    global available_coins
    try:
        url = f"{COINGECKO_API_URL}/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 100,  # Increased to get more coins
            'page': 1,
            'sparkline': 'false'
        }
        
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            coins = response.json()
            available_coins = [{
                'id': coin['id'],
                'name': coin['name'],
                'symbol': coin['symbol'].upper(),
                'current_price': coin['current_price'],
                'market_cap': coin.get('market_cap', 0),
                'price_change_24h': coin.get('price_change_percentage_24h', 0),
                'volume_24h': coin.get('total_volume', 0)
            } for coin in coins]
            print(f"✅ Fetched {len(available_coins)} cryptocurrencies from CoinGecko API")
            return jsonify(available_coins)
        else:
            print(f"❌ API request failed: {response.status_code}")
            return jsonify([])
    except Exception as e:
        print(f"❌ Error fetching coins: {e}")
        return jsonify([])

@app.route('/api/market-data/<coin_id>')
def get_coin_market_data(coin_id):
    """Get real-time market data for a specific coin"""
    try:
        url = f"{COINGECKO_API_URL}/coins/{coin_id}"
        params = {
            'localization': 'false',
            'tickers': 'false',
            'market_data': 'true',
            'community_data': 'false',
            'developer_data': 'false',
            'sparkline': 'false'
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            market_data = {
                'id': data['id'],
                'name': data['name'],
                'symbol': data['symbol'].upper(),
                'current_price': data['market_data']['current_price']['usd'],
                'price_change_24h': data['market_data']['price_change_percentage_24h'],
                'market_cap': data['market_data']['market_cap']['usd'],
                'volume_24h': data['market_data']['total_volume']['usd'],
                'last_updated': data['last_updated']
            }
            return jsonify(market_data)
        else:
            return jsonify({'error': 'Coin not found'}), 404
    except Exception as e:
        print(f"❌ Error fetching market data for {coin_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/real-time-data')
@login_required
def get_real_time_data():
    """Get real-time market data for user's selected coins"""
    try:
        user_selections = UserCoinSelection.query.filter_by(user_id=current_user.id).all()
        if not user_selections:
            return jsonify({'message': 'No coins selected'})
        
        coin_ids = [selection.coin_id for selection in user_selections]
        coin_ids_str = ','.join(coin_ids)
        
        url = f"{COINGECKO_API_URL}/simple/price"
        params = {
            'ids': coin_ids_str,
            'vs_currencies': 'usd',
            'include_24hr_change': 'true',
            'include_last_updated_at': 'true'
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            market_data = response.json()
            
            # Add user-specific threshold information
            result = {}
            for selection in user_selections:
                coin_id = selection.coin_id
                if coin_id in market_data:
                    result[coin_id] = {
                        **market_data[coin_id],
                        'user_threshold': selection.threshold_price,
                        'is_invested': selection.is_invested,
                        'coin_name': Coin.query.get(coin_id).name if Coin.query.get(coin_id) else coin_id
                    }
            
            return jsonify(result)
        elif response.status_code == 429:
            return jsonify({'error': 'API rate limit exceeded. Please try again later.'}), 429
        else:
            print(f"❌ API request failed: {response.status_code}")
            return jsonify({'error': f'API request failed: {response.status_code}'}), response.status_code
            
    except Exception as e:
        print(f"❌ Error fetching real-time data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chart-data/<coin_id>')
@login_required
def get_chart_data(coin_id):
    """Get historical data for candlestick charts"""
    try:
        # Check if user has selected this coin
        user_selection = UserCoinSelection.query.filter_by(
            user_id=current_user.id, 
            coin_id=coin_id
        ).first()
        
        if not user_selection:
            return jsonify({'error': 'Coin not selected by user'}), 403
        
        # Get timeframe from query parameter (default: 1 day)
        timeframe = request.args.get('timeframe', '1d')
        
        # Map timeframes to CoinGecko parameters
        timeframe_map = {
            '1h': {'days': 1, 'interval': 'hourly'},
            '4h': {'days': 1, 'interval': 'hourly'},
            '1d': {'days': 1, 'interval': 'hourly'},
            '7d': {'days': 7, 'interval': 'daily'},
            '30d': {'days': 30, 'interval': 'daily'},
            '90d': {'days': 90, 'interval': 'daily'}
        }
        
        if timeframe not in timeframe_map:
            timeframe = '1d'
        
        params = timeframe_map[timeframe]
        
        # Fetch historical data from CoinGecko
        url = f"{COINGECKO_API_URL}/coins/{coin_id}/market_chart"
        api_params = {
            'vs_currency': 'usd',
            'days': params['days'],
            'interval': params['interval']
        }
        
        response = requests.get(url, params=api_params, timeout=15)
        print(f"Chart API call: {url} with params {api_params}")
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Chart data received: {len(data.get('prices', []))} price points")
            
            # Process data for candlestick chart
            prices = data.get('prices', [])
            volumes = data.get('total_volumes', [])
            
            if not prices:
                print("No price data received from API")
                return jsonify({'error': 'No price data available'}), 500
            
            # Convert to candlestick format
            candlesticks = []
            for i in range(len(prices)):
                timestamp = prices[i][0]
                price = prices[i][1]
                volume = volumes[i][1] if i < len(volumes) else 0
                
                # For simplicity, we'll use the same price for OHLC
                # In a real implementation, you'd need minute-level data
                candlestick = {
                    'timestamp': timestamp,
                    'open': price,
                    'high': price * 1.02,  # Simulated high
                    'low': price * 0.98,   # Simulated low
                    'close': price,
                    'volume': volume
                }
                candlesticks.append(candlestick)
            
            # Get current coin info
            coin = Coin.query.get(coin_id)
            coin_info = {
                'id': coin_id,
                'name': coin.name if coin else coin_id,
                'symbol': coin.symbol if coin else coin_id.upper(),
                'current_price': candlesticks[-1]['close'] if candlesticks else 0,
                'threshold_price': user_selection.threshold_price,
                'is_invested': user_selection.is_invested
            }
            
            return jsonify({
                'coin_info': coin_info,
                'candlesticks': candlesticks,
                'timeframe': timeframe
            })
        else:
            print(f"Chart API failed with status {response.status_code}: {response.text}")
            return jsonify({'error': f'Failed to fetch chart data: {response.status_code}'}), 500
            
    except Exception as e:
        print(f"❌ Error fetching chart data: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/update_esp32_settings', methods=['POST'])
@login_required
def update_esp32_settings():
    """Update ESP32 settings in real-time"""
    try:
        data = request.json
        
        # Update user settings in database
        current_user.enable_led = data.get('enable_led', current_user.enable_led)
        current_user.enable_buzzer = data.get('enable_buzzer', current_user.enable_buzzer)
        current_user.led_brightness = float(data.get('led_brightness', current_user.led_brightness))
        current_user.buzzer_volume = float(data.get('buzzer_volume', current_user.buzzer_volume))
        current_user.buzzer_duration = float(data.get('buzzer_duration', current_user.buzzer_duration))
        current_user.led_blink_speed = float(data.get('led_blink_speed', current_user.led_blink_speed))
        
        db.session.commit()
        
        # Send settings to ESP32 if connected (disabled for testing)
        # if current_user.esp32_connected and current_user.id in market_monitors:
        #     market_monitors[current_user.id].send_personalized_settings()
        #     print(f"Real-time settings update sent to ESP32 for user {current_user.username}")
        
        return jsonify({'success': True, 'message': 'Settings updated and sent to ESP32'})
        
    except Exception as e:
        print(f"Error updating ESP32 settings: {e}")
        return jsonify({'success': False, 'error': str(e)})

# Auto-Save API Endpoints
@app.route('/api/auto-save-settings', methods=['POST'])
@login_required
def auto_save_settings():
    """Auto-save user settings as they type/change"""
    try:
        data = request.json
        setting_type = data.get('type')
        value = data.get('value')
        
        if setting_type == 'led_brightness':
            current_user.led_brightness = float(value)
        elif setting_type == 'buzzer_volume':
            current_user.buzzer_volume = float(value)
        elif setting_type == 'buzzer_duration':
            current_user.buzzer_duration = float(value)
        elif setting_type == 'led_blink_speed':
            current_user.led_blink_speed = float(value)
        elif setting_type == 'enable_led':
            current_user.enable_led = bool(value)
        elif setting_type == 'enable_buzzer':
            current_user.enable_buzzer = bool(value)
        
        db.session.commit()
        
        # Log the auto-save activity
        activity = UserActivity(
            user_id=current_user.id,
            activity_type='auto_save',
            description=f'Auto-saved {setting_type} = {value}'
        )
        db.session.add(activity)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'{setting_type} auto-saved'})
        
    except Exception as e:
        print(f"Error in auto-save: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/auto-save-coin-selection', methods=['POST'])
@login_required
def auto_save_coin_selection():
    """Auto-save coin selections as user makes changes"""
    try:
        data = request.json
        coin_id = data.get('coin_id')
        threshold_price = float(data.get('threshold_price', 0))
        is_invested = bool(data.get('is_invested', False))
        action = data.get('action', 'update')  # add, update, remove
        
        if action == 'add':
            # Add new coin selection
            existing = UserCoinSelection.query.filter_by(
                user_id=current_user.id, 
                coin_id=coin_id
            ).first()
            
            if not existing:
                selection = UserCoinSelection(
                    user_id=current_user.id,
                    coin_id=coin_id,
                    threshold_price=threshold_price,
                    is_invested=is_invested
                )
                db.session.add(selection)
                db.session.commit()
                
                # Log activity
                activity = UserActivity(
                    user_id=current_user.id,
                    activity_type='coin_added',
                    description=f'Added {coin_id} with threshold ${threshold_price}'
                )
                db.session.add(activity)
                db.session.commit()
                
        elif action == 'update':
            # Update existing selection
            selection = UserCoinSelection.query.filter_by(
                user_id=current_user.id,
                coin_id=coin_id
            ).first()
            
            if selection:
                selection.threshold_price = threshold_price
                selection.is_invested = is_invested
                db.session.commit()
                
                # Log activity
                activity = UserActivity(
                    user_id=current_user.id,
                    activity_type='coin_updated',
                    description=f'Updated {coin_id} threshold to ${threshold_price}'
                )
                db.session.add(activity)
                db.session.commit()
                
        elif action == 'remove':
            # Remove selection
            selection = UserCoinSelection.query.filter_by(
                user_id=current_user.id,
                coin_id=coin_id
            ).first()
            
            if selection:
                db.session.delete(selection)
                db.session.commit()
                
                # Log activity
                activity = UserActivity(
                    user_id=current_user.id,
                    activity_type='coin_removed',
                    description=f'Removed {coin_id} from selections'
                )
                db.session.add(activity)
                db.session.commit()
        
        return jsonify({'success': True, 'message': f'Coin selection {action}ed'})
        
    except Exception as e:
        print(f"Error in auto-save coin selection: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/get-user-activity', methods=['GET'])
@login_required
def get_user_activity():
    """Get recent user activity for real-time updates"""
    try:
        # Get last 10 activities for current user
        activities = UserActivity.query.filter_by(user_id=current_user.id)\
            .order_by(UserActivity.timestamp.desc())\
            .limit(10).all()
        
        activity_data = []
        for activity in activities:
            activity_data.append({
                'id': activity.id,
                'activity_type': activity.activity_type,
                'description': activity.description,
                'timestamp': activity.timestamp.isoformat()
            })
        
        return jsonify({'activities': activity_data})
        
    except Exception as e:
        print(f"Error getting user activity: {e}")
        return jsonify({'error': str(e)})

@app.route('/api/auto-save-dashboard', methods=['POST'])
@login_required
def auto_save_dashboard():
    """Auto-save dashboard interactions and state"""
    try:
        # Check if request has JSON data
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Content-Type must be application/json'}), 400
        
        data = request.get_json()
        
        # Validate required fields
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Ensure we have at least an interaction type
        interaction = data.get('interaction', 'unknown')
        timestamp = data.get('timestamp', datetime.utcnow().isoformat())
        
        # Validate interaction is a string
        if not isinstance(interaction, str):
            interaction = str(interaction)
        
        # Log the dashboard interaction
        activity = UserActivity(
            user_id=current_user.id,
            activity_type='dashboard_interaction',
            description=f"Dashboard: {interaction} at {timestamp}",
            ip_address=request.remote_addr
        )
        db.session.add(activity)
        db.session.commit()
        
        print(f"Dashboard auto-save successful for user {current_user.username}: {interaction}")
        return jsonify({'success': True, 'message': 'Dashboard data auto-saved'})
        
    except Exception as e:
        print(f"Error in dashboard auto-save: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Create a separate API route without CSRF protection for auto-save
@app.route('/api/auto-save-dashboard-no-csrf', methods=['POST'])
def auto_save_dashboard_no_csrf():
    """Auto-save dashboard interactions and state (no CSRF protection)"""
    try:
        # Check if request has JSON data
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Content-Type must be application/json'}), 400
        
        data = request.get_json()
        
        # Validate required fields
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Ensure we have at least an interaction type
        interaction = data.get('interaction', 'unknown')
        timestamp = data.get('timestamp', datetime.utcnow().isoformat())
        user_id = data.get('user_id', None)
        
        # Validate interaction is a string
        if not isinstance(interaction, str):
            interaction = str(interaction)
        
        # If user_id is provided, log the activity
        if user_id:
            try:
                activity = UserActivity(
                    user_id=user_id,
                    activity_type='dashboard_interaction',
                    description=f"Dashboard: {interaction} at {timestamp}"
                )
                db.session.add(activity)
                db.session.commit()
                print(f"Dashboard auto-save successful for user {user_id}: {interaction}")
            except Exception as db_error:
                print(f"Database error in auto-save: {db_error}")
                # Don't fail the request for database errors
        
        return jsonify({'success': True, 'message': 'Dashboard data auto-saved'})
        
    except Exception as e:
        print(f"Error in dashboard auto-save: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Exempt the no-csrf endpoint from CSRF protection
csrf.exempt(auto_save_dashboard_no_csrf)

# WebSocket Events
@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        join_room(f'user_{current_user.id}')
        emit('connected', {'status': 'Connected to server', 'user_id': current_user.id})
        print(f'User {current_user.username} connected')

@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        leave_room(f'user_{current_user.id}')
        print(f'User {current_user.username} disconnected')

@socketio.on('esp32_connect')
def handle_esp32_connect():
    if current_user.is_authenticated:
        current_user.esp32_connected = True
        current_user.esp32_last_seen = datetime.utcnow()
        db.session.commit()
        
        emit('esp32_status', {'connected': True}, room=f'user_{current_user.id}')
        print(f'ESP32 connected for user {current_user.username}')

@socketio.on('esp32_disconnect')
def handle_esp32_disconnect():
    if current_user.is_authenticated:
        current_user.esp32_connected = False
        db.session.commit()
        
        emit('esp32_status', {'connected': False}, room=f'user_{current_user.id}')
        print(f'ESP32 disconnected for user {current_user.username}')

@socketio.on('check_esp32_connection')
def handle_check_esp32_connection():
    if current_user.is_authenticated:
        # Send current ESP32 status
        emit('esp32_status', {'connected': current_user.esp32_connected}, room=f'user_{current_user.id}')
        print(f'ESP32 connection check requested by user {current_user.username}')

# Real-time Auto-Save WebSocket Handlers
@socketio.on('auto_save_request')
def handle_auto_save_request(data):
    """Handle real-time auto-save requests from frontend"""
    if current_user.is_authenticated:
        try:
            setting_type = data.get('type')
            value = data.get('value')
            
            # Update user settings
            if setting_type == 'led_brightness':
                current_user.led_brightness = float(value)
            elif setting_type == 'buzzer_volume':
                current_user.buzzer_volume = float(value)
            elif setting_type == 'buzzer_duration':
                current_user.buzzer_duration = float(value)
            elif setting_type == 'led_blink_speed':
                current_user.led_blink_speed = float(value)
            elif setting_type == 'enable_led':
                current_user.enable_led = bool(value)
            elif setting_type == 'enable_buzzer':
                current_user.enable_buzzer = bool(value)
            
            db.session.commit()
            
            # Emit confirmation back to user
            emit('auto_save_confirmed', {
                'type': setting_type,
                'value': value,
                'timestamp': datetime.utcnow().isoformat()
            }, room=f'user_{current_user.id}')
            
            print(f"Auto-saved {setting_type} = {value} for user {current_user.username}")
            
        except Exception as e:
            emit('auto_save_error', {'error': str(e)}, room=f'user_{current_user.id}')
            print(f"Auto-save error for user {current_user.username}: {e}")

@socketio.on('coin_selection_change')
def handle_coin_selection_change(data):
    """Handle real-time coin selection changes"""
    if current_user.is_authenticated:
        try:
            coin_id = data.get('coin_id')
            threshold_price = float(data.get('threshold_price', 0))
            is_invested = bool(data.get('is_invested', False))
            action = data.get('action', 'update')
            
            if action == 'add':
                # Add new coin selection
                existing = UserCoinSelection.query.filter_by(
                    user_id=current_user.id, 
                    coin_id=coin_id
                ).first()
                
                if not existing:
                    selection = UserCoinSelection(
                        user_id=current_user.id,
                        coin_id=coin_id,
                        threshold_price=threshold_price,
                        is_invested=is_invested
                    )
                    db.session.add(selection)
                    db.session.commit()
                    
                    emit('coin_selection_added', {
                        'coin_id': coin_id,
                        'threshold_price': threshold_price,
                        'is_invested': is_invested,
                        'timestamp': datetime.utcnow().isoformat()
                    }, room=f'user_{current_user.id}')
                    
            elif action == 'update':
                # Update existing selection
                selection = UserCoinSelection.query.filter_by(
                    user_id=current_user.id,
                    coin_id=coin_id
                ).first()
                
                if selection:
                    selection.threshold_price = threshold_price
                    selection.is_invested = is_invested
                    db.session.commit()
                    
                    emit('coin_selection_updated', {
                        'coin_id': coin_id,
                        'threshold_price': threshold_price,
                        'is_invested': is_invested,
                        'timestamp': datetime.utcnow().isoformat()
                    }, room=f'user_{current_user.id}')
                    
            elif action == 'remove':
                # Remove selection
                selection = UserCoinSelection.query.filter_by(
                    user_id=current_user.id,
                    coin_id=coin_id
                ).first()
                
                if selection:
                    db.session.delete(selection)
                    db.session.commit()
                    
                    emit('coin_selection_removed', {
                        'coin_id': coin_id,
                        'timestamp': datetime.utcnow().isoformat()
                    }, room=f'user_{current_user.id}')
            
            print(f"Coin selection {action} for {coin_id} by user {current_user.username}")
            
        except Exception as e:
            emit('coin_selection_error', {'error': str(e)}, room=f'user_{current_user.id}')
            print(f"Coin selection error for user {current_user.username}: {e}")

@socketio.on('request_live_updates')
def handle_request_live_updates():
    """Handle requests for live database updates"""
    if current_user.is_authenticated:
        # Send current user's data
        emit('live_data_update', {
            'user_id': current_user.id,
            'username': current_user.username,
            'esp32_connected': current_user.esp32_connected,
            'led_brightness': current_user.led_brightness,
            'buzzer_volume': current_user.buzzer_volume,
            'timestamp': datetime.utcnow().isoformat()
        }, room=f'user_{current_user.id}')
        
        # Send user's coin selections
        selections = UserCoinSelection.query.filter_by(user_id=current_user.id).all()
        for selection in selections:
            emit('live_coin_data', {
                'coin_id': selection.coin_id,
                'threshold_price': selection.threshold_price,
                'is_invested': selection.is_invested,
                'timestamp': datetime.utcnow().isoformat()
            }, room=f'user_{current_user.id}')
        
        print(f"Live updates requested by user {current_user.username}")

@socketio.on('dashboard_data_update')
def handle_dashboard_data_update(data):
    """Handle dashboard data updates from frontend"""
    if current_user.is_authenticated:
        try:
            # Validate data
            if not data or not isinstance(data, dict):
                emit('dashboard_update_error', {'error': 'Invalid data format'}, room=f'user_{current_user.id}')
                return
            
            # Extract and validate interaction
            interaction = data.get('interaction', 'unknown')
            if not isinstance(interaction, str):
                interaction = str(interaction)
            
            # Log the dashboard update
            activity = UserActivity(
                user_id=current_user.id,
                activity_type='dashboard_update',
                description=f"Dashboard updated: {interaction}",
                ip_address=request.remote_addr
            )
            db.session.add(activity)
            db.session.commit()
            
            # Emit confirmation back to user
            emit('dashboard_update_confirmed', {
                'interaction': interaction,
                'timestamp': datetime.utcnow().isoformat()
            }, room=f'user_{current_user.id}')
            
            print(f"Dashboard data updated for user {current_user.username}: {interaction}")
            
        except Exception as e:
            emit('dashboard_update_error', {'error': str(e)}, room=f'user_{current_user.id}')
            print(f"Dashboard update error for user {current_user.username}: {e}")

# Initialize database and create admin user
def init_db():
    with app.app_context():
        db.create_all()
        
        # Create admin user if it doesn't exist
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@iotstockmonitor.com',
                is_admin=True
            )
            admin.set_password('admin123')  # Change this in production!
            db.session.add(admin)
            db.session.commit()
            print("Admin user created: username='admin', password='admin123'")

if __name__ == '__main__':
    init_db()
    print("Starting Multi-User IoT Stock Monitor Application...")
    print("Access the application at: http://localhost:5000")
    print("Admin login: username='admin', password='admin123'")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
