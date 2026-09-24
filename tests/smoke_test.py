"""Smoke test: runs the 3-minute demo story end to end, fully OFFLINE and without an API key, on a temporary
database (the demo database is never touched).
Run: .venv\\Scripts\\python.exe tests\\smoke_test.py
"""
import os
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
os.environ["CAT_OPERATOR_DB"] = str(Path(tempfile.mkdtemp()) / "smoke.db")
os.environ["CAT_OFFLINE"] = "1"          # no internet
os.environ["ANTHROPIC_API_KEY"] = ""     # no Claude key

from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(Path(__file__).resolve().parents[1] / "app.py")
failures = []


def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}{('  ' + detail) if detail and not ok else ''}")
    if not ok:
        failures.append(name)


def texts(at):
    return " ".join([m.value for m in at.markdown] + [c.value for c in at.caption] + [i.value for i in at.info]
                    + [s.value for s in at.success] + [w.value for w in at.warning])


def ask(at, q):
    at.chat_input[0].set_value(q).run()
    return at.chat_message[-1].markdown[0].value if at.chat_message else ""


at = AppTest.from_file(APP, default_timeout=300).run()
at.button[0].click().run()  # 1. log in (OP1001 Ravi)
check("login", not at.exception, str(at.exception))

pages = at.sidebar.radio[0].options
for p in pages:  # every screen renders offline
    at.sidebar.radio[0].set_value(p).run()
    check(f"page {p}", not at.exception, str(at.exception[0].message) if at.exception else "")

at.sidebar.radio[0].set_value("🚜 Live Cab").run()  # 2. pre-start checklist gates the cab
for cb in at.checkbox[:5]:  # incomplete: 5/8
    cb.check()
next(b for b in at.button if "Submit inspection" in b.label).click().run()
check("incomplete checklist keeps machine locked", not any(m.label == "Speed" for m in at.metric)
      and any("LOCKED" in e.value for e in at.error))
at.run()
check("incomplete checklist still locked after rerun", not any(m.label == "Speed" for m in at.metric))
for cb in at.checkbox:  # complete: 8/8
    cb.check()
next(b for b in at.button if "Submit inspection" in b.label).click().run()
check("complete checklist unlocks live cab", any(m.label == "Speed" for m in at.metric))


def prox_banners():
    return [m.value for m in at.markdown if 'class="banner' in m.value and ("STOP:" in m.value or " within " in m.value)]


normal = []
for _ in range(8):  # normal operation: no spontaneous proximity alert across refreshes
    at.run()
    normal += prox_banners()
check("no spontaneous proximity alert (8 refreshes)", not normal, str(normal[:2]))
worker = at.sidebar.toggle(key="demo_person_close")
worker.set_value(True).run()
seen = []
for _ in range(5):
    at.run()
    seen.append(any("STOP: Worker 1.6 m away at 20°" in b for b in prox_banners()))
check("worker approaching persists (5 refreshes)", all(seen), str(seen))
at.sidebar.toggle(key="demo_person_close").set_value(False).run()
cleared = []
for _ in range(5):
    at.run()
    cleared += prox_banners()
check("clearing worker returns to normal", not cleared, str(cleared[:2]))

for t in at.sidebar.toggle:  # 3. safety event: steep slope
    if t.label == "Machine on steep slope":
        t.set_value(True)
at.run()
check("tilt alert explained", "Inclinometer" in texts(at), texts(at)[:200])
check("fatigue indicator is labelled as an indicator", "Fatigue risk indicator" in texts(at))

at.sidebar.radio[0].set_value("🤖 Ask Assistant").run()  # 4. assistant answers from app data, offline
ans = ask(at, "Why am I getting this warning?")
check("assistant explains the live warning", "Tilt" in ans and "15°" in ans, ans[:200])
ans = ask(at, "How long will T005 take?")
check("assistant uses the estimator", "T005" in ans and "min" in ans, ans[:200])
ans = ask(at, "What should I improve?")
check("assistant reads the skill profile", "Terrain handling" in ans, ans[:300])
for q in ["Which training should I take?", "What training should I do?", "What should I learn?",
          "What skill should I improve?"]:
    ans = ask(at, q)
    check(f"training intent: {q}", "Terrain handling" in ans and "condition" not in ans.lower(), ans[:200])
next(b for b in at.button if "Safe operation on sloped terrain" in b.label).click().run()
check("assistant routes to the lesson", at.sidebar.radio[0].value == "🎓 Training Hub")

# 5. targeted training: offline local video + knowledge check
check("local MP4 plays offline", any("terrain.mp4" in c.value for c in at.caption))
for r in at.radio:
    if r.key and r.key.startswith("q_terrain_"):
        r.set_value(r.options[1])
next(b for b in at.button if b.label == "Submit answers").click().run()
check("training quiz passed and logged", any("Passed" in s.value for s in at.success))

at.sidebar.radio[0].set_value("🧭 My Skill Profile").run()  # 6. profile shows the loop moving on
check("profile shows post-training monitoring", "Monitoring: 0/8" in texts(at), texts(at)[:300])
check("profile shows a verified earlier loop", "Improvement verified" in texts(at))
check("new training labelled: not persisted, no improvement claimed",
      "aren't saved in this prototype" in texts(at) and "No improvement is claimed" in texts(at))
check("seeded loop labelled as synthetic history", "Seeded synthetic history" in texts(at))

at.sidebar.button[0].click().run()  # 7. end-of-shift report
report = " ".join(m.value for m in at.markdown)
check("shift report", "End-of-shift report" in report and "Safe operation on sloped terrain" in report)

print("ALL PASSED" if not failures else f"FAILED: {failures}")
sys.exit(1 if failures else 0)
