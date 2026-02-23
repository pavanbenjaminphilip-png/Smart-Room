/*
 * ============================================================
 * SMART ROOM CONTROL SYSTEM - FINAL VERSION
 * ============================================================
 * 
 * Features:
 * - System ON/OFF with smart auto mode
 * - LED brightness control (analogWrite - direct PWM)
 * - Stepper motor blinds (light sensor control)
 * - Fan control (temperature-based)
 * - Motion sensor (PIR) detection
 * - Temperature & humidity monitoring (DHT11/DHT22)
 * - Light sensor (LDR) for blinds automation
 * - Camera detection integration
 * - Voice control via Gemini AI
 * 
 * Hardware:
 * - ESP32 Board
 * - LED on Pin 25 (PWM - analogWrite)
 * - DHT11/DHT22 on Pin 14
 * - PIR Motion Sensor on Pin 21
 * - LDR Light Sensor on Pin 33 (ADC)
 * - Fan Relay on Pin 13
 * - Stepper Motor (28BYJ-48 with ULN2003 Driver)
 *   - IN1 → Pin 23
 *   - IN2 → Pin 4
 *   - IN3 → Pin 15
 *   - IN4 → Pin 35
 * 
 * IP: 192.168.0.139
 * 
 * BLINDS LOGIC:
 * - High light detected (bright) → OPEN blinds (let light in)
 * - Low light (dark/cloudy) → CLOSE blinds (privacy)
 * 
 * ============================================================
 */

#include <WiFi.h>
#include <WebServer.h>
#include <DHT.h>
#include <ArduinoJson.h>
#include <Stepper.h>

// ============================================================
// CONFIGURATION
// ============================================================

const char* ssid = "Georgephilip-2G";
const char* password = "Thakkol1";

// Pin Definitions
#define LED_PIN 25           // PWM LED (analogWrite)
#define DHT_PIN 14            // DHT sensor
#define DHT_TYPE DHT11       // DHT11 or DHT22
#define PIR_PIN 21           // PIR Motion Sensor
#define LDR_PIN 33           // Light sensor (ADC)
#define FAN_PIN 13           // Fan relay

// Stepper Motor Pins (28BYJ-48)
#define STEPPER_IN1 23
#define STEPPER_IN2 4
#define STEPPER_IN3 15
#define STEPPER_IN4 35

// Stepper Motor Configuration
#define STEPS_PER_REV 2048   // 28BYJ-48 with gear reduction
#define STEPPER_SPEED 10     // RPM

// Brightness levels (0-255 for analogWrite)
#define BRIGHTNESS_OFF 0
#define BRIGHTNESS_DIM 50
#define BRIGHTNESS_BRIGHT 255

// Detection timeouts (ms)
#define DETECTION_TIMEOUT 5000

// Light thresholds for blinds (REVERSED LOGIC)
#define LIGHT_THRESHOLD_BRIGHT 2000  // If light > this, OPEN blinds
#define LIGHT_THRESHOLD_DIM 800      // If light < this, CLOSE blinds

// Temperature threshold for fan
#define TEMP_THRESHOLD_FAN 26.0      // °C - turn on fan above this

// Blinds positions (in steps)
#define BLINDS_OPEN_STEPS 0
#define BLINDS_CLOSED_STEPS 2048     // Full revolution

// ============================================================
// GLOBALS
// ============================================================

WebServer server(80);
DHT dht(DHT_PIN, DHT_TYPE);
Stepper stepperMotor(STEPS_PER_REV, STEPPER_IN1, STEPPER_IN3, STEPPER_IN2, STEPPER_IN4);

// System state
bool systemOn = true;         // System ON by default
bool manualMode = false;
int manualBrightness = 0;
bool motionDetected = false;
bool cameraDetected = false;

// Blinds state
int blindsPosition = 0;
bool blindsAuto = true;
String blindsState = "OPEN";

// Fan state
bool fanOn = false;
bool fanAuto = true;

// Sensor readings
float temperature = 0;
float humidity = 0;
int lightLevel = 0;
unsigned long lastSensorRead = 0;
const unsigned long SENSOR_INTERVAL = 2000;

