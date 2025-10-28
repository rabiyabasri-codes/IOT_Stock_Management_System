/*
 * Enhanced IoT Stock Monitor - ESP32 Code
 * 
 * Multi-user support with personalized output settings
 * 
 * Hardware Connections:
 * - Red LED: GPIO 2
 * - Green LED: GPIO 4  
 * - Blue LED: GPIO 5
 * - Buzzer: GPIO 18
 * - Built-in LED: GPIO 2 (for status indication)
 * 
 * Features:
 * - Personalized LED brightness control
 * - Customizable buzzer volume and duration
 * - LED blink speed control
 * - User-specific settings
 * - WebSocket connection to Flask server
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

// PWM channels for LED brightness control
const int RED_PWM_CHANNEL = 0;
const int GREEN_PWM_CHANNEL = 1;
const int BLUE_PWM_CHANNEL = 2;
const int BUZZER_PWM_CHANNEL = 3;

// PWM settings
const int PWM_FREQUENCY = 5000;
const int PWM_RESOLUTION = 8;  // 8-bit resolution (0-255)

// WebSocket client
WebSocketsClient webSocket;

// State variables
bool isConnected = false;
unsigned long lastHeartbeat = 0;
unsigned long lastSignalTime = 0;
String currentSignal = "neutral";
String currentCoin = "";
int currentUserId = 0;

// LED states
bool redLedState = false;
bool greenLedState = false;
bool blueLedState = false;
bool buzzerState = false;

// Personalized settings
struct UserSettings {
    bool enable_led = true;
    bool enable_buzzer = true;
    int led_brightness = 100;  // 0-100%
    int buzzer_volume = 50;    // 0-100%
    int buzzer_duration = 2000; // milliseconds
    int led_blink_speed = 500;  // milliseconds
} userSettings;

// LED blink control
unsigned long lastBlinkTime = 0;
bool blinkState = false;

void setup() {
  Serial.begin(115200);
  Serial.println("Starting Enhanced IoT Stock Monitor...");
  
  // Initialize hardware pins
  pinMode(RED_LED_PIN, OUTPUT);
  pinMode(GREEN_LED_PIN, OUTPUT);
  pinMode(BLUE_LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(STATUS_LED_PIN, OUTPUT);
  
  // Setup PWM channels for LED brightness control
  ledcSetup(RED_PWM_CHANNEL, PWM_FREQUENCY, PWM_RESOLUTION);
  ledcSetup(GREEN_PWM_CHANNEL, PWM_FREQUENCY, PWM_RESOLUTION);
  ledcSetup(BLUE_PWM_CHANNEL, PWM_FREQUENCY, PWM_RESOLUTION);
  ledcSetup(BUZZER_PWM_CHANNEL, PWM_FREQUENCY, PWM_RESOLUTION);
  
  ledcAttachPin(RED_LED_PIN, RED_PWM_CHANNEL);
  ledcAttachPin(GREEN_LED_PIN, GREEN_PWM_CHANNEL);
  ledcAttachPin(BLUE_LED_PIN, BLUE_PWM_CHANNEL);
  ledcAttachPin(BUZZER_PIN, BUZZER_PWM_CHANNEL);
  
  // Turn off all LEDs initially
  setLEDBrightness(RED_PWM_CHANNEL, 0);
  setLEDBrightness(GREEN_PWM_CHANNEL, 0);
  setLEDBrightness(BLUE_PWM_CHANNEL, 0);
  setLEDBrightness(BUZZER_PWM_CHANNEL, 0);
  
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
  
  // Handle LED blinking
  handleLEDBlinking();
  
  // Handle buzzer timing
  if (buzzerState && millis() - lastSignalTime > userSettings.buzzer_duration) {
    setLEDBrightness(BUZZER_PWM_CHANNEL, 0);
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
  }
}

void setupOTA() {
  ArduinoOTA.setHostname("ESP32-StockMonitor-Enhanced");
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
  DynamicJsonDocument doc(2048);
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
    } else if (messageType == "user_settings") {
      handleUserSettings(doc);
    } else if (messageType == "esp32_command") {
      handleESP32Command(doc);
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
      
      // Update user settings if provided
      if (signalData.containsKey("user_settings")) {
        JsonObject settings = signalData["user_settings"];
        userSettings.enable_led = settings["enable_led"];
        userSettings.enable_buzzer = settings["enable_buzzer"];
        userSettings.led_brightness = settings["led_brightness"];
        userSettings.buzzer_volume = settings["buzzer_volume"];
        userSettings.buzzer_duration = settings["buzzer_duration"];
        userSettings.led_blink_speed = settings["led_blink_speed"];
        
        Serial.println("Updated user settings:");
        Serial.printf("  LED enabled: %s\n", userSettings.enable_led ? "true" : "false");
        Serial.printf("  Buzzer enabled: %s\n", userSettings.enable_buzzer ? "true" : "false");
        Serial.printf("  LED brightness: %d%%\n", userSettings.led_brightness);
        Serial.printf("  Buzzer volume: %d%%\n", userSettings.buzzer_volume);
      }
      
      Serial.printf("Coin: %s, Signal: %s, LED: %s, Change: %.2f%%\n", 
                   coinId.c_str(), signalType.c_str(), ledColor.c_str(), priceChange);
      
      // Update LEDs based on signal and user preferences
      updateLEDs(ledColor);
      
      // Trigger buzzer for significant changes (if enabled)
      if (userSettings.enable_buzzer && abs(priceChange) > 5.0) {
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
    if (trigger && userSettings.enable_buzzer) {
      triggerBuzzer();
    }
  }
}

void handleUserSettings(DynamicJsonDocument& doc) {
  if (doc.containsKey("enable_led")) {
    userSettings.enable_led = doc["enable_led"];
  }
  if (doc.containsKey("enable_buzzer")) {
    userSettings.enable_buzzer = doc["enable_buzzer"];
  }
  if (doc.containsKey("led_brightness")) {
    userSettings.led_brightness = doc["led_brightness"];
  }
  if (doc.containsKey("buzzer_volume")) {
    userSettings.buzzer_volume = doc["buzzer_volume"];
  }
  if (doc.containsKey("buzzer_duration")) {
    userSettings.buzzer_duration = doc["buzzer_duration"];
  }
  if (doc.containsKey("led_blink_speed")) {
    userSettings.led_blink_speed = doc["led_blink_speed"];
  }
  
  Serial.println("User settings updated");
}

void handleESP32Command(DynamicJsonDocument& doc) {
  Serial.println("Received ESP32 command");
  
  if (doc.containsKey("type")) {
    String commandType = doc["type"];
    
    if (commandType == "user_settings") {
      // Handle real-time settings update
      if (doc.containsKey("user_settings")) {
        JsonObject settings = doc["user_settings"];
        updateUserSettings(settings);
      }
    } else if (commandType == "market_update") {
      // Handle market update with settings
      if (doc.containsKey("signals")) {
        handleMarketUpdate(doc);
      }
    }
  }
}

void updateUserSettings(JsonObject settings) {
  bool settingsChanged = false;
  
  if (settings.containsKey("enable_led")) {
    bool newEnableLed = settings["enable_led"];
    if (userSettings.enable_led != newEnableLed) {
      userSettings.enable_led = newEnableLed;
      settingsChanged = true;
      Serial.printf("LED output %s\n", newEnableLed ? "enabled" : "disabled");
    }
  }
  
  if (settings.containsKey("enable_buzzer")) {
    bool newEnableBuzzer = settings["enable_buzzer"];
    if (userSettings.enable_buzzer != newEnableBuzzer) {
      userSettings.enable_buzzer = newEnableBuzzer;
      settingsChanged = true;
      Serial.printf("Buzzer output %s\n", newEnableBuzzer ? "enabled" : "disabled");
    }
  }
  
  if (settings.containsKey("led_brightness")) {
    int newBrightness = settings["led_brightness"];
    if (userSettings.led_brightness != newBrightness) {
      userSettings.led_brightness = newBrightness;
      settingsChanged = true;
      Serial.printf("LED brightness updated to %d%%\n", newBrightness);
      
      // Apply brightness change immediately to current LEDs
      applyCurrentLEDBrightness();
    }
  }
  
  if (settings.containsKey("buzzer_volume")) {
    int newVolume = settings["buzzer_volume"];
    if (userSettings.buzzer_volume != newVolume) {
      userSettings.buzzer_volume = newVolume;
      settingsChanged = true;
      Serial.printf("Buzzer volume updated to %d%%\n", newVolume);
    }
  }
  
  if (settings.containsKey("buzzer_duration")) {
    int newDuration = settings["buzzer_duration"];
    if (userSettings.buzzer_duration != newDuration) {
      userSettings.buzzer_duration = newDuration;
      settingsChanged = true;
      Serial.printf("Buzzer duration updated to %dms\n", newDuration);
    }
  }
  
  if (settings.containsKey("led_blink_speed")) {
    int newBlinkSpeed = settings["led_blink_speed"];
    if (userSettings.led_blink_speed != newBlinkSpeed) {
      userSettings.led_blink_speed = newBlinkSpeed;
      settingsChanged = true;
      Serial.printf("LED blink speed updated to %dms\n", newBlinkSpeed);
    }
  }
  
  if (settingsChanged) {
    Serial.println("Real-time settings applied successfully!");
    
    // Test the new settings with a quick LED flash
    testNewSettings();
  }
}

void applyCurrentLEDBrightness() {
  int brightness = map(userSettings.led_brightness, 0, 100, 0, 255);
  
  if (redLedState) setLEDBrightness(RED_PWM_CHANNEL, brightness);
  if (greenLedState) setLEDBrightness(GREEN_PWM_CHANNEL, brightness);
  if (blueLedState) setLEDBrightness(BLUE_PWM_CHANNEL, brightness);
}

void testNewSettings() {
  // Quick test of new settings
  Serial.println("Testing new settings...");
  
  if (userSettings.enable_led) {
    // Flash all LEDs with new brightness
    int brightness = map(userSettings.led_brightness, 0, 100, 0, 255);
    
    setLEDBrightness(RED_PWM_CHANNEL, brightness);
    setLEDBrightness(GREEN_PWM_CHANNEL, brightness);
    setLEDBrightness(BLUE_PWM_CHANNEL, brightness);
    
    delay(200);
    
    setLEDBrightness(RED_PWM_CHANNEL, 0);
    setLEDBrightness(GREEN_PWM_CHANNEL, 0);
    setLEDBrightness(BLUE_PWM_CHANNEL, 0);
  }
  
  if (userSettings.enable_buzzer) {
    // Test buzzer with new volume
    int volume = map(userSettings.buzzer_volume, 0, 100, 0, 255);
    setLEDBrightness(BUZZER_PWM_CHANNEL, volume);
    delay(100);
    setLEDBrightness(BUZZER_PWM_CHANNEL, 0);
  }
  
  Serial.println("Settings test completed");
}

void updateLEDs(String color) {
  if (!userSettings.enable_led) {
    // Turn off all LEDs if LED output is disabled
    setLEDBrightness(RED_PWM_CHANNEL, 0);
    setLEDBrightness(GREEN_PWM_CHANNEL, 0);
    setLEDBrightness(BLUE_PWM_CHANNEL, 0);
    return;
  }
  
  // Turn off all LEDs first
  setLEDBrightness(RED_PWM_CHANNEL, 0);
  setLEDBrightness(GREEN_PWM_CHANNEL, 0);
  setLEDBrightness(BLUE_PWM_CHANNEL, 0);
  
  redLedState = false;
  greenLedState = false;
  blueLedState = false;
  
  // Turn on appropriate LED with user's brightness setting
  int brightness = map(userSettings.led_brightness, 0, 100, 0, 255);
  
  if (color == "red") {
    setLEDBrightness(RED_PWM_CHANNEL, brightness);
    redLedState = true;
    Serial.println("Red LED ON - Market down");
  } else if (color == "green") {
    setLEDBrightness(GREEN_PWM_CHANNEL, brightness);
    greenLedState = true;
    Serial.println("Green LED ON - Market up");
  } else if (color == "blue") {
    setLEDBrightness(BLUE_PWM_CHANNEL, brightness);
    blueLedState = true;
    Serial.println("Blue LED ON - Invested coin");
  } else {
    Serial.println("All LEDs OFF - Neutral signal");
  }
}

void setLEDBrightness(int channel, int brightness) {
  ledcWrite(channel, brightness);
}

void handleLEDBlinking() {
  if (!userSettings.enable_led) return;
  
  // Only blink if there's an active signal
  if (currentSignal != "neutral" && currentSignal != "") {
    if (millis() - lastBlinkTime > userSettings.led_blink_speed) {
      blinkState = !blinkState;
      lastBlinkTime = millis();
      
      // Apply blinking to active LEDs
      int brightness = blinkState ? map(userSettings.led_brightness, 0, 100, 0, 255) : 0;
      
      if (redLedState) setLEDBrightness(RED_PWM_CHANNEL, brightness);
      if (greenLedState) setLEDBrightness(GREEN_PWM_CHANNEL, brightness);
      if (blueLedState) setLEDBrightness(BLUE_PWM_CHANNEL, brightness);
    }
  }
}

void triggerBuzzer() {
  if (!userSettings.enable_buzzer) return;
  
  int volume = map(userSettings.buzzer_volume, 0, 100, 0, 255);
  setLEDBrightness(BUZZER_PWM_CHANNEL, volume);
  buzzerState = true;
  lastSignalTime = millis();
  Serial.printf("Buzzer triggered - Volume: %d%%, Duration: %dms\n", 
                userSettings.buzzer_volume, userSettings.buzzer_duration);
}

void sendConnectionMessage() {
  DynamicJsonDocument doc(256);
  doc["type"] = "esp32_connect";
  doc["device_id"] = WiFi.macAddress();
  doc["status"] = "connected";
  doc["features"] = "enhanced_personalized_output";
  
  String message;
  serializeJson(doc, message);
  webSocket.sendTXT(message);
  
  Serial.println("Sent connection message");
}

void sendHeartbeat() {
  if (isConnected) {
    DynamicJsonDocument doc(512);
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
    doc["user_settings"] = {
      "enable_led": userSettings.enable_led,
      "enable_buzzer": userSettings.enable_buzzer,
      "led_brightness": userSettings.led_brightness,
      "buzzer_volume": userSettings.buzzer_volume,
      "buzzer_duration": userSettings.buzzer_duration,
      "led_blink_speed": userSettings.led_blink_speed
    };
    
    String message;
    serializeJson(doc, message);
    webSocket.sendTXT(message);
    
    Serial.println("Sent heartbeat with user settings");
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
