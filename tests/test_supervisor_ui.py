"""End-to-end checks for prototype role selection and the Supervisor Console:
Operator → train → quiz passed → awaiting review → Supervisor → approve / request retraining / recommend instructor
→ Operator sees the result. Temporary database; offline; operator.db untouched.
Run: .venv\\Scripts\\python.exe tests\\test_supervisor_ui.py
"""
import os
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
DB = Path(tempfile.mkdtemp()) / "supervisor_ui.db"
os.environ["CAT_OPERATOR_DB"] = str(DB)
os.environ["CAT_OFFLINE"] = "1"
os.environ["ANTHROPIC_API_KEY"] = ""

from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(Path(__file__).resolve().parents[1] / "app.py")
OPERATOR_PAGES = ["🚜 Live Cab", "📋 My Day", "🦺 Safety Center", "📊 Machine Insights", "⏱️ Task Estimator",
                  "🤖 Ask Assistant", "🧭 My Skill Profile", "🎓 Training Hub"]
SUP_PAGES = ["📊 Dashboard", "📝 Training Reviews", "👷 Operators", "📈 Outcomes", "👨‍🏫 Coaching & Bookings"]
failures = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}{('  ' + detail) if detail and not ok else ''}")
    if not ok:
        failures.append(name)


def text(at):
    return " ".join([m.value for m in at.markdown] + [c.value for c in at.caption] + [i.value for i in at.info]
                    + [s.value for s in at.success] + [w.value for w in at.warning] + [e.value for e in at.error])


def rows(table):
    with sqlite3.connect(DB) as con:
        return con.execute(f"SELECT * FROM {table}").fetchall()


def metric(at, label):
    return next(m.value for m in at.metric if m.label == label)


def btn(at, label):
    return next(b for b in at.button if label in b.label)


def login_operator(at):
    at.button[0].click().run()  # Operator is the default role; Start shift is the first button


def login_supervisor(at):
    at.radio(key="login_role").set_value("Supervisor").run()
    btn(at, "Open Supervisor Console").click().run()


def logout_operator(at):
    at.sidebar.button[0].click().run()  # End shift & report
    btn(at, "Log out").click().run()


def logout_supervisor(at):
    btn(at, "Log out").click().run()


def pass_terrain_quiz(at):
    at.sidebar.radio[0].set_value("🎓 Training Hub").run()
    btn(at, "Safe operation on sloped terrain · 📁 offline").click().run()  # lesson list → terrain
    for r in at.radio:
        if r.key and r.key.startswith("q_terrain_"):
            r.set_value(r.options[1])
    btn(at, "Submit answers").click().run()


def open_first_review(at):
    at.sidebar.radio(key="sup_nav").set_value("📝 Training Reviews").run()
    next(b for b in at.button if b.label == "Review").click().run()


def style(at):
    return " ".join(m.value for m in at.markdown if "--bg:" in m.value)


at = AppTest.from_file(APP, default_timeout=300).run()

# ---- login: prototype role selection
check("operator is the default role", at.radio(key="login_role").value == "Operator")
check("Start shift is the first button for Operator", "Start shift" in at.button[0].label and len(at.button) == 1)
check("RBAC limitation visible on login", "authentication/RBAC not implemented" in text(at))
login_operator(at)
check("operator sidebar = exactly the 8 operator pages", list(at.sidebar.radio[0].options) == OPERATOR_PAGES,
      str(at.sidebar.radio[0].options))
check("no supervisor entry anywhere in the operator sidebar",
      not any("Supervisor" in str(o) for r in at.sidebar.radio for o in r.options) and not any("Supervisor" in b.label for b in at.sidebar.button))

# ---- operator: train → quiz passed → awaiting supervisor review
pass_terrain_quiz(at)
check("quiz passed; training sent for review", any("sent to your supervisor for review" in s.value for s in at.success))
check("Training Hub shows the awaiting-review chip", "1 awaiting supervisor review" in text(at))
at.sidebar.radio[0].set_value("🧭 My Skill Profile").run()
t = text(at)
check("Skill Profile: AWAITING SUPERVISOR REVIEW on the terrain loop", "AWAITING SUPERVISOR REVIEW" in t and "awaiting review" in t)
check("Skill Profile: statistical monitoring caption unchanged (0/8)", "Monitoring: 0/8" in t)
check("Skill Profile: seeded fuel loop still verified", "Improvement verified" in t)
check("training recorded once in training_log", sum(1 for r in rows("training_log") if r[1] == "terrain") == 1)
logout_operator(at)
check("operator logout returns to role selection", at.radio(key="login_role").value == "Operator" and not at.sidebar.radio)

# ---- supervisor console
login_supervisor(at)
check("supervisor sidebar = only supervisor pages", list(at.sidebar.radio(key="sup_nav").options) == SUP_PAGES)
check("supervisor has no operator pages, demo controls or End shift",
      not any(p in str(o) for r in at.sidebar.radio for o in r.options for p in OPERATOR_PAGES)
      and not at.sidebar.toggle and not any("End shift" in b.label for b in at.button))
