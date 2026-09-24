"""Data layer for the Smart Operator Assistant.

Both organiser sample schemas are kept exactly and extended with the extra signals the machine is
assumed to collect:
  * machine telemetry: Timestamp, Machine ID, Operator ID, Engine Hours, Fuel Used (L), Load Cycles,
    Idling Time (min), Seatbelt Status, Safety Alert Triggered
  * task history: Task ID, Task Type, Weather, Operator Skill, Machine Age (yrs), Estimated Time (min), Actual Time (min)
Every work session is one row carrying both, stored in a local SQLite file so the app runs offline.
"""
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
DB_PATH = Path(os.getenv("CAT_OPERATOR_DB", ROOT / "operator.db"))  # tests point this at a temp file

TELEMETRY_SCHEMA = {
    "timestamp": "Timestamp", "machine_id": "Machine ID", "operator_id": "Operator ID",
    "engine_hours": "Engine Hours", "fuel_used_l": "Fuel Used (L)", "load_cycles": "Load Cycles",
    "idling_time_min": "Idling Time (min)", "seatbelt_status": "Seatbelt Status",
    "safety_alert_triggered": "Safety Alert Triggered",
}
TASK_SCHEMA = {
    "task_id": "Task ID", "task_type": "Task Type", "weather": "Weather", "operator_skill": "Operator Skill",
    "machine_age_yrs": "Machine Age (yrs)", "estimated_time_min": "Estimated Time (min)", "duration_min": "Actual Time (min)",
}

MACHINES = pd.DataFrame([
    ("EXC001", "Excavator", "CAT 320", 2, 1520.0),
    ("EXC002", "Excavator", "CAT 336", 4, 4310.0),
    ("LDR001", "Wheel Loader", "CAT 950 GC", 3, 2890.0),
    ("DOZ001", "Dozer", "CAT D6", 6, 6120.0),
    ("TRK001", "Articulated Truck", "CAT 745", 5, 3375.0),
    ("GRD001", "Motor Grader", "CAT 140", 1, 980.0),
], columns=["machine_id", "machine_type", "model", "machine_age_yrs", "engine_hours_start"])

OPERATORS = pd.DataFrame([
    ("OP1001", "Ravi Kumar", 12, "EXC001"),
    ("OP1002", "Anita Sharma", 3, "LDR001"),
    ("OP1003", "Mohammed Irfan", 7, "DOZ001"),
    ("OP1004", "Priya Nair", 1, "TRK001"),
    ("OP1005", "Suresh Patel", 18, "EXC002"),
    ("OP1006", "Lakshmi Iyer", 5, "GRD001"),
], columns=["operator_id", "name", "experience_yrs", "machine_id"])

# Hidden behavioural traits used ONLY by the generator. They are never stored in the database or shown
# to the models, so skill gaps have to be inferred from observed behaviour.
#   pace: unobserved speed multiplier beyond the Beginner/Intermediate/Expert label
#   belt: P(seatbelt fastened) · idle: typical idle share · slope_care: 0 (careless) – 1 (careful) on slopes
#   smooth: control smoothness (fewer harsh events) · fill: bucket-fill efficiency · speeding: P(overspeed)
_TRAITS = {
    "OP1001": dict(pace=0.97, belt=0.98, idle=0.24, slope_care=0.30, smooth=0.90, fill=1.00, speeding=0.03),
    "OP1002": dict(pace=1.05, belt=0.70, idle=0.14, slope_care=0.80, smooth=0.80, fill=0.97, speeding=0.07),
    "OP1003": dict(pace=1.02, belt=0.96, idle=0.30, slope_care=0.75, smooth=0.85, fill=1.00, speeding=0.04),
    "OP1004": dict(pace=1.08, belt=0.90, idle=0.23, slope_care=0.70, smooth=0.40, fill=0.95, speeding=0.06),
    "OP1005": dict(pace=0.93, belt=0.99, idle=0.10, slope_care=0.95, smooth=0.95, fill=1.05, speeding=0.02),
    "OP1006": dict(pace=1.00, belt=0.95, idle=0.13, slope_care=0.85, smooth=0.85, fill=0.78, speeding=0.03),
}
# Unobserved machine condition (hydraulic wear, undercarriage…) not captured by machine age
_MACHINE_CONDITION = {"EXC001": 1.00, "EXC002": 1.07, "LDR001": 0.98, "DOZ001": 1.09, "TRK001": 1.03, "GRD001": 0.97}

