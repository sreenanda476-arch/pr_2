"""
Hospital Emergency Capacity Prediction System
Prediction & Inference Engine

Provides multi-horizon predictions for:
- ED Bed Occupancy % (+1h, +2h, +3h, +6h)
- ED Patient Load (+1h, +2h, +3h, +6h)
- ICU Occupancy % (+1h, +2h, +3h, +6h)
- Capacity Classification (NORMAL, BUSY, HIGH, CRITICAL, OVER CAPACITY)
- Time-to-saturation estimation & early warning flags
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, List

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")

class CapacityPredictor:
    def __init__(self, models_dir=MODELS_DIR):
        self.models_dir = models_dir
        self.models = {}
        self.metadata = {}
        self.load_artifacts()
        
    def load_artifacts(self):
        metadata_file = os.path.join(self.models_dir, "model_metadata.json")
        if os.path.exists(metadata_file):
            with open(metadata_file, "r") as f:
                self.metadata = json.load(f)
                
        # Load regressors
        for h in [1, 2, 3, 6]:
            ed_occ_path = os.path.join(self.models_dir, f"rf_ed_occupancy_{h}h.joblib")
            if os.path.exists(ed_occ_path):
                self.models[f"ed_occupancy_{h}h"] = joblib.load(ed_occ_path)
                
            ed_pts_path = os.path.join(self.models_dir, f"rf_ed_patients_{h}h.joblib")
            if os.path.exists(ed_pts_path):
                self.models[f"ed_patients_{h}h"] = joblib.load(ed_pts_path)
                
            icu_path = os.path.join(self.models_dir, f"rf_icu_occupancy_{h}h.joblib")
            if os.path.exists(icu_path):
                self.models[f"icu_occupancy_{h}h"] = joblib.load(icu_path)
                
        # Load classifier
        cls_path = os.path.join(self.models_dir, "rf_capacity_classifier_1h.joblib")
        if os.path.exists(cls_path):
            self.models["capacity_classifier_1h"] = joblib.load(cls_path)
            
    def prepare_feature_vector(self, data: Dict[str, Any]) -> pd.DataFrame:
        features_list = self.metadata.get("features", [])
        
        # Extract inputs with defaults
        hour = int(data.get("hour", 14))
        day_of_week = int(data.get("day_of_week", 2))
        is_weekend = int(data.get("is_weekend", 1 if day_of_week in [5, 6] else 0))
        is_holiday = int(data.get("is_holiday", 0))
        
        total_ed_beds = float(data.get("total_emergency_beds", 50))
        curr_patients = float(data.get("current_emergency_patients", 35))
        occupied_ed = float(data.get("occupied_emergency_beds", min(curr_patients, total_ed_beds)))
        avail_ed = float(data.get("available_emergency_beds", max(0.0, total_ed_beds - occupied_ed)))
        
        admissions = float(data.get("new_emergency_admissions", 12))
        discharges = float(data.get("emergency_discharges", 8))
        
        total_icu_beds = float(data.get("total_icu_beds", 16))
        occupied_icu = float(data.get("occupied_icu_beds", 11))
        icu_admits = float(data.get("icu_admissions", 1))
        icu_discharges = float(data.get("icu_discharges", 0))
        
        alos = float(data.get("average_length_of_stay", 4.2))
        staff_avail = float(data.get("staff_availability", 20))
        ambulances = float(data.get("ambulance_arrivals", 3))
        
        esi_1 = float(data.get("esi_level_1", 1))
        esi_2 = float(data.get("esi_level_2", 3))
        esi_3 = float(data.get("esi_level_3", 5))
        esi_4 = float(data.get("esi_level_4", 2))
        esi_5 = float(data.get("esi_level_5", 1))
        
        # Rolling estimates if not provided
        r1h = float(data.get("rolling_admissions_1h", admissions))
        r3h = float(data.get("rolling_admissions_3h", admissions * 2.8))
        r6h = float(data.get("rolling_admissions_6h", admissions * 5.2))
        avg_adm = float(data.get("average_admissions", 10.5))
        adm_growth = float(data.get("admission_growth_rate", 0.05))
        
        # Computed rates
        bed_occ_rate = round((occupied_ed / max(1.0, total_ed_beds)) * 100.0, 2)
        icu_occ_rate = round((occupied_icu / max(1.0, total_icu_beds)) * 100.0, 2)
        staff_rate = round(staff_avail / max(1.0, curr_patients), 3)
        
        # Cyclical encodings
        sin_hour = round(np.sin(2 * np.pi * hour / 24.0), 4)
        cos_hour = round(np.cos(2 * np.pi * hour / 24.0), 4)
        sin_dow = round(np.sin(2 * np.pi * day_of_week / 7.0), 4)
        cos_dow = round(np.cos(2 * np.pi * day_of_week / 7.0), 4)
        
        row = {
            "hour": hour,
            "day_of_week": day_of_week,
            "is_weekend": is_weekend,
            "is_holiday": is_holiday,
            "current_emergency_patients": curr_patients,
            "new_emergency_admissions": admissions,
            "emergency_discharges": discharges,
            "occupied_emergency_beds": occupied_ed,
            "available_emergency_beds": avail_ed,
            "total_emergency_beds": total_ed_beds,
            "occupied_icu_beds": occupied_icu,
            "total_icu_beds": total_icu_beds,
            "icu_admissions": icu_admits,
            "icu_discharges": icu_discharges,
            "average_length_of_stay": alos,
            "staff_availability": staff_avail,
            "ambulance_arrivals": ambulances,
            "esi_level_1": esi_1,
            "esi_level_2": esi_2,
            "esi_level_3": esi_3,
            "esi_level_4": esi_4,
            "esi_level_5": esi_5,
            "rolling_admissions_1h": r1h,
            "rolling_admissions_3h": r3h,
            "rolling_admissions_6h": r6h,
            "average_admissions": avg_adm,
            "admission_growth_rate": adm_growth,
            "bed_occupancy_rate": bed_occ_rate,
            "icu_occupancy_rate": icu_occ_rate,
            "staff_availability_rate": staff_rate,
            "sin_hour": sin_hour,
            "cos_hour": cos_hour,
            "sin_dow": sin_dow,
            "cos_dow": cos_dow
        }
        
        df = pd.DataFrame([row])
        # Reorder to match exact training feature columns
        df = df[features_list]
        return df, row

    def classify_status(self, occ_pct: float, thresholds: Dict[str, float] = None) -> str:
        """Classifies occupancy percentage based on configurable thresholds."""
        th = thresholds or {
            "NORMAL_MAX": 60.0,
            "BUSY_MAX": 75.0,
            "HIGH_MAX": 90.0,
            "CRITICAL_MAX": 100.0
        }
        
        if occ_pct <= th["NORMAL_MAX"]:
            return "NORMAL"
        elif occ_pct <= th["BUSY_MAX"]:
            return "BUSY"
        elif occ_pct <= th["HIGH_MAX"]:
            return "HIGH"
        elif occ_pct <= th["CRITICAL_MAX"]:
            return "CRITICAL"
        else:
            return "OVER CAPACITY"

    def predict(self, input_data: Dict[str, Any], custom_thresholds: Dict[str, float] = None) -> Dict[str, Any]:
        df_feat, raw_features = self.prepare_feature_vector(input_data)
        
        total_ed_beds = raw_features["total_emergency_beds"]
        total_icu_beds = raw_features["total_icu_beds"]
        current_ed_occ = raw_features["bed_occupancy_rate"]
        current_icu_occ = raw_features["icu_occupancy_rate"]
        
        predictions_by_horizon = {}
        horizons = [1, 2, 3, 6]
        
        for h in horizons:
            # ED Occupancy %
            reg_ed = self.models.get(f"ed_occupancy_{h}h")
            pred_ed_occ = float(reg_ed.predict(df_feat)[0]) if reg_ed else current_ed_occ
            pred_ed_occ = round(max(0.0, pred_ed_occ), 2)
            
            # ED Patient count
            reg_pts = self.models.get(f"ed_patients_{h}h")
            pred_pts = int(round(float(reg_pts.predict(df_feat)[0]))) if reg_pts else int(round(pred_ed_occ * total_ed_beds / 100.0))
            pred_pts = max(0, pred_pts)
            
            # ICU Occupancy %
            reg_icu = self.models.get(f"icu_occupancy_{h}h")
            pred_icu_occ = float(reg_icu.predict(df_feat)[0]) if reg_icu else current_icu_occ
            pred_icu_occ = round(max(0.0, pred_icu_occ), 2)
            pred_icu_pts = int(round(pred_icu_occ * total_icu_beds / 100.0))
            
            # Classification
            status = self.classify_status(pred_ed_occ, custom_thresholds)
            
            predictions_by_horizon[f"{h}h"] = {
                "horizon_hours": h,
                "predicted_ed_occupancy_pct": pred_ed_occ,
                "predicted_ed_patients": pred_pts,
                "predicted_icu_occupancy_pct": pred_icu_occ,
                "predicted_icu_patients": pred_icu_pts,
                "status": status,
                "is_overcrowded": pred_ed_occ > 75.0,
                "available_ed_beds": max(0, int(total_ed_beds - round(pred_ed_occ * total_ed_beds / 100.0))),
                "available_icu_beds": max(0, int(total_icu_beds - pred_icu_pts))
            }
            
        # Classifier output probabilities for 1h ahead
        classifier_info = {}
        if "capacity_classifier_1h" in self.models:
            rf_cls = self.models["capacity_classifier_1h"]
            cls_probs = rf_cls.predict_proba(df_feat)[0]
            cls_classes = list(rf_cls.classes_)
            prob_dict = {cls: round(float(prob) * 100.0, 1) for cls, prob in zip(cls_classes, cls_probs)}
            predicted_class = str(rf_cls.predict(df_feat)[0])
            classifier_info = {
                "predicted_class": predicted_class,
                "class_probabilities": prob_dict
            }
            
        # Current status
        current_status = self.classify_status(current_ed_occ, custom_thresholds)
        
        # Calculate saturation velocity & time to critical threshold
        saturation_time_hours = None
        trend = "STABLE"
        pred_1h_occ = predictions_by_horizon["1h"]["predicted_ed_occupancy_pct"]
        pred_3h_occ = predictions_by_horizon["3h"]["predicted_ed_occupancy_pct"]
        pred_6h_occ = predictions_by_horizon["6h"]["predicted_ed_occupancy_pct"]
        
        delta_rate = (pred_3h_occ - current_ed_occ) / 3.0
        if delta_rate > 1.5:
            trend = "RAPIDLY RISING"
        elif delta_rate > 0.4:
            trend = "RISING"
        elif delta_rate < -1.5:
            trend = "RAPIDLY FALLING"
        elif delta_rate < -0.4:
            trend = "FALLING"
            
        critical_threshold = (custom_thresholds or {}).get("HIGH_MAX", 90.0)
        if current_ed_occ < critical_threshold and delta_rate > 0.1:
            hours_needed = (critical_threshold - current_ed_occ) / delta_rate
            if 0 < hours_needed <= 6.0:
                saturation_time_hours = round(hours_needed, 1)
                
        # Primary alert level based on maximum projected occupancy in 1-3h
        max_projected_occ = max(pred_1h_occ, pred_3h_occ)
        primary_alert_status = self.classify_status(max_projected_occ, custom_thresholds)
        
        return {
            "current_state": {
                "ed_occupancy_pct": current_ed_occ,
                "current_patients": int(raw_features["current_emergency_patients"]),
                "occupied_ed_beds": int(raw_features["occupied_emergency_beds"]),
                "total_ed_beds": int(total_ed_beds),
                "available_ed_beds": int(raw_features["available_emergency_beds"]),
                "icu_occupancy_pct": current_icu_occ,
                "occupied_icu_beds": int(raw_features["occupied_icu_beds"]),
                "total_icu_beds": int(total_icu_beds),
                "available_icu_beds": int(max(0, total_icu_beds - raw_features["occupied_icu_beds"])),
                "staff_availability": int(raw_features["staff_availability"]),
                "ambulance_arrivals": int(raw_features["ambulance_arrivals"]),
                "status": current_status
            },
            "horizons": predictions_by_horizon,
            "classifier_1h": classifier_info,
            "trend": trend,
            "saturation_time_hours": saturation_time_hours,
            "primary_alert_status": primary_alert_status,
            "raw_features": raw_features
        }

# Singleton instance
predictor = CapacityPredictor()

if __name__ == "__main__":
    sample_input = {
        "hour": 18,
        "day_of_week": 4, # Friday
        "current_emergency_patients": 42,
        "occupied_emergency_beds": 40,
        "total_emergency_beds": 50,
        "new_emergency_admissions": 16,
        "emergency_discharges": 6,
        "total_icu_beds": 16,
        "occupied_icu_beds": 13,
        "staff_availability": 18,
        "ambulance_arrivals": 5,
        "esi_level_1": 2,
        "esi_level_2": 5,
        "esi_level_3": 7,
        "esi_level_4": 1,
        "esi_level_5": 1
    }
    res = predictor.predict(sample_input)
    print("Inference Result Sample:")
    print(f"Current ED Occupancy: {res['current_state']['ed_occupancy_pct']}% ({res['current_state']['status']})")
    print(f"Projected 1h: {res['horizons']['1h']['predicted_ed_occupancy_pct']}% ({res['horizons']['1h']['status']})")
    print(f"Projected 3h: {res['horizons']['3h']['predicted_ed_occupancy_pct']}% ({res['horizons']['3h']['status']})")
    print(f"Projected 6h: {res['horizons']['6h']['predicted_ed_occupancy_pct']}% ({res['horizons']['6h']['status']})")
    print(f"Classifier 1h: {res['classifier_1h']}")
    print(f"Saturation Time: {res['saturation_time_hours']} hrs | Trend: {res['trend']}")
