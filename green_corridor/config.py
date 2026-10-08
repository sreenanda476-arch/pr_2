"""
GreenCorridor AI - Configuration & Constants
Defines intersections, emergency vehicle profiles, route coordinates, and safety thresholds.
"""

# Default preemption distance threshold in meters and kilometers
DEFAULT_THRESHOLD_METERS = 500.0
DEFAULT_THRESHOLD_KM = DEFAULT_THRESHOLD_METERS / 1000.0

# Safe clearance distance in meters (vehicle has passed intersection)
CLEARANCE_DISTANCE_METERS = 50.0

# Normal traffic signal cycle timings in seconds (for simulated ambient civilian traffic)
NORMAL_CYCLE_SECONDS = {
    "GREEN": 25,
    "YELLOW": 4,
    "RED": 30
}

# Safety transition delay in seconds (cross-traffic yellow clear before emergency green)
YELLOW_CLEARANCE_DELAY_SECONDS = 3.0

# Preemption signal hold duration in seconds after vehicle passes
SIGNAL_RESTORE_HOLD_SECONDS = 5.0

# Default coordinates (Kochi/Ernakulam area)
START_POINT = {"lat": 9.9816, "lng": 76.2999, "label": "Start: General Hospital"}
END_POINT = {"lat": 10.0261, "lng": 76.3125, "label": "Destination: Medical Center"}

# Route Waypoints (General Hospital to Medical Center via MG Road, Palarivattom, Edappally)
DEFAULT_ROUTE_WAYPOINTS = [
    {"lat": 9.9816, "lng": 76.2999, "name": "General Hospital (Start)"},
    {"lat": 9.9860, "lng": 76.3008, "name": "Maharajas College Ground"},
    {"lat": 9.9920, "lng": 76.3020, "name": "MG Road Junction"},
    {"lat": 9.9985, "lng": 76.3040, "name": "Kaloor Stadium Roundabout"},
    {"lat": 10.0050, "lng": 76.3060, "name": "Palarivattom Bypass"},
    {"lat": 10.0115, "lng": 76.3080, "name": "Changampuzha Park"},
    {"lat": 10.0180, "lng": 76.3100, "name": "Edappally Intersection"},
    {"lat": 10.0220, "lng": 76.3112, "name": "Toll Junction"},
    {"lat": 10.0261, "lng": 76.3125, "name": "Medical Center (Destination)"}
]

# Traffic Signal Intersections along the corridor
INTERSECTIONS = [
    {
        "id": "SIG_1",
        "name": "MG Road Junction",
        "lat": 9.9920,
        "lng": 76.3020,
        "normal_state": "RED",
        "order": 1,
        "cross_street": "Jos Junction Link",
        "speed_limit_kmh": 40
    },
    {
        "id": "SIG_2",
        "name": "Palarivattom Bypass",
        "lat": 10.0050,
        "lng": 76.3060,
        "normal_state": "RED",
        "order": 2,
        "cross_street": "Civil Line Road",
        "speed_limit_kmh": 50
    },
    {
        "id": "SIG_3",
        "name": "Edappally Intersection",
        "lat": 10.0180,
        "lng": 76.3100,
        "normal_state": "RED",
        "order": 3,
        "cross_street": "NH 66 Bypass Highway",
        "speed_limit_kmh": 50
    }
]

# Emergency Vehicle Profiles
VEHICLES = {
    "AMB-108": {
        "id": "AMB-108",
        "name": "EMS Ambulance 108",
        "type": "Ambulance",
        "agency": "State Emergency Medical Service",
        "priority_level": 1,
        "icon": "ambulance",
        "callsign": "Med-Rescue-1"
    },
    "FT-101": {
        "id": "FT-101",
        "name": "Rescue Engine 101",
        "type": "Fire Truck",
        "agency": "Fire & Rescue Brigade",
        "priority_level": 1,
        "icon": "fire_truck",
        "callsign": "Bravo-Lead-Fire"
    }
}