TRAINING_MODULES = {  # id -> title (single source of truth for the training log)
    "safety": "Excavator safety essentials",
    "fuel": "Fuel efficiency & idle reduction",
    "walkaround": "Machine walkaround & familiarisation",
    "operation": "Operating controls & settings",
    "terrain": "Safe operation on sloped terrain",
    "simulator": "Scenario simulator",
}
# Simulated past training and its SIMULATED behavioural effect (disclosed in PITCH.md). This lets the
# app demonstrate post-training verification on history. The verification itself only uses observed data.
_TRAINING_HISTORY = [
    ("OP1001", "fuel", 40, {"idle": 0.12}),                      # behaviour changed after training
    ("OP1002", "safety", 30, {"belt": 0.98, "speeding": 0.02}),  # behaviour changed after training
    ("OP1004", "fuel", 25, {}),                                   # training completed, NO behaviour change
]

TASK_TYPES = {
    "Excavator": ["Earth Excavation", "Trenching", "Material Loading", "Demolition"],
    "Wheel Loader": ["Material Loading", "Earth Excavation"],
    "Dozer": ["Earth Excavation", "Grading"],
    "Articulated Truck": ["Haulage"],
    "Motor Grader": ["Grading"],
}
ALL_TASKS = sorted({t for v in TASK_TYPES.values() for t in v})
SITES = {"North Pit": 9, "Access Road B": 3, "Stockyard 2": 2, "Foundation Block C": 5, "Drainage Line": 7}
SOILS = ["Sand", "Clay", "Gravel", "Rock"]
WEATHER = ["Sunny", "Cloudy", "Rainy", "Windy", "Foggy", "Dusty"]
SKILLS = ["Beginner", "Intermediate", "Expert"]
SERVICE_INTERVAL_H = 500
SPEED_LIMIT = {"Excavator": 6, "Wheel Loader": 25, "Dozer": 10, "Articulated Truck": 40, "Motor Grader": 30}

_SOIL = {"Sand": 0.9, "Clay": 1.15, "Gravel": 1.0, "Rock": 1.45}
_WX = {"Sunny": 1.0, "Cloudy": 1.03, "Rainy": 1.25, "Windy": 1.12, "Foggy": 1.2, "Dusty": 1.1}
_SKILL = {"Beginner": 1.35, "Intermediate": 1.12, "Expert": 0.95}
_RATE = {"Earth Excavation": 110, "Trenching": 60, "Material Loading": 150, "Grading": 200,
         "Demolition": 45, "Haulage": 110}  # m3 per hour, standard planning rate
# Machine specifications (reference values a CAT machine/dealer would supply)
RATED_FUEL_LPH = {"Excavator": 18, "Wheel Loader": 16, "Dozer": 24, "Articulated Truck": 22, "Motor Grader": 14}
RATED_M3_PER_CYCLE = 10.0  # rated volume moved per load cycle at 100% fill
_FUEL_WORK = RATED_FUEL_LPH
_VISIBILITY = {"Sunny": 800, "Cloudy": 600, "Rainy": 300, "Windy": 500, "Foggy": 80, "Dusty": 150}


def skill_of(experience_yrs):
    return "Beginner" if experience_yrs < 3 else "Intermediate" if experience_yrs < 10 else "Expert"


_PLANNER_WX_ALLOWANCE = {"Rainy": 1.15, "Foggy": 1.10}


def planner_estimate_min(task, soil, volume, weather=None):
    """Planner baseline: standard rate × soil difficulty, plus a contingency for rain/fog, rounded to 5 min.
    Like a real planning sheet it does not model individual operators, machine condition, slope or heat."""
    minutes = volume / _RATE[task] * 60 * _SOIL[soil] * _PLANNER_WX_ALLOWANCE.get(weather, 1.0)
    return float(max(5, round(minutes / 5) * 5))


