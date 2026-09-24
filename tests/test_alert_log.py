"""Live Cab alert log: edge-triggered logging (one entry per inactive → active transition, per condition) and the
Alert log expander keeping its open/closed state across telemetry refreshes. Temporary database; offline.
Run: .venv\\Scripts\\python.exe tests\\test_alert_log.py
"""
import os
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
os.environ["CAT_OPERATOR_DB"] = str(Path(tempfile.mkdtemp()) / "alert_log.db")
os.environ["CAT_OFFLINE"] = "1"
os.environ["ANTHROPIC_API_KEY"] = ""

from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(Path(__file__).resolve().parents[1] / "app.py")
failures = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}{('  ' + detail) if detail and not ok else ''}")
    if not ok:
        failures.append(name)


def new_shift():
    at = AppTest.from_file(APP, default_timeout=300).run()
    at.button[0].click().run()  # Start shift (Ravi, OP1001)
    at.sidebar.radio[0].set_value("🚜 Live Cab").run()
    submit = [b for b in at.button if "Submit inspection" in b.label]
    if submit:  # the pre-start checklist is only asked once per day (recorded in the temp DB)
        for cb in at.checkbox:
            cb.check()
        submit[0].click().run()
    return at


def refresh(at, n):
    for _ in range(n):  # each run = one telemetry tick of the Live Cab panel
        at.run()


def log(at, typ=None):
    return [a for a in at.session_state["live_alerts"] if typ is None or a["type"] == typ]


def toggle(at, name, on):
    at.sidebar.toggle(key=f"demo_{name}").set_value(on).run()


def log_expander(at):
    return next(e for e in at.expander if "Alert log this shift" in e.label)


# 1. one active worker alert across many refreshes → exactly 1 entry
at = new_shift()
check("baseline: no alerts at start", len(log(at)) == 0, str(log(at)))
toggle(at, "person_close", True)
refresh(at, 10)
check("worker held active over 10 refreshes → 1 entry", len(log(at, "Proximity")) == 1 and len(log(at)) == 1, str(log(at)))
check("live warning still shown while active", any("Worker" in m.value for m in at.markdown if "banner" in m.value))

# 3. worker clears and re-enters → exactly 2 worker events
toggle(at, "person_close", False)
refresh(at, 3)
check("cleared condition leaves the active set", "Proximity" not in at.session_state["alert_active"])
toggle(at, "person_close", True)
refresh(at, 5)
check("worker clears and re-enters → 2 worker events", len(log(at, "Proximity")) == 2, str(log(at, "Proximity")))

# 2. one active tilt alert across many refreshes → exactly 1 entry
at = new_shift()
toggle(at, "slope", True)
refresh(at, 10)
check("tilt held active over 10 refreshes → 1 entry", len(log(at, "Tilt")) == 1 and len(log(at)) == 1, str(log(at)))

# 4. worker + tilt simultaneously → exactly 2 events (the old last-entry check alternated and logged every tick)
at = new_shift()
toggle(at, "person_close", True)
toggle(at, "slope", True)
refresh(at, 15)
check("worker + tilt active together → exactly 2 events",
      len(log(at)) == 2 and {a["type"] for a in log(at)} == {"Proximity", "Tilt"}, str([a["type"] for a in log(at)]))

# other live conditions follow the same rule
toggle(at, "unbuckled", True)
toggle(at, "overspeed", True)
refresh(at, 10)
check("seatbelt + overspeed each logged once while held",
      len(log(at, "Seatbelt")) == 1 and len(log(at, "Overspeed")) == 1 and len(log(at)) == 4, str([a["type"] for a in log(at)]))

# 5. expander state persists across reruns
check("alert log starts collapsed", log_expander(at).proto.expanded is False)
refresh(at, 3)
check("closed stays closed across refreshes", log_expander(at).proto.expanded is False)
at.session_state["alert_log_exp"] = True  # what the frontend sends when the operator opens it
at.session_state["alert_log_open"] = True  # on_change callback result (AppTest can't click an expander)
refresh(at, 5)
check("opened log stays open across refreshes", log_expander(at).proto.expanded is True)
toggle(at, "hot", True)  # a new event changes the label count; state must survive that too
refresh(at, 3)
check("stays open when a new event changes the label", log_expander(at).proto.expanded is True
      and len(log(at, "Engine temp")) >= 1)
check("no exceptions", not at.exception, str(at.exception)[:200])

print("ALL PASSED" if not failures else f"FAILED: {failures}")
sys.exit(1 if failures else 0)
