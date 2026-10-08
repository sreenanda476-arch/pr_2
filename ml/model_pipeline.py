"""
Hospital Emergency Capacity Prediction System
Machine Learning Training Pipeline

Trains multi-horizon regressors and classifiers:
- Random Forest Regressors for ED Occupancy %, ICU Occupancy %, and Patient Load at +1h, +2h, +3h, +6h
- Random Forest Classifier for Capacity Alert Classification (NORMAL, BUSY, HIGH, CRITICAL, OVER CAPACITY)
- Calculates MAE, RMSE, R2, Accuracy, Confusion Matrix, and Feature Importances
- Saves model artifacts and metadata
"""

import os
import json
import numpy as np
import pandas as pd
import joblib
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    accuracy_score, classification_report, confusion_matrix
)

FEATURES = [
    "hour",
    "day_of_week",
    "is_weekend",
    "is_holiday",
    "current_emergency_patients",
    "new_emergency_admissions",
    "emergency_discharges",
    "occupied_emergency_beds",
    "available_emergency_beds",
    "total_emergency_beds",
    "occupied_icu_beds",
    "total_icu_beds",
    "icu_admissions",
    "icu_discharges",
    "average_length_of_stay",
    "staff_availability",
    "ambulance_arrivals",
    "esi_level_1",
    "esi_level_2",
    "esi_level_3",
    "esi_level_4",
    "esi_level_5",
    "rolling_admissions_1h",
    "rolling_admissions_3h",
    "rolling_admissions_6h",
    "average_admissions",
    "admission_growth_rate",
    "bed_occupancy_rate",
    "icu_occupancy_rate",
    "staff_availability_rate",
    "sin_hour",
    "cos_hour",
    "sin_dow",
    "cos_dow"
]

def engineer_features(df):
    """Adds cyclical, ratio, and engineered features."""
    df_feat = df.copy()
    
    # Bed occupancy rates
    df_feat["bed_occupancy_rate"] = (df_feat["occupied_emergency_beds"] / df_feat["total_emergency_beds"] * 100.0).round(2)
    df_feat["icu_occupancy_rate"] = (df_feat["occupied_icu_beds"] / df_feat["total_icu_beds"] * 100.0).round(2)
    
    # Staff availability rate (staff per patient or staff ratio)
    df_feat["staff_availability_rate"] = (df_feat["staff_availability"] / 
                                          df_feat["current_emergency_patients"].replace(0, 1)).round(3)
    
    # Cyclical hour encoding (24h period)
    df_feat["sin_hour"] = np.sin(2 * np.pi * df_feat["hour"] / 24.0).round(4)
    df_feat["cos_hour"] = np.cos(2 * np.pi * df_feat["hour"] / 24.0).round(4)
    
    # Cyclical day of week encoding (7d period)
    df_feat["sin_dow"] = np.sin(2 * np.pi * df_feat["day_of_week"] / 7.0).round(4)
    df_feat["cos_dow"] = np.cos(2 * np.pi * df_feat["day_of_week"] / 7.0).round(4)
    
    return df_feat