// Detection tracking
unsigned long lastDetectionTime = 0;
unsigned long lastMotionTime = 0;
int detectionCount = 0;

// Blinds control timing
unsigned long lastBlindsUpdate = 0;
const unsigned long BLINDS_UPDATE_INTERVAL = 10000;

// ============================================================
// SETUP
// ============================================================

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  // Enable CORS
  server.enableCORS(true);
  
  // Initialize pins
  pinMode(LED_PIN, OUTPUT);
  pinMode(PIR_PIN, INPUT);
  pinMode(LDR_PIN, INPUT);
  pinMode(FAN_PIN, OUTPUT);
  
  // Turn off LED initially using analogWrite
  analogWrite(LED_PIN, 0);
  
  // Setup stepper motor
  stepperMotor.setSpeed(STEPPER_SPEED);
  
  // Initialize outputs
  digitalWrite(FAN_PIN, LOW);
  
  // Initialize DHT sensor
  dht.begin();
  
  Serial.println("\n========================================");
  Serial.println("   SMART ROOM CONTROL SYSTEM");
  Serial.println("   analogWrite/digitalWrite Control");
  Serial.println("========================================");
  
  // Connect to WiFi
  Serial.print("\nConnecting to WiFi");
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false); // Disable power saving for low latency (fixes timeouts)
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✓ WiFi connected!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());
    Serial.println("\nAPI Endpoints:");
    Serial.println("  GET  /status        - Full system status");
    Serial.println("  GET  /sensors       - Temperature, humidity, light");
    Serial.println("  POST /system        - System ON/OFF");
    Serial.println("  POST /mode          - Auto/Manual mode");
    Serial.println("  POST /brightness    - Set LED brightness (0-255)");
    Serial.println("  POST /blinds        - Control blinds");
    Serial.println("  POST /fan           - Control fan");
    Serial.println("  POST /camera/human  - Camera detection");
    Serial.println("  POST /ai/command    - AI voice commands");
    Serial.println("\n✓ System ready!\n");
  } else {
    Serial.println("\n❌ WiFi connection failed!");
  }
  
  setupWebServer();
  server.begin();
  
  readSensors();
  
  Serial.println("Stabilizing motion sensor...");
  delay(2000);
  Serial.println("✓ All sensors ready");
  Serial.println("\n⚡ System is ON by default");
  Serial.println("LED will be DIM when no one present");
  Serial.println("LED will be BRIGHT when human detected\n");
}

// ============================================================
// WEB SERVER SETUP
// ============================================================

void setupWebServer() {
  server.on("/", HTTP_GET, handleRoot);
  server.on("/status", HTTP_GET, handleStatus);
  server.on("/sensors", HTTP_GET, handleSensors);
  server.on("/system", HTTP_POST, handleSystemControl);
  server.on("/mode", HTTP_POST, handleModeControl);
  server.on("/camera/human", HTTP_POST, handleCameraDetection);
  server.on("/brightness", HTTP_POST, handleBrightness);
  server.on("/blinds", HTTP_POST, handleBlinds);
  server.on("/fan", HTTP_POST, handleFan);
  server.on("/ai/command", HTTP_POST, handleAICommand);
  
  server.enableCORS(true);
}

// ============================================================
// MAIN LOOP
// ============================================================

void loop() {
  server.handleClient();
  
  if (millis() - lastSensorRead >= SENSOR_INTERVAL) {
    readSensors();
    lastSensorRead = millis();
  }
  
  readMotionSensor();
  checkDetectionTimeouts();
  updateLED();
  
  // Auto fan control
  if (fanAuto) {
    updateFan();
  }
  
  // Auto blinds control
  if (blindsAuto && (millis() - lastBlindsUpdate >= BLINDS_UPDATE_INTERVAL)) {
    updateBlindsAuto();
    lastBlindsUpdate = millis();
  }
}

void readMotionSensor() {
  if (digitalRead(PIR_PIN)) {
    if (!motionDetected) {
      Serial.println("🚶 Motion detected");
      motionDetected = true;
    }
    lastMotionTime = millis();
  }
}

