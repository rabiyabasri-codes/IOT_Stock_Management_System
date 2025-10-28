// Socket.IO connection
const socket = io();

// Global variables
let currentSettings = {
    threshold: 0,
    selected_coins: [],
    invested_coins: []
};

let availableCoins = [];
let marketData = {};

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    loadAvailableCoins();
    loadCurrentSettings();
    setupSocketListeners();
});

// Load available cryptocurrencies
async function loadAvailableCoins() {
    try {
        const response = await fetch('/api/coins');
        availableCoins = await response.json();
        
        const coinSelect = document.getElementById('coinSelect');
        const investedSelect = document.getElementById('investedCoins');
        
        // Clear existing options
        coinSelect.innerHTML = '';
        investedSelect.innerHTML = '';
        
        // Add coins to both select elements
        availableCoins.forEach(coin => {
            const option1 = new Option(`${coin.name} (${coin.symbol}) - $${coin.current_price}`, coin.id);
            const option2 = new Option(`${coin.name} (${coin.symbol})`, coin.id);
            
            coinSelect.add(option1);
            investedSelect.add(option2);
        });
        
        console.log('Loaded coins:', availableCoins.length);
    } catch (error) {
        console.error('Error loading coins:', error);
        document.getElementById('coinSelect').innerHTML = '<option value="">Error loading coins</option>';
    }
}

// Load current settings from server
async function loadCurrentSettings() {
    try {
        const response = await fetch('/api/settings');
        currentSettings = await response.json();
        
        // Update UI with current settings
        document.getElementById('threshold').value = currentSettings.threshold;
        
        // Update selected coins
        const coinSelect = document.getElementById('coinSelect');
        Array.from(coinSelect.options).forEach(option => {
            option.selected = currentSettings.selected_coins.includes(option.value);
        });
        
        // Update invested coins
        const investedSelect = document.getElementById('investedCoins');
        Array.from(investedSelect.options).forEach(option => {
            option.selected = currentSettings.invested_coins.includes(option.value);
        });
        
        console.log('Loaded settings:', currentSettings);
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

// Save settings to server
async function saveSettings() {
    const threshold = parseFloat(document.getElementById('threshold').value) || 0;
    const selectedCoins = Array.from(document.getElementById('coinSelect').selectedOptions).map(option => option.value);
    const investedCoins = Array.from(document.getElementById('investedCoins').selectedOptions).map(option => option.value);
    
    if (threshold <= 0) {
        alert('Please enter a valid threshold percentage');
        return;
    }
    
    if (selectedCoins.length === 0) {
        alert('Please select at least one cryptocurrency to monitor');
        return;
    }
    
    const settings = {
        threshold: threshold,
        selected_coins: selectedCoins,
        invested_coins: investedCoins
    };
    
    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });
        
        if (response.ok) {
            currentSettings = settings;
            showNotification('Settings saved successfully!', 'success');
            console.log('Settings saved:', settings);
        } else {
            throw new Error('Failed to save settings');
        }
    } catch (error) {
        console.error('Error saving settings:', error);
        showNotification('Error saving settings', 'error');
    }
}

// Setup Socket.IO event listeners
function setupSocketListeners() {
    socket.on('connect', function() {
        console.log('Connected to server');
        showNotification('Connected to server', 'success');
    });
    
    socket.on('disconnect', function() {
        console.log('Disconnected from server');
        showNotification('Disconnected from server', 'error');
    });
    
    socket.on('market_update', function(data) {
        console.log('Market update received:', data);
        updateMarketDisplay(data);
    });
    
    socket.on('esp32_status', function(data) {
        updateESP32Status(data.connected);
    });
}

