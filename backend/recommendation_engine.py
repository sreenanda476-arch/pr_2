"""
Hospital Emergency Capacity Prediction System
Decision Support & Resource Recommendation Engine

Generates prioritized, actionable recommendations for hospital administrators
based on current & projected ED and ICU capacity, severity distributions,
staffing ratios, and ambulance traffic.
"""

from typing import Dict, Any, List

def generate_recommendations(prediction_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    curr = prediction_result.get("current_state", {})
    horizons = prediction_result.get("horizons", {})
    raw = prediction_result.get("raw_features", {})
    
    current_occ = curr.get("ed_occupancy_pct", 50.0)
    pred_1h_occ = horizons.get("1h", {}).get("predicted_ed_occupancy_pct", current_occ)
    pred_3h_occ = horizons.get("3h", {}).get("predicted_ed_occupancy_pct", current_occ)
    pred_6h_occ = horizons.get("6h", {}).get("predicted_ed_occupancy_pct", current_occ)
    
    current_icu_occ = curr.get("icu_occupancy_pct", 50.0)
    pred_1h_icu = horizons.get("1h", {}).get("predicted_icu_occupancy_pct", current_icu_occ)
    pred_3h_icu = horizons.get("3h", {}).get("predicted_icu_occupancy_pct", current_icu_occ)
    
    staff = curr.get("staff_availability", 20)
    patients = curr.get("current_patients", 30)
    staff_patient_ratio = round(staff / max(1, patients), 2)
    
    ambulances = curr.get("ambulance_arrivals", 2)
    esi_1 = raw.get("esi_level_1", 1)
    esi_2 = raw.get("esi_level_2", 3)
    esi_4 = raw.get("esi_level_4", 2)
    esi_5 = raw.get("esi_level_5", 1)
    
    peak_pred_occ = max(pred_1h_occ, pred_3h_occ)
    peak_icu_occ = max(pred_1h_icu, pred_3h_icu)
    
    recommendations = []
    
    # 1. CRITICAL OVER-CAPACITY EMERGENCY INTERVENTIONS (>90% or >100%)
    if peak_pred_occ >= 90.0:
        recommendations.append({
            "category": "Bed Management",
            "priority": "CRITICAL",
            "title": "Activate Level 2 Surge Protocol & Overflow Unit",
            "description": f"Predicted ED occupancy reaches {peak_pred_occ:.1f}% within 3 hours. Convert the observation annex and Day Surgery Recovery Ward into 10 active ED surge beds. Mandate immediate transfer of awaiting-discharge patients to the Discharge Lounge.",
            "impact": "+10 Surge Beds (-16% Occupancy Pressure)",
            "action_code": "ACTIVATE_SURGE_LVL2",
            "timeframe": "Immediate (< 30 mins)"
        })
        
        recommendations.append({
            "category": "Staffing",
            "priority": "CRITICAL",
            "title": "Recall On-Call Clinical Roster (Code Surge Staffing)",
            "description": f"Call in 4 on-call emergency registered nurses and 2 attending emergency physicians. Reassign 2 float nurses from low-census inpatient units to ED triage and resuscitation bays.",
            "impact": "+6 Clinical Staff (Restores safe 1:3 nurse-patient ratio)",
            "action_code": "RECALL_SURGE_STAFF",
            "timeframe": "Immediate (< 45 mins)"
        })
        
        recommendations.append({
            "category": "EMS Diversion",
            "priority": "HIGH",
            "title": "Request Regional EMS Diversion for Basic Life Support (BLS)",
            "description": "Notify Regional Emergency Medical Services (EMS) dispatch to initiate partial ambulance diversion for non-critical (ESI 3-5) patients to neighboring network hospitals for 3 hours. Maintain open trauma/STEMI/Stroke reception.",
            "impact": "Reduces incoming ambulances by ~50%",
            "action_code": "EMS_PARTIAL_DIVERSION",
            "timeframe": "Within 45 mins"
        })
        
    elif peak_pred_occ >= 75.0:
        # HIGH CAPACITY PROTOCOLS (75% - 89%)
        recommendations.append({
            "category": "Bed Management",
            "priority": "HIGH",
            "title": "Fast-Track Inpatient Bed Turnaround & Discharge Rounding",
            "description": f"Predicted ED load is {peak_pred_occ:.1f}% (High). Dispatch ED Nurse Navigator to inpatient medical/surgical wards to clear bed blocks and expedite transport of 6 admitted ED boarding patients.",
            "impact": "Frees up 6-8 ED beds within 90 minutes",
            "action_code": "EXPEDITE_INPATIENT_BEDS",
            "timeframe": "Next 60 mins"
        })
        
        recommendations.append({
            "category": "Staffing",
            "priority": "HIGH",
            "title": "Mobilize Auxiliary Float Triage Team",
            "description": "Deploy 2 additional triage screening nurses to prevent front-door bottlenecks and reduce wait-time to physician initial assessment.",
            "impact": "-25 min triage waiting time",
            "action_code": "DEPLOY_FLOAT_NURSES",
            "timeframe": "Next 60 mins"
        })
        
    else:
        # NORMAL / BUSY CAPACITY PROTOCOLS (<75%)
        recommendations.append({
            "category": "Bed Management",
            "priority": "INFO",
            "title": "Standard Flow Monitoring & Routine Turnaround",
            "description": f"Emergency capacity remains within sustainable operating bounds ({current_occ:.1f}% current, {peak_pred_occ:.1f}% peak). Maintain standard 4-hour discharge target benchmarks.",
            "impact": "Optimized continuous patient flow",
            "action_code": "MAINTAIN_ROUTINE",
            "timeframe": "Ongoing shift"
        })
        
    # 2. ICU CAPACITY DECISION SUPPORT
    if peak_icu_occ >= 88.0:
        recommendations.append({
            "category": "ICU Operations",
            "priority": "CRITICAL" if peak_icu_occ >= 94.0 else "HIGH",
            "title": "Initiate ICU Bed Prioritization & Elective Surgical Hold",
            "description": f"Projected ICU occupancy is {peak_icu_occ:.1f}%. Place an immediate hold on scheduled elective inpatient surgeries that require anticipated post-op ICU recovery beds. Conduct rapid step-down rounds on 2 telemetry-ready patients.",
            "impact": "Protects 2-3 emergency ICU beds for trauma/sepsis",
            "action_code": "HOLD_ELECTIVE_ICU",
            "timeframe": "Within 60 mins"
        })
    elif peak_icu_occ >= 75.0:
        recommendations.append({
            "category": "ICU Operations",
            "priority": "MEDIUM",
            "title": "Screen Potential Step-Down Units",
            "description": f"ICU occupancy trending high at {peak_icu_occ:.1f}%. Coordinate with Step-Down Unit (SDU) charge nurse to evaluate 2 stable patients for early step-down transfer.",
            "impact": "+2 ICU bed capacity buffer",
            "action_code": "SCREEN_STEP_DOWN",
            "timeframe": "Next 2 hours"
        })
        
    # 3. TRIAGE & SEVERITY FAST-TRACK
    if (esi_4 + esi_5) >= 5:
        recommendations.append({
            "category": "Triage & Flow",
            "priority": "MEDIUM",
            "title": "Activate Fast-Track Ambulatory Clinic for Low-Acuity Cases",
            "description": f"High volume of minor acuity arrivals (ESI 4: {int(esi_4)}, ESI 5: {int(esi_5)}). Open Fast-Track minor injury lane staffed by a Physician Assistant or Nurse Practitioner to clear waiting room queue.",
            "impact": "Diverts minor cases away from acute resuscitation bays",
            "action_code": "OPEN_FAST_TRACK",
            "timeframe": "Within 45 mins"
        })
        
    # 4. AMBULANCE SWARM PREPAREDNESS
    if ambulances >= 4:
        recommendations.append({
            "category": "Supply & Staging",
            "priority": "HIGH",
            "title": "Pre-Stage Resuscitation Bays & Rapid Ambulance Offload",
            "description": f"Ambulance arrival rate is elevated ({int(ambulances)} arrivals/hour). Assign Dedicated Ambulance Triage Nurse to offload EMS stretchers under 15 minutes to avoid offload delays.",
            "impact": "Prevents ambulance offload delays and EMS bay gridlock",
            "action_code": "STAGE_AMBULANCE_OFFLOAD",
            "timeframe": "Next 30 mins"
        })
        
    # 5. STAFFING RATIO ADVISORY
    if staff_patient_ratio < 0.35 and peak_pred_occ >= 70.0:
        recommendations.append({
            "category": "Staffing",
            "priority": "HIGH",
            "title": "Staffing Deficit Warning: Increase Provider-to-Patient Ratio",
            "description": f"Current staff-to-patient ratio is {staff_patient_ratio:.2f} ({staff} staff for {patients} patients). Contact Float Pool Administrator to assign 2 Patient Care Technicians (PCTs) and 1 Pharmacist.",
            "impact": "Prevents provider burnout and reduces medication turnaround time",
            "action_code": "FLOAT_PCT_SUPPORT",
            "timeframe": "Next 1 hour"
        })

    return recommendations
