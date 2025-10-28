/*
 * IoT Stock Monitor - ESP32 Code
 * 
 * This code runs on ESP32 to control LEDs and buzzer based on stock market signals
 * 
 * Hardware Connections:
 * - Red LED: GPIO 2
 * - Green LED: GPIO 4  
 * - Blue LED: GPIO 5
 * - Buzzer: GPIO 18
 * - Built-in LED: GPIO 2 (for status indication)
 * 
 * Features:
 * - WebSocket connection to Flask server
 * - Real-time LED control based on market signals
 * - Buzzer alerts for significant price changes
 * - WiFi connection with fallback
 * - OTA update capability
 */

#include <WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>
#include <ArduinoOTA.h>

// WiFi credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Server configuration
const char* server_host = "YOUR_SERVER_IP";  // Replace with your computer's IP
const int server_port = 5000;
const char* server_path = "/socket.io/?transport=websocket";

// Hardware pins
const int RED_LED_PIN = 2;
const int GREEN_LED_PIN = 4;
const int BLUE_LED_PIN = 5;
const int BUZZER_PIN = 18;
const int STATUS_LED_PIN = 2;  // Built-in LED

// WebSocket client
WebSocketsClient webSocket;

// State variables
bool isConnected = false;
unsigned long lastHeartbeat = 0;
unsigned long lastSignalTime = 0;
String currentSignal = "neutral";
String currentCoin = "";

// LED states
bool redLedState = false;
bool greenLedState = false;
bool blueLedState = false;
bool buzzerState = false;

void setup() {
  Serial.begin(115200);
  Serial.println("Starting IoT Stock Monitor...");
  
  // Initialize hardware pins
  pinMode(RED_LED_PIN, OUTPUT);
  pinMode(GREEN_LED_PIN, OUTPUT);
  pinMode(BLUE_LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(STATUS_LED_PIN, OUTPUT);
  
  // Turn off all LEDs initially
  digitalWrite(RED_LED_PIN, LOW);
  digitalWrite(GREEN_LED_PIN, LOW);
  digitalWrite(BLUE_LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);
  digitalWrite(STATUS_LED_PIN, LOW);
  
  // Connect to WiFi
  connectToWiFi();
  
  // Setup OTA updates
  setupOTA();
  
  // Initialize WebSocket connection
  setupWebSocket();
  
  Serial.println("Setup complete!");
}

void loop() {
  // Handle OTA updates
  ArduinoOTA.handle();
  
  // Handle WebSocket events
  webSocket.loop();
  
  // Send heartbeat every 30 seconds
  if (millis() - lastHeartbeat > 30000) {
    sendHeartbeat();
    lastHeartbeat = millis();
  }
  
  // Blink status LED to show activity
  if (millis() % 2000 < 100) {
    digitalWrite(STATUS_LED_PIN, !digitalRead(STATUS_LED_PIN));
  }
  
  // Handle buzzer timing
  if (buzzerState && millis() - lastSignalTime > 2000) {
    digitalWrite(BUZZER_PIN, LOW);
    buzzerState = false;
  }
  
  delay(10);
}

void connectToWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.println("WiFi connected!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    Serial.print("MAC address: ");
    Serial.println(WiFi.macAddress());
  } else {
    Serial.println();
    Serial.println("WiFi connection failed!");
    // You can implement fallback behavior here
  }
}

void setupOTA() {
  ArduinoOTA.setHostname("ESP32-StockMonitor");
  ArduinoOTA.setPassword("stockmonitor123");
  
  ArduinoOTA.onStart([]() {
    String type = (ArduinoOTA.getCommand() == U_FLASH) ? "sketch" : "filesystem";
    Serial.println("Start updating " + type);
  });
  
  ArduinoOTA.onEnd([]() {
    Serial.println("\nEnd");
  });
  
  ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
    Serial.printf("Progress: %u%%\r", (progress / (total / 100)));
  });
  
  ArduinoOTA.onError([](ota_error_t error) {
    Serial.printf("Error[%u]: ", error);
    if (error == OTA_AUTH_ERROR) Serial.println("Auth Failed");
    else if (error == OTA_BEGIN_ERROR) Serial.println("Begin Failed");
    else if (error == OTA_CONNECT_ERROR) Serial.println("Connect Failed");
    else if (error == OTA_RECEIVE_ERROR) Serial.println("Receive Failed");
    else if (error == OTA_END_ERROR) Serial.println("End Failed");
  });
  
  ArduinoOTA.begin();
  Serial.println("OTA Ready");
}

void setupWebSocket() {
  webSocket.begin(server_host, server_port, server_path);
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(5000);
  webSocket.enableHeartbeat(15000, 3000, 2);
}

