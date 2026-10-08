/**
 * Hospital Emergency Capacity Prediction System
 * Front-end Application Controller & Visualizations
 */

let state = {
  currentTelemetry: null,
  predictions: null,
  thresholds: {
    NORMAL_MAX: 60.0,
    BUSY_MAX: 75.0,
    HIGH_MAX: 90.0,
    CRITICAL_MAX: 100.0
  },
  historical: null,
  featureImportances: [],
  charts: {
    trajectory: null,
    diurnal: null,
    importance: null
  }
};

// Initialize Dashboard on DOM Load
document.addEventListener("DOMContentLoaded", async () => {
  console.log("Initializing Hospital Emergency Capacity Prediction System...");
  await loadStatus();
  await refreshTelemetry();
  await loadHistoricalAnalytics();
  setupEventListeners();
});

// 1. Load System Status & ML Metadata
async function loadStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    if (data.current_thresholds) {
      state.thresholds = data.current_thresholds;
      syncThresholdInputs();
    }
    if (data.feature_importances) {
      state.featureImportances = data.feature_importances;
      renderFeatureImportanceChart(state.featureImportances);
    }
    // Update ML Governance Stats
    if (data.metrics && data.metrics.ed_occupancy_1h) {
      document.getElementById("stat-mae").innerText = data.metrics.ed_occupancy_1h.mae + "%";
      document.getElementById("stat-r2").innerText = data.metrics.ed_occupancy_1h.r2;
    }
    if (data.metrics && data.metrics.ed_patients_1h) {
      document.getElementById("stat-pts-mae").innerText = data.metrics.ed_patients_1h.mae;
    }
    if (data.classification_metrics && data.classification_metrics["1h"]) {
      const acc = (data.classification_metrics["1h"].accuracy * 100).toFixed(1);
      document.getElementById("stat-acc").innerText = acc + "%";
    }
  } catch (err) {
    console.error("Error loading status:", err);
  }
}

// 2. Fetch Live Telemetry & Initial Predictions
async function refreshTelemetry() {
  try {
    const btn = document.getElementById("btn-refresh-telemetry");
    if (btn) btn.classList.add("loading");
    
    const res = await fetch("/api/current_telemetry");
    const data = await res.json();
    state.currentTelemetry = data;
    
    updateDashboardUI(data);
    populateFormWithData(data.raw_features || {});
    
    if (btn) btn.classList.remove("loading");
  } catch (err) {
    console.error("Error fetching telemetry:", err);
  }
}

// 3. Load Historical Data for Diurnal & Trend Charts
async function loadHistoricalAnalytics() {
  try {
    const res = await fetch("/api/historical_sample?hours=48");
    const data = await res.json();
    state.historical = data;
    renderDiurnalChart(data.diurnal_profile || []);
  } catch (err) {
    console.error("Error loading historical sample:", err);
  }
}

// 4. Update Complete Dashboard UI
function updateDashboardUI(predData) {
  state.predictions = predData;
  const curr = predData.current_state || {};
  const horizons = predData.horizons || {};
  const recs = predData.recommendations || [];
  const status = predData.primary_alert_status || curr.status || "NORMAL";

  // Alert Banner
  updateAlertBanner(status, predData.trend, predData.saturation_time_hours, horizons);

  // Executive KPI Cards
  updateKpiCards(curr, horizons);

  // Multi-Horizon Matrix Cards
  updateHorizonCards(horizons);

  // Decision Support Recommendations
  renderRecommendations(recs);

  // Update Trajectory Chart
  renderTrajectoryChart(curr, horizons);
}

