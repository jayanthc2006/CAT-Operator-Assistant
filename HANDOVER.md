# CAT Operator Assistant: Developer Handover & Technical Documentation

> **Source of truth.** This document was rebuilt on **24 Sep 2026** from a fresh audit of the current code
> (`app.py` 1,801 lines, `data.py` 378, `analytics.py` 259, `skills.py` 243, 4 test files, launcher, config) and the current
> `operator.db`. Every metric below was **recomputed from the current code and database during this audit** unless it is
> explicitly marked *previously documented* or *Needs verification*. The previous `HANDOVER.md` was used only as a checklist
> of topics; where it and the code disagreed, the code won.
>
> **Update 24 Sep 2026 (later the same day): prototype roles + Supervisor Console.** Login now offers a prototype role
> selection (Operator / Supervisor), and a supervisor review checkpoint sits between TRAIN and VERIFY (§5.1, §5.13, §9,
> §14.1). `skills.py` and `analytics.py` are unchanged; all headline metrics below are unchanged. Test counts in §19 were
> re-run after this change.

**Status markers used throughout**

| Marker | Meaning |
|---|---|
| ✅ Working | Implemented and exercised in this audit (automated test and/or browser run) |
| ⚠️ Partial | Implemented, but with a real functional gap described next to it |
| 🟡 Simulated / prototype | Works, but its input is simulated, synthetic or seeded, or it only exists in the app UI |
| ❌ Not implemented | Not in the code (may be mentioned as future work only) |
| 🔍 Needs verification | Could not be verified in this environment |

**How the numbers were obtained (this audit)**
- Database statistics: read-only copy of `operator.db` (SHA-1 at audit time `c96b0191…`).
- Model and detector metrics: `analytics.train_time_model` / `detect_anomalies` / `evaluate_detector` run on that copy.
- Robustness: the generator was re-run in memory with seeds 11–15 (no database written).
- Tests: all four suites run on temporary databases (see §19 for exact counts).
- UI: every page opened by the Streamlit AppTest suites; Live Cab alert logging and the alert-log expander were also
  checked in a real browser on a temporary database earlier on 24 Sep.

---

## Project in one paragraph

**CAT Operator Assistant** is a standalone, offline-first operator application (Python + Streamlit + SQLite) for CAT
machine operators. It combines a live cab screen (pre-start inspection gate, simulated real-time telemetry, safety alerts,
360° proximity radar, fatigue risk indicator), a daily task dashboard with machine-learning task-time estimates, a safety
centre with incident logging, machine-usage insights with an explainable Isolation Forest anomaly detector, a task-time
estimator, and a **closed-loop training system**: it scores each operator against written competency standards from their
own recorded sessions, recommends a matched lesson when a score falls below 70, records the lesson and quiz, and then
compares sessions before and after training with Fisher exact and Mann–Whitney U tests to mark the improvement as
*verified* or *escalate to coaching*. A natural-language assistant answers operator questions from the app's own data,
works fully offline, and can optionally use Claude only to rephrase those facts. **All history is synthetic, live
telemetry is simulated, and past training effects are seeded;** the logic that processes them (models, rules, statistics,
UI) is real and tested.

---

## 1. Project overview

### 1.1 What it is
A single-machine operator HMI ("human–machine interface") that runs in a browser window (launched as an Edge `--app`
window) on the operator's laptop/tablet. There is no server-side backend beyond the local Streamlit process.

### 1.2 Target user
The **machine operator** in the cab (primary). Secondary readers of its outputs: a site supervisor or trainer (end-of-shift
report, incident log, training record). A prototype **Supervisor** role (chosen at login, no authentication) reviews completed
trainings in the Supervisor Console (§5.13); there is **no notification mechanism**.

### 1.3 Problem being solved
The hackathon problem statement ("Smart Operator Assistant for CAT machinery") asks for: a daily task dashboard; safety
features (seatbelt compliance, proximity hazards, incident logging, working conditions); an operator training hub;
unusual machine-usage detection (excessive idling, unsafe operation); and task-time estimation from past data plus
environmental conditions. The organisers allow synthetic data and want standalone operator software.

The underlying operator problem: telematics shows operators *what happened* (idle %, alerts) but rarely turns it into
**specific training**, and rarely checks **whether the training changed behaviour**.

### 1.4 Main objectives
1. Keep the operator safe *now* (live alerts with the reason and the action).
2. Plan the day with honest task-time estimates (model vs planner, with typical error).
3. Surface unusual machine usage with evidence, not just a score.
4. Close the loop: detect a skill gap → train → verify from later sessions → adapt.
5. Work offline; be honest about what is simulated.

### 1.5 Core workflow (operator's day)
```
Login (pick operator) → Live Cab: pre-start inspection (8/8 mandatory) → Live Cab unlocks
   → watch live alerts / radar / telemetry (simulated, every 2 s)
   → My Day: start / complete tasks with model ETAs
   → Safety Center: conditions, history, log an incident
   → Machine Insights / Task Estimator (evidence and what-ifs)
   → My Skill Profile / Training Hub: gap → lesson → quiz → loop status
   → Ask Assistant at any time
   → End shift → report (download) → Back to shift or Log out
```

### 1.6 Major features (all present in the current code)
Login · pre-start checklist gate · Live Cab (simulated telemetry, 5 live alert types, proximity radar, edge-triggered alert
log, fatigue risk indicator, idle micro-lessons) · My Day · Safety Center (incident logging) · Machine Insights
(idle cost, Isolation Forest anomalies with evidence and synthetic-label validation, maintenance estimate) · Task Estimator
(HistGradientBoosting vs planner, what-if grid, CSV upload) · Training Hub (5 lessons incl. an offline MP4, quizzes,
scenario simulator, instructor booking, training record, certificate) · My Skill Profile (6 competencies, closed-loop
status, personal improvement, milestones) · Ask Assistant (offline intent router + optional Claude phrasing) ·
End-of-shift report + logout · Light/Dark display theme · **prototype role selection (Operator / Supervisor)** ·
**Supervisor Console** (training reviews, monitoring/verified/escalated outcomes, coaching and instructor booking).

### 1.7 What makes it different
- **Closed loop with verification**: training is not the end state; a statistical before/after check decides *Verified*
  vs *Monitoring* vs *Escalate to coaching*. A training that did not work (Priya, fuel) is shown as escalated, not hidden.
- **Evidence everywhere**: every alert has a "Why:" line with the sensor value and threshold; every flagged session has an
  operator-baseline vs site-baseline table; every competency score has evidence counts and a written standard.
- **Honest ML**: temporal split, leakage-safe operator-pace feature, out-of-fold benchmarks, bootstrap CI, planner and
  task-type-median baselines, and multi-seed robustness; the retired "72%" claim is documented as an artefact.
- **Offline-first**: everything except YouTube lessons and optional Claude phrasing runs with no network.

### 1.8 Genuinely implemented vs simulated vs missing (summary)
| Genuinely implemented (real code, tested) | Simulated / synthetic / seeded | Missing (not implemented) |
|---|---|---|
| Alert rules and thresholds, edge-triggered logging, checklist gate (in the app), incident/checklist/training/booking persistence, task start/complete, task-time model + evaluation, anomaly detector + evidence + validation, competency scoring, statistical verification, loop stages, assistant router, report, theme, logout | Live telemetry (`data.live_reading`), all 1,549 historical sessions, the three seeded training outcomes, service history, today's task list, incidents #1–2, demo toggles | Real CAT telemetry / CAN bus, physical machine interlock, supervisor notification, persistence of live sessions, model retraining from new data, user authentication, multi-machine/fleet backend, medical fatigue detection |

---

## 2. Problem-statement mapping

| Challenge requirement | Current implementation | Status | Evidence (code) |
|---|---|---|---|
| Daily task dashboard | My Day: next task hero card, ETA (model) vs planner, Start/Mark complete, upcoming list, timeline, overlap warning, "why this estimate" | ✅ (⚠️ task list is dated the day the DB was created, see §23) | `page_day`, `todays_tasks`, `data.update_task` |
| Seatbelt compliance | Live: red banner + "simulated interlock" signal; history: 30-day compliance, weekly trend, Safety-discipline competency, "Buckle Champion" milestone | ✅ logic · 🟡 sensor simulated | `live_panel`, `page_safety`, `skills.session_standards`, `an.badges` |
| Proximity hazards | Live: radar, <3 m red STOP / <6 m amber; history: closest-approach scatter, proximity alert counts | ✅ logic · 🟡 sensor simulated | `live_panel`, `data.live_reading`, `page_safety` |
| Incident logging | Safety Center form → `incidents` table, table view | ✅ (no notification) | `page_safety` → `data.append("incidents")` |
| Working conditions | Manual sidebar inputs → heat / slippery / wind / visibility / slope / shift-length rules; fatigue risk indicator | ✅ rules · 🟡 inputs manual / demo sliders | `an.condition_warnings`, `an.fatigue_risk_indicator` |
| Operator training hub | 5 lessons (1 offline MP4, 4 Cat® YouTube), key points, 3-question quiz (pass ≥ 66%), certificate, scenario simulator, instructor booking, training record | ✅ | `page_training`, `LESSONS`, `data.log_training` |
| Personalised training (organisers asked "how do you help operators get trained") | Closed loop: competency gap (<70) → matched lesson → before/after verification → verified / monitoring / escalate | ✅ logic · 🟡 past effects seeded; new trainings cannot be verified (live sessions not persisted) | `skills.py`, `render_loop`, `loop_rail` |
| Unusual usage: excessive idling | Idle % vs 20% standard, idle fuel/cost/CO₂, fleet idle bar chart, Isolation Forest flags with evidence | ✅ (historical data) | `page_insights`, `an.detect_anomalies`, `an.explain_anomaly` |
| Unusual usage: unsafe operation | Live alerts; 30-day unsafe-pattern counts vs fleet average; detector features include speed vs limit, tilt, engine temp | ✅ · ⚠️ detector recall on speed events is only 13.6% | `page_insights`, `an.evaluate_detector` |
| Task-time estimation (past data + environment) | HistGradientBoostingRegressor on 10 pre-task features incl. weather, temp, slope, soil, operator past pace; MAE 12.27 vs planner 24.31 min on held-out synthetic data | ✅ (synthetic evaluation) | `an.train_time_model`, `page_estimator` |
| Organisers' sample schemas | `sessions` keeps all 9 telemetry columns and all 7 task columns verbatim; CSV exports in organisers' format; CSV upload in organisers' task format | ✅ | `data.TELEMETRY_SCHEMA`, `data.TASK_SCHEMA`, `export_csvs`, estimator "Estimate a task list" tab |
| Standalone operator software | Local Streamlit + SQLite, `.bat` launcher opening an Edge app window, offline mode | ✅ · 🔍 launcher window must be checked on the presentation laptop | `Start Operator Assistant.bat` |
| Sample training videos (organisers welcomed them) | Offline 42 s MP4 `training_videos/terrain.mp4` + official Cat® YouTube embeds | ✅ (YouTube needs internet) | `LESSONS`, `local_video`, `online` |
| Extra: pre-start inspection | 8 mandatory checks gate the Live Cab (app-level lock only) | ✅ · 🟡 not a machine lock | `page_live`, `checklist_done_today` |
| Extra: operator assistant | Natural-language, follow-up-aware, offline intent router; optional Claude phrasing | ✅ offline · 🔍 Claude path not exercised with a real key | `route`, `ask_claude` |
| Extra: supervisor review of training | Prototype Supervisor role: review a completed training (Approve / Request retraining / Recommend instructor), then follow Monitoring → statistical verification; approval is never verification | ✅ · 🟡 no authentication (prototype role selection) | `supervision.py`, supervisor section of `app.py`, `supervisor_reviews` table |
| Extra: end-of-shift report | Markdown report (tasks, alerts, conditions, fatigue, machine, skills, training) with download, logout | ✅ | end-of-shift block in `app.py` |
| Extra: maintenance estimate | Engine hours to next 500 h service (seeded service history) | 🟡 | `machine_hours` |

---

## 3. System architecture

### 3.1 Actual architecture (as implemented)

