# 🏠 Smart Room: Local AI & Multi-Agent Ecosystem

A high-performance, privacy-first smart room automation system. This project integrates local LLMs (Llama 3.2), computer vision (Raspberry Pi 5), and distributed hardware (ESP32) into a unified, voice-controlled ecosystem.

![Project Status](https://img.shields.io/badge/Status-Active-brightgreen)
![Tech](https://img.shields.io/badge/AI-Llama_3.2-blue)
![Platform](https://img.shields.io/badge/Hardware-ESP32_%7C_RPi_5-orange)

## 🌟 Key Features

*   **🧠 Local AI Intelligence**: Fully local interaction using Llama 3.2:1b via Ollama. No data leaves your room.
*   **🗣️ Voice Interface**: Integrated voice input and response for hands-free room control.
*   **👁️ Hybrid Vision System**: Raspberry Pi 5-powered human detection using a high-performance hybrid engine (HOG, Haar Cascades, and MOG2 Background Subtraction).
*   **📱 Modern PWA**: Responsive, installable web dashboard with real-time status monitoring and manual overrides.
*   **📟 Hardware Integration**: ESP32-based control for:
    *   💡 **Lighting**: Analog dimming and mood control.
    *   🌀 **Climate**: Automated fan management based on presence and temperature.
    *   🪟 **Privacy**: Motorized blind control (Open/Close/Auto).
*   **🌉 Unified Server**: A Flask-based proxy hub that handles CORS, security, and multi-device communication.

## 🛠️ Architecture

The system consists of three main "agents" working in harmony:

1.  **Central Hub (PC/Server)**: Runs `server.py` to serve the PWA and proxy requests to Ollama and the ESP32.
2.  **Vision Agent (RPi 5)**: Runs `camera_detection_headless.py` to monitor presence and automate lights/fans.
3.  **Hardware Agent (ESP32)**: Handles physical I/O for sensors and actuators.

## 🚀 Getting Started

### Prerequisites

*   **Ollama**: Install and pull the model: `ollama pull llama3.2:1b`
*   **Python 3.10+**: For the unified server and RPi vision system.
*   **ESP32 Firmware**: Upload the `.ino` code in the `esp32_analogwrite_final` folder.

### Installation

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/YOUR_USERNAME/Smart-Room.git
    cd Smart-Room
    ```

2.  **Install Dependencies**:
    ```bash
    pip install flask requests opencv-python numpy
    ```

3.  **Configuration**:
    Edit `config.json` with your ESP32 IP address and preferred ports.

4.  **Launch the Server**:
    Double-click `START_SERVER.bat` (Windows) or run:
    ```bash
    python server.py
    ```

## 📂 Project Structure

*   `server.py`: The heart of the system (Flask Proxy).
*   `index.html`: Modern PWA interface with AI integration.
*   `camera_detection_headless.py`: High-performance RPi 5 vision engine.
*   `esp32_analogwrite_final/`: Firmware for the hardware controller.
*   `config.json`: Centralized configuration for IP and thresholds.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request or open an issue for feature requests.

---
*Created with ❤️ for a smarter, private home.*
