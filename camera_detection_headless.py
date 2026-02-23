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
CONFIG_FILE = "config.json"

def load_config():
    """Load configuration from file or return defaults"""
    default_config = {
        "esp32_ip": "192.168.0.138",
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
            print("  2. Enable camera: sudo raspi-config \u2192 Interface \u2192 Camera")
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
            print("\u2713 Camera closed")
        except:
            pass


# ============================================================
# HYBRID HUMAN DETECTION
# ============================================================

class FastHumanDetector:
    """Hybrid human detection using HOG, Haar Cascades, and Motion Blobs"""
    
    def __init__(self):
        print(f"\n[2/3] Loading hybrid detection engine...")
        
        # 1. HOG People Detector (Standard for body shapes)
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        
        # 2. Haar Cascades (Better for faces and upper bodies)
        cascade_path = self._find_haarcascades()
        self.face_cascade = cv2.CascadeClassifier(os.path.join(cascade_path, 'haarcascade_frontalface_default.xml'))
        self.upper_body_cascade = cv2.CascadeClassifier(os.path.join(cascade_path, 'haarcascade_upperbody.xml'))
        
        # 3. Background Subtraction (For pose invariance/any position)
        self.back_sub = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=16, detectShadows=False)
        
        # 4. CLAHE for light normalization
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        
        # Detection history
        self.detection_history = []
        self.history_size = CONSECUTIVE_FRAMES
        
        print(f"\u2713 Hybrid engine ready (HOG + Haar + MOG2 + NMS)")
        
    def _find_haarcascades(self):
        if hasattr(cv2, 'data') and hasattr(cv2.data, 'haarcascades'):
            return cv2.data.haarcascades
        paths = ['/usr/share/opencv4/haarcascades/', '/usr/share/opencv/haarcascades/']
        for p in paths:
            if os.path.exists(p): return p
        return ""

    def _nms(self, boxes, overlapThresh=0.3):
        """Non-Maximum Suppression to merge overlapping boxes"""
        if len(boxes) == 0: return []
        boxes = np.array(boxes)
        pick = []
        if len(boxes.shape) == 1: boxes = np.array([boxes])
        x1, y1 = boxes[:,0], boxes[:,1]
        x2, y2 = x1 + boxes[:,2], y1 + boxes[:,3]
        area = (x2 - x1 + 1) * (y2 - y1 + 1)
        idxs = np.argsort(y2)
        while len(idxs) > 0:
            last = len(idxs) - 1
            i = idxs[last]
            pick.append(i)
            xx1 = np.maximum(x1[i], x1[idxs[:last]])
            yy1 = np.maximum(y1[i], y1[idxs[:last]])
            xx2 = np.minimum(x2[i], x2[idxs[:last]])
            yy2 = np.minimum(y2[i], y2[idxs[:last]])
            w = np.maximum(0, xx2 - xx1 + 1)
            h = np.maximum(0, yy2 - yy1 + 1)
            overlap = (w * h) / area[idxs[:last]]
            idxs = np.delete(idxs, np.concatenate(([last], np.where(overlap > overlapThresh)[0])))
        return boxes[pick].tolist()

    def detect(self, frame):
        """Hybrid detection: HOG + Haar + Motion Blobs"""
        # Resize and Preprocess
        small_frame = cv2.resize(frame, None, fx=DETECTION_SCALE, fy=DETECTION_SCALE)
        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
        gray = self.clahe.apply(gray) # Light normalization
        
        all_boxes = []
        
        # A. HOG Detection (Standard humans)
        hog_boxes, _ = self.hog.detectMultiScale(gray, winStride=(8,8), padding=(8,8), scale=1.05)
        for (x, y, w, h) in hog_boxes:
            all_boxes.append((int(x), int(y), int(w), int(h)))
            
        # B. Haar Face & Upper Body (Seated/Close-up)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(30, 30))
        for (x, y, w, h) in faces:
            all_boxes.append((int(x), int(y), int(w), int(h)))
            
        upper = self.upper_body_cascade.detectMultiScale(gray, 1.1, 3, minSize=(40, 40))
        for (x, y, w, h) in upper:
            all_boxes.append((int(x), int(y), int(w), int(h)))
            
        # C. MOG2 Motion Blobs (Any position/Lying down fallback)
        fg_mask = self.back_sub.apply(small_frame)
        _, thresh = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for cnt in contours:
            if cv2.contourArea(cnt) > (MIN_DETECTION_SIZE * DETECTION_SCALE * DETECTION_SCALE):
                all_boxes.append(cv2.boundingRect(cnt))
        
        # D. Clean up
        merged_boxes = self._nms(all_boxes)
        
        # Scale back
        scale_back = 1.0 / DETECTION_SCALE
        final_boxes = []
        for (x, y, w, h) in merged_boxes:
            final_boxes.append((int(x*scale_back), int(y*scale_back), int(w*scale_back), int(h*scale_back)))
        
        # Temporal filtering
        is_detected = len(final_boxes) > 0
        self.detection_history.append(is_detected)
        if len(self.detection_history) > self.history_size:
            self.detection_history.pop(0)
            
        confirmed = sum(self.detection_history) >= CONSECUTIVE_FRAMES
        return final_boxes, confirmed