```
                         ┌──────────────────────────────── DATA SOURCES ───────────────────────────────┐
                         │ data._sessions(seed=11)      data._todays_tasks(seed=5)   data.live_reading()│
                         │ synthetic history, 1,549     today's 28 tasks             simulated sensors, │
                         │ sessions (generated ONCE)    (generated ONCE)             every 2 s, in RAM  │
                         │ sidebar: weather/temp/visibility/ground (manual) · demo toggles/sliders       │
                         └───────────────┬──────────────────────────────┬─────────────────┬─────────────┘
                                         ↓ init_db() (first run only)   │                 │
                         ┌─────────────────────────────┐                │                 │
                         │ SQLite  operator.db          │←── writes: checklists, tasks, incidents,
                         │ machines · operators ·       │           training_log, bookings (UI actions)
                         │ sessions · tasks · incidents │                │                 │
                         │ checklists · training_log ·  │                │                 │
                         │ bookings                     │                │                 │
                         └───────────────┬──────────────┘                │                 │
                                         ↓ boot()  (@st.cache_resource: once per server process)
                         ┌────────────────────────────────────────────┐   │                 │
                         │ FEATURE ENGINEERING  analytics.enrich()     │   │                 │
                         │ idle_ratio, fuel_per_work_h, cycles_per_h,  │   │                 │
                         │ m3_per_cycle, speed_vs_limit, tilt_excess,  │   │                 │
                         │ idle_fuel_l, pace_ratio, operator_pace_hist │   │                 │
                         └──────┬──────────────────┬──────────────────┘   │                 │
                                ↓                  ↓                      │                 │
          ┌─────────────────────────────┐ ┌──────────────────────────┐    │                 │
          │ ML 1: task-time model        │ │ ML 2: anomaly detector   │    │                 │
          │ HistGradientBoosting         │ │ IsolationForest (5%) on  │    │                 │
          │ temporal eval + OOF + refit  │ │ robust z-scores per type │    │                 │
          └──────┬──────────────────────┘ └──────────┬───────────────┘    │                 │
                 ↓ expected_min_oof                   ↓ is_anomaly/reason  │                 │
          ┌──────────────────────────────────────────────────────────┐    │                 │
          │ COMPETENCY ENGINE  skills.session_standards()             │    │                 │
          │ 6 written standards → 1/0/NaN per session → score (% met) │    │                 │
          └──────┬───────────────────────────────────────────────────┘    │                 │
                 ↓ (every rerun, reads training_log)                       ↓                 ↓
          ┌──────────────────────────────┐          ┌──────────────────────────────────────────────┐
          │ CLOSED LOOP  skills.py        │          │ RULE ENGINES (deterministic)                 │
          │ gap<70 → module → verify      │          │ live alert rules (live_panel) · condition    │
          │ (Fisher + Mann–Whitney) →     │          │ warnings · fatigue indicator · checklist gate│
          │ verified / monitoring / adapt │          │ · badges · service estimate                  │
          └──────┬───────────────────────┘          └──────────────────┬───────────────────────────┘
                 └────────────────────┬─────────────────────────────────┘
                                      ↓
          ┌──────────────────────────────────────────────────────────────────────────────────────┐
          │ ASSISTANT  route(): keyword/regex intent router + follow-up context → answer builders │
          │ (a_safety, a_task, a_anomaly, a_skill, a_training, a_loop, …) → facts + action buttons │
          │ optional: ask_claude() rephrases the retrieved facts (never decides)                   │
          └──────────────────────────────────────┬───────────────────────────────────────────────┘
                                                 ↓
          ┌──────────────────────────────────────────────────────────────────────────────────────┐
          │ STREAMLIT UI (app.py)  Login · Live Cab · My Day · Safety Center · Machine Insights · │
          │ Task Estimator · Ask Assistant · My Skill Profile · Training Hub · End-of-shift report│
          │ session_state: operator, alerts, live reading, chat, theme, navigation …              │
          └──────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Components

| Layer | Implementation | Notes |
|---|---|---|
| Frontend | Streamlit 1.64 (`app.py`), Plotly 7.1 charts, custom CSS design system | Single script; pages are functions chosen by a sidebar radio |
| "Backend" | The same Streamlit Python process | No API server. `fastapi`/`uvicorn` are installed but **unused**; there is no `main.py` |
| Database | SQLite file `operator.db` via `sqlite3` + pandas (`data.py`) | Path from `CAT_OPERATOR_DB` env var (tests use temp files) |
| ML layer | scikit-learn 1.9.1: `HistGradientBoostingRegressor`, `IsolationForest`, `GroupKFold`, `permutation_importance` | Trained in memory at startup; not persisted |
| Statistics | SciPy 1.17.1: `fisher_exact`, `mannwhitneyu` | Used only in `skills.compare_before_after` |
| Rule engines | `live_panel` alert rules, `an.condition_warnings`, `an.fatigue_risk_indicator`, checklist gate, `an.badges` | Deterministic, thresholds in code |
| Training system | `skills.py` (scoring, loops) + `page_training` (lessons, quizzes, simulator, booking) | |
| Supervisor review layer | `supervision.py` (pure review-state logic) + supervisor section of `app.py` + `supervisor_reviews` table | Human checkpoint between TRAIN and VERIFY; never produces a statistical verdict |
| Assistant | `route()` + answer builders in `app.py` (section 8); optional `ask_claude()` (Anthropic SDK 1.8.0) | Offline by default; `.env` key enables phrasing |
| External services | YouTube (4 lesson embeds), Anthropic API (optional) | Both optional; app degrades gracefully |
| Local/offline assets | `operator.db`, `training_videos/terrain.mp4`, all models, all rules | |

### 3.3 Control flow (one Streamlit run)
1. `load_dotenv()`, page config, theme tokens (`st.session_state.theme`, default Dark) → CSS.
2. `boot()` (cached per server process): `init_db()` → read tables → `enrich` → `train_time_model` → attach OOF/test
   predictions → `detect_anomalies` → `session_standards`. **About 30 s on the audit laptop** (measured 31.7 s while other
   tests were running), then instant for later reruns and sessions until the server restarts.
3. If no `operator_id` in session → login screen → `st.stop()`.
4. Apply `pending_nav` (page + optional lesson) **before** drawing the navigation radio.
5. Sidebar: operator card, navigation, site conditions, demo controls, Display theme, End shift button.
6. `condition_warnings` computed from sidebar inputs.
7. If `show_report` → render end-of-shift report → `st.stop()`.
8. Dispatch to the selected page function. Live Cab's `live_panel` is an `@st.fragment(run_every=2)` that re-runs on its
   own every 2 s without re-running the whole page.

### 3.4 Session state (per browser session, never persisted)

| Key | Set by | Used for |
|---|---|---|
| `operator_id`, `shift_start` | Start shift | identity, assistant "shift" answer |
| `live_alerts` | Live Cab (edge-triggered) | alert log, fatigue indicator (+4 per alert), report, assistant |
| `alert_active` | Live Cab | set of condition types currently active (for edge-triggered logging) |
| `active_alerts`, `last_reading`, `tick`, `idle_ticks` | Live Cab | Safety Center "last reading", assistant, radar, micro-lesson |
| `alert_log_open` / `alert_log_exp` | Alert-log expander | keeps the expander open/closed across 2 s refreshes |
| `nav`, `pending_nav`, `lesson` | sidebar / buttons | navigation and lesson selection |
| `chat`, `chat_actions`, `asst_ctx` | Ask Assistant | conversation, action buttons, follow-up topic/task/competency |
| `score_<lesson>`, `q_<lesson>_<i>`, `sc<i>` | Training Hub | quiz and scenario answers |
| `theme` | Display radio | Dark/Light (kept on logout) |
| `show_report` | End shift | keeps the report open across reruns |
| `demo_*` | Demo controls | simulator toggles, shift sliders |

### 3.5 Model lifecycle
```
server start → boot() trains on ALL rows of sessions table (in memory) → cached until the Streamlit process restarts
new UI actions (tasks, incidents, training, checklists) → written to SQLite → NOT fed back into the models
live telemetry → never written anywhere → never enters training
```
There is **no retraining, no model file, no versioning**. Deleting `operator.db` and restarting regenerates identical
synthetic data (fixed seeds) relative to the new "today", and retrains.

---

## 4. File / folder structure

| File / folder | Purpose | Important functions / contents | Used by | Status |
|---|---|---|---|---|
| `app.py` | The whole Streamlit UI, rule engines for live alerts, assistant | `boot`, `page_live`, `live_panel`, `sensor_states`, `page_day`, `page_safety`, `page_insights`, `page_estimator`, `organiser_task_features`, `page_training`, `render_loop`, `loop_rail`, `page_profile`, `route` + `a_*` builders, `ask_claude`, `page_assistant`, `logout`, `navigate`, design helpers (`page_header`, `chip`, `status_chip`, `card`, `section`, `state_panel`, `hmi_chart`) | launcher, tests | ✅ critical |
| `data.py` | Synthetic generator, SQLite access, live simulator | `_sessions`, `_todays_tasks`, `init_db`, `export_csvs`, `read`, `append`, `update_task`, `log_training`, `live_reading`, `planner_estimate_min`, `true_duration_min`, constants (`MACHINES`, `OPERATORS`, `SPEED_LIMIT`, `TRAINING_MODULES`, hidden `_TRAITS`) | app, analytics, skills, tests | ✅ critical |
| `analytics.py` | ML + rule engines | `enrich`, `operator_pace_history`, `current_pace`, `train_time_model`, `predict_minutes`, `explain_prediction`, `detect_anomalies`, `explain_anomaly`, `evaluate_detector`, `condition_warnings`, `fatigue_risk_indicator`, `badges` | app, skills, tests | ✅ critical |
| `supervision.py` | Supervisor review layer (pure logic, no UI) | `REVIEWABLE_MODULES`, `training_cases`, `review_state`, `case_group`, `post_sessions` | app, tests | ✅ new |
| `skills.py` | Competencies and closed-loop training | `COMPETENCIES`, `session_standards`, `evidence`, `operator_profile`, `compare_before_after`, `verdict`, `training_loops`, `loop_stage`, `personal_improvement` | app, tests | ✅ critical |
| `operator.db` | Live SQLite database (auto-created) | 8 tables (§9) | app | ✅ runtime state; currently contains rehearsal rows |
| `operator - Copy.db` | Manual backup copy (23 Sep 15:43) | — | nothing | Legacy; safe to delete |
| `synthetic_machine_data.csv` | Export of `sessions` in organisers' telemetry format + extra columns (no `injected_event`) | 1,549 rows | humans/judges only | ✅ matches the DB |
| `synthetic_task_data.csv` | Export in organisers' task format + context columns | 1,549 rows | humans/judges only | ✅ matches the DB |
| `Start Operator Assistant.bat` | Launcher: starts Streamlit on 8501 (minimised window), waits for `/_stcore/health`, opens Edge `--app` window (explicit Edge paths; falls back to default browser) | — | operator | ✅ · 🔍 window opening to be checked on the demo laptop |
| `.streamlit/config.toml` | Dark base theme (CAT yellow primary), headless, `runOnSave = true`, minimal toolbar, no usage stats | — | Streamlit | ✅ |
| `.env.example` | Template: `ANTHROPIC_API_KEY=` | — | developer | ✅ (no `.env` exists now) |
| `requirements.txt` | Full `pip freeze` pin list (Streamlit 1.64.0, scikit-learn 1.9.1, SciPy 1.17.1, pandas 3.0.6, Plotly 7.1.0, anthropic 1.8.0 …) | — | install | ⚠️ includes unused fastapi/uvicorn; lacks `imageio-ffmpeg` (tool only) |
| `tests/test_logic.py` | 26 unit tests (standards, verification, loops, ML leakage, detector, simulator, fatigue, MP4, planner) | `unittest` | developer | ✅ |
| `tests/smoke_test.py` | 32-check end-to-end demo story via Streamlit AppTest | — | developer | ✅ |
| `tests/test_final_ui.py` | 25 checks: assistant NL + follow-ups + fallbacks, Light/Dark, logout/re-login | — | developer | ✅ |
| `tests/test_alert_log.py` | 13 checks: edge-triggered alert logging, alert-log expander persistence | — | developer | ✅ |
| `tests/test_supervision.py` | 13 unit tests: review-state logic, seeded outcomes unchanged, additive migration | `unittest` | developer | ✅ new |
| `tests/test_supervisor_ui.py` | 51 end-to-end checks: role selection, review → approve / retrain / instructor, booking, Dark/Light for both roles | AppTest | developer | ✅ new |
| `presentation/` | Hackathon deck sources (`deck/`), speaker copy sheet (`PRESENTATION_NOTES.md`), app screenshots (`screens/`) | — | team | ✅ |
| `tools/make_offline_lesson.py` | Builds `terrain.mp4` with matplotlib frames + ffmpeg | — | build-time only | ⚠️ needs `imageio-ffmpeg`, which is **not installed** in `.venv` |
| `training_videos/terrain.mp4` | Offline 42.0 s lesson (1280×720, 12 fps) | — | Training Hub | ✅ (its title card still says "2-minute") |
| `training_videos/README.txt` | Says extra MP4s appear under "Site videos (offline)" | — | — | ⚠️ stale: that section does not exist; only `<lesson id>.mp4` files are used |
| `PITCH.md` | Pitch, requirement coverage, metrics, demo script | — | team | ✅ metrics match this audit |
| `CLAUDE.md` | Workspace notes for AI assistants | — | AI tools | ⚠️ mentions `main.py`/uvicorn API and `web/` frontend that are not part of the product |
| `HANDOVER.md` | This document | — | team | ✅ |
| `web/` | Default Vite + React + TS template (hero image, counter) with recharts/axios installed | — | nothing | Unused scaffold |
| `.venv/` | Python 3.11.9 virtual env (points to `.python311/`) | — | runtime | ✅ required |
| `.python311/` | Portable Python 3.11.9 interpreter used by `.venv` | — | runtime | ✅ required |
| `.venv.broken/` | Old broken virtual env (~807 MB) | — | nothing | Legacy; safe to delete |
| `wheels/` | Downloaded wheels (~72 MB) for offline reinstall | — | reinstall only | Optional |
| `__pycache__/` | Bytecode | — | Python | Generated |

---

## 5. Feature-by-feature documentation

### 5.1 Login (prototype role selection)
- **Purpose:** choose the role, then who is operating; starts a browser-session "shift".
- **Role:** a **Select role** radio (`login_role`): **Operator** (default) or **Supervisor**, with the visible notice
  "Prototype role selection — authentication/RBAC not implemented". Supervisor → **🧑‍💼 Open Supervisor Console**
  (§5.13). The operator never sees supervisor pages in the operator sidebar; anyone can still pick either role at login.
- **User flow (Operator):** pick an operator from the dropdown (`OP1001 · Ravi Kumar` … `OP1006 · Lakshmi Iyer`); the assigned
  machine is shown; press **🔑 Start shift** (still the first and only button while Operator is selected).
- **Data used:** `operators`, `machines` tables.
- **Processing:** sets `operator_id`, `shift_start`, empties `live_alerts`, `alert_active`, `chat`.
- **Output:** the app with the sidebar; lands on Live Cab (first radio item).
- **Database changes:** none.
- **Status:** ✅ Working. **Limitations:** no password or authentication (anyone can pick any operator); one operator per
  browser session; shift start time is not stored in the database.

### 5.2 Sidebar (always visible after login)
- Brand, operator card (name, ID, skill label from experience, machine, model, type, age).
- **Navigation** (one radio; group labels OPERATION / INTELLIGENCE / DEVELOPMENT drawn with CSS):
  🚜 Live Cab · 📋 My Day · 🦺 Safety Center | 📊 Machine Insights · ⏱️ Task Estimator · 🤖 Ask Assistant |
  🧭 My Skill Profile · 🎓 Training Hub.
- **Site conditions (manual input):** Weather (Sunny default, Cloudy, Rainy, Windy, Foggy, Dusty), Temperature slider
  5–50 °C (default 34), Visibility (Poor/Moderate/Good, default Good), Ground (Firm default, Soft / muddy, Slope > 15°,
  Uneven / rocky).
- **🎬 Demo controls (expander):** Hours on shift (0–12, default 3.5), Hours since last break (0–8, default 1.5),
  toggles: Seatbelt unfastened, Worker approaching, Parked & idling, Machine on steep slope, Overspeed, Engine overheating.
- **Display:** Dark / Light radio.
- **🏁 End shift & report** button.
- **Status:** ✅. Weather/temperature feed the task-time model, the condition rules and the fatigue indicator in real time.

### 5.3 Pre-start checklist (part of Live Cab)
- **Purpose:** daily walkaround inspection before operating.
- **User flow:** on Live Cab, tick the 8 checks (Tracks/tyres & undercarriage; No hydraulic or fuel leaks; Engine oil,
  coolant & hydraulic levels; Lights, beacon & horn; Mirrors & rear camera; Backup alarm; Fire extinguisher; Seatbelt &
  ROPS undamaged), optional defects text, **✅ Submit inspection & unlock machine**.
- **Processing:** every submit writes a `checklists` row (`items_ok` = number ticked, `issues` = unticked items + text).
  `checklist_done_today()` unlocks only if a row **for this operator, dated today, with items_ok ≥ 8** exists.
- **Output:** incomplete → red error "Machine remains LOCKED in the operator app … supervisor notification isn't connected";
  complete → Live Cab telemetry appears; header chip changes from `🔒 LOCKED · PRE-START REQUIRED` to `✓ PRE-START PASSED`.
- **Database:** `checklists` (append on every submit).
- **Status:** ✅ Working (tested 5/8 stays locked, still locked after rerun, 8/8 unlocks). 🟡 The lock is **only in the app
  UI**; there is no machine integration. Unlock is per operator per calendar day.

### 5.4 Live Cab (`page_live`, `live_panel`)
- **Purpose:** the in-cab safety screen.
- **User flow:** after the checklist, watch the screen; demo toggles simulate events; press lesson / break buttons.
- **Data used:** `data.live_reading` (simulated), today's tasks + model ETA, sidebar conditions, demo sliders.
- **Processing (every 2 s, fragment):** new reading → 5 alert rules (§6) → edge-triggered logging → state level
  (CRITICAL if any red, CAUTION if any amber, else NORMAL) → idle micro-lesson rule.
- **Output, top to bottom:**
  1. Header with `◌ SIMULATED TELEMETRY` chip and pre-start chip.
  2. **Current task hero card** (in-progress task, else next pending): task, site, **ETA (model)** vs planner, start time,
     volume/soil/slope, site note, site-condition level and chips.
  3. **State panel** NORMAL/CAUTION/CRITICAL with chips for Seatbelt, Proximity, Tilt, Speed, Engine coolant and
     `simulated reading #N · time`.
  4. **Alert banners** (red first) each followed by "Why: …" (sensor value vs threshold).
  5. Tilt active → button **🎓 Terrain awareness · 42 sec lesson: Safe operation on sloped terrain** (jumps to Training Hub).
  6. Parked & idling for ≥ 4 s at 0 km/h → "💤 Parked & idling…" info with a rotating safety micro-tip.
  7. Three columns: **Proximity radar · 360°** (3/6/15 m rings, objects coloured by distance) | **Critical telemetry**
     (Speed, Tilt, Engine temp, Engine rpm + Load, Fuel rate, Seatbelt, State) | **Nearest object** and **Fatigue risk
     indicator** (level chip, score/100, progress bar, "What is this based on?" popover with the factor table).
  8. Expanders: "Alert thresholds used by this screen"; "📜 Alert log this shift (N), recorded automatically" (stays
     open/closed across refreshes).
  9. After the panel: "Site condition details (n)" expander; **☕ Log a break** (resets the *demo* "hours since break" slider).
