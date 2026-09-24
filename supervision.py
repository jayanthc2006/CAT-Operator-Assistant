"""Supervisor review layer: a human checkpoint between TRAIN and VERIFY.

Supervisor approval means "the operator completed the assigned training and a supervisor reviewed and approved it".
It is NOT statistical verification: Verified / Monitoring / Escalate still come only from skills.verdict (via
skills.training_loops). Nothing here creates sessions, changes scores or produces a Verified result.

A review case is the operator's latest passed training for a module that maps to a competency. Trainings recorded
on or before the last historical session are seeded history and are exempt from review (they pre-date this layer).
Decisions are append-only; the latest decision for the case's training decides its state. A retake is a new training,
so it starts a new case awaiting review while older decisions stay in the table.
"""
import pandas as pd

import skills as sk

REVIEWABLE_MODULES = sorted({m["module"] for m in sk.COMPETENCIES.values() if m["module"]})
DECISIONS = ("approved", "retraining", "instructor")
GROUP_ORDER = ["awaiting", "retraining", "coaching", "monitoring", "verified", "escalated"]
GROUP_LABEL = {"awaiting": "Awaiting review", "retraining": "Retraining requested", "coaching": "Instructor coaching recommended",
               "monitoring": "Monitoring", "verified": "Verified", "escalated": "Escalated"}


def competencies_for(module_id):
    return [c for c, m in sk.COMPETENCIES.items() if m["module"] == module_id]


def training_cases(training_log, hist_end):
    """One case per (operator, reviewable module): the latest passed training (retakes supersede older attempts)."""
    tl = training_log[training_log.module_id.isin(REVIEWABLE_MODULES)]
    cases = []
    for (op, mod), g in tl.groupby(["operator_id", "module_id"], sort=True):
        g = g.sort_values("time", kind="stable")
        last = g.iloc[-1]
        cases.append({"operator_id": op, "module_id": mod, "module": last["module"], "training_time": last["time"],
                      "score": float(last["score"]), "attempts": int(g["time"].nunique()),
                      "exempt": pd.Timestamp(last["time"]) <= pd.Timestamp(hist_end)})
    return cases


def review_state(case, reviews):
    """('exempt' | 'awaiting' | 'approved' | 'retraining' | 'instructor', latest review row or None)."""
    if case["exempt"]:
        return "exempt", None
    r = reviews[(reviews.operator_id == case["operator_id"]) & (reviews.module_id == case["module_id"])
                & (reviews.training_time == case["training_time"])]
    if not len(r):
        return "awaiting", None
    last = r.sort_values("time", kind="stable").iloc[-1]
    return last["decision"], last.to_dict()


def case_group(state, loops):
    """Overview group. Verified and Escalated come ONLY from the existing statistical verdicts in `loops`
    (skills.training_loops); supervisor approval by itself can only ever lead to Monitoring."""
    if state in ("awaiting", "retraining"):
        return state
    if state == "instructor":
        return "coaching"
    verdicts = [l["verdict"] for l in loops]
    if verdicts and all(v == "verified" for v in verdicts):
        return "verified"
    if any(v == "adapt" for v in verdicts):
        return "escalated"
    return "monitoring"


def post_sessions(loops):
    """Post-training sessions recorded so far (the smallest count across the module's competencies)."""
    return min((l["n_post"] for l in loops), default=0)