void checkDetectionTimeouts() {
  unsigned long now = millis();
  
  // Clear motion if timeout reached
  if (motionDetected && (now - lastMotionTime > DETECTION_TIMEOUT)) {
    motionDetected = false;
    Serial.println("🚫 Motion cleared");
  }
  
  // Clear camera if timeout reached
  if (cameraDetected && (now - lastDetectionTime > DETECTION_TIMEOUT)) {
    cameraDetected = false;
    Serial.println("🚫 Camera detection cleared");
  }
}

// ============================================================
// SENSOR FUNCTIONS
// ============================================================

void readSensors() {
  float t = dht.readTemperature();
  float h = dht.readHumidity();
  
  if (!isnan(t)) {
    temperature = t;
  }
  
  if (!isnan(h)) {
    humidity = h;
  }
  
  // Read light sensor
  lightLevel = analogRead(LDR_PIN);
}

// (Function was moved and merged above)

void updateLED() {
  if (manualMode) {
    // Manual mode - use manual brightness
    analogWrite(LED_PIN, manualBrightness);
    return;
  }
  
  if (!systemOn) {
    // System OFF - all lights off
    analogWrite(LED_PIN, BRIGHTNESS_OFF);
    return;
  }
  
  // System ON + Auto Mode
  // Simple rule: Human detected = BRIGHT, No human = DIM
  bool humanPresent = cameraDetected || motionDetected;
  
  if (humanPresent) {
    analogWrite(LED_PIN, BRIGHTNESS_BRIGHT);
  } else {
    analogWrite(LED_PIN, BRIGHTNESS_DIM);
  }
}

void updateFan() {
  // Auto fan control based on temperature
  bool shouldFanBeOn = (temperature > TEMP_THRESHOLD_FAN);
  
  if (shouldFanBeOn != fanOn) {
    fanOn = shouldFanBeOn;
    digitalWrite(FAN_PIN, fanOn ? HIGH : LOW);
    
    if (fanOn) {
      Serial.printf("🌀 Fan ON (temp: %.1f°C > %.1f°C)\n", temperature, TEMP_THRESHOLD_FAN);
    } else {
      Serial.printf("🌀 Fan OFF (temp: %.1f°C)\n", temperature);
    }
  }
}

void updateBlindsAuto() {
  // Auto blinds - REVERSED: High light = OPEN, Low light = CLOSED
  String targetState = blindsState;
  
  if (lightLevel > LIGHT_THRESHOLD_BRIGHT) {
    // Bright outside - OPEN blinds (let light in)
    targetState = "OPEN";
  } else if (lightLevel < LIGHT_THRESHOLD_DIM) {
    // Dark/cloudy - CLOSE blinds (privacy)
    targetState = "CLOSED";
  }
  
  if (targetState != blindsState) {
    moveBlinds(targetState);
  }
}

void moveBlinds(String target) {
  int targetPosition;
  
  if (target == "OPEN") {
    targetPosition = BLINDS_OPEN_STEPS;
  } else {
    targetPosition = BLINDS_CLOSED_STEPS;
  }
  
  int stepsToMove = targetPosition - blindsPosition;
  
  if (stepsToMove != 0) {
    Serial.printf("🪟 Moving blinds: %s (steps: %d)\n", target.c_str(), stepsToMove);
    
    // Chunked movement to keep web server responsive
    int direction = (stepsToMove > 0) ? 1 : -1;
    int remaining = abs(stepsToMove);
    int chunkSize = 10; 
    
    while (remaining > 0) {
        int stepSize = (remaining > chunkSize) ? chunkSize : remaining;
        stepperMotor.step(stepSize * direction);
        remaining -= stepSize;
        
        // Handle web requests while moving (prevents "Read timed out")
        server.handleClient();
        delay(1); // Small yield
    }

    blindsPosition = targetPosition;
    blindsState = target;
    
    // Power off stepper coils
    digitalWrite(STEPPER_IN1, LOW);
    digitalWrite(STEPPER_IN2, LOW);
    digitalWrite(STEPPER_IN3, LOW);
    digitalWrite(STEPPER_IN4, LOW);
    
    Serial.printf("✓ Blinds: %s (light: %d)\n", blindsState.c_str(), lightLevel);
  }
}

// ============================================================
// WEB HANDLERS
// ============================================================

