"""Operator competency profile and closed-loop adaptive training.

OBSERVE   every work session is checked against an explicit, documented standard per competency
DIAGNOSE  competency score = % of the operator's recent sessions that meet the standard (with evidence counts)
INTERVENE a score below GAP_THRESHOLD is a skill gap and maps to a specific training module
TRAIN     the operator completes the module (video/lesson + knowledge check), which is logged
VERIFY    sessions before vs after the training are compared (pass rate: one-sided Fisher exact test;
          key behaviour metric: Mann-Whitney U test)
ADAPT     improvement verified → gap closed; no measurable change after enough sessions → escalate to coaching

Scores are data-derived (share of sessions meeting a standard). The standards and thresholds are explicit
policy choices listed in COMPETENCIES, not hidden weights.
"""
import numpy as np
import pandas as pd
from scipy.stats import fisher_exact, mannwhitneyu

import data

WINDOW = 30          # recent sessions that make up the current profile
MIN_SESSIONS = 8     # minimum applicable sessions to score a competency / to judge a training outcome
GAP_THRESHOLD = 70   # competency score below this is treated as a skill gap
PRE_N, POST_N = 30, 30
ADAPT_AFTER = 15     # post-training sessions without measurable improvement before escalating
ALPHA = 0.05

COMPETENCIES = {
    "safety": {"name": "Safety discipline", "module": "safety",
               "standard": "Seatbelt fastened, speed within the site limit, no overload",
               "metric": ("unbuckled", "Seatbelt-unfastened sessions", "{:.0%}", "lower")},
    "fuel": {"name": "Fuel efficiency", "module": "fuel",
             "standard": "Idle ≤ 20% of the session and fuel burn while working ≤ 120% of the machine's rated burn",
             "metric": ("idle_ratio", "Average idle share", "{:.0%}", "lower")},
    "cycle": {"name": "Cycle efficiency", "module": "operation",
              "standard": "Volume moved per load cycle ≥ 85% of rated capacity",
              "metric": ("m3_per_cycle", "Volume per load cycle", "{:.1f} m³", "higher")},
    "handling": {"name": "Machine handling", "module": "operation",
                 "standard": "No harsh braking / harsh turning events",
                 "metric": ("harsh_events", "Harsh events per session", "{:.2f}", "lower")},
    "terrain": {"name": "Terrain handling", "module": "terrain",
                "standard": "On slopes ≥ 5°: tilt ≤ 15°, ≤ 7° above the ground slope, speed ≤ 95% of limit",
                "metric": ("tilt_excess_deg", "Tilt above ground slope", "{:.1f}°", "lower")},
    "execution": {"name": "Task execution", "module": None,
                  "standard": "Actual time ≤ 120% of the model's expected time for the same conditions",
                  "metric": ("exec_ratio", "Actual ÷ expected time", "{:.2f}", "lower")},
}


def session_standards(s):
    """1 = session meets the competency standard, 0 = does not, NaN = standard does not apply."""
    rated_fuel = s.machine_type.map(data.RATED_FUEL_LPH)  # compared with specs, not peers, so single-operator
    rated_cycle = data.RATED_M3_PER_CYCLE                  # machine types are not benchmarked against themselves
    sloped = s.slope_deg >= 5
    out = pd.DataFrame(index=s.index)
    out["safety"] = ((s.seatbelt_status == "Fastened") & (s.speed_vs_limit <= 1) & (s.overload_events == 0)).astype(float)
    out["fuel"] = ((s.idle_ratio <= .20) & (s.fuel_per_work_h <= 1.20 * rated_fuel)).astype(float)
    out["cycle"] = (s.m3_per_cycle >= 0.85 * rated_cycle).astype(float)
    out["handling"] = (s.harsh_events == 0).astype(float)
    terrain_ok = (s.max_tilt_deg <= 15) & (s.tilt_excess_deg <= 7) & (s.speed_vs_limit <= .95)
    out["terrain"] = terrain_ok.astype(float).where(sloped)
    if "expected_min_oof" in s:
        out["execution"] = (s.duration_min <= 1.20 * s.expected_min_oof).astype(float).where(s.expected_min_oof.notna())
    else:
        out["execution"] = np.nan
    return out


def _metric_series(s):
    """Continuous behaviour metrics used for evidence and before/after comparisons."""
    m = pd.DataFrame(index=s.index)
    m["unbuckled"] = (s.seatbelt_status == "Unfastened").astype(float)
    m["idle_ratio"] = s.idle_ratio
    m["m3_per_cycle"] = s.m3_per_cycle
    m["harsh_events"] = s.harsh_events.astype(float)
    m["tilt_excess_deg"] = s.tilt_excess_deg.where(s.slope_deg >= 5)
    m["exec_ratio"] = (s.duration_min / s.expected_min_oof) if "expected_min_oof" in s else np.nan
    return m