// Update Top Alert Banner
function updateAlertBanner(status, trend, satHours, horizons) {
  const banner = document.getElementById("surge-alert-banner");
  const badge = document.getElementById("alert-status-badge");
  const msg = document.getElementById("alert-status-message");
  const sub = document.getElementById("alert-saturation-forecast");
  const tag = document.getElementById("alert-action-tag");

  const normalizedStatus = status.replace(/\s+/g, "-");
  banner.className = `surge-alert-banner ${normalizedStatus}`;
  badge.innerText = status;

  if (status === "OVER CAPACITY") {
    msg.innerText = "CODE RED SURGE: Hospital Emergency Department Exceeds 100% Operational Bed Capacity";
    sub.innerText = "Immediate Level 2 Surge Protocol Required: Open overflow wards and mandate triage diversion.";
    tag.innerText = "CRITICAL ACTION";
    tag.style.background = "rgba(225, 29, 72, 0.4)";
    tag.style.color = "#fff";
  } else if (status === "CRITICAL") {
    msg.innerText = "CRITICAL CAPACITY ALERT: Emergency Department Occupancy Exceeds 90%";
    sub.innerText = satHours 
      ? `Saturation Warning: Projected to reach Critical threshold in ${satHours} hours. Influx velocity is ${trend}.`
      : `High patient load with critical bed occupancy in next 1-3 hours. Influx velocity is ${trend}.`;
    tag.innerText = "CODE SURGE PREPAREDNESS";
    tag.style.background = "rgba(239, 68, 68, 0.3)";
    tag.style.color = "#fca5a5";
  } else if (status === "HIGH") {
    msg.innerText = "HIGH CAPACITY WARNING: Emergency Department Operating at 76–90% Load";
    sub.innerText = `Elevated patient influx. Mobilize auxiliary triage and expedite pending inpatient transfers. Trend: ${trend}.`;
    tag.innerText = "SURGE MITIGATION";
    tag.style.background = "rgba(245, 158, 11, 0.3)";
    tag.style.color = "#fde68a";
  } else if (status === "BUSY") {
    msg.innerText = "BUSY STATE: Emergency Department Operating at 61–75% Occupancy";
    sub.innerText = `Patient load is climbing. Prepare discharge rounds and monitor fast-track intake. Trend: ${trend}.`;
    tag.innerText = "ELEVATED VIGILANCE";
    tag.style.background = "rgba(56, 189, 248, 0.25)";
    tag.style.color = "#bae6fd";
  } else {
    msg.innerText = "NORMAL: Emergency Department Operating Within Sustainable Capacity Thresholds";
    sub.innerText = `Stable patient inflow and bed availability across all acuity tiers. Trend: ${trend}.`;
    tag.innerText = "ROUTINE FLOW";
    tag.style.background = "rgba(16, 185, 129, 0.2)";
    tag.style.color = "#a7f3d0";
  }
}

