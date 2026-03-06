import pandas as pd
import numpy as np
import os

print("Generating synthetic dataset mapping environmental conditions to user temperature preferences...")
np.random.seed(42)
n_samples = 12000

outside_temp = np.random.uniform(-5, 40, n_samples)
outside_humidity = np.random.uniform(20, 100, n_samples)
outdoor_light = np.random.uniform(0, 700, n_samples)   # LDR sensor range: 0 (dark) to ~700 (direct flash)

# Synthetic target logic
# outdoor_light scaled to 700 max (real LDR sensor ceiling)
target_indoor_temp = 22.0 - (outside_temp - 20) * 0.15 - (outside_humidity - 50) * 0.02 - (outdoor_light / 700) * 1.5
target_indoor_temp += np.random.normal(0, 0.8, n_samples)

df = pd.DataFrame({
    'outside_temp': outside_temp,
    'outside_humidity': outside_humidity,
    'outdoor_light': outdoor_light,
    'target_indoor_temp': target_indoor_temp
})

# Introduce a few NaN values to simulate real-world sensor dropouts and demonstrate cleaning later
drop_indices = np.random.choice(df.index, size=50, replace=False)
df.loc[drop_indices, 'outside_temp'] = np.nan

csv_path = 'historical_temp_data.csv'
df.to_csv(csv_path, index=False)
print(f"Successfully generated {n_samples} samples and saved to {csv_path}")
