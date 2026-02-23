#!/bin/bash
#
# Smart Room Camera Detection - Setup Script for Raspberry Pi 5
# This script installs all dependencies and sets up the camera detection service
#

set -e  # Exit on error

echo "========================================================================"
echo " Smart Room - Raspberry Pi 5 Camera Detection Setup"
echo "========================================================================"
echo ""

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    echo "⚠ Warning: This doesn't appear to be a Raspberry Pi"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "[1/6] Updating system packages..."
sudo apt update

echo ""
echo "[2/6] Installing Python dependencies..."
sudo apt install -y python3-picamera2 python3-opencv python3-numpy python3-requests

echo ""
echo "[3/6] Enabling camera interface..."
sudo raspi-config nonint do_camera 0

# [4/6] Creating installation directory...
INSTALL_DIR="$HOME/smart-room"
mkdir -p "$INSTALL_DIR"

echo ""
echo "[5/6] Copying files..."
cp camera_detection_headless.py "$INSTALL_DIR/"
cp config.json "$INSTALL_DIR/"

echo ""
echo "[6/6] Installing systemd service..."
# Prepare service file with correct paths and user
sudo sed -i "s|RP_PATH|$INSTALL_DIR|g" smart-room-camera.service
sudo sed -i "s|RP_USER|$USER|g" smart-room-camera.service

sudo cp smart-room-camera.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable smart-room-camera.service

echo ""
echo "========================================================================"
echo " ✓ Installation Complete!"
echo "========================================================================"
echo ""
echo "Configuration file: $INSTALL_DIR/config.json"
echo "  Edit to change ESP32 IP, camera settings, etc."
echo ""
echo "Service commands:"
echo "  Start:   sudo systemctl start smart-room-camera"
echo "  Stop:    sudo systemctl stop smart-room-camera"
echo "  Status:  sudo systemctl status smart-room-camera"
echo "  Logs:    sudo journalctl -u smart-room-camera -f"
echo ""
echo "Manual run (for testing):"
echo "  cd $INSTALL_DIR"
echo "  python3 camera_detection_headless.py"
echo ""
echo "!!! IMPORTANT: Please reboot your Raspberry Pi now!"
echo "  sudo reboot"
echo ""
echo "After reboot, the camera detection will start automatically."
echo "========================================================================"