// Update KPI Cards
function updateKpiCards(curr, horizons) {
  // ED Occupancy
  const edOcc = curr.ed_occupancy_pct || 0;
  document.getElementById("kpi-ed-occ-val").innerText = `${edOcc.toFixed(1)}%`;
  document.getElementById("kpi-ed-beds-val").innerText = `${curr.occupied_ed_beds || 0} / ${curr.total_ed_beds || 50} Beds`;
  document.getElementById("kpi-ed-avail").innerText = `${curr.available_ed_beds || 0} Beds Available`;
  
  const edBar = document.getElementById("kpi-ed-bar");
  edBar.style.width = `${Math.min(100, edOcc)}%`;
  edBar.style.background = getStatusColor(curr.status || "NORMAL");
  
  const edBadge = document.getElementById("kpi-ed-badge");
  edBadge.innerText = curr.status || "NORMAL";
  edBadge.className = `kpi-badge badge-${(curr.status || "normal").toLowerCase().replace(/\s+/g, "-")}`;

  // ED Census
  document.getElementById("kpi-patients-val").innerText = curr.current_patients || 0;
  const pBar = document.getElementById("kpi-patients-bar");
  pBar.style.width = `${Math.min(100, ((curr.current_patients || 0) / (curr.total_ed_beds || 50)) * 100)}%`;

  // ICU Occupancy
  const icuOcc = curr.icu_occupancy_pct || 0;
  document.getElementById("kpi-icu-occ-val").innerText = `${icuOcc.toFixed(1)}%`;
  document.getElementById("kpi-icu-beds-val").innerText = `${curr.occupied_icu_beds || 0} / ${curr.total_icu_beds || 16} Beds`;
  document.getElementById("kpi-icu-avail").innerText = `${curr.available_icu_beds || 0} ICU Beds Left`;
  
  const icuBar = document.getElementById("kpi-icu-bar");
  icuBar.style.width = `${Math.min(100, icuOcc)}%`;
  icuBar.style.background = icuOcc > 85 ? "var(--status-critical)" : (icuOcc > 75 ? "var(--status-high)" : "var(--status-busy)");
  
  const icuStatus = icuOcc > 90 ? "CRITICAL" : (icuOcc > 75 ? "HIGH" : (icuOcc > 60 ? "BUSY" : "NORMAL"));
  const icuBadge = document.getElementById("kpi-icu-badge");
  icuBadge.innerText = icuStatus;
  icuBadge.className = `kpi-badge badge-${icuStatus.toLowerCase()}`;

  // Staffing
  const staff = curr.staff_availability || 20;
  const patients = curr.current_patients || 25;
  const ratio = (patients / Math.max(1, staff)).toFixed(1);
  document.getElementById("kpi-staff-val").innerText = staff;
  document.getElementById("kpi-staff-ratio-val").innerText = `Ratio: 1 : ${ratio} (Staff:Pt)`;
  
  const staffStatus = document.getElementById("kpi-staff-status");
  if (ratio > 2.5) {
    staffStatus.innerText = "STRAINED";
    staffStatus.className = "kpi-badge badge-critical";
  } else if (ratio > 1.8) {
    staffStatus.innerText = "ELEVATED";
    staffStatus.className = "kpi-badge badge-high";
  } else {
    staffStatus.innerText = "SUFFICIENT";
    staffStatus.className = "kpi-badge badge-normal";
  }

  // EMS & Influx
  document.getElementById("kpi-amb-val").innerText = curr.ambulance_arrivals || 0;
}

// Update Multi-Horizon Prediction Cards
function updateHorizonCards(horizons) {
  const hList = [1, 2, 3, 6];
  hList.forEach(h => {
    const data = horizons[`${h}h`];
    if (!data) return;

    const occ = data.predicted_ed_occupancy_pct || 0;
    const status = data.status || "NORMAL";

    document.getElementById(`h${h}-occ`).innerText = `${occ.toFixed(1)}%`;
    document.getElementById(`h${h}-patients`).innerText = data.predicted_ed_patients || 0;
    document.getElementById(`h${h}-avail`).innerText = `${data.available_ed_beds || 0} / 50`;
    document.getElementById(`h${h}-icu`).innerText = `${(data.predicted_icu_occupancy_pct || 0).toFixed(1)}%`;

    const badge = document.getElementById(`h${h}-badge`);
    badge.innerText = status;
    badge.className = `kpi-badge badge-${status.toLowerCase().replace(/\s+/g, "-")}`;

    const bar = document.getElementById(`h${h}-bar`);
    bar.style.width = `${Math.min(100, occ)}%`;
    bar.style.background = getStatusColor(status);
  });
}