- **Database:** none (alerts and readings stay in session state).
- **Status:** ✅ logic · 🟡 telemetry simulated. **Limitations:** readings are not persisted; "interlock" is a UI message;
  the fatigue indicator's shift hours come from demo sliders, not real time.

### 5.5 My Day (`page_day`)
- **Purpose:** daily task dashboard.
- **User flow:** read the next task, press **▶️ Start task**, later **✅ Mark complete**; open "Why this estimate?".
- **Data used:** `tasks` rows for this operator, model predictions under current sidebar weather/temperature, operator's
  recent pace (`an.current_pace`, Ravi = 1.13× planner), machine hours.
- **Processing:** model ETA per task (`an.predict_minutes`), estimated finish = scheduled start + ETA, overlap count,
  difference vs planner total, substitution explanation (`an.explain_prediction`).
- **Output:** header "Hello, {first name}" with task-done and service chips; KPIs (Tasks today, Planned work h (AI estimate),
  Service estimate h, Site warnings); service warning if < 60 h (Ravi's EXC001: 38 h → shown); next-task hero card with
  status/priority chips, ETA vs planner with ± typical error; progress bar; site note; "Why this estimate?" table;
  Upcoming list; info "the AI expects today's work to take X min longer/less" when the gap > 15 min; overlap warning;
  Gantt timeline with a "now" line; "Full schedule table" expander.
- **Database:** `tasks.status`, `started_at`, `completed_at` via `data.update_task`.
- **Status:** ✅ Working. **Limitations:** ⚠️ `todays_tasks()` does not filter by date: the list is whatever
  `_todays_tasks()` generated on the day the DB was created (currently **23 Sep** tasks shown on 24 Sep, with D001 and D002
  already Done from rehearsals). Completing a task does not create a `sessions` row, so it never feeds the models.

### 5.6 Safety Center (`page_safety`)
- **Purpose:** one place for machine status, site conditions, history and incidents.
- **Data used:** `last_reading` from the Live Cab session state, sidebar conditions, last-30-day sessions, `incidents`.
- **Processing:** sensor states (same thresholds as Live Cab), condition rules, overall level = worst of both.
- **Output:** state panel; "Machine sensors · last simulated reading HH:MM:SS" card (or "No live reading yet"); "Site
  conditions" card with the rule for each row; **What to do now** (from `SAFETY_ACTIONS`) for any non-OK sensor; Site
  guidance messages; KPIs: Seatbelt compliance (30d), Sessions with alerts, Proximity alerts, Safety discipline /100;
  tabs: 📈 Trends (weekly seatbelt %, alerts by type per week), 📡 Proximity history (closest approach per session, red
  < 3 m band), 📝 Incident log (form + table, newest first).
- **Database:** `incidents` append (type, severity, location prefix in description). Description must be non-empty.
- **Status:** ✅. **Limitations:** the sensor card shows the *last* reading taken while Live Cab was open (it does not stream
  on this page); "Supervisor notification isn't connected in this prototype" is shown after logging.

### 5.7 Machine Insights (`page_insights`)
- **Purpose:** idling cost and unusual machine usage.
- **Output:** chips `78 sessions flagged` and `detector recall 80% on synthetic labels`; KPIs (My idle time 30d vs 20%
  standard, Fuel burned idling, Estimated idling cost ₹ at ₹95/L, Estimated CO₂ from idling at 2.68 kg/L); fleet idle bar
  chart (red > 20%); daily idle % area chart; "🧠 AI-detected unusual machine behaviour" with scope radio (My machine /
  Whole fleet), anomaly-score scatter, "Inspect a flagged session" select → evidence card (title, evidence table vs
  operator and site baselines, context, recommendation); validation expander; "⚠️ Unusual operation patterns (30 days)"
  (me vs fleet average for seatbelt, proximity < 3 m, tilt > 15°, overspeed, overload, harsh events); 🔧 Maintenance
  progress "Service estimate · N engine hours remaining".
- **Database:** read-only.
- **Status:** ✅ on historical synthetic data. Anomalies are **not** computed live and are not persisted.

### 5.8 Task Estimator (`page_estimator`)
- **Purpose:** estimate a task and show how the model was evaluated.
- **Output:** chips `MAE 12.3 vs 24.3 min`, `synthetic evaluation`; KPIs Model MAE 12.3 min (16% of task time), Planner
  MAE 24.3 min (29%), MAE reduction 49.5% (95% CI 43.5% to 54.9%), Tasks within ±10% 42% (planner 15%); tabs:
  - **🔮 Predict a task:** task type, weather, skill, machine age, volume, "Site & operating context" expander (machine type,
    soil, slope, temperature, *use my past pace* checkbox) → Model estimate (± typical error), Planner's standard estimate,
    **Estimated finish if started now**, contributing-factors table, what-if heat-map (weather × skill), global permutation
    importance chart.
  - **📈 How we evaluated it:** method bullets, estimate-vs-actual scatter on the test set, error histogram, sample rows in
    the organisers' format with the model prediction.
  - **📂 Estimate a task list:** CSV upload in the organisers' task format (default: organisers' 5-row example + template
    download) → adds "🤖 Model Predicted (min)".
- **Status:** ✅ (synthetic evaluation). **Limitation:** uploaded lists lack soil/slope/volume, so defaults are assumed
  (gravel, 3°, volume back-calculated from the planner estimate) and pace is missing; the page says it is an illustration.

### 5.9 Training Hub (`page_training`)
- **Purpose:** targeted training + the closed loop.
- **Output:** header chips (`N gap(s) to train`, `N monitoring`, `N verified`, `N escalated`); loop legend rail;
  **Recommended now** hero card (WHY / WHAT / HOW LONG / NEXT) with **▶️ Open lesson** for the first untrained gap
  (Ravi → Safe operation on sloped terrain, 42 sec); "🔁 Your closed-loop training plan" (a loop card per gap or trained
  competency); tabs:
  - **🎥 Lessons:** list (✅ done / ▶️; `📁 offline` marker), player (local MP4 if present, else YouTube if online, else a
    warning), key takeaways, 3-question **knowledge check** (pass ≥ 66% = 2 of 3) → training logged → success message,
    **📜 Download certificate** (HTML), "🧭 See my updated skill profile".
  - **🕹️ Scenario simulator:** 5 situational questions with instant feedback; score; **Save result** logs module
    `simulator` with the score.
  - **👨‍🏫 Book an instructor:** topic, instructor, date (≥ today), slot → `bookings`.
  - **📜 My training record:** progress x/5 lessons + table.
- **Database:** `training_log` (quiz pass; simulator save), `bookings`.
- **Status:** ✅. **Limitations:** quiz can be retaken and logged again (each log creates another loop entry); simulator
  results do not map to a competency; booking does not notify anyone.

### 5.10 My Skill Profile (`page_profile`)
- **Output:** header with loop chips; loop legend; **🔁 Closed-loop status** cards for every gap or trained competency;
  "Supporting evidence · competency profile" radar (you vs anonymous site median) and per-competency bars with trend vs
  previous 30; "All competencies: standards and evidence" expander; **📈 Personal improvement** (latest 30 vs previous 30
  sessions: idle share, alerts/session, seatbelt compliance, harsh events, cycle consistency, actual ÷ expected time);
  **🎖️ Milestones** (sensor-based badges; Ravi currently has none).
- **Database:** read-only.
- **Status:** ✅.

### 5.11 Ask Assistant (`page_assistant`) — see §16 for internals
- Quick buttons: "Why am I getting this warning?", "How long will my next task take?", "What should I improve?", "Teach me
  about slopes"; chat input; action buttons under the answer that navigate (e.g. to a lesson).
- Chips: `works offline`, and `Claude phrasing on` (key present) or `Claude off (optional)`.
- **Status:** ✅ offline · 🔍 Claude phrasing not exercised with a real key in this audit.

### 5.12 End-of-shift report and logout
- **User flow:** **🏁 End shift & report** → report page (stays open across reruns) → **⬇️ Download report** (Markdown),
  **↩ Back to shift**, or **🔒 Log out**.
- **Content:** date, machine, shift length (demo slider value), tasks completed x/y and each task's status, live alerts this
  shift (last 10), conditions, fatigue indicator, engine hours / next service, 30-day idle share, competency scores with
  gaps, training completed today and every loop's verdict.
- **Logout:** clears the browser session state (not the database), keeps the theme, returns to Login.
- **Database:** none. **Status:** ✅ (tested: report persists across rerun, logout → login → new shift works).
  **Limitation:** "Shift length" is the demo slider, not the real login duration.

### 5.13 Supervisor Console (Supervisor role)
- **Purpose:** a human checkpoint between TRAIN and VERIFY, plus an overview of every operator's training outcomes.
- **Isolation:** runs right after login and stops (`st.stop()`); no operator setup, demo controls, site conditions, Live Cab
  or End shift. Sidebar: role card with the RBAC notice, 5 pages, Display theme, **🔒 Log out**.
- **Pages:**
  - **📊 Dashboard:** counts (Pending reviews · Monitoring · Verified outcomes · Coaching recommended) and cases grouped as
    Awaiting review / Retraining requested / Instructor coaching recommended / Monitoring (`MONITORING n/8`) / Verified / Escalated.
  - **📝 Training Reviews:** pending cases with **Review**; the review panel shows the operator, why training was assigned
    (competency score, written standard, evidence), the training (lesson, ✓ completed, ✓ quiz passed + score, date, attempts),
    the statistical status, the assessment "Did the operator demonstrate understanding of the training?" (Approved / Needs
    reinforcement) with an optional note, and **APPROVE & START MONITORING** (enabled only for Approved), **REQUEST
    RETRAINING** and **RECOMMEND INSTRUCTOR** (enabled only for Needs reinforcement); plus the append-only review history.
  - **👷 Operators:** all 6 operators × 6 competency scores (gaps marked) and each operator's training status.
  - **📈 Outcomes:** Monitoring, Verified and Escalated loops with the existing loop rail and before/after numbers.
  - **👨‍🏫 Coaching & Bookings:** supervisor instructor recommendations **and** statistical escalations (e.g. Priya), each
    with the existing booking form for that operator, plus all bookings.
- **Database:** `supervisor_reviews` (append-only); bookings go to the existing `bookings` table via the shared `booking_form`.
- **Status:** ✅ Working (51 end-to-end checks + browser walkthrough). 🟡 No authentication.

### 5.14 Light / Dark display theme
- Sidebar **Display** radio; Dark is the default; session-only; kept across navigation and logout.
- Implemented with CSS tokens + Light-mode overrides of Streamlit widgets + `hmi_chart` (Plotly `plotly_white` /
  `plotly_dark`, transparent backgrounds). `.streamlit/config.toml` stays dark.
- **Status:** ✅. **Limitation:** Streamlit data tables (`st.dataframe`) keep a dark grid in Light mode (readable).

---

## 6. Safety system

### 6.1 Live alerts (Live Cab, every 2 s, from the simulated reading)

| Alert | Input | Threshold / rule | Severity | UI response | Logged where | Real or simulated |
|---|---|---|---|---|---|---|
| Seatbelt | `seatbelt` (bool) | open while engine runs (`not r["seatbelt"]`) | 🔴 red | "🪢 SEATBELT UNFASTENED: buckle up now. Travel/hydraulics lock signal raised (simulated interlock)" + Why | session `live_alerts` (once per onset) | 🟡 sensor simulated; "interlock" is a UI message only |
| Proximity STOP | nearest object distance | `< 3 m` | 🔴 red | "🛑 STOP: {kind} {d} m away at {bearing}°. Check before moving" | same | 🟡 |
| Proximity caution | nearest object distance | `3 ≤ d < 6 m` | 🟠 amber | "⚠️ {kind} within {d} m at {bearing}°" | same (shares the "Proximity" condition with STOP) | 🟡 |
| Tilt / rollover | `tilt_deg` | `> 15°` | 🔴 red | "⛰️ ROLLOVER RISK: tilt X°. Lower the bucket and move to level ground" + lesson button | same | 🟡 |
| Overspeed | `speed_kmh` | `> SPEED_LIMIT[type]`: Excavator 6, Wheel Loader 25, Dozer 10, Articulated Truck 40, Motor Grader 30 km/h | 🟠 amber | "🏎️ Overspeed: X km/h (site limit L)" | same | 🟡 |
| Engine temperature | `engine_temp_c` | `> 98 °C` | 🟠 amber | "🌡️ Engine temperature X°C. Reduce load and let it idle to cool" | same | 🟡 |

- **Overall state:** CRITICAL if any red alert, CAUTION if only amber, NORMAL otherwise (site conditions are shown in the task
  card, not in this level).
- **Edge-triggered logging (new):** `st.session_state.alert_active` holds the condition types active on the previous tick.
  A condition is appended to `live_alerts` only on its inactive → active transition; while it stays active, the banner keeps
  showing but nothing is re-logged; when it clears it can log again. Each type is tracked independently (worker + tilt →
  exactly 2 entries). Proximity amber and red count as one condition type. The engine-overheating demo reading is
  N(101, 1.5) °C, so about 2% of ticks dip below 98 °C; such a dip clears the condition and the next rise is logged as a new
  event (correct edge behaviour, but it can add an extra entry).
