"""
Hospital Emergency Capacity Prediction System
Realistic Synthetic Dataset Generator
Generates 8,760 hourly records (1 full year) of realistic hospital emergency data.

Notice: "Demo Dataset: Synthetic data generated for academic prototype."
"""

import os
import math
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_synthetic_hospital_data(num_days=365, start_date="2025-01-01 00:00:00", output_file="data/hospital_emergency_data.csv"):
    np.random.seed(42)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    total_hours = num_days * 24
    base_time = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
    
    # Hospital baseline capacity parameters
    TOTAL_ED_BEDS = 50
    TOTAL_ICU_BEDS = 16
    
    # Holiday calendar for 2025
    holidays = {
        "2025-01-01", "2025-01-20", "2025-02-17", "2025-05-26", 
        "2025-07-04", "2025-09-01", "2025-10-13", "2025-11-11", 
        "2025-11-27", "2025-12-25", "2025-12-31"
    }
    
    # Scheduled surge events (day, hour, additional_surge_arrivals)
    surge_events = {
        (15, 18): 14,   # Day 15, 6 PM: Winter storm pileup
        (42, 19): 18,   # Day 42, 7 PM: Highway accident
        (118, 21): 22,  # Day 118, 9 PM: Factory incident
        (175, 23): 16,  # Day 175, 11 PM: Summer festival surge
        (205, 16): 20,  # Day 205, 4 PM: Heat exhaustion cluster
        (290, 20): 19,  # Day 290, 8 PM: Metro transit stoppage
        (358, 22): 17   # Day 358, 10 PM: Holiday eve accident cluster
    }
    
    # Patient queue tracking: list of remaining stay hours for active ED and ICU patients
    # Seed with initial patients
    active_ed_patients_remaining_stay = list(np.random.uniform(0.5, 4.0, size=22))
    active_icu_patients_remaining_stay = list(np.random.uniform(1.0, 18.0, size=7))
    
    records = []
    
    for i in range(total_hours):
        dt = base_time + timedelta(hours=i)
        day_offset = i // 24
        hour = dt.hour
        day_of_week = dt.weekday() # 0 = Monday, 6 = Sunday
        is_weekend = 1 if day_of_week in [5, 6] else 0
        date_str = dt.strftime("%Y-%m-%d")
        is_holiday = 1 if date_str in holidays else 0
        
        # Seasonality
        month = dt.month
        if month in [12, 1, 2]:
            season = "Winter"
            seasonal_multiplier = 1.15
            season_stay_boost = 0.4
        elif month in [3, 4, 5]:
            season = "Spring"
            seasonal_multiplier = 0.95
            season_stay_boost = 0.0
        elif month in [6, 7, 8]:
            season = "Summer"
            seasonal_multiplier = 1.05
            season_stay_boost = 0.1
        else:
            season = "Fall"
            seasonal_multiplier = 1.00
            season_stay_boost = 0.05
            
        # Realistic diurnal arrival rate curve:
        # 0-5h: 2.5 - 4.5
        # 6-10h: 5.5 - 8.5
        # 11-16h: 8.5 - 12.0
        # 17-21h: 11.5 - 15.0
        # 22-23h: 6.0 - 9.0
        if 0 <= hour <= 5:
            base_arrival_rate = 3.0 + 1.0 * math.sin((hour / 5.0) * math.pi)
        elif 6 <= hour <= 10:
            base_arrival_rate = 5.5 + 3.0 * ((hour - 6) / 4.0)
        elif 11 <= hour <= 16:
            base_arrival_rate = 9.0 + 2.5 * math.sin(((hour - 11) / 5.0) * math.pi)
        elif 17 <= hour <= 21:
            base_arrival_rate = 12.0 + 3.0 * math.cos(((hour - 17) / 4.0) * math.pi)
        else:
            base_arrival_rate = 7.5 - 3.0 * ((hour - 22) / 1.0)
            
        # Adjust for weekend and holiday
        if is_weekend:
            if hour >= 20 or hour <= 4:
                base_arrival_rate *= 1.30
            elif 7 <= hour <= 11:
                base_arrival_rate *= 0.85
                
        if is_holiday:
            base_arrival_rate *= 1.25
            
        expected_arrivals = base_arrival_rate * seasonal_multiplier
        
        # Check for sudden emergency event
        surge_arrival = surge_events.get((day_offset, hour), 0)
        
        # Random noise on arrivals
        arrivals = max(1, int(np.random.poisson(expected_arrivals) + surge_arrival))
        
        # Ambulance arrivals (typically 18% - 32%)
        amb_ratio = 0.65 if surge_arrival > 0 else np.random.uniform(0.18, 0.32)
        ambulances = max(0, int(round(arrivals * amb_ratio + np.random.normal(0, 0.5))))
        
        # Severity distribution (ESI 1-5)
        if surge_arrival > 0:
            p_esi = [0.14, 0.36, 0.32, 0.12, 0.06]
        else:
            # Baseline hospital ESI distribution
            p_esi = [0.03, 0.18, 0.44, 0.25, 0.10]
            
        esi_counts = np.random.multinomial(arrivals, p_esi)
        esi_1, esi_2, esi_3, esi_4, esi_5 = esi_counts
        
        # Generate length of stay for new ED arrivals (in hours)
        # ESI 1: 5.5h avg, ESI 2: 4.5h avg, ESI 3: 3.5h avg, ESI 4: 2.2h avg, ESI 5: 1.4h avg
        new_stays = []
        for _ in range(esi_1):
            new_stays.append(max(1.5, np.random.normal(5.5 + season_stay_boost, 1.0)))
        for _ in range(esi_2):
            new_stays.append(max(1.0, np.random.normal(4.6 + season_stay_boost, 0.9)))
        for _ in range(esi_3):
            new_stays.append(max(0.8, np.random.normal(3.5 + season_stay_boost, 0.8)))
        for _ in range(esi_4):
            new_stays.append(max(0.5, np.random.normal(2.2 + season_stay_boost, 0.6)))
        for _ in range(esi_5):
            new_stays.append(max(0.3, np.random.normal(1.4 + season_stay_boost, 0.4)))
            
        # Add new arrivals to ED active pool
        active_ed_patients_remaining_stay.extend(new_stays)
        
        # Decrement remaining stay by 1 hour for all current patients
        active_ed_patients_remaining_stay = [stay - 1.0 for stay in active_ed_patients_remaining_stay]
        
        # Patients whose stay reaches <= 0 are discharged
        discharged_patients = [stay for stay in active_ed_patients_remaining_stay if stay <= 0]
        discharges = len(discharged_patients)
        # Keep remaining active patients
        active_ed_patients_remaining_stay = [stay for stay in active_ed_patients_remaining_stay if stay > 0]
        
        curr_ed_patients = len(active_ed_patients_remaining_stay)
        
        # Bed occupancy: Patients in ED beds vs waiting room / observation chairs
        # If patients exceed total beds, physical occupied beds can reach up to 105-115% with surge hallway gurneys
        curr_ed_occupied = min(int(TOTAL_ED_BEDS * 1.15), curr_ed_patients)
        avail_ed_beds = max(0, TOTAL_ED_BEDS - curr_ed_occupied)
        
        # Average length of stay calculation for current cohort
        if len(new_stays) > 0:
            alos = round(float(np.mean(new_stays)), 2)
        else:
            alos = 3.6
            
        # ICU Admissions: severe ESI 1 and subset of ESI 2
        icu_candidates = esi_1 + int(esi_2 * np.random.uniform(0.12, 0.25))
        icu_admits = max(0, min(icu_candidates, np.random.poisson(0.6) + (1 if esi_1 > 0 else 0)))
        
        # New ICU patient length of stay (longer, typically 12 - 48 hours)
        new_icu_stays = [max(4.0, np.random.normal(24.0, 8.0)) for _ in range(icu_admits)]
        active_icu_patients_remaining_stay.extend(new_icu_stays)
        
        # Decrement ICU stays
        active_icu_patients_remaining_stay = [stay - 1.0 for stay in active_icu_patients_remaining_stay]
        icu_discharged_patients = [stay for stay in active_icu_patients_remaining_stay if stay <= 0]
        icu_discharges = len(icu_discharged_patients)
        active_icu_patients_remaining_stay = [stay for stay in active_icu_patients_remaining_stay if stay > 0]
        
        curr_icu_occupied = min(TOTAL_ICU_BEDS + 2, len(active_icu_patients_remaining_stay))
        
        # Staff availability (shift-based)
        if 7 <= hour <= 15:
            base_staff = 22 # Day shift
        elif 16 <= hour <= 23:
            base_staff = 20 # Evening shift
        else:
            base_staff = 14 # Night shift
            
        # Adjust staff if surge protocol triggered
        if curr_ed_occupied >= 45:
            base_staff += 3 # On-call staff mobilized
            
        staff_availability = max(8, int(round(np.random.normal(base_staff, 1.2))))
        
        record = {
            "timestamp": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "date": date_str,
            "day_of_week": day_of_week,
            "hour": hour,
            "season": season,
            "is_weekend": is_weekend,
            "is_holiday": is_holiday,
            "total_emergency_beds": TOTAL_ED_BEDS,
            "occupied_emergency_beds": curr_ed_occupied,
            "available_emergency_beds": avail_ed_beds,
            "current_emergency_patients": curr_ed_patients,
            "new_emergency_admissions": arrivals,
            "emergency_discharges": discharges,
            "total_icu_beds": TOTAL_ICU_BEDS,
            "occupied_icu_beds": curr_icu_occupied,
            "icu_admissions": icu_admits,
            "icu_discharges": icu_discharges,
            "average_length_of_stay": alos,
            "staff_availability": staff_availability,
            "ambulance_arrivals": ambulances,
            "esi_level_1": int(esi_1),
            "esi_level_2": int(esi_2),
            "esi_level_3": int(esi_3),
            "esi_level_4": int(esi_4),
            "esi_level_5": int(esi_5),
            "data_attribution": "Demo Dataset: Synthetic data generated for academic prototype."
        }
        records.append(record)
        
    df = pd.DataFrame(records)
    
    # Calculate baseline metrics
    df["emergency_bed_occupancy_pct"] = (df["occupied_emergency_beds"] / df["total_emergency_beds"] * 100.0).round(2)
    df["icu_occupancy_pct"] = (df["occupied_icu_beds"] / df["total_icu_beds"] * 100.0).round(2)
    
    # Feature Engineering: Rolling metrics & growth rates
    df["rolling_admissions_1h"] = df["new_emergency_admissions"]
    df["rolling_admissions_3h"] = df["new_emergency_admissions"].rolling(window=3, min_periods=1).sum().round(1)
    df["rolling_admissions_6h"] = df["new_emergency_admissions"].rolling(window=6, min_periods=1).sum().round(1)
    df["average_admissions"] = df["new_emergency_admissions"].rolling(window=24, min_periods=1).mean().round(2)
    df["admission_growth_rate"] = ((df["new_emergency_admissions"] - df["new_emergency_admissions"].shift(1)) / 
                                   df["new_emergency_admissions"].shift(1).replace(0, 1)).fillna(0).round(3)
    
    # Target calculations for 1h, 2h, 3h, 6h ahead
    for h in [1, 2, 3, 6]:
        df[f"future_ed_occupancy_{h}h"] = df["emergency_bed_occupancy_pct"].shift(-h)
        df[f"future_ed_patients_{h}h"] = df["current_emergency_patients"].shift(-h)
        df[f"future_icu_occupancy_{h}h"] = df["icu_occupancy_pct"].shift(-h)
        
    # Capacity classification function based on standard thresholds:
    # 0–60%: NORMAL, 61–75%: BUSY, 76–90%: HIGH, 91–100%: CRITICAL, >100%: OVER CAPACITY
    def classify_capacity(pct):
        if pd.isna(pct):
            return "NORMAL"
        if pct <= 60.0:
            return "NORMAL"
        elif pct <= 75.0:
            return "BUSY"
        elif pct <= 90.0:
            return "HIGH"
        elif pct <= 100.0:
            return "CRITICAL"
        else:
            return "OVER CAPACITY"
            
    df["future_capacity_class_1h"] = df["future_ed_occupancy_1h"].apply(classify_capacity)
    df["future_capacity_class_3h"] = df["future_ed_occupancy_3h"].apply(classify_capacity)
    
    # Drop rows at tail where future shift is NaN
    df = df.dropna().reset_index(drop=True)
    
    # Save to CSV
    df.to_csv(output_file, index=False)
    print(f"Successfully generated {len(df)} synthetic records in {output_file}")
    print(f"Demo Dataset: Synthetic data generated for academic prototype.")
    print("\nSummary of ED Bed Occupancy %:")
    print(df["emergency_bed_occupancy_pct"].describe())
    print("\nCapacity Class Distribution (1h ahead):")
    print(df["future_capacity_class_1h"].value_counts(normalize=True).round(3) * 100)
    
    return df

if __name__ == "__main__":
    generate_synthetic_hospital_data()
