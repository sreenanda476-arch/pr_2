"""
Hospital Emergency Capacity Prediction System
FastAPI Backend Application
"""

import os
import io
import json
import pandas as pd
from typing import Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from ml.predict import predictor
from ml.model_pipeline import train_and_evaluate
from backend.config import get_thresholds, update_thresholds
from backend.recommendation_engine import generate_recommendations

app = FastAPI(
    title="Hospital Emergency Capacity Prediction System",
    description="AI/ML-based Predictive Analytics and Decision Support System for Emergency Department Overcrowding Prevention",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static directories exist
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)
os.makedirs("data", exist_ok=True)

class PredictRequest(BaseModel):
    hour: Optional[int] = 17
    day_of_week: Optional[int] = 4
    is_weekend: Optional[int] = 0
    is_holiday: Optional[int] = 0
    current_emergency_patients: Optional[int] = 42
    occupied_emergency_beds: Optional[int] = 40
    total_emergency_beds: Optional[int] = 50
    available_emergency_beds: Optional[int] = 10
    new_emergency_admissions: Optional[int] = 15
    emergency_discharges: Optional[int] = 6
    occupied_icu_beds: Optional[int] = 13
    total_icu_beds: Optional[int] = 16
    icu_admissions: Optional[int] = 2
    icu_discharges: Optional[int] = 0
    average_length_of_stay: Optional[float] = 4.2
    staff_availability: Optional[int] = 18
    ambulance_arrivals: Optional[int] = 4
    esi_level_1: Optional[int] = 2
    esi_level_2: Optional[int] = 5
    esi_level_3: Optional[int] = 6
    esi_level_4: Optional[int] = 1
    esi_level_5: Optional[int] = 1
    rolling_admissions_1h: Optional[float] = None
    rolling_admissions_3h: Optional[float] = None
    rolling_admissions_6h: Optional[float] = None
    average_admissions: Optional[float] = None
    admission_growth_rate: Optional[float] = None

class ThresholdUpdateRequest(BaseModel):
    normal_max: float
    busy_max: float
    high_max: float
    critical_max: float

class ScenarioRequest(BaseModel):
    scenario_type: str # 'mci_trauma', 'winter_flu', 'staff_shortage', 'ambulance_swarm', 'normal_shift'
    baseline_patients: Optional[int] = 32

@app.get("/")
def serve_dashboard():
    return FileResponse("static/index.html")

@app.get("/api/status")
def get_system_status():
    metadata = predictor.metadata
    dataset_path = "data/hospital_emergency_data.csv"
    record_count = 0
    if os.path.exists(dataset_path):
        try:
            with open(dataset_path, "r", encoding="utf-8") as f:
                record_count = sum(1 for _ in f) - 1
        except Exception:
            record_count = 8754
            
    return {
        "status": "ONLINE",
        "system_name": "Hospital Emergency Capacity Prediction System",
        "domain": "Urban Intelligence -> Healthcare Emergency Management",
        "attribution_notice": "Demo Dataset: Synthetic data generated for academic prototype.",
        "models_loaded": list(predictor.models.keys()),
        "record_count": record_count,
        "metrics": metadata.get("horizons", {}),
        "classification_metrics": metadata.get("classification", {}),
        "feature_importances": metadata.get("feature_importances", {}).get("ed_occupancy_1h", [])[:10],
        "current_thresholds": get_thresholds()
    }

@app.post("/api/predict")
def run_prediction(req: PredictRequest):
    data_dict = req.model_dump()
    thresholds = get_thresholds()
    res = predictor.predict(data_dict, thresholds)
    recommendations = generate_recommendations(res)
    res["recommendations"] = recommendations
    res["attribution_notice"] = "Demo Dataset: Synthetic data generated for academic prototype."
    return res

@app.get("/api/current_telemetry")
def get_current_telemetry():
    """Returns a representative current hospital telemetry state from recent data."""
    dataset_path = "data/hospital_emergency_data.csv"
    if os.path.exists(dataset_path):
        df = pd.read_csv(dataset_path)
        # Select an interesting busy evening hour (e.g. 18:00)
        evening_samples = df[(df["hour"] >= 17) & (df["hour"] <= 20) & (df["emergency_bed_occupancy_pct"] >= 70)]
        if not evening_samples.empty:
            row = evening_samples.iloc[10 % len(evening_samples)].to_dict()
        else:
            row = df.iloc[-1].to_dict()
    else:
        row = {
            "hour": 18, "day_of_week": 4, "is_weekend": 0, "is_holiday": 0,
            "current_emergency_patients": 41, "occupied_emergency_beds": 39, "total_emergency_beds": 50,
            "available_emergency_beds": 11, "new_emergency_admissions": 14, "emergency_discharges": 6,
            "total_icu_beds": 16, "occupied_icu_beds": 13, "icu_admissions": 2, "icu_discharges": 1,
            "average_length_of_stay": 4.4, "staff_availability": 19, "ambulance_arrivals": 4,
            "esi_level_1": 2, "esi_level_2": 4, "esi_level_3": 6, "esi_level_4": 1, "esi_level_5": 1
        }
        
    # Run full prediction & recommendations on this state
    thresholds = get_thresholds()
    pred_res = predictor.predict(row, thresholds)
    pred_res["recommendations"] = generate_recommendations(pred_res)
    pred_res["attribution_notice"] = "Demo Dataset: Synthetic data generated for academic prototype."
    return pred_res