- **Actions:** `SAFETY_ACTIONS` gives the operator instruction per type (Safety Center "What to do now", assistant).
- **No overload alert live**: overload exists only in historical sessions (`overload_events`).

### 6.2 Pre-start checklist
8 mandatory items; unlock requires a checklist row today with `items_ok ≥ 8`; every submit is logged in `checklists`.
App-level lock only.

### 6.3 Site-condition rules (`an.condition_warnings`, from manual sidebar inputs)

| Rule | Condition | Level |
|---|---|---|
| Extreme heat | temperature ≥ 40 °C | error (critical) |
| High heat | 35 ≤ temperature < 40 °C | warning |
| Slippery ground | weather Rainy **or** ground "Soft / muddy" | warning |
| High wind | weather Windy | warning |
| Low visibility | weather Foggy/Dusty **or** visibility Poor | warning |
| Steep slope | ground "Slope > 15°" | error |
| Long shift | hours on shift ≥ 10 (demo slider) | error |
| Shift getting long | 8 ≤ hours on shift < 10 | warning |

Output: chips in the Live Cab task card, "Site condition details" expander, Safety Center "Site guidance" and conditions card,
assistant "Is it safe to work today?". Nothing is logged.

### 6.4 Fatigue risk indicator (`an.fatigue_risk_indicator`) — operational, **not medical**
Score = min(100, sum of):
- time on shift: `min(40, max(0, h − 6) × 10)` (demo slider "Hours on shift")
- time since break: `min(36, max(0, h − 2) × 12)` (demo slider; ☕ Log a break resets it to 0)
- heat: `min(16, max(0, T − 32) × 2)` (sidebar temperature)
- safety alerts this shift: `min(20, 4 × len(live_alerts))`

Level: High ≥ 60, Elevated ≥ 30, else Low. Defaults (3.5 h, 1.5 h, 34 °C, 0 alerts) → **4/100 Low**. Shown in Live Cab
(with the factor table), report, assistant. Not logged. No biometric or camera input exists.

### 6.5 Historical safety signals (synthetic sessions)
`seatbelt_status`, `min_proximity_m`, `proximity_alerts`, `max_speed_kmh`, `max_tilt_deg`, `overload_events`,
`harsh_events`, `alert_types`, `safety_alert_triggered` (Yes if any of Seatbelt / Proximity < 3 m / Tilt > 15° / Overspeed /
Overload). Used by Safety Center trends, Machine Insights patterns, the Safety-discipline and Terrain competencies, badges.

### 6.6 Incident logging
Safety Center form: type (Near miss, Equipment damage, Injury, Unsafe condition, Environmental, Other), severity (Low,
Medium, High, Critical), location (5 sites), description (required) → `incidents` row with `[location]` prefix. Stored locally
only; no notification.

### 6.7 Other safety-related items
- **Heat, shift duration, breaks, weather, visibility, ground:** covered by §6.3 and §6.4 (manual inputs / demo sliders).
- **Idle micro-lessons:** only when parked, idling and at 0 km/h for ≥ 4 s (never while moving).
- **Tilt → lesson link:** red tilt alert shows a button to the 42 s terrain lesson.

---

## 7. Live telemetry

| Aspect | Current implementation |
|---|---|
| Source | `data.live_reading(machine_type, tick, rng, demo)`, **simulated**. No CAN bus, J1939, VisionLink or other telematics connection exists. |
| Update interval | `@st.fragment(run_every=2)`: every 2 s while Live Cab is open (plus on any full rerun of that page) |
| Randomness | `np.random.default_rng(tick)`; `tick` is a per-session counter, so the sequence is deterministic per session |
| Fields | `seatbelt`, `speed_kmh`, `tilt_deg`, `engine_rpm`, `engine_temp_c`, `fuel_rate_lph`, `load_pct`, `idling`, `objects` [(bearing°, distance m, kind)] |
| Normal behaviour | working 80% of ticks; speed U(2, 0.8 × limit); tilt abs(N(4, 1.5)); engine temp N(92, 1.5); 2–4 background objects at ≥ 7 m (`NORMAL_OBJECT_MIN_M`), so **no spontaneous alerts** |
| Demo controls | Seatbelt unfastened → belt open; Worker approaching → fixed worker at 1.6 m, 20°; Parked & idling → not working (0 km/h, ~850 rpm, 3.5 L/h); Steep slope → +17° tilt; Overspeed → 1.3 × limit; Engine overheating → +9 °C |
| Persistence | **None.** Readings live only in session state (`last_reading`); alerts in `live_alerts` for the browser session |
| Real-time alerts? | Yes, in the sense that they are evaluated on each simulated reading every 2 s |
| Real-time anomaly detection? | **No.** The Isolation Forest runs once at startup on historical sessions only |
| For real CAT telemetry | Replace `live_reading` with an adapter (e.g. J1939/CAN gateway or a telematics API) returning the same dict; persist readings and roll them up into `sessions` rows at task end; keep the alert thresholds; add a watchdog for stale/missing data; validate sensor semantics (tilt axis, proximity sensor type) with CAT engineering |

---

## 8. Dataset / data generation

### 8.1 Current database facts (computed during this audit)

| Item | Value |
|---|---|
| Sessions | **1,549** (OP1001 250, OP1002 264, OP1003 270, OP1004 256, OP1005 249, OP1006 260) |
| Date range | 2026-07-10 07:24 → 2026-09-22 18:36 (75 calendar days before DB creation, Sundays skipped → **64 working days**) |
| Operators / machines | 6 / 6 (one machine each) |
| Task types (sessions) | Grading 393, Earth Excavation 386, Material Loading 260, Haulage 256, Trenching 128, Demolition 126 |
| Weather (days) | Sunny 34, Cloudy 11, Rainy 6, Windy 6, Foggy 5, Dusty 2 (probabilities .40/.20/.15/.12/.07/.06) |
| Weather (sessions) | Sunny 830, Cloudy 261, Windy 147, Rainy 143, Foggy 121, Dusty 47 |
| Sessions with a safety alert | 36.9% · alert types: Proximity 265, Tilt 133, Seatbelt 123, Overspeed 104, Overload 56 |
| Seatbelt unfastened | 7.9% of sessions |
| Anomaly labels (`injected_event`) | idle 27, idle+fuel 33 (= 60 idle/fuel), speed 66, none 1,423 |
| Today's tasks (`tasks`) | 28 tasks D001–D028, **dated 2026-09-23** (DB creation day), 4–5 per operator; D001 and D002 Done (rehearsal) |
| Incidents | 4: 2 seeded (12 and 5 days before creation), 2 rehearsal entries by OP1001 (23 Sep 16:15, 24 Sep 00:55) |
| Checklists | 9 rehearsal rows (OP1001 and OP1003; mix of incomplete and 8/8) |
| Training log | 3 seeded rows (OP1001 fuel 14 Aug, OP1002 safety 24 Aug, OP1004 fuel 29 Aug) |
| Bookings | 0 |
| Seeds | sessions 11, today's tasks 5; model/detector/bootstrap/permutation `random_state` 0 |

### 8.2 Machines and operators
| Machine | Type | Model | Age (yrs) | Operator | Experience → skill |
|---|---|---|---|---|---|
| EXC001 | Excavator | CAT 320 | 2 | OP1001 Ravi Kumar | 12 yrs → Expert |
| LDR001 | Wheel Loader | CAT 950 GC | 3 | OP1002 Anita Sharma | 3 → Intermediate |
| DOZ001 | Dozer | CAT D6 | 6 | OP1003 Mohammed Irfan | 7 → Intermediate |
| TRK001 | Articulated Truck | CAT 745 | 5 | OP1004 Priya Nair | 1 → Beginner |
| EXC002 | Excavator | CAT 336 | 4 | OP1005 Suresh Patel | 18 → Expert |
| GRD001 | Motor Grader | CAT 140 | 1 | OP1006 Lakshmi Iyer | 5 → Intermediate |

Skill: < 3 yrs Beginner, < 10 Intermediate, else Expert. Service remaining (500 h interval, seeded "hours since service"):
DOZ001 12 h, EXC001 38 h, LDR001 170 h, TRK001 250 h, EXC002 320 h, GRD001 405 h.

### 8.3 How a session is generated (`data._sessions`)
Per working day: one weather draw, base temperature N(31, 5), one daily **site disruption** factor lognormal(0, 0.06).
Per operator: 3–5 tasks from their machine type's task list, random site (slope from site mean + N(0, 2)), soil
(Sand/Clay/Gravel/Rock .30/.30/.25/.15), volume U(30, 150) m³, temperature rising through the day.
- **Duration** = `true_duration_min` (standard rate × soil × weather × skill × (1 + 0.03·age + 0.02·max(0, T−35) + 0.012·slope))
  × hidden operator pace × hidden machine condition × daily disruption × lognormal(0, 0.10) noise, plus a 15–60 min delay
  with probability 5%.
- **Planner estimate** (`planner_estimate_min`) = volume ÷ rate × 60 × soil factor × (Rainy 1.15, Foggy 1.10), rounded to
  5 min. It ignores skill, machine age, temperature, slope, operator pace and machine condition by design (like a planning
  sheet).
- **Behaviour** from hidden traits (`_TRAITS`, never stored): seatbelt probability, idle share, slope care, smoothness, bucket
  fill, speeding probability. Idle, fuel, cycles, tilt, speed, harsh events and engine temperature follow from these.
- **Injected anomalies** (validation labels): 4% of sessions get idle 45–70% ("idle"); half of those also fuel × 1.3–1.6
  ("idle+fuel"); speeding sessions (trait probability) are labelled "speed".
- **Seeded training history** (`_TRAINING_HISTORY`): after the training date, Ravi's idle trait drops 0.24 → 0.12 (fuel),
  Anita's belt 0.70 → 0.98 and speeding 0.07 → 0.02 (safety), Priya's fuel training has **no** effect. These effects are
  *generated*; the verification that detects them only uses the recorded sessions.

### 8.4 Column usage

| Column(s) | Role |
|---|---|
| `timestamp`, `machine_id`, `operator_id`, `engine_hours`, `fuel_used_l`, `load_cycles`, `idling_time_min`, `seatbelt_status`, `safety_alert_triggered` | Organisers' 9 telemetry columns (all kept) |
| `task_id`, `task_type`, `weather`, `operator_skill`, `machine_age_yrs`, `estimated_time_min`, `duration_min` | Organisers' 7 task columns (all kept) |
| `task_type`, `weather`, `operator_skill`, `machine_age_yrs`, `soil`, `temp_c`, `slope_deg`, `volume_m3` (+ `machine_type` from `machines`, + derived `operator_pace_hist`) | **Task-time model inputs** |
| `duration_min` | **Target** |
| `estimated_time_min` | Planner baseline (and source of the pace ratio of *earlier* days) |
| `idling_time_min`, `fuel_used_l`, `load_cycles`, `max_speed_kmh`, `max_tilt_deg`, `engine_temp_c` | **Anomaly detector inputs** (via derived ratios) |
| `seatbelt_status`, `overload_events`, `harsh_events`, `max_tilt_deg`, `slope_deg`, `max_speed_kmh`, `volume_m3`, `load_cycles` | **Competency standards** |
| `min_proximity_m`, `proximity_alerts`, `alert_types`, `safety_alert_triggered`, `site`, `engine_hours` | Display / history charts / service estimate |
| `injected_event` | **Validation only** (detector recall); never a model input; excluded from the CSV exports |
| `visibility_m`, `hours_into_shift` | **Unused** by any logic |

---

## 9. Database documentation

**Engine:** SQLite file. **Path:** `data.DB_PATH = $CAT_OPERATOR_DB` or `<project>/operator.db`. **Access:** `data.read(table)`
(full-table `SELECT *` into pandas), `data.append(table, row)`, `data.update_task(task_id, **fields)`, `data.log_training`.
There are no primary keys, foreign keys or indexes (tables are created by `pandas.to_sql`).

| Table | Columns (type) | Purpose | Written by | Read by |
|---|---|---|---|---|
| `machines` (6) | machine_id TEXT, machine_type TEXT, model TEXT, machine_age_yrs INTEGER, engine_hours_start REAL, last_service_hours REAL | fleet master data | `init_db` | `boot`, service estimate |
| `operators` (6) | operator_id TEXT, name TEXT, experience_yrs INTEGER, machine_id TEXT | operator master data | `init_db` | `boot`, login |
| `sessions` (1,549) | timestamp TIMESTAMP, machine_id, operator_id, engine_hours REAL, fuel_used_l REAL, load_cycles INTEGER, idling_time_min INTEGER, seatbelt_status TEXT, safety_alert_triggered TEXT, task_id, task_type, weather, operator_skill, machine_age_yrs INTEGER, estimated_time_min REAL, duration_min INTEGER, alert_types, site, soil, temp_c REAL, visibility_m INTEGER, slope_deg REAL, volume_m3 INTEGER, min_proximity_m REAL, proximity_alerts INTEGER, max_speed_kmh REAL, max_tilt_deg REAL, overload_events INTEGER, harsh_events INTEGER, engine_temp_c REAL, hours_into_shift REAL, injected_event TEXT | one row per historical work session (synthetic) | `init_db` only | `boot` (all ML, competencies, charts) |
| `tasks` (28) | task_id, operator_id, machine_id, task_type, site, soil, slope_deg INTEGER, volume_m3 INTEGER, estimated_time_min REAL, scheduled_start TEXT, priority, status, started_at, completed_at, notes | "today's" work orders | `init_db`; `update_task` (Start / Mark complete) | My Day, Live Cab, assistant, report |
| `incidents` (4) | time, operator_id, machine_id, type, severity, description | incident log | `init_db` (2 seeded); Safety Center form | Safety Center |
| `checklists` (9) | operator_id, machine_id, time, items_ok TEXT, issues | pre-start inspections | Live Cab form (every submit) | `checklist_done_today` |
| `training_log` (3) | operator_id, module_id, module, score REAL, time | completed training | `init_db` (3 seeded); quiz pass; simulator save | loops, Training Hub, report, assistant |
| `bookings` (0) | operator_id, topic, date, slot, instructor | instructor bookings | `booking_form` (Training Hub tab and Supervisor Console) | Training Hub, Supervisor Console |
| `supervisor_reviews` (0) | operator_id, module_id, training_time TEXT (= `training_log.time`), decision (approved / retraining / instructor), assessment, note, reviewer, time TEXT (seconds) | supervisor decisions, **append-only** | `data.log_review` (Supervisor review panel) | `supervision.review_state`, both roles |

Relationships (logical, not enforced): `operator_id` → `operators`; `machine_id` → `machines`; `training_log.module_id` →
`data.TRAINING_MODULES` and `skills.COMPETENCIES[*].module`.

