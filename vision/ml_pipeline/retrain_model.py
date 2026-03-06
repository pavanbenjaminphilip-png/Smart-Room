import pandas as pd
import joblib
import os
from sklearn.linear_model import LinearRegression

def retrain():
    # 1. Load data
    df_hist = pd.read_csv('historical_temp_data.csv')
    
    # 2. Merge user logs if they exist
    pref_file = 'user_preferences.csv'
    
    if os.path.exists(pref_file):
        try:
            df_user = pd.read_csv(pref_file)
            if 'timestamp' in df_user.columns:
                df_user = df_user.drop(columns=['timestamp'])
            
            df = pd.concat([df_hist, df_user], ignore_index=True)
            print(f"Retraining: Successfully merged {len(df_user)} user preference samples.")
        except Exception as e:
            print(f"Retraining Warning: Could not read user preferences: {e}")
            df = df_hist
    else:
        df = df_hist
        print("Retraining: No user preference file found. Training on historical data only.")

    # 3. Clean and prepare
    df = df.dropna().astype('float32')
    
    X = df[['outside_temp', 'outside_humidity', 'outdoor_light']]
    y = df['target_indoor_temp']
    
    print(f"Retraining: Building Linear Regression model with {len(df)} total samples...")
    
    # 4. Train the Linear Regression model
    model = LinearRegression()
    model.fit(X, y)
    
    # 5. Export/Update the model file
    model_output = 'temp_model.pkl'
    joblib.dump(model, model_output)
    
    print(f"Retraining Success: Model updated at {model_output}")

if __name__ == "__main__":
    retrain()