void handleRoot() {
  String html = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <title>Smart Room</title>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body { font-family: Arial; text-align: center; padding: 20px; 
           background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
           color: #fff; min-height: 100vh; }
    h1 { font-size: 2.5rem; margin-bottom: 10px; }
    .card { background: rgba(255,255,255,0.95); backdrop-filter: blur(10px);
            border-radius: 20px; padding: 30px; margin: 20px auto; color: #333;
            max-width: 500px; box-shadow: 0 8px 32px rgba(0,0,0,0.3); }
    button { background: #667eea; color: #fff; border: none; padding: 15px 30px; 
             margin: 5px; border-radius: 10px; cursor: pointer; font-weight: bold;
             font-size: 1rem; transition: all 0.3s; }
    button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.3); }
    .status { font-size: 1.5rem; margin: 20px; font-weight: bold; }
    .info { font-size: 1rem; margin: 10px; }
  </style>
</head>
<body>
  <h1>🏠 Smart Room</h1>
  <div class="card">
    <div class="status" id="status">Loading...</div>
    <div class="info" id="info">--</div>
    <button onclick="setSystem('on')">⚡ SYSTEM ON</button>
    <button onclick="setSystem('off')">⏹️ SYSTEM OFF</button>
  </div>
  <p style="opacity: 0.9;">Use Ollama interface for full control</p>
  
  <script>
    function setSystem(state) {
      fetch('/system', {method: 'POST', 
                     headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                     body: 'state=' + state});
    }
    
    function update() {
      Promise.all([
        fetch('/status').then(r => r.json()),
        fetch('/sensors').then(r => r.json())
      ]).then(([status, sensors]) => {
        document.getElementById('status').textContent = 
          status.system_on ? '⚡ SYSTEM ON' : '⏹️ SYSTEM OFF';
        document.getElementById('info').innerHTML = 
          '🌡️ ' + sensors.temperature.toFixed(1) + '°C | ' +
          '💧 ' + sensors.humidity.toFixed(1) + '% | ' +
          '☀️ Light: ' + sensors.light_level + '<br>' +
          '🪟 Blinds: ' + status.blinds_state + ' | ' +
          '🌀 Fan: ' + (status.fan_on ? 'ON' : 'OFF');
      });
    }
    
    update();
    setInterval(update, 2000);
  </script>
</body>
</html>
)rawliteral";
  
  server.send(200, "text/html", html);
}

void handleStatus() {
  StaticJsonDocument<512> doc;
  
  doc["system"] = "Smart Room Control";
  doc["uptime"] = millis() / 1000;
  doc["system_on"] = systemOn;
  doc["manual_mode"] = manualMode;
  
  // Current LED brightness
  int currentBrightness = 0;
  if (manualMode) {
    currentBrightness = manualBrightness;
  } else if (systemOn) {
    bool humanPresent = cameraDetected || motionDetected;
    currentBrightness = humanPresent ? BRIGHTNESS_BRIGHT : BRIGHTNESS_DIM;
  }
  
  doc["led_brightness"] = currentBrightness;
  doc["led_state"] = currentBrightness > 0 ? (currentBrightness > 100 ? "BRIGHT" : "DIM") : "OFF";
  doc["motion"] = motionDetected;
  doc["camera"] = cameraDetected;
  doc["blinds_position"] = blindsPosition;
  doc["blinds_state"] = blindsState;
  doc["blinds_auto"] = blindsAuto;
  doc["fan_on"] = fanOn;
  doc["fan_auto"] = fanAuto;
  doc["detection_count"] = detectionCount;
  doc["temperature"] = temperature;
  doc["humidity"] = humidity;
  doc["light_level"] = lightLevel;
  
  String response;
  serializeJson(doc, response);
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "application/json", response);
}

void handleSensors() {
  StaticJsonDocument<256> doc;
  
  doc["temperature"] = temperature;
  doc["humidity"] = humidity;
  doc["light_level"] = lightLevel;
  doc["motion"] = motionDetected;
  doc["timestamp"] = millis();
  
  String response;
  serializeJson(doc, response);
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "application/json", response);
}