void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
  switch(type) {
    case WStype_DISCONNECTED:
      Serial.println("WebSocket Disconnected");
      isConnected = false;
      break;
      
    case WStype_CONNECTED:
      Serial.println("WebSocket Connected");
      isConnected = true;
      sendConnectionMessage();
      break;
      
    case WStype_TEXT:
      handleWebSocketMessage((char*)payload);
      break;
      
    case WStype_ERROR:
      Serial.println("WebSocket Error");
      break;
      
    default:
      break;
  }
}

void handleWebSocketMessage(char* message) {
  Serial.print("Received: ");
  Serial.println(message);
  
  // Parse JSON message
  DynamicJsonDocument doc(1024);
  DeserializationError error = deserializeJson(doc, message);
  
  if (error) {
    Serial.print("JSON parsing failed: ");
    Serial.println(error.c_str());
    return;
  }
  
  // Handle different message types
  if (doc.containsKey("type")) {
    String messageType = doc["type"];
    
    if (messageType == "market_update") {
      handleMarketUpdate(doc);
    } else if (messageType == "led_control") {
      handleLedControl(doc);
    } else if (messageType == "buzzer_control") {
      handleBuzzerControl(doc);
    }
  }
}

void handleMarketUpdate(DynamicJsonDocument& doc) {
  if (doc.containsKey("signals")) {
    JsonObject signals = doc["signals"];
    
    // Process each coin signal
    for (JsonPair signal : signals) {
      String coinId = signal.key().c_str();
      JsonObject signalData = signal.value();
      
      String ledColor = signalData["led_color"];
      String signalType = signalData["signal"];
      float priceChange = signalData["change_24h"];
      
      Serial.printf("Coin: %s, Signal: %s, LED: %s, Change: %.2f%%\n", 
                   coinId.c_str(), signalType.c_str(), ledColor.c_str(), priceChange);
      
      // Update LEDs based on signal
      updateLEDs(ledColor);
      
      // Trigger buzzer for significant changes
      if (abs(priceChange) > 5.0) {  // Buzzer for changes > 5%
        triggerBuzzer();
      }
      
      currentSignal = signalType;
      currentCoin = coinId;
      lastSignalTime = millis();
    }
  }
}

void handleLedControl(DynamicJsonDocument& doc) {
  if (doc.containsKey("color")) {
    String color = doc["color"];
    updateLEDs(color);
  }
}

void handleBuzzerControl(DynamicJsonDocument& doc) {
  if (doc.containsKey("trigger")) {
    bool trigger = doc["trigger"];
    if (trigger) {
      triggerBuzzer();
    }
  }
}

void updateLEDs(String color) {
  // Turn off all LEDs first
  digitalWrite(RED_LED_PIN, LOW);
  digitalWrite(GREEN_LED_PIN, LOW);
  digitalWrite(BLUE_LED_PIN, LOW);
  
  redLedState = false;
  greenLedState = false;
  blueLedState = false;
  
  // Turn on appropriate LED
  if (color == "red") {
    digitalWrite(RED_LED_PIN, HIGH);
    redLedState = true;
    Serial.println("Red LED ON - Market down");
  } else if (color == "green") {
    digitalWrite(GREEN_LED_PIN, HIGH);
    greenLedState = true;
    Serial.println("Green LED ON - Market up");
  } else if (color == "blue") {
    digitalWrite(BLUE_LED_PIN, HIGH);
    blueLedState = true;
    Serial.println("Blue LED ON - Invested coin");
  } else {
    Serial.println("All LEDs OFF - Neutral signal");
  }
}

void triggerBuzzer() {
  digitalWrite(BUZZER_PIN, HIGH);
  buzzerState = true;
  lastSignalTime = millis();
  Serial.println("Buzzer triggered - Significant price change!");
}

void sendConnectionMessage() {
  DynamicJsonDocument doc(256);
  doc["type"] = "esp32_connect";
  doc["device_id"] = WiFi.macAddress();
  doc["status"] = "connected";
  
  String message;
  serializeJson(doc, message);
  webSocket.sendTXT(message);
  
  Serial.println("Sent connection message");
}

void sendHeartbeat() {
  if (isConnected) {
    DynamicJsonDocument doc(256);
    doc["type"] = "heartbeat";
    doc["device_id"] = WiFi.macAddress();
    doc["uptime"] = millis();
    doc["signal"] = currentSignal;
    doc["coin"] = currentCoin;
    doc["leds"] = {
      "red": redLedState,
      "green": greenLedState,
      "blue": blueLedState
    };
    
    String message;
    serializeJson(doc, message);
    webSocket.sendTXT(message);
    
    Serial.println("Sent heartbeat");
  }
}

// Utility function to get WiFi signal strength
int getWiFiSignalStrength() {
  return WiFi.RSSI();
}

// Utility function to get free heap memory
size_t getFreeHeap() {
  return ESP.getFreeHeap();
}

// Function to handle deep sleep (optional)
void enterDeepSleep(int seconds) {
  Serial.println("Entering deep sleep for " + String(seconds) + " seconds");
  esp_deep_sleep(seconds * 1000000);
}
