# GreenCorridor AI

> **Urban Intelligence → Emergency Response Traffic Management**  
> *Dynamic Traffic Signal Preemption and Green Corridor Generation for Emergency Vehicles*

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-black.svg)](https://flask.palletsprojects.com/)
[![Leaflet.js](https://img.shields.io/badge/Leaflet-1.9.4-green.svg)](https://leafletjs.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 1. Project Title & Overview

**GreenCorridor AI** is an intelligent urban traffic management and decision support system engineered to eliminate critical transit delays for emergency vehicles (such as ambulances and fire engines) navigating congested city intersections.

The system continuously tracks the GPS coordinates of dispatched emergency vehicles in real time. When an emergency vehicle approaches a traffic intersection within a configurable geofence threshold (e.g., 500 meters), the system detects the upcoming signal, manages safe phase transitions, and dynamically turns the signal to **GREEN**, clearing standing vehicular queues before the emergency vehicle arrives. Once the vehicle clears the intersection, the system smoothly restores the normal civilian signal cycle.

---

## 2. Problem Statement

In metropolitan areas, emergency vehicles lose vital minutes stuck behind red lights and static traffic gridlock. Seconds saved during medical emergencies (cardiac arrest, stroke, severe trauma) directly correlate with patient survival rates.

Traditional traffic signal systems operate on rigid, fixed-time schedules or isolated local induction loops that lack situational awareness of oncoming emergency responders. Manual police escorts or ad-hoc green corridors require labor-intensive manual coordination and cannot scale across citywide operations.

---

## 3. Existing Solution (Baseline)

The original prototype provided an initial concept:
* A Flask web server accepting HTTP POST requests with vehicle coordinates.
* A basic Haversine distance check against 3 fixed intersections in Kochi (MG Road, Palarivattom, Edappally).
* A single 500m hardcoded threshold that toggled signals between text-only "RED" and "GREEN".
* A basic Leaflet map with a straight-line interpolation between start and destination.

### Limitations of the Original Implementation:
1. **Unrealistic Routing:** Interpolated in a straight line between endpoints rather than traversing actual road network waypoints.
2. **Abrupt Signal Jumps:** Instantly toggled between RED and GREEN with no safety clearance transitions (missing YELLOW clearance phase).
3. **Hardcoded Threshold:** 500 meters hardcoded across logic without runtime configurability.
4. **Encoding Issues:** Corrupted characters in UI text and emojis (`dYs"`, `dYs?`, `30%?"50%`).
5. **No Input Validation:** Crashed on malformed payloads or invalid GPS inputs.
6. **Single Vehicle Only:** No multi-vehicle or agency support.
7. **Static Civilian State:** Signals lacked a realistic civilian cycle when no emergency vehicle was approaching.

---

## 4. Proposed Improved Solution

This improved version preserves the core concept, architecture, and technology stack while introducing realistic operational mechanics:
* **Road-Constrained Path Simulation:** Interpolates along actual street geometry through designated intersection waypoints.
* **Safety State Machine:** Implements realistic signal phases: `RED (Normal)` → `YELLOW (Cross-Traffic Clearance)` → `GREEN (Preemption Active)` → `YELLOW (Cycle Recovery)` → `NORMAL`.
* **Configurable Thresholds:** Preemption radius can be adjusted dynamically (200m–1000m) via the UI slider or API without code changes.
* **Multi-Intersection Selectivity:** Intelligently identifies the **next relevant upcoming intersection** rather than preempting unrelated signals.
* **Vehicle Telemetry Dashboard:** Displays vehicle identifier, type, live GPS coordinates, speed, upcoming intersection, distance in meters, and signal state.
* **Green Corridor Status Hierarchy:** Standardized state management (`NORMAL`, `EMERGENCY VEHICLE EN ROUTE`, `APPROACHING INTERSECTION`, `GREEN CORRIDOR ACTIVE`, `VEHICLE PASSED`).
* **Input Validation & Error Handling:** Comprehensive payload verification, GPS boundary validation, and graceful error responses.
* **Authentic 3-Bulb Signal Visualization:** Physical traffic light fixtures with active bulb illumination (🔴 🟡 🟢) on both dashboard and map.

---

## 5. System Workflow

```
Emergency Vehicle Dispatched
            ↓
GPS / Location Telemetry Broadcast
            ↓
Server Validates Coordinates & Vehicle Authorization
            ↓
Calculates Haversine Distance to Corridor Intersections
            ↓
Identifies Immediate Next Upcoming Intersection
            ↓
Is Distance <= Threshold (e.g., 500m) and Vehicle Approaching?
       ├── NO  → Maintain Normal Civilian Signal Cycle
       └── YES → Trigger Safe Preemption Phase:
                    1. Cross-Traffic Safe Clearance (YELLOW)
                    2. Emergency Route Switches to GREEN
                    3. Traffic Clears Ahead of Vehicle
            ↓
Vehicle Traverses Intersection (Distance < 50m Clearance Zone)
            ↓
Vehicle Clears Intersection (Distance Increases)
            ↓
Hold Window & Recovery Transition (YELLOW)
            ↓
Normal Multi-Phase Civilian Cycle Restored
            ↓
Vehicle Reaches Hospital Destination
```

---

## 6. Main Features

1. **Automated Green Wave Preemption:** Detects approaching vehicles within configurable geofence (200–1000m) and grants priority green signals.
2. **Safety-First Signal State Machine:** Prevents abrupt phase collisions by executing yellow clearance transitions before granting green waves.
3. **Realistic Street-Level Simulation:** Vehicle smoothly navigates waypoints from General Hospital to Medical Center along actual Kochi arterial roads.
4. **Interactive Leaflet Command Center:**
   - Visual route polyline with active preemption geofence visualization.
   - Animated emergency vehicle marker with siren indicator.
   - Interactive intersection pins with live 3-bulb traffic light fixtures.
   - Simulation speed controls (1x, 2x, 5x), pause, resume, and reset.
5. **Multi-Vehicle Registry:** Supports multiple emergency agencies (EMS Ambulance 108 and Rescue Engine 101).
6. **Live Telemetry Readout:** Displays latitude, longitude, speed, next signal, and distance in meters.
7. **RESTful API Suite:** Endpoints for telemetry updates, signal inspection, configuration updates, and baseline resets.

---

## 7. Technology Stack

* **Backend:** Python 3.10+, Flask 3.0+
* **Frontend:** HTML5, CSS3 (Modern Dark Theme), JavaScript (ES6+)
* **Mapping & GIS:** Leaflet.js 1.9.4, OpenStreetMap
* **Mathematical Utilities:** Haversine Great-Circle Distance, Great-Circle Initial Bearing

---

## 8. GPS / Location Handling

> **Demonstration Notice:**  
> In this prototype, GPS coordinates are generated via a realistic waypoint interpolation simulator that mirrors vehicle travel along Ernakulam's MG Road and NH Bypass corridor.  
> The backend API (`POST /api/traffic-update`) is fully hardware-ready: it accepts standard JSON payloads containing `lat`, `lng`, `speed_kmh`, and `vehicle_id` from onboard GPS telematics units, mobile dispatch apps, or OBD-II vehicle trackers.

---

## 9. Traffic Signal Intersections Tracked

| Intersection ID | Name | Coordinates (Lat, Lng) | Normal State | Speed Limit |
| :--- | :--- | :--- | :---: | :---: |
| `SIG_1` | MG Road Junction | `9.9920, 76.3020` | RED (Normal Flow) | 40 km/h |
| `SIG_2` | Palarivattom Bypass | `10.0050, 76.3060` | RED (Normal Flow) | 50 km/h |
| `SIG_3` | Edappally Intersection | `10.0180, 76.3100` | RED (Normal Flow) | 50 km/h |

---

## 10. Installation & Setup Guide

### 1. Prerequisites
Ensure Python 3.10 or higher is installed on your system.

### 2. Navigate to Project Directory
```bash
cd C:\Users\Sreenanda\Desktop\projecth\green_corridor
```

### 3. Install Dependencies
```bash
pip install flask
```

### 4. Run the Application
```bash
python app.py
```

### 5. Access the Web Dashboard
Open your web browser and navigate to:  
👉 **`http://127.0.0.1:5000`**

---

## 11. Testing & Demonstration Scenarios

| Test Scenario | Action | Expected System Behavior | Result |
| :--- | :--- | :--- | :---: |
| **TEST 1: Baseline Idle** | Load application without starting dispatch. | All signals remain in normal flow (RED/Civilian cycle). Corridor status is `NORMAL`. | PASS |
| **TEST 2: Vehicle Far Away** | Start dispatch; vehicle is > 500m from MG Road Junction. | Signal remains RED. Telemetry shows decreasing distance (e.g., 750m, 620m). | PASS |
| **TEST 3: Geofence Entry** | Vehicle crosses within 500m threshold of MG Road Junction. | Signal transitions to `GREEN (Corridor Preemption Active)`. Active green glow appears on card and map. | PASS |
| **TEST 4: Intersection Clearance** | Vehicle passes MG Road Junction and moves past 50m clearance zone. | Signal transitions to `YELLOW` clearance, then restores normal cycle. Next signal (Palarivattom) becomes active target. | PASS |
| **TEST 5: Sequential Intersections** | Vehicle travels along full corridor. | Each intersection turns green sequentially as approached and restores after passage. Unrelated distant signals do not pre-trigger. | PASS |
| **TEST 6: Threshold Adjustment** | Move threshold slider to 700m or 300m. | Geofence circle on map resizes immediately; preemption triggers at updated distance. | PASS |
| **TEST 7: Invalid GPS Handling** | POST malformed GPS payload to `/api/traffic-update`. | API responds with HTTP 400 Bad Request and descriptive error message without crashing. | PASS |

---

## 12. REST API Documentation

### `POST /api/traffic-update`
Receives vehicle telemetry and updates signal states.
* **Payload:**
  ```json
  {
    "lat": 9.9910,
    "lng": 76.3018,
    "vehicle_id": "AMB-108",
    "speed_kmh": 45.0,
    "threshold_meters": 500.0
  }
  ```
* **Response (HTTP 200):**
  ```json
  {
    "status": "success",
    "corridor_status": "GREEN CORRIDOR ACTIVE",
    "next_intersection": {
      "id": "SIG_1",
      "name": "MG Road Junction",
      "distance_m": 120.4,
      "color": "green"
    },
    "signals": [...]
  }
  ```

### `POST /api/reset`
Resets all signals to baseline normal state.

### `GET /api/signals`
Returns current states of all tracked intersections.

### `GET /api/config` & `POST /api/config`
Retrieves or updates threshold parameters.

### `GET /api/health`
Health check endpoint confirming system status.

---

## 13. Limitations

1. **Hardware Actuation:** In this prototype, traffic light control is software-simulated. Real-world deployment requires integration with NEMA TS2 / 170 / 2070 traffic signal controllers or SCATS/SCOOT municipal APIs.
2. **Civilian Cross-Traffic Simulation:** Civilian queue lengths are not physically tracked by induction loops or computer-vision camera feeds in this version.
3. **Fixed Route:** The demonstration route is configured between General Hospital and Medical Center in Kochi. Multi-route dynamic routing via OSRM/GraphHopper is a target for future enhancement.

---

## 14. Future Improvements

1. **Dynamic Routing Engine:** Integrate OpenStreetMap Routing Machine (OSRM) for turn-by-turn routing based on real-time traffic congestion.
2. **V2X (Vehicle-to-Everything) Communication:** Implement DSRC / C-V2X (Cellular V2X) communication standards for low-latency preemption requests.
3. **Computer Vision Congestion Detection:** Analyze intersection CCTV feeds with YOLO to gauge queue clearance times dynamically before preemption.
4. **Physical Controller Integration:** Connect to Raspberry Pi / ESP32 hardware relays controlling physical scale-model LED traffic light poles.

---

## 15. License

This project is licensed under the MIT License.
