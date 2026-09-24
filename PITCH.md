# CAT Operator Assistant: closed-loop operator intelligence and training

## 1. Problem
CAT machines already record rich telemetry, but operators see little of it. Most tools stop at dashboards
("you idled 30%"). They rarely turn the data into targeted training, and they rarely check whether the
training actually changed behaviour.

## 2. Solution
Standalone, offline-first operator software (Streamlit + local SQLite) built around one loop:

**OBSERVE → DIAGNOSE → INTERVENE → TRAIN → VERIFY → ADAPT**

1. **Observe:** each work session (organisers' telemetry and task schemas, plus extra sensor signals) is checked against written standards.
2. **Diagnose:** competency score = share of the operator's last 30 applicable sessions that met the standard, with evidence counts.
3. **Intervene:** a score below 70 is a skill gap, mapped to a specific lesson. Live alerts link straight to the relevant lesson.
4. **Train:** video (offline MP4 or YouTube) + key points + a 3-question knowledge check (pass mark 66%), logged with a certificate.
5. **Verify:** the 30 sessions before training are compared with up to 30 after (one-sided Fisher exact test on the pass rate, Mann–Whitney U on the key metric). A verdict needs at least 8 post-training sessions.
6. **Adapt:** improvement verified → loop closed. No measurable change after 15 sessions → escalate to instructor coaching.

## 3. Requirements mapped to features
| Requirement | Where | What it does |
|---|---|---|
| Daily task dashboard | My Day | Tasks, Start/Complete, planner vs model estimate, "why this estimate" factors, overlap warnings |
| Seatbelt compliance | Live Cab, Safety Center, Skill Profile | Simulated interlock banner, weekly trend, safety-discipline competency |
| Proximity hazards | Live Cab, Safety Center | 360° radar (3 m stop / 6 m caution), history of closest approaches |
| Incident logging | Safety Center | Form saved to SQLite. Live alerts are logged automatically with their sensor evidence |
| Working conditions | All screens | Rain, wind, fog/dust, heat, slope and long-shift rules, plus the fatigue risk indicator |
| Training hub | Training Hub | Closed-loop plan, lessons, knowledge checks, certificates, scenario simulator, instructor booking, training record |
| Unusual behaviour | Machine Insights | Isolation Forest with evidence vs operator and site baselines, plus validation against labelled anomalies |
| Task-time estimation | Task Estimator | Gradient boosting, temporal evaluation against the planner baseline, per-prediction factors |
| Standalone software | `Start Operator Assistant.bat` | Local server + app window. The launcher requires **Microsoft Edge** (it opens `msedge --app=…`). Works with no internet and no API key |

## 4. What is actually implemented vs simulated
- **Implemented:** every model, rule, score, statistical test, the database and the UI flows.
- **Simulated:** all machine data (synthetic history + live readings generated every 2 s). The live-cab "interlock" is a UI banner,
  not a machine control. Idle fuel uses an assumed 3.5 L/h. Service intervals are seeded values.

## 5. ML / data pipeline (the actual techniques)
```
Telemetry + operator + task + environment + machine specs   (SQLite: data.py)
        │
Feature engineering (analytics.enrich): idle share, fuel/work-h, m³/cycle, speed ÷ limit,
tilt above slope, operator's past pace (earlier days only)
        │
├─ Safety rule engine (live alert thresholds, condition warnings)          rules
├─ Anomaly detection                                                        IsolationForest on per-machine-type robust z-scores
├─ Task-time estimation                                                     HistGradientBoostingRegressor
├─ Fatigue risk indicator                                                   transparent point rules (not a medical model)
        │
Decision engine (skills.py): per-session standards → competency scores → skill gaps → lesson
        │
Operator interface → training (lesson + quiz) → training_log
        │
Verification (skills.compare_before_after): Fisher exact + Mann–Whitney → verdict → updated profile
```
The ML uses scikit-learn only; the statistical tests use SciPy. There is no XGBoost, no deep learning and no computer vision.

## 6. Synthetic data methodology
- 1,549 sessions: 75 calendar days (**64 working days**, Sundays off) × 6 operators (one machine each), 3–5 sessions per working day. Includes the organisers' 9 telemetry and 7 task columns.
- **Observable effects** (a model can learn them): task type, volume, soil, weather, skill, machine age, slope, heat.
- **Unobserved effects** (so the target can't be learned exactly): per-operator pace, machine condition, daily site disruption
  (shared by all tasks that day), about 10% log-normal per-task noise, and a 5% chance of a 15–60 min delay.
- **Hidden operator habits** (seatbelt use, idling, slope care, smoothness, bucket fill, speeding) live only in the generator. They
  aren't stored in the database, so skill gaps must be inferred from behaviour.
- **Simulated training effects (synthetic, not real-world evidence):** three past training records are seeded. Two change behaviour afterwards (Ravi: fuel, Anita: safety)
  and one doesn't (Priya: fuel). This exists to demonstrate verification. The effect is synthetic, but the verdict is computed only from the recorded sessions.
- **Labelled anomalies:** `injected_event` marks 60 idle/fuel anomalies (27 idle, 33 idle+fuel; about 4% of sessions) and 66 speed events. This label is used only to validate the detector and is never a model input.

## 7. Model evaluation (task time)
- **Target:** actual minutes. **Inputs:** only information known before a task starts. Idle time, fuel, cycles and alerts are excluded.
- **Split:** temporal. Train on the first 80% of days, test on the last 20%. The deployed model is then refit on all history.
- **Current dataset (seed 11), held-out synthetic test set (311 later sessions):** MAE **12.27 min vs 24.31 min** for the planner baseline → **49.5% lower error (bootstrap 95% CI 43.5–54.9%)**. This is measured on synthetic data, not real machines.
  A task-type median baseline scores 30.7 min.
- **Robustness:** across 5 generator seeds the reduction was **40–55%**, and model MAE stayed at 11.9–13.2 min.
- **Reference point:** a model that knew the generator's observable formula would score **10.21 min**, so the remaining error is the unobserved noise.
- **Superseded claim:** the earlier "72% / ±6 vs ±22 min" came from a random split on data where actual time was an exact formula of the
  inputs plus 7% noise, and the planner ignored five of those inputs by design. It was an artefact of how the data was generated.

## 8. Explainability
- **Live alerts:** each alert shows its sensor evidence ("Inclinometer 18.5° is above the 15° threshold").
- **Anomalies:** each flagged session is compared with the operator's own median and the site median (same machine type, excluding the session),
  shown as percentage deviations, with context and a recommendation.
- **Detector validation (synthetic labels only):** the **80%** figure is **recall** on the 60 injected idle/fuel anomalies (48 flagged).
  **Precision** against those labels is **61.5%** (78 sessions flagged). Recall on the 66 injected speed events is only 13.6%,
  because they are single-signal spikes. The in-app "flags with a known cause" figure (75.6%) is not precision.
- **Predictions:** substitution effects show how many minutes the estimate changes if each input were at its site-typical value, alongside global permutation importance.
- **Competencies:** each score comes with its written standard and the evidence counts behind it.

## 9. Adaptive training loop (verification details)
Loop status is shown as Detected → Training recommended → Training completed → Monitoring (k/8) → Verified, or Adapt: coaching.
On the current synthetic data. The behaviour changes after training were programmed into the generator; the verification logic is real:

| Operator | Result |
|---|---|
| Ravi (fuel) | 26.7% → 80.0% of sessions meeting the standard, p < 0.001 → verified |
| Anita (safety) | 60.0% → 93.3%, p ≈ 0.002 → verified |
| Priya (fuel) | 30% → 20%, not significant → escalated to coaching |
| Newly completed training | Shows "Monitoring 0/8". No improvement is displayed until real post-training sessions exist |

## 10. Operator at the centre
- Personal improvement compares your latest 30 sessions with the 30 before. The named leaderboard has been removed.
- The site comparison is an anonymous median only.
- Milestones use sensor data only, so there's no incentive to under-report incidents.
- The fatigue indicator is explicitly *not* a medical assessment.

## 11. Offline-first
Everything except the YouTube lessons runs locally: login, live cab, alerts, estimator, anomalies, profile, quizzes, reports.
The terrain lesson is a local MP4 (`training_videos/terrain.mp4`, built by `tools/make_offline_lesson.py`). Any `<lesson id>.mp4` placed
in `training_videos/` replaces the YouTube stream. When offline, YouTube lessons fall back to their key points and quiz. The assistant computes
every answer locally; Claude (optional) only rephrases the retrieved data, and a missing key or network is handled.
`CAT_OFFLINE=1` forces offline mode.

## 12. What's different about it
We don't claim the individual pieces are new. The difference is how they're connected: the same session data drives
live alerts, explainable anomaly flags, the competency profile, the choice of lesson and a statistical check of whether the lesson worked.
The operator sees why (evidence), what to do (lesson) and whether it helped (before vs after).

## 13. 3-minute demo (operator Ravi, OP1001)
1. **Log in**, complete the pre-start checklist, and the Live Cab unlocks.
2. **Demo controls → "Machine on steep slope"**: a red rollover alert appears with its reason, plus a button for the terrain lesson.
3. **Ask Assistant: "Why am I getting this warning?"** It answers from the live sensor evidence.
4. **My Day**: change the weather to *Rainy* and the estimates update. Open "Why this estimate?".
5. **Machine Insights**: inspect a flagged session with its evidence table, then open the validation expander.
6. **My Skill Profile**: terrain handling 31/100 (gap) with evidence. Fuel efficiency shows a *verified* earlier loop (27% → 80%).
7. **Training Hub**: play the offline terrain MP4 and pass the knowledge check. The loop moves to *Monitoring 0/8*.
8. **End shift**: the report includes the skill profile and training loop status.

## 14. Limitations and assumptions
- All data is synthetic, and the training effects in history are simulated. Real validation needs field data.
- Standards and thresholds (70 gap line, 20% idle, 15° tilt…) are explicit policy choices, not learned values.
- The fatigue indicator uses unvalidated point rules. The live interlock is a UI signal only.
- Before/after comparisons are observational. Weather or task mix could also change between the two periods.
- Single-operator machine types mean site comparisons use rated specs, not peers.
- Tests: `tests/smoke_test.py` (end-to-end demo, offline, no key) and `tests/test_logic.py` (23 unit tests).
