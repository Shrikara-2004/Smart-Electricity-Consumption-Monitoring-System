from flask import Flask, render_template, request, jsonify
from sklearn.preprocessing import StandardScaler
from flask_socketio import SocketIO, emit
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import numpy as np
from sklearn.ensemble import IsolationForest
from datetime import datetime
import json
import os


# --- App Initialization ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'a_very_secret_key_change_this'
bcrypt = Bcrypt(app)
socketio = SocketIO(app, async_mode='gevent')


# --- User Authentication Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# Load user store
users = {}
if os.path.exists('users.json'):
    with open('users.json', 'r') as f:
        users = json.load(f)


class User(UserMixin):
    def __init__(self, id):
        self.id = id


@login_manager.user_loader
def load_user(user_id):
    if user_id in users:
        return User(user_id)
    return None


# --- Real-Time Monitoring Class (Single Bulb) ---
class RealTimeEnergyMonitor:
    def __init__(self):
        self.anomaly_model = IsolationForest(contamination=0.1, random_state=42)  # Increased contamination
        self.data_history = []
        self.model_trained = False
        self.scaler = StandardScaler()
        self.connected_clients = 0
        self.retrain_interval = 10  # Retrain model every 10 new points

    def detect_anomaly(self, consumption_value):
        self.data_history.append(consumption_value)
        if len(self.data_history) < 50:
            return False, 0.0
        
        # Retrain model every retrain_interval points or if not trained yet
        if len(self.data_history) % self.retrain_interval == 0 or not self.model_trained:
            data_array = np.array(self.data_history[-100:]).reshape(-1, 1)
            scaled_data = self.scaler.fit_transform(data_array)
            self.anomaly_model.fit(scaled_data)
            self.model_trained = True

        # Scale current input and predict
        scaled_value = self.scaler.transform([[consumption_value]])
        prediction = self.anomaly_model.decision_function(scaled_value)
        is_anomaly = self.anomaly_model.predict(scaled_value)[0] == -1

        print(f"Anomaly check - Value: {consumption_value:.3f} kW, Scaled: {scaled_value[0][0]:.3f}, Score: {prediction[0]:.5f}, Anomaly: {is_anomaly}")

        return bool(is_anomaly), float(abs(prediction[0]))



monitor = RealTimeEnergyMonitor()


# --- HTTP Routes ---
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')


    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password are required'}), 400
    if username in users:
        return jsonify({'success': False, 'message': 'Username already exists'}), 409


    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    users[username] = {'password': hashed_password}
    with open('users.json', 'w') as f:
        json.dump(users, f)


    return jsonify({'success': True, 'message': 'Registration successful'}), 201


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    user_data = users.get(username)


    if user_data and bcrypt.check_password_hash(user_data['password'], password):
        user = User(username)
        login_user(user)
        return jsonify({'success': True, 'message': 'Login successful'}), 200


    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401


@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'success': True, 'message': 'Logout successful'}), 200


@app.route('/api/status')
def status():
    if current_user.is_authenticated:
        return jsonify({'authenticated': True, 'username': current_user.id})
    return jsonify({'authenticated': False})