def machine_for_task(task):
    return next((m for m, tasks in TASK_TYPES.items() if task in tasks), "Excavator")


def volume_from_estimate(task, soil, estimated_min, weather=None):
    """Invert the planner's standard estimate to recover the planned volume (m3)."""
    return float(estimated_min) / 60 * _RATE.get(task, 100) / _SOIL.get(soil, 1.0) / _PLANNER_WX_ALLOWANCE.get(weather, 1.0)


def true_duration_min(task, soil, weather, temp_c, slope_deg, skill, machine_age, volume):
    """Observable part of task time: effects of inputs a planner/model can know before the task starts.
    The generator multiplies this by UNOBSERVED factors (operator pace, machine condition, daily site
    disruption, per-task noise) and adds occasional delays, so no model can reproduce it exactly."""
    minutes = volume / _RATE[task] * 60 * _SOIL[soil] * _WX[weather] * _SKILL[skill]
    minutes *= 1 + machine_age * 0.03 + max(0, temp_c - 35) * 0.02 + slope_deg * 0.012
    return minutes


def training_date(days_ago):
    return (datetime.now() - timedelta(days=days_ago)).replace(hour=16, minute=0, second=0, microsecond=0)


def _traits_on(op_id, day):
    """Operator traits on a given day, including simulated effects of past training."""
    t = dict(_TRAITS[op_id])
    for who, _, days_ago, effect in _TRAINING_HISTORY:
        if who == op_id and day.date() > training_date(days_ago).date():
            t.update(effect)
    return t


