pip install scikit-learn

import pandas as pd

# Load the CSV
df = pd.read_csv(r"C:\Users\HP\Downloads\HomeC.csv\HomeC.csv", low_memory=False)

# Convert UNIX timestamp (as string or int) to datetime
df['timestamp'] = pd.to_datetime(df['time'], unit='s', errors='coerce')

# Drop rows where timestamp couldn't be parsed
df = df.dropna(subset=['timestamp'])

# View result
print(df[['timestamp']].head())


##################################################


# Select relevant columns
selected_columns = ['timestamp', 'use [kW]', 'Fridge [kW]', 'Dishwasher [kW]', 
                    'Microwave [kW]', 'temperature', 'humidity']

# Filter the DataFrame
df = df[selected_columns]

# Handle missing values
df = df.dropna()

# Optional: reset index after cleaning
df.reset_index(drop=True, inplace=True)

# Preview cleaned data
print(df.head())

######################################################

# Add hour and day of week
df['hour'] = df['timestamp'].dt.hour
df['day_of_week'] = df['timestamp'].dt.dayofweek  # 0 = Monday

# Example: rolling average of total usage over past 3 minutes
df['rolling_use'] = df['use [kW]'].rolling(window=3).mean()

# Drop rows with NaN from rolling
df.dropna(inplace=True)

print(df.head())


########################################################

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# Select features for training
feature_cols = ['use [kW]', 'Fridge [kW]', 'Dishwasher [kW]', 'Microwave [kW]', 
                'temperature', 'humidity', 'hour', 'day_of_week', 'rolling_use']

X = df[feature_cols]

# Scale the features
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Train Isolation Forest
model = IsolationForest(n_estimators=100, contamination=0.01, random_state=42)
df['anomaly'] = model.fit_predict(X_scaled)

# Anomaly labels: 1 = normal, -1 = anomaly
df['anomaly'] = df['anomaly'].map({1: 0, -1: 1})

# Count anomalies
print("Anomalies detected:", df['anomaly'].sum())
print(df[df['anomaly'] == 1].head())

#################################################################

import matplotlib.pyplot as plt

# Convert timestamp to datetime again (if not already)
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Plot energy usage with anomalies highlighted
plt.figure(figsize=(15, 6))

# Normal points
normal = df[df['anomaly'] == 0]
# Anomalies
anomalies = df[df['anomaly'] == 1]

plt.plot(df['timestamp'], df['use [kW]'], label='Energy Use (kW)', color='blue', linewidth=0.7)
plt.scatter(anomalies['timestamp'], anomalies['use [kW]'], color='red', label='Anomalies', s=20)

plt.xlabel('Time')
plt.ylabel('Energy Consumption (kW)')
plt.title('Energy Consumption with Anomaly Detection')
plt.legend()
plt.tight_layout()
plt.show()