def evidence(comp, sess):
    """Plain-language evidence counts for one competency, computed from the given sessions."""
    n = len(sess)
    if comp == "safety":
        return [f"{(sess.seatbelt_status == 'Unfastened').sum()} of {n} sessions with seatbelt unfastened",
                f"{(sess.speed_vs_limit > 1).sum()} sessions above the site speed limit",
                f"{int(sess.overload_events.sum())} overload events"]
    if comp == "fuel":
        return [f"Average idle {sess.idle_ratio.mean():.0%} of session time (standard ≤ 20%)",
                f"{(sess.idle_ratio > .20).sum()} of {n} sessions above 20% idle",
                f"≈{sess.idle_fuel_l.sum():.0f} L burned while idling (at an assumed 3.5 L/h)"]
    if comp == "cycle":
        return [f"Average {sess.m3_per_cycle.mean():.1f} m³ per load cycle = {sess.m3_per_cycle.mean() / data.RATED_M3_PER_CYCLE:.0%} of rated capacity (standard ≥ 85%)",
                f"{(sess.m3_per_cycle < 0.85 * data.RATED_M3_PER_CYCLE).sum()} of {n} sessions below the standard",
                f"{sess.load_cycles.sum()} load cycles over {sess.volume_m3.sum():,.0f} m³"]
    if comp == "handling":
        return [f"{int(sess.harsh_events.sum())} harsh braking/turning events in {n} sessions",
                f"{(sess.harsh_events > 0).sum()} sessions with at least one harsh event"]
    if comp == "terrain":
        sl = sess[sess.slope_deg >= 5]
        return [f"{len(sl)} sessions on slopes ≥ 5°",
                f"{(sl.max_tilt_deg > 15).sum()} with tilt above 15° (rollover warning threshold)",
                f"{(sl.tilt_excess_deg > 7).sum()} with tilt more than 7° above the ground slope",
                f"{(sl.speed_vs_limit > .95).sum()} with speed above 95% of the limit on a slope"]
    if comp == "execution":
        r = (sess.duration_min / sess.expected_min_oof).dropna()
        return [f"Median actual ÷ expected time: {r.median():.2f}" if len(r) else "No expected-time benchmark yet",
                f"{(r > 1.20).sum()} of {len(r)} tasks took more than 120% of the expected time"]
    return []


def _window(s, operator_id, before=None, n=WINDOW, offset=0):
    ops = s[s.operator_id == operator_id].sort_values("timestamp")
    if before is not None:
        ops = ops[ops.timestamp < before]
    end = len(ops) - offset
    return ops.iloc[max(0, end - n):max(0, end)]


def _score(std, idx, comp):
    vals = std.loc[idx, comp].dropna()
    return (100 * vals.mean() if len(vals) >= MIN_SESSIONS else None), len(vals)


def operator_profile(s, std, operator_id):
    """Current competency profile (last WINDOW sessions), previous window, and anonymised site median."""
    cur, prev = _window(s, operator_id), _window(s, operator_id, offset=WINDOW)
    site_scores = {c: [] for c in COMPETENCIES}
    for other in s.operator_id.unique():
        w = _window(s, other)
        for c in COMPETENCIES:
            sc, _ = _score(std, w.index, c)
            if sc is not None:
                site_scores[c].append(sc)
    rows = []
    for c, meta in COMPETENCIES.items():
        score, n = _score(std, cur.index, c)
        prev_score, _ = _score(std, prev.index, c)
        rows.append({"id": c, "competency": meta["name"], "score": score, "n": n, "previous": prev_score,
                     "site_median": float(np.median(site_scores[c])) if site_scores[c] else None,
                     "gap": score is not None and score < GAP_THRESHOLD, "module": meta["module"],
                     "standard": meta["standard"], "evidence": evidence(c, cur)})
    return pd.DataFrame(rows)


