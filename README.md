# Hospital Emergency Capacity Prediction System

> **Urban Intelligence → Emergency Response → Healthcare Emergency Management**  
> *AI/ML-based Predictive Analytics and Operational Decision Support System*

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-1.4%2B-F7931E.svg)](https://scikit-learn.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📌 Project Overview & Problem Statement

Hospitals frequently face sudden, severe overcrowding during mass casualty incidents, seasonal epidemics (such as winter flu surges), extreme weather events, local festivals, and systemic bottlenecks. 

Hospital administrators and emergency room directors must make high-stakes resource decisions—deploying on-call staff, opening surge wards, placing elective surgeries on hold, and coordinating ambulance diversion—**before** critical overcrowding and gridlock actually occur.

The **Hospital Emergency Capacity Prediction System** is an intelligent predictive analytics command center that analyzes real-time and historical emergency telemetry to forecast Emergency Department (ED) and Intensive Care Unit (ICU) load **1 to 6 hours ahead**. It provides early saturation warnings and generates prioritized, actionable resource recommendations for hospital administrators.

---

## ⚠️ Important Differentiation

* **This is NOT a hospital-finding application.**
* **Does NOT use Google Maps, GPS routing, or patient navigation.**
* **Does NOT recommend hospitals based on geographical proximity.**

### Primary Focus:
```
Hospital Emergency Capacity + Patient Flow Dynamics + Multi-Horizon Machine Learning + Early Warning Saturation + Resource Optimization
```

---

## 🔬 Academic Disclaimer

> **Demo Dataset: Synthetic data generated for academic prototype.**  
> *The included 8,754-record dataset models realistic hospital compartment queues, diurnal curves, and emergency shocks for academic evaluation and system demonstration.*

---

## 🚀 Key Capabilities

### 1. Multi-Horizon Machine Learning Forecasting
* **Horizons:** Forecasts occupancy and patient load at **+1 hour**, **+2 hours**, **+3 hours**, and **+6 hours** ahead.
* **Dual Output:**
  * **Continuous Regressors:** Emergency Bed Occupancy %, ICU Bed Occupancy %, and Patient Census counts.
  * **Categorical Classifier:** Capacity Risk Tier (**NORMAL**, **BUSY**, **HIGH**, **CRITICAL**, **OVER CAPACITY**).

### 2. Early Warning & Saturation Velocity Tracking
* Calculates **Time-to-Saturation** (e.g., *"Projected to breach 90% Critical Threshold in 2.1 hours"*).
* Detects patient velocity trends: *STABLE*, *RISING*, *RAPIDLY RISING*, *FALLING*, *RAPIDLY FALLING*.

### 3. Clinical Decision Support & Recommendation Engine
Dynamically generates prioritized interventions categorized by operational domain:
* **Bed Management:** Activation of Level 2 Surge Protocols, annex overflow wards, and discharge lounge routing.
* **Staffing:** Triggering of on-call nurse rosters, float pool redeployment, and physician re-allocation.
* **ICU Operations:** Temporary hold on elective surgeries requiring post-op ICU beds; rapid step-down candidate screening.
* **EMS Coordination:** Regional Basic Life Support (BLS) ambulance partial diversion requests while maintaining trauma reception.
* **Triage & Flow:** Opening Fast-Track ambulatory lanes for minor acuity (ESI-4/5) patients.

### 4. Interactive "What-If" Stress Test Simulator
One-click simulation of critical shock events:
* 🚑 **Mass-Casualty Incident:** Multi-vehicle highway collision (+18 trauma casualties, high ESI-1/2 ratio).
* 🦠 **Winter Epidemic Surge:** Sustained respiratory illness influx with elevated average length of stay (ALOS).
* ⚠️ **Severe Staff Shortage:** Sudden 40% reduction in on-duty nursing staff with discharge delays.
* 🚨 **Ambulance Swarm:** Spillover from adjacent hospital diversion resulting in 7 EMS arrivals in 45 minutes.
* 🩺 **Midweek Routine:** Baseline operating equilibrium.

### 5. High-Fidelity Hospital Operations Command Center
* Dark-slate telemetry monitoring theme with glowing status indicators.
* Live KPI telemetry cards for ED Occupancy, Census, ICU Beds, Staff Ratio, and EMS Velocity.
* Interactive Multi-Horizon timeline trajectory charts.
* 24-hour diurnal patient flow analysis.
* Top 10 Feature Importance transparency chart.
* Support for custom hospital CSV dataset uploads and one-click demo dataset export.
* Dynamically configurable classification thresholds.

---

## 🏗️ System Architecture

```
pr/
├── backend/
│   ├── app.py                     # FastAPI REST API & Static File Server
│   ├── config.py                  # Configurable Thresholds & Application Settings
│   └── recommendation_engine.py   # Clinical Decision Support Engine
├── data/
│   ├── generate_dataset.py        # Realistic Queue-based Synthetic Dataset Generator
│   └── hospital_emergency_data.csv# 8,754 Hourly Records (1 Full Year)
├── ml/
│   ├── model_pipeline.py          # Feature Engineering & Model Training Pipeline
│   ├── predict.py                 # Real-time Multi-Horizon Inference Engine
│   └── models/                    # Serialized Model Artifacts & Metrics
│       ├── rf_ed_occupancy_1h.joblib
│       ├── rf_ed_occupancy_2h.joblib
│       ├── rf_ed_occupancy_3h.joblib
│       ├── rf_ed_occupancy_6h.joblib
│       ├── rf_ed_patients_1h.joblib
│       ├── rf_icu_occupancy_1h.joblib
│       ├── rf_capacity_classifier_1h.joblib
│       └── model_metadata.json
├── static/
│   ├── index.html                 # Command Center Single-Page Dashboard
│   ├── css/
│   │   └── style.css              # Telemetry Dark Theme & Responsive Styles
│   └── js/
│       └── app.js                 # Dashboard Controller, Chart.js Visualizations & API Client
├── run_server.py                  # Entry-point Server Launcher
└── README.md                      # Project Documentation
```

---

## 📊 Machine Learning Model Details

### Algorithms
* **Multi-Horizon Regressors:** Random Forest Regressors (`n_estimators=100`, `max_depth=16`)
* **Capacity Classifier:** Balanced Random Forest Classifier (`n_estimators=100`, `class_weight='balanced'`)

### Feature Engineering
1. **Temporal & Circadian:** `hour`, `day_of_week`, `is_weekend`, `is_holiday`, cyclical `sin_hour`, `cos_hour`, `sin_dow`, `cos_dow`.
2. **Current State:** `current_emergency_patients`, `occupied_emergency_beds`, `available_emergency_beds`, `total_emergency_beds`.
3. **Flow & Velocity:** `new_emergency_admissions`, `emergency_discharges`, `rolling_admissions_1h`, `rolling_admissions_3h`, `rolling_admissions_6h`, `admission_growth_rate`.
4. **Severity Distribution:** Emergency Severity Index counts (`esi_level_1` to `esi_level_5`).
5. **Acuity & Resources:** `occupied_icu_beds`, `total_icu_beds`, `average_length_of_stay`, `staff_availability`, `staff_availability_rate`, `ambulance_arrivals`.

### Performance Metrics (Temporal Holdout Test Set)

| Model Target | Horizon | Metric (MAE) | Metric (RMSE) | R² Score |
| :--- | :---: | :---: | :---: | :---: |
| **ED Bed Occupancy %** | +1 Hour | **6.22%** | 7.98% | **0.8850** |
| **ED Bed Occupancy %** | +2 Hours | **7.93%** | 10.24% | **0.8107** |
| **ED Bed Occupancy %** | +3 Hours | **8.90%** | 11.59% | **0.7584** |
| **ED Bed Occupancy %** | +6 Hours | **9.66%** | 12.59% | **0.7167** |
| **ED Patient Census** | +1 Hour | **3.13 patients** | 4.06 | **0.8824** |
| **ICU Occupancy %** | +1 Hour | **3.07%** | 4.41% | **0.8883** |
| **Capacity Risk Classifier** | +1 Hour | **75.33% Accuracy** | — | — |

---

## 🚦 Capacity Classification Thresholds

Thresholds are fully configurable via the backend API and UI modal:

* `0% – 60%`: **NORMAL** (Standard patient flow and routine discharges)
* `61% – 75%`: **BUSY** (Elevated vigilance, fast-track intake monitoring)
* `76% – 90%`: **HIGH** (Expedite inpatient transfers, mobilize auxiliary staff)
* `91% – 100%`: **CRITICAL** (Activate surge unit, recall on-call clinical roster)
* `> 100%`: **OVER CAPACITY** (Code Red Surge Protocol, partial EMS diversion)

---

## 🛠️ Installation & Setup Guide

### 1. Clone the Repository
```bash
git clone https://github.com/<your-username>/hospital-emergency-capacity-prediction.git
cd hospital-emergency-capacity-prediction
```

### 2. Create a Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
*(If `requirements.txt` is not yet present, install the core packages directly:)*
```bash
pip install fastapi uvicorn scikit-learn pandas numpy scipy python-multipart
```

### 4. (Optional) Re-generate Dataset & Train Models
The repository includes pre-generated data and trained models. To re-generate or re-train from scratch:
```bash
# 1. Generate 8,754 synthetic records
python data/generate_dataset.py

# 2. Train and evaluate all ML models
python ml/model_pipeline.py
```

### 5. Launch the Application
```bash
python run_server.py
```
Open your browser and navigate to:  
👉 **`http://127.0.0.1:8000`**

---

## 🔌 REST API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Serves the main Command Center Single-Page App |
| `GET` | `/api/status` | System health, model metrics, feature importances |
| `GET` | `/api/current_telemetry` | Retrieves the latest hospital state and baseline predictions |
| `POST` | `/api/predict` | Runs multi-horizon predictions on custom telemetry inputs |
| `POST` | `/api/simulate_scenario` | Executes pre-configured "What-If" stress test scenarios |
| `GET` | `/api/historical_sample` | Time-series data and 24-hour diurnal curves |
| `GET` | `/api/thresholds` | Returns current capacity classification cutoffs |
| `POST` | `/api/thresholds` | Dynamically updates capacity thresholds |
| `POST` | `/api/upload_csv` | Parses user-uploaded hospital CSV dataset |
| `GET` | `/api/download_demo_csv` | Downloads the full 8,754-record academic synthetic dataset |
| `POST` | `/api/retrain` | Triggers retraining of all regression and classification models |

---

## 📋 Example Prediction Request Payload

```json
POST /api/predict
Content-Type: application/json

{
  "hour": 19,
  "day_of_week": 4,
  "is_weekend": 0,
  "is_holiday": 0,
  "current_emergency_patients": 42,
  "total_emergency_beds": 50,
  "occupied_emergency_beds": 40,
  "new_emergency_admissions": 16,
  "emergency_discharges": 6,
  "occupied_icu_beds": 13,
  "total_icu_beds": 16,
  "staff_availability": 18,
  "ambulance_arrivals": 5,
  "average_length_of_stay": 4.5,
  "esi_level_1": 2,
  "esi_level_2": 5,
  "esi_level_3": 7,
  "esi_level_4": 2,
  "esi_level_5": 1
}
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