# ============================================
# ESP32 PZEM-004T Integration Endpoint
# ============================================
# ============================================
# ESP32 PZEM-004T Integration Endpoint
# ============================================
@app.route('/api/esp32/data', methods=['POST'])
def receive_esp32_data():
    """
    Receive live sensor data from ESP32 PZEM-004T monitoring a single bulb
    Expected JSON format:
    {
        "voltage": 230.5,
        "current": 0.45,
        "power": 103.7,
        "energy": 0.254,
        "frequency": 50.0,
        "pf": 0.98
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'message': 'No data received'}), 400

    # Extract sensor readings
    voltage = data.get('voltage', 0)
    current = data.get('current', 0)
    power = data.get('power', 0)
    energy = data.get('energy', 0)
    frequency = data.get('frequency', 0)
    pf = data.get('pf', 0)

    # Calculate consumption in kW (convert from Watts)
    consumption = power / 1000.0

    timestamp = datetime.now().strftime('%H:%M:%S')

    # ---- 1) Treat very low power as "OFF" -> never anomaly ----
    OFF_THRESHOLD_W = 2.0   # below ~2 W: bulb considered OFF / standby
    if power < OFF_THRESHOLD_W:
        data_point = {
            'appliance_id': 'bulb',
            'appliance_name': 'Bulb',
            'timestamp': timestamp,
            'consumption': round(consumption, 3),
            'voltage': round(voltage, 2),
            'current': round(current, 3),
            'power': round(power, 2),
            'energy': round(energy, 3),
            'frequency': round(frequency, 1),
            'pf': round(pf, 2),
            'is_anomaly': False,
            'confidence': 0.0
        }
        socketio.emit('energy_update', data_point)
        print(f"💡 Bulb OFF/very low load: {power:.2f}W | Anomaly: NO")
        return jsonify({
            'success': True,
            'is_anomaly': False,
            'confidence': 0.0,
            'message': 'Low power, treated as normal (OFF)'
        }), 200

    # ---- 2) Normal case: add to history and run anomaly detection ----
    monitor.data_history.append(consumption)
    if len(monitor.data_history) > 500:
        monitor.data_history.pop(0)

    # Run ML anomaly detection
    is_anomaly, confidence = monitor.detect_anomaly(consumption)

    # Extra rule: ignore very small jumps around recent average
    if len(monitor.data_history) >= 30:
        recent_avg = float(np.mean(monitor.data_history[-30:]))
        diff_kw = abs(consumption - recent_avg)
        diff_w = diff_kw * 1000.0

        MIN_JUMP_W = 20.0   # only spikes > 20 W can be anomalies
        if diff_w < MIN_JUMP_W:
            is_anomaly = False
            confidence = 0.0

    # Prepare data point for single bulb
    data_point = {
        'appliance_id': 'bulb',
        'appliance_name': 'Bulb',
        'timestamp': timestamp,
        'consumption': round(consumption, 3),
        'voltage': round(voltage, 2),
        'current': round(current, 3),
        'power': round(power, 2),
        'energy': round(energy, 3),
        'frequency': round(frequency, 1),
        'pf': round(pf, 2),
        'is_anomaly': is_anomaly,
        'confidence': round(confidence, 3)
    }

    # Broadcast to all connected WebSocket clients
    socketio.emit('energy_update', data_point)

    # Send anomaly alert if detected
    if is_anomaly:
        alert_data = {
            'appliance_name': 'Bulb',
            'timestamp': timestamp,
            'consumption': round(consumption, 3),
            'power': round(power, 2),
            'voltage': round(voltage, 2),
            'current': round(current, 3)
        }
        print(f"🚨 ANOMALY DETECTED: Power={power:.2f}W, Voltage={voltage:.2f}V")
        socketio.emit('anomaly_alert', alert_data)

    # Log to console
    print(f"💡 Bulb: {power:.2f}W | {voltage:.2f}V | Anomaly: {'YES' if is_anomaly else 'NO'}")

    return jsonify({
        'success': True,
        'is_anomaly': is_anomaly,
        'confidence': round(confidence, 3),
        'message': 'Bulb data received successfully'
    }), 200



# --- SocketIO Events ---
@socketio.on('connect')
def handle_connect():
    if not current_user.is_authenticated:
        return  # Reject connection if not logged in


    monitor.connected_clients += 1
    print(f'✅ Client connected: {current_user.id}. Total: {monitor.connected_clients}')
    emit('connection_status', {'status': 'connected', 'username': current_user.id})


@socketio.on('disconnect')
def handle_disconnect():
    if not current_user.is_authenticated:
        return


    monitor.connected_clients = max(0, monitor.connected_clients - 1)
    print(f'❌ Client disconnected: {current_user.id}. Total: {monitor.connected_clients}')


# --- Main Execution ---
if __name__ == '__main__':
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  🚀 Smart Bulb Energy Monitor with ML")
    print("  📡 ESP32 endpoint: /api/esp32/data")
    print("  🌐 Dashboard: http://localhost:5001")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    socketio.run(app, host='0.0.0.0', port=5001, debug=False)