check("supervisor sidebar shows the RBAC limitation", "authentication/RBAC not implemented" in text(at))
check("dashboard counts: 1 pending, 0 monitoring, 2 verified, 1 coaching",
      (metric(at, "Pending reviews"), metric(at, "Monitoring"), metric(at, "Verified outcomes"), metric(at, "Coaching recommended"))
      == ("1", "0", "2", "1"))
t = text(at)
check("seeded Anita + Ravi verified, Priya escalated on the dashboard",
      "Anita Sharma" in t and "VERIFIED · STATISTICAL" in t and "Priya Nair" in t and "ESCALATED" in t)

open_first_review(at)
t = text(at)
check("review opens Ravi's terrain training", "Review · Ravi Kumar" in t and "Safe operation on sloped terrain" in t)
check("review shows why (Terrain handling 31/100 + evidence)", "Terrain handling" in t and ">31<" in t and "slopes ≥ 5°" in t)
check("review shows completion + quiz passed + score", "✓ Completed" in t and "✓ Passed · 100%" in t)
approve = btn(at, "APPROVE & START MONITORING")
check("decision buttons disabled until an assessment is chosen",
      approve.disabled and btn(at, "REQUEST RETRAINING").disabled and btn(at, "RECOMMEND INSTRUCTOR").disabled)
at.radio(key=next(r.key for r in at.radio if r.key and r.key.startswith("assess_"))).set_value("Approved").run()
check("Approved enables only APPROVE", not btn(at, "APPROVE & START MONITORING").disabled and btn(at, "REQUEST RETRAINING").disabled)
at.text_area(key=next(a.key for a in at.text_area if a.key.startswith("note_"))).set_value("Explained slope technique well").run()
btn(at, "APPROVE & START MONITORING").click().run()
t = text(at)
check("approval message", "Supervisor approved training. Behavioural verification begins after post-training sessions" in t)
check("approved case: SUPERVISOR APPROVED + MONITORING 0/8, not verified",
      "✓ SUPERVISOR APPROVED" in t and "MONITORING 0/8" in t and "VERIFIED · STATISTICAL" not in t)
r = rows("supervisor_reviews")
check("one review row stored (approved, with note)", len(r) == 1 and r[0][3] == "approved" and r[0][5] == "Explained slope technique well")
at.sidebar.radio(key="sup_nav").set_value("📊 Dashboard").run()
check("dashboard after approval: 0 pending, 1 monitoring, verified still 2",
      (metric(at, "Pending reviews"), metric(at, "Monitoring"), metric(at, "Verified outcomes")) == ("0", "1", "2"))
for p in SUP_PAGES:
    at.sidebar.radio(key="sup_nav").set_value(p).run()
check("every supervisor page renders", not at.exception, str(at.exception)[:200])
at.sidebar.radio(key="sup_nav").set_value("📈 Outcomes").run()
t = text(at)
# The seeded loops must show exactly what the existing statistical logic computes on this database (the percentages
# depend on the weekday the DB was generated; the verdicts don't): Ravi fuel + Anita safety verified, Priya fuel escalated.
import analytics as an  # noqa: E402
import data  # noqa: E402
import skills as sk  # noqa: E402
_s = an.enrich(data.read("sessions"), data.read("machines"), data.read("operators"))
_s["expected_min_oof"] = an.train_time_model(_s)["oof"]
_std, _tl = sk.session_standards(_s), data.read("training_log")
expected = {op: next(l for l in sk.training_loops(_s, _std, op, _tl) if l["module_id"] == mod)
            for op, mod in [("OP1001", "fuel"), ("OP1002", "safety"), ("OP1004", "fuel")]}
check("outcomes: seeded verdicts unchanged (verified, verified, escalated)",
      [expected[o]["verdict"] for o in ("OP1001", "OP1002", "OP1004")] == ["verified", "verified", "adapt"])
check("outcomes: console shows exactly the statistical before/after numbers",
      all(f"{l['pre_rate']:.0f}% → {l['post_rate']:.0f}%" in t for l in expected.values())
      and f"{expected['OP1001']['pre_rate']:.0f}% → {expected['OP1001']['post_rate']:.0f}%" == "27% → 80%"
      and "Monitoring: 0/8" in t, str([f"{l['pre_rate']:.0f}→{l['post_rate']:.0f}" for l in expected.values()]))

# ---- dark / light for the supervisor
at.sidebar.radio(key="theme").set_value("Light").run()
check("supervisor light mode", "--bg:#F3F4F6" in style(at) and not at.exception)
at.sidebar.radio(key="theme").set_value("Dark").run()
check("supervisor dark mode", "--bg:#0E1013" in style(at) and not at.exception)
logout_supervisor(at)
check("supervisor logout returns to role selection", at.radio(key="login_role").value == "Operator" and not at.sidebar.radio)

