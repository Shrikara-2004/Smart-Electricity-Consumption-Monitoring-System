document.addEventListener('DOMContentLoaded', () => {
    let socket;
    let chart;
    const MAX_DATA_POINTS = 25;  // Reduced for mobile performance
    const powerData = [];
    const timeLabels = [];

    // DOM Elements
    const authContainer = document.getElementById('auth-container');
    const dashboardContainer = document.getElementById('dashboard-container');
    const loginView = document.getElementById('login-view');
    const registerView = document.getElementById('register-view');

    // Toggle between login and register
    document.getElementById('show-register-link').addEventListener('click', (e) => {
        e.preventDefault();
        loginView.classList.add('hidden');
        registerView.classList.remove('hidden');
    });

    document.getElementById('show-login-link').addEventListener('click', (e) => {
        e.preventDefault();
        registerView.classList.add('hidden');
        loginView.classList.remove('hidden');
    });

    // Form submissions
    document.getElementById('login-form').addEventListener('submit', (e) => handleAuth(e, true));
    document.getElementById('register-form').addEventListener('submit', (e) => handleAuth(e, false));
    document.getElementById('logout-button').addEventListener('click', handleLogout);

    // Authentication handler
    async function handleAuth(e, isLogin) {
        e.preventDefault();
        const prefix = isLogin ? 'login' : 'register';
        const url = isLogin ? '/api/login' : '/api/register';
        const username = document.getElementById(`${prefix}-username`).value;
        const password = document.getElementById(`${prefix}-password`).value;

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            const data = await response.json();

            if (data.success) {
                if (isLogin) {
                    showDashboard(username);
                } else {
                    Swal.fire('Success!', 'Account created! Please login.', 'success');
                    document.getElementById('show-login-link').click();
                }
            } else {
                Swal.fire('Error', data.message, 'error');
            }
        } catch (error) {
            Swal.fire('Error', 'Connection failed. Please try again.', 'error');
        }
    }

    // Logout
    async function handleLogout() {
        await fetch('/api/logout', { method: 'POST' });
        location.reload();
    }

    // Check if user is already logged in
    async function checkAuthStatus() {
        const response = await fetch('/api/status');
        const data = await response.json();
        if (data.authenticated) {
            showDashboard(data.username);
        }
    }

    // Show dashboard
    function showDashboard(username) {
        authContainer.classList.add('hidden');
        dashboardContainer.classList.remove('hidden');
        document.getElementById('username-display').textContent = username;
        initializeChart();
        initializeSocket();
    }

    // Initialize Chart.js - Mobile Optimized
    function initializeChart() {
        const ctx = document.getElementById('overall-chart').getContext('2d');
        chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: timeLabels,
                datasets: [{
                    label: 'Power (W)',
                    data: powerData,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4,
                    fill: true,
                    borderWidth: 2,
                    pointRadius: 2,  // Smaller points for mobile
                    pointHoverRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,  // Allow CSS to control size
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: { 
                            color: '#f8fafc',
                            font: { size: 12 },
                            boxWidth: 20,
                            padding: 10
                        }
                    },
                    tooltip: {
                        enabled: true,
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        padding: 8,
                        titleFont: { size: 12 },
                        bodyFont: { size: 11 }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: { 
                            color: '#cbd5e1',
                            font: { size: 11 }
                        }
                    },
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.1)' },
                        ticks: { 
                            color: '#cbd5e1',
                            font: { size: 10 },
                            maxRotation: 45,
                            minRotation: 0
                        }
                    }
                },
                animation: {
                    duration: 0  // Disable animation for performance
                }
            }
        });
    }

    // Initialize WebSocket
    function initializeSocket() {
        socket = io({ autoConnect: true });

        socket.on('connect', () => console.log('✅ Connected to server'));
        socket.on('disconnect', () => console.log('❌ Disconnected from server'));

        // Handle bulb data updates
        socket.on('energy_update', (data) => {
            updateBulbDisplay(data);
            updateChart(data);
        });

        // Handle anomaly alerts
        socket.on('anomaly_alert', (data) => {
            logAnomaly(data);
            showAnomalyAlert(data);
        });
    }

    // Update bulb display
    function updateBulbDisplay(data) {
        const bulbCard = document.getElementById('card-bulb');
        const consumption = bulbCard.querySelector('.consumption');
        
        consumption.innerHTML = `${data.consumption.toFixed(3)} <span class="unit">kW</span>`;
        
        // Update individual metrics
        document.getElementById('voltage-display').innerHTML = 
            `${data.voltage} <span class="unit">V</span>`;
        document.getElementById('current-display').innerHTML = 
            `${data.current} <span class="unit">A</span>`;
        document.getElementById('power-display').innerHTML = 
            `${data.power} <span class="unit">W</span>`;

        // Toggle anomaly state
        if (data.is_anomaly) {
            bulbCard.classList.add('anomaly');
        } else {
            bulbCard.classList.remove('anomaly');
        }
    }

    // Update chart
    function updateChart(data) {
        powerData.push(data.power);
        timeLabels.push(data.timestamp);

        if (powerData.length > MAX_DATA_POINTS) {
            powerData.shift();
            timeLabels.shift();
        }

        chart.update('none');  // No animation for smooth performance
    }

    // Log anomaly to list
    function logAnomaly(data) {
        const list = document.getElementById('anomaly-list');
        
        // Remove "no anomalies" placeholder
        if (list.children.length === 1 && list.children[0].textContent.includes('No anomalies')) {
            list.innerHTML = '';
        }

        const item = document.createElement('li');
        item.innerHTML = `
            <span class="timestamp">[${data.timestamp}]</span> 
            <strong>Bulb Anomaly:</strong> 
            Power: ${data.power}W, Voltage: ${data.voltage}V
        `;
        list.prepend(item);

        // Keep only last 15 entries
        if (list.children.length > 15) {
            list.removeChild(list.lastChild);
        }
    }

    // Show anomaly popup alert
    function showAnomalyAlert(data) {
        Swal.fire({
            icon: 'warning',
            title: '⚠️ Anomaly Detected!',
            html: `
                <strong>Bulb Power Spike</strong><br>
                Power: ${data.power}W<br>
                Voltage: ${data.voltage}V<br>
                <small>${data.timestamp}</small>
            `,
            toast: true,
            position: 'top-end',
            showConfirmButton: false,
            timer: 5000,
            timerProgressBar: true,
            background: '#fee2e2',
            iconColor: '#ef4444'
        });
    }

    // Initialize on page load
    checkAuthStatus();
});
