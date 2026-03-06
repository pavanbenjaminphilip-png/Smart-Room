import joblib
import pandas as pd
import numpy as np
import os
import csv
from datetime import datetime
import requests

# Constants
MODEL_PATH = 'ml_pipeline/temp_model.pkl'
LOG_PATH = 'ml_pipeline/user_preferences.csv'
WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast?latitude=25.2048&longitude=55.2708&current=temperature_2m,relative_humidity_2m" # UAE (Dubai) coordinates for accurate local weather forecast

# Global model cache
_model = None

def load_model():
    """Load the model if not already loaded"""
    global _model
    if _model is None:
        try:
            if os.path.exists(MODEL_PATH):
                _model = joblib.load(MODEL_PATH)
                print(f"ML Optimizer: Successfully loaded model from {MODEL_PATH}")
            else:
                print(f"ML Optimizer Error: Model file not found at {MODEL_PATH}")
        except Exception as e:
            print(f"ML Optimizer Error loading model: {e}")
    return _model

def get_outside_weather():
    """Fetch real-time outside weather from Open-Meteo"""
    try:
        response = requests.get(WEATHER_API_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            current = data.get("current", {})
            return {
                "outside_temp": current.get("temperature_2m", 25.0),
                "outside_humidity": current.get("relative_humidity_2m", 50.0)
            }
    except Exception as e:
        print(f"ML Optimizer Warning: Could not fetch weather API. Using fallback defaults. {e}")
    
    return {
        "outside_temp": 25.0,
        "outside_humidity": 50.0
    }

def predict_optimal_temp(outdoor_light):
    """
    Predict optimal temperature dynamically using the ML model.
    Fetches real-time weather internally.
    """
    model = load_model()
    weather = get_outside_weather()
    outside_temp = weather["outside_temp"]
    outside_humidity = weather["outside_humidity"]

    if model is None:
        # Fallback heuristic if model fails to load
        target = 22.0 - (outside_temp - 20) * 0.15 - (outside_humidity - 50) * 0.02 - (outdoor_light / 700) * 1.5
        return {
            "predicted_temp": round(target, 1),
            "outside_temp": outside_temp,
            "outside_humidity": outside_humidity,
            "outdoor_light": outdoor_light,
            "source": "heuristic_fallback"
        }

    # Run the model prediction
    input_data = pd.DataFrame([{
        'outside_temp': float(outside_temp),
        'outside_humidity': float(outside_humidity),
        'outdoor_light': float(outdoor_light)
    }])

    pred = model.predict(input_data)[0]

    return {
        "predicted_temp": round(pred, 1),
        "outside_temp": outside_temp,
        "outside_humidity": outside_humidity,
        "outdoor_light": outdoor_light,
        "source": "ml_model"
    }

def log_user_preference(outside_temp, outside_humidity, outdoor_light, user_set_temp):
    """Log manual overrides for future retraining"""
    file_exists = os.path.isfile(LOG_PATH)
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        
        with open(LOG_PATH, mode='a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(['timestamp', 'outside_temp', 'outside_humidity', 'outdoor_light', 'target_indoor_temp'])
            
            writer.writerow([
                datetime.now().isoformat(),
                outside_temp,
                outside_humidity,
                outdoor_light,
                user_set_temp
            ])
            print(f"ML Optimizer: Logged user preference: {user_set_temp}°C")
            return True
    except Exception as e:
        print(f"ML Optimizer Error logging preference: {e}")
        return False
