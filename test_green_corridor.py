"""
Automated Test Suite for GreenCorridor AI
Tests all Phase 15 scenarios:
- Baseline state
- Far distance behavior
- Preemption within threshold
- Clearance and signal recovery
- Multiple sequential intersections
- Invalid GPS handling
- Threshold customization
- Multi-vehicle validation
"""

import sys
import os

# Add target directory to sys.path
sys.path.insert(0, r"C:\Users\Sreenanda\Desktop\projecth\green_corridor")

from app import app
from config import INTERSECTIONS, START_POINT, END_POINT, DEFAULT_THRESHOLD_METERS
from services import calculate_distance_meters, signal_manager

def run_tests():
    print("=" * 60)
    print("🚦 RUNNING GREENCORRIDOR AI AUTOMATED TEST SUITE")
    print("=" * 60)

    client = app.test_client()

    # TEST 1: Baseline Idle
    print("\n[TEST 1] Baseline Idle Verification...")
    res = client.get("/api/signals")
    assert res.status_code == 200, "Failed to get signals"
    data = res.get_json()
    assert len(data["signals"]) == 3, "Expected 3 intersections"
    for sig in data["signals"]:
        assert sig["state"] == "RED", f"Expected RED state, got {sig['state']}"
    print("  -> PASS: All signals in normal flow (RED).")

    # TEST 2: Vehicle far away (> 500m)
    print("\n[TEST 2] Vehicle at Start Point (> 500m from all signals)...")
    payload = {
        "lat": START_POINT["lat"],
        "lng": START_POINT["lng"],
        "vehicle_id": "AMB-108",
        "speed_kmh": 40.0,
        "threshold_meters": 500.0
    }
    res = client.post("/api/traffic-update", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["corridor_status"] != "GREEN CORRIDOR ACTIVE", "Corridor should NOT be active when far"
    assert data["next_intersection"]["name"] == "MG Road Junction"
    assert data["next_intersection"]["distance_m"] > 500.0
    print(f"  -> PASS: Distance is {data['next_intersection']['distance_m']}m (> 500m). Signal remains normal.")

    # TEST 3: Vehicle approaches within threshold (<= 500m)
    print("\n[TEST 3] Vehicle Approaches MG Road Junction within 500m...")
    # MG Road is at 9.9920, 76.3020. Put vehicle at ~200m away (9.9905, 76.3015)
    near_payload = {
        "lat": 9.9905,
        "lng": 76.3015,
        "vehicle_id": "AMB-108",
        "speed_kmh": 50.0,
        "threshold_meters": 500.0
    }
    res = client.post("/api/traffic-update", json=near_payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["corridor_status"] == "GREEN CORRIDOR ACTIVE", f"Expected GREEN CORRIDOR ACTIVE, got {data['corridor_status']}"
    mg_sig = next(s for s in data["signals"] if s["id"] == "SIG_1")
    assert mg_sig["state"] == "GREEN", f"Expected MG Road to be GREEN, got {mg_sig['state']}"
    assert "Corridor Preemption Active" in mg_sig["status"]
    print(f"  -> PASS: MG Road Junction preemption triggered to GREEN ({mg_sig['distance_m']}m away).")

    # TEST 4: Vehicle clears intersection
    print("\n[TEST 4] Vehicle Passes MG Road Junction and moves past clearance zone...")
    # Put vehicle 100m past MG Road Junction (e.g. at 9.9935, 76.3025)
    past_payload = {
        "lat": 9.9935,
        "lng": 76.3025,
        "vehicle_id": "AMB-108",
        "speed_kmh": 50.0,
        "threshold_meters": 500.0
    }
    res = client.post("/api/traffic-update", json=past_payload)
    assert res.status_code == 200
    data = res.get_json()
    mg_sig = next(s for s in data["signals"] if s["id"] == "SIG_1")
    assert mg_sig["state"] in ["YELLOW", "RED"], f"Expected YELLOW or RED after clearing, got {mg_sig['state']}"
    print(f"  -> PASS: MG Road transitioned out of preemption to {mg_sig['state']}.")

    # TEST 5: Multiple Intersections (Second intersection - Palarivattom)
    print("\n[TEST 5] Multiple Intersections: Approaching Second Intersection (Palarivattom)...")
    # Palarivattom is at 10.0050, 76.3060. Put vehicle at ~150m away (10.0040, 76.3055)
    pal_payload = {
        "lat": 10.0040,
        "lng": 76.3055,
        "vehicle_id": "AMB-108",
        "speed_kmh": 50.0,
        "threshold_meters": 500.0
    }
    res = client.post("/api/traffic-update", json=pal_payload)
    assert res.status_code == 200
    data = res.get_json()
    pal_sig = next(s for s in data["signals"] if s["id"] == "SIG_2")
    edap_sig = next(s for s in data["signals"] if s["id"] == "SIG_3")
    assert pal_sig["state"] == "GREEN", "Palarivattom should be GREEN"
    assert edap_sig["state"] == "RED", "Edappally (far ahead) should remain RED"
    print("  -> PASS: Palarivattom is GREEN, while Edappally remains RED (only relevant signal preempted).")

    # TEST 6: Invalid GPS Data
    print("\n[TEST 6] Invalid GPS Data Error Handling...")
    bad_payload = {"lat": "invalid_latitude", "lng": 76.3000}
    res = client.post("/api/traffic-update", json=bad_payload)
    assert res.status_code == 400, f"Expected 400 for bad lat, got {res.status_code}"
    print("  -> PASS: Handled invalid latitude with HTTP 400 error.")

    out_of_bounds = {"lat": 195.0, "lng": 76.3000}
    res = client.post("/api/traffic-update", json=out_of_bounds)
    assert res.status_code == 400, f"Expected 400 for out-of-bounds, got {res.status_code}"
    print("  -> PASS: Handled out-of-bounds latitude with HTTP 400 error.")

    # TEST 7: Threshold Configuration
    print("\n[TEST 7] Threshold Configuration Update via API...")
    res = client.post("/api/config", json={"threshold_meters": 800.0})
    assert res.status_code == 200
    res_cfg = client.get("/api/config")
    cfg_data = res_cfg.get_json()
    assert cfg_data["threshold_meters"] == 800.0, f"Expected 800m, got {cfg_data['threshold_meters']}"
    print("  -> PASS: Threshold successfully updated to 800.0 meters.")

    # TEST 8: Multi-Vehicle Support
    print("\n[TEST 8] Multi-Vehicle Support (Fire Truck FT-101)...")
    ft_payload = {
        "lat": 9.9905,
        "lng": 76.3015,
        "vehicle_id": "FT-101",
        "speed_kmh": 55.0,
        "threshold_meters": 800.0
    }
    res = client.post("/api/traffic-update", json=ft_payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["vehicle"]["type"] == "Fire Truck", f"Expected Fire Truck, got {data['vehicle']['type']}"
    assert data["vehicle"]["name"] == "Rescue Engine 101"
    print("  -> PASS: Rescue Engine 101 successfully recognized and processed.")

    # Reset
    client.post("/api/reset")
    print("\n" + "=" * 60)
    print("🎉 ALL 8 TEST SCENARIOS PASSED WITH 100% SUCCESS!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
