"""
Hospital Emergency Capacity Prediction System
Configuration and Threshold Settings
"""

from typing import Dict

# Default capacity classification thresholds
DEFAULT_THRESHOLDS = {
    "NORMAL_MAX": 60.0,
    "BUSY_MAX": 75.0,
    "HIGH_MAX": 90.0,
    "CRITICAL_MAX": 100.0
}

# ICU thresholds
DEFAULT_ICU_THRESHOLDS = {
    "NORMAL_MAX": 65.0,
    "BUSY_MAX": 80.0,
    "HIGH_MAX": 90.0,
    "CRITICAL_MAX": 100.0
}

# Global runtime state for dynamic threshold updates
current_thresholds = DEFAULT_THRESHOLDS.copy()
current_icu_thresholds = DEFAULT_ICU_THRESHOLDS.copy()

def get_thresholds() -> Dict[str, float]:
    return current_thresholds

def update_thresholds(normal: float, busy: float, high: float, critical: float):
    global current_thresholds
    current_thresholds["NORMAL_MAX"] = float(normal)
    current_thresholds["BUSY_MAX"] = float(busy)
    current_thresholds["HIGH_MAX"] = float(high)
    current_thresholds["CRITICAL_MAX"] = float(critical)
    return current_thresholds
