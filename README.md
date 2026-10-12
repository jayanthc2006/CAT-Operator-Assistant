# CAT Operator Assistant 🚜

**An offline-first operator assistance and safety monitoring prototype built with Python, Streamlit, and SQLite.**

CAT Operator Assistant is a standalone application designed to help equipment operators monitor simulated machine conditions, plan daily tasks, identify unusual machine usage, and receive targeted training recommendations.

The project combines rule-based safety monitoring, machine-learning models, explainable anomaly detection, and a prototype closed-loop training workflow in a locally running application.

> **Prototype notice:** Historical records are synthetic, live machine telemetry is simulated, and historical training outcomes are seeded. This project does not connect to real CAT machinery or control physical machine interlocks.

## Key Features

### 🚧 Live Cab & Safety Monitoring
- Pre-start inspection checklist that gates access to the Live Cab interface.
- Simulated telemetry with proximity radar and threshold-based safety alerts.
- Safety Center for reviewing conditions and recording incidents.
- Rule-based fatigue-risk indicators and working-condition warnings.

### 📋 Task Planning & Time Estimation
- Daily task dashboard with task start and completion workflows.
- Machine-learning-based task-duration estimation using `HistGradientBoostingRegressor`.
- Environmental and task-related features used to estimate completion times.
- Task-estimation insights and comparisons with a planner baseline.

### 📊 Machine Insights & Anomaly Detection
- Isolation Forest for identifying unusual machine-operating patterns.
- Robust z-score-based features for comparing operating signals.
- Evidence-based anomaly explanations using operator and site baselines.
- Machine-usage insights to help investigate unusual idling and operating conditions.

### 🎯 Personalized Training Workflow
- Competency scoring based on recorded operator sessions and defined standards.
- Training recommendations linked to identified skill gaps.
- Lessons, knowledge checks, training records, and a prototype supervisor review workflow.
- Statistical before-and-after comparisons designed to classify outcomes as verified, monitoring, or requiring further coaching.

**Important:** Historical training improvements use seeded synthetic outcomes. Real-world training effectiveness has not been established, and newly completed training cannot yet be verified from newly recorded live sessions.

### 💬 Offline-First Operator Assistant
- A keyword- and pattern-based intent router that answers questions using application data.
- Optional Claude integration for rephrasing retrieved facts.
- Local fallback responses when the optional AI integration is unavailable.

### 💾 Standalone Architecture
- Local Streamlit application.
- SQLite database for supported persistent records.
- Local application launcher for Windows.
- Core application workflows designed to operate without cloud infrastructure.

## Technology Stack

- **Language:** Python
- **Application UI:** Streamlit
- **Database:** SQLite
- **Machine Learning:** scikit-learn, HistGradientBoostingRegressor, Isolation Forest
- **Data Processing:** pandas, NumPy
- **Statistics:** SciPy
- **Visualizations:** Plotly
- **Optional AI Integration:** Anthropic Claude

## Architecture Overview

```text
Simulated Telemetry + Synthetic Historical Data
                    |
                    v
         SQLite Data Layer
                    |
                    v
       Feature Engineering
                    |
          +---------+---------+
          |                   |
          v                   v
    Task-Time Model     Anomaly Detector
          |                   |
          +---------+---------+
                    |
                    v
       Competency & Rule Engines
                    |
                    v
       Streamlit Operator UI
                    |
                    v
       Training & Verification
```

## Getting Started

### Prerequisites
- Python 3.11 or a compatible version supported by the pinned dependencies.
- Git.
- Windows is recommended for the provided `.bat` launcher.

### Installation

Clone the repository:

```bash
git clone https://github.com/jayanthc2006/CAT-Operator-Assistant.git
cd CAT-Operator-Assistant
```

Create and activate a virtual environment on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Run the Application

Start the application using Streamlit:

```bash
streamlit run app.py
```

Alternatively, after setting up the virtual environment and dependencies on Windows, double-click **`Start Operator Assistant.bat`** to launch the application.

## Project Documentation

- [`HANDOVER.md`](HANDOVER.md) — Detailed technical documentation, implementation audit, architecture, evaluation, and limitations.
- [`PITCH.md`](PITCH.md) — Project problem statement, solution workflow, feature mapping, and demonstration outline.

## Limitations & Future Scope

- Replace synthetic historical records and simulated telemetry with validated, real-world machine data.
- Integrate real telemetry sources where authorized and technically supported.
- Extend verification to newly recorded post-training sessions.
- Introduce authenticated operator and supervisor accounts.
- Validate model performance, anomaly detection, and training outcomes on field data.
- Integrate with machine systems only after appropriate safety engineering and validation.

## Recognition

Shortlisted among the **top 250 participants out of 1,600 students** in the Caterpillar hackathon.

---

**Disclaimer:** This is a hackathon prototype for operator assistance and safety monitoring. It is not a certified safety system and must not be used as a substitute for official equipment safeguards or operating procedures.
