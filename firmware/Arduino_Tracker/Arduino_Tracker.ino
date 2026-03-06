/*
 * Smart Room - Arduino Ultrasonic + Servo Tracker
 * 
 * Hardware: Arduino Uno
 *           HC-SR04 Ultrasonic Sensor
 *           Servo Motor (e.g. SG90 / MG996R)
 * 
 * Function: Sweeps left to right continuously.
 *           If an object is within 100cm (1m), it stops.
 *           Includes anti-shake deadzone: only follows if the person moves >4cm.
 */

#include <Servo.h>

const int TRIG_PIN = 5;
const int ECHO_PIN = 6;
const int SERVO_PIN = 9;

// --- NEW LOGIC GLOBALS ---
const int MOVEMENT_THRESHOLD = 5; // cm threshold to consider as "moving"
const unsigned long LOCK_DURATION = 5000; // 5 seconds
unsigned long lockStartTime = 0;

// --- USER PREFERENCES ---
const int DETECT_RANGE_CM = 100; // <--- Changed from 300 to 100 (1 meter)
const int SWEEP_STEP = 5;
const int SWEEP_DELAY_MS = 50;

Servo scannerServo;
int pos = 90;
int sweepDir = 1;

bool isTracking = false;
int lostFrames = 0;
float lastTrackDist = -1.0; 

void setup() {
  Serial.begin(115200);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  
  scannerServo.attach(SERVO_PIN);
  scannerServo.write(pos);
  delay(1000); // Settle time
  Serial.println("Arduino Tracker Ready");
}

float measureDistanceCM() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  
  // Timeout 25000us ~ 4.2 meters max range
  long duration = pulseIn(ECHO_PIN, HIGH, 25000);
  
  if (duration == 0) {
    return -1.0; // Out of range or no echo
  }
  
  // Distance in cm
  return (duration * 0.0343) / 2.0;
}

void loop() {
  if (!isTracking) {
    // ----------------------------------------------------
    // 1. SWEEPING STATE (Detects ONLY if moving)
    // ----------------------------------------------------
    static int lastPos = -1;
    
    pos += (sweepDir * SWEEP_STEP);
    if (pos >= 90) { pos = 90; sweepDir = -1; }
    else if (pos <= 0) { pos = 0; sweepDir = 1; }
    
    scannerServo.write(pos);
    delay(SWEEP_DELAY_MS);
    
    // Movement check: Sample 1
    float dist1 = measureDistanceCM();
    delay(100); // Wait 100ms to see if object moved
    // Movement check: Sample 2
    float dist2 = measureDistanceCM();
    
    // Condition: Within 1m AND the distance changed significantly (Movement)
    if (dist1 > 0 && dist1 <= DETECT_RANGE_CM && 
        dist2 > 0 && dist2 <= DETECT_RANGE_CM &&
        abs(dist1 - dist2) >= MOVEMENT_THRESHOLD) {
      
      Serial.print("Detection -> Moving object at ");
      Serial.print(pos); Serial.println(" deg. Locking for 5s...");
      
      isTracking = true;
      lockStartTime = millis();
    }
    
  } else {
    // ----------------------------------------------------
    // 2. LOCK STATE (Wait 5s, then re-check movement)
    // ----------------------------------------------------
    
    // Check if 5 seconds have passed
    if (millis() - lockStartTime >= LOCK_DURATION) {
      Serial.println("Lock -> 5s passed. Checking for movement...");
      
      float d1 = measureDistanceCM();
      delay(200);
      float d2 = measureDistanceCM();
      
      if (abs(d1 - d2) >= MOVEMENT_THRESHOLD && d1 > 0 && d1 <= DETECT_RANGE_CM) {
        // Still moving! Stay another 5 seconds
        Serial.println("Lock -> Movement detected! Staying 5 more seconds.");
        lockStartTime = millis(); 
      } else {
        // Stationary or gone. Resume sweep.
        Serial.println("Lock -> No movement. Resuming sweep.");
        isTracking = false;
        delay(500); // Small pause before sweeping
      }
    } else {
      // Still in the 5-second waiting window
      // We don't move the motor here, keeping it locked at 'pos'
      delay(100); 
    }
  }
}