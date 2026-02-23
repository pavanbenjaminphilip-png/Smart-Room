# ============================================================
# Smart Room - Automated Raspberry Pi 5 Deployment Script
# ============================================================

$RPI_IP = "192.168.0.178"
$RPI_USER = "pavan799"
$RPI_TARGET = "${RPI_USER}@${RPI_IP}"

Write-Host "========================================================================"
Write-Host " Smart Room - Raspberry Pi 5 Camera Detection Deployment"
Write-Host "========================================================================"
Write-Host ""
Write-Host "Target: $RPI_TARGET"
Write-Host ""

# Check if files exist
$requiredFiles = @(
    "camera_detection_headless.py",
    "config.json",
    "setup_rpi.sh",
    "smart-room-camera.service"
)

Write-Host "[1/4] Checking files..."
$allFilesExist = $true
foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "  [OK] $file"
    }
    else {
        Write-Host "  [MISSING] $file!" -ForegroundColor Red
        $allFilesExist = $false
    }
}

if (-not $allFilesExist) {
    Write-Host ""
    Write-Host "ERROR: Some files are missing. Please run this script from the smart-room-pwa directory." -ForegroundColor Red
    Write-Host ""
    pause
    exit 1
}

Write-Host ""
Write-Host "[2/4] Copying files to Raspberry Pi..."
Write-Host "You will be prompted for the SSH password (default: raspberry)"
Write-Host ""

# Copy files using scp
scp camera_detection_headless.py config.json setup_rpi.sh smart-room-camera.service "${RPI_TARGET}:~/"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Failed to copy files. Check:" -ForegroundColor Red
    Write-Host "  - Raspberry Pi is powered on" -ForegroundColor Yellow
    Write-Host "  - IP address is correct: $RPI_IP" -ForegroundColor Yellow
    Write-Host "  - SSH is enabled on Raspberry Pi" -ForegroundColor Yellow
    Write-Host "  - Both devices are on the same network" -ForegroundColor Yellow
    Write-Host ""
    pause
    exit 1
}

Write-Host ""
Write-Host "Files copied successfully!"
Write-Host ""

# SSH and run setup + reboot in one go to minimize password prompts
# We use '&& sudo reboot' so it only reboots if setup was successful
ssh -t "${RPI_TARGET}" "chmod +x setup_rpi.sh && ./setup_rpi.sh && sudo reboot"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Deployment failed at the setup or reboot stage." -ForegroundColor Red
    Write-Host "Check the output above for specific errors." -ForegroundColor Yellow
    Write-Host "Common issues: No internet on RPi, incorrect password, or sudo requires manual password." -ForegroundColor Yellow
    Write-Host ""
    pause
    exit 1
}

Write-Host ""
Write-Host "========================================================================"
Write-Host "   Deployment Complete!"
Write-Host "========================================================================"
Write-Host ""
Write-Host "Your Raspberry Pi is rebooting..."
Write-Host ""
Write-Host "After reboot (~30 seconds), the camera detection will start automatically!"
Write-Host ""
Write-Host "To monitor the system:"
Write-Host "  ssh ${RPI_TARGET}"
Write-Host "  sudo journalctl -u smart-room-camera -f"
Write-Host ""
Write-Host "Expected output:"
Write-Host "  [10:30:15] HUMAN #1 -> T-Beam: LED ON"
Write-Host "  [10:30:22] No human -> T-Beam: LED OFF"
Write-Host ""
Write-Host "========================================================================"
Write-Host ""
pause
