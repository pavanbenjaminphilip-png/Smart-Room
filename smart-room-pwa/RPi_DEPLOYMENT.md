# 🍓 Raspberry Pi 5 Camera Detection - Deployment Guide

## 📋 Quick Setup

### What You Need
- ✅ Raspberry Pi 5
- ✅ Raspberry Pi Camera Module (any version)
- ✅ Raspberry Pi OS (Bullseye or Bookworm)
- ✅ T-Beam ESP32 on your network
- ✅ MicroSD card (8GB+)

---

## 🚀 Installation Steps

### 1️⃣ Prepare Raspberry Pi

1. **Flash OS** (you already did this!)
   - Used Raspberry Pi Imager ✓
   
2. **Connect camera module**
   - Attach to CSI camera port
   - Make sure the ribbon cable is facing the correct direction

3. **Boot and connect to WiFi**
   - Connect RPi to your router (same network as T-Beam)
   - Get the IP address: `hostname -I`

---

### 2️⃣ Copy Files to Raspberry Pi

**From your PC**, copy the files to RPi:

```powershell
# Replace <RPI_IP> with your Raspberry Pi's IP address
scp camera_detection_headless.py config.json smart-room-pwa/setup_rpi.sh smart-room-pwa/smart-room-camera.service pavan799@10.247.253.127:/home/pavan799/
```

**Example:**
```powershell
scp camera_detection_headless.py pi@192.168.0.100:/home/pi/
scp config.json pi@192.168.0.100:/home/pi/
scp setup_rpi.sh pi@192.168.0.100:/home/pi/
scp smart-room-camera.service pi@192.168.0.100:/home/pi/
```

---

### 3️⃣ SSH into Raspberry Pi

```powershell
ssh pavan799@10.247.253.127
```

Default password is usually: `raspberry` (change this for security!)

---

### 4️⃣ Run Setup Script

```bash
cd /home/pi
chmod +x setup_rpi.sh
./setup_rpi.sh
```

This will:
- ✅ Install Python libraries (picamera2, opencv, etc.)
- ✅ Enable camera interface
- ✅ Create `/home/pi/smart-room/` directory
- ✅ Install systemd service for auto-start
- ✅ Configure everything

---

### 5️⃣ Configure Your T-Beam IP

Edit the config file if your T-Beam has a different IP:

```bash
nano /home/pi/smart-room/config.json
```

Change the `esp32_ip` to your T-Beam's IP address:
```json
{
  "esp32_ip": "192.168.0.137",  ← Change this if needed
  ...
}
```

Save: `Ctrl+O`, `Enter`, then `Ctrl+X`

---

### 6️⃣ Reboot

```bash
sudo reboot
```

After reboot, the camera detection will **automatically start**!

---

## 🔍 Testing & Monitoring

### Check if Service is Running

```bash
sudo systemctl status smart-room-camera
```

You should see: `active (running)` in green ✓

### View Live Logs

```bash
sudo journalctl -u smart-room-camera -f
```

You should see:
```
[10:30:15] 👤 HUMAN #1 → T-Beam: LED ON
[10:30:22] 🚫 No human → T-Beam: LED OFF
```

Press `Ctrl+C` to exit logs.

---

## 🛠️ Manual Testing (Optional)

If you want to test without the service:

```bash
# Stop the service first
sudo systemctl stop smart-room-camera

# Run manually
cd /home/pi/smart-room
python3 camera_detection_headless.py
```

Press `Ctrl+C` to stop.

---

## ⚙️ Service Management

```bash
# Start the service
sudo systemctl start smart-room-camera

# Stop the service
sudo systemctl stop smart-room-camera

# Restart the service
sudo systemctl restart smart-room-camera

# Disable auto-start on boot
sudo systemctl disable smart-room-camera

# Enable auto-start on boot
sudo systemctl enable smart-room-camera

# View recent logs
sudo journalctl -u smart-room-camera -n 50
```

---

## 🔧 Configuration Options

Edit `/home/pi/smart-room/config.json`:

| Setting | Description | Default |
|---------|-------------|---------|
| `esp32_ip` | T-Beam ESP32 IP address | `192.168.0.137` |
| `camera_slot` | Camera slot number | `0` |
| `camera_width` | Camera resolution width | `640` |
| `camera_height` | Camera resolution height | `480` |
| `process_every_n_frames` | Process every Nth frame (higher = faster, less accurate) | `3` |
| `detection_scale` | Detection resolution scale (0.3-1.0) | `0.5` |
| `send_interval` | Seconds between updates to T-Beam | `2.0` |
| `log_detections` | Print detection events to console | `true` |

**After editing config**, restart the service:
```bash
sudo systemctl restart smart-room-camera
```

---

## 🐛 Troubleshooting

### Camera Not Detected

```bash
# Check if camera is recognized
libcamera-hello --list-cameras

# If not found, enable camera manually
sudo raspi-config
# → Interface Options → Camera → Enable
```

### T-Beam Not Connecting

1. **Check T-Beam IP**:
   ```bash
   ping 192.168.0.137
   ```

2. **Check if T-Beam web server is running**:
   ```bash
   curl http://192.168.0.137/status
   ```

3. **Update config.json** with correct IP

### Low FPS / Laggy

Edit `/home/pi/smart-room/config.json`:
- Increase `process_every_n_frames` to `4` or `5`
- Decrease `detection_scale` to `0.4` or `0.3`

### Service Won't Start

```bash
# Check detailed error
sudo journalctl -u smart-room-camera -n 100

# Check Python errors
cd /home/pi/smart-room
python3 camera_detection_headless.py
```

---

## 📱 Phone App Integration

Your phone app should connect to:
- **T-Beam ESP32**: `http://192.168.0.137` (controls LED, gets status)
- **AI Backend** (if using): Separate server (not on RPi)

The RPi runs **independently** - it only sends detection signals to T-Beam.

---

## 🎯 Architecture Overview

```
┌─────────────────┐
│  Raspberry Pi 5 │
│  Camera Module  │
│                 │
│  Detects humans │
│  (headless)     │
└────────┬────────┘
         │ HTTP POST
         │ /camera/human
         ▼
┌─────────────────┐
│  T-Beam ESP32   │
│                 │
│  Controls LED   │
│  ├─ ON: Person  │
│  └─ OFF: Empty  │
└────────┬────────┘
         │ HTTP API
         ▼
┌─────────────────┐
│   Phone App     │
│  (Smart Room)   │
│                 │
│  View status    │
│  Manual control │
└─────────────────┘
```

---

## ✅ Success Checklist

- [ ] Camera module connected and detected
- [ ] Files copied to `/home/pi/smart-room/`
- [ ] Setup script run successfully
- [ ] Config.json has correct T-Beam IP
- [ ] Rebooted Raspberry Pi
- [ ] Service is `active (running)`
- [ ] Logs show detection events
- [ ] T-Beam LED turns on when person detected
- [ ] Phone app can connect to T-Beam

---

## 📞 Support

If you run into issues:
1. Check the logs: `sudo journalctl -u smart-room-camera -f`
2. Verify T-Beam connectivity: `curl http://<T-BEAM-IP>/status`
3. Test camera: `libcamera-hello`

**Created by:** Smart Room Camera Detection System
**Version:** 1.0 (Headless for RPi5 + T-Beam)