- **Initialisation:** `init_db()` runs inside `boot()`. If the file exists and has a `sessions` table, nothing happens.
  Otherwise (missing file, or a blank file SQLite re-created) it deletes the file, generates everything and writes the CSVs
  (only when the DB lives in the project folder).
- **Reset:** stop the app, delete `operator.db`, start again → identical synthetic history re-dated to the new "today",
  fresh today's tasks, 2 seeded incidents, 3 seeded trainings, empty checklists/bookings.
- **Caching:** `boot()` is `@st.cache_resource`; the `sessions`-derived data and models are fixed for the process lifetime.
  `tasks`, `checklists`, `incidents`, `training_log`, `bookings` are re-read on every rerun (so UI writes show immediately).
- **Migrations:** one additive migration: `data.ensure_review_table()` runs `CREATE TABLE IF NOT EXISTS supervisor_reviews`
  (called by `init_db` and before every review read/write). It never alters or deletes existing tables or rows, so an
  existing `operator.db` gains the table on first use without a reset (tested on a copy). Any other schema change still
  requires deleting the DB.
- **Training time precision:** new `training_log` rows (quiz pass, simulator) are stamped to the second
  (`%Y-%m-%d %H:%M:%S`) so a retake is always a new review case; seeded rows keep minute precision.
- **Persistence limitations:** live telemetry, live alerts, chat and shift state are not stored; tasks are not re-generated
  per day; no concurrency control beyond SQLite's own locking.

---

## 10. Machine learning overview

| # | Model | Library | Purpose | Trained when | Persisted | Retrains on new data |
|---|---|---|---|---|---|---|
| 1 | Task-time regressor | `HistGradientBoostingRegressor` in a pipeline with `OneHotEncoder` | predict actual task minutes before a task starts | at server start (`boot`) | No (in memory) | No |
| 2 | Anomaly detector | `IsolationForest` | flag unusual sessions | at server start | No | No |

Everything else that looks "smart" is deterministic: alert rules, condition rules, fatigue indicator, competency standards,
statistical tests, badges, the assistant router, the substitution explanations.

---

## 11. Task-time prediction

### 11.1 Definition
- **Target:** `duration_min` (actual minutes).
- **Features (`an.TIME_FEATURES`, all known before the task starts):** task_type, weather, operator_skill,
  machine_age_yrs, machine_type, soil, temp_c, slope_deg, volume_m3, operator_pace_hist.
- **Operator past pace (`operator_pace_history`):** median of actual ÷ planner over the operator's previous 30 sessions from
  **strictly earlier days** (≥ 5 needed, else NaN; 38 sessions are NaN). At prediction time, `current_pace` uses the last 30
  recorded sessions (Ravi 1.13).
- **Preprocessing:** one-hot encoding of the 5 categoricals (`handle_unknown="ignore"`), numeric passthrough, NaN handled
  natively by the booster.
- **Hyperparameters:** `max_iter=300, learning_rate=0.06, min_samples_leaf=20, random_state=0` (fixed, not tuned).

### 11.2 Evaluation (recomputed on the current DB)
- **Split:** temporal. The first 80% of days train (1,238 sessions, 10 Jul – 7 Sep), the last 20% test (311 sessions,
  8 – 22 Sep).
- **Results (held-out synthetic test set):**

| Metric | Model | Planner baseline | Task-type median |
|---|---|---|---|
| MAE | **12.27 min** | 24.31 min | 30.70 min |
| MAPE | 16.1% | 28.7% | — |
| Within ±10% of actual | 42.4% | 14.8% | — |
| Mean bias (pred − actual) | −1.7 min | −24.0 min (planner underestimates) | — |

- **MAE reduction vs planner: 49.5%**, bootstrap 95% CI **43.5% – 54.9%** (1,000 resamples of test rows, `rng(0)`).
- **Reference ("oracle"):** using the generator's observable formula (`true_duration_min`) directly gives MAE 10.21 min; the
  remaining gap is unobserved noise, so the model is near what is learnable.
- **Robustness (generator seeds 11–15, recomputed in this audit):**

| Seed | Sessions | Model MAE | Planner MAE | Reduction | 95% CI |
|---|---|---|---|---|---|
| 11 (current DB) | 1,549 | 12.27 | 24.31 | 49.5% | 43.5–54.9% |
| 12 | 1,546 | 12.74 | 28.29 | 55.0% | 49.6–60.0% |
| 13 | 1,531 | 12.66 | 21.91 | 42.2% | 35.2–48.8% |
| 14 | 1,528 | 11.86 | 19.82 | 40.2% | 30.8–47.5% |
| 15 | 1,545 | 13.20 | 25.87 | 49.0% | 42.8–54.2% |

  → **40–55% reduction, model MAE 11.9–13.2 min.** The old "72% / ±6 vs ±22 min" claim is retired (it came from a random
  split on formula-exact data).
- **Global importance** (permutation, test set, % of total): Volume 40.5, Task type 38.4, Soil 10.3, Operator skill 5.4,
  Weather 2.7, Machine age 1.2, Operator past pace 0.8, Machine type 0.5, Slope 0.2, Temperature 0.0.
- **Out-of-fold expected time:** `GroupKFold(5)` grouped by day gives each session a prediction from a model that never saw
  that day (OOF MAE 12.03; no NaN). Used only for the Task-execution competency and the assistant's history answer.
- **Deployment model:** refit on all 1,549 sessions.

### 11.3 Runtime inference and explainability
- `predict_minutes(model, **features)` for My Day, Live Cab hero card, estimator, assistant, CSV upload.
- **Local explanation (`explain_prediction`)**: for each input that differs from the site-typical reference (mode / median:
  Grading, Sunny, Intermediate, 4 yrs, Excavator, Sand, 32 °C, 5.1°, 90 m³, pace 1.35), the change in minutes if that input
  is set to the reference. Indicative, non-additive, **not causal** (labelled so in the UI).
- **What-if:** weather × skill heat-map; sidebar weather/temperature changes update every ETA live.
- **Uncertainty:** only a global "± typical error" (the test MAE, ±12 min) is shown; there are **no per-prediction intervals**.
- **CSV upload:** organisers' format → defaults for missing columns (see §5.8).

### 11.4 Leakage controls (tested in `test_logic.py`)
No post-task signals in `TIME_FEATURES` (idle, fuel, cycles, alerts, actual time); pace uses earlier days only; temporal split;
OOF grouped by day.

### 11.5 Limitations
Synthetic data only; the generator's structure is partially mirrored by the model's features; no real-world validation;
no per-prediction uncertainty; no retraining; temperature has near-zero importance here because heat only matters above
35 °C in the generator.

---

## 12. Anomaly detection

### 12.1 In simple words
An **Isolation Forest** builds many random decision trees that keep splitting the data at random until each session is
isolated. Normal sessions look like many others and need many splits; strange sessions get isolated in a few splits. Short
average path = high anomaly score. We flag the 5% most isolated sessions and explain *which signals* made them unusual.

### 12.2 Technically (`an.detect_anomalies`)
- **Features (6):** idle share, fuel burn per working hour, load cycles per working hour, top speed ÷ site limit, maximum
  tilt, engine temperature.
- **Normalisation:** robust z-score **within each machine type**: (x − median) / (1.4826 × MAD).
- **Model:** `IsolationForest(contamination=0.05, random_state=0)` (default 100 trees, 256-sample subsampling).
- **Outputs:** `anomaly_score = −score_samples`, `is_anomaly` (predict = −1) → **78 of 1,549 sessions flagged**, `top_feature`,
  `reason` = the top two features with |z| ≥ 2 ("Idle share high (+5.0 robust SD); Fuel burn while working high (+4.5 robust
  SD)"), else "unusual combination of signals".