// Render Decision Support Recommendations
function renderRecommendations(recs) {
  const container = document.getElementById("recommendations-list");
  const countBadge = document.getElementById("rec-count-badge");
  if (countBadge) countBadge.innerText = `${recs.length} ACTIONS TRIGGERED`;

  if (!recs || recs.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 2rem; color: var(--text-muted); font-size: 0.85rem;">
        ✅ All capacity parameters currently within nominal bounds. No immediate emergency resource re-allocation triggered.
      </div>
    `;
    return;
  }

  container.innerHTML = recs.map(r => `
    <article class="rec-card ${r.priority}">
      <div class="rec-header">
        <span class="rec-category-tag">${r.category}</span>
        <span class="rec-priority-badge badge-${r.priority.toLowerCase()}">${r.priority}</span>
      </div>
      <div class="rec-title">${r.title}</div>
      <div class="rec-desc">${r.description}</div>
      <div class="rec-meta">
        <span class="rec-impact">⚡ Impact: ${r.impact}</span>
        <span>⏱️ Timeframe: ${r.timeframe}</span>
      </div>
    </article>
  `).join("");
}

// Trajectory Chart (0h -> 1h -> 2h -> 3h -> 6h)
function renderTrajectoryChart(curr, horizons) {
  const ctx = document.getElementById("trajectoryChart");
  if (!ctx) return;

  const labels = ["Current (0h)", "+1h Ahead", "+2h Ahead", "+3h Ahead", "+6h Ahead"];
  const edData = [
    curr.ed_occupancy_pct || 0,
    horizons["1h"] ? horizons["1h"].predicted_ed_occupancy_pct : 0,
    horizons["2h"] ? horizons["2h"].predicted_ed_occupancy_pct : 0,
    horizons["3h"] ? horizons["3h"].predicted_ed_occupancy_pct : 0,
    horizons["6h"] ? horizons["6h"].predicted_ed_occupancy_pct : 0
  ];
  const icuData = [
    curr.icu_occupancy_pct || 0,
    horizons["1h"] ? horizons["1h"].predicted_icu_occupancy_pct : 0,
    horizons["2h"] ? horizons["2h"].predicted_icu_occupancy_pct : 0,
    horizons["3h"] ? horizons["3h"].predicted_icu_occupancy_pct : 0,
    horizons["6h"] ? horizons["6h"].predicted_icu_occupancy_pct : 0
  ];

  if (state.charts.trajectory) {
    state.charts.trajectory.destroy();
  }

  if (typeof Chart !== "undefined") {
    state.charts.trajectory = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          {
            label: "ED Bed Occupancy %",
            data: edData,
            borderColor: "#06b6d4",
            backgroundColor: "rgba(6, 182, 212, 0.15)",
            borderWidth: 3,
            fill: true,
            tension: 0.35,
            pointBackgroundColor: "#06b6d4",
            pointRadius: 5,
            pointHoverRadius: 8
          },
          {
            label: "ICU Occupancy %",
            data: icuData,
            borderColor: "#a855f7",
            backgroundColor: "rgba(168, 85, 247, 0.08)",
            borderWidth: 2.5,
            borderDash: [5, 5],
            fill: false,
            tension: 0.35,
            pointBackgroundColor: "#a855f7",
            pointRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "top",
            labels: { color: "#94a3b8", font: { size: 11, family: "Inter" } }
          },
          tooltip: {
            backgroundColor: "#0f172a",
            titleColor: "#f8fafc",
            bodyColor: "#94a3b8",
            borderColor: "rgba(255, 255, 255, 0.1)",
            borderWidth: 1,
            callbacks: {
              label: (ctx) => `${ctx.dataset.label}: ${ctx.raw.toFixed(1)}%`
            }
          }
        },
        scales: {
          y: {
            min: 0,
            max: 120,
            grid: { color: "rgba(255, 255, 255, 0.06)" },
            ticks: {
              color: "#64748b",
              callback: (val) => val + "%"
            }
          },
          x: {
            grid: { color: "rgba(255, 255, 255, 0.04)" },
            ticks: { color: "#94a3b8", font: { weight: 600 } }
          }
        }
      }
    });
  }
}

// Diurnal Rhythm Chart (24 Hours Profile)
function renderDiurnalChart(diurnal) {
  const ctx = document.getElementById("diurnalChart");
  if (!ctx || !diurnal || diurnal.length === 0) return;

  const hours = diurnal.map(d => `${d.hour}:00`);
  const admissions = diurnal.map(d => d.new_emergency_admissions);
  const discharges = diurnal.map(d => d.emergency_discharges);
  const ambulances = diurnal.map(d => d.ambulance_arrivals);

  if (state.charts.diurnal) {
    state.charts.diurnal.destroy();
  }

  if (typeof Chart !== "undefined") {
    state.charts.diurnal = new Chart(ctx, {
      type: "bar",
      data: {
        labels: hours,
        datasets: [
          {
            label: "Arrivals / Hr",
            data: admissions,
            backgroundColor: "rgba(56, 189, 248, 0.65)",
            borderRadius: 4,
            barPercentage: 0.7
          },
          {
            label: "Discharges / Hr",
            data: discharges,
            backgroundColor: "rgba(16, 185, 129, 0.5)",
            borderRadius: 4,
            barPercentage: 0.7
          },
          {
            label: "EMS Ambulances",
            data: ambulances,
            type: "line",
            borderColor: "#f59e0b",
            borderWidth: 2,
            pointRadius: 3,
            fill: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "top",
            labels: { color: "#94a3b8", font: { size: 11, family: "Inter" } }
          }
        },
        scales: {
          y: {
            grid: { color: "rgba(255, 255, 255, 0.06)" },
            ticks: { color: "#64748b" }
          },
          x: {
            grid: { display: false },
            ticks: { color: "#64748b", maxTicksLimit: 12 }
          }
        }
      }
    });
  }
}

// Feature Importance Bar Chart
function renderFeatureImportanceChart(features) {
  const ctx = document.getElementById("featureImportanceChart");
  if (!ctx || !features || features.length === 0) return;

  const top10 = features.slice(0, 8);
  const labels = top10.map(f => f.feature.replace(/_/g, " "));
  const values = top10.map(f => (f.importance * 100).toFixed(2));

  if (state.charts.importance) {
    state.charts.importance.destroy();
  }

  if (typeof Chart !== "undefined") {
    state.charts.importance = new Chart(ctx, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [{
          label: "Relative Feature Importance (%)",
          data: values,
          backgroundColor: "rgba(6, 182, 212, 0.7)",
          borderRadius: 4,
          barPercentage: 0.6
        }]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (c) => `Weight: ${c.raw}%`
            }
          }
        },
        scales: {
          x: {
            grid: { color: "rgba(255, 255, 255, 0.06)" },
            ticks: { color: "#64748b", callback: v => v + "%" }
          },
          y: {
            grid: { display: false },
            ticks: { color: "#94a3b8", font: { size: 10 } }
          }
        }
      }
    });
  }
}

// Scenario Quick Presets
async function runScenario(scenarioKey) {
  // Update UI pill active state
  document.querySelectorAll(".scenario-pill").forEach(p => p.classList.remove("active"));
  const activeBtn = document.getElementById(`scenario-${scenarioKey.split('_')[0]}`);
  if (activeBtn) activeBtn.classList.add("active");

  try {
    const res = await fetch("/api/simulate_scenario", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario_type: scenarioKey })
    });
    const data = await res.json();
    
    // Update scenario description banner
    document.getElementById("sc-name").innerText = (data.scenario_name || scenarioKey) + ": ";
    document.getElementById("sc-desc").innerText = data.scenario_description || "";

    // Sync input form fields
    populateFormWithData(data.raw_features || {});

    // Re-render dashboard
    updateDashboardUI(data);
  } catch (err) {
    console.error("Scenario simulation error:", err);
  }
}

// Submit Custom Prediction Form
async function submitCustomPrediction() {
  const payload = {
    current_emergency_patients: parseInt(document.getElementById("inp-patients").value),
    total_emergency_beds: parseInt(document.getElementById("inp-total-beds").value),
    occupied_emergency_beds: parseInt(document.getElementById("inp-occupied-beds").value),
    new_emergency_admissions: parseInt(document.getElementById("inp-admissions").value),
    emergency_discharges: parseInt(document.getElementById("inp-discharges").value),
    ambulance_arrivals: parseInt(document.getElementById("inp-ambulances").value),
    staff_availability: parseInt(document.getElementById("inp-staff").value),
    average_length_of_stay: parseFloat(document.getElementById("inp-alos").value),
    occupied_icu_beds: parseInt(document.getElementById("inp-icu-occ").value),
    hour: parseInt(document.getElementById("inp-hour").value),
    day_of_week: parseInt(document.getElementById("inp-day").value),
    is_holiday: parseInt(document.getElementById("inp-holiday").value),
    esi_level_1: parseInt(document.getElementById("esi-1").value),
    esi_level_2: parseInt(document.getElementById("esi-2").value),
    esi_level_3: parseInt(document.getElementById("esi-3").value),
    esi_level_4: parseInt(document.getElementById("esi-4").value),
    esi_level_5: parseInt(document.getElementById("esi-5").value)
  };

  const btn = document.getElementById("btn-run-prediction");
  btn.innerText = "Analyzing Telemetry & Computing ML...";
  btn.disabled = true;

  try {
    const res = await fetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    updateDashboardUI(data);
  } catch (err) {
    console.error("Prediction error:", err);
  } finally {
    btn.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
      Compute AI Multi-Horizon Prediction
    `;
    btn.disabled = false;
  }
}

