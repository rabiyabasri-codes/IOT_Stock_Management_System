# 🚀 Multi-User IoT Stock Monitor

A comprehensive, multi-user cryptocurrency monitoring platform with ESP32 hardware integration, featuring real-time market data, user authentication, and admin management.

## ✨ Features

### 🔐 **Multi-User System**
- **User Registration & Authentication** - Secure login system with password hashing
- **Admin Panel** - Complete user management and system monitoring
- **User-Specific Settings** - Each user has their own monitoring configuration
- **Session Management** - Secure user sessions with remember me functionality

### 📊 **Real-Time Monitoring**
- **Live Market Data** - Real-time cryptocurrency prices from CoinGecko API
- **Custom Thresholds** - Set personalized price change thresholds
- **Multi-Coin Support** - Monitor multiple cryptocurrencies simultaneously
- **Investment Tracking** - Mark coins you've invested in for special alerts

### 🎨 **Modern UI/UX**
- **Responsive Design** - Beautiful, modern interface that works on all devices
- **Glass Morphism Effects** - Contemporary design with backdrop blur effects
- **Real-Time Updates** - Live data updates without page refresh
- **Interactive Dashboard** - Comprehensive analytics and status monitoring

### 🔧 **Hardware Integration**
- **ESP32 Support** - Connect multiple ESP32 devices
- **LED Control** - Red/Green/Blue LED indicators based on market movements
- **Buzzer Alerts** - Audio notifications for significant price changes
- **WebSocket Communication** - Real-time hardware control

### 🛡️ **Admin Features**
- **User Management** - View, edit, and manage all users
- **Activity Monitoring** - Track user activities and system events
- **Market Data Analytics** - View historical market data
- **System Status** - Monitor server health and API connections

## 🏗️ **System Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser   │    │   Flask Server  │    │   ESP32 Device  │
│                 │    │                 │    │                 │
│ • Login/Register│◄──►│ • User Auth     │◄──►│ • LED Control   │
│ • Dashboard     │    │ • Market Data   │    │ • Buzzer        │
│ • Settings      │    │ • WebSocket     │    │ • WiFi Connect  │
│ • Admin Panel   │    │ • Database      │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │  CoinGecko API  │
                       │                 │
                       │ • Live Prices   │
                       │ • 24h Changes   │
                       │ • Market Data   │
                       └─────────────────┘
```

## 🚀 **Quick Start**

### 1. **Installation**
```bash
# Clone or download the project
cd CNproj

# Install dependencies
pip install -r requirements.txt