def train_and_evaluate(data_path="data/hospital_emergency_data.csv", models_dir="ml/models"):
    os.makedirs(models_dir, exist_ok=True)
    print(f"Loading hospital dataset from: {data_path}")
    df = pd.read_csv(data_path)
    df = engineer_features(df)
    
    # Drop rows where target horizons might be NaN
    valid_mask = df["future_ed_occupancy_6h"].notna()
    df = df[valid_mask].reset_index(drop=True)
    
    X = df[FEATURES]
    
    # Split train/test (temporal preservation: 80% train, 20% test)
    split_idx = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    
    metrics = {
        "training_date": datetime.now().isoformat(),
        "total_records": len(df),
        "train_records": len(X_train),
        "test_records": len(X_test),
        "features": FEATURES,
        "horizons": {},
        "classification": {},
        "feature_importances": {}
    }
    
    horizons = [1, 2, 3, 6]
    
    # 1. Train Multi-Horizon Regressors for ED Occupancy %
    for h in horizons:
        print(f"--- Training ED Occupancy Regressor ({h}h ahead) ---")
        y_train = df.iloc[:split_idx][f"future_ed_occupancy_{h}h"]
        y_test = df.iloc[split_idx:][f"future_ed_occupancy_{h}h"]
        
        rf_reg = RandomForestRegressor(n_estimators=100, max_depth=16, min_samples_split=4, random_state=42, n_jobs=-1)
        rf_reg.fit(X_train, y_train)
        
        y_pred = rf_reg.predict(X_test)
        mae = float(mean_absolute_error(y_test, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        r2 = float(r2_score(y_test, y_pred))
        
        model_filename = f"{models_dir}/rf_ed_occupancy_{h}h.joblib"
        joblib.dump(rf_reg, model_filename)
        
        metrics["horizons"][f"ed_occupancy_{h}h"] = {
            "horizon_hours": h,
            "target": f"future_ed_occupancy_{h}h",
            "model": "RandomForestRegressor",
            "mae": round(mae, 3),
            "rmse": round(rmse, 3),
            "r2": round(r2, 4),
            "model_file": model_filename
        }
        print(f"[{h}h ED Occupancy] MAE: {mae:.2f}%, RMSE: {rmse:.2f}%, R2: {r2:.4f}")
        
        # Save feature importances for 1h model as prime reference
        if h == 1:
            importances = dict(zip(FEATURES, rf_reg.feature_importances_))
            sorted_imp = sorted(importances.items(), key=lambda x: x[1], reverse=True)
            metrics["feature_importances"]["ed_occupancy_1h"] = [
                {"feature": k, "importance": round(float(v), 4)} for k, v in sorted_imp
            ]
            
    # 2. Train Multi-Horizon Regressors for ED Patient Counts
    for h in horizons:
        print(f"--- Training ED Patient Count Regressor ({h}h ahead) ---")
        y_train_pts = df.iloc[:split_idx][f"future_ed_patients_{h}h"]
        y_test_pts = df.iloc[split_idx:][f"future_ed_patients_{h}h"]
        
        rf_pts = RandomForestRegressor(n_estimators=80, max_depth=16, random_state=42, n_jobs=-1)
        rf_pts.fit(X_train, y_train_pts)
        
        y_pred_pts = rf_pts.predict(X_test)
        mae_pts = float(mean_absolute_error(y_test_pts, y_pred_pts))
        rmse_pts = float(np.sqrt(mean_squared_error(y_test_pts, y_pred_pts)))
        r2_pts = float(r2_score(y_test_pts, y_pred_pts))
        
        pts_model_filename = f"{models_dir}/rf_ed_patients_{h}h.joblib"
        joblib.dump(rf_pts, pts_model_filename)
        
        metrics["horizons"][f"ed_patients_{h}h"] = {
            "horizon_hours": h,
            "target": f"future_ed_patients_{h}h",
            "model": "RandomForestRegressor",
            "mae": round(mae_pts, 3),
            "rmse": round(rmse_pts, 3),
            "r2": round(r2_pts, 4),
            "model_file": pts_model_filename
        }
        print(f"[{h}h ED Patient Count] MAE: {mae_pts:.2f} patients, RMSE: {rmse_pts:.2f}, R2: {r2_pts:.4f}")

    # 3. Train Regressors for ICU Occupancy % (1h, 2h, 3h, 6h)
    for h in horizons:
        print(f"--- Training ICU Occupancy Regressor ({h}h ahead) ---")
        y_train_icu = df.iloc[:split_idx][f"future_icu_occupancy_{h}h"]
        y_test_icu = df.iloc[split_idx:][f"future_icu_occupancy_{h}h"]
        
        rf_icu = RandomForestRegressor(n_estimators=70, max_depth=14, random_state=42, n_jobs=-1)
        rf_icu.fit(X_train, y_train_icu)
        
        y_pred_icu = rf_icu.predict(X_test)
        mae_icu = float(mean_absolute_error(y_test_icu, y_pred_icu))
        rmse_icu = float(np.sqrt(mean_squared_error(y_test_icu, y_pred_icu)))
        r2_icu = float(r2_score(y_test_icu, y_pred_icu))
        
        icu_model_filename = f"{models_dir}/rf_icu_occupancy_{h}h.joblib"
        joblib.dump(rf_icu, icu_model_filename)
        
        metrics["horizons"][f"icu_occupancy_{h}h"] = {
            "horizon_hours": h,
            "target": f"future_icu_occupancy_{h}h",
            "model": "RandomForestRegressor",
            "mae": round(mae_icu, 3),
            "rmse": round(rmse_icu, 3),
            "r2": round(r2_icu, 4),
            "model_file": icu_model_filename
        }
        print(f"[{h}h ICU Occupancy] MAE: {mae_icu:.2f}%, RMSE: {rmse_icu:.2f}%, R2: {r2_icu:.4f}")

    # 3. Train Capacity Classification Model (1h ahead)
    print("--- Training Capacity Classification Model (Random Forest Classifier) ---")
    y_train_cls = df.iloc[:split_idx]["future_capacity_class_1h"]
    y_test_cls = df.iloc[split_idx:]["future_capacity_class_1h"]
    
    classes = ["NORMAL", "BUSY", "HIGH", "CRITICAL", "OVER CAPACITY"]
    rf_cls = RandomForestClassifier(n_estimators=100, max_depth=16, random_state=42, class_weight="balanced", n_jobs=-1)
    rf_cls.fit(X_train, y_train_cls)
    
    y_pred_cls = rf_cls.predict(X_test)
    acc = float(accuracy_score(y_test_cls, y_pred_cls))
    report = classification_report(y_test_cls, y_pred_cls, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_test_cls, y_pred_cls, labels=classes).tolist()
    
    cls_model_filename = f"{models_dir}/rf_capacity_classifier_1h.joblib"
    joblib.dump(rf_cls, cls_model_filename)
    
    metrics["classification"]["1h"] = {
        "model": "RandomForestClassifier",
        "accuracy": round(acc, 4),
        "classes": classes,
        "confusion_matrix": cm,
        "classification_report": report,
        "model_file": cls_model_filename
    }
    print(f"[Capacity Classifier 1h] Accuracy: {acc*100:.2f}%")
    
    # Save Metadata JSON
    metadata_path = f"{models_dir}/model_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Successfully saved all models and metadata to {metadata_path}")
    
    return metrics

if __name__ == "__main__":
    train_and_evaluate()
