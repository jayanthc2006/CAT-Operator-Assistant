# CAT Operator Assistant: presentation copy sheet

Deck: https://claude.ai/artifact/D8wg3wGMJtgTPV94QjxQJk (15 main slides + 4 backup, speaker notes on every slide).
Updated 24 Sep 2026 for the prototype roles + Supervisor Console (new slide 10; 160 automated checks).
Source of truth: `HANDOVER.md` (audit of 24 Sep 2026). Screenshots in `presentation/screens/` are real app captures
from a fresh database (offline, no API key, demo toggles on where stated).

---

## 0. Before you present (read this first)

1. **Reset the database on the presentation day, on a weekday (Mon–Fri).** Stop the app, delete `operator.db`, and launch the `.bat`.
   The synthetic history is dated relative to the day it's created. Resetting on a **Saturday or Sunday** gives a different dataset
   (1,574 sessions, 52.3% MAE reduction, Ravi's terrain score 23.5), and then slides 6, 7 and B2 would be wrong.
2. **After the reset, log in as Priya (OP1004) and check My Skill Profile.** Her verdict is always **escalate to coaching**, but her
   percentages depend on the reset weekday:

   | Reset day | Priya: fuel before → after | Fisher p | Verdict |
   |---|---|---|---|
   | Wed, Mon*, Tue | 30.0% → 20.0% | 0.88 | Escalate (matches slide 9) |
   | Thu | 23.3% → 30.0% | 0.39 | Escalate: **edit slide 9** |
   | Fri | 23.3% → 33.3% | 0.28 | Escalate: **edit slide 9** |

   *On a Monday reset, Anita's row also changes to 66.7% → 93.3% (p = 0.011), still Verified.
   Everything else on the slides (model, detector, Ravi's loops) is identical for any weekday reset. This was checked for 23 Sep – 1 Oct.
3. **Assistant phrasing:** the router is keyword-based. Use the tested questions (slide 12 / backup B4).
   "How am I performing?" is **not** understood; say "What should I improve?" instead.
4. **The terrain MP4's title card says "2-minute micro-lesson"; the video is 42 s.** If it's visible, say "the title card is outdated, it's 42 seconds".
5. **Keep the minimised server window open.** First load takes about 30 s.
6. **Slide 8's title was changed on purpose.** Your brief said "Detection Is Not the End. Training Is." That literally says training *is*
   the end, which contradicts our novelty. The slide says **"Detection is not the end. Neither is 'training completed'."** Revert it if you prefer.
7. **Fill the placeholders on slide 1:** `[Team name] · [Presenter names]`.
8. The artifact link is private until you share it from the page's Share menu.
9. **Login now starts with Select role.** Operator is the default, so the operator demo is unchanged (Start shift is still the only
   button). For the supervisor part choose **Supervisor → Open Supervisor Console**. It's a prototype role picker: say so if asked.
10. **After the reset, the review queue is empty** until an operator passes a quiz in the app. The seeded Ravi/Anita/Priya trainings
   are exempt from review ("seeded history"), so do the operator quiz first if you want to demo a review.

---

## 1. Recommended timing

| Format | Plan |
|---|---|
| **8 min talk (recommended)** | S1 0:15 · S2 0:35 · S3 0:35 · S4 0:45 · S5 0:45 · S6 0:50 · S7 0:50 · **S8 1:00** · **S9 0:55** · **S10 0:45** · S11 0:40 · S12 0:40 · S13 0:30 · S14 0:35 · S15 0:35 → ≈ 9:55 incl. transitions; trim S3/S11/S12 to hit 8–9 min |
| **5 min talk** | S1, S2, S4, S5 (15 s), S6 (30 s), S8, S9, S10 (30 s), S14, S15; show S7/S11/S12/S13 only if asked |
| **10–12 min with live demo** | S1–S3 (1:30) → live demo from B4 (5:00) → S8, S9, S10 (2:40) → S13, S14, S15 (1:30) |

Spend the most time on **S8, S9 and S10**. They are the climax: the loop, how it's verified, and the human checkpoint.

---

## 2. Slide-by-slide copy

### Slide 1: Title
**A. On the slide:** CAT Operator Assistant · "An offline-first digital co-pilot for safer, smarter heavy-machine operations" · badges SAFETY / EFFICIENCY / TRAINING / OFFLINE-FIRST · footer "Prototype · simulated telemetry · synthetic data".
**Visual:** CAT-yellow excavator line drawing with a small in-cab screen, faint proximity-radar rings, a red worker dot.
**B. Say (15 s):** "Hi, we're [team]. We built CAT Operator Assistant: an offline-first co-pilot for the machine operator. It keeps them safe in the cab, plans their day, and turns their own machine data into targeted training, and then checks whether that training actually worked."
**C. Know:** Standalone Python/Streamlit/SQLite app; runs offline; launched as an Edge app window.
**D. Judge Q&A**
- *Is this connected to a real CAT machine?* "No. It uses simulated telemetry. The architecture isolates the source in one function (`live_reading`), so it can later be replaced by a CAN/J1939 or CAT telematics adapter. We label simulated data rather than claim a machine connection."

### Slide 2: The problem
**A.** "Telematics tells you what happened. Who helps the operator improve?" · grey row: Machine data → Idle, alerts, behaviour → Dashboards & reports → "Something happened." · yellow row: Why did it happen? / Which skill gap caused it? / What should the operator learn? / Did the training actually work? · "CAT Operator Assistant closes this loop."
**B. Say (35 s):** "Machines already produce a lot of data. Telematics can tell a site that an operator idled 30% of the time or triggered tilt alerts. But that usually stops at 'something happened'. It doesn't say which skill gap caused it or what the operator should learn, and nobody checks whether the training changed behaviour. Training gets marked 'completed' and that's it. Our assistant closes that loop."
**C.** Keep it non-technical. The question row sets up slides 8–9.
**D.**
- *Doesn't CAT already do this?* "Telematics platforms are strong at monitoring. Our focus is the operator-level loop: explicit standards, a matched lesson, and a statistical check afterwards. We're not claiming nobody tracks training; we're showing a prototype that verifies training *outcomes* from behaviour."
- *Who is the user?* "The operator in the cab. Supervisors and trainers benefit from the report, incident log and training record, and a prototype Supervisor role reviews completed trainings (slide 10). There are no notifications yet."

### Slide 3: Our solution
**A.** "One operator HMI. One closed loop." · DATA → SAFETY → INSIGHTS → **SKILL GAP → TRAINING → VERIFY → ADAPT** · 9 module cards · "Runs locally · offline-first · operator + supervisor roles (prototype)".
**B. Say (35 s):** "Everything lives in one operator app. The top row is the story of the deck: data comes in, we keep the operator safe, we turn history into insights. The yellow part is what we're proudest of: find a skill gap, deliver matched training, verify it from later sessions and adapt. It all runs locally, so it keeps working without connectivity."
**C.** 8 navigation pages + end-of-shift report. Covers every brief requirement: task dashboard, seatbelt, proximity, incidents, working conditions, training hub, unusual usage, task-time estimation.
**D.**
- *Why Streamlit?* "Fastest way to build a complete, interactive, Python-native app in a hackathon. A production in-cab HMI would be native or embedded."
- *Why nine screens?* "One per job the operator does: drive safely, plan, report, learn."

### Slide 4: In-cab HMI
**A.** "Designed around the operator" · HMI = Human–Machine Interface · 7 highlights · Live Cab screenshot (CRITICAL state) · dashed note "Prototype: runs locally (Streamlit) on a laptop/tablet with simulated telemetry. Not connected to a CAT machine."
**B. Say (45 s):** "HMI means human–machine interface: the screen the operator looks at in the cab. Before the shift, the Live Cab stays locked until the 8-point walkaround inspection is complete. Then the operator sees one task card with the model's ETA, and one big state: NORMAL, CAUTION or CRITICAL. Here we triggered two simulated events: a worker 1.6 m away and a 23° tilt. Each banner says what's wrong, why, and what to do, and the tilt alert links to a 42-second slope lesson. Below: the 360° proximity radar, critical telemetry and a fatigue-risk indicator. Note the 'simulated telemetry' chip."
**C.** 2 s refresh (Streamlit fragment). Fatigue-risk indicator: rule-based points for shift > 6 h (+10/h, max 40), > 2 h since break (+12/h, max 36), heat > 32 °C (+2/°C, max 16), alerts this shift (+4 each, max 20); Low < 30 ≤ Elevated < 60 ≤ High; **operational, not medical**. Shift hours come from demo sliders. Checklist lock is app-level; each submit is logged; 8/8 needed.
**D.**
- *Is the machine really locked?* "No. The app gates the Live Cab until the inspection is complete. A physical interlock would need certified machine safety systems; it's on the roadmap."
- *How do you detect fatigue?* "We don't detect it medically. It's a transparent points indicator from shift time, breaks, heat and alerts, labelled 'not a medical assessment'."
- *Why a laptop?* "It's the prototype platform; the intended deployment is an in-cab display."

### Slide 5: Safety system
**A.** Pipeline: Simulated telemetry → Deterministic rules → Severity → "Why" explanation → Operator action → Event log · 5-alert table · edge-triggered log visual (naive: every 2 s vs ours: once per event) · amber note "App-level interlock only: the prototype does not physically lock hydraulics."
**B. Say (45 s):** "Safety is deliberately not machine learning: stop/go decisions must be predictable and testable. Five live alerts, each with a severity, a 'why' line with the value and threshold, and an action. One engineering detail: the screen refreshes every two seconds, and a naive design logs the same alert every refresh. We caught that in stress testing, when the log went from 14 to 172 entries in about a minute. Now we log on the transition: once when a condition starts, again only if it clears and returns. Worker plus tilt held for a minute gives exactly two entries."
**C.** Thresholds: seatbelt open = CRITICAL; proximity < 3 m CRITICAL (STOP), 3–6 m CAUTION; tilt > 15° CRITICAL; speed > site limit CAUTION (Excavator 6, Wheel Loader 25, Dozer 10, Articulated Truck 40, Motor Grader 30 km/h); engine coolant > 98 °C CAUTION. Normal simulated operation fires nothing (objects ≥ 7 m, tilt ≈ 4°). Proximity amber/red count as one condition. 13 alert-log tests. No live overload alert.
**D.**
- *False alarms?* "Normal operation fires nothing, there are caution and stop bands, and each event logs once. Real sensors would need debounce and sensor-fault checks."
- *Why not ML for safety?* "Deterministic rules are auditable and predictable. ML is used for estimates and pattern-finding, not stop/go."
- *What if connectivity is lost?* "Nothing changes: all rules run locally."
- *Are alerts saved?* "Per shift in the session and in the report; not in the database. That's a roadmap item."

### Slide 6: Task-time intelligence
**A.** "From planner estimates to data-driven ETAs" · bars: Planner 24.31 min vs Our model 12.27 min · "49.5% lower MAE than the planner, on our held-out synthetic evaluation · CI 43.5–54.9% · 40–55% across 5 seeds" · 42.4% vs 14.8% within ±10% · MAPE 16.1% vs 28.7% · 1,238 → 311 temporal split · estimator screenshot · 10 inputs.
**B. Say (50 s):** "The planner estimates from a standard rate and soil. Our gradient-boosting model uses ten inputs known before the task starts, including weather, slope and the operator's own past pace from earlier days. We trained on the first 1,238 sessions and tested on 311 later ones it had never seen. On that held-out synthetic test set, MAE drops from 24.3 to 12.3 minutes: 49.5% lower, confidence interval 43.5 to 54.9%, and 40 to 55% across five generator seeds. 42% of tasks land within ±10% of the actual time, versus 15% for the planner."
**C.** Split: first 80% of days / last 20% (10 Jul–7 Sep vs 8–22 Sep for a DB created 23 Sep; dates shift with the reset day). Task-type median baseline 30.70 min. Oracle (generator formula) 10.21 min. Bias −1.7 vs −24.0 min. Hyperparameters max_iter 300, lr 0.06, min_samples_leaf 20, random_state 0. Importance: volume 40.5%, task type 38.4%, soil 10.3%, skill 5.4%, weather 2.7%. OOF (GroupKFold by day) MAE 12.03. Explanations are substitution-based, indicative, not causal. Only a global ±12 min error, no per-prediction interval. Model trained at startup, not persisted, not retrained.
**D.**
- *Leakage?* "Only pre-task inputs; no idle, fuel, cycles or alerts. Past pace uses strictly earlier days. Temporal split. Unit tests check all three."
- *Why gradient boosting?* "Strong on small mixed tabular data, handles missing pace for new operators natively, fast."
- *Isn't the planner a straw man?* "It's what a planning sheet does: rate × soil plus a rain/fog allowance. We also beat a task-type median (30.7 min), and we report the oracle limit (10.2 min)."
- *Missing data?* "Missing pace is handled natively; unknown categories are ignored; CSV uploads get stated defaults."
- *Would it work on real CAT data?* "Unknown until validated on real history. This is a synthetic evaluation."

### Slide 7: Unusual machine behaviour
**A.** "Not just an anomaly score: evidence" · 6 signals → Isolation Forest → evidence · evidence screenshot (idle 59% vs 19% operator / 13% site) · 78 of 1,549 flagged (5%) · 80% recall on injected idle/fuel (48/60) · 61.5% precision · 13.6% speed-only recall (known limitation) · "Historical sessions, not live · synthetic labels".
**B. Say (50 s):** "An Isolation Forest keeps splitting the data at random; sessions isolated in very few splits are the strange ones. Six signals per session, normalised within each machine type, and the 5% most unusual are flagged. A score alone isn't useful to an operator, so every flag gets evidence: this session's idle was 59%, against 19% for this operator and 13% for the site, plus a recommendation. Because the data is synthetic, we know where we injected anomalies: it catches 80% of the idle/fuel ones with 61.5% precision. It's weak on speed-only spikes, 13.6%, and we say so."
**C.** `IsolationForest(contamination=0.05, random_state=0)`, 100 trees. Robust z = (x − median)/(1.4826·MAD) within machine type. Reason = top 2 signals with |z| ≥ 2; evidence = top 3 by deviation from the site median; baselines exclude the session. Runs once at startup; not live, not persisted, doesn't feed training. In-app "flags with known cause 75.6%" is **not** precision. Seeds 11–15 recall 69–80%. Quirk: the one-line reason and the evidence ranking can highlight different signals.
**D.**
- *Why unsupervised?* "Real incidents are rarely labelled. Unsupervised plus evidence is a practical start."
- *Why is speed recall low?* "Speed events are single-signal spikes; the forest isolates multi-signal outliers better. A simple speed rule already covers it live."
- *Is 80% your accuracy?* "No, it's recall on injected idle/fuel anomalies in synthetic data."
- *Live?* "No, it runs on historical sessions."

### Slide 8: The core differentiator (yellow)
**A.** "Detection is not the end. Neither is 'training completed'." · loop 1 OBSERVE → 2 SCORE → 3 IDENTIFY GAP → 4 TRAIN → 5 VERIFY → 6 ADAPT · centre: "Did the operator actually improve?" · "Our main novelty: a closed, verified operator-training loop".
**B. Say (60 s, slow):** "This is the heart of the project. Most systems stop at detection. Some assign training, tick 'completed', and stop. We observe every session, score it against a written standard, for example idle at most 20% of the session; a competency score is the share of your last 30 sessions that met it. Below 70 is a gap. The gap picks a matched lesson and a three-question quiz. Then the difference: we compare the operator's later sessions with the ones before, statistically, and adapt: verified, keep monitoring, or escalate to an instructor. The question isn't 'did they finish the course', it's 'did the operator actually improve?'"
**C.** 6 competencies: Safety discipline (belt + speed ≤ limit + no overload), Fuel efficiency (idle ≤ 20% and fuel ≤ 120% of rated), Cycle efficiency (≥ 85% of rated 10 m³/cycle), Machine handling (no harsh events), Terrain handling (slopes ≥ 5°: tilt ≤ 15°, ≤ 7° above slope, ≤ 95% speed limit), Task execution (≤ 120% of model-expected time; coaching, no lesson). ≥ 8 applicable sessions needed. Gap < 70. Pass mark 2/3 (≥ 66%). Standards are explicit policy, not learned. Ravi terrain 31/100 (16 slope sessions: 4 tilt > 15°, 5 > 7° above slope, 9 over 95% of the limit).
**D.**
- *Why 70?* "An explicit, adjustable policy threshold; a site safety manager would set it."
- *How is training personalised?* "The gap chooses the lesson, and the recommendation cites the operator's own numbers."
- *What's actually novel?* "Measuring outcomes (behaviour in later sessions), not completion, and admitting failure by escalating."

### Slide 9: How we verify training
**A.** "We don't count training completion as success" · Fisher exact / Mann–Whitney U cards · Verified p < 0.05 right direction · Monitoring ≥ 8 post sessions · Escalate after 15 · SEEDED SYNTHETIC HISTORY: Ravi fuel 26.7% → 80.0% (p < 0.001) VERIFIED · Anita safety 60.0% → 93.3% (p = 0.002) VERIFIED · Priya fuel 30.0% → 20.0% (p = 0.88) ESCALATE · "No control group… not proof of causality. A training completed today stays at Monitoring 0/8."
**B. Say (55 s):** "We take the 30 sessions before training and up to 30 after. Fisher's exact test asks whether the share meeting the standard went up; Mann–Whitney asks whether the behaviour metric itself moved the right way. Verified means p below 0.05 in the right direction. We need eight sessions before judging; after 15 with no improvement, it escalates to an instructor. On our seeded synthetic history, Ravi and Anita improved and are verified; Priya didn't, so the system escalates her instead of claiming success. These effects were seeded, and with no control group this is before/after evidence, not causality."
**C.** Ravi idle 26.6% → 15.5% (Fisher 3.6e-5, MW 6e-7). Anita unbuckled 33% → 0% (Fisher 0.0024, MW 0.0003). Priya idle 26.7% → 24.2% (MW 0.30). Fisher: small counts (8–30). Mann–Whitney: skewed metrics, no normality. No multiple-testing correction. MW skipped if fewer than 3 distinct values. **Check Priya's row after the reset (section 0).**
**D.**
- *Did training cause the improvement?* "We don't claim that. The prototype found statistically significant before/after improvement in seeded synthetic history. Causality needs a controlled evaluation."
- *Can today's training be verified?* "Not yet: live sessions aren't saved, so it honestly stays at Monitoring 0/8."
- *What if an operator games the quiz?* "The quiz only unlocks monitoring; the verdict comes from behaviour in later sessions."

### Slide 10: Supervisor review (new)
**A.** "A human checkpoint, not a shortcut to 'Verified'" · role flow: OPERATOR observe → diagnose → train (quiz passed) · SUPERVISOR review: approve · retrain · instructor · OPERATOR Monitoring 0/8 · SYSTEM statistics → verified · monitor · escalate · "Supervisor Approved ≠ Statistically Verified" · Supervisor Dashboard screenshot · "Prototype role selection · authentication/RBAC not implemented".
**B. Say (45 s):** "Real sites have supervisors, so we added a separate supervisor role. When an operator passes a lesson, it waits for supervisor review. The supervisor sees why the training was assigned and the quiz result, and decides: approve, request retraining, or recommend an instructor, which uses our booking system. The key point: supervisor approval is not verification. Approval only starts monitoring. Here Ravi's slope training is 'supervisor approved, monitoring 0 of 8', while the two seeded loops are 'verified, statistical'. Only the before/after tests can mark a result verified. The role picker is a prototype: no real authentication yet."
**C.** Roles are chosen at login (Operator default); the operator sidebar still has exactly its 8 pages. Supervisor pages: Dashboard, Training Reviews, Operators, Outcomes, Coaching & Bookings; the supervisor interface never runs operator code. Review panel: operator, why assigned (score + standard + evidence), lesson, quiz score, date, attempts; assessment "Did the operator demonstrate understanding?" (Approved / Needs reinforcement) + note; APPROVE is enabled only for Approved, RETRAIN/INSTRUCTOR only for Needs reinforcement. Retraining keeps the gap open and the score unchanged; the retake is a new case. Instructor → existing `bookings` table. Decisions are append-only in `supervisor_reviews`; the latest wins. Seeded trainings pre-date review. New training stays at Monitoring 0/8 (no sessions are created). Tests: 13 unit + 51 end-to-end.
**D.**
- *Does approval count as verification?* "No. It's a human checkpoint that starts monitoring; Verified comes only from the Fisher and Mann–Whitney tests."
- *Can an operator approve their own training?* "In this prototype anyone can pick the Supervisor role at login; it's labelled, and real authentication is on the roadmap. The operator's own screens have no supervisor controls."
- *What happens after 'request retraining'?* "The gap stays open, the lesson is recommended again, and the next pass becomes a new review case. History is kept."

### Slide 11: Offline-first architecture
**A.** Stack: Telemetry source (simulated today, future CAN/J1939) → Python application logic → SQLite local file → Analytics · ML · Rules → Streamlit operator HMI; optional dashed: Claude API (phrasing only), YouTube (online lessons); tech stack list; "Claude is not the decision-maker".
**B. Say (40 s):** "The whole thing runs on the device. Telemetry comes from our simulator today, later from a CAN/J1939 or telematics adapter. Python holds the logic, SQLite stores everything locally, and the analytics layer holds the models, rules and training loop. Only two optional things touch the internet: YouTube lessons and Claude. If the network drops, nothing important changes, and Claude only rephrases facts the app already retrieved."
**C.** No backend server (FastAPI installed but unused). Models train in memory at startup (~30 s) and are cached, not persisted. `CAT_OPERATOR_DB`, `CAT_OFFLINE=1`. Terrain lesson = local 42 s MP4; 4 Cat® YouTube lessons (key points + quiz still work offline). Claude: `claude-opus-5` with SDK server-side fallback; any error → offline answer. A real Claude call wasn't exercised (no key on the machine).
**D.**
- *Why SQLite?* "Zero install, offline, one file; the data layer is isolated, so moving to a fleet database is contained."
- *Why no backend?* "One operator, one machine, one device. A fleet version would sync to a server; not built."
- *Security?* "Not production-ready: no login, and Streamlit listens on all interfaces. Production: badge/PIN login, encrypted store, bind to localhost, key in a secure store."

### Slide 12: Assistant
**A.** "Ask the system in plain language" · 1 question → 2 rule-based intent router + follow-up context → 3 app facts → 4 optional Claude rephrasing → 5 answer + action button · example chips · real offline conversation screenshot · "Works offline. Claude never invents machine readings, safety decisions, anomaly results or training outcomes."
**B. Say (40 s):** "Operators can just ask. This screenshot is fully offline. 'Why am I getting this warning?' gets the live evidence; 'What should I do?' understands we're still on the alert; 'What training should I take?' recommends the 42-second slope lesson because terrain handling is 31/100, with a button to open it. It's a rule-based intent router retrieving app facts. If a Claude key is configured, Claude only rephrases them."
**C.** 18-step priority router with follow-up context (topic/task/competency/anomaly); unclear follow-up → clarification question; out of scope → "I can help with your machine, safety alerts, tasks, anomalies, skills, training and shift status while offline." Keyword-based, English only. Tested phrasings: "Why is the machine warning me?", "What should I do?", "What's my current tilt?", "How long will my next task take?", "Why is this ETA higher than the planner?", "What looks unusual here?", "Why?", "Why is my terrain score low?", "What training should I take?", "What happens after training?", "How long have I been working?", "What machine am I using?", "What should I improve?". "What is my ETA?" also routes to the ETA answer.
**D.**
- *Why not let the LLM answer?* "Safety and training facts must be exact and auditable. The LLM only gets retrieved facts and a rephrase-only prompt, and the offline answer is always there as a fallback."
- *Is it real NLU?* "No: keyword/regex intent matching with conversational context. Honest, fast and offline."

### Slide 13: Engineering validation
**A.** "Built, tested and audited" · 160 / 160 · 26/26 unit · 13/13 supervisor unit · 32/32 smoke/E2E · 25/25 final UI · 13/13 alert log · 51/51 roles & supervisor flow · temp DBs · offline · no API key · 0 failed, 0 skipped · coverage chips.
**B. Say (30 s):** "This isn't just a UI mock-up: 160 automated checks, all passing, run on temporary databases, offline, with no API key. They cover leakage controls, the temporal split, the checklist gate, the training-loop verdicts, assistant fallbacks, the alert log, and that supervisor approval never marks a result verified."
**C.** Commands: `.venv\Scripts\python.exe -m unittest tests.test_logic`, `tests\smoke_test.py`, `tests\test_final_ui.py`, `tests\test_alert_log.py`. E2E uses Streamlit AppTest. Not covered: a real Claude call, the launcher/Edge window, online YouTube, the incident and booking forms, the simulator, visual layout.
**D.**
- *Tested with real users?* "No, that's field validation on the roadmap."
- *How do you know the metrics are right?* "They were recomputed from the code during a fresh audit, and tests check metric consistency."

### Slide 14: Real vs simulated
**A.** Implemented & tested (11 items) · ◌ Simulated / synthetic (5) · Path to production (8).
**B. Say (35 s):** "We want to be precise about scope. Left: what's genuinely implemented and tested. Middle: what's simulated or synthetic, and the app labels these on screen. Right: the production path. These are the clear boundaries of a hackathon prototype, not hidden gaps."
**C.** Biggest gap = live-session persistence (blocks verifying new training). Security: no auth; Streamlit on all interfaces.
**D.**
- *Biggest gap?* "Saving live sessions. It lets the loop verify new training, and it's the first thing we'd build."
- *What's real if the data is synthetic?* "All the logic: rules, models, evaluation, statistics, loop, storage, UI. Swap the data source and the same code runs."

### Slide 15: Roadmap
**A.** 01 Prototype (today) · 02 Telemetry integration · 03 Sensor validation · 04 Certified interlock · 05 Fleet sync · 06 Supervisor notifications · 07 LMS integration · 08 Field validation · 09 Controlled evaluation · Also: security + functional-safety reviews · "Steps 02–09 are future work".
**B. Say (35 s + close):** "From prototype to deployment: replace the simulator with a CAN/J1939 or telematics adapter, validate sensors, route any interlock through certified safety systems, then fleet sync, notifications, LMS integration, and field validation with a controlled evaluation for causal claims. To close: most systems stop at 'training completed'. Ours asks what matters: did the operator actually improve? Thank you."
**C.** Near-term: persist Live Cab sessions, date-filter today's tasks, scheduled retraining, per-prediction intervals, alert debounce, operator PIN, bind to localhost.
**D.**
- *Deploy on a machine?* "An in-cab display reading the machine gateway, storing sessions locally and syncing when connected. Not built."
- *Scale to a fleet?* "A central store for sessions, training records and models, per-site standards and scheduled retraining."

---

## 3. Backup slides

| Slide | Use when | Content |
|---|---|---|
| **B1 Technical deep dive** | A technical judge asks how anything works | Methods table: model, validation, OOF benchmark, leakage, detector, competencies, verification |
| **B2 Dataset** | "What data did you use?" | 1,549 sessions · 6 operators · 6 machines · 64 working days · 10 Jul – 22 Sep · task-type bars · generation method · **SYNTHETIC** label |
| **B3 Limitations** | "What doesn't work?" | 8 honest limits (no real telemetry, no causal claim, no physical interlock, no live anomaly detection, no retraining, no per-task uncertainty, new training can't be verified, weak on speed-only events) |
| **B4 Live demo path** | You're doing a live demo | 9-step run sheet with exact clicks and phrasings; the optional last card is the supervisor review (approve → Monitoring 0/8) |

---

## 4. Visual guide (what each slide shows)

| Slide | Visual |
|---|---|
| 1 | Custom CAT-yellow excavator line drawing, radar rings, red worker dot; yellow edge stripe |
| 2 | Two rows of cards: grey "what exists" flow vs yellow-edged "what's missing" |
| 3 | 7-stage flow (loop stages in solid yellow) + 3×3 module grid |
| 4 | **Screenshot:** Live Cab, CRITICAL, with SIMULATED TELEMETRY chip; dashed prototype disclaimer |
| 5 | Alert pipeline, alert table (severity in words and colour), naive-vs-edge-triggered log comparison |
| 6 | MAE bar comparison, big "49.5% lower MAE", 3 stat cards, **screenshot:** Task Estimator KPIs |
| 7 | 3-stage flow, **screenshot:** evidence card, 4 big numbers (speed limitation in amber) |
| 8 | Yellow statement slide; 6-node circular loop with clockwise arrows; centre question |
| 9 | Test cards + rules; 3 outcome rows with VERIFIED/ESCALATE pills; SEEDED SYNTHETIC HISTORY tag |
| 10 | Role flow (operator → supervisor → operator → system), "Supervisor Approved ≠ Statistically Verified", **screenshot:** Supervisor Dashboard after approval |
| 11 | Stack diagram with arrows; dashed optional services; tech-stack list |
| 12 | 5-step pipeline, question chips, **screenshot:** real offline conversation |
| 13 | Big "160 / 160", 6 test tiles, coverage chips |
| 14 | Three columns: implemented (yellow top) / simulated (dashed, like the app's SIM chip) / production path |
| 15 | 10-card roadmap grid, "today" in yellow, reviews card dashed |

More real screenshots in `presentation/screens/` (not all used): locked checklist, Live Cab NORMAL, My Day, Skill Profile loop, Training Hub recommendation, Monitoring 0/8 card, end-of-shift report.
Not used on purpose: the lesson player (its title card says "2-minute") and Priya's loop (its numbers are from a Thursday-created DB and differ from slide 9).

---

## 5. NUMBERS I MUST REMEMBER

> **ALL HISTORICAL DATA AND LIVE TELEMETRY ARE SYNTHETIC / SIMULATED IN THIS PROTOTYPE.**

| Number | What it is |
|---|---|
| **1,549** | synthetic work sessions |
| **6 / 6** | operators / machines |
| **64** | working days (10 Jul – 22 Sep 2026, for a weekday reset on 23 Sep; dates move with the reset) |
| **10** | task-time input features, all known before the task |
| **12.27 min** | model MAE (held-out synthetic test) |
| **24.31 min** | planner MAE |
| **49.5%** | lower MAE than the planner |
| **43.5–54.9%** | bootstrap 95% CI of that reduction |
| **40–55%** | reduction across 5 generator seeds |
| **1,238 → 311** | train → later test sessions (temporal split) |
| **42.4% vs 14.8%** | tasks within ±10%: model vs planner |
| **16.1% vs 28.7%** | MAPE: model vs planner |
| **30.70 / 10.21 min** | task-type-median baseline / oracle limit |
| **78** | sessions flagged by the anomaly detector (5%) |
| **80% (48/60)** | recall on injected idle/fuel anomalies |
| **61.5%** | precision against idle/fuel labels |
| **13.6%** | recall on injected speed events (limitation) |
| **6** | anomaly signals; **6** competencies |
| **< 70** | competency gap threshold |
| **30** | sessions per profile window and per before/after side |
| **8** | minimum post-training sessions before a verdict |
| **15** | post-training sessions without improvement → coaching |
| **p < 0.05** | significance, one-sided, correct direction |
| **5** | training lessons (1 offline MP4 of 42 s + 4 Cat® YouTube) |
| **3 / 2 of 3 (66%)** | quiz questions / pass mark |
| **8** | pre-start checklist items (all mandatory) |
| **< 3 m / < 6 m** | proximity STOP / caution |
| **> 15°** | tilt rollover warning |
| **> 98 °C** | engine coolant warning |
| **2 s** | live refresh |
| **31/100** | Ravi's terrain handling (gap) |
| **26.7 → 80.0%** | Ravi fuel loop (verified, seeded) |
| **60.0 → 93.3%** | Anita safety loop (verified, seeded) |
| **30.0 → 20.0%** | Priya fuel loop (escalated, seeded; check after reset) |
| **160** | automated checks: **26 + 13** unit · **32 + 25 + 13 + 51** end-to-end |
| **2** | prototype roles (Operator default, Supervisor); **5** supervisor pages |
| **3** | supervisor decisions: approve · request retraining · recommend instructor |

---

## 6. Claims to avoid

| ❌ Don't say | ✅ Say instead |
|---|---|
| "49.5% more accurate than the planner" | "49.5% lower MAE than the planner on our held-out synthetic test set." |
| "Real-time CAT telemetry" | "Simulated real-time telemetry in the prototype." |
| "The model prevents accidents." | "The prototype applies deterministic safety rules and provides operator alerts." |
| "Training caused the improvement." | "The prototype found statistically significant before/after improvement in seeded synthetic history." |
| "The machine is physically locked until inspection." | "The application gates the Live Cab until the inspection is complete; a physical machine interlock is not implemented." |
| "Isolation Forest detects all unsafe behaviour." | "It detects unusual historical sessions, with the strongest validation on injected idle/fuel anomalies; speed-only events are a known limitation." |
| "80% accuracy" | "80% recall on injected idle/fuel anomalies (synthetic labels)." |
| "The supervisor verified the training." | "The supervisor approved the training; verification comes only from later behaviour (before/after tests)." |
| "We have role-based access control." | "Prototype role selection; authentication/RBAC isn't implemented." |
| "The anomaly detector runs live." | "It runs on historical sessions; live safety uses deterministic rules." |
| "We detect operator fatigue." | "A rule-based fatigue-risk indicator; not a medical assessment." |
| "Supervisors are notified." | "Incidents are logged locally; notifications aren't connected in the prototype." |
| "Claude/AI decides…" | "Deterministic rules and models decide; Claude optionally rephrases retrieved facts." |
| "Today's training is being verified." | "A training completed today stays at Monitoring 0/8, because live sessions aren't saved in this prototype." |
| "Validated on real operators / CAT data." | "Evaluated on synthetic data; field validation is on the roadmap." |
| "The model retrains as it learns." | "Models train at startup; retraining is on the roadmap." |