void handleSystemControl() {
  if (server.hasArg("state")) {
    String state = server.arg("state");
    
    if (state == "on") {
      systemOn = true;
      manualMode = false;
      Serial.println("⚡ SYSTEM ON - Auto mode");
      server.send(200, "application/json", "{\"status\":\"on\"}");
    } else if (state == "off") {
      systemOn = false;
      Serial.println("⚡ SYSTEM OFF");
      server.send(200, "application/json", "{\"status\":\"off\"}");
    } else {
      server.send(400, "application/json", "{\"error\":\"Invalid state\"}");
    }
  } else {
    server.send(400, "application/json", "{\"error\":\"Missing parameter\"}");
  }
}

void handleModeControl() {
  if (server.hasArg("mode")) {
    String mode = server.arg("mode");
    
    if (mode == "auto") {
      manualMode = false;
      Serial.println("🤖 Auto mode");
      server.sendHeader("Access-Control-Allow-Origin", "*");
      server.send(200, "application/json", "{\"status\":\"auto\"}");
    } else if (mode == "manual") {
      manualMode = true;
      Serial.println("✋ Manual mode");
      server.sendHeader("Access-Control-Allow-Origin", "*");
      server.send(200, "application/json", "{\"status\":\"manual\"}");
    } else {
      server.sendHeader("Access-Control-Allow-Origin", "*");
      server.send(400, "application/json", "{\"error\":\"Invalid mode\"}");
    }
  } else {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send(400, "application/json", "{\"error\":\"Missing parameter\"}");
  }
}

void handleCameraDetection() {
  if (server.hasArg("detected")) {
    String detected = server.arg("detected");
    
    if (detected == "true") {
      if (!cameraDetected) {
        Serial.println("📷 Camera: Human detected");
        cameraDetected = true;
      }
      lastDetectionTime = millis();
      detectionCount++;
    }
    // If "false", we do nothing and let checkDetectionTimeouts() handle the 5s window
    
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send(200, "application/json", "{\"status\":\"ok\"}");
  } else {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send(400, "application/json", "{\"error\":\"Missing parameter\"}");
  }
}

void handleBrightness() {
  if (server.hasArg("value")) {
    int value = server.arg("value").toInt();
    
    if (value >= 0 && value <= 255) {
      manualBrightness = value;
      manualMode = true;
      
      Serial.printf("💡 Manual brightness: %d\n", value);
      server.sendHeader("Access-Control-Allow-Origin", "*");
      server.send(200, "application/json", "{\"status\":\"ok\"}");
    } else {
      server.sendHeader("Access-Control-Allow-Origin", "*");
      server.send(400, "application/json", "{\"error\":\"Value must be 0-255\"}");
    }
  } else {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send(400, "application/json", "{\"error\":\"Missing value\"}");
  }
}

void handleBlinds() {
  if (server.hasArg("position")) {
    String position = server.arg("position");
    
    if (position == "open") {
      blindsAuto = false;
      moveBlinds("OPEN");
      Serial.println("🪟 Blinds: OPEN (manual)");
      server.sendHeader("Access-Control-Allow-Origin", "*");
      server.send(200, "application/json", "{\"status\":\"open\"}");
    } else if (position == "close" || position == "closed") {
      blindsAuto = false;
      moveBlinds("CLOSED");
      Serial.println("🪟 Blinds: CLOSED (manual)");
      server.sendHeader("Access-Control-Allow-Origin", "*");
      server.send(200, "application/json", "{\"status\":\"closed\"}");
    } else if (position == "auto") {
      blindsAuto = true;
      Serial.println("🪟 Blinds: AUTO (light sensor)");
      server.sendHeader("Access-Control-Allow-Origin", "*");
      server.send(200, "application/json", "{\"status\":\"auto\"}");
    } else {
      server.sendHeader("Access-Control-Allow-Origin", "*");
      server.send(400, "application/json", "{\"error\":\"Invalid position\"}");
    }
  } else {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send(400, "application/json", "{\"error\":\"Missing position\"}");
  }
}