def _sessions(days=75, seed=11):
    rng = np.random.default_rng(seed)
    mt = MACHINES.set_index("machine_id")
    engine_h = mt.engine_hours_start.to_dict()
    start_day = (datetime.now() - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
    rows, n = [], 1
    for d in range(days):
        day = start_day + timedelta(days=d)
        if day.weekday() == 6:  # Sunday off
            continue
        weather = rng.choice(WEATHER, p=[.4, .2, .15, .12, .07, .06])
        base_temp = rng.normal(31, 5)
        site_disruption = rng.lognormal(0, 0.06)  # unobserved: truck availability, coordination, rework
        for op in OPERATORS.itertuples():
            m = mt.loc[op.machine_id]
            tr = _traits_on(op.operator_id, day)
            skill = skill_of(op.experience_yrs)
            t = day + timedelta(hours=7, minutes=int(rng.integers(0, 45)))
            shift_start = t
            for _ in range(int(rng.integers(3, 6))):
                task = rng.choice(TASK_TYPES[m.machine_type])
                site = rng.choice(list(SITES))
                slope = max(0.0, rng.normal(SITES[site], 2))
                soil = rng.choice(SOILS, p=[.3, .3, .25, .15])
                temp = base_temp + (t.hour - 8) * 0.8 + rng.normal(0, 1)
                volume = rng.uniform(30, 150)
                dur = true_duration_min(task, soil, weather, temp, slope, skill, m.machine_age_yrs, volume)
                dur *= tr["pace"] * _MACHINE_CONDITION[op.machine_id] * site_disruption * rng.lognormal(0, 0.10)
                delay = rng.uniform(15, 60) if rng.random() < .05 else 0.0  # breakdown / waiting / rework
                dur += delay
                # --- behaviour ---
                idle = dur * np.clip(rng.normal(tr["idle"], .05), .02, .9) + delay * 0.8
                injected = ""
                if rng.random() < .04:  # labelled ground truth for validating the anomaly detector
                    injected = "idle"
                    idle = dur * rng.uniform(.45, .7)
                idle = min(idle, dur * 0.95)
                work = dur - idle
                fuel = work / 60 * _FUEL_WORK[m.machine_type] * rng.normal(1, .06) + idle / 60 * 3.5
                if injected and rng.random() < .5:
                    injected = "idle+fuel"
                    fuel *= rng.uniform(1.3, 1.6)  # e.g. fuel leak / wrong power mode
                cycles = max(1, int(round(volume / (RATED_M3_PER_CYCLE * rng.uniform(.8, 1.2) * tr["fill"]))))
                belt_ok = rng.random() < tr["belt"]
                min_prox = float(np.clip(rng.gamma(3, 2.2), .4, 30))
                prox_alerts = int((min_prox < 3) * rng.integers(1, 5))
                limit = SPEED_LIMIT[m.machine_type]
                on_slope = slope >= 5
                speed_mult = 1 + (1 - tr["slope_care"]) * 0.35 if on_slope else 1.0
                max_speed = limit * rng.uniform(.55, .9) * speed_mult
                if rng.random() < tr["speeding"]:
                    max_speed = limit * rng.uniform(1.15, 1.5)
                    injected = injected or "speed"
                tilt_excess = rng.normal(3 + ((1 - tr["slope_care"]) * 5 if on_slope else 0), 2)
                max_tilt = min(slope + tilt_excess, 35)
                overload = int(rng.random() < .04) * int(rng.integers(1, 4))
                harsh = int(rng.poisson(0.05 + (1 - tr["smooth"]) * 1.2))
                engine_temp = 88 + max(0, temp - 30) * .6 + work / dur * 6 + rng.normal(0, 1.5)
                alerts = [name for cond, name in [
                    (not belt_ok, "Seatbelt"), (min_prox < 3, "Proximity"), (max_tilt > 15, "Tilt"),
                    (max_speed > limit, "Overspeed"), (overload > 0, "Overload")] if cond]
                engine_h[op.machine_id] += dur / 60
                rows.append({
                    # organisers' telemetry columns
                    "timestamp": t.replace(second=0, microsecond=0), "machine_id": op.machine_id, "operator_id": op.operator_id,
                    "engine_hours": round(engine_h[op.machine_id], 1), "fuel_used_l": round(fuel, 1),
                    "load_cycles": cycles, "idling_time_min": round(idle), "seatbelt_status": "Fastened" if belt_ok else "Unfastened",
                    "safety_alert_triggered": "Yes" if alerts else "No",
                    # organisers' task columns
                    "task_id": f"T{n:04d}", "task_type": task, "weather": weather, "operator_skill": skill,
                    "machine_age_yrs": int(m.machine_age_yrs),
                    "estimated_time_min": planner_estimate_min(task, soil, volume, weather), "duration_min": round(dur),
                    # extended signals
                    "alert_types": ", ".join(alerts), "site": site, "soil": soil, "temp_c": round(temp, 1),
                    "visibility_m": round(_VISIBILITY[weather] * rng.uniform(.7, 1.1)), "slope_deg": round(slope, 1),
                    "volume_m3": round(volume), "min_proximity_m": round(min_prox, 1), "proximity_alerts": prox_alerts,
                    "max_speed_kmh": round(max_speed, 1), "max_tilt_deg": round(max_tilt, 1), "overload_events": overload,
                    "harsh_events": harsh, "engine_temp_c": round(engine_temp, 1),
                    "hours_into_shift": round((t - shift_start).seconds / 3600, 1),
                    # generator ground truth, used ONLY to validate the anomaly detector (never a model input)
                    "injected_event": injected,
                })
                n += 1
                t += timedelta(minutes=dur + rng.uniform(10, 40))
    return pd.DataFrame(rows)


def _todays_tasks(seed=5):
    rng = np.random.default_rng(seed)
    today = datetime.now().replace(hour=7, minute=30, second=0, microsecond=0)
    mt = MACHINES.set_index("machine_id")
    rows, tid = [], 1
    for op in OPERATORS.itertuples():
        t = today
        for _ in range(int(rng.integers(4, 6))):
            site = rng.choice(list(SITES))
            task = rng.choice(TASK_TYPES[mt.loc[op.machine_id, "machine_type"]])
            soil = rng.choice(SOILS)
            volume = int(rng.uniform(40, 140))
            rows.append({"task_id": f"D{tid:03d}", "operator_id": op.operator_id, "machine_id": op.machine_id,
                         "task_type": task, "site": site, "soil": soil, "slope_deg": SITES[site], "volume_m3": volume,
                         "estimated_time_min": planner_estimate_min(task, soil, volume),
                         "scheduled_start": t.strftime("%Y-%m-%d %H:%M"),
                         "priority": rng.choice(["High", "Medium", "Low"], p=[.3, .5, .2]),
                         "status": "Pending", "started_at": None, "completed_at": None,
                         "notes": rng.choice(["", "Watch for underground cables", "Ground crew on site",
                                              "Coordinate with truck TRK001", "Overhead power line nearby", ""])})
            tid += 1
            t += timedelta(minutes=planner_estimate_min(task, soil, volume) + int(rng.uniform(15, 30)))
    return pd.DataFrame(rows)


def _connect():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db(force=False):
    """Create operator.db with synthetic history the first time the app runs. Also rebuilds a database that
    exists but is empty (e.g. SQLite re-created a blank file after operator.db was deleted mid-run)."""
    if DB_PATH.exists() and not force:
        con = sqlite3.connect(DB_PATH)
        try:
            ready = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='sessions'").fetchone()
        finally:
            con.close()  # must close before the file can be replaced on Windows
        if ready:
            return
    DB_PATH.unlink(missing_ok=True)
    sessions = _sessions()
    machines = MACHINES.copy()
    since_service = {"EXC001": 462, "EXC002": 180, "LDR001": 330, "DOZ001": 488, "TRK001": 250, "GRD001": 95}
    latest = sessions.groupby("machine_id").engine_hours.max()
    machines["last_service_hours"] = machines.machine_id.map(lambda m: round(latest[m] - since_service[m], 1))
    with _connect() as con:
        machines.to_sql("machines", con, index=False)
        OPERATORS.to_sql("operators", con, index=False)
        sessions.to_sql("sessions", con, index=False)
        _todays_tasks().to_sql("tasks", con, index=False)
        pd.DataFrame([
            {"time": (datetime.now() - timedelta(days=12)).strftime("%Y-%m-%d %H:%M"), "operator_id": "OP1004",
             "machine_id": "TRK001", "type": "Near miss", "severity": "High",
             "description": "[Stockyard 2] Reversed toward a ground worker; stopped after the proximity alarm."},
            {"time": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d %H:%M"), "operator_id": "OP1002",
             "machine_id": "LDR001", "type": "Unsafe condition", "severity": "Medium",
             "description": "[North Pit] Stockpile edge undercut after rain."},
        ]).to_sql("incidents", con, index=False)
        pd.DataFrame(columns=["operator_id", "topic", "date", "slot", "instructor"]).to_sql("bookings", con, index=False)
        pd.DataFrame(columns=["operator_id", "machine_id", "time", "items_ok", "issues"]).to_sql("checklists", con, index=False)
        pd.DataFrame([{"operator_id": who, "module_id": mod, "module": TRAINING_MODULES[mod], "score": 100.0,
                       "time": training_date(days_ago).strftime("%Y-%m-%d %H:%M")}
                      for who, mod, days_ago, _ in _TRAINING_HISTORY]).to_sql("training_log", con, index=False)
    ensure_review_table()
    if DB_PATH.parent == ROOT:  # don't overwrite the demo CSVs from tests using a temp database
        export_csvs(sessions)


def export_csvs(sessions):
    """Human-readable copies of the dataset in the organisers' exact formats (+ our extra columns).
    The generator's ground-truth label (injected_event) is left out: it is only for validating the detector."""
    sessions = sessions.drop(columns=["injected_event"])
    tel = telemetry_format(sessions)
    tel.join(sessions.drop(columns=list(TELEMETRY_SCHEMA))).to_csv(ROOT / "synthetic_machine_data.csv", index=False)
    task_format(sessions).join(sessions[["machine_id", "operator_id", "soil", "temp_c", "slope_deg", "volume_m3"]]) \
        .to_csv(ROOT / "synthetic_task_data.csv", index=False)


def telemetry_format(sessions):
    out = sessions[list(TELEMETRY_SCHEMA)].rename(columns=TELEMETRY_SCHEMA)
    out["Timestamp"] = pd.to_datetime(out["Timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    return out


def task_format(sessions):
    return sessions[list(TASK_SCHEMA)].rename(columns=TASK_SCHEMA)


def read(table):
    with _connect() as con:
        df = pd.read_sql(f"SELECT * FROM {table}", con)
    if "timestamp" in df:
        df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601")
    return df


def log_training(operator_id, module_id, score):
    append("training_log", {"operator_id": operator_id, "module_id": module_id,
                            "module": TRAINING_MODULES.get(module_id, module_id), "score": float(score),
                            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})  # seconds: a retake is a new case


def append(table, row: dict):
    with _connect() as con:
        pd.DataFrame([row]).to_sql(table, con, index=False, if_exists="append")


REVIEW_COLUMNS = ["operator_id", "module_id", "training_time", "decision", "assessment", "note", "reviewer", "time"]


def ensure_review_table():
    """Additive migration for the supervisor review layer: creates `supervisor_reviews` if it is missing.
    Existing tables and rows are never touched, so this is safe on an existing operator.db."""
    with _connect() as con:
        con.execute("CREATE TABLE IF NOT EXISTS supervisor_reviews (operator_id TEXT, module_id TEXT, training_time TEXT, "
                    "decision TEXT, assessment TEXT, note TEXT, reviewer TEXT, time TEXT)")


def read_reviews():
    ensure_review_table()
    return read("supervisor_reviews")


def log_review(operator_id, module_id, training_time, decision, assessment, note="", reviewer="Site supervisor (prototype)"):
    """Append-only: every supervisor decision is a new row; the latest row for a training decides its state."""
    ensure_review_table()
    append("supervisor_reviews", {"operator_id": operator_id, "module_id": module_id, "training_time": training_time,
                                  "decision": decision, "assessment": assessment, "note": note, "reviewer": reviewer,
                                  "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})


def update_task(task_id, **fields):
    sets = ", ".join(f"{k} = ?" for k in fields)
    with _connect() as con:
        con.execute(f"UPDATE tasks SET {sets} WHERE task_id = ?", [*fields.values(), task_id])


NORMAL_OBJECT_MIN_M = 7.0          # background objects never come closer than this in normal operation
DEMO_WORKER_DISTANCE_M = 1.6       # "Worker approaching" demo: inside the 3 m stop zone
DEMO_WORKER_BEARING = 20.0         # degrees, fixed so the radar dot stays put


def live_reading(machine_type, tick, rng, demo):
    """One simulated real-time telemetry reading (on a real machine: CAN bus / sensors)."""
    working = rng.random() > 0.2 and not demo.get("parked")
    # Normal operation: background objects stay OUTSIDE the 6 m caution zone (no spontaneous proximity alerts)
    objects = [(float(rng.uniform(0, 360)), float(np.clip(NORMAL_OBJECT_MIN_M + rng.gamma(3, 2), NORMAL_OBJECT_MIN_M, 30)), kind)
               for kind in rng.choice(["Worker", "Vehicle", "Structure"], size=int(rng.integers(2, 5)))]
    if demo.get("person_close"):  # demo scenario: one worker, fixed position, persists while the toggle is on
        objects.append((DEMO_WORKER_BEARING, DEMO_WORKER_DISTANCE_M, "Worker"))
    speed = rng.uniform(2, SPEED_LIMIT[machine_type] * 0.8) if working else 0.0
    if demo.get("overspeed"):
        speed = SPEED_LIMIT[machine_type] * 1.3
    tilt = abs(rng.normal(4, 1.5)) + (17 if demo.get("slope") else 0)
    return {
        "seatbelt": not demo.get("unbuckled"), "speed_kmh": round(speed, 1), "tilt_deg": round(tilt, 1),
        "engine_rpm": int(rng.normal(1800, 80) if working else rng.normal(850, 20)),
        "engine_temp_c": round(rng.normal(92, 1.5) + (9 if demo.get("hot") else 0), 1),
        "fuel_rate_lph": round(rng.normal(18, 1.5) if working else rng.normal(3.5, .3), 1),
        "load_pct": round(float(np.clip(rng.normal(70, 12), 0, 100)) if working else 0.0, 1),
        "idling": not working, "objects": objects,
    }
