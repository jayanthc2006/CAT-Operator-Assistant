# Caterpillar Hackathon workspace

## Problem statement: Smart Operator Assistant for CAT machinery
Build an intelligent operator companion with: daily task dashboard; safety features (seatbelt compliance,
proximity hazards, incident logging, working conditions); operator training hub; unusual machine-usage
detection (excessive idling, unsafe operation); task time estimation from past data + environmental conditions.

Organiser rules: synthetic data allowed (any columns, assume the machine collects everything, clean data);
deliver standalone operator software; judged on completeness, technical depth and novelty.
Organisers' sample columns: Timestamp, Machine ID, Operator ID, Engine Hours, Fuel Used (L), Load Cycles,
Idling Time (min), Seatbelt Status, Safety Alert Triggered.
Organisers' task-time sample: Task ID, Task Type (Earth Excavation, Trenching, Material Loading, Grading, Demolition),
Weather (Sunny, Rainy, Cloudy, Windy), Operator Skill (Beginner/Intermediate/Expert), Machine Age (yrs),
Estimated Time (min), Actual Time (min). Presenters asked how we help operators get trained; sample videos welcome.
Training videos: official Cat® Products YouTube embeds (IDs in app.py LESSONS; verified embeddable), plus local .mp4 in `training_videos/`.

## Closed-loop upgrade (freeze before the hackathon)
- `skills.py`: competencies (share of sessions meeting written standards), gaps (<70), before/after verification
  (Fisher exact + Mann-Whitney), loop stages, personal improvement. Named leaderboard removed.
- Task model: temporal split, `operator_pace_hist` feature (earlier days only), out-of-fold expected times,
  substitution explanations. Honest metric ≈ 50% MAE reduction vs planner (40–55% across seeds). The old 72% claim is retired.
- Generator: hidden traits (not in DB), unobserved noise/delays, seeded training history, `injected_event` label (validation only).
- Offline lesson `training_videos/terrain.mp4` (tools/make_offline_lesson.py). `CAT_OFFLINE=1` forces offline mode.
- Tests: `tests/smoke_test.py` (temp DB, offline, no key) + `python -m unittest tests.test_logic`.

## Current build
- `app.py`: Streamlit UI. Login → sidebar pages: Live Cab (pre-start checklist gate, 2 s live telemetry fragment,
  proximity radar, seatbelt interlock), My Day, Safety Center, Machine Insights, Task Estimator, Training Hub,
  My Skill Profile, Ask Assistant; End-shift report. Demo toggles in the sidebar simulate sensor events.
- `data.py`: synthetic data generator + SQLite (`operator.db`, auto-created on first run; delete it to regenerate).
  `sessions` table = organisers' 9 columns + extended signals. `synthetic_machine_data.csv` = export.
- `analytics.py`: task-time model (HistGradientBoosting), explainable anomalies (IsolationForest on robust z-scores),
  anomaly evidence + detector validation, condition warnings, fatigue risk indicator, milestones.
- `Start Operator Assistant.bat`: standalone launcher (Edge `--app` window). `.streamlit/config.toml`: CAT theme.
- `tests/smoke_test.py`: opens every page via Streamlit AppTest. Run after changes.
- `PITCH.md`: requirement coverage, novelty, demo script.
- Assistant uses Claude (`claude-opus-5`) when ANTHROPIC_API_KEY is in `.env`, otherwise offline rule-based answers.

Packages are pre-installed. Don't reinstall; add only packages that are missing.
The internet connection is slow (~80 kB/s), so avoid large packages (PyTorch, TensorFlow) unless essential.

## Python (backend, data, ML)
- Virtual env: `.venv` (Python 3.11). Run with `.venv\Scripts\python.exe`, or activate first with `.venv\Scripts\Activate.ps1`
- Installed and verified: numpy, pandas, scikit-learn, matplotlib, plotly, fastapi, uvicorn,
  anthropic, python-dotenv, requests, openpyxl
- Streamlit and seaborn: check with `.venv\Scripts\pip.exe list` (they were still installing at setup time)
- Not installed: xgboost, opencv (too large for this connection), jupyter, sqlalchemy, pytest.
  For gradient boosting, use scikit-learn's `HistGradientBoostingClassifier` instead of xgboost.
- `wheels/` holds downloaded package files; install offline with `pip install --find-links wheels <pkg>`
- Quick dashboard: `.venv\Scripts\streamlit.exe run app.py`
- API: `.venv\Scripts\uvicorn.exe main:app --reload`

## Web frontend
- `web/`: Vite + React + TypeScript, with recharts and axios installed
- Run with: `cd web; npm run dev`

## Tools on this machine
Python 3.11, Node 25 / npm 11, git, VS Code. There's no Docker.

## Notes
- Put API keys in `.env` (never commit it). Load them with python-dotenv.
- Likely Caterpillar themes: predictive maintenance on equipment sensor data, fleet telematics,
  fuel efficiency, safety and computer vision, dashboards. Keep a demo-able UI (Streamlit is quickest).
