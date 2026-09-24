"""ML + rule engines: task-time prediction, explainable anomaly detection, condition warnings, fatigue risk indicator."""
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, IsolationForest
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder

import data

# Organisers' task features first, then signals known BEFORE a task starts. Nothing measured during or after
# the task (idle time, fuel, cycles, alerts, actual time) is used as an input.
TIME_FEATURES = ["task_type", "weather", "operator_skill", "machine_age_yrs",
                 "machine_type", "soil", "temp_c", "slope_deg", "volume_m3", "operator_pace_hist"]
CATEGORICAL = ["task_type", "weather", "operator_skill", "machine_type", "soil"]
FEATURE_LABELS = {"task_type": "Task type", "weather": "Weather", "operator_skill": "Operator skill",
                  "machine_age_yrs": "Machine age (yrs)", "machine_type": "Machine type", "soil": "Soil",
                  "temp_c": "Temperature (°C)", "slope_deg": "Ground slope (°)", "volume_m3": "Volume (m³)",
                  "operator_pace_hist": "Operator's past pace (actual ÷ planner)"}
FUEL_PRICE = 95        # ₹ per litre of diesel (assumption)
CO2_PER_L = 2.68       # kg CO2 per litre of diesel (standard emission factor)
IDLE_FUEL_LPH = 3.5    # assumed idle burn rate; used only for the idle-fuel estimate
PACE_WINDOW = 30       # past sessions used for the operator pace feature


def enrich(sessions, machines, operators):
    s = sessions.merge(machines[["machine_id", "machine_type", "model"]], on="machine_id") \
                .merge(operators[["operator_id", "name", "experience_yrs"]], on="operator_id")
    s = s.sort_values("timestamp").reset_index(drop=True)
    s["idle_ratio"] = s.idling_time_min / s.duration_min
    s["work_h"] = (s.duration_min - s.idling_time_min).clip(lower=1) / 60
    s["fuel_per_work_h"] = s.fuel_used_l / s.work_h
    s["cycles_per_h"] = s.load_cycles / s.work_h
    s["m3_per_cycle"] = s.volume_m3 / s.load_cycles
    s["speed_vs_limit"] = s.max_speed_kmh / s.machine_type.map(data.SPEED_LIMIT)
    s["tilt_excess_deg"] = s.max_tilt_deg - s.slope_deg
    s["idle_fuel_l"] = s.idling_time_min / 60 * IDLE_FUEL_LPH
    s["pace_ratio"] = s.duration_min / s.estimated_time_min
    s["operator_pace_hist"] = operator_pace_history(s)
    return s


def operator_pace_history(s):
    """For each session: median (actual ÷ planner) over the operator's previous PACE_WINDOW sessions from
    strictly EARLIER days. Uses only information available before the task, so there is no target leakage."""
    out = pd.Series(np.nan, index=s.index)
    for _, g in s.groupby("operator_id"):
        g = g.sort_values("timestamp")
        dates = g.timestamp.dt.date.to_numpy()
        ratio = g.pace_ratio.to_numpy()
        for pos, idx in enumerate(g.index):
            prev = ratio[:pos][dates[:pos] < dates[pos]][-PACE_WINDOW:]
            if len(prev) >= 5:
                out[idx] = np.median(prev)
    return out  # NaN = not enough history (HistGradientBoosting handles missing values natively)


def current_pace(s, operator_id):
    r = s[s.operator_id == operator_id].sort_values("timestamp").pace_ratio.tail(PACE_WINDOW)
    return float(r.median()) if len(r) >= 5 else np.nan


def _new_model():
    return make_pipeline(
        ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL)],
                          remainder="passthrough"),
        HistGradientBoostingRegressor(max_iter=300, learning_rate=0.06, min_samples_leaf=20, random_state=0),
    )


