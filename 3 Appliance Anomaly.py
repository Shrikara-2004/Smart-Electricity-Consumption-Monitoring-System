pip install scikit-learn

import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest
import matplotlib.pyplot as plt


# Load the CSV
df = pd.read_csv(r"C:\Users\HP\Downloads\HomeC.csv\HomeC.csv", low_memory=False)

# Convert UNIX timestamp (as string or int) to datetime
df['timestamp'] = pd.to_datetime(df['time'], unit='s', errors='coerce')

# Drop rows where timestamp couldn't be parsed
df = df.dropna(subset=['timestamp'])

# View result
print(df[['timestamp']].head())


##################################################


# 3. Select and clean features
df = df[['timestamp', 'use [kW]', 'Fridge [kW]', 'Dishwasher [kW]', 'Microwave [kW]', 'temperature', 'humidity']]
df = df.dropna()

# 4. Smooth energy consumption (optional)
df['use_smooth'] = df['use [kW]'].rolling(window=10, center=True).mean()
df = df.dropna()  # Drop NA values from smoothing

# Preview cleaned data
print(df.head())

######################################################

features = df[['use_smooth', 'Fridge [kW]', 'Dishwasher [kW]', 'Microwave [kW]', 'temperature', 'humidity']]

# 6. Train Isolation Forest
model = IsolationForest(contamination=0.001, random_state=42)
df['anomaly'] = model.fit_predict(features)
df['anomaly'] = df['anomaly'].map({1: 0, -1: 1})

# Count anomalies
print("Anomalies detected:", df['anomaly'].sum())
print(df[df['anomaly'] == 1].head())




#################################################################
# 7. Plot
plt.figure(figsize=(15, 6))
plt.plot(df['timestamp'], df['use [kW]'], label='Energy Use', color='blue', linewidth=0.7)
plt.scatter(df[df['anomaly'] == 1]['timestamp'], df[df['anomaly'] == 1]['use [kW]'],
            color='red', label='Anomalies', s=20)
plt.title('Energy Consumption with Anomaly Detection')
plt.xlabel('Time')
plt.ylabel('Energy Consumption (kW)')
plt.legend()
plt.tight_layout()
plt.show(