// Update market data display
function updateMarketDisplay(data) {
    const marketDataDiv = document.getElementById('marketData');
    const signals = data.signals;
    
    if (!signals || Object.keys(signals).length === 0) {
        marketDataDiv.innerHTML = '<p class="text-muted">No market data available</p>';
        return;
    }
    
    let html = '<div class="row">';
    
    Object.entries(signals).forEach(([coinId, signal]) => {
        const coin = availableCoins.find(c => c.id === coinId);
        const coinName = coin ? coin.name : coinId;
        const coinSymbol = coin ? coin.symbol : coinId.toUpperCase();
        
        const priceClass = signal.change_24h > 0 ? 'price-positive' : 
                          signal.change_24h < 0 ? 'price-negative' : 'price-neutral';
        
        const changeIcon = signal.change_24h > 0 ? 'fa-arrow-up' : 
                          signal.change_24h < 0 ? 'fa-arrow-down' : 'fa-minus';
        
        html += `
            <div class="col-md-6 col-lg-4 mb-3">
                <div class="coin-card">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="mb-1">${coinName}</h6>
                            <small class="text-muted">${coinSymbol}</small>
                        </div>
                        <div class="text-end">
                            <div class="led-indicator led-${signal.led_color}"></div>
                        </div>
                    </div>
                    <hr class="my-2">
                    <div class="d-flex justify-content-between">
                        <span>Price:</span>
                        <strong>$${signal.price.toFixed(2)}</strong>
                    </div>
                    <div class="d-flex justify-content-between">
                        <span>24h Change:</span>
                        <span class="${priceClass}">
                            <i class="fas ${changeIcon}"></i> ${Math.abs(signal.change_24h).toFixed(2)}%
                        </span>
                    </div>
                    <div class="d-flex justify-content-between">
                        <span>Signal:</span>
                        <span class="badge bg-${getSignalColor(signal.signal)}">${signal.signal.toUpperCase()}</span>
                    </div>
                    <small class="text-muted">Updated: ${new Date(signal.timestamp).toLocaleTimeString()}</small>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    marketDataDiv.innerHTML = html;
    
    // Update hardware status
    updateHardwareStatus(signals);
}

// Get signal color for badge
function getSignalColor(signal) {
    switch(signal) {
        case 'up': return 'success';
        case 'down': return 'danger';
        case 'invested': return 'primary';
        case 'neutral': return 'secondary';
        default: return 'secondary';
    }
}

// Update ESP32 connection status
function updateESP32Status(connected) {
    const statusDiv = document.getElementById('esp32Status');
    const hardwareStatus = document.getElementById('hardwareStatus');
    
    if (connected) {
        statusDiv.className = 'esp32-status esp32-connected';
        statusDiv.innerHTML = '<i class="fas fa-microchip"></i> ESP32: Connected';
        
        hardwareStatus.innerHTML = `
            <p><i class="fas fa-circle text-success"></i> ESP32: Connected</p>
            <p><i class="fas fa-lightbulb text-warning"></i> LED: Active</p>
            <p><i class="fas fa-volume-up text-info"></i> Buzzer: Ready</p>
        `;
    } else {
        statusDiv.className = 'esp32-status esp32-disconnected';
        statusDiv.innerHTML = '<i class="fas fa-microchip"></i> ESP32: Disconnected';
        
        hardwareStatus.innerHTML = `
            <p><i class="fas fa-circle text-danger"></i> ESP32: Not Connected</p>
            <p><i class="fas fa-lightbulb text-muted"></i> LED: Off</p>
            <p><i class="fas fa-volume-up text-muted"></i> Buzzer: Off</p>
        `;
    }
}

// Update hardware status based on signals
function updateHardwareStatus(signals) {
    const hardwareStatus = document.getElementById('hardwareStatus');
    const esp32Status = document.getElementById('esp32Status');
    
    if (esp32Status.classList.contains('esp32-connected')) {
        const activeSignals = Object.values(signals).filter(s => s.led_color !== 'off');
        
        if (activeSignals.length > 0) {
            const ledStatus = activeSignals.some(s => s.led_color === 'red') ? 'text-danger' : 
                            activeSignals.some(s => s.led_color === 'green') ? 'text-success' : 'text-primary';
            
            hardwareStatus.innerHTML = `
                <p><i class="fas fa-circle text-success"></i> ESP32: Connected</p>
                <p><i class="fas fa-lightbulb ${ledStatus}"></i> LED: ${activeSignals[0].led_color.toUpperCase()}</p>
                <p><i class="fas fa-volume-up text-info"></i> Buzzer: Ready</p>
            `;
        }
    }
}

// Show notification
function showNotification(message, type) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'success' ? 'success' : 'danger'} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 3000);
}

// Simulate ESP32 connection (for testing)
function simulateESP32Connection() {
    socket.emit('esp32_connect');
    showNotification('ESP32 simulation connected', 'info');
}

// Add keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl+S to save settings
    if (e.ctrlKey && e.key === 's') {
        e.preventDefault();
        saveSettings();
    }
    
    // Ctrl+R to refresh coins
    if (e.ctrlKey && e.key === 'r') {
        e.preventDefault();
        loadAvailableCoins();
    }
});

// Auto-save settings when threshold changes
document.getElementById('threshold').addEventListener('input', function() {
    // Debounce the auto-save
    clearTimeout(window.autoSaveTimeout);
    window.autoSaveTimeout = setTimeout(() => {
        if (this.value && parseFloat(this.value) > 0) {
            saveSettings();
        }
    }, 1000);
});

console.log('IoT Stock Monitor frontend loaded successfully!');