def train_time_model(s):
    """Temporal hold-out evaluation (train on earlier days, test on the latest 20% of days) against the planner
    baseline, then a deployment model refit on all history. Also out-of-fold 'expected time' per session."""
    days = np.sort(s.timestamp.dt.normalize().unique())
    cutoff = days[int(len(days) * 0.8)]
    train, test = s[s.timestamp < cutoff], s[s.timestamp >= cutoff]
    eval_model = _new_model().fit(train[TIME_FEATURES], train.duration_min)
    pred = pd.Series(eval_model.predict(test[TIME_FEATURES]), index=test.index)
    y, planner = test.duration_min, test.estimated_time_min
    type_median = test.task_type.map(train.groupby("task_type").duration_min.median())

    rng = np.random.default_rng(0)  # bootstrap CI for the relative MAE reduction vs planner
    err_ai, err_pl = (pred - y).abs().to_numpy(), (planner - y).abs().to_numpy()
    boots = [1 - err_ai[i].mean() / err_pl[i].mean() for i in (rng.integers(0, len(y), len(y)) for _ in range(1000))]
    metrics = {
        "ai_mae": float(err_ai.mean()), "planner_mae": float(err_pl.mean()),
        "type_median_mae": mean_absolute_error(y, type_median),
        "reduction": 1 - err_ai.mean() / err_pl.mean(), "reduction_ci": (float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))),
        "ai_mape": float(np.mean(err_ai / y)), "planner_mape": float(np.mean(err_pl / y)),
        "ai_within_10": float(np.mean(err_ai / y <= .10)), "planner_within_10": float(np.mean(err_pl / y <= .10)),
        "ai_bias": float((pred - y).mean()), "planner_bias": float((planner - y).mean()),
        "n_train": len(train), "n_test": len(test),
        "train_period": (train.timestamp.min(), train.timestamp.max()), "test_period": (test.timestamp.min(), test.timestamp.max()),
    }
    imp = permutation_importance(eval_model, test[TIME_FEATURES], y, n_repeats=5, random_state=0,
                                 scoring="neg_mean_absolute_error")
    importance = pd.Series(imp.importances_mean, index=TIME_FEATURES).clip(lower=0)
    importance = (importance / importance.sum() * 100).rename(FEATURE_LABELS).sort_values()

    # Out-of-fold expected time for every session (folds grouped by day): used as a fair benchmark for
    # "task execution" without scoring an operator against a model that has already seen that session.
    oof = pd.Series(np.nan, index=s.index)
    for tr_idx, te_idx in GroupKFold(n_splits=5).split(s, groups=s.timestamp.dt.date):
        m = _new_model().fit(s.iloc[tr_idx][TIME_FEATURES], s.iloc[tr_idx].duration_min)
        oof.iloc[te_idx] = m.predict(s.iloc[te_idx][TIME_FEATURES])

    final_model = _new_model().fit(s[TIME_FEATURES], s.duration_min)
    reference = {f: (s[f].mode().iloc[0] if f in CATEGORICAL else float(s[f].median())) for f in TIME_FEATURES}
    return {"model": final_model, "metrics": metrics, "importance": importance, "test_pred": pred,
            "oof": oof, "reference": reference}


def predict_minutes(model, **features):
    row = {k: features.get(k, np.nan) for k in TIME_FEATURES}
    return float(model.predict(pd.DataFrame([row]))[0])


def explain_prediction(model, features, reference):
    """Local explanation by substitution: for each input, how much the prediction changes if that input is set
    to the site-typical value (most common category / median). Only model inputs appear here."""
    base = predict_minutes(model, **features)
    rows = []
    for f in TIME_FEATURES:
        val, ref = features.get(f, np.nan), reference[f]
        if (isinstance(val, float) and np.isnan(val)) or val == ref:
            continue
        delta = base - predict_minutes(model, **{**features, f: ref})
        def txt(v):
            if isinstance(v, (int, float, np.number)):
                return f"{v:.2f}" if f == "operator_pace_hist" else f"{v:.0f}"
            return str(v)
        ref_txt, val_txt = txt(ref), txt(val)
        rows.append({"factor": FEATURE_LABELS[f], "value": val_txt, "site typical": ref_txt, "effect_min": round(delta, 1)})
    df = pd.DataFrame(rows, columns=["factor", "value", "site typical", "effect_min"])
    return base, df.reindex(df.effect_min.abs().sort_values(ascending=False).index)


