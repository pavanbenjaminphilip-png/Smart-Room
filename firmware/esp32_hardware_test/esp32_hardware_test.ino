/*
 * ============================================================
 * ESP32 HARDWARE COMPONENT DIAGNOSTIC TEST
 * ============================================================
 * Use this sketch to isolate and test each physical component
 * attached to the ESP32. This skips WiFi and Web Servers to 
 * verify that the wiring and sensors are working correctly.
 * 
 * Instructions:
 * 1. Upload this code to the ESP32.
 * 2. Open the Serial Monitor (Baud Rate: 115200).
 * 3. The ESP32 will automatically cycle through tests for 
 *    the LED, Fan Relay, Stepper Motor, PIR, DHT, and LDR.
 * ============================================================
 */

#include <DHT.h>
#include <Stepper.h>

// Pin Definitions
#define LED_PIN 25
#define FAN_PIN 13
#define PIR_PIN 21
#define LDR_PIN 33
#define DHT_PIN 14
#define DHT_TYPE DHT11 // Change to DHT22 if using DHT22

// Stepper Motor Pins
#define STEPPER_IN1 35
#define STEPPER_IN2 15
#define STEPPER_IN3 4
#define STEPPER_IN4 23

#define STEPS_PER_REV 2048
#define STEPPER_SPEED 10

// Objects
DHT dht(DHT_PIN, DHT_TYPE);
Stepper stepperMotor(STEPS_PER_REV, STEPPER_IN1, STEPPER_IN3, STEPPER_IN2, STEPPER_IN4);

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n=================================");
  Serial.println("  ESP32 HARDWARE DIAGNOSTICS");
  Serial.println("=================================");

  // Initialize Pins
  pinMode(LED_PIN, OUTPUT);
  pinMode(FAN_PIN, OUTPUT);
  pinMode(PIR_PIN, INPUT);
  // LDR_PIN is for analogRead, no pinMode needed strictly, but good practice
  pinMode(LDR_PIN, INPUT); 

  // Initialize DHT
  dht.begin();
  
  // Initialize Stepper
  stepperMotor.setSpeed(STEPPER_SPEED);
  
  Serial.println("Init complete. Starting tests...\n");
}

void loop() {
  // ---------------------------------------------------------
  // 1. TEST LED (Analog Write / PWM)
  // ---------------------------------------------------------
  Serial.println("\n--- 1. Testing LED (PWM on Pin 25) ---");
  Serial.println("Fading UP...");
  for(int i = 0; i <= 255; i += 5) {
    analogWrite(LED_PIN, i);
    delay(20);
  }
  Serial.println("Fading DOWN...");
  for(int i = 255; i >= 0; i -= 5) {
    analogWrite(LED_PIN, i);
    delay(20);
  }
  analogWrite(LED_PIN, 0); // Ensure it's off
  delay(1000);

  // ---------------------------------------------------------
  // 2. TEST FAN RELAY
  // ---------------------------------------------------------
  Serial.println("\n--- 2. Testing Fan Relay (Pin 13) ---");
  Serial.println("Fan ON");
  digitalWrite(FAN_PIN, HIGH);
  delay(3000);
  Serial.println("Fan OFF");
  digitalWrite(FAN_PIN, LOW);
  delay(1000);

  // ---------------------------------------------------------
  // 3. TEST DHT11/22 SENSOR
  // ---------------------------------------------------------
  Serial.println("\n--- 3. Testing DHT Sensor (Pin 14) ---");
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  if (isnan(h) || isnan(t)) {
    Serial.println("❌ ERROR: Failed to read from DHT sensor! Check wiring.");
  } else {
    Serial.print("✅ Temperature: ");
    Serial.print(t);
    Serial.print("°C  |  Humidity: ");
    Serial.print(h);
    Serial.println("%");
  }
  delay(1000);

  // ---------------------------------------------------------
  // 4. TEST LDR (Light Sensor)
  // ---------------------------------------------------------
  Serial.println("\n--- 4. Testing LDR / Light Sensor (Pin 33) ---");
  int lightVal = analogRead(LDR_PIN);
  Serial.print("✅ Light Level (0 - 4095): ");
  Serial.println(lightVal);
  if (lightVal == 0 || lightVal >= 4095) {
    Serial.println("⚠️ Warning: Value is extreme, check LDR resistor wiring if this is indoors.");
  }
  delay(1000);

  // ---------------------------------------------------------
  // 5. TEST PIR MOTION SENSOR
  // ---------------------------------------------------------
  Serial.println("\n--- 5. Testing PIR Motion Sensor (Pin 21) ---");
  Serial.print("Motion State: ");
  int motion = digitalRead(PIR_PIN);
  if (motion == HIGH) {
    Serial.println("✅ Motion DETECTED (HIGH)");
  } else {
    Serial.println("✅ No motion (LOW)");
  }
  delay(1000);

  // ---------------------------------------------------------
  // 6. TEST STEPPER MOTOR
  // ---------------------------------------------------------
  Serial.println("\n--- 6. Testing Stepper Motor ---");
  Serial.println("Opening Blinds (moving 500 steps forward)...");
  stepperMotor.step(500);
  delay(500);
  
  Serial.println("Closing Blinds (moving 500 steps backward)...");
  stepperMotor.step(-500);
  delay(500);
  
  // De-energize coils to prevent heating
  digitalWrite(STEPPER_IN1, LOW);
  digitalWrite(STEPPER_IN2, LOW);
  digitalWrite(STEPPER_IN3, LOW);
  digitalWrite(STEPPER_IN4, LOW);
  
  Serial.println("Stepper coils powered off.");
  
  Serial.println("\n=================================");
  Serial.println("  END OF TEST CYCLE. Restarting in 5s...");
  Serial.println("=================================\n");
  delay(5000);
}
