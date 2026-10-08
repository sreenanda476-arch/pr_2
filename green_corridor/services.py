"""
GreenCorridor AI - Services & Logic Engine
Handles distance calculations, heading/bearing tracking, traffic signal safety state machines,
and green corridor preemption management.
"""

import math
import time
from typing import Dict, Any, List, Optional
from config import (
    DEFAULT_THRESHOLD_METERS,
    CLEARANCE_DISTANCE_METERS,
    INTERSECTIONS,
    VEHICLES,
    SIGNAL_RESTORE_HOLD_SECONDS
)

def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates great-circle distance in kilometers between two GPS points using the Haversine formula.
    """
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calculate_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates distance in meters between two GPS coordinates."""
    return calculate_distance_km(lat1, lon1, lat2, lon2) * 1000.0

def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates bearing in degrees (0 - 360) from point 1 to point 2."""
    dlon = math.radians(lon2 - lon1)
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    x = math.sin(dlon) * math.cos(lat2_r)
    y = math.cos(lat1_r) * math.sin(lat2_r) - (math.sin(lat1_r) * math.cos(lat2_r) * math.cos(dlon))
    initial_bearing = math.atan2(x, y)
    initial_bearing = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360
    return round(compass_bearing, 1)

class TrafficSignalManager:
    """
    Manages the lifecycle, safety transitions, and preemption state of traffic signals.
    """
    def __init__(self, intersections_list: List[Dict[str, Any]] = INTERSECTIONS):
        self.intersections = {item["id"]: dict(item) for item in intersections_list}
        self.signal_states = {}
        self.reset()

    def reset(self):
        """Resets all signals back to normal default state."""
        for sig_id in self.intersections:
            self.signal_states[sig_id] = {
                "id": sig_id,
                "current_state": "RED",            # "RED", "YELLOW", "GREEN"
                "override_mode": "NORMAL",         # "NORMAL", "TRANSITIONING", "PREEMPTION", "HOLD_CLEARING"
                "active_vehicle_id": None,
                "preempted_at": None,
                "cleared_at": None,
                "last_distance_m": float("inf"),
                "status_text": "RED (Normal Flow)",
                "color": "red"
            }

    def process_vehicle_telemetry(
        self,
        vehicle_id: str,
        current_lat: float,
        current_lng: float,
        threshold_meters: float = DEFAULT_THRESHOLD_METERS,
        speed_kmh: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Evaluates vehicle position against upcoming intersections.
        Identifies relevant upcoming signals, enforces safety transition logic,
        and computes corridor status.
        """
        now = time.time()
        updated_signals = []
        next_intersection = None
        min_distance_to_next = float("inf")
        corridor_active_for_any = False
        approaching_any = False
        vehicle_just_passed = False

        # Sort intersections sequentially by corridor order
        sorted_sigs = sorted(self.intersections.values(), key=lambda x: x.get("order", 0))

        for sig_meta in sorted_sigs:
            sig_id = sig_meta["id"]
            state = self.signal_states[sig_id]
            sig_lat = sig_meta["lat"]
            sig_lng = sig_meta["lng"]

            dist_m = calculate_distance_meters(current_lat, current_lng, sig_lat, sig_lng)
            dist_km = dist_m / 1000.0
            prev_dist = state["last_distance_m"]

            # Determine whether vehicle is approaching or has passed this intersection
            # Corridor travels South to North (latitude 9.9816 -> 10.0261)
            has_crossed_geographically = current_lat > (sig_lat + 0.0002)
            dist_increasing = dist_m > (prev_dist + 2.0) if prev_dist != float("inf") else False
            is_approaching = (not has_crossed_geographically) and (dist_m < prev_dist if prev_dist != float("inf") else True)

            # Detect whether vehicle has cleared this intersection:
            # Vehicle was in preemption or close (< 100m), and has now crossed north or distance is increasing
            if (state["override_mode"] == "PREEMPTION" or prev_dist < 100.0) and (has_crossed_geographically or dist_increasing):
                state["override_mode"] = "HOLD_CLEARING"
                state["cleared_at"] = now
                state["active_vehicle_id"] = None
                state["current_state"] = "YELLOW"
                state["status_text"] = "YELLOW (Clearing & Restoring Cycle)"
                state["color"] = "yellow"
                vehicle_just_passed = True

            # If currently in HOLD_CLEARING and hold window has elapsed, restore normal
            if state["override_mode"] == "HOLD_CLEARING":
                elapsed = now - (state["cleared_at"] or now)
                if elapsed >= SIGNAL_RESTORE_HOLD_SECONDS or dist_m > (threshold_meters * 0.8):
                    state["override_mode"] = "NORMAL"
                    state["current_state"] = "RED"
                    state["status_text"] = "RED (Normal Flow Restored)"
                    state["color"] = "red"

            # Check if vehicle is approaching and within preemption threshold
            if dist_m <= threshold_meters and is_approaching and state["override_mode"] != "HOLD_CLEARING":
                approaching_any = True

                # Safety preemption: transition to GREEN
                if state["override_mode"] != "PREEMPTION":
                    state["override_mode"] = "PREEMPTION"
                    state["current_state"] = "GREEN"
                    state["status_text"] = "GREEN (Corridor Preemption Active)"
                    state["color"] = "green"
                    state["active_vehicle_id"] = vehicle_id
                    state["preempted_at"] = now

                corridor_active_for_any = True
            elif state["override_mode"] == "PREEMPTION" and (has_crossed_geographically or dist_increasing):
                state["override_mode"] = "HOLD_CLEARING"
                state["current_state"] = "YELLOW"
                state["status_text"] = "YELLOW (Clearing & Restoring Cycle)"
                state["color"] = "yellow"
                state["active_vehicle_id"] = None

            # Track distance
            state["last_distance_m"] = dist_m

            # Identify the closest upcoming intersection ahead
            if is_approaching and dist_m < min_distance_to_next and dist_m > CLEARANCE_DISTANCE_METERS:
                min_distance_to_next = dist_m
                next_intersection = {
                    "id": sig_id,
                    "name": sig_meta["name"],
                    "distance_m": round(dist_m, 1),
                    "distance_km": round(dist_km, 2),
                    "status": state["status_text"],
                    "color": state["color"],
                    "cross_street": sig_meta.get("cross_street", "")
                }

            updated_signals.append({
                "id": sig_id,
                "name": sig_meta["name"],
                "lat": sig_lat,
                "lng": sig_lng,
                "distance_km": round(dist_km, 2),
                "distance_m": round(dist_m, 1),
                "status": state["status_text"],
                "color": state["color"],
                "state": state["current_state"],
                "override_mode": state["override_mode"],
                "cross_street": sig_meta.get("cross_street", "")
            })

        # Resolve Global Corridor Status (Phase 8 Requirements)
        if corridor_active_for_any:
            corridor_status = "GREEN CORRIDOR ACTIVE"
            corridor_badge = "active"
        elif vehicle_just_passed:
            corridor_status = "VEHICLE PASSED (RESTORING SIGNALS)"
            corridor_badge = "clearing"
        elif approaching_any:
            corridor_status = "APPROACHING INTERSECTION"
            corridor_badge = "warning"
        elif next_intersection is not None:
            corridor_status = "EMERGENCY VEHICLE EN ROUTE"
            corridor_badge = "info"
        else:
            corridor_status = "NORMAL (ALL SIGNALS ROUTINE)"
            corridor_badge = "normal"

        return {
            "signals": updated_signals,
            "next_intersection": next_intersection,
            "corridor_status": corridor_status,
            "corridor_badge": corridor_badge,
            "threshold_meters": threshold_meters
        }

# Singleton instance
signal_manager = TrafficSignalManager()
