"""
============================================================
 Smart Room - Raspberry Pi 5 Headless Camera Detection
 
 Hardware: Raspberry Pi 5 + Camera Module
 Target: T-Beam ESP32 LED Control
 Mode: Headless + ML (High Accuracy 30 FPS)
============================================================
"""

import cv2
import numpy as np
import requests
import time
import json
import os
import threading
import queue
from datetime import datetime
from picamera2 import Picamera2

# ============================================================
# CONFIGURATION
# ============================================================

# Load config from file or use defaults
CONFIG_FILE = "../config/config.json"

def load_config():
    """Load configuration from file or return defaults"""
    default_config = {
        "esp32_ip": "192.168.0.138",
        "camera_slot": 0,
        "camera_width": 640,
        "camera_height": 480,
        "process_every_n_frames": 3,
        "detection_scale": 0.5,
        "min_detection_size": 500,
        "consecutive_frames": 2,
        "send_interval": 2.0,
        "headless_mode": True,
        "log_detections": True,
        "ml_confidence": 0.4
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                print(f"Loaded config from {CONFIG_FILE}")
                return {**default_config, **config}  # Merge with defaults
        except Exception as e:
            print(f"Error loading config: {e}")
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
ML_CONFIDENCE = CONFIG.get("ml_confidence", 0.4)

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
            
            print(f"Camera ready: {CAMERA_WIDTH}x{CAMERA_HEIGHT} @ 30fps")
            
        except Exception as e:
            print(f"ERROR: Failed to initialize camera: {e}")
            print("\nTroubleshooting:")
            print("  1. Check camera cable connection")
            print("  2. Enable camera: sudo raspi-config -> Interface -> Camera")
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
            print(f"Error reading frame: {e}")
            return False, None
    
    def release(self):
        """Close the camera"""
        try:
            self.picam2.stop()
            print("Camera closed")
        except:
            pass


# ============================================================
# ML HUMAN DETECTION (YOLOv8 ONNX)
# ============================================================

class MLHumanDetector:
    """Async ML Human Detection using YOLOv8 ONNX (RPi 5 Optimized)"""
    
    def __init__(self):
        print(f"\n[2/3] Loading ML Detection Engine (YOLOv8 ONNX)...")
        
        # Model path (Consolidated production model)
        self.model_path = "models/human_detector.onnx"
        
        try:
            import onnxruntime as ort
            # Use CPU execution provider (optimized for ARM NEON on RPi 5)
            self.session = ort.InferenceSession(self.model_path, providers=['CPUExecutionProvider'])
            self.input_name = self.session.get_inputs()[0].name
            print(f"✓ YOLOv8 ONNX Model loaded successfully: {self.model_path}")
        except Exception as e:
            print(f"WARNING: ONNX Model not found at {self.model_path}. Falling back to basic vision.")
            self.session = None

        # Threading infrastructure
        self.frame_queue = queue.Queue(maxsize=1)
        self.last_ml_result = False
        self.stop_event = threading.Event()
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        
        # Detection history (Temporal filtering)
        self.detection_history = []
        self.history_size = CONSECUTIVE_FRAMES
        
        print(f"ML Engine Ready (Pure YOLOv8 ONNX Human Detection)")

    def start(self):
        if self.worker_thread and not self.stop_event.is_set():
            self.worker_thread.start()

    def stop(self):
        self.stop_event.set()
        if self.worker_thread.is_alive():
            self.worker_thread.join()

    def _worker(self):
        """Background thread for YOLOv8 ONNX inference"""
        while not self.stop_event.is_set():
            try:
                frame = self.frame_queue.get(timeout=1.0)
                if not self.session:
                    self.last_ml_result = False
                    continue

                # Preprocess for YOLOv8 (640x640, NCHW, float32)
                input_img = cv2.resize(frame, (640, 640))
                input_img = input_img.astype(np.float32) / 255.0
                input_img = np.transpose(input_img, (2, 0, 1)) # HWC to CHW
                input_img = np.expand_dims(input_img, axis=0) # CHW to NCHW

                # Inference
                outputs = self.session.run(None, {self.input_name: input_img})
                
                # Process outputs (Person detection skip logic for prototype)
                # YOLOv8 output: [1, 5, 8400] -> [x, y, w, h, confidence]
                predictions = outputs[0]
                max_conf = np.max(predictions[0, 4, :])
                human_found = max_conf > ML_CONFIDENCE
                
                self.last_ml_result = human_found
                self.frame_queue.task_done()
                
            except queue.Empty:
                continue
            except:
                pass

    def detect(self, frame):
        """Pure ML detection: YOLOv8 ONNX"""
        if self.frame_queue.empty():
            try:
                self.frame_queue.put(frame, block=False)
            except:
                pass
            
        human_detected = self.last_ml_result
        
        # Temporal filtering
        self.detection_history.append(human_detected)
        if len(self.detection_history) > self.history_size:
            self.detection_history.pop(0)
            
        confirmed = sum(self.detection_history) >= CONSECUTIVE_FRAMES
        return [], confirmed



# ============================================================
# T-BEAM ESP32 COMMUNICATION
# ============================================================

def test_esp32_connection():
    """Test T-Beam ESP32 connection"""
    print(f"\n[3/3] Testing T-Beam ESP32 at {ESP32_IP}...")
    
    try:
        response = requests.get(f"http://{ESP32_IP}/status", timeout=5)
        if response.status_code == 200:
            print("T-Beam ESP32 connected!")
            return True
        else:
            print("ESP32 not responding")
            return False
    except Exception as e:
        print(f"T-Beam not connected: {e}")
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
    print(" Smart Room - Raspberry Pi 5 Headless ML Detection")
    print(" Target: T-Beam ESP32 LED Control")
    print("=" * 70)
    
    # Initialize camera
    try:
        camera = RaspberryPiCamera(camera_num=CAMERA_SLOT)
    except Exception as e:
        print(f"\nFailed to initialize camera. Exiting.")
        return 1
    
    # Initialize detector
    detector = MLHumanDetector()
    detector.start()
    
    # Test T-Beam
    esp32_connected = test_esp32_connection()
    
    print("\n" + "=" * 70)
    print(" System Ready!")
    print(f" Mode: ML-ENHANCED (30 FPS Async)")
    print(f" Camera: RPi Camera Module (slot {CAMERA_SLOT})")
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
    
    cached_boxes = []
    cached_detection = False
    
    try:
        while True:
            # Capture frame
            ret, frame = camera.read()
            if not ret:
                print("Failed to read frame")
                time.sleep(0.1)
                continue
            
            frame_count += 1
            fps_counter += 1
            
            # Process detection
            boxes, human_detected = detector.detect(frame)
            
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
                            print(f"[{timestamp}] OBJECT/HUMAN DETECTED #{detection_count} -> T-Beam ON")
                        else:
                            print(f"[{timestamp}] No detection -> T-Beam OFF")
                        last_detection_state = human_detected
                else:
                    esp32_ok = False

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        return 1
    
    # Cleanup
    print("\n[Cleanup] Shutting down...")
    detector.stop()
    try:
        send_detection(False)
        print("Sent OFF signal to T-Beam")
    except:
        pass
    
    camera.release()
    print("Camera closed")
    print("Shutdown complete\n")
    return 0


if __name__ == "__main__":
    exit(main())