// Populate input controls from data dictionary
function populateFormWithData(f) {
  if (!f) return;
  setVal("inp-patients", f.current_emergency_patients || 35, "lbl-patients");
  setVal("inp-total-beds", f.total_emergency_beds || 50, "lbl-total-beds");
  setVal("inp-occupied-beds", f.occupied_emergency_beds || 32, "lbl-occupied-beds");
  setVal("inp-admissions", f.new_emergency_admissions || 12, "lbl-admissions");
  setVal("inp-discharges", f.emergency_discharges || 6, "lbl-discharges");
  setVal("inp-ambulances", f.ambulance_arrivals || 3, "lbl-ambulances");
  setVal("inp-staff", f.staff_availability || 20, "lbl-staff");
  if (f.average_length_of_stay) {
    document.getElementById("inp-alos").value = f.average_length_of_stay;
    document.getElementById("lbl-alos").innerText = f.average_length_of_stay + "h";
  }
  setVal("inp-icu-occ", f.occupied_icu_beds || 11, "lbl-icu-occ");

  if (f.hour !== undefined) document.getElementById("inp-hour").value = f.hour;
  if (f.day_of_week !== undefined) document.getElementById("inp-day").value = f.day_of_week;
  if (f.is_holiday !== undefined) document.getElementById("inp-holiday").value = f.is_holiday;

  if (f.esi_level_1 !== undefined) document.getElementById("esi-1").value = f.esi_level_1;
  if (f.esi_level_2 !== undefined) document.getElementById("esi-2").value = f.esi_level_2;
  if (f.esi_level_3 !== undefined) document.getElementById("esi-3").value = f.esi_level_3;
  if (f.esi_level_4 !== undefined) document.getElementById("esi-4").value = f.esi_level_4;
  if (f.esi_level_5 !== undefined) document.getElementById("esi-5").value = f.esi_level_5;
}

