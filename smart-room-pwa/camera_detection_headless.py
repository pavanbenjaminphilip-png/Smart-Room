"""
============================================================
 Smart Room - Raspberry Pi 5 Headless Camera Detection
 
 Hardware: Raspberry Pi 5 + Camera Module
 Target: T-Beam ESP32 LED Control
 Mode: Headless (no display required)
============================================================
"""

import cv2
import numpy as np
import requests
import time
import json
import os
from datetime import datetime
from picamera2 import Picamera2

# ============================================================
# CONFIGURATION
# ============================================================

# Load config from file or use defaults
CONFIG_FILE = "/home/pi/smart-room/config.json"

def load_config():
    """Load configuration from file or return defaults"""
    default_config = {
        "esp32_ip": "192.168.0.178",
        "camera_slot": 0,
        "camera_width": 640,
        "camera_height": 480,
        "process_every_n_frames": 3,
        "detection_scale": 0.5,
        "min_detection_size": 2000,
        "consecutive_frames": 2,
        "send_interval": 2.0,
        "headless_mode": True,
        "log_detections": True
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                print(f"✓ Loaded config from {CONFIG_FILE}")
                return {**default_config, **config}  # Merge with defaults
        except Exception as e:
            print(f"⚠ Error loading config: {e}")
            print("  Using default configuration")
    
    return default_config

# Load configuration
CONFIG = load_config()

ESP32_IP = CONFIG["esp32_ip"]
CAMERA_SLOT = CONFIG["camera_slot"]
CAMERA_WIDTH = CONFIG["camera_width"]
CAMERA_HEIGHT = CONFIG["camera_height"]
PROCESS_EVERY_N_FRAMES = CONFIG["process_every_n_frames"]
DETECTION_SCALE = CONFIG["detection_scale"]
MIN_DETECTION_SIZE = CONFIG["min_detection_size"]
CONSECUTIVE_FRAMES = CONFIG["consecutive_frames"]
SEND_INTERVAL = CONFIG["send_interval"]
HEADLESS_MODE = CONFIG["headless_mode"]
LOG_DETECTIONS = CONFIG["log_detections"]

# ============================================================
# RASPBERRY PI CAMERA
# ============================================================

class RaspberryPiCamera:
    """Raspberry Pi 5 Camera Module interface using picamera2"""
    
    def __init__(self, camera_num=0):
        print(f"\n[1/3] Initializing RPi Camera (slot {camera_num})...")
        
        try:
            # Initialize Picamera2
            self.picam2 = Picamera2(camera_num)
            
            # Configure for optimal performance
            config = self.picam2.create_preview_configuration(
                main={
                    "size": (CAMERA_WIDTH, CAMERA_HEIGHT),
                    "format": "RGB888"
                },
                controls={
                    "FrameRate": 30,
                }
            )
            
            self.picam2.configure(config)
            self.picam2.start()
            
            # Camera warmup
            time.sleep(2)
            
            # Test capture
            frame = self.picam2.capture_array()
            
            if frame is None or frame.size == 0:
                raise Exception("Failed to capture test frame")
            
            print(f"✓ Camera ready: {CAMERA_WIDTH}x{CAMERA_HEIGHT} @ 30fps")
            
        except Exception as e:
            print(f"❌ ERROR: Failed to initialize camera: {e}")
            print("\nTroubleshooting:")
            print("  1. Check camera cable connection")
            print("  2. Enable camera: sudo raspi-config → Interface → Camera")
            print("  3. Install picamera2: sudo apt install -y python3-picamera2")
            print("  4. Reboot: sudo reboot")
            raise
    
    def read(self):
        """Capture a frame from the camera"""
        try:
            frame = self.picam2.capture_array()
            # picamera2 returns RGB, convert to BGR for OpenCV
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            return True, frame_bgr
        except Exception as e:
            print(f"❌ Error reading frame: {e}")
            return False, None
    
    def release(self):
        """Close the camera"""
        try:
            self.picam2.stop()
            print("✓ Camera closed")
        except:
            pass


# ============================================================
# HUMAN DETECTION
# ============================================================

class FastHumanDetector:
    """Optimized human detection using HAAR Cascades"""
    
    def __init__(self):
        print(f"\n[2/3] Loading detection model...")
        
        # Use Haar Cascade (fast and efficient for RPi)
        self.body_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_upperbody.xml'
        )
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        # Detection history for temporal filtering
        self.detection_history = []
        self.history_size = CONSECUTIVE_FRAMES
        
        print(f"✓ Detection model loaded")
    
    def detect(self, frame):
        """Fast human detection with frame scaling"""
        
        # Resize for faster processing
        small_frame = cv2.resize(frame, None, fx=DETECTION_SCALE, fy=DETECTION_SCALE)
        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        
        # Detect upper bodies
        bodies = self.body_cascade.detectMultiScale(
            gray,
            scaleFactor=1.15,
            minNeighbors=2,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.2,
            minNeighbors=3,
            minSize=(20, 20),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        # Scale back to original size
        scale_back = 1.0 / DETECTION_SCALE
        boxes = []
        
        for (x, y, w, h) in bodies:
            x, y, w, h = int(x*scale_back), int(y*scale_back), int(w*scale_back), int(h*scale_back)
            if w * h >= MIN_DETECTION_SIZE:
                boxes.append((x, y, w, h))
        
        for (x, y, w, h) in faces:
            x, y, w, h = int(x*scale_back), int(y*scale_back), int(w*scale_back*2), int(h*scale_back*2)
            if w * h >= MIN_DETECTION_SIZE:
                boxes.append((x, y, w, h))
        
        # Temporal filtering (reduce false positives)
        detected = len(boxes) > 0
        self.detection_history.append(detected)
        
        if len(self.detection_history) > self.history_size:
            self.detection_history.pop(0)
        
        # Confirm detection only if seen in multiple consecutive frames
        confirmed = sum(self.detection_history) >= CONSECUTIVE_FRAMES
        
        return boxes, confirmed


# ============================================================
# T-BEAM ESP32 COMMUNICATION
# ============================================================

def test_esp32_connection():
    """Test T-Beam ESP32 connection"""
    print(f"\n[3/3] Testing T-Beam ESP32 at {ESP32_IP}...")
    
    try:
        response = requests.get(f"http://{ESP32_IP}/status", timeout=2)
        if response.status_code == 200:
            print("✓ T-Beam ESP32 connected!")
            return True
        else:
            print("⚠ ESP32 not responding")
            return False
    except Exception as e:
        print(f"⚠ T-Beam not connected: {e}")
        print("  Camera will run anyway, retrying connection in background")
        return False


def send_detection(detected):
    """Send detection to T-Beam ESP32"""
    try:
        url = f"http://{ESP32_IP}/camera/human"
        data = {"detected": "true" if detected else "false"}
        response = requests.post(url, data=data, timeout=1)
        return response.status_code == 200
    except:
        return False


# ============================================================
# MAIN LOOP
# ============================================================

def main():
    print("=" * 70)
    print(" Smart Room - Raspberry Pi 5 Headless Camera Detection")
    print(" Target: T-Beam ESP32 LED Control")
    print("=" * 70)
    
    # Initialize camera
    try:
        camera = RaspberryPiCamera(camera_num=CAMERA_SLOT)
    except Exception as e:
        print(f"\n❌ Failed to initialize camera. Exiting.")
        return 1
    
    # Initialize detector
    detector = FastHumanDetector()
    
    # Test T-Beam
    esp32_connected = test_esp32_connection()
    
    print("\n" + "=" * 70)
    print(" System Ready!")
    print(f" Mode: HEADLESS (no display)")
    print(f" Camera: RPi Camera Module (slot {CAMERA_SLOT})")
    print(f" Resolution: {CAMERA_WIDTH}x{CAMERA_HEIGHT}")
    print(f" Processing: Every {PROCESS_EVERY_N_FRAMES} frames @ {DETECTION_SCALE*100:.0f}% scale")
    print(f" Target: T-Beam ESP32 @ {ESP32_IP}")
    print("\n Press Ctrl+C to stop")
    print("=" * 70 + "\n")
    
    # Main loop variables
    last_send_time = 0
    last_detection_state = False
    frame_count = 0
    detection_count = 0
    esp32_retry_time = 0
    esp32_ok = esp32_connected
    
    # FPS tracking
    fps_start = time.time()
    fps_counter = 0
    fps = 0
    
    # Cache detection results
    cached_boxes = []
    cached_detection = False
    
    try:
        while True:
            # Capture frame
            ret, frame = camera.read()
            if not ret:
                print("❌ Failed to read frame")
                time.sleep(0.1)
                continue
            
            frame_count += 1
            fps_counter += 1
            
            # Process detection every N frames
            if frame_count % PROCESS_EVERY_N_FRAMES == 0:
                boxes, human_detected = detector.detect(frame)
                cached_boxes = boxes
                cached_detection = human_detected
            else:
                # Use cached results
                boxes = cached_boxes
                human_detected = cached_detection
            
            # Calculate FPS
            elapsed = time.time() - fps_start
            if elapsed >= 1.0:
                fps = fps_counter / elapsed
                fps_start = time.time()
                fps_counter = 0
                # Print FPS every 10 seconds in headless mode
                if frame_count % 300 == 0:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] FPS: {fps:.1f} | Detections: {detection_count}")
            
            # Retry ESP32 connection if failed
            current_time = time.time()
            if not esp32_ok and current_time - esp32_retry_time >= 30:
                esp32_retry_time = current_time
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Retrying T-Beam connection...")
                esp32_ok = test_esp32_connection()
            
            # Send to T-Beam every SEND_INTERVAL seconds
            if current_time - last_send_time >= SEND_INTERVAL:
                last_send_time = current_time
                
                success = send_detection(human_detected)
                
                if success:
                    esp32_ok = True
                    if human_detected != last_detection_state and LOG_DETECTIONS:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        if human_detected:
                            detection_count += 1
                            print(f"[{timestamp}] 👤 HUMAN #{detection_count} → T-Beam: LED ON")
                        else:
                            print(f"[{timestamp}] 🚫 No human → T-Beam: LED OFF")
                        last_detection_state = human_detected
                else:
                    esp32_ok = False

    except KeyboardInterrupt:
        print("\n⏸ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
    
    # Cleanup
    print("\n[Cleanup] Shutting down...")
    try:
        send_detection(False)  # Turn off LED
        print("✓ Sent OFF signal to T-Beam")
    except:
        pass
    
    camera.release()
    print("✓ Camera closed")
    print("✓ Shutdown complete\n")
    return 0


if __name__ == "__main__":
    exit(main())
