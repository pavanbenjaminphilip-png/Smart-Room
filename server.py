from flask import Flask, request, Response, send_from_directory, jsonify
import requests
import os

app = Flask(__name__, static_folder='.')

OLLAMA_BASE_URL = "http://localhost:11434"
ESP32_BASE_URL = "http://192.168.0.139"

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)

# ============================================================
# ESP32 PROXY ROUTES (for HTTPS access via ngrok)
# ============================================================

@app.route('/esp32/status', methods=['GET'])
def proxy_esp32_status():
    """Proxy ESP32 status endpoint"""
    try:
        resp = requests.get(f"{ESP32_BASE_URL}/status", timeout=5)
        return Response(resp.content, status=resp.status_code, content_type='application/json')
    except Exception as e:
        print(f"ESP32 Proxy Error: {str(e)}")
        return jsonify({"error": f"ESP32 not reachable: {str(e)}"}), 503

@app.route('/esp32/sensors', methods=['GET'])
def proxy_esp32_sensors():
    """Proxy ESP32 sensors endpoint"""
    try:
        resp = requests.get(f"{ESP32_BASE_URL}/sensors", timeout=5)
        return Response(resp.content, status=resp.status_code, content_type='application/json')
    except Exception as e:
        print(f"ESP32 Proxy Error: {str(e)}")
        return jsonify({"error": f"ESP32 not reachable: {str(e)}"}), 503

@app.route('/esp32/mode', methods=['POST'])
def proxy_esp32_mode():
    """Proxy ESP32 mode control"""
    try:
        # Forward the raw body data to ESP32
        resp = requests.post(f"{ESP32_BASE_URL}/mode", 
                           data=request.form,
                           timeout=20)
        
        # Create response with no-cache headers
        response = Response(resp.content, status=resp.status_code, content_type='application/json')
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response
    except Exception as e:
        print(f"Mode Proxy Error: {str(e)}")
        return jsonify({"error": str(e)}), 503

@app.route('/esp32/brightness', methods=['POST'])
def proxy_esp32_brightness():
    """Proxy ESP32 brightness control"""
    try:
        resp = requests.post(f"{ESP32_BASE_URL}/brightness", 
                           data=request.form,
                           timeout=20)
        response = Response(resp.content, status=resp.status_code, content_type='application/json')
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response
    except Exception as e:
        print(f"Brightness Proxy Error: {str(e)}")
        return jsonify({"error": str(e)}), 503

@app.route('/esp32/blinds', methods=['POST'])
def proxy_esp32_blinds():
    """Proxy ESP32 blinds control"""
    try:
        resp = requests.post(f"{ESP32_BASE_URL}/blinds", 
                           data=request.form,
                           timeout=25)
        response = Response(resp.content, status=resp.status_code, content_type='application/json')
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response
    except Exception as e:
        print(f"Blinds Proxy Error: {str(e)}")
        return jsonify({"error": str(e)}), 503

@app.route('/esp32/fan', methods=['POST'])
def proxy_esp32_fan():
    """Proxy ESP32 fan control"""
    try:
        resp = requests.post(f"{ESP32_BASE_URL}/fan", 
                           data=request.form,
                           timeout=20)
        response = Response(resp.content, status=resp.status_code, content_type='application/json')
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response
    except Exception as e:
        print(f"Fan Proxy Error: {str(e)}")
        return jsonify({"error": str(e)}), 503

# ============================================================
# OLLAMA PROXY ROUTE
# ============================================================

@app.route('/api/chat', methods=['POST'])
def proxy_ollama():
    """Proxy requests to Ollama to avoid CORS and Mixed Content issues."""
    try:
        data = request.get_json()
        print(f"Proxying request to Ollama...")
        
        # Forward the request to Ollama
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=data,
            stream=True
        )

        def generate():
            for line in resp.iter_lines():
                if line:
                    yield line + b'\n'

        return Response(generate(), content_type=resp.headers.get('Content-Type', 'application/json'))
    except Exception as e:
        print(f"Proxy Error: {str(e)}")
        return Response(f"Error connecting to Ollama: {str(e)}", status=500)

if __name__ == '__main__':
    print("========================================")
    print("Smart Room Unified Server")
    print("Serving PWA and Proxying Ollama + ESP32")
    print("Port: 8000")
    print(f"ESP32: {ESP32_BASE_URL}")
    print(f"Ollama: {OLLAMA_BASE_URL}")
    print("========================================")
    # Use 0.0.0.0 to allow network access
    app.run(host='0.0.0.0', port=8000, debug=False)
