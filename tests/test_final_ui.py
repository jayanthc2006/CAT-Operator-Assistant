"""Focused end-to-end checks for the final polish pass: logout, natural-language assistant (incl. follow-ups and
offline / Claude-unavailable fallbacks) and the Light/Dark theme. Temporary database; offline; operator.db untouched.
Run: .venv\\Scripts\\python.exe tests\\test_final_ui.py
"""
import os
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
os.environ["CAT_OPERATOR_DB"] = str(Path(tempfile.mkdtemp()) / "final_ui.db")
os.environ["CAT_OFFLINE"] = "1"
os.environ["ANTHROPIC_API_KEY"] = ""

from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(Path(__file__).resolve().parents[1] / "app.py")
failures = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}{('  ' + detail) if detail and not ok else ''}")
    if not ok:
        failures.append(name)


def start(at):
    at.button[0].click().run()  # Start shift (Ravi, OP1001)
    at.sidebar.radio[0].set_value("🚜 Live Cab").run()
    for cb in at.checkbox:
        cb.check()
    next(b for b in at.button if "Submit inspection" in b.label).click().run()


def ask(at, q):
    at.chat_input[0].set_value(q).run()
    return at.chat_message[-1].markdown[0].value


at = AppTest.from_file(APP, default_timeout=300).run()
start(at)
at.sidebar.toggle(key="demo_slope").set_value(True).run()  # steep slope → Tilt alert

# ---- natural-language assistant (offline, no key)
at.sidebar.radio[0].set_value("🤖 Ask Assistant").run()
a = ask(at, "Why is the machine warning me?")
check("NL safety: why warning", "Tilt" in a and "15°" in a, a[:160])
a = ask(at, "What should I do?")
check("follow-up: what should I do (safety actions)", "Lower the bucket" in a, a[:160])
a = ask(at, "What's my current tilt?")
check("NL telemetry: current tilt", "Tilt is" in a and "Simulated reading" in a, a[:160])
a = ask(at, "How long will my next task take?")
check("NL task: next task ETA", "Model estimate" in a and "D0" in a, a[:160])
a = ask(at, "Why is this ETA higher than the planner?")
check("NL task: why vs planner (indicative factors)", "planner" in a and "indicative" in a, a[:200])
a = ask(at, "What looks unusual here?")
check("NL anomaly: status", "flagged" in a and "synthetic labels" in a, a[:160])
a = ask(at, "Why?")
check("follow-up: anomaly why → evidence", "usual" in a and "vs site" in a, a[:200])
a = ask(at, "Why is my terrain score low?")
check("NL skill: terrain why", "Terrain handling" in a and "31%" in a, a[:200])
a = ask(at, "What should I do next?")
check("follow-up: skill next step → lesson", "Safe operation on sloped terrain" in a, a[:200])
a = ask(at, "What training should I take?")
check("NL training: recommendation grounded in gap", "Safe operation on sloped terrain" in a and "Terrain handling" in a, a[:200])
a = ask(at, "What happens after training?")
check("NL loop: after training", "Monitoring" in a and "escalates" in a, a[:200])
a = ask(at, "How long have I been working?")
check("NL shift summary", "h on shift" in a and "not a medical assessment" in a, a[:200])
a = ask(at, "What machine am I using?")
check("NL machine", "EXC001" in a and "simulated" in a, a[:160])
a = ask(at, "What is the capital of France?")
check("offline fallback for out-of-scope questions", "while offline" in a, a[:160])
at2 = AppTest.from_file(APP, default_timeout=300).run()  # fresh session: follow-up without context → clarification
at2.button[0].click().run()
at2.sidebar.radio[0].set_value("🤖 Ask Assistant").run()
a = ask(at2, "Why?")
check("ambiguous follow-up asks for clarification", "Do you mean" in a, a[:160])

# ---- Claude unavailable (key set, endpoint unreachable) → deterministic offline answer
os.environ["ANTHROPIC_API_KEY"] = "sk-test-invalid"
os.environ["ANTHROPIC_BASE_URL"] = "http://127.0.0.1:9"
a = ask(at, "What should I improve?")
check("Claude-unavailable fallback returns local answer", "Terrain handling" in a and "offline answer" in a, a[:220])
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ.pop("ANTHROPIC_BASE_URL")

# ---- Light / Dark theme
style = lambda: " ".join(m.value for m in at.markdown if "--bg:" in m.value)
check("dark is the default", "--bg:#0E1013" in style())
at.sidebar.radio(key="theme").set_value("Light").run()
check("light theme switches tokens", "--bg:#F3F4F6" in style())
for p in ["📋 My Day", "🦺 Safety Center", "🧭 My Skill Profile", "⏱️ Task Estimator"]:
    at.sidebar.radio[0].set_value(p).run()
check("theme persists across navigation", "--bg:#F3F4F6" in style() and not at.exception)
at.sidebar.radio(key="theme").set_value("Dark").run()
check("back to dark", "--bg:#0E1013" in style())

# ---- End shift → Log out → Login → Start shift again
at.sidebar.radio(key="theme").set_value("Light").run()
at.sidebar.button[0].click().run()
check("end shift shows report", any("End-of-shift report" in m.value for m in at.markdown))
at.run()  # a rerun must NOT lose the report (the old bug lost the Log out click)
check("report persists across rerun", any("End-of-shift report" in m.value for m in at.markdown))
next(b for b in at.button if "Log out" in b.label).click().run()
check("logout returns to login", any("Start shift" in b.label for b in at.button) and not at.sidebar.radio)
check("theme kept after logout", "--bg:#F3F4F6" in style())
at.button[0].click().run()
check("Ravi can start a shift again", at.sidebar.radio[0].value == "🚜 Live Cab" and not at.exception, str(at.exception)[:120])

print("ALL PASSED" if not failures else f"FAILED: {failures}")
sys.exit(1 if failures else 0)