# ============================================================
# T-BEAM ESP32 COMMUNICATION
# ============================================================

def test_esp32_connection():
    """Test T-Beam ESP32 connection"""
    print(f"\n[3/3] Testing T-Beam ESP32 at {ESP32_IP}...")
    
    try:
        response = requests.get(f"http://{ESP32_IP}/status", timeout=5)
        if response.status_code == 200:
            print("\u2713 T-Beam ESP32 connected!")
            return True
        else:
            print("\u26a0 ESP32 not responding")
            return False
    except Exception as e:
        print(f"\u26a0 T-Beam not connected: {e}")
        print("  Camera will run anyway, retrying connection in background")
        return False


def send_detection(detected):
    """Send detection to T-Beam ESP32"""
    try:
        url = f"http://{ESP32_IP}/camera/human"
        data = {"detected": "true" if detected else "false"}
        response = requests.post(url, data=data, timeout=5)
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
        print(f"\n\u274c Failed to initialize camera. Exiting.")
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
                print("\u274c Failed to read frame")
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
                if frame_count % 300 == 0:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] FPS: {fps:.1f} | Detections: {detection_count}")
            
            # Retry ESP32 connection
            current_time = time.time()
            if not esp32_ok and current_time - esp32_retry_time >= 30:
                esp32_retry_time = current_time
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Retrying T-Beam connection...")
                esp32_ok = test_esp32_connection()
            
            # Send to T-Beam
            if current_time - last_send_time >= SEND_INTERVAL:
                last_send_time = current_time
                success = send_detection(human_detected)
                
                if success:
                    esp32_ok = True
                    if human_detected != last_detection_state and LOG_DETECTIONS:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        if human_detected:
                            detection_count += 1
                            print(f"[{timestamp}] \ud83d\udc64 HUMAN #{detection_count} \u2192 T-Beam: LED ON")
                        else:
                            print(f"[{timestamp}] \ud83d\udeab No human \u2192 T-Beam: LED OFF")
                        last_detection_state = human_detected
                else:
                    esp32_ok = False

    except KeyboardInterrupt:
        print("\n\u23f8 Interrupted by user")
    except Exception as e:
        print(f"\n\u274c Error: {e}")
        return 1
    
    # Cleanup
    print("\n[Cleanup] Shutting down...")
    try:
        send_detection(False)
        print("\u2713 Sent OFF signal to T-Beam")
    except:
        pass
    
    camera.release()
    print("\u2713 Camera closed")
    print("\u2713 Shutdown complete\n")
    return 0


if __name__ == "__main__":
    exit(main())