# ---- operator sees Supervisor Approved + Monitoring 0/8 (never Verified)
login_operator(at)
at.sidebar.radio[0].set_value("🧭 My Skill Profile").run()
t = text(at)
check("operator: SUPERVISOR APPROVED + approval message", "✓ SUPERVISOR APPROVED" in t and
      "Supervisor approved training. Behavioural verification begins after post-training sessions are recorded." in t)
check("operator: terrain rail monitoring 0/8, still only 1 verified loop (fuel)",
      "monitoring 0/8" in t and "Monitoring: 0/8" in t and "1 verified" in t and "1 monitoring" in t)
check("no post-training sessions created", len(rows("sessions")) == 1549)

# ---- retraining: a retake is a new case; the supervisor requests retraining
time.sleep(1.2)  # trainings are stamped to the second; a retake is a new case
pass_terrain_quiz(at)
check("retake recorded as a second terrain training", sum(1 for r in rows("training_log") if r[1] == "terrain") == 2)
logout_operator(at)
login_supervisor(at)
check("retake appears as a new pending review", metric(at, "Pending reviews") == "1")
open_first_review(at)
check("review covers the latest attempt", "2 recorded pass(es)" in text(at))
at.radio(key=next(r.key for r in at.radio if r.key and r.key.startswith("assess_"))).set_value("Needs reinforcement").run()
check("Needs reinforcement disables APPROVE", btn(at, "APPROVE & START MONITORING").disabled and not btn(at, "REQUEST RETRAINING").disabled)
btn(at, "REQUEST RETRAINING").click().run()
check("retraining message + chip", "Retraining requested." in text(at) and "RETRAINING REQUESTED" in text(at))
r = rows("supervisor_reviews")
check("append-only: earlier approval kept, retraining added", [x[3] for x in r] == ["approved", "retraining"])
logout_supervisor(at)
login_operator(at)
at.sidebar.radio[0].set_value("🎓 Training Hub").run()
t = text(at)
check("operator: gap stays open, lesson recommended again",
      "1 gap to train" in t and "Recommended now" in t and any("Open lesson: Safe operation on sloped terrain" in b.label for b in at.button))
at.sidebar.radio[0].set_value("🧭 My Skill Profile").run()
t = text(at)
check("operator: retraining shown, score unchanged at 31, Start button back",
      "RETRAINING REQUESTED" in t and "requested retraining" in t and ">31<" in t
      and any("Start: Safe operation on sloped terrain" in b.label for b in at.button))

# ---- instructor recommendation → existing booking
time.sleep(1.2)
pass_terrain_quiz(at)
logout_operator(at)
login_supervisor(at)
open_first_review(at)
at.radio(key=next(r.key for r in at.radio if r.key and r.key.startswith("assess_"))).set_value("Needs reinforcement").run()
btn(at, "RECOMMEND INSTRUCTOR").click().run()
check("instructor recommendation shown with the existing booking form",
      "Instructor coaching recommended" in text(at) and any(b.label == "Book session" for b in at.button))
next(b for b in at.button if b.label == "Book session").click().run()
bk = rows("bookings")
check("booking written to the existing bookings table for OP1001",
      len(bk) == 1 and bk[0][0] == "OP1001" and bk[0][1] == "Safe operation on sloped terrain")
at.sidebar.radio(key="sup_nav").set_value("👨‍🏫 Coaching & Bookings").run()
t = text(at)
check("coaching page: Ravi (supervisor) + Priya (statistical escalation) + booking listed",
      "Source: supervisor recommendation." in t and "Source: statistical verification" in t and "Priya Nair" in t
      and len(at.dataframe) >= 1)
logout_supervisor(at)
login_operator(at)
at.sidebar.radio[0].set_value("🧭 My Skill Profile").run()
check("operator: instructor coaching recommended + booking button",
      "INSTRUCTOR COACHING RECOMMENDED" in text(at) and any("Book instructor coaching" in b.label for b in at.button))
at.sidebar.radio[0].set_value("🎓 Training Hub").run()
check("operator booking tab lists the supervisor's booking", any(len(d.value) == 1 for d in at.dataframe))

# ---- operator dark / light, other pages still fine
at.sidebar.radio(key="theme").set_value("Light").run()
for p in OPERATOR_PAGES:
    at.sidebar.radio[0].set_value(p).run()
check("operator light mode: every page renders", "--bg:#F3F4F6" in style(at) and not at.exception, str(at.exception)[:200])
at.sidebar.radio(key="theme").set_value("Dark").run()
check("operator dark mode", "--bg:#0E1013" in style(at) and not at.exception)
check("no post-training sessions created at any point", len(rows("sessions")) == 1549)

print("ALL PASSED" if not failures else f"FAILED: {failures}")
sys.exit(1 if failures else 0)