# Start the application
python app_multi_user.py
```

### 2. **Access the Application**
- **URL**: http://localhost:5000
- **Admin Login**: 
  - Username: `admin`
  - Password: `admin123`

### 3. **Create Your Account**
1. Click "Register" on the login page
2. Fill in your details
3. Log in with your new account
4. Configure your monitoring settings

## 👥 **User Roles**

### **Regular Users**
- Create and manage their own monitoring settings
- View real-time market data for their selected coins
- Control their ESP32 hardware
- Access personal dashboard and analytics

### **Admin Users**
- All regular user features
- Access to admin panel
- User management (view, edit, delete users)
- System monitoring and analytics
- Activity logs and market data history

## 🎛️ **LED Logic System**

### **Red LED** 🔴
- **Trigger**: Price drops below your threshold
- **Example**: If threshold is 5% and Bitcoin drops 7%, red LED activates

### **Green LED** 🟢
- **Trigger**: Price rises above your threshold
- **Example**: If threshold is 5% and Bitcoin rises 8%, green LED activates

### **Blue LED** 🔵
- **Trigger**: You have marked this coin as "invested"
- **Behavior**: Always on for invested coins, regardless of price movement

### **No LED** ⚫
- **Trigger**: Price change is within your threshold range
- **Example**: If threshold is 5% and Bitcoin changes only 2%, no LED activates

## 🔧 **ESP32 Setup**

### **Hardware Requirements**
- ESP32 Development Board
- 3x LEDs (Red, Green, Blue) with 220Ω resistors
- 1x Buzzer (5V)
- Breadboard and jumper wires

### **Wiring Diagram**
```
ESP32 Pin    →    Component
GPIO 2       →    Red LED + 220Ω resistor to GND
GPIO 4       →    Green LED + 220Ω resistor to GND  
GPIO 5       →    Blue LED + 220Ω resistor to GND
GPIO 18      →    Buzzer positive terminal
GND          →    Buzzer negative terminal + LED cathodes
```

### **Code Configuration**
1. Open `esp32_code.ino` in Arduino IDE
2. Update WiFi credentials:
   ```cpp
   const char* ssid = "YOUR_WIFI_SSID";
   const char* password = "YOUR_WIFI_PASSWORD";
   ```
3. Update server IP (use your computer's IP):
   ```cpp
   const char* server_host = "192.168.1.100";  // Your computer's IP
   ```
4. Upload to ESP32

## 📱 **Web Interface Guide**

### **Dashboard**
- **Stats Cards**: Overview of your monitoring setup
- **Quick Actions**: Fast access to common tasks
- **Real-time Data**: Live market data with LED status
- **System Status**: Connection status and hardware info

### **Settings**
- **Threshold Configuration**: Set your price change threshold
- **Coin Selection**: Choose cryptocurrencies to monitor
- **Investment Tracking**: Mark coins you've invested in
- **ESP32 Configuration**: Hardware setup and connection info

### **Admin Panel**
- **User Management**: View and manage all users
- **Activity Logs**: Track system activities
- **Market Analytics**: Historical market data
- **System Status**: Server health and API status

## 🗄️ **Database Schema**

### **Users Table**
- `id`: Primary key
- `username`: Unique username
- `email`: Unique email address
- `password_hash`: Encrypted password
- `is_admin`: Admin privileges flag
- `threshold`: Price change threshold
- `selected_coins`: JSON array of monitored coins
- `invested_coins`: JSON array of invested coins
- `esp32_connected`: Hardware connection status

### **Market Data Table**
- `id`: Primary key
- `coin_id`: Cryptocurrency identifier
- `price`: Current price in USD
- `change_24h`: 24-hour price change percentage
- `timestamp`: Data collection time

### **User Activity Table**
- `id`: Primary key
- `user_id`: Foreign key to users table
- `activity_type`: Type of activity (login, logout, etc.)
- `description`: Activity description
- `timestamp`: Activity time
- `ip_address`: User's IP address

## 🔒 **Security Features**

- **Password Hashing**: Bcrypt encryption for all passwords
- **Session Management**: Secure user sessions
- **CSRF Protection**: Cross-site request forgery protection
- **Input Validation**: All user inputs are validated
- **SQL Injection Protection**: SQLAlchemy ORM prevents SQL injection
- **Admin Access Control**: Role-based access control

## 🌐 **API Endpoints**

### **Authentication**
- `GET /login` - Login page
- `POST /login` - Process login
- `GET /register` - Registration page
- `POST /register` - Process registration
- `GET /logout` - Logout user

### **User Interface**
- `GET /` - Redirect to dashboard
- `GET /dashboard` - User dashboard
- `GET /settings` - User settings
- `POST /settings` - Update settings

### **Admin**
- `GET /admin` - Admin panel
- Admin-only access to user management

### **API**
- `GET /api/coins` - Get available cryptocurrencies
- WebSocket events for real-time communication

## 🚀 **Deployment Options**

### **Development**
```bash
python app_multi_user.py
```

### **Production (Recommended)**
```bash
# Using Gunicorn
pip install gunicorn
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 app_multi_user:app

# Using uWSGI
pip install uwsgi
uwsgi --http :5000 --module app_multi_user:app --processes 4 --threads 2
```

### **Docker Deployment**
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app_multi_user.py"]
```

## 📊 **Monitoring & Analytics**

### **User Analytics**
- Login/logout tracking
- Settings change history
- ESP32 connection status
- Market data access patterns

### **System Analytics**
- API response times
- Database performance
- WebSocket connections
- Error rates and logs

### **Market Analytics**
- Historical price data
- Price change patterns
- Alert frequency
- User engagement metrics

## 🔧 **Configuration**

### **Environment Variables**
```bash
# Flask Configuration
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///iot_stock_monitor.db

# API Configuration
COINGECKO_API_KEY=your-api-key-optional

# ESP32 Configuration
ESP32_WIFI_SSID=your-wifi-ssid
ESP32_WIFI_PASSWORD=your-wifi-password
```

### **Database Configuration**
- **SQLite** (default): Good for development and small deployments
- **PostgreSQL**: Recommended for production
- **MySQL**: Alternative production option

## 🐛 **Troubleshooting**

### **Common Issues**

1. **Database Errors**
   - Ensure database file permissions
   - Check SQLAlchemy configuration
   - Verify database URL format

2. **ESP32 Connection Issues**
   - Verify WiFi credentials
   - Check server IP address
   - Ensure ESP32 and server are on same network

3. **API Rate Limits**
   - CoinGecko has rate limits
   - Consider upgrading to paid API
   - Implement request caching

4. **WebSocket Issues**
   - Check firewall settings
   - Verify port 5000 is open
   - Test with different browsers

### **Debug Mode**
```bash
# Enable debug mode
export FLASK_DEBUG=1
python app_multi_user.py
```

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 **License**

This project is open source. Feel free to modify and distribute.

## 🆘 **Support**

For issues and questions:
1. Check the troubleshooting section
2. Review the logs for error messages
3. Test with different configurations
4. Create an issue with detailed information

---

**🎉 Enjoy your Multi-User IoT Stock Monitor!**

*Monitor cryptocurrencies like a pro with real-time hardware alerts and comprehensive user management.*