@app.get("/api/historical_sample")
def get_historical_sample(hours: int = 48):
    """Returns recent time-series records for dashboard charts."""
    dataset_path = "data/hospital_emergency_data.csv"
    if not os.path.exists(dataset_path):
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    df = pd.read_csv(dataset_path)
    sample_df = df.iloc[-hours:].copy()
    
    # Also calculate diurnal hourly averages across full dataset
    diurnal = df.groupby("hour").agg({
        "new_emergency_admissions": "mean",
        "emergency_discharges": "mean",
        "emergency_bed_occupancy_pct": "mean",
        "ambulance_arrivals": "mean"
    }).round(2).reset_index().to_dict(orient="records")
    
    return {
        "recent_time_series": sample_df.to_dict(orient="records"),
        "diurnal_profile": diurnal,
        "total_records": len(df),
        "attribution_notice": "Demo Dataset: Synthetic data generated for academic prototype."
    }

@app.post("/api/simulate_scenario")
def simulate_scenario(req: ScenarioRequest):
    """Interactive What-If Scenario Simulator."""
    scenario = req.scenario_type
    base_patients = req.baseline_patients or 32
    
    scenario_configs = {
        "mci_trauma": {
            "name": "Mass-Casualty Incident (Highway Collision)",
            "description": "Sudden arrival of 18 high-acuity trauma casualties via multiple ambulances.",
            "data": {
                "hour": 20, "day_of_week": 4, "is_weekend": 0, "is_holiday": 0,
                "current_emergency_patients": base_patients + 16,
                "occupied_emergency_beds": min(56, base_patients + 14),
                "total_emergency_beds": 50,
                "available_emergency_beds": max(0, 50 - (base_patients + 14)),
                "new_emergency_admissions": 22,
                "emergency_discharges": 3,
                "total_icu_beds": 16, "occupied_icu_beds": 14,
                "icu_admissions": 4, "icu_discharges": 0,
                "average_length_of_stay": 5.8,
                "staff_availability": 18,
                "ambulance_arrivals": 8,
                "esi_level_1": 5, "esi_level_2": 8, "esi_level_3": 6, "esi_level_4": 2, "esi_level_5": 1
            }
        },
        "winter_flu": {
            "name": "Winter Epidemic / Flu Respiratory Surge",
            "description": "Sustained influx of elderly and vulnerable patients with acute respiratory distress, increasing length of stay.",
            "data": {
                "hour": 16, "day_of_week": 1, "is_weekend": 0, "is_holiday": 0,
                "current_emergency_patients": base_patients + 12,
                "occupied_emergency_beds": min(54, base_patients + 11),
                "total_emergency_beds": 50,
                "available_emergency_beds": max(0, 50 - (base_patients + 11)),
                "new_emergency_admissions": 18,
                "emergency_discharges": 5,
                "total_icu_beds": 16, "occupied_icu_beds": 15,
                "icu_admissions": 3, "icu_discharges": 1,
                "average_length_of_stay": 6.2,
                "staff_availability": 16,
                "ambulance_arrivals": 5,
                "esi_level_1": 2, "esi_level_2": 6, "esi_level_3": 8, "esi_level_4": 2, "esi_level_5": 0
            }
        },
        "staff_shortage": {
            "name": "Severe Shift Staff Shortage (-40% Nursing)",
            "description": "Sudden staffing callouts due to winter illness during regular patient census.",
            "data": {
                "hour": 14, "day_of_week": 2, "is_weekend": 0, "is_holiday": 0,
                "current_emergency_patients": base_patients + 6,
                "occupied_emergency_beds": base_patients + 5,
                "total_emergency_beds": 50,
                "available_emergency_beds": max(0, 50 - (base_patients + 5)),
                "new_emergency_admissions": 12,
                "emergency_discharges": 3, # discharges delayed due to shortage
                "total_icu_beds": 16, "occupied_icu_beds": 12,
                "icu_admissions": 1, "icu_discharges": 0,
                "average_length_of_stay": 5.4,
                "staff_availability": 9, # severe shortage!
                "ambulance_arrivals": 3,
                "esi_level_1": 1, "esi_level_2": 3, "esi_level_3": 5, "esi_level_4": 2, "esi_level_5": 1
            }
        },
        "ambulance_swarm": {
            "name": "Ambulance Swarm / Regional Diversion Spillover",
            "description": "Neighboring trauma center diverted ambulances, resulting in 7 EMS arrivals in 45 minutes.",
            "data": {
                "hour": 19, "day_of_week": 5, "is_weekend": 1, "is_holiday": 0,
                "current_emergency_patients": base_patients + 10,
                "occupied_emergency_beds": base_patients + 9,
                "total_emergency_beds": 50,
                "available_emergency_beds": max(0, 50 - (base_patients + 9)),
                "new_emergency_admissions": 17,
                "emergency_discharges": 5,
                "total_icu_beds": 16, "occupied_icu_beds": 13,
                "icu_admissions": 2, "icu_discharges": 1,
                "average_length_of_stay": 4.6,
                "staff_availability": 19,
                "ambulance_arrivals": 7,
                "esi_level_1": 2, "esi_level_2": 5, "esi_level_3": 7, "esi_level_4": 2, "esi_level_5": 1
            }
        },
        "normal_shift": {
            "name": "Standard Midweek Shift (Baseline)",
            "description": "Typical Tuesday afternoon operations with balanced flow.",
            "data": {
                "hour": 14, "day_of_week": 1, "is_weekend": 0, "is_holiday": 0,
                "current_emergency_patients": 26,
                "occupied_emergency_beds": 24,
                "total_emergency_beds": 50,
                "available_emergency_beds": 26,
                "new_emergency_admissions": 8,
                "emergency_discharges": 8,
                "total_icu_beds": 16, "occupied_icu_beds": 8,
                "icu_admissions": 1, "icu_discharges": 1,
                "average_length_of_stay": 3.7,
                "staff_availability": 22,
                "ambulance_arrivals": 2,
                "esi_level_1": 1, "esi_level_2": 2, "esi_level_3": 3, "esi_level_4": 1, "esi_level_5": 1
            }
        }
    }
    
    cfg = scenario_configs.get(scenario, scenario_configs["normal_shift"])
    thresholds = get_thresholds()
    pred_res = predictor.predict(cfg["data"], thresholds)
    pred_res["scenario_name"] = cfg["name"]
    pred_res["scenario_description"] = cfg["description"]
    pred_res["recommendations"] = generate_recommendations(pred_res)
    pred_res["attribution_notice"] = "Demo Dataset: Synthetic data generated for academic prototype."
    return pred_res