function setVal(id, val, lblId) {
  const el = document.getElementById(id);
  if (el) el.value = val;
  const lbl = document.getElementById(lblId);
  if (lbl) lbl.innerText = val;
}

function syncRange(sliderId, labelId) {
  const slider = document.getElementById(sliderId);
  const label = document.getElementById(labelId);
  if (slider && label) label.innerText = slider.value;
}

function autoAdjustBeds() {
  const total = parseInt(document.getElementById("inp-total-beds").value) || 50;
  const patients = parseInt(document.getElementById("inp-patients").value) || 30;
  const occupied = Math.min(total + 6, patients);
  document.getElementById("inp-occupied-beds").value = occupied;
  document.getElementById("lbl-occupied-beds").innerText = occupied;
}

// Helpers
function getStatusColor(status) {
  switch (status) {
    case "OVER CAPACITY": return "var(--status-over)";
    case "CRITICAL": return "var(--status-critical)";
    case "HIGH": return "var(--status-high)";
    case "BUSY": return "var(--status-busy)";
    default: return "var(--status-normal)";
  }
}

// Modal management
function openModal(id) {
  document.getElementById(id).classList.add("open");
}

function closeModal(id) {
  document.getElementById(id).classList.remove("open");
}

function syncThresholdInputs() {
  const th = state.thresholds;
  if (!th) return;
  document.getElementById("th-normal").value = th.NORMAL_MAX || 60;
  document.getElementById("val-th-normal").innerText = (th.NORMAL_MAX || 60) + "%";
  document.getElementById("th-busy").value = th.BUSY_MAX || 75;
  document.getElementById("val-th-busy").innerText = (th.BUSY_MAX || 75) + "%";
  document.getElementById("th-high").value = th.HIGH_MAX || 90;
  document.getElementById("val-th-high").innerText = (th.HIGH_MAX || 90) + "%";
  document.getElementById("th-critical").value = th.CRITICAL_MAX || 100;
  document.getElementById("val-th-critical").innerText = (th.CRITICAL_MAX || 100) + "%";
}