void handleFan() {
  if (server.hasArg("state")) {
    String state = server.arg("state");
    
    if (state == "on") {
      fanAuto = false;
      fanOn = true;
      digitalWrite(FAN_PIN, HIGH);
      Serial.println("🌀 Fan: ON (manual)");
      server.sendHeader("Access-Control-Allow-Origin", "*");
      server.send(200, "application/json", "{\"status\":\"on\"}");
    } else if (state == "off") {
      fanAuto = false;
      fanOn = false;
      digitalWrite(FAN_PIN, LOW);
      Serial.println("🌀 Fan: OFF (manual)");
      server.sendHeader("Access-Control-Allow-Origin", "*");
      server.send(200, "application/json", "{\"status\":\"off\"}");
    } else if (state == "auto") {
      fanAuto = true;
      Serial.println("🌀 Fan: AUTO (temperature)");
      server.sendHeader("Access-Control-Allow-Origin", "*");
      server.send(200, "application/json", "{\"status\":\"auto\"}");
    } else {
      server.sendHeader("Access-Control-Allow-Origin", "*");
      server.send(400, "application/json", "{\"error\":\"Invalid state\"}");
    }
  } else {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send(400, "application/json", "{\"error\":\"Missing state\"}");
  }
}

void handleAICommand() {
  if (server.hasArg("command")) {
    String command = server.arg("command");
    command.toLowerCase();
    
    StaticJsonDocument<256> responseDoc;
    bool success = false;
    String action = "";
    
    // System control
    if (command.indexOf("system on") >= 0 || command.indexOf("turn on") >= 0) {
      systemOn = true;
      manualMode = false;
      action = "System turned ON";
      success = true;
    }
    else if (command.indexOf("system off") >= 0 || command.indexOf("turn off system") >= 0) {
      systemOn = false;
      action = "System turned OFF";
      success = true;
    }
    // Brightness
    else if (command.indexOf("bright") >= 0 || command.indexOf("full") >= 0) {
      manualMode = true;
      manualBrightness = BRIGHTNESS_BRIGHT;
      action = "Brightness: FULL";
      success = true;
    }
    else if (command.indexOf("dim") >= 0) {
      manualMode = true;
      manualBrightness = BRIGHTNESS_DIM;
      action = "Brightness: DIM";
      success = true;
    }
    else if (command.indexOf("lights off") >= 0) {
      manualMode = true;
      manualBrightness = BRIGHTNESS_OFF;
      action = "Lights OFF";
      success = true;
    }
    // Blinds
    else if (command.indexOf("open blinds") >= 0 || command.indexOf("blinds open") >= 0) {
      blindsAuto = false;
      moveBlinds("OPEN");
      action = "Blinds opened";
      success = true;
    }
    else if (command.indexOf("close blinds") >= 0 || command.indexOf("blinds close") >= 0) {
      blindsAuto = false;
      moveBlinds("CLOSED");
      action = "Blinds closed";
      success = true;
    }
    else if (command.indexOf("blinds auto") >= 0) {
      blindsAuto = true;
      action = "Blinds set to auto (light sensor)";
      success = true;
    }
    // Fan
    else if (command.indexOf("fan on") >= 0 || command.indexOf("turn on fan") >= 0) {
      fanAuto = false;
      fanOn = true;
      digitalWrite(FAN_PIN, HIGH);
      action = "Fan turned ON";
      success = true;
    }
    else if (command.indexOf("fan off") >= 0 || command.indexOf("turn off fan") >= 0) {
      fanAuto = false;
      fanOn = false;
      digitalWrite(FAN_PIN, LOW);
      action = "Fan turned OFF";
      success = true;
    }
    else if (command.indexOf("fan auto") >= 0) {
      fanAuto = true;
      action = "Fan set to auto (temperature)";
      success = true;
    }
    
    responseDoc["success"] = success;
    responseDoc["action"] = action;
    
    String response;
    serializeJson(responseDoc, response);
    
    if (success) {
      Serial.printf("🎤 AI: %s → %s\n", command.c_str(), action.c_str());
      server.sendHeader("Access-Control-Allow-Origin", "*");
      server.send(200, "application/json", response);
    } else {
      server.sendHeader("Access-Control-Allow-Origin", "*");
      server.send(400, "application/json", response);
    }
  } else {
    server.sendHeader("Access-Control-Allow-Origin", "*");
    server.send(400, "application/json", "{\"error\":\"Missing command\"}");
  }
}