# ---------------------------------------------------------------- anomaly detection
ANOMALY_FEATURES = {
    "idle_ratio": "Idle share", "fuel_per_work_h": "Fuel burn while working", "cycles_per_h": "Load-cycle rate",
    "speed_vs_limit": "Top speed vs site limit", "max_tilt_deg": "Maximum tilt", "engine_temp_c": "Engine temperature",
}
_FMT = {"idle_ratio": lambda v: f"{v:.0%}", "fuel_per_work_h": lambda v: f"{v:.1f} L/h", "cycles_per_h": lambda v: f"{v:.1f}/h",
        "speed_vs_limit": lambda v: f"{v:.0%} of limit", "max_tilt_deg": lambda v: f"{v:.1f}°", "engine_temp_c": lambda v: f"{v:.1f}°C"}
_RECOMMEND = {
    "idle_ratio": "Review waiting and repositioning: shut down when waiting more than 5 min and coordinate truck arrival.",
    "fuel_per_work_h": "Check the power mode and possible leaks. If the operating pattern is normal, book a machine inspection.",
    "cycles_per_h": "Check truck positioning and bucket fill. Low cycle rates often mean waiting or long swings.",
    "speed_vs_limit": "Respect the site speed limit, especially on haul roads and slopes.",
    "max_tilt_deg": "Review slope technique: travel straight up/down, keep the bucket low, avoid side-slopes.",
    "engine_temp_c": "Check coolant level and radiator cleanliness. Reduce load in high ambient temperature.",
}


def detect_anomalies(s):
    """Isolation Forest (contamination 5%) on robust z-scores computed within each machine type."""
    z = pd.DataFrame(index=s.index)
    for f in ANOMALY_FEATURES:
        g = s.groupby("machine_type")[f]
        med = g.transform("median")
        mad = g.transform(lambda x: (x - x.median()).abs().median()).replace(0, 1e-6)
        z[f] = (s[f] - med) / (1.4826 * mad)
    iso = IsolationForest(contamination=0.05, random_state=0).fit(z)
    out = s.copy()
    out["anomaly_score"] = -iso.score_samples(z)
    out["is_anomaly"] = iso.predict(z) == -1
    out["top_feature"] = z.abs().idxmax(axis=1)
    out["reason"] = ""
    for i in out.index[out.is_anomaly]:
        top = z.loc[i].abs().sort_values(ascending=False)
        parts = [f"{ANOMALY_FEATURES[f]} {'high' if z.loc[i, f] > 0 else 'low'} ({z.loc[i, f]:+.1f} robust SD)"
                 for f in top.index[:2] if abs(z.loc[i, f]) >= 2]
        out.loc[i, "reason"] = "; ".join(parts) or "unusual combination of signals"
    return out


def explain_anomaly(s, i):
    """Evidence for one flagged session: value vs the operator's own baseline and the site baseline
    (median of the same machine type), both computed from the data, excluding the session itself."""
    row = s.loc[i]
    others = s.drop(index=i)
    op_base = others[others.operator_id == row.operator_id]
    site_base = others[others.machine_type == row.machine_type]
    order = sorted(ANOMALY_FEATURES, key=lambda f: -abs(row[f] / site_base[f].median() - 1))
    evidence = []
    for f in order[:3]:
        ob, sb = op_base[f].median(), site_base[f].median()
        evidence.append({"signal": ANOMALY_FEATURES[f], "this session": _FMT[f](row[f]),
                         "operator baseline": _FMT[f](ob), "site baseline": _FMT[f](sb),
                         "vs operator": f"{row[f] / ob - 1:+.0%}", "vs site": f"{row[f] / sb - 1:+.0%}"})
    context = {"When": f"{row.timestamp:%d %b %H:%M}", "Machine": f"{row.machine_id} ({row.machine_type})",
               "Operator": row.operator_id, "Task": f"{row.task_type} at {row.site}",
               "Duration": f"{row.duration_min:.0f} min", "Idle time": f"{row.idling_time_min:.0f} min",
               "Fuel used": f"{row.fuel_used_l:.1f} L", "Weather": row.weather}
    return {"title": f"Abnormal {ANOMALY_FEATURES[order[0]].lower()}", "evidence": pd.DataFrame(evidence),
            "context": context, "recommendation": _RECOMMEND[order[0]]}