async function saveThresholds() {
  const payload = {
    normal_max: parseFloat(document.getElementById("th-normal").value),
    busy_max: parseFloat(document.getElementById("th-busy").value),
    high_max: parseFloat(document.getElementById("th-high").value),
    critical_max: parseFloat(document.getElementById("th-critical").value)
  };

  try {
    const res = await fetch("/api/thresholds", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    state.thresholds = data.thresholds;
    closeModal("thresholds-modal");
    // Re-run prediction with new thresholds
    await submitCustomPrediction();
  } catch (err) {
    console.error("Save thresholds error:", err);
  }
}

// CSV File Upload
async function handleFileSelected(event) {
  const file = event.target.files[0];
  if (!file) return;

  const box = document.getElementById("upload-progress-box");
  const txt = document.getElementById("upload-status-text");
  box.style.display = "block";
  txt.innerText = `Uploading and parsing "${file.name}"...`;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/upload_csv", {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (res.ok) {
      txt.innerText = `✅ Processed ${data.rows_processed} records from ${data.filename}!`;
      setTimeout(() => {
        closeModal("upload-modal");
        if (data.latest_record_prediction) {
          updateDashboardUI(data.latest_record_prediction);
        }
      }, 1200);
    } else {
      txt.innerText = `❌ Error: ${data.detail || "Failed to process CSV"}`;
    }
  } catch (err) {
    txt.innerText = `❌ Upload failed: ${err.message}`;
  }
}

// Retrain Trigger
async function triggerRetrain() {
  const btn = document.getElementById("btn-retrain");
  btn.innerText = "Training Pipeline Active...";
  btn.disabled = true;

  try {
    const res = await fetch("/api/retrain", { method: "POST" });
    const data = await res.json();
    if (res.ok) {
      alert("✅ ML Pipeline retrained successfully! Model artifacts reloaded.");
      await loadStatus();
      await refreshTelemetry();
    } else {
      alert("Retraining failed: " + (data.detail || "Unknown error"));
    }
  } catch (err) {
    alert("Retraining error: " + err.message);
  } finally {
    btn.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/></svg>
      Retrain Models
    `;
    btn.disabled = false;
  }
}

function setupEventListeners() {
  // Close modals on overlay background click
  document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) {
        overlay.classList.remove("open");
      }
    });
  });
}
