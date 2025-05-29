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

####################################################################

# Step 5: Filter only fridge data
df_fridge = df[['timestamp', 'Fridge [kW]']].copy()

# Step 6: Smooth fridge data using rolling mean (to reduce noise)
df_fridge['fridge_smooth'] = df_fridge['Fridge [kW]'].rolling(window=60, min_periods=1).mean()

# Step 7: Drop any remaining NaN values (due to smoothing)
df_fridge = df_fridge.dropna()

print(df_fridge.head())

###################################################################

# Step 8: Fit Isolation Forest to the smoothed fridge data
model = IsolationForest(contamination=0.005, random_state=42)
df_fridge['anomaly'] = model.fit_predict(df_fridge[['fridge_smooth']])

# Step 9: Convert -1/1 to 1/0 (1 = anomaly, 0 = normal)
df_fridge['anomaly'] = df_fridge['anomaly'].map({1: 0, -1: 1})

# Step 10: Extract anomaly records
anomalies = df_fridge[df_fridge['anomaly'] == 1]
print("Anomalies detected:", len(anomalies))
display(anomalies.head())

##################################################################

# Plot fridge usage with anomalies
plt.figure(figsize=(15, 6))
plt.plot(df_fridge['timestamp'], df_fridge['fridge_smooth'], label='Fridge Power Usage', color='blue')
plt.scatter(anomalies['timestamp'], anomalies['fridge_smooth'], color='red', label='Anomalies')
plt.xlabel('Time')
plt.ylabel('Fridge Power [kW]')
plt.title('Anomaly Detection in Fridge Power Consumption')
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