def evaluate_detector(s):
    """Validation against the generator's labelled ground truth (possible only because the data is synthetic)."""
    usage = s.injected_event.str.contains("idle")
    known = (s.injected_event != "") | (s.max_tilt_deg > 15) | (s.speed_vs_limit > 1) | (s.overload_events > 0)
    flagged = s.is_anomaly
    return {"recall_usage": float(flagged[usage].mean()), "n_usage": int(usage.sum()),
            "flag_explained": float(known[flagged].mean()), "n_flagged": int(flagged.sum()),
            "base_rate_known": float(known.mean())}


# ---------------------------------------------------------------- rule engines
def condition_warnings(weather, temp_c, visibility, ground, hours_on_shift):
    w = []
    if temp_c >= 40:
        w.append(("error", "🌡️", f"Extreme heat {temp_c}°C: hydrate every 30 min, watch coolant temperature, take shade breaks."))
    elif temp_c >= 35:
        w.append(("warning", "🌡️", f"High heat {temp_c}°C: hydrate regularly and monitor engine temperature."))
    if weather == "Rainy" or ground == "Soft / muddy":
        w.append(("warning", "🌧️", "Slippery ground: reduce speed, stay away from edges and trenches, and allow longer braking distance."))
    if weather == "Windy":
        w.append(("warning", "💨", "High wind: don't lift suspended loads high, lower the boom when parked, and watch for flying debris."))
    if weather in ("Foggy", "Dusty") or visibility == "Poor":
        w.append(("warning", "🌫️", "Low visibility: lights and beacon ON, use a spotter, and sound the horn before moving."))
    if ground == "Slope > 15°":
        w.append(("error", "⛰️", "Steep slope: travel straight up or down, keep the bucket low, and never turn across the slope."))
    if hours_on_shift >= 10:
        w.append(("error", "⏱️", f"{hours_on_shift:.1f} h on shift: long-shift limit reached. Take a break or hand over."))
    elif hours_on_shift >= 8:
        w.append(("warning", "⏱️", f"{hours_on_shift:.1f} h on shift: plan a rest break soon."))
    return w


def fatigue_risk_indicator(hours_on_shift, hours_since_break, temp_c, alerts_this_shift):
    """Rule-based OPERATIONAL risk indicator (not a medical or validated fatigue measure).
    Points: shift > 6 h (+10/h, max 40); > 2 h since last break (+12/h, max 36);
    heat above 32°C (+2/°C, max 16); safety alerts this shift (+4 each, max 20)."""
    factors = [
        ("Time on shift", min(40.0, max(0.0, hours_on_shift - 6) * 10), f"{hours_on_shift:.1f} h (points after 6 h)"),
        ("Time since last break", min(36.0, max(0.0, hours_since_break - 2) * 12), f"{hours_since_break:.1f} h (points after 2 h)"),
        ("Heat", min(16.0, max(0.0, temp_c - 32) * 2), f"{temp_c}°C (points above 32°C)"),
        ("Safety alerts this shift", min(20.0, alerts_this_shift * 4.0), f"{alerts_this_shift} alert(s)"),
    ]
    score = float(min(100.0, sum(p for _, p, _ in factors)))
    level = "High" if score >= 60 else "Elevated" if score >= 30 else "Low"
    return score, level, factors


def badges(ops):
    """Sensor-based milestones only (never based on self-reported incidents, so there's no incentive to under-report)."""
    out = []
    if len(ops) >= 15 and (ops.tail(15).seatbelt_status == "Fastened").all():
        out.append(("🪢", "Buckle Champion", "Seatbelt fastened in the last 15 sessions"))
    if len(ops) >= 10 and ops.tail(10).idle_ratio.mean() < 0.15:
        out.append(("🌱", "Fuel Saver", "Average idle under 15% over the last 10 sessions"))
    if len(ops) >= 10 and ops.harsh_events.tail(10).sum() == 0:
        out.append(("🧈", "Smooth Operator", "No harsh events in the last 10 sessions"))
    return out