- **Evidence card (`explain_anomaly`):** the 3 signals that deviate most (ratio) from the **site baseline** (median of the same
  machine type, excluding the session) with the **operator baseline** (operator's own median, excluding the session), context,
  and a rule-based recommendation for the top signal.
- **Runs:** once at startup on historical sessions; the result is shown in Machine Insights and the assistant. **Not live, not
  persisted, does not feed training.**

### 12.3 Validation (synthetic labels, recomputed)
| Measure | Value | Meaning |
|---|---|---|
| **Recall on injected idle/fuel anomalies** | **80% (48 / 60)** | share of labelled idle/fuel anomalies that were flagged |
| Precision vs idle/fuel labels | 61.5% (48 / 78) | share of flags that are labelled idle/fuel anomalies |
| Share of flags with any injected label | 73.1% | includes speed labels |
| Recall on injected speed events | 13.6% (9 / 66) | single-signal spikes are mostly missed |
| "Flags with a known cause" (in-app) | 75.6% vs 18.8% base rate | injected label **or** a safety-threshold breach; **not precision** |
| Seeds 11–15 recall | 69–80% | robustness |

Top features among flags: idle share 36, fuel burn 34, speed vs limit 8. Flags per machine: GRD001 17, EXC001 16, LDR001 15,
DOZ001 14, TRK001 8, EXC002 8.

### 12.4 Known weaknesses
- Fixed 5% contamination: it always flags ~5% whether or not anything is wrong.
- Weak on single-signal events (speed recall 13.6%).
- The `reason` (z-score, top 2) and the evidence table (ratio vs site median, top 3) can highlight different signals. Example
  found in this audit: the latest EXC001 flag (22 Sep 10:37) has reason "idle high; fuel burn high" but its evidence table
  lists idle share, load-cycle rate and maximum tilt.
- Validation is only possible because labels are synthetic; real use needs labelled incidents.
- "80%" is **recall**, never "accuracy".

---

## 13. Competency / skill system (`skills.py`)

**Scoring:** for each competency, each session is 1 (meets the standard), 0 (does not) or NaN (not applicable). Score =
100 × share of applicable sessions meeting the standard among the operator's **last 30 sessions** (`WINDOW = 30`), only if
at least **8** are applicable (`MIN_SESSIONS`), else "not enough sessions". **Gap:** score < **70** (`GAP_THRESHOLD`).
Site median = median of all operators' scores (anonymous, no ranking). Trend = previous 30-session window.

| Competency | Standard (session meets it when…) | Applies to | Key metric (before/after) | Training module |
|---|---|---|---|---|
| Safety discipline | seatbelt fastened **and** max speed ≤ site limit **and** no overload | all | share unbuckled (lower better) | `safety` Excavator safety essentials (YouTube) |
| Fuel efficiency | idle ≤ 20% of session **and** fuel per working hour ≤ 120% of rated burn (Exc 18, WL 16, Dozer 24, Truck 22, Grader 14 L/h) | all | idle share (lower) | `fuel` Fuel efficiency & idle reduction (YouTube) |
| Cycle efficiency | m³ per load cycle ≥ 85% of rated 10 m³ | all | m³ per cycle (higher) | `operation` Operating controls & settings (YouTube) |
| Machine handling | no harsh braking/turning events | all | harsh events per session (lower) | `operation` |
| Terrain handling | tilt ≤ 15° **and** tilt ≤ 7° above ground slope **and** speed ≤ 95% of limit | sessions on slopes ≥ 5° | tilt above ground slope (lower) | `terrain` Safe operation on sloped terrain (**offline MP4, 42 s**) |
| Task execution | actual ≤ 120% of the out-of-fold model-expected time | sessions with an OOF estimate | actual ÷ expected (lower) | none → instructor coaching |

**Current scores (last 30 sessions; gaps in bold):**

| Operator | Safety | Fuel | Cycle | Handling | Terrain (n) | Execution |
|---|---|---|---|---|---|---|
| OP1001 Ravi | 83 | 80 | 80 | 87 | **31 (16)** | 87 |
| OP1002 Anita | 87 | 80 | 87 | 70 | **67 (15)** | 87 |
| OP1003 Irfan | 93 | **0** | 73 | 87 | 94 (16) | 80 |
| OP1004 Priya | 83 | **27** | **57** | **53** | 93 (15) | 83 |
| OP1005 Suresh | 87 | 90 | 93 | 80 | 84 (19) | 77 |
| OP1006 Lakshmi | 87 | 90 | **23** | 77 | 83 (18) | 83 |
| Site median | 87 | 80 | 77 | 78 | 84 | 83 |

Ravi's terrain evidence: 16 sessions on slopes ≥ 5°; 4 with tilt > 15°; 5 with tilt > 7° above the slope; 9 with speed > 95%
of the limit on a slope.

**Personal improvement** (latest 30 vs previous 30, Ravi): idle share 17% → 18% (worse), alerts/session 0.87 → 0.60 (better),
seatbelt 90% → 97% (better), harsh events 0.13 → 0.13, cycle variation 0.11 → 0.14 (worse), actual ÷ expected 0.98 → 0.95
(better).

**Milestones (`an.badges`, sensor-based only):** Buckle Champion (belt fastened in last 15 sessions), Fuel Saver (average
idle < 15% over last 10), Smooth Operator (no harsh events in last 10). Ravi currently has none.

Standards and thresholds are **explicit policy choices** (not learned) and are listed in `COMPETENCIES`.

---

## 14. Closed-loop training

```
OBSERVE → DIAGNOSE → RECOMMEND → TRAIN → MONITOR → VERIFY → ADAPT
```

| Stage | What the code does |
|---|---|
| **OBSERVE** | `session_standards()` marks every recorded session 1/0/NaN against each written standard (at startup). |
| **DIAGNOSE** | `operator_profile()` scores the last 30 sessions (≥ 8 applicable), attaches evidence counts and the site median; score < 70 → `gap=True`. |
| **RECOMMEND** | `loop_stage()` returns stage 1 "Skill gap detected: training recommended"; Training Hub shows the **Recommended now** card for the first gap with a lesson not yet trained; loop cards show **▶️ Start: {module}**; assistant training answers list the same. Task execution has no lesson → **Book instructor coaching**. |
| **TRAIN** | Lesson (offline MP4 or YouTube or key points when offline) + 3-question check; **pass ≥ 66%** → `data.log_training(op, module, score)` → `training_log`; certificate download. |
| **MONITOR** | `compare_before_after()` takes applicable sessions **before** the training time (last 30, `PRE_N`) and **after** it (first 30, `POST_N`). With fewer than 8 post sessions → verdict "Monitoring: k/8 sessions recorded since training". |
| **VERIFY** | With ≥ 8 post sessions: one-sided Fisher exact on pass/fail counts (post > pre) and one-sided Mann–Whitney U on the key metric in the "better" direction. Verified if (Fisher p < 0.05 **and** post rate > pre rate) **or** Mann–Whitney p < 0.05. |
| **ADAPT** | Not verified and ≥ 15 post sessions (`ADAPT_AFTER`) → "No measurable improvement: escalate to instructor coaching" (red ADAPT step, coaching button). Otherwise "Monitoring: no significant change yet". |

**Current loops (recomputed):**

| Operator · training (date) | Competency | Pre (n=30) → Post (n=30) pass rate | Fisher p (one-sided) | Key metric pre → post | Mann–Whitney p | Verdict |
|---|---|---|---|---|---|---|
| Ravi · Fuel efficiency (14 Aug) | Fuel efficiency | 26.7% → 80.0% | 3.6 × 10⁻⁵ | idle share 26.6% → 15.5% | 6.2 × 10⁻⁷ | **Verified** |
| Anita · Excavator safety essentials (24 Aug) | Safety discipline | 60.0% → 93.3% | 0.0024 | unbuckled share 33.3% → 0% | 0.00031 | **Verified** |
| Priya · Fuel efficiency (29 Aug) | Fuel efficiency | 30.0% → 20.0% | 0.88 | idle share 26.7% → 24.2% | 0.30 | **Escalate to coaching** |

These three outcomes come from **seeded synthetic history** (the generator changed Ravi's and Anita's hidden traits after the
training dates, and deliberately did not change Priya's). The verdicts themselves are computed from the recorded sessions.
The UI labels them "SEEDED HISTORY · synthetic".

**A training completed in the app today** (e.g. Ravi's terrain quiz in the demo):
- is logged at the current time, which is after the last recorded session (`HIST_END` = 22 Sep 18:36), so the loop shows
  **"NEW · completed this session"** and **VERIFY: monitoring 0/8**;
- the page states that live sessions aren't saved, so the check stays at 0 and **no improvement is claimed**;
- ⚠️ **The loop cannot progress past Monitoring in this prototype** because new sessions are never written to `sessions`
  (live telemetry is not persisted and completed tasks do not create session rows), and the models/scores are only
  recomputed from `sessions` at server start. This has **not** changed since the previous handover.

### 14.1 Supervisor review (human checkpoint between TRAIN and VERIFY)

Conceptually the operator workflow is now **OBSERVE → DIAGNOSE → TRAIN → SUPERVISOR REVIEW → VERIFY → ADAPT**, but the
five-stage loop and `skills.py` are unchanged: the review is shown as a state inside TRAIN/VERIFY.

| Case | Rule (`supervision.py`) |
|---|---|
| What is reviewed | The operator's **latest passed training** for a module that maps to a competency (`safety`, `fuel`, `operation`, `terrain`); `walkaround` and `simulator` are not reviewed |
| Seeded history | Trainings on or before the last recorded session (`HIST_END`) are **exempt** ("SEEDED HISTORY · synthetic"); Ravi/Anita/Priya keep Verified / Verified / Escalated |
| Awaiting review | New training with no decision → amber "AWAITING SUPERVISOR REVIEW"; TRAIN "awaiting review", VERIFY "after supervisor approval" |
| Approved | Green "✓ SUPERVISOR APPROVED" + blue "Monitoring 0/8": "Supervisor approved training. Behavioural verification begins after post-training sessions are recorded." |
| Retraining | "RETRAINING REQUESTED": the gap stays open (score unchanged, it comes from sessions), "Recommended now" and **Start** return; the next pass is a **new case** |
| Instructor | "INSTRUCTOR COACHING RECOMMENDED": the operator's **Book instructor coaching** button and the supervisor's booking form both write to `bookings` |
| Decisions | Append-only; the latest decision for the case's training wins; older decisions stay in `supervisor_reviews` |

**Supervisor Approved ≠ Statistically Verified.** `supervision.case_group` returns Verified/Escalated only from the existing
`skills.training_loops` verdicts (i.e. `skills.verdict`); approval alone can only lead to Monitoring (unit-tested). A training
approved today stays at **Monitoring 0/8** because live sessions are not persisted; no sessions are created.

Other details: `walkaround` and `simulator` modules map to no competency (no loop); retaking a quiz logs another training and
creates another loop entry (the latest one drives the stage).

---

## 15. Statistical verification

| Test | Purpose | Inputs | Null hypothesis (as implemented) | Sidedness | Significance |
|---|---|---|---|---|---|
| Fisher exact (`scipy.stats.fisher_exact`, `alternative="greater"`) | Did the share of sessions meeting the standard increase? | 2×2 table [[post pass, post fail], [pre pass, pre fail]] | the odds of meeting the standard after training are not higher than before | one-sided (improvement only) | p < 0.05 **and** post rate > pre rate |
| Mann–Whitney U (`scipy.stats.mannwhitneyu`) | Did the key behaviour metric shift in the better direction? | per-session metric values post vs pre (e.g. idle share) | post values are not stochastically lower (or higher, for "higher is better") than pre values | one-sided (`less` or `greater`) | p < 0.05; skipped if the two samples have ≤ 2 distinct values in total |

**Interpretation:** a verified loop means *sessions after the training differ from sessions before it, in the expected
direction, beyond what chance would usually produce*. It is **before/after statistical association, not causal proof**:
there is no control group, other factors (season, tasks, sites) change over time, several tests are run per loop without
multiple-comparison correction, and 30 sessions per side is small. Minimum 8 post sessions is a pragmatic floor, not a power
calculation. In this prototype the effects being detected were generated by the synthetic data.

---

## 16. Assistant / AI chat (`app.py`, section 8)

### 16.1 Architecture: deterministic router first, optional LLM phrasing second
```
question ──► route(q) ──► intent (fixed priority order, keyword/regex) ──► answer builder a_*() ──► (markdown facts, action buttons)
                │                                                                  │
                └─ follow-up context st.session_state.asst_ctx {topic, task_id, comp, anomaly_idx}
                                                                                   ▼
                              no key ─────────────────────────────────────► show facts (offline answer)
                              ANTHROPIC_API_KEY set ─► ask_claude(chat, facts) ─► show Claude's rephrasing
                                                          └─ any exception ─► facts + "(Online AI unavailable (…), so this is the offline answer.)"
```
**The router and builders decide every fact.** Claude never computes readings, estimates, scores, anomaly results, loop
verdicts or safety actions; the action buttons always come from the router.

### 16.2 Intent order in `route()` (first match wins)
Matching uses `_has()` (word-start regex `\b<term>`) for trigger phrases and plain substring checks for
`COMP_WORDS` / `SENSOR_WORDS` / `TOPIC_LESSONS`.

| # | Intent | Example triggers | Builder |
|---|---|---|---|
| 1 | Help | "what can you do", "help", "what can i ask" | `a_help` |
| 2 | Closed loop | "after training", "happens after", "verify", "monitoring", "the loop" | `a_loop` |
| 3 | Shift / fatigue | "how long have i", "last break", "shift", "tired", "fatigue" | `a_shift` |
| 4 | Machine | "what machine", "my machine", "engine hours", "service", "maintenance" | `a_machine` |
| 5 | Current telemetry | a sensor word (tilt, speed, rpm, coolant/temperature, load, fuel rate, seatbelt, proximity/nearest) **and** "current/now/what's my/reading…", not "why" | `a_telemetry` |
| 6 | Task by ID | `T0001`–style or `D001`–style ID in the text | `a_task("eta"/"why", id)` |
| 7 | Live safety | "warning", "alert", "alarm", "danger", "hazard", "worker", "critical" | `a_safety("why"/"action")` |
| 8 | Anomaly | "flagged", "anomal", "unusual", "odd", "abnormal", "outlier" | `a_anomaly("status"/"why"/"action")` |
| 9 | Task ETA | "eta", "estimate", "how long", "next task", "planner", "job" (+ "schedule/today" → schedule) | `a_task` |
| 10 | Schedule | "schedule", "my tasks", "what's next", "rest of the day" | `a_task("schedule")` |
| 11 | Lesson on a topic | "teach/lesson/video/learn about" + a topic word (slope, seatbelt, fuel, inspection, bucket…) | `a_training` |
| 12 | Training | "training", "train", "course", "learn", "quiz" | `a_training` |
| 13 | Skills | "improve", "skill", "score", "weak", "gap", "profile" (+ competency word → specific, "why/low" → evidence) | `a_skill` |
| 14 | Idle / fuel | "idle", "idling", "fuel" | `a_idle` |
| 15 | Conditions | "is it safe", "safe to work", "weather", "rain", "heat", "visibility", "wind", "conditions" | `a_conditions` |
| 16 | Follow-up | ≤ 8 words with "why/what should I do/more/it/that/then…" → resolved against the stored topic (safety, task, anomaly, skill, training/loop, shift/machine) | respective builder |
| 17 | Ambiguous follow-up | follow-up with no stored topic | "Do you mean the current safety alert, your next task, a flagged session or your skill profile?" |
| 18 | Out of scope | anything else | "I can help with your machine, safety alerts, tasks, anomalies, skills, training and shift status while offline. Try "what can you do?" for examples." |

### 16.3 Data each builder retrieves
- `a_safety`: `active_alerts` + `last_reading` (live, simulated) or recent `live_alerts`; action mode lists `SAFETY_ACTIONS`;
  tilt → terrain lesson button.
- `a_telemetry`: one value from `last_reading` with its threshold, labelled "Simulated reading at HH:MM:SS".
- `a_task`: model ETA + top factors (`explain_prediction`), "why vs planner" (labelled indicative, not causal), next action
  (Start/Mark complete), schedule; also organisers' sample IDs T001–T005 and historical session IDs.
- `a_anomaly`: flagged sessions for the machine/fleet, evidence vs operator and site baselines, recommendation; notes that the
  detector was validated on synthetic labels only.
- `a_skill` / `a_training`: profile scores, gaps, evidence, the matched lesson (with "42 sec, plays offline" for terrain),
  verified loops labelled "seeded synthetic history".
- `a_loop`: the verification rules (8 sessions, Fisher + Mann–Whitney, escalate after 15) and each loop's verdict.
- `a_shift`, `a_conditions`: demo shift sliders, fatigue indicator ("not a medical assessment"), condition warnings.
- `a_machine`, `a_idle`, `a_help`.

### 16.4 Claude integration (`ask_claude`)
- Only when `ANTHROPIC_API_KEY` is set (via `.env`, loaded by `python-dotenv`).
- `anthropic.Anthropic().beta.messages.create(model="claude-opus-5", max_tokens=1024, betas=["server-side-fallback-2026-07-01"],
  fallbacks="default", system=…, messages=<whole chat>)`.
- System prompt: "language layer … the facts below are the only source of truth … never invent readings, estimates, scores,
  anomaly results or training outcomes; never make or override safety decisions; never claim real CAT telemetry, medical
  fatigue detection or real-world training effects … if the facts don't answer the question, say so", plus `context()`
  (operator, conditions, today's tasks, competencies, loops, active alerts, site warnings) and the retrieved facts.
- `stop_reason == "refusal"` → the facts are shown instead.
- Verified in this audit: the installed SDK (1.8.0) accepts the `fallbacks` parameter and the `server-side-fallback-2026-07-01`
  beta (static check); the unreachable-endpoint fallback is tested (`test_final_ui.py`). **🔍 A real Claude call was not made
  (no `.env`/key on this machine).**
- Privacy note: with a key, operator name, tasks and scores are sent to the Anthropic API.

### 16.5 Known assistant limitations
Rule-based keyword routing with a fixed priority, not an NLU model: unusual phrasings can land in the wrong intent (e.g. any
question containing "shift" goes to the shift answer, "service" to the machine answer). Substring matching of topic words can
over-match. English only. No memory beyond the browser session. Claude's rephrasing is constrained by the prompt only; its
output is not checked against the facts.

---

## 17. Offline-first behaviour

| Works completely offline | Needs internet | Needs an API key |
|---|---|---|
| Login, checklist, Live Cab (simulated), My Day, Safety Center, incidents, Machine Insights, Task Estimator (incl. CSV upload), Skill Profile, closed loop, quizzes, simulator, booking, report, assistant (offline answers), theme, the terrain MP4 lesson | 4 YouTube lessons (`online()` checks `www.youtube.com:443` with a 1.5 s timeout, cached 60 s) | Claude phrasing (`ANTHROPIC_API_KEY`) |

- **Local assets:** `operator.db`, models in memory, `training_videos/terrain.mp4`. Any `training_videos/<lesson id>.mp4`
  (e.g. `fuel.mp4`) automatically replaces that lesson's YouTube video and plays offline.
- **Offline YouTube lessons:** a warning replaces the player; key points and the quiz still work and still count.
- **`CAT_OFFLINE=1`** forces offline mode (used by the tests).
- **Failure behaviour:** no network or bad key → offline answer + note; no YouTube → local/key points; no DB → created on
  first run.
- Streamlit itself is local; the Edge app window loads `http://localhost:8501`.

---

## 18. UI / UX and design system

### 18.1 Screens
Documented feature-by-feature in §5 (Login, Live Cab, My Day, Safety Center, Machine Insights, Task Estimator, Ask Assistant,
My Skill Profile, Training Hub, End-of-shift report). Navigation is one sidebar radio with 8 pages in 3 groups.
Programmatic jumps (lesson buttons, assistant actions) use `navigate()` → `st.session_state.pending_nav`, applied before the
radio is drawn (works from inside the auto-refreshing fragment).

### 18.2 Design system (current, industrial HMI style)
- **Colour tokens** (CSS variables on `:root`, switched by theme):
  - Dark (default): bg `#0E1013`, surface `#16191E`, surface-2 `#1E2228`, border `#2A2F37`, text `#E8EAED`, muted `#98A1AD`.
  - Light: bg `#F3F4F6`, surface `#FFFFFF`, surface-2 `#ECEEF1`, border `#D5D9DF`, text `#15181C`, muted `#5B6470`,
    CAT-text `#8A6A00` (readable yellow-brown for accent text on white).
  - Semantic: CAT yellow `#FFCD11`, CAT black `#111316`, critical `#E5484D`, caution `#F5A524`, normal `#2FB463`,
    info `#4C9AFF`, neutral `#6B7480`.
- **CAT yellow usage:** brand block, sidebar right border, selected navigation item, primary buttons (black text), hero-card
  accent bar, ETA value, "now"-stage in loop rails, `cat` chips, radar machine marker. Not used for alert severity.
- **Typography:** display font stack Bahnschrift → DIN Alternate → Segoe UI (headings, metrics, chips, buttons); body uses
  Streamlit's default.
- **Components (helpers in `app.py`):** `page_header` (kicker "■ GROUP", title, subtitle, chips), `chip` / `status_chip`
  (one status language: NORMAL, CAUTION, CRITICAL, LOCKED, MONITORING, VERIFIED, PENDING), `card` (`accent`, `hero`),
  `section`, `state_panel` (large NORMAL/CAUTION/CRITICAL block), `.banner` (red/amber/green alert bars), `.rail` (loop
  stepper), `.kv` rows, `hmi_chart` (theme-aware Plotly), `SIM_CHIP` (dashed "◌ SIMULATED TELEMETRY").
- **Layout:** `layout="wide"`, content max width 1500 px, columns per page; buttons ≥ 2.9 rem (~46 px) for gloved/touch use.
- **Responsive behaviour:** *previously documented* (final polish pass, 23 Sep): no overflow or truncation at 1280×720,
  1440×900 and 1920×1080 in both themes. Not re-measured in this audit. Streamlit collapses the sidebar on narrow widths.
- **Streamlit components used:** radio, selectbox, slider, select_slider, toggle, checkbox, form, text_input/area, file_uploader,
  date_input, button, download_button, expander (keyed for the alert log), popover, tabs, container, metric, progress, video,
  chat_input/chat_message, dataframe, plotly_chart, fragment.

---

## 19. Testing

**All run fresh during this audit (24 Sep 2026), on temporary databases, offline, with no API key:**

| Suite | Command | Result |
|---|---|---|
| Unit | `.venv\Scripts\python.exe -m unittest tests.test_logic` | **26 run, 26 OK, 0 failed, 0 skipped** |
| Unit: supervisor review logic + migration | `.venv\Scripts\python.exe -m unittest tests.test_supervision` | **13 run, 13 OK** |
| Smoke / E2E demo story | `.venv\Scripts\python.exe tests\smoke_test.py` | **32 / 32 passed** |
| Final UI (assistant, theme, logout) | `.venv\Scripts\python.exe tests\test_final_ui.py` | **25 / 25 passed** |
| Alert log (edge logging, expander) | `.venv\Scripts\python.exe tests\test_alert_log.py` | **13 / 13 passed** |
| Supervisor roles & review flow | `.venv\Scripts\python.exe tests\test_supervisor_ui.py` | **51 / 51 passed** |

**Total: 160 automated checks, 0 failed, 0 skipped** (re-run after the Supervisor Console change; the four original suites
were also run before the change: 26 / 32 / 25 / 13, identical).

`operator.db` had the same SHA-1 before and after all runs (tests never touch it).

**Covered:** competency standards and scoring; min-sample rule; verification verdicts (verified / monitoring / adapt);
loop stages; personal improvement direction; no post-task features; temporal split; pace uses earlier days only; metric
consistency; OOF coverage; anomaly evidence baselines; detector validation; explanation lists only model inputs; hidden traits
not in the DB; seeded training story; simulator normal/worker/clear behaviour; fatigue indicator; the MP4 is valid; planner
baseline; every page renders; checklist gate (5/8 locked, 8/8 unlocks); no spontaneous proximity alert; worker persists and
clears; tilt alert "Why"; assistant NL questions, follow-ups, clarification, offline fallback, Claude-unavailable fallback;
lesson routing; offline MP4; quiz pass → Monitoring 0/8; seeded loops labelled; report; Dark default, Light switch, theme
persistence; report persists across rerun; logout → login → new shift; one entry per held alert (worker, tilt), clear and
re-enter → 2, worker + tilt → 2, seatbelt + overspeed once each; alert-log expander state.

**Not covered by automated tests:** a real Claude call; the `.bat` launcher / Edge window; YouTube playback online;
incident-logging form, instructor booking, scenario simulator save, certificate and report download contents, CSV upload with
a user file (the incident form and task Start/Complete were used manually during rehearsals, visible in the DB); visual layout
and Light-mode styling (spot-checked manually only); the real 2 s browser refresh (AppTest simulates it by rerunning; the
alert-log behaviour was also checked in a real browser).

---

## 20. Running the project

### 20.1 Requirements
- **OS:** Windows 10/11 for the `.bat` launcher (the Python code itself is cross-platform).
- **Python:** 3.11 (a portable 3.11.9 is bundled in `.python311/`; `.venv` points to it).
- **Browser:** Microsoft Edge (for the app window) or any modern browser.
- **Node:** not required (`web/` is unused).
- **Packages:** `requirements.txt` (key: streamlit 1.64.0, scikit-learn 1.9.1, scipy 1.17.1, pandas 3.0.6, numpy 2.4.6,
  plotly 7.1.0, anthropic 1.8.0, python-dotenv 1.2.3).

### 20.2 Installation (only if `.venv` is missing)
```powershell
py -3.11 -m venv .venv
.venv\Scripts\pip.exe install -r requirements.txt
# offline alternative using the downloaded wheels:
.venv\Scripts\pip.exe install --no-index --find-links wheels -r requirements.txt
```
🔍 The offline wheel install was not re-run in this audit.

### 20.3 Environment variables
| Variable | Required? | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | No | Put in `.env` (copy `.env.example`) to enable Claude phrasing in Ask Assistant |
| `CAT_OPERATOR_DB` | No | Database path (default `operator.db` in the project folder; tests use temp files) |
| `CAT_OFFLINE` | No | `1` forces offline mode (no YouTube check) |
| `ANTHROPIC_BASE_URL` | No | Standard Anthropic SDK override; used by tests to simulate an unreachable API |

### 20.4 Run
- **Operator way:** double-click **`Start Operator Assistant.bat`**. A minimised "server" window starts Streamlit on port 8501
  (keep it open), then an Edge app window opens at `http://localhost:8501` (or the default browser if Edge isn't found).
- **Developer way:** `.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501`
- First load takes about 30 s (data check + model training); later loads are instant.

### 20.5 Tests
```powershell
.venv\Scripts\python.exe -m unittest tests.test_logic
.venv\Scripts\python.exe tests\smoke_test.py
.venv\Scripts\python.exe tests\test_final_ui.py
.venv\Scripts\python.exe tests\test_alert_log.py
.venv\Scripts\python.exe -m unittest tests.test_supervision
.venv\Scripts\python.exe tests\test_supervisor_ui.py
```

### 20.6 Clean reset (do this on the presentation day)
1. Close the Edge window and the minimised server window (or stop the Streamlit process).
2. Delete `operator.db` (optionally also `operator - Copy.db`).
3. Start again with the launcher. The DB, today's tasks (dated today), the CSV exports, seeded incidents and trainings are
   regenerated; checklists, bookings and rehearsal incidents are gone.

**Never delete `operator.db` while the app is running** (the running process keeps its cached data but new reads would hit a
blank file).

---

## 21. Troubleshooting

| Problem | Cause | Solution |
|---|---|---|
| First page takes ~30 s | `boot()` checks/creates the DB and trains both models | Wait; later loads are cached |
| Edge window doesn't open | Edge not at the standard path / blocked | Open `http://localhost:8501` in any browser |
| "Port 8501 is already in use" / old version shown | Another Streamlit instance is running | Close the old server window (or `Get-NetTCPConnection -LocalPort 8501` → stop that process) and relaunch |
| My Day shows yesterday's date / "now" line outside the timeline / odd overlap warnings | `tasks` are generated once, dated the day the DB was created | Clean reset (§20.6) on the presentation day |
| Live Cab keeps showing the checklist | No 8/8 checklist today for this operator | Tick all 8 items and submit |
| Errors like "no such table" after deleting the DB mid-run | Cached `boot()` did not re-run; a blank DB file was created | Stop the app, delete `operator.db`, start again |
| Alert log shows many identical entries | Old browser session from before the edge-triggered fix | Start a new shift (or press F5 and log in again) |
| YouTube lessons show a warning | Offline or `CAT_OFFLINE=1` | Expected; terrain MP4 still plays; add `<lesson id>.mp4` for offline copies |
| Assistant answer ends with "(Online AI unavailable (…), so this is the offline answer.)" | Invalid key / no network | Fix `.env` or remove the key; the offline answer is complete |
| App reruns when a file is saved | `runOnSave = true` in `.streamlit/config.toml` | Don't edit files during a demo |
| `tools/make_offline_lesson.py` fails with `ModuleNotFoundError: imageio_ffmpeg` | Build-only dependency not installed | `.venv\Scripts\pip.exe install imageio-ffmpeg` (only to rebuild the MP4) |
| Data tables look dark in Light mode | Streamlit draws tables with its configured (dark) theme | Known cosmetic limitation |
| "missing ScriptRunContext" warnings when running tests | Streamlit AppTest bare mode | Harmless |
| `UnicodeEncodeError` printing emoji in a console | cp1252 console encoding | Set `PYTHONIOENCODING=utf-8` (the test files already reconfigure stdout) |

---

## 22. Current project status

| Component | Status | Explanation |
|---|---|---|
| Login + prototype role selection | ✅ Working | Operator (default) / Supervisor; no authentication (labelled) |
| Supervisor Console + review checkpoint | ✅ Working | Approve / retraining / instructor; append-only; never sets Verified |
| Pre-start checklist gate | ✅ / 🟡 | Works and is tested; lock exists only in the app |
| Live telemetry | 🟡 Simulated | `data.live_reading`; not persisted |
| Live safety alerts (5 types) | ✅ logic · 🟡 input | Thresholds and banners tested; sensors simulated |
| Edge-triggered alert log + expander state | ✅ Working | New; unit/E2E + browser checked |
| Proximity radar | ✅ / 🟡 | Real rendering of simulated objects |
| "Seatbelt interlock" | 🟡 UI message | No machine control |
| Site-condition rules | ✅ | Manual inputs |
| Fatigue risk indicator | ✅ / 🟡 | Rule-based operational indicator; shift hours from demo sliders; not medical |
| Incident logging | ✅ Working | Local only; no notification (not auto-tested; used in rehearsal) |
| My Day task dashboard | ⚠️ Partial | Works; task list not re-generated per day (date issue) |
| Task-time model | ✅ Working | Synthetic evaluation: MAE 12.27 vs 24.31 min |
| Task explanations / what-if / CSV | ✅ Working | Indicative explanations; CSV uses defaults for missing columns |
| Anomaly detector | ✅ Working (historical) | Recall 80% on synthetic idle/fuel labels; weak on speed events; not live |
| Machine Insights idle cost / CO₂ | ✅ | Based on assumed 3.5 L/h, ₹95/L, 2.68 kg/L |
| Maintenance estimate | 🟡 | Seeded service history |
| Competency scoring | ✅ Working | Written standards, tested |
| Closed loop: diagnose → recommend → train | ✅ Working | Tested end to end |
| Closed loop: verify / adapt on history | ✅ / 🟡 | Real statistics on seeded synthetic effects |
| Closed loop: verify a training done today | ⚠️ Partial | Stays "Monitoring 0/8": new sessions are never recorded |
| Training Hub lessons, quiz, certificate | ✅ Working | YouTube lessons need internet |
| Scenario simulator, instructor booking | ✅ Working | No notification for bookings; not auto-tested |
| Ask Assistant (offline) | ✅ Working | Rule-based router; tested |
| Ask Assistant (Claude phrasing) | 🔍 Needs verification | Fallback tested; real call not made |
| End-of-shift report + logout | ✅ Working | Shift length from demo slider |
| Light / Dark theme | ✅ Working | Dark tables in Light mode |
| Launcher (`.bat`) | 🔍 Needs verification | Not re-tested in this audit; double-click test (server window + Edge app window) on the demo laptop |
| Real CAT telemetry / CAN bus | ❌ Not implemented | |
| Physical interlock / machine control | ❌ Not implemented | |
| Supervisor notification | ❌ Not implemented | |
| Persisting live sessions / retraining | ❌ Not implemented | |
| Authentication / multi-user backend / fleet server | ❌ Not implemented | |
| React `web/` frontend, FastAPI backend | ❌ Not implemented | Template/unused packages only |

---

## 23. Known limitations

**Prototype**
- Single Streamlit script; state per browser tab; one operator (or the supervisor) per session; the Supervisor role is a prototype
  role picker without authentication.
- "Today's" tasks are generated once when the DB is created and never re-dated; `todays_tasks()` does not filter by date.
- Shift duration and time since break come from demo sliders; "Log a break" only resets the slider.
- Machine lock, seatbelt interlock and supervisor notification exist only as UI text.

**Data**
- All history synthetic (seed 11); hidden traits drive behaviour; three training effects are seeded; service history,
  incidents #1–2 and task lists are seeded; `visibility_m` and `hours_into_shift` are unused.
- Current `operator.db` contains rehearsal rows (checklists, incidents, D001–D002 Done) and 23 Sep tasks.

**ML**
- Evaluated only on synthetic data; no real-world validation; generator and model share structure.
- No per-prediction uncertainty; fixed hyperparameters; no retraining or model persistence; ~30 s startup training.
- Detector: fixed 5% contamination, weak on single-signal events (speed recall 13.6%), reason vs evidence can disagree,
  validation needs synthetic labels.

**Safety**
- Sensors simulated; thresholds are fixed policy values (15° tilt, 3/6 m, 98 °C, site speed limits), not machine-specific
  engineering limits; no sensor-fault/stale-data detection; no audible alarm; alerts are not persisted; the checklist lock is
  not a real lock; fatigue indicator is not medical.

**Security**
- Role selection is a prototype: anyone can choose Supervisor at login (labelled "authentication/RBAC not implemented").
- No authentication; any operator can be selected. Streamlit listens on all network interfaces by default (no
  `server.address` set), so anyone on the same network can open the app. No encryption of `operator.db`. With a Claude key,
  operator data is sent to the Anthropic API.

**Scalability**
- SQLite single file, full-table reads each rerun, no indexes; models retrained per server start; one machine per operator.

**Deployment**
- Windows launcher only; the minimised server window must stay open; Edge window not verified in this environment;
  `runOnSave = true`; `.venv.broken` (~807 MB) and `wheels/` (~72 MB) inflate the folder.

**UX**
- Light-mode tables stay dark; the MP4's own title card says "2-minute" (it is 42 s); assistant is keyword-based;
  Safety Center shows the last Live Cab reading rather than streaming; alert log is per browser session.

**Integration**
- No telematics, no CAN bus, no dispatch/fleet system, no LMS for training records, no notification channel.

**Validation**
- Training "verification" is before/after association on seeded data, no control group, no multiple-testing correction;
  no user testing with real operators; no field trial.

---

## 24. Hackathon demo flow (operator Ravi, OP1001)

**Before the demo:** clean reset on the presentation day (§20.6); launch; wait ~30 s; Dark theme; sidebar left at defaults
(Sunny, 34 °C, Good, Firm); all demo toggles off. Rehearse once, then reset again.

| Step | Action | What the judge sees | What we say | Technical concept |
|---|---|---|---|---|
| 1 | Log in as Ravi, open Live Cab | 🔒 LOCKED · PRE-START REQUIRED, 8-item inspection | "The machine can't be used in the app until the daily walkaround is complete." | App-level gate, `checklists` log |
| 2 | Tick 5 → submit, then all 8 → submit | Error "remains LOCKED 5/8", then the live cab | "Incomplete inspections are recorded, not ignored." | Every submit persisted; unlock needs 8/8 today |
| 3 | Point at the Live Cab | NORMAL state, task hero with ETA vs planner, radar, telemetry, `SIMULATED TELEMETRY` chip | "This is simulated telemetry; on a real machine it would come from the CAN bus." | Simulator, 2 s fragment, model ETA |
| 4 | Demo controls → Worker approaching | Red "STOP: Worker 1.6 m away at 20°", Why line, radar dot inside 3 m, state CRITICAL | "Every alert says why: value and threshold." | Deterministic proximity rule |
| 5 | Demo controls → Machine on steep slope | Rollover banner + 42 s lesson button; alert log (open it) shows exactly 2 entries and stays open | "Alerts are logged once per event, not every refresh." | Edge-triggered logging |
| 6 | Ask Assistant: "Why is the machine warning me?" → "What should I do?" → "What training should I take?" → "What happens after training?" | Tilt/worker evidence → actions → terrain lesson (31/100 gap) → Monitoring/verify/escalate rules | "The assistant answers from the app's own data, offline; follow-ups use context." | Intent router + follow-up context; Claude optional, rephrase only |
| 7 | My Day; change sidebar weather to Rainy | ETAs rise; "Why this estimate?" factor table | "The model knows weather, soil, slope, skill and Ravi's past pace; the planner doesn't." | HistGradientBoosting, substitution explanations |
| 8 | Task Estimator | MAE 12.3 vs 24.3 min, 49.5% (CI 43.5–54.9%), evaluation tab scatter | "Measured on later, held-out synthetic sessions, with a confidence interval; 40–55% across seeds." | Temporal split, bootstrap, baselines |
| 9 | Machine Insights → inspect a flagged EXC001 session → validation expander | Evidence vs Ravi's own and site baselines; "80% of injected idle/fuel anomalies flagged" | "80% is recall on synthetic labels, not accuracy; precision is 61.5%." | Isolation Forest on robust z-scores |
| 10 | My Skill Profile | Terrain 31/100 gap with evidence; Fuel loop Verified 26.7% → 80% (p < 0.001), labelled seeded history | "Scores are the share of sessions meeting a written standard; verification is a statistical before/after check." | Competency standards, Fisher + Mann–Whitney |
| 11 | Training Hub → Recommended now → Open lesson → play the 42 s MP4 → answer the 3 questions (2nd option each) → Submit | Passed, certificate, loop card "NEW · completed this session", VERIFY Monitoring 0/8 | "We don't claim success yet: it needs 8 new sessions; live sessions aren't saved in this prototype." | Closed loop, honesty |
| 12 | (Optional) End shift → Log out → log in as Priya → My Skill Profile | Fuel loop "escalate to instructor coaching" (30% → 20%, p = 0.88) | "When training doesn't work, the system says so and escalates." | ADAPT stage |
| 13 | End shift & report → Download → Log out | Markdown report: tasks, alerts, fatigue, skills, training loops | "A shift summary the operator or supervisor can keep." | Report, logout keeps theme |
| (opt.) | End shift → Log out → Select role: Supervisor → Open Supervisor Console → Training Reviews → Review Ravi → Approved → APPROVE & START MONITORING → Log out → Ravi → My Skill Profile | Pending review with why/quiz; after approval "✓ SUPERVISOR APPROVED" + "Monitoring 0/8", never Verified | "A supervisor confirms the training; only later behaviour can verify it." | Human checkpoint vs statistical verification |
| (opt.) | Display → Light | Same layout, light tokens | "Readable in bright cabs." | CSS tokens |

Keep the minimised server window open throughout.

---

## 25. Judge Q&A

### Architecture
- **Why Streamlit?** Fastest way to build a complete, interactive, Python-native operator app in a hackathon; the ML stack is
  Python. *Detail:* fragments give a 2 s live refresh without a separate frontend; a production HMI would be native/embedded.
- **Why SQLite?** Zero-install, offline, one file, enough for one machine. *Detail:* the data layer is isolated in `data.py`;
  swapping to Postgres or an edge store is a contained change.
- **Why offline-first?** Cabs and remote sites often lack connectivity; safety features must not depend on the network.
  *Detail:* only YouTube lessons and optional Claude phrasing need the internet.
- **Why no backend?** One operator, one machine, one device; a backend adds failure points. *Detail:* a fleet version would
  sync sessions/training records to a server; that is not built.

### ML
- **Why gradient boosting?** Strong on small tabular data with mixed categorical/numeric features, handles missing values
  (new operators without pace history) natively, fast. *Detail:* `HistGradientBoostingRegressor`, 300 iterations, lr 0.06.
- **Why Isolation Forest?** Unsupervised (real incidents are rarely labelled), handles several signals jointly, cheap.
  *Detail:* robust z-scores within machine type so an excavator isn't compared with a truck; explained per signal.
- **Features?** Task-time: task type, weather, skill, machine age, machine type, soil, temperature, slope, volume, operator's
  past pace. Anomaly: idle share, fuel/working hour, cycles/hour, speed vs limit, max tilt, engine temperature.
- **Validation?** Temporal split (train 10 Jul–7 Sep, test 8–22 Sep), planner and task-type baselines, 1,000-sample
  bootstrap CI, 5 generator seeds; detector checked against injected labels.
- **Metrics?** MAE 12.27 vs planner 24.31 min (49.5%, CI 43.5–54.9%; 40–55% across seeds). Detector recall 80% (48/60),
  precision 61.5%, speed-event recall 13.6%. All synthetic.
- **Leakage?** Only pre-task inputs; pace from strictly earlier days; temporal split; OOF grouped by day; tested.
- **Missing data?** Pace NaN is handled natively by the booster; unknown categories are ignored by the encoder; CSV uploads
  get stated defaults.
- **Does it retrain?** No. Models train at startup on the stored history; new app activity is not fed back. Retraining on
  persisted sessions is on the roadmap.

### Safety
- **Real sensors?** No. Telemetry is simulated by `data.live_reading`; the rules would be the same on real signals.
- **Connectivity lost?** Nothing changes: alerts, rules, models and the assistant run locally.
- **False alarms?** In normal simulated operation no alert fires (objects ≥ 7 m, tilt ~4°); thresholds have caution/stop
  bands; each alert is logged once per event. Real sensors would need debounce and fault detection.
- **Why deterministic rules?** Safety actions must be predictable, explainable and testable; ML is used for estimates and
  pattern-finding, not for stop/go decisions.

### Training
- **How do you know an operator needs training?** A competency score below 70: fewer than 70% of their recent applicable
  sessions met a written standard, with evidence counts.
- **Personalised how?** The gap picks the lesson (terrain → slope lesson, fuel → idle lesson…); the recommendation card cites
  the operator's own numbers.
- **How do you know it worked?** Sessions after training are compared with the 30 before (Fisher exact on pass rate,
  Mann–Whitney on the key metric); ≥ 8 post sessions required.
- **Why Fisher exact?** Small counts (8–30 sessions) where chi-square approximations are unreliable.
- **Why Mann–Whitney?** Behaviour metrics (idle share, tilt excess) are skewed; it needs no normality assumption.
- **No improvement?** After 15 post-training sessions without a significant change, the loop escalates to instructor
  coaching (Priya's case).
- **Is that causal?** No: it is before/after evidence without a control group; in this prototype the effect was seeded.

### Data
- **Why synthetic?** Allowed by the organisers; no real CAT data was available. It's designed with unobserved factors and noise
  so the model can't be perfect, and with labels so the detector can be validated.
- **With real CAT data?** Map telematics fields to the `sessions` schema (the organisers' 9 + 7 columns are already the core),
  retrain, and validate on real history.
- **Telemetry needed?** Seatbelt switch, inclinometer, ground speed, engine hours/rpm/coolant, fuel rate, load cycles/payload,
  idle time, proximity/object detection, GPS/site, task start/end.

### Production
- **Deploy on a machine?** Package as an in-cab app on an industrial tablet/display; read signals from the machine gateway;
  store sessions locally; sync when connected. Not built.
- **CAN bus / telematics?** Replace `live_reading` with a J1939/CAN or telematics-API adapter producing the same dict; roll
  readings into sessions. Not built.
- **Security?** Operator authentication (badge/PIN), encrypted local store, bind to localhost, signed updates, API key in a
  secure store. Not built.
- **Fleet scale?** Central store for sessions, training records and models; per-site standards; scheduled retraining and
  monitoring. Not built.

### Novelty
- **What is novel?** The closed, verified training loop at the operator level: gap from written standards → targeted lesson
  → statistical before/after verification → escalate when training fails, all visible to the operator with evidence.
- **Why not just a dashboard?** It acts: gates the machine in the app, explains alerts, recommends and delivers training, and
  checks whether it worked.
- **Why not just anomaly detection?** Anomalies are one input; competencies use explicit standards and feed training.
- **What differentiates the training loop?** It measures *outcomes* (behaviour in later sessions), not just completion, and
  admits failure.

---

## 26. Future roadmap

**Current prototype (works now):** everything marked ✅ in §22, on simulated/synthetic data.

**Near-term (realistic next steps):**
- Persist Live Cab sessions (aggregate readings per task into `sessions`) so new trainings can be verified.
- Re-generate or date-filter today's tasks; real shift clock and break logging.
- Retrain models on a schedule; per-prediction intervals (e.g. quantile boosting).
- Align anomaly `reason` and evidence ranking; debounce/hysteresis for live alerts; persist alerts.
- Local operator PIN; bind Streamlit to localhost; tidy `requirements.txt`; remove legacy folders.
- Tests for incident form, booking, simulator and CSV upload; a real-key Claude check.

**Production (for actual CAT deployment):**
- Telemetry integration (CAN/J1939 gateway or CAT telematics), sensor validation, real interlock only via certified machine
  systems, supervisor notifications, fleet backend and sync, LMS integration, security review, functional-safety review,
  field validation with real operators and controlled training evaluations.

None of the roadmap items are implemented.

---

## 27. Executive summary

- **What we built:** a standalone, offline-first operator assistant covering every challenge requirement: task dashboard,
  live safety, incident logging, working conditions, training hub, unusual-usage detection and task-time estimation.
- **How it works:** synthetic history in SQLite → feature engineering → a gradient-boosting task-time model and an Isolation
  Forest anomaly detector → written competency standards → a closed training loop with statistical verification → an
  explainable operator UI and an offline assistant; live safety runs on deterministic rules over simulated telemetry.
- **Why it matters:** it turns machine data into specific training and checks whether that training changed behaviour, while
  keeping the operator safe with explained alerts.
- **Genuinely implemented:** all rules, models, statistics, the loop logic, persistence of operator actions, the assistant,
  the UI, the prototype Supervisor Console and 160 passing automated checks.
- **Simulated:** live telemetry, all historical data, the three past training effects, service history, today's tasks.
- **Remaining:** real telemetry, live-session persistence (so today's training can be verified), machine interlock,
  notifications, authentication, fleet backend.

**30-second explanation**
> "CAT Operator Assistant is an offline in-cab companion. It gates the machine behind the daily inspection, explains every
> safety alert, and plans the day with a task-time model that halves the planner's error on our held-out synthetic data.
> Its core idea is a closed training loop: it spots a skill gap from the operator's own sessions, delivers a matched lesson,
> and then checks statistically whether behaviour actually improved, or escalates to a coach if it didn't."

**1-minute explanation**
> "Operators get lots of data but little help turning it into better, safer work. Our assistant runs fully offline on the
> operator's device. In the Live Cab it locks the app until the pre-start inspection is complete, then watches seatbelt,
> proximity, tilt, speed and engine temperature, and each alert says why and what to do; telemetry is simulated in this
> prototype. My Day uses a gradient-boosting model trained on past sessions and today's conditions; on later, held-out
> synthetic data its error is 12 minutes versus 24 for the planner. An Isolation Forest flags unusual sessions with evidence
> against the operator's and the site's baselines. Then the closed loop: every session is checked against written standards,
> a score below 70 is a gap, the gap picks a lesson, and after training we compare sessions before and after with Fisher and
> Mann–Whitney tests. We show a verified improvement, a training that didn't work and was escalated, and we never claim
> success before the data exists. An assistant answers questions from all of this, even without internet."

---

## 28. Changes since the previous handover and final quality check

### 28.1 Changes in the final development passes (now reflected here)
1. **Edge-triggered alert logging** (`live_panel`, `alert_active`): fixes the alert log growing on every 2 s refresh
   (observed 14 → 96 → 172 in about a minute with worker + tilt). One entry per condition onset; independent per type.
2. **Alert-log expander keeps its state** across refreshes (`key="alert_log_exp"`, `alert_log_open`).
3. **Natural-language assistant** with follow-up context, clarification question, offline scope message; Claude restricted to
   rephrasing retrieved facts, with SDK server-side fallback and local fallback on any error.
4. **Light/Dark theme** (session-only; Dark default; config file unchanged).
5. **Logout fix:** the report stays open across reruns; **Back to shift** / **Log out** use callbacks; logout keeps the theme.
6. **HMI refinements:** Live Cab hero task card + state panel + full-width banners; Safety Center "What to do now"; Training Hub
   "Recommended now" card; Skill Profile shows the loop before the radar.
7. **Wording:** "Hello, {name}", "Estimated finish if started now", "Service estimate · N engine hours remaining",
   "Estimated idling cost" / "Estimated CO₂ from idling", "Unusual operation patterns (30 days)", "Site & operating context",
   singular/plural gap chips, terrain lesson "42 sec".
8. **Tests added:** `tests/test_final_ui.py` (25 checks), `tests/test_alert_log.py` (13 checks).
9. **Launcher:** explicit Edge install paths with default-browser fallback.

10. **Prototype roles + Supervisor Console** (later on 24 Sep): role selection at login, isolated supervisor interface
    (Dashboard, Training Reviews, Operators, Outcomes, Coaching & Bookings), `supervision.py`, additive `supervisor_reviews`
    table, review states on the operator's loop cards, shared `booking_form`, second-precision training timestamps,
    `tests/test_supervision.py` (13) and `tests/test_supervisor_ui.py` (51). `skills.py`/`analytics.py` unchanged.

### 28.2 Issues found during this audit (documented, not fixed; development is frozen)
- `todays_tasks()` does not filter by date; tasks are dated the DB creation day.
- Anomaly `reason` and evidence ranking can highlight different signals.
- `training_videos/README.txt` describes a "Site videos (offline)" section that doesn't exist.
- `CLAUDE.md` mentions a `main.py` API and a `web/` frontend that are not part of the product.
- `imageio-ffmpeg` (needed only by `tools/make_offline_lesson.py`) is not installed.
- `visibility_m` and `hours_into_shift` are generated but unused.
- `requirements.txt` includes unused FastAPI/uvicorn.

### 28.3 Final quality check
| Check | Result |
|---|---|
| Every documented feature exists in the current code | ✅ checked against `app.py`, `data.py`, `analytics.py`, `skills.py` |
| Documented tables/columns exist | ✅ from `PRAGMA table_info` on the current DB |
| ML features/hyperparameters match the code | ✅ `TIME_FEATURES`, `_new_model`, `ANOMALY_FEATURES`, `IsolationForest(contamination=0.05)` |
| Screens/buttons exist | ✅ labels quoted from the code; pages opened by AppTest |
| Metrics recalculated from the current implementation | ✅ model, detector, competencies, loops, seeds 11–15 recomputed on 24 Sep; responsive-layout checks marked *previously documented* |
| Demo flow can be performed | ✅ every step is covered by the E2E suites or was exercised in the browser; step 12 (Priya) follows from the recomputed loop verdict |
| Synthetic/simulated items labelled | ✅ throughout (§1.8, §6–§8, §14, §22) |
| Recent changes identified | ✅ §28.1 |
| Unverifiable items marked | 🔍 Claude real call, Edge launcher window, offline wheel install |