def compare_before_after(s, std, operator_id, comp, when):
    """Pre/post comparison around a training completion time, using only observed sessions."""
    ops = s[s.operator_id == operator_id].sort_values("timestamp")
    applicable = std.loc[ops.index, comp].notna()
    ops = ops[applicable]
    pre, post = ops[ops.timestamp < when].tail(PRE_N), ops[ops.timestamp > when].head(POST_N)
    metrics = _metric_series(s)
    key, label, fmt, better = COMPETENCIES[comp]["metric"]
    res = {"competency": COMPETENCIES[comp]["name"], "comp": comp, "n_pre": len(pre), "n_post": len(post),
           "pre_rate": None, "post_rate": None, "p_rate": None, "metric": label,
           "pre_metric": None, "post_metric": None, "p_metric": None, "fmt": fmt}
    if len(pre) >= MIN_SESSIONS:
        pre_pass, post_pass = std.loc[pre.index, comp], std.loc[post.index, comp]
        res["pre_rate"], res["pre_metric"] = 100 * pre_pass.mean(), metrics.loc[pre.index, key].mean()
        if len(post):
            res["post_rate"], res["post_metric"] = 100 * post_pass.mean(), metrics.loc[post.index, key].mean()
        if len(post) >= MIN_SESSIONS:
            table = [[int(post_pass.sum()), int(len(post) - post_pass.sum())],
                     [int(pre_pass.sum()), int(len(pre) - pre_pass.sum())]]
            res["p_rate"] = float(fisher_exact(table, alternative="greater")[1])
            a, b = metrics.loc[post.index, key].dropna(), metrics.loc[pre.index, key].dropna()
            if a.nunique() + b.nunique() > 2:
                alt = "less" if better == "lower" else "greater"
                res["p_metric"] = float(mannwhitneyu(a, b, alternative=alt).pvalue)
    return res


def verdict(res):
    if res["pre_rate"] is None:
        return "insufficient", "Not enough sessions before training to compare"
    if res["n_post"] < MIN_SESSIONS:
        return "monitoring", f"Monitoring: {res['n_post']}/{MIN_SESSIONS} sessions recorded since training"
    improved_rate = res["p_rate"] is not None and res["p_rate"] < ALPHA and res["post_rate"] > res["pre_rate"]
    improved_metric = res["p_metric"] is not None and res["p_metric"] < ALPHA
    if improved_rate or improved_metric:
        return "verified", "Improvement verified from post-training sessions"
    if res["n_post"] >= ADAPT_AFTER:
        return "adapt", "No measurable improvement: escalate to instructor coaching"
    return "monitoring", "Monitoring: no significant change yet"


def training_loops(s, std, operator_id, training_log):
    """Every completed training for this operator with its before/after verification."""
    log = training_log[training_log.operator_id == operator_id]
    loops = []
    for _, t in log.sort_values("time").iterrows():
        mod = t.get("module_id")
        comps = [c for c, m in COMPETENCIES.items() if m["module"] == mod]
        for c in comps:
            res = compare_before_after(s, std, operator_id, c, pd.Timestamp(t["time"]))
            res["verdict"], res["verdict_text"] = verdict(res)
            res["module_id"], res["module"], res["completed"] = mod, t["module"], t["time"]
            loops.append(res)
    return loops


LOOP_STAGES = ["Detected", "Training recommended", "Training completed", "Monitoring", "Verified"]


def loop_stage(row, loops):
    """Where a competency sits in the loop. Returns (stage index, label, adapt flag)."""
    mine = [l for l in loops if l["comp"] == row["id"]]
    if mine:
        last = mine[-1]
        if last["verdict"] == "verified":
            return 4, "Improvement verified", False
        if last["verdict"] == "adapt":
            return 3, "No measurable improvement: escalate to instructor coaching", True
        return 3, last["verdict_text"], False
    if row["gap"]:
        return 1, "Skill gap detected: training recommended", False
    return -1, "Meeting the standard", False


def personal_improvement(s, std, operator_id):
    """Latest WINDOW sessions vs the WINDOW before them, for the operator only (no ranking)."""
    cur, prev = _window(s, operator_id), _window(s, operator_id, offset=WINDOW)
    if len(prev) < MIN_SESSIONS:
        return None

    def stats(w):
        alerts = w.alert_types.str.split(", ").apply(lambda a: len([x for x in a if x]))
        return {"Idle share": w.idle_ratio.mean(), "Safety alerts per session": alerts.mean(),
                "Seatbelt compliance": (w.seatbelt_status == "Fastened").mean(),
                "Harsh events per session": w.harsh_events.mean(),
                "Cycle consistency (variation in m³/cycle)": w.m3_per_cycle.std() / w.m3_per_cycle.mean(),
                "Actual ÷ expected time": (w.duration_min / w.expected_min_oof).median()}

    a, b = stats(prev), stats(cur)
    better_high = {"Seatbelt compliance"}
    rows = []
    for k in a:
        change = b[k] - a[k]
        good = change > 0 if k in better_high else change < 0
        pct = k in ("Idle share", "Seatbelt compliance")
        f = (lambda v: f"{v:.0%}") if pct else (lambda v: f"{v:.2f}")
        rows.append({"measure": k, "previous 30": f(a[k]), "latest 30": f(b[k]),
                     "change": ("▲ better" if good else "▼ worse") if abs(change) > 1e-9 else "no change"})
    return pd.DataFrame(rows)