@app.get("/api/thresholds")
def fetch_thresholds():
    return get_thresholds()

@app.post("/api/thresholds")
def save_thresholds(req: ThresholdUpdateRequest):
    updated = update_thresholds(req.normal_max, req.busy_max, req.high_max, req.critical_max)
    return {"status": "SUCCESS", "thresholds": updated}

@app.get("/api/download_demo_csv")
def download_demo_csv():
    dataset_path = "data/hospital_emergency_data.csv"
    if not os.path.exists(dataset_path):
        raise HTTPException(status_code=404, detail="Dataset not found")
    return FileResponse(dataset_path, filename="hospital_emergency_data_synthetic.csv", media_type="text/csv")

@app.post("/api/upload_csv")
async def upload_csv(file: UploadFile = File(...)):
    """Upload custom hospital CSV data and return analysis."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")
        
    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")
        
    req_cols = ["current_emergency_patients", "new_emergency_admissions", "total_emergency_beds"]
    missing = [c for c in req_cols if c not in df.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing essential hospital columns: {missing}")
        
    # Save as active uploaded dataset
    save_path = "data/uploaded_hospital_data.csv"
    df.to_csv(save_path, index=False)
    
    # Run prediction on latest record in the uploaded file
    latest_row = df.iloc[-1].to_dict()
    thresholds = get_thresholds()
    pred_res = predictor.predict(latest_row, thresholds)
    pred_res["recommendations"] = generate_recommendations(pred_res)
    
    return {
        "status": "UPLOAD_SUCCESS",
        "filename": file.filename,
        "rows_processed": len(df),
        "columns_found": list(df.columns),
        "latest_record_prediction": pred_res,
        "attribution_notice": "User Uploaded Dataset Analyzed by Hospital Capacity System"
    }

@app.post("/api/retrain")
def retrain_models():
    """Retrain ML models on the active dataset."""
    try:
        metrics = train_and_evaluate(data_path="data/hospital_emergency_data.csv")
        predictor.load_artifacts() # reload into memory
        return {"status": "RETRAIN_SUCCESS", "metrics": metrics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retraining error: {str(e)}")

# Mount static files at /static
app.mount("/static", StaticFiles(directory="static"), name="static")
