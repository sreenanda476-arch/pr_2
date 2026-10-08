from flask import Flask, jsonify, request, render_template_string
import os
import time
from typing import Dict, Any

from config import (
    DEFAULT_THRESHOLD_METERS,
    DEFAULT_THRESHOLD_KM,
    DEFAULT_ROUTE_WAYPOINTS,
    INTERSECTIONS,
    VEHICLES,
    START_POINT,
    END_POINT
)
from services import (
    signal_manager,
    calculate_distance_km,
    calculate_distance_meters,
    calculate_bearing
)

app = Flask(__name__)

# In-memory runtime state
system_audit_log = []
active_simulation_state = {
    "vehicle_id": "AMB-108",
    "threshold_meters": DEFAULT_THRESHOLD_METERS,
    "current_position": START_POINT,
    "status": "IDLE"
}

def log_event(event_type: str, message: str):
    """Appends an event to the in-memory audit log (capped at 50 entries)."""
    entry = {
        "timestamp": time.strftime("%H:%M:%S"),
        "type": event_type,
        "message": message
    }
    system_audit_log.insert(0, entry)
    if len(system_audit_log) > 50:
        system_audit_log.pop()

# --- 1. API ENDPOINTS (ORIGINAL PRESERVED & EXPANDED) ---

@app.route("/")
def home():
    """Serves the interactive frontend web dashboard."""
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/traffic-update", methods=["POST"])
def traffic_update():
    """
    Receives emergency vehicle GPS position, validates telemetry,
    and dynamically toggles traffic signal status along the corridor.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            "status": "error",
            "message": "Invalid or missing JSON payload."
        }), 400

    ambulance_lat = data.get("lat")
    ambulance_lng = data.get("lng")
    vehicle_id = data.get("vehicle_id", "AMB-108")
    speed_kmh = data.get("speed_kmh", 45.0)
    threshold_m = data.get("threshold_meters", active_simulation_state["threshold_meters"])

    # Phase 11 & 14: Input validation & error handling
    if ambulance_lat is None or ambulance_lng is None:
        return jsonify({
            "status": "error",
            "message": "Missing 'lat' or 'lng' coordinates."
        }), 400

    try:
        ambulance_lat = float(ambulance_lat)
        ambulance_lng = float(ambulance_lng)
        threshold_m = float(threshold_m)
    except (ValueError, TypeError):
        return jsonify({
            "status": "error",
            "message": "Coordinates and threshold must be numeric values."
        }), 400

    # Bounds check
    if not (-90.0 <= ambulance_lat <= 90.0) or not (-180.0 <= ambulance_lng <= 180.0):
        return jsonify({
            "status": "error",
            "message": "GPS coordinates out of valid planetary bounds."
        }), 400

    # Phase 9: Authorization check
    vehicle_profile = VEHICLES.get(vehicle_id, VEHICLES["AMB-108"])

    # Process telemetry through Signal Manager
    result = signal_manager.process_vehicle_telemetry(
        vehicle_id=vehicle_id,
        current_lat=ambulance_lat,
        current_lng=ambulance_lng,
        threshold_meters=threshold_m,
        speed_kmh=speed_kmh
    )

    # State changes audit logging
    for sig in result["signals"]:
        if sig["override_mode"] == "PREEMPTION" and sig.get("state") == "GREEN":
            log_event("PREEMPTION", f"Signal {sig['name']} set to GREEN for {vehicle_profile['name']} ({sig['distance_m']}m away)")
        elif sig["override_mode"] == "HOLD_CLEARING":
            log_event("CLEARANCE", f"{vehicle_profile['name']} cleared {sig['name']} - Normal cycle restoring")

    # Update active simulation state
    active_simulation_state["current_position"] = {"lat": ambulance_lat, "lng": ambulance_lng}
    active_simulation_state["vehicle_id"] = vehicle_id
    active_simulation_state["threshold_meters"] = threshold_m
    active_simulation_state["status"] = result["corridor_status"]

    return jsonify({
        "status": "success",
        "ambulance_position": {"lat": ambulance_lat, "lng": ambulance_lng},
        "vehicle": vehicle_profile,
        "speed_kmh": speed_kmh,
        "signals": result["signals"],
        "next_intersection": result["next_intersection"],
        "corridor_status": result["corridor_status"],
        "corridor_badge": result["corridor_badge"],
        "threshold_meters": threshold_m,
        "threshold_km": round(threshold_m / 1000.0, 3)
    })

@app.route("/api/reset", methods=["POST"])
def reset_signals():
    """Resets all signals to baseline normal traffic state."""
    signal_manager.reset()
    active_simulation_state["current_position"] = START_POINT
    active_simulation_state["status"] = "IDLE"
    log_event("RESET", "Simulation and traffic signals reset to baseline.")
    return jsonify({
        "status": "success",
        "message": "All corridor signals reset to normal.",
        "signals": [
            {
                "id": s["id"],
                "name": s["name"],
                "status": "RED (Normal Flow)",
                "color": "red",
                "state": "RED"
            } for s in INTERSECTIONS
        ]
    })

@app.route("/api/config", methods=["GET", "POST"])
def manage_config():
    """Retrieves or updates system configuration parameters."""
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        if "threshold_meters" in data:
            try:
                th = float(data["threshold_meters"])
                if 50.0 <= th <= 3000.0:
                    active_simulation_state["threshold_meters"] = th
                    log_event("CONFIG", f"Preemption distance threshold updated to {th}m")
            except ValueError:
                return jsonify({"status": "error", "message": "Invalid threshold value"}), 400

    return jsonify({
        "threshold_meters": active_simulation_state["threshold_meters"],
        "threshold_km": round(active_simulation_state["threshold_meters"] / 1000.0, 2),
        "start_point": START_POINT,
        "end_point": END_POINT,
        "waypoints": DEFAULT_ROUTE_WAYPOINTS,
        "intersections": INTERSECTIONS,
        "vehicles": list(VEHICLES.values())
    })

@app.route("/api/signals", methods=["GET"])
def get_signals():
    """Returns the current state of all traffic signals along the corridor."""
    signals_data = []
    for sig in INTERSECTIONS:
        runtime = signal_manager.signal_states.get(sig["id"], {})
        signals_data.append({
            "id": sig["id"],
            "name": sig["name"],
            "lat": sig["lat"],
            "lng": sig["lng"],
            "state": runtime.get("current_state", "RED"),
            "status": runtime.get("status_text", "RED (Normal Flow)"),
            "color": runtime.get("color", "red"),
            "cross_street": sig.get("cross_street", "")
        })
    return jsonify({"signals": signals_data})

@app.route("/api/audit-log", methods=["GET"])
def get_audit_log():
    """Returns the recent event audit log."""
    return jsonify({"events": system_audit_log})

@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "ONLINE",
        "system": "GreenCorridor AI",
        "mode": "Simulated GPS & Intersection Control",
        "intersections_tracked": len(INTERSECTIONS)
    })

# --- 2. EMBEDDED FRONTEND DASHBOARD (HTML + JS + LEAFLET.JS) ---

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GreenCorridor AI - Urban Emergency Traffic Clearing System</title>
    <!-- Leaflet CSS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0f172a;
            --bg-sidebar: #1e293b;
            --bg-card: #334155;
            --text-main: #f8fafc;
            --text-sub: #94a3b8;
            --cyan: #38bdf8;
            --green: #22c55e;
            --yellow: #eab308;
            --red: #ef4444;
            --border: rgba(255, 255, 255, 0.1);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Inter', sans-serif; display: flex; height: 100vh; background: var(--bg-dark); color: var(--text-main); overflow: hidden; }
        
        #sidebar {
            width: 440px;
            background: var(--bg-sidebar);
            display: flex;
            flex-direction: column;
            border-right: 1px solid var(--border);
            z-index: 1000;
            box-shadow: 4px 0 24px rgba(0,0,0,0.4);
        }
        
        .sidebar-header {
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
            background: rgba(15, 23, 42, 0.85);
        }
        .brand-title {
            font-size: 1.25rem;
            font-weight: 800;
            color: #fff;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .brand-subtitle {
            font-size: 0.72rem;
            color: var(--cyan);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 2px;
        }
        .sim-disclaimer {
            font-size: 0.68rem;
            color: #fbbf24;
            background: rgba(245, 158, 11, 0.12);
            border: 1px solid rgba(245, 158, 11, 0.25);
            padding: 3px 8px;
            border-radius: 4px;
            margin-top: 8px;
            display: inline-block;
        }
        
        .sidebar-content {
            flex: 1;
            overflow-y: auto;
            padding: 16px 20px;
            display: flex;
            flex-direction: column;
            gap: 14px;
        }
        
        /* Corridor Status Banner */
        .status-banner {
            padding: 12px 14px;
            border-radius: 8px;
            background: rgba(30, 41, 59, 0.8);
            border: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .status-banner.active {
            background: rgba(34, 197, 94, 0.15);
            border-color: rgba(34, 197, 94, 0.4);
        }
        .status-banner.warning {
            background: rgba(234, 179, 8, 0.15);
            border-color: rgba(234, 179, 8, 0.4);
        }
        .status-label { font-size: 0.7rem; color: var(--text-sub); text-transform: uppercase; font-weight: 600; }
        .status-value { font-size: 0.88rem; font-weight: 800; color: #fff; }
        
        /* Controls */
        .control-panel {
            background: var(--bg-card);
            border-radius: 8px;
            padding: 14px;
            border: 1px solid var(--border);
        }
        .btn-group { display: flex; gap: 8px; margin-top: 10px; }
        .btn {
            flex: 1;
            padding: 10px 12px;
            border: none;
            border-radius: 6px;
            font-weight: 700;
            font-size: 0.82rem;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
        }
        .btn-primary { background: #0284c7; color: #fff; }
        .btn-primary:hover { background: #0369a1; transform: translateY(-1px); }
        .btn-danger { background: #dc2626; color: #fff; }
        .btn-danger:hover { background: #b91c1c; }
        .btn-secondary { background: #475569; color: #fff; }
        .btn-secondary:hover { background: #334155; }
        
        .slider-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-top: 10px;
            font-size: 0.75rem;
            color: var(--text-sub);
        }
        .slider-ctrl { width: 100%; margin-top: 4px; accent-color: var(--cyan); }
        
        /* Telemetry Card */
        .telemetry-card {
            background: rgba(15, 23, 42, 0.6);
            border-radius: 8px;
            padding: 12px 14px;
            border: 1px solid var(--border);
        }
        .telemetry-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 8px;
            font-size: 0.78rem;
        }
        .telemetry-item strong { display: block; color: var(--text-sub); font-size: 0.7rem; }
        .telemetry-item span { color: #fff; font-weight: 700; }
        
        /* Traffic Signal Cards */
        .signal-card {
            background: var(--bg-card);
            border-radius: 8px;
            padding: 12px 14px;
            border: 1px solid var(--border);
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            transition: all 0.2s ease;
        }
        .signal-card.active-corridor {
            border-color: var(--green);
            background: rgba(34, 197, 94, 0.1);
            box-shadow: 0 0 12px rgba(34, 197, 94, 0.25);
        }
        .signal-info strong { font-size: 0.88rem; color: #fff; }
        .signal-info small { display: block; color: var(--text-sub); font-size: 0.72rem; }
        
        /* 3-Bulb Traffic Light Box */
        .traffic-light-fixture {
            background: #090d16;
            border: 2px solid #334155;
            border-radius: 14px;
            padding: 5px 6px;
            display: flex;
            flex-direction: column;
            gap: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.6);
        }
        .light-bulb {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            opacity: 0.2;
            transition: all 0.2s ease;
        }
        .light-bulb.red { background: #ef4444; }
        .light-bulb.yellow { background: #eab308; }
        .light-bulb.green { background: #22c55e; }
        
        .light-bulb.red.lit { opacity: 1; box-shadow: 0 0 8px #ef4444; }
        .light-bulb.yellow.lit { opacity: 1; box-shadow: 0 0 8px #eab308; }
        .light-bulb.green.lit { opacity: 1; box-shadow: 0 0 10px #22c55e; }
        
        /* Map Container */
        #map { flex: 1; height: 100%; position: relative; }
        
        /* Custom Leaflet Pulsing Markers */
        .ambulance-marker {
            font-size: 24px;
            text-align: center;
            filter: drop-shadow(0 0 6px rgba(239, 68, 68, 0.8));
            animation: pulse-veh 1s infinite alternate;
        }
        @keyframes pulse-veh {
            from { transform: scale(1); }
            to { transform: scale(1.15); }
        }
    </style>
</head>
<body>

<aside id="sidebar">
    <div class="sidebar-header">
        <div class="brand-title">
            <span>🚨</span> GreenCorridor AI
        </div>
        <div class="brand-subtitle">Automated Emergency Traffic Signal Preemption</div>
        <div class="sim-disclaimer">⚠️ Academic Demonstration • Simulated GPS & Traffic Signals</div>
    </div>

    <div class="sidebar-content">
        <!-- Live Corridor Status -->
        <div class="status-banner" id="status-banner">
            <div>
                <div class="status-label">Green Corridor Status</div>
                <div class="status-value" id="corridor-status-val">NORMAL (ROUTINE FLOW)</div>
            </div>
            <div id="status-badge" style="font-size: 1.2rem;">🚦</div>
        </div>

        <!-- Vehicle Controls -->
        <div class="control-panel">
            <label style="font-size: 0.72rem; color: var(--text-sub); text-transform: uppercase; font-weight: 700;">Emergency Vehicle</label>
            <select id="vehicle-select" style="width: 100%; padding: 8px; background: #1e293b; color: #fff; border: 1px solid var(--border); border-radius: 4px; font-weight: 600; margin-top: 4px;">
                <option value="AMB-108">🚑 EMS Ambulance 108 (Priority 1)</option>
                <option value="FT-101">🚒 Rescue Engine 101 (Fire Truck)</option>
            </select>

            <div class="btn-group">
                <button class="btn btn-primary" id="btn-start" onclick="toggleSimulation()">
                    <span id="btn-icon">▶️</span> <span id="btn-text">Start Dispatch</span>
                </button>
                <button class="btn btn-secondary" onclick="resetSimulation()">🔄 Reset</button>
            </div>

            <div class="slider-row">
                <span>Preemption Geofence:</span>
                <strong id="threshold-val" style="color: var(--cyan);">500 m</strong>
            </div>
            <input type="range" class="slider-ctrl" id="threshold-slider" min="200" max="1000" step="50" value="500" oninput="updateThreshold(this.value)">

            <div class="slider-row" style="margin-top: 8px;">
                <span>Simulation Speed:</span>
                <strong id="speed-val" style="color: #fff;">1x</strong>
            </div>
            <input type="range" class="slider-ctrl" id="speed-slider" min="1" max="5" value="1" oninput="updateSpeed(this.value)">
        </div>

        <!-- Telemetry Card -->
        <div class="telemetry-card">
            <div style="font-size: 0.72rem; color: var(--cyan); font-weight: 700; text-transform: uppercase;">Live Telemetry & Navigation</div>
            <div class="telemetry-grid">
                <div class="telemetry-item">
                    <strong>GPS Coordinates:</strong>
                    <span id="tel-gps">9.9816, 76.2999</span>
                </div>
                <div class="telemetry-item">
                    <strong>Estimated Speed:</strong>
                    <span id="tel-speed">45 km/h</span>
                </div>
                <div class="telemetry-item">
                    <strong>Next Intersection:</strong>
                    <span id="tel-next-sig">MG Road Junction</span>
                </div>
                <div class="telemetry-item">
                    <strong>Distance to Light:</strong>
                    <span id="tel-dist" style="color: var(--yellow);">-- m</span>
                </div>
            </div>
        </div>

        <!-- Intersections List -->
        <div>
            <div style="font-size: 0.75rem; color: var(--text-sub); text-transform: uppercase; font-weight: 700; margin-bottom: 8px;">Corridor Intersections (Kochi Metro Corridor)</div>
            <div id="signals-container">
                <!-- Dynamically populated -->
            </div>
        </div>
    </div>
</aside>

<main id="map"></main>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
    // Initialize Map centered on Ernakulam/Kochi
    const map = L.map('map', { zoomControl: false }).setView([10.0050, 76.3060], 13);
    L.control.zoom({ position: 'topright' }).addTo(map);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors | GreenCorridor AI'
    }).addTo(map);

    // Route coordinates following road trajectory
    const waypoints = [
        [9.9816, 76.2999], // General Hospital
        [9.9860, 76.3008], // Maharajas Ground
        [9.9920, 76.3020], // MG Road Junction
        [9.9985, 76.3040], // Kaloor Roundabout
        [10.0050, 76.3060], // Palarivattom Bypass
        [10.0115, 76.3080], // Changampuzha Park
        [10.0180, 76.3100], // Edappally Intersection
        [10.0220, 76.3112], // Toll Junction
        [10.0261, 76.3125]  // Medical Center
    ];

    // Baseline route polyline
    const routeLine = L.polyline(waypoints, { color: '#0284c7', weight: 6, opacity: 0.8 }).addTo(map);

    // Markers for Start & End
    L.marker(waypoints[0]).addTo(map).bindPopup("<b>General Hospital</b><br>Emergency Dispatch Point");
    L.marker(waypoints[waypoints.length - 1]).addTo(map).bindPopup("<b>Medical Center</b><br>Destination Trauma Unit");

    // Dynamic ambulance marker
    let ambulanceIcon = L.divIcon({
        html: '<div class="ambulance-marker">🚑</div>',
        className: 'veh-icon-wrap',
        iconSize: [32, 32],
        iconAnchor: [16, 16]
    });
    let ambulanceMarker = L.marker(waypoints[0], { icon: ambulanceIcon, zIndexOffset: 1000 }).addTo(map);

    // Dynamic preemption geofence circle around ambulance
    let geofenceCircle = L.circle(waypoints[0], {
        radius: 500,
        color: '#38bdf8',
        fillColor: '#38bdf8',
        fillOpacity: 0.08,
        weight: 1,
        dashArray: '4, 4'
    }).addTo(map);

    // Signal markers storage
    let signalMapMarkers = {};
    let simulationInterval = null;
    let isRunning = false;
    let currentStep = 0;
    const totalSteps = 60; // Smooth 60-step interpolation along road trajectory
    let simulationSpeed = 1;
    let thresholdMeters = 500;

    // Build dense interpolation path along all waypoints
    let pathPoints = [];
    for (let i = 0; i < waypoints.length - 1; i++) {
        let p1 = waypoints[i];
        let p2 = waypoints[i + 1];
        let subSteps = Math.floor(totalSteps / (waypoints.length - 1));
        for (let s = 0; s < subSteps; s++) {
            let lat = p1[0] + (p2[0] - p1[0]) * (s / subSteps);
            let lng = p1[1] + (p2[1] - p1[1]) * (s / subSteps);
            pathPoints.push([lat, lng]);
        }
    }
    pathPoints.push(waypoints[waypoints.length - 1]);

    // Initial signals load
    fetch('/api/signals')
        .then(res => res.json())
        .then(data => renderSignalsUI(data.signals));

    function toggleSimulation() {
        if (isRunning) {
            pauseSimulation();
        } else {
            startSimulation();
        }
    }

    function startSimulation() {
        isRunning = true;
        document.getElementById('btn-icon').innerText = '⏸️';
        document.getElementById('btn-text').innerText = 'Pause Dispatch';

        const stepDelay = Math.max(200, 1000 / simulationSpeed);

        simulationInterval = setInterval(() => {
            if (currentStep >= pathPoints.length) {
                clearInterval(simulationInterval);
                isRunning = false;
                document.getElementById('btn-icon').innerText = '▶️';
                document.getElementById('btn-text').innerText = 'Start Dispatch';
                document.getElementById('corridor-status-val').innerText = 'DESTINATION REACHED (ALL SIGNALS RESTORED)';
                document.getElementById('status-banner').className = 'status-banner';
                alert("🏥 Emergency vehicle has arrived at Medical Center! Green corridor concluded.");
                return;
            }

            let pt = pathPoints[currentStep];
            ambulanceMarker.setLatLng(pt);
            geofenceCircle.setLatLng(pt);

            let vehId = document.getElementById('vehicle-select').value;

            // Send telemetry to Flask backend
            fetch('/api/traffic-update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    lat: pt[0],
                    lng: pt[1],
                    vehicle_id: vehId,
                    threshold_meters: thresholdMeters,
                    speed_kmh: 48
                })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    updateDashboard(data);
                }
            })
            .catch(err => console.error("Telemetry update error:", err));

            currentStep++;
        }, stepDelay);
    }

    function pauseSimulation() {
        clearInterval(simulationInterval);
        isRunning = false;
        document.getElementById('btn-icon').innerText = '▶️';
        document.getElementById('btn-text').innerText = 'Resume Dispatch';
    }

    function resetSimulation() {
        pauseSimulation();
        currentStep = 0;
        ambulanceMarker.setLatLng(waypoints[0]);
        geofenceCircle.setLatLng(waypoints[0]);
        document.getElementById('btn-text').innerText = 'Start Dispatch';

        fetch('/api/reset', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                renderSignalsUI(data.signals);
                document.getElementById('corridor-status-val').innerText = 'NORMAL (ROUTINE FLOW)';
                document.getElementById('status-banner').className = 'status-banner';
                document.getElementById('tel-dist').innerText = '-- m';
            });
    }

    function updateThreshold(val) {
        thresholdMeters = parseFloat(val);
        document.getElementById('threshold-val').innerText = val + ' m';
        geofenceCircle.setRadius(thresholdMeters);
    }

    function updateSpeed(val) {
        simulationSpeed = parseInt(val);
        document.getElementById('speed-val').innerText = val + 'x';
        if (isRunning) {
            pauseSimulation();
            startSimulation();
        }
    }

    function updateDashboard(data) {
        // Update Corridor Status Banner
        const statusVal = document.getElementById('corridor-status-val');
        const banner = document.getElementById('status-banner');
        statusVal.innerText = data.corridor_status;
        banner.className = 'status-banner ' + data.corridor_badge;

        // Telemetry
        document.getElementById('tel-gps').innerText = `${data.ambulance_position.lat.toFixed(4)}, ${data.ambulance_position.lng.toFixed(4)}`;
        document.getElementById('tel-speed').innerText = `${data.speed_kmh} km/h`;

        if (data.next_intersection) {
            document.getElementById('tel-next-sig').innerText = data.next_intersection.name;
            document.getElementById('tel-dist').innerText = `${data.next_intersection.distance_m} m`;
            document.getElementById('tel-dist').style.color = data.next_intersection.color === 'green' ? '#22c55e' : '#eab308';
        } else {
            document.getElementById('tel-next-sig').innerText = 'Destination Approach';
            document.getElementById('tel-dist').innerText = 'Cleared';
        }

        renderSignalsUI(data.signals);
    }

    function renderSignalsUI(signals) {
        let container = document.getElementById('signals-container');
        container.innerHTML = '';

        signals.forEach(sig => {
            let isGreen = sig.state === 'GREEN';
            let isYellow = sig.state === 'YELLOW';
            let isRed = sig.state === 'RED' || !sig.state;

            let card = document.createElement('div');
            card.className = 'signal-card ' + (isGreen ? 'active-corridor' : '');
            card.innerHTML = `
                <div class="signal-info">
                    <strong>${sig.name}</strong>
                    <small>${sig.cross_street || 'Intersection'} • ${sig.distance_m ? sig.distance_m + 'm' : ''}</small>
                    <small style="color: ${isGreen ? '#22c55e' : (isYellow ? '#eab308' : '#ef4444')}; font-weight: 700; margin-top: 2px;">
                        ${sig.status}
                    </small>
                </div>
                <div class="traffic-light-fixture">
                    <div class="light-bulb red ${isRed ? 'lit' : ''}"></div>
                    <div class="light-bulb yellow ${isYellow ? 'lit' : ''}"></div>
                    <div class="light-bulb green ${isGreen ? 'lit' : ''}"></div>
                </div>
            `;
            container.appendChild(card);

            // Update Map Signal Markers
            if (!signalMapMarkers[sig.id]) {
                signalMapMarkers[sig.id] = L.circleMarker([sig.lat, sig.lng], {
                    radius: 12,
                    weight: 3,
                    opacity: 1
                }).addTo(map);
            }

            let markerColor = isGreen ? '#22c55e' : (isYellow ? '#eab308' : '#ef4444');
            signalMapMarkers[sig.id].setStyle({
                color: markerColor,
                fillColor: markerColor,
                fillOpacity: isGreen ? 0.9 : 0.6
            }).bindPopup(`<b>${sig.name}</b><br>Status: ${sig.status}`);
        });
    }
</script>

</body>
</html>
"""

if __name__ == "__main__":
    print("\n========================================================")
    print("GreenCorridor AI - Urban Emergency Traffic System")
    print("========================================================")
    print("Preemption Threshold: 500 meters (configurable)")
    print("Simulated GPS & Intersection Control: ACTIVE")
    print("Open your browser and navigate to: http://127.0.0.1:5000\n")
    app.run(debug=True, port=5000)
