# 🏠 Smart Room: Edge-AI & IoT Ecosystem

Welcome to the **Smart Room** project—a deep integration of high-performance Edge Computer Vision, localized Large Language Models (LLMs), and responsive IoT hardware. This system transforms a standard room into an intelligent, adaptive environment that detects people, optimizes climate, and responds to natural language commands.

---

## 🏗️ Project Architecture

The system is built as a decentralized modular ecosystem, distributing compute-heavy tasks to specialized nodes:

1.  **Vision Node (Raspberry Pi 5)**: High-FPS human detection using YOLOv8 ONNX.
2.  **Control Node (LilyGO T-Beam)**: ESP32-based sensor acquisition and climate control.
3.  **Tracking Node (Arduino Uno)**: Ultrasonic-based mechanical servo tracking.
4.  **Intelligence Hub (Flask Server)**: Local LLM (Ollama) and ML Climate Optimizer.
5.  **User Interface (PWA)**: A modern, real-time glassmorphism dashboard.

---

## 📂 Directory Structure

```text
Smart_Room/
├── vision/                 # [RPi 5] Edge AI Computer Vision
│   ├── models/             # YOLOv8 ONNX production weights
│   ├── vision_training/    # Jupyter notebooks & training scripts
│   └── camera_detection_headless.py  # Main RPi 5 detection service
├── web_app/                # [HPC/PC] Backend & UI Dashboard
│   ├── server.py           # Unified Flask hub & AI proxy
│   ├── ml_optimizer.py     # Gradient Boosting climate predictor
│   └── index.html          # PWA frontend (Glassmorphism UI)
├── firmware/               # [MCU] Hardware Controller Code
│   ├── LilyGO_TBeam/       # Main ESP32 control firmware
│   └── Arduino_Tracker/    # Uno-based ultrasonic servo tracking
├── config/                 # Shared system configurations
├── docs/                   # Reports, manuals, and project assets
└── backups/                # Legacy codes and training history
```

---

## 🔍 Codebase Deep Dive

### 1. High-Performance Vision (`vision/`)
**File:** `camera_detection_headless.py`
*   **Purpose**: Runs on the Raspberry Pi 5 to provide real-time human detection via the camera module.
*   **Key Logic**:
    *   **YOLOv8 ONNX**: Uses `onnxruntime` with ARM NEON optimization to achieve **30 FPS**.
    *   **Temporal Filtering**: Detections must be confirmed over multiple frames before alerting the system, preventing flickering.
    *   **Communication**: Sends detection status to the T-Beam via asynchronous HTTP POST requests.

### 2. The Main Controller (`firmware/LilyGO_TBeam/`)
**File:** `esp32_analogwrite_final.ino`
*   **Purpose**: Manages sensors (DHT11, LDR, PIR) and actuators (Fan, LED, Blinds).
*   **Key Functions**:
    *   `loop()`: Constantly polls sensors and handles incoming API requests from the Web App and RPi.
    *   `updateLED()`: Implements "Smart Lighting"—Bright when a human is detected, Dim otherwise.
    *   `updateBlindsAuto()`: Automatically opens/closes blinds based on LDR light levels (Lux).
    *   `handleAICommand()`: A mini command-parser that executes actions (like "Turn on fan") sent from the LLM.

### 3. The Backend Hub (`web_app/`)
**File:** `server.py`
*   **Purpose**: Acts as a secure HTTPS proxy and integrates the AI brains.
*   **Key Logic**:
    *   **Reverse Proxy**: Routes frontend commands to the local IP of the T-Beam, resolving CORS and mixed-content issues.
    *   **LLM Integration**: Merges live room status into the AI prompt, giving the Assistant "eyes" and "ears" into the room's current state.
    *   **ML Integration**: Connects to the climate optimizer to provide predictive temp suggestions.

**File:** `ml_optimizer.py`
*   **Purpose**: Predicts the "Perfect Room Temperature" using a Gradient Boosting Regressor.
*   **Functionality**:
    *   `predict_optimal_temp()`: Fetches current outdoor weather (Open-Meteo) and pairs it with indoor light levels to run an inference against the trained `.pkl` model.
    *   `log_user_preference()`: Captures manual overrides to enable continuous learning.

### 4. Servo Tracker (`firmware/Arduino_Tracker/`)
**File:** `Arduino_Tracker.ino`
*   **Purpose**: Standalone tracking system for the camera/sensor pod.
*   **Key Logic**:
    *   **Sweep & Lock**: Sweeps 180° until an object is detected within 1m by the Ultrasonic sensor.
    *   **Anti-Shake Deadzone**: Only physically repositions the servo if the person moves more than 4cm, preventing annoying mechanical jitter.

### 5. Frontend Dashboard (`web_app/index.html`)
*   **Purpose**: A Progressive Web App that provides a premium, responsive glassmorphism UI.
*   **Features**:
    *   **Live Metrics**: Auto-polling every 2 seconds for real-time sensor updates.
    *   **AI Chat**: Local streaming chat interface for natural language room control.
    *   **Voice Control**: Integrated web-speech APIs for hands-free operation.

---

## ⚡ Deployment Quick Start

1.  **Hardware**: Flash the T-Beam and Arduino Uno with their respective `.ino` files.
2.  **Vision Node**: Deploy the `vision/` folder to your Raspberry Pi 5 and enable the `smart-room-camera.service`.
3.  **Backend**: Run `python web_app/server.py` on your main computer/hub.
4.  **UI**: Access the dashboard via `http://localhost:8000` or your local IP.

---
*Created with ❤️ by Antigravity AI for the Smart Room Project.*
