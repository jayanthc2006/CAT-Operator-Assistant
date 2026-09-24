"""Smart Operator Assistant for CAT machinery: standalone operator software.
Launch: double-click "Start Operator Assistant.bat"  (or: .venv\\Scripts\\streamlit.exe run app.py)
"""
import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

import analytics as an
import data
import skills as sk
import supervision

load_dotenv()
st.set_page_config(page_title="CAT Operator Assistant", page_icon="🚜", layout="wide")

# ---------------------------------------------------------------- design system (industrial HMI)
# Theme = session-state choice (sidebar "Display"). Only visual tokens change between Dark and Light;
# .streamlit/config.toml keeps the dark base for Streamlit's own widgets and light-mode overrides are CSS.
THEME = st.session_state.get("theme", "Dark")
LIGHT = THEME == "Light"
CAT_YELLOW, CAT_BLACK = "#FFCD11", "#111316"
RED, AMBER, GREEN, GREY, INFO = "#E5484D", "#F5A524", "#2FB463", "#6B7480", "#4C9AFF"
TOK = (dict(bg="#F3F4F6", surface="#FFFFFF", surface2="#ECEEF1", border="#D5D9DF", text="#15181C", muted="#5B6470",
            ok_t="#1E7E45", warn_t="#9A5B00", crit_t="#C62828", info_t="#1F5FBF", grid="#E2E5EA", cat_t="#8A6A00") if LIGHT else
       dict(bg="#0E1013", surface="#16191E", surface2="#1E2228", border="#2A2F37", text="#E8EAED", muted="#98A1AD",
            ok_t=GREEN, warn_t=AMBER, crit_t="#FF6B6F", info_t=INFO, grid="#2A2F37", cat_t=CAT_YELLOW))
STEEL = "#3A4048" if LIGHT else "#C9D1D9"   # neutral chart colour with good contrast on the active surface
STATE_CLASS = {"NORMAL": "ok", "CAUTION": "warn", "CRITICAL": "crit"}
STATUS_KIND = {"NORMAL": "ok", "VERIFIED": "ok", "CAUTION": "warn", "MONITORING": "info", "PENDING": "",
               "CRITICAL": "crit", "LOCKED": "crit"}
st.markdown(f"""<style>
:root {{--bg:{TOK['bg']}; --surface:{TOK['surface']}; --surface-2:{TOK['surface2']}; --border:{TOK['border']};
  --text:{TOK['text']}; --muted:{TOK['muted']}; --cat:{CAT_YELLOW}; --ok:{GREEN}; --warn:{AMBER}; --crit:{RED}; --info:{INFO};
  --ok-t:{TOK['ok_t']}; --warn-t:{TOK['warn_t']}; --crit-t:{TOK['crit_t']}; --info-t:{TOK['info_t']}; --cat-t:{TOK['cat_t']};
  --display:"Bahnschrift","DIN Alternate","Segoe UI",system-ui,sans-serif;}}
.block-container {{padding-top: 1rem; max-width: 1500px;}}
h1, h2, h3, h4 {{font-family: var(--display) !important; letter-spacing: .02em;}}
h3 {{font-size: 1.25rem !important; margin-top: .6rem;}}
/* sidebar + grouped navigation (one radio; group labels are drawn with CSS so page names stay unchanged) */
section[data-testid="stSidebar"] {{background: var(--surface); border-right: 3px solid var(--cat);}}
section[data-testid="stSidebar"] div[role="radiogroup"] > * {{padding: .45rem .6rem; margin: 1px 0; border-radius: 6px;
  font-family: var(--display); font-size: 1.02rem; width: 100%; position: relative;}}
section[data-testid="stSidebar"] div[role="radiogroup"] > *:hover {{background: var(--surface-2);}}
section[data-testid="stSidebar"] div[role="radiogroup"] > *:has(input:checked) {{background: rgba(255,205,17,.16);
  box-shadow: inset 3px 0 0 var(--cat);}}
section[data-testid="stSidebar"] .st-key-nav div[role="radiogroup"] > *:nth-child(4),
section[data-testid="stSidebar"] .st-key-nav div[role="radiogroup"] > *:nth-child(7) {{margin-top: 1.7rem;}}
section[data-testid="stSidebar"] .st-key-nav div[role="radiogroup"] > *:nth-child(4)::before,
section[data-testid="stSidebar"] .st-key-nav div[role="radiogroup"] > *:nth-child(7)::before {{position: absolute; top: -1.35rem; left: .2rem;
  font-size: .68rem; letter-spacing: .16em; color: var(--muted); font-family: var(--display);}}
section[data-testid="stSidebar"] .st-key-nav div[role="radiogroup"] > *:nth-child(4)::before {{content: "INTELLIGENCE";}}
section[data-testid="stSidebar"] .st-key-nav div[role="radiogroup"] > *:nth-child(7)::before {{content: "DEVELOPMENT";}}
.nav-group, .sec {{font-size: .7rem; letter-spacing: .16em; color: var(--muted); font-family: var(--display); text-transform: uppercase;}}
.nav-group {{margin: .4rem 0 .1rem .2rem;}}
.sec {{margin: 1.3rem 0 .45rem 0;}}
/* large, touch-friendly controls */
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {{min-height: 2.9rem; font-weight: 600;
  border-radius: 8px; font-family: var(--display); letter-spacing: .02em;}}
button[kind="primary"], button[kind="primaryFormSubmit"] {{color: {CAT_BLACK} !important; font-weight: 700;}}
button[kind="primary"] *, button[kind="primaryFormSubmit"] * {{color: {CAT_BLACK} !important;}}
/* telemetry readouts (st.metric): flat, value-first */
div[data-testid="stMetric"] {{background: var(--surface); border: 1px solid var(--border); padding: .55rem .8rem; border-radius: 8px;}}
div[data-testid="stMetricLabel"] p {{text-transform: uppercase; letter-spacing: .09em; font-size: .7rem !important; color: var(--muted) !important;}}
div[data-testid="stMetricValue"] {{font-family: var(--display); font-size: 1.75rem; color: var(--text);}}
div[data-testid="stExpander"] details {{border: 1px solid var(--border); border-radius: 8px; background: var(--surface);}}
/* alert banners (class names are part of the tested interface) */
.banner {{padding: .9rem 1.15rem; border-radius: 8px; font-weight: 700; font-size: 1.15rem; margin: .15rem 0 .1rem 0;
  font-family: var(--display); letter-spacing: .01em;}}
.b-red {{background: var(--crit); color: #fff;}} .b-amber {{background: var(--warn); color: #111316;}}
.b-green {{background: rgba(47,180,99,.14); color: var(--ok-t); border: 1px solid rgba(47,180,99,.5);}}
/* components */
.brand {{font-weight: 800; font-size: 1.5rem; letter-spacing: .04em; font-family: var(--display); color: var(--text);}}
.brand span {{background: var(--cat); color: {CAT_BLACK}; padding: 0 .4rem; border-radius: 3px; margin-right: .2rem;}}
.hmi-head {{display:flex; align-items:flex-end; justify-content:space-between; gap:1rem; border-bottom: 1px solid var(--border);
  padding-bottom: .6rem; margin-bottom: 1rem; flex-wrap: wrap;}}
.hmi-head .kicker {{font-size: .72rem; letter-spacing: .18em; color: var(--muted); font-family: var(--display);}}
.hmi-head .kicker b {{color: var(--cat); font-weight: 700;}}
.hmi-head .title {{font-size: 2.15rem; font-weight: 700; font-family: var(--display); line-height: 1.1; color: var(--text);}}
.hmi-head .sub {{color: var(--muted); font-size: .95rem; margin-top: .15rem;}}
.chip {{display:inline-flex; align-items:center; gap:.35rem; padding: .22rem .65rem; border-radius: 999px; font-size: .8rem;
  font-weight: 600; letter-spacing: .04em; border: 1px solid var(--border); background: var(--surface-2); color: var(--text);
  font-family: var(--display); margin: 0 .3rem .3rem 0; white-space: nowrap;}}
.chip.ok {{color: var(--ok-t); border-color: rgba(47,180,99,.55); background: rgba(47,180,99,.10);}}
.chip.warn {{color: var(--warn-t); border-color: rgba(245,165,36,.6); background: rgba(245,165,36,.12);}}
.chip.crit {{color: #fff; border-color: var(--crit); background: var(--crit);}}
.chip.info {{color: var(--info-t); border-color: rgba(76,154,255,.5); background: rgba(76,154,255,.10);}}
.chip.cat {{color: {CAT_BLACK}; background: var(--cat); border-color: var(--cat);}}
.chip.sim {{color: var(--muted); border-style: dashed; background: transparent;}}
.card {{background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: .95rem 1.15rem; margin-bottom: .75rem;
  color: var(--text);}}
.card.accent {{border-left: 4px solid var(--cat);}}
.card.flat {{background: transparent; border: 0; padding: .2rem 0; margin-bottom: .4rem;}}
.card .label {{font-size: .7rem; letter-spacing: .13em; color: var(--muted); text-transform: uppercase; font-family: var(--display);}}
.card .big {{font-size: 1.55rem; font-weight: 700; font-family: var(--display); line-height: 1.2;}}
.card.hero .big {{font-size: 2.05rem;}}
.card .eta {{font-family: var(--display); font-size: 1.35rem; color: var(--text);}}
.card .eta b {{color: var(--cat-t); font-size: 1.7rem;}}
.card .meta {{color: var(--muted); font-size: .9rem;}}
.row {{display:flex; justify-content:space-between; align-items:center; gap:.6rem; padding:.45rem 0; border-top:1px solid var(--border);}}
.row:first-of-type {{border-top: 0;}}
.kv {{display:grid; grid-template-columns: 7rem 1fr; gap:.8rem; align-items: baseline; padding:.5rem 0; border-top:1px solid var(--border);}}
.kv > span:first-child {{color: var(--muted); font-size: .72rem; letter-spacing: .13em; font-family: var(--display);}}
.row .v {{font-family: var(--display); font-size: 1.1rem; text-align: right;}}
.state {{border-radius: 10px; padding: 1.05rem 1.25rem; margin-bottom: .8rem; border: 1px solid var(--border); background: var(--surface);
  color: var(--text);}}
.state .lvl {{font-family: var(--display); font-size: 2rem; font-weight: 800; letter-spacing: .08em; line-height: 1.1;}}
.state.ok {{border-left: 7px solid var(--ok);}} .state.ok .lvl {{color: var(--ok-t);}}
.state.warn {{border-left: 7px solid var(--warn); background: rgba(245,165,36,.07);}} .state.warn .lvl {{color: var(--warn-t);}}
.state.crit {{border-left: 7px solid var(--crit); background: rgba(229,72,77,.11);}} .state.crit .lvl {{color: var(--crit-t);}}
.rail {{display:flex; gap:.35rem; flex-wrap: wrap; margin: .35rem 0 .6rem 0;}}
.rail .step {{flex: 1 1 110px; padding: .5rem .6rem; border-radius: 8px; border: 1px solid var(--border); background: var(--surface-2);
  font-family: var(--display); font-size: .84rem; letter-spacing: .08em; color: var(--muted); text-align: center;}}
.rail .step small {{display:block; letter-spacing: 0; font-size: .75rem; margin-top: .1rem; text-transform: none;}}
.rail .step.done {{color: var(--ok-t); border-color: rgba(47,180,99,.55); background: rgba(47,180,99,.10);}}
.rail .step.now {{color: {CAT_BLACK}; background: var(--cat); border-color: var(--cat); font-weight: 700;}}
.rail .step.alert {{color: #fff; background: var(--crit); border-color: var(--crit); font-weight: 700;}}
.badge {{display:inline-block; background: rgba(255,205,17,.12); border:1px solid rgba(255,205,17,.5); border-radius: 20px;
  padding:.3rem .8rem; margin:.2rem; font-size:.9rem; color: var(--text);}}
</style>""", unsafe_allow_html=True)
if LIGHT:  # light-mode overrides for Streamlit's own (dark-configured) widgets; tokens above already switched
    st.markdown("""<style>
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {background: var(--bg) !important; color: var(--text);}
[data-testid="stHeader"] {background: transparent !important;}
section[data-testid="stSidebar"] > div {background: var(--surface) !important;}
.stApp [data-testid="stMarkdownContainer"], .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp label,
.stApp [data-testid="stWidgetLabel"] p, .stApp [data-testid="stMarkdownContainer"] p, .stApp [data-testid="stMarkdownContainer"] li,
.stApp [data-testid="stMarkdownContainer"] strong {color: var(--text) !important;}
.stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stCaptionContainer"] p {color: var(--muted) !important;}
.stApp [data-baseweb="select"] > div, .stApp [data-baseweb="input"], .stApp [data-baseweb="base-input"], .stApp textarea,
.stApp input:not([type="checkbox"]):not([type="radio"]), .stApp [data-baseweb="textarea"] {background: var(--surface-2) !important;
  color: var(--text) !important; border-color: var(--border) !important;}
.stApp [data-baseweb="select"] * {color: var(--text) !important;}
[data-baseweb="popover"] ul, [data-baseweb="menu"], [data-baseweb="popover"] [role="listbox"] {background: var(--surface) !important;}
[data-baseweb="popover"] li, [data-baseweb="menu"] li {color: var(--text) !important;}
.stApp button[kind="secondary"], .stApp button[kind="secondaryFormSubmit"], .stApp [data-testid="stPopover"] button,
.stApp .stDownloadButton button {background: var(--surface) !important; color: var(--text) !important; border-color: var(--border) !important;}
.stApp button[kind="secondary"] p, .stApp [data-testid="stPopover"] button p {color: var(--text) !important;}
.stApp details summary, .stApp details summary p, .stApp details summary span {color: var(--text) !important;}
.stApp button[data-baseweb="tab"] p {color: var(--text) !important;}
.stApp [data-testid="stMetricDelta"], .stApp [data-testid="stMetricDelta"] div {color: var(--muted) !important;}
.stApp [data-testid="stSliderTickBarMin"], .stApp [data-testid="stSliderTickBarMax"], .stApp [data-testid="stThumbValue"] {color: var(--text) !important;}
.stApp [data-testid="stChatMessage"] {background: var(--surface) !important; border: 1px solid var(--border);}
.stApp [data-testid="stChatInput"], .stApp [data-testid="stChatInput"] > div {background: var(--surface) !important;}
.stApp [data-testid="stAlert"] p, .stApp [data-testid="stAlert"] li {color: var(--text) !important;}
.stApp [data-testid="stForm"], .stApp [data-testid="stVerticalBlockBorderWrapper"] {border-color: var(--border) !important;}
.stApp [data-testid="stCheckbox"] label span, .stApp [data-testid="stRadio"] label div {color: var(--text);}
.stApp [data-testid="stProgressBarTrack"] {background: var(--surface-2) !important;}
.stApp label[data-testid="stRadioOption"]:not(:has(input:checked)) > div > div:first-child > div {background: var(--surface) !important;}
.stApp label[data-testid="stRadioOption"]:not(:has(input:checked)) > div > div:first-child {background: var(--border) !important;}
</style>""", unsafe_allow_html=True)


def page_header(title, group, subtitle="", chips_html=""):
    st.markdown(f'<div class="hmi-head"><div><div class="kicker"><b>■</b> {group.upper()}</div><div class="title">{title}</div>'
                f'<div class="sub">{subtitle}</div></div><div>{chips_html}</div></div>', unsafe_allow_html=True)


def chip(text, kind=""):
    return f'<span class="chip {kind}">{text}</span>'


def status_chip(status, text=None):
    """One visual language for NORMAL / CAUTION / CRITICAL / LOCKED / MONITORING / VERIFIED / PENDING (text + colour)."""
    return chip(text or status, STATUS_KIND.get(status, ""))


def card(body_html, accent=False, extra=""):
    st.markdown(f'<div class="card{" accent" if accent else ""}{" " + extra if extra else ""}">{body_html}</div>',
                unsafe_allow_html=True)


def section(title):
    st.markdown(f'<div class="sec">{title}</div>', unsafe_allow_html=True)


def state_panel(level, title, detail=""):
    st.markdown(f'<div class="state {STATE_CLASS[level]}"><div class="lvl">{level}</div><div><b>{title}</b></div>'
                f'<div class="meta" style="color:var(--muted);margin-top:.35rem">{detail}</div></div>', unsafe_allow_html=True)


def hmi_chart(where, fig, **kwargs):
    """Plotly chart styled for the active theme (transparent background, theme text/grid colours)."""
    fig.update_layout(template="plotly_white" if LIGHT else "plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Bahnschrift, Segoe UI, sans-serif", color=TOK["text"]))
    fig.update_xaxes(gridcolor=TOK["grid"], zerolinecolor=TOK["grid"])
    fig.update_yaxes(gridcolor=TOK["grid"], zerolinecolor=TOK["grid"])
    if any(getattr(t, "type", "") in ("scatterpolar", "barpolar") for t in fig.data):
        fig.update_polars(bgcolor="rgba(0,0,0,0)", radialaxis_gridcolor=TOK["grid"], angularaxis_gridcolor=TOK["grid"])
    where.plotly_chart(fig, theme=None, **kwargs)


SIM_CHIP = '<span class="chip sim" title="Readings come from the built-in simulator, not a connected machine">◌ SIMULATED TELEMETRY</span>'
SAFETY_ACTIONS = {  # operator guidance per alert type (restates the alert banners; used by Safety Center + assistant)
    "Seatbelt": "Stop and fasten the seatbelt before moving the machine again.",
    "Proximity": "Stop all motion, make eye contact with the person and wait until they are clear of the 6 m zone. Use a spotter if needed.",
    "Tilt": "Lower the bucket, travel straight up or down the slope and move to level ground. Never turn across the slope.",
    "Overspeed": "Slow down below the site speed limit.",
    "Engine temp": "Reduce load and let the engine idle to cool. Check coolant once parked.",
}


# ============================ data + models ============================
@st.cache_resource(show_spinner="Starting up the operator assistant…")
def boot():
    data.init_db()
    machines, operators = data.read("machines"), data.read("operators")
    s = an.enrich(data.read("sessions"), machines, operators)
    tmod = an.train_time_model(s)
    s["expected_min_oof"] = tmod["oof"]                     # out-of-fold: fair per-session benchmark
    s["in_test_set"] = s.index.isin(tmod["test_pred"].index)
    s["predicted_min"] = tmod["test_pred"]                  # hold-out predictions (evaluation only)
    s = an.detect_anomalies(s)
    return machines, operators, s, sk.session_standards(s), tmod


machines, operators, sessions, standards, tmod = boot()
time_model, tm, importance = tmod["model"], tmod["metrics"], tmod["importance"]
time_mae = tm["ai_mae"]
PAGES = ["🚜 Live Cab", "📋 My Day", "🦺 Safety Center",                   # OPERATION
         "📊 Machine Insights", "⏱️ Task Estimator", "🤖 Ask Assistant",     # INTELLIGENCE
         "🧭 My Skill Profile", "🎓 Training Hub"]                            # DEVELOPMENT


def navigate(page, lesson=None):
    """Request a jump to a page (and optionally a lesson). Applied at the top of the next run, before the
    navigation widget is drawn, so it also works from inside the auto-refreshing live panel."""
    st.session_state.pending_nav = (page, lesson)
M = machines.set_index("machine_id")
OPS = operators.set_index("operator_id")

# ============================ shared by both roles (role-neutral) ============================
HIST_END = sessions.timestamp.max()  # last recorded session; trainings after this have no post-training data yet
RBAC_NOTE = "Prototype role selection — authentication/RBAC not implemented"
REVIEWER = "Site supervisor (prototype)"


def is_new_training(loop):
    """True if the training was completed after the last recorded session (e.g. in this app session)."""
    return pd.Timestamp(loop["completed"]) > HIST_END


def logout():
    """Log out (either role): clear this browser session's state (not the database) and keep the display theme."""
    keep_theme = st.session_state.get("theme", "Dark")
    st.session_state.clear()
    st.session_state.theme = keep_theme


# Supervisor review of a training (a human checkpoint between TRAIN and VERIFY; never a statistical verdict)
REVIEW_CHIP = {"awaiting": ("AWAITING SUPERVISOR REVIEW", "warn"), "approved": ("✓ SUPERVISOR APPROVED", "ok"),
               "retraining": ("RETRAINING REQUESTED", "warn"), "instructor": ("INSTRUCTOR COACHING RECOMMENDED", "crit")}
REVIEW_TEXT = {"awaiting": ("warning", "Awaiting supervisor review. Behavioural monitoring starts once your supervisor approves "
                                       "this training."),
               "approved": ("success", "Supervisor approved training. Behavioural verification begins after post-training "
                                       "sessions are recorded."),
               "retraining": ("warning", "Your supervisor requested retraining: repeat the lesson. The skill gap stays open "
                                         "and your score is unchanged."),
               "instructor": ("warning", "Instructor coaching recommended by your supervisor. Book a session in "
                                         "Training Hub → Book an instructor.")}


def review_of(operator_id, loop):
    """Supervisor review state of one training loop, or None for seeded history (it pre-dates supervisor review)."""
    if loop is None or not is_new_training(loop):
        return None
    case = {"operator_id": operator_id, "module_id": loop["module_id"], "training_time": loop["completed"], "exempt": False}
    return supervision.review_state(case, data.read_reviews())[0]


def loop_rail(row, loops, stage, adapt, review=None):
    """OBSERVE → DIAGNOSE → TRAIN → VERIFY → ADAPT for one competency (derived from skills.loop_stage).
    `review` (supervisor state of the latest training) only annotates TRAIN/VERIFY; the verdict stays statistical."""
    mine = [l for l in loops if l["comp"] == row["id"]]
    last = mine[-1] if mine else None
    steps = [("OBSERVE", f"{row['n']} sessions", "done")]
    if last is None and stage == -1:
        steps += [("DIAGNOSE", "meets standard", "done"), ("TRAIN", "not needed", ""), ("VERIFY", "–", ""), ("ADAPT", "–", "")]
    elif last is None:
        steps += [("DIAGNOSE", f"gap · {row['score']:.0f}/100", "now"), ("TRAIN", "recommended", ""),
                  ("VERIFY", "after training", ""), ("ADAPT", "–", "")]
    else:
        train = {"awaiting": ("TRAIN", f"done {last['completed'][:10]} · awaiting review", "now"),
                 "approved": ("TRAIN", f"done {last['completed'][:10]} · supervisor approved", "done"),
                 "retraining": ("TRAIN", "retraining requested", "now"),
                 "instructor": ("TRAIN", "instructor coaching", "alert")}.get(review, ("TRAIN", f"done {last['completed'][:10]}", "done"))
        steps += [("DIAGNOSE", f"now {row['score']:.0f}/100", "done"), train]
        if stage == 4:
            steps += [("VERIFY", "improvement verified", "done"), ("ADAPT", "loop closed", "done")]
        elif adapt:
            steps += [("VERIFY", "no measurable change", "done"), ("ADAPT", "escalate: coaching", "alert")]
        elif review in ("awaiting", "retraining", "instructor"):
            steps += [("VERIFY", "after supervisor approval", ""), ("ADAPT", "–", "")]
        else:
            sub = (f"monitoring {last['n_post']}/{sk.MIN_SESSIONS}" if last["n_post"] < sk.MIN_SESSIONS
                   else "no significant change yet")
            steps += [("VERIFY", sub, "now"), ("ADAPT", "pending", "")]
    return '<div class="rail">' + "".join(f'<div class="step {k}">{n}<small>{s}</small></div>' for n, s, k in steps) + "</div>"


BOOKING_TOPICS = [data.TRAINING_MODULES[m] for m in ("terrain", "safety", "fuel", "walkaround", "operation")] + [
    "Machine-specific hands-on training", "Task planning & execution coaching"]


def booking_form(operator_id, form_key="book", topic=None):
    """Instructor booking (Training Hub tab and Supervisor Console): one row in the existing `bookings` table."""
    with st.form(form_key, clear_on_submit=True):
        a, b = st.columns(2)
        topic = a.selectbox("Topic", BOOKING_TOPICS, index=BOOKING_TOPICS.index(topic) if topic in BOOKING_TOPICS else 0)
        instructor = b.selectbox("Instructor", ["R. Menon (Safety)", "K. Das (Excavators & Loaders)", "S. Rao (Dozers & Graders)"])
        day = a.date_input("Date", datetime.now().date() + timedelta(days=1), min_value=datetime.now().date())
        slot = b.selectbox("Slot", ["08:00–10:00", "10:00–12:00", "14:00–16:00"])
        if st.form_submit_button("Book session", type="primary"):
            data.append("bookings", {"operator_id": operator_id, "topic": topic, "date": str(day), "slot": slot,
                                     "instructor": instructor})
            st.success(f"Booked **{topic}** with {instructor} on {day} at {slot}.")


def fmt_score(v):
    return "–" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.0f}"


# ============================ login (prototype role selection) ============================
if "operator_id" not in st.session_state and st.session_state.get("role") != "Supervisor":
    _, mid, _ = st.columns([1, 1.3, 1])
    with mid:
        st.markdown('<div style="height:8vh"></div><div class="brand"><span>CAT</span> Operator Assistant</div>',
                    unsafe_allow_html=True)
        st.caption("Operator HMI: tasks, safety, training and insights. Runs locally; telemetry in this prototype is simulated.")
        st.divider()
        role = st.radio("Select role", ["Operator", "Supervisor"], horizontal=True, key="login_role")
        st.caption(f"🔓 {RBAC_NOTE}")
        if role == "Operator":
            pick = st.selectbox("Operator", operators.operator_id,
                                format_func=lambda o: f"{o} · {OPS.loc[o, 'name']}")
            mid_ = OPS.loc[pick, "machine_id"]
            st.info(f"Assigned machine: **{mid_}** · {M.loc[mid_, 'model']} {M.loc[mid_, 'machine_type']}")
            if st.button("🔑 Start shift", type="primary", width="stretch"):
                st.session_state.operator_id = pick
                st.session_state.shift_start = datetime.now()
                st.session_state.live_alerts = []
                st.session_state.alert_active = set()
                st.session_state.chat = []
                st.rerun()
        else:
            st.info(f"**{REVIEWER}**: review completed trainings, follow monitoring and verified outcomes, and arrange "
                    "instructor coaching for all operators.")
            if st.button("🧑‍💼 Open Supervisor Console", type="primary", width="stretch"):
                st.session_state.role = "Supervisor"
                st.rerun()
    st.stop()


# ============================ SUPERVISOR CONSOLE (separate role; never runs operator code) ============================
SUP_PAGES = ["📊 Dashboard", "📝 Training Reviews", "👷 Operators", "📈 Outcomes", "👨‍🏫 Coaching & Bookings"]
GROUP_CHIP = {"awaiting": ("AWAITING SUPERVISOR REVIEW", "warn"), "retraining": ("RETRAINING REQUESTED", "warn"),
              "coaching": ("INSTRUCTOR COACHING RECOMMENDED", "crit"), "monitoring": ("MONITORING", "info"),
              "verified": ("VERIFIED · STATISTICAL", "ok"), "escalated": ("ESCALATED · NO MEASURABLE IMPROVEMENT", "crit")}


@st.cache_resource(show_spinner=False)
def profile_of(operator_id):
    """Competency profile from recorded sessions (fixed for the server process, like the models)."""
    return sk.operator_profile(sessions, standards, operator_id)


def all_cases():
    """Every review case with its review state and the existing statistical loops for that training."""
    tl = data.read("training_log")
    reviews = data.read_reviews()
    loops_by_op, out = {}, []
    for c in supervision.training_cases(tl, HIST_END):
        opid = c["operator_id"]
        if opid not in loops_by_op:
            loops_by_op[opid] = sk.training_loops(sessions, standards, opid, tl)
        loops = [l for l in loops_by_op[opid] if l["module_id"] == c["module_id"] and l["completed"] == c["training_time"]]
        state, last = supervision.review_state(c, reviews)
        out.append({**c, "loops": loops, "state": state, "last_review": last, "group": supervision.case_group(state, loops),
                    "key": f"{opid}|{c['module_id']}|{c['training_time']}"})
    return out, reviews


def case_chips(c):
    label, kind = GROUP_CHIP[c["group"]]
    if c["group"] == "monitoring":
        label = f"MONITORING {supervision.post_sessions(c['loops'])}/{sk.MIN_SESSIONS}"
    chips = (chip("✓ SUPERVISOR APPROVED", "ok") if c["state"] == "approved" else "") + chip(label, kind)
    return chips + (chip("SEEDED HISTORY · synthetic", "sim") if c["exempt"] else chip("NEW · recorded in the app", "cat"))


def case_reason(c):
    prof = profile_of(c["operator_id"]).set_index("id")
    return " · ".join(f"{prof.loc[k, 'competency']} {fmt_score(prof.loc[k, 'score'])}/100"
                      for k in supervision.competencies_for(c["module_id"]))


def case_card(c):
    o = OPS.loc[c["operator_id"]]
    card(f'<div class="label">{o["name"]} · {c["operator_id"]} · {o.machine_id}</div>'
         f'<div class="big" style="font-size:1.35rem">{c["module"]}</div>'
         f'<div class="meta">Reason: {case_reason(c)} · training completed {c["training_time"]} · quiz passed {c["score"]:.0f}%</div>'
         f'<div style="margin-top:.5rem">{case_chips(c)}</div>')


def open_review(key):
    st.session_state.sup_case = key
    st.session_state.sup_nav = "📝 Training Reviews"


def decide(c, decision, assessment):
    data.log_review(c["operator_id"], c["module_id"], c["training_time"], decision, assessment,
                    note=st.session_state.get(f"note_{c['key']}", ""), reviewer=REVIEWER)
    st.session_state.sup_flash = decision


def sup_dashboard(cases, reviews):
    n = {g: sum(c["group"] == g for c in cases) for g in supervision.GROUP_ORDER}
    page_header("Supervisor Dashboard", "Supervision", "Training reviews and outcomes for all operators · " + RBAC_NOTE,
                chip(f"{n['awaiting']} pending review", "warn" if n["awaiting"] else "ok"))
    k = st.columns(4)
    k[0].metric("Pending reviews", n["awaiting"])
    k[1].metric("Monitoring", n["monitoring"])
    k[2].metric("Verified outcomes", n["verified"], help="Statistical verification only (Fisher exact + Mann–Whitney U); "
                                                         "supervisor approval never sets this")
    k[3].metric("Coaching recommended", n["coaching"] + n["escalated"],
                help="Supervisor recommendations plus statistical escalations")
    for g in supervision.GROUP_ORDER:
        grp = [c for c in cases if c["group"] == g]
        if not grp and g in ("retraining", "coaching"):
            continue
        section(f"{supervision.GROUP_LABEL[g]} ({len(grp)})")
        if not grp:
            st.caption("None.")
        for c in grp:
            case_card(c)
            if g == "awaiting":
                st.button("Review", key=f"dash_rev_{c['key']}", type="primary", on_click=open_review, args=(c["key"],))


def review_panel(c, reviews):
    o = OPS.loc[c["operator_id"]]
    opid, k = c["operator_id"], c["key"]
    prof = profile_of(opid).set_index("id")
    page_header(f"Review · {o['name']}", "Supervision · Training review", f"{opid} · {c['module']} · {RBAC_NOTE}", case_chips(c))
    st.button("← All training reviews", on_click=lambda: st.session_state.pop("sup_case", None))
    flash = st.session_state.pop("sup_flash", None)
    if flash == "approved":
        st.success("Supervisor approved training. Behavioural verification begins after post-training sessions are recorded.")
    elif flash == "retraining":
        st.warning("Retraining requested. The skill gap stays open and the score is unchanged; the operator sees the lesson "
                   "again in Training Hub.")
    elif flash == "instructor":
        st.warning("Instructor coaching recommended. Book a session below or from Coaching & Bookings.")
    a, b = st.columns(2)
    with a:
        section("Operator")
        card("".join(f'<div class="kv"><span>{n}</span><span>{v}</span></div>' for n, v in [
            ("NAME", f"{o['name']} · {opid}"), ("SKILL", f"{data.skill_of(o.experience_yrs)} · {o.experience_yrs} yrs"),
            ("MACHINE", f"{o.machine_id} · {M.loc[o.machine_id, 'model']} {M.loc[o.machine_id, 'machine_type']}")]))
        section("Why training was assigned")
        for comp in supervision.competencies_for(c["module_id"]):
            r = prof.loc[comp]
            card(f'<div class="label">{r["competency"]}</div><div class="big">{fmt_score(r["score"])}<span class="meta" '
                 f'style="font-size:.9rem"> /100 · last {r["n"]} applicable sessions</span> '
                 f'{chip("SKILL GAP", "warn") if r["gap"] else chip("MEETS STANDARD", "ok")}</div>'
                 f'<div class="meta">Standard: {r["standard"]}</div>'
                 + "".join(f'<div class="meta">• {e}</div>' for e in r["evidence"]))
    with b:
        section("Training")
        card("".join(f'<div class="kv"><span>{n}</span><span>{v}</span></div>' for n, v in [
            ("LESSON", c["module"]), ("COMPLETION", "✓ Completed"),
            ("QUIZ", f"✓ Passed · {c['score']:.0f}% (pass mark 66%)"), ("DATE", c["training_time"]),
            ("ATTEMPTS", f"{c['attempts']} recorded pass(es); this review covers the latest")]))
        section("Statistical verification (separate from this review)")
        st.caption(f"Post-training sessions recorded: {supervision.post_sessions(c['loops'])}/{sk.MIN_SESSIONS}. "
                   "Verified / Monitoring / Escalate come only from the before/after tests (Fisher exact + Mann–Whitney U, "
                   "p < 0.05, ≥ 8 post-training sessions). Live Cab sessions aren't saved in this prototype, so new training "
                   "stays at 0 until real session data is recorded.")
        section("Supervisor assessment")
        if c["exempt"]:
            st.info("Seeded synthetic history: this training pre-dates supervisor review, so no decision is needed.")
        else:
            assess = st.radio("Did the operator demonstrate understanding of the training?", ["Approved", "Needs reinforcement"],
                              index=None, key=f"assess_{k}")
            st.text_area("Supervisor note (optional)", key=f"note_{k}")
            b1, b2, b3 = st.columns(3)
            b1.button("APPROVE & START MONITORING", key=f"approve_{k}", type="primary", width="stretch",
                      disabled=assess != "Approved", on_click=decide, args=(c, "approved", "Approved"))
            b2.button("REQUEST RETRAINING", key=f"retrain_{k}", width="stretch", disabled=assess != "Needs reinforcement",
                      on_click=decide, args=(c, "retraining", "Needs reinforcement"))
            b3.button("RECOMMEND INSTRUCTOR", key=f"instr_{k}", width="stretch", disabled=assess != "Needs reinforcement",
                      on_click=decide, args=(c, "instructor", "Needs reinforcement"))
    if c["state"] == "instructor":
        section("Book instructor coaching (existing booking)")
        booking_form(opid, f"book_{k}", c["module"])
    hist = reviews[(reviews.operator_id == opid) & (reviews.module_id == c["module_id"])]
    if len(hist):
        section("Review history (append-only)")
        st.dataframe(hist.iloc[::-1][["time", "training_time", "decision", "assessment", "note", "reviewer"]],
                     hide_index=True, width="stretch")


def sup_reviews(cases, reviews):
    case = next((c for c in cases if c["key"] == st.session_state.get("sup_case")), None)
    if case is not None:
        return review_panel(case, reviews)
    pending = [c for c in cases if c["group"] == "awaiting"]
    page_header("Training Reviews", "Supervision", "Completed trainings waiting for a supervisor decision · " + RBAC_NOTE,
                chip(f"{len(pending)} pending", "warn" if pending else "ok"))
    if not pending:
        st.success("No trainings are waiting for review.")
    for c in pending:
        case_card(c)
        st.button("Review", key=f"rev_{c['key']}", type="primary", on_click=open_review, args=(c["key"],))
    done = [c for c in cases if not c["exempt"] and c["group"] != "awaiting"]
    if done:
        section("Reviewed")
        for c in done:
            case_card(c)
            st.button("Open", key=f"open_{c['key']}", on_click=open_review, args=(c["key"],))


def sup_operators(cases, reviews):
    page_header("Operators", "Supervision", "Competency scores = share of each operator's last 30 applicable sessions meeting "
                "the written standard · below 70 = skill gap")
    rows = []
    for opid in OPS.index:
        r = {"Operator": f"{OPS.loc[opid, 'name']} · {opid}", "Machine": OPS.loc[opid, "machine_id"]}
        for p in profile_of(opid).itertuples():
            r[p.competency] = fmt_score(p.score) + (" ⚠ gap" if p.gap else "")
        r["Training status"] = "; ".join(f"{c['module']}: {supervision.GROUP_LABEL[c['group']]}"
                                         for c in cases if c["operator_id"] == opid) or "–"
        rows.append(r)
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.caption("Scores come from recorded (synthetic) sessions and don't change when training is logged or reviewed.")


def sup_outcomes(cases, reviews):
    page_header("Outcomes", "Supervision", "Monitoring, verified and escalated training loops · verification is statistical, "
                "not a supervisor decision")
    for g in ("monitoring", "verified", "escalated"):
        grp = [c for c in cases if c["group"] == g]
        section(f"{supervision.GROUP_LABEL[g]} ({len(grp)})")
        if not grp:
            st.caption("None.")
        for c in grp:
            prof = profile_of(c["operator_id"]).set_index("id")
            with st.container(border=True):
                case_card(c)
                for comp in supervision.competencies_for(c["module_id"]):
                    row = {**prof.loc[comp].to_dict(), "id": comp}
                    stage, _, adapt = sk.loop_stage(row, c["loops"])
                    st.markdown(loop_rail(row, c["loops"], stage, adapt, None if c["exempt"] else c["state"]),
                                unsafe_allow_html=True)
                    for l in [l for l in c["loops"] if l["comp"] == comp][-1:]:
                        if l["post_rate"] is not None:
                            p = l["p_rate"]
                            st.caption(f"{l['competency']}: {l['pre_rate']:.0f}% → {l['post_rate']:.0f}% of sessions meeting the "
                                       f"standard (last {l['n_pre']} before vs first {l['n_post']} after) · one-sided Fisher exact "
                                       + ("p < 0.001" if p is not None and p < 0.001 else f"p = {p:.3f}" if p is not None else "–")
                                       + f" · {l['verdict_text']}")
                        elif l["pre_rate"] is not None:
                            st.caption(f"{l['competency']}: baseline {l['pre_rate']:.0f}% before training · "
                                       f"{l['verdict_text']}")


def sup_coaching(cases, reviews):
    recs = [c for c in cases if c["group"] in ("coaching", "escalated")]
    page_header("Coaching & Bookings", "Supervision", "Instructor coaching recommended by a supervisor or by the statistical "
                "escalation rule · uses the existing instructor booking", chip(f"{len(recs)} recommended", "crit" if recs else "ok"))
    for c in recs:
        case_card(c)
        st.caption("Source: supervisor recommendation." if c["group"] == "coaching" else
                   f"Source: statistical verification found no measurable improvement after {sk.ADAPT_AFTER}+ post-training "
                   "sessions (existing escalation rule).")
        with st.expander(f"Book instructor coaching for {OPS.loc[c['operator_id'], 'name']}"):
            booking_form(c["operator_id"], f"cbook_{c['key']}", c["module"])
    if not recs:
        st.success("No coaching recommendations right now.")
    section("All instructor bookings")
    bk = data.read("bookings")
    if len(bk):
        st.dataframe(bk.iloc[::-1], hide_index=True, width="stretch")
    else:
        st.caption("No bookings yet.")


def supervisor_app():
    with st.sidebar:
        st.markdown('<div class="brand"><span>CAT</span> Assistant</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card accent" style="margin-top:.6rem"><div class="label">Role</div>'
                    f'<div style="font-weight:700">{REVIEWER}</div><div class="meta">{RBAC_NOTE}</div></div>',
                    unsafe_allow_html=True)
        st.markdown('<div class="nav-group">SUPERVISION</div>', unsafe_allow_html=True)
        page_ = st.radio("Supervisor navigation", SUP_PAGES, key="sup_nav", label_visibility="collapsed")
        st.divider()
        st.radio("Display", ["Dark", "Light"], key="theme", horizontal=True,
                 help="Visual theme only. Layout and behaviour are identical.")
        st.button("🔒 Log out", width="stretch", on_click=logout)
    cases, reviews = all_cases()
    {"📊 Dashboard": sup_dashboard, "📝 Training Reviews": sup_reviews, "👷 Operators": sup_operators,
     "📈 Outcomes": sup_outcomes, "👨‍🏫 Coaching & Bookings": sup_coaching}[page_](cases, reviews)


if st.session_state.get("role") == "Supervisor":
    supervisor_app()
    st.stop()

op_id = st.session_state.operator_id
op = OPS.loc[op_id]
machine_id = op.machine_id
mtype = M.loc[machine_id, "machine_type"]
skill = data.skill_of(op.experience_yrs)
machine_age = int(M.loc[machine_id, "machine_age_yrs"])
now = datetime.now()
my_hist = sessions[sessions.operator_id == op_id].sort_values("timestamp")
last30 = sessions[sessions.timestamp >= now - timedelta(days=30)]
my30 = last30[last30.operator_id == op_id]

if "pending_nav" in st.session_state:
    _page, _lesson = st.session_state.pop("pending_nav")
    st.session_state.nav = _page
    if _lesson:
        st.session_state.lesson = _lesson

# ============================ sidebar ============================
with st.sidebar:
    st.markdown('<div class="brand"><span>CAT</span> Assistant</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="card accent" style="margin-top:.6rem"><div class="label">Operator</div>'
                f'<div style="font-weight:700">{op["name"]} · {op_id}</div><div class="meta">{skill} · {op.experience_yrs} yrs</div>'
                f'<div class="label" style="margin-top:.45rem">Machine</div><div style="font-weight:700">{machine_id} · '
                f'{M.loc[machine_id, "model"]}</div><div class="meta">{mtype} · {machine_age} yrs old</div></div>',
                unsafe_allow_html=True)
    st.markdown('<div class="nav-group">OPERATION</div>', unsafe_allow_html=True)
    page = st.radio("Navigate", PAGES, key="nav", label_visibility="collapsed")
    st.divider()
    st.markdown('<div class="nav-group">SITE CONDITIONS (MANUAL INPUT)</div>', unsafe_allow_html=True)
    weather = st.selectbox("Weather", data.WEATHER)
    temp_c = st.slider("Temperature (°C)", 5, 50, 34)
    visibility = st.select_slider("Visibility", ["Poor", "Moderate", "Good"], value="Good")
    ground = st.selectbox("Ground", ["Firm", "Soft / muddy", "Slope > 15°", "Uneven / rocky"])
    with st.expander("🎬 Demo controls"):
        st.caption("Simulate sensor events for the live demo. They drive the built-in telemetry simulator only.")
        hours_on_shift = st.slider("Hours on shift", 0.0, 12.0, 3.5, 0.5, key="demo_shift_h")
        hours_since_break = st.slider("Hours since last break", 0.0, 8.0, 1.5, 0.5, key="demo_since_break")
        demo = {k: st.toggle(label, key=f"demo_{k}") for k, label in [
            ("unbuckled", "Seatbelt unfastened"), ("person_close", "Worker approaching"), ("parked", "Parked & idling"),
            ("slope", "Machine on steep slope"), ("overspeed", "Overspeed"), ("hot", "Engine overheating")]}
    st.divider()
    st.radio("Display", ["Dark", "Light"], key="theme", horizontal=True,
             help="Visual theme only. Layout and behaviour are identical.")
    end_shift = st.button("🏁 End shift & report", width="stretch")

warnings = an.condition_warnings(weather, temp_c, visibility, ground, hours_on_shift)


# ============================ helpers ============================
def banner(text, kind="red"):
    st.markdown(f'<div class="banner b-{kind}">{text}</div>', unsafe_allow_html=True)


MY_PACE = an.current_pace(sessions, op_id)  # operator's recent actual ÷ planner ratio (history only)


def task_features(r):
    """Model inputs for one of today's tasks under the current site conditions."""
    return dict(task_type=r.task_type, weather=weather, operator_skill=skill, machine_age_yrs=machine_age,
                machine_type=mtype, soil=r.soil, temp_c=temp_c, slope_deg=r.slope_deg, volume_m3=r.volume_m3,
                operator_pace_hist=MY_PACE)


def todays_tasks():
    t = data.read("tasks")
    t = t[t.operator_id == op_id].copy()
    t["scheduled_start"] = pd.to_datetime(t.scheduled_start)
    t["est_min"] = [an.predict_minutes(time_model, **task_features(r)) for r in t.itertuples()]
    t["est_finish"] = t.scheduled_start + pd.to_timedelta(t.est_min, unit="min")
    return t


def machine_hours():
    last = sessions[sessions.machine_id == machine_id].engine_hours.max()
    due = M.loc[machine_id, "last_service_hours"] + data.SERVICE_INTERVAL_H - last
    return last, due


CHECKLIST_ITEMS = ["Tracks / tyres & undercarriage", "No hydraulic or fuel leaks", "Engine oil, coolant & hydraulic levels",
                   "Lights, beacon & horn working", "Mirrors & rear camera clean", "Backup alarm working",
                   "Fire extinguisher present", "Seatbelt & ROPS undamaged"]  # all mandatory


def checklist_done_today():
    """The machine unlocks only after a COMPLETE inspection today (all mandatory items passed)."""
    c = data.read("checklists")
    today = c[(c.operator_id == op_id) & (c.time.str[:10] == now.strftime("%Y-%m-%d"))]
    return bool((pd.to_numeric(today.items_ok, errors="coerce") >= len(CHECKLIST_ITEMS)).any())


def my_profile():
    """Current competency profile + every training loop (recomputed from the database each run)."""
    prof = sk.operator_profile(sessions, standards, op_id)
    loops = sk.training_loops(sessions, standards, op_id, data.read("training_log"))
    return prof, loops


def fatigue_indicator():
    return an.fatigue_risk_indicator(hours_on_shift, hours_since_break, temp_c, len(st.session_state.live_alerts))


# ============================ end-of-shift report ============================
if end_shift:  # the report stays open across reruns until the operator closes it or logs out
    st.session_state.show_report = True
if st.session_state.get("show_report"):
    t = todays_tasks()
    done = t[t.status == "Done"]
    alerts = st.session_state.live_alerts
    prof, loops = my_profile()
    fr_score, fr_level, _ = fatigue_indicator()
    trained_today = data.read("training_log")
    trained_today = trained_today[(trained_today.operator_id == op_id) & (trained_today.time.str[:10] == now.strftime("%Y-%m-%d"))]
    report = f"""# End-of-shift report: {op['name']} ({op_id})
**Date:** {now:%d %b %Y} · **Machine:** {machine_id} ({M.loc[machine_id, 'model']}) · **Shift length:** {hours_on_shift:.1f} h

## Tasks
- Completed: {len(done)} / {len(t)}
{chr(10).join(f"- {r.task_type} at {r.site}: {r.status}" for r in t.itertuples())}

## Safety
- Live alerts this shift: {len(alerts)}
{chr(10).join(f"  - {a['time']} {a['type']}: {a['detail']}" for a in alerts[-10:]) or '  - none'}
- Conditions: {weather}, {temp_c}°C, visibility {visibility}, ground {ground}
- Fatigue risk indicator (operational, not medical): {fr_level} ({fr_score:.0f}/100)

## Machine
- Engine hours: {machine_hours()[0]:.0f} h · next service in {machine_hours()[1]:.0f} h
- Idle share over the last 30 days: {my30.idle_ratio.mean():.0%}

## Skill profile (share of your last 30 sessions meeting each standard)
{chr(10).join(f"- {r.competency}: {r.score:.0f}/100" + (" (skill gap)" if r.gap else "") for r in prof.itertuples() if r.score is not None)}

## Training
- Completed this shift: {', '.join(trained_today.module) or 'none'}
{chr(10).join(f"- {l['module']} ({l['completed'][:10]}) → {l['competency']}: {l['verdict_text']}" for l in loops) or '- No training on record'}
"""
    page_header("End of shift", "Report", f"{op['name']} · {machine_id} · {now:%d %b %Y}")
    st.markdown(report)
    c1, c2, c3 = st.columns(3)
    c1.download_button("⬇️ Download report", report, file_name=f"shift_report_{op_id}_{now:%Y%m%d}.md", width="stretch")
    c2.button("↩ Back to shift", width="stretch", on_click=lambda: st.session_state.pop("show_report", None))
    c3.button("🔒 Log out", type="primary", width="stretch", on_click=logout)
    st.stop()


# ============================ 1. LIVE CAB ============================
def current_task():
    """The task in progress, else the next pending task (None if the day is done)."""
    t = todays_tasks()
    for status in ("In progress", "Pending"):
        cand = t[t.status == status]
        if len(cand):
            return cand.iloc[0]
    return None


def conditions_summary():
    """Worst site-condition level + compact chips (full texts stay available in an expander)."""
    worst = "CRITICAL" if any(l == "error" for l, _, _ in warnings) else "CAUTION" if warnings else "NORMAL"
    chips_html = "".join(chip(f"{icon} {msg.split(':')[0]}", "crit" if level == "error" else "warn") for level, icon, msg in warnings)
    return worst, chips_html or chip("✓ No site-condition warnings", "ok")


def page_live():
    checklist_ok = checklist_done_today()
    page_header("Live Cab", "Operation", f"{machine_id} · {M.loc[machine_id, 'model']} {mtype} · {op['name']}",
                SIM_CHIP + (status_chip("NORMAL", "✓ PRE-START PASSED") if checklist_ok else
                            status_chip("LOCKED", "🔒 LOCKED · PRE-START REQUIRED")))
    if not checklist_ok:
        st.subheader("Pre-start walkaround inspection")
        st.caption("Complete the daily inspection to unlock the machine, as required before every shift. "
                   f"All {len(CHECKLIST_ITEMS)} checks are mandatory.")
        items = CHECKLIST_ITEMS
        with st.form("checklist"):
            cols = st.columns(2)
            ok = [cols[i % 2].checkbox(it) for i, it in enumerate(items)]
            issues = st.text_input("Defects noticed (optional)")
            if st.form_submit_button("✅ Submit inspection & unlock machine", type="primary"):
                failed = [i for i, v in zip(items, ok) if not v]
                data.append("checklists", {"operator_id": op_id, "machine_id": machine_id,
                                           "time": now.strftime("%Y-%m-%d %H:%M"), "items_ok": sum(ok),
                                           "issues": "; ".join(failed + ([issues] if issues else []))})
                if failed:
                    st.error(f"🔒 Machine remains LOCKED in the operator app: {sum(ok)}/{len(items)} checks passed. Not confirmed: "
                             f"{', '.join(failed)}. Recorded in the local checklist log (supervisor notification isn't connected in this prototype). Resolve these, then submit again.")
                else:
                    st.rerun()
        return

    task = current_task()
    worst, cond_chips = conditions_summary()
    if task is not None:
        eta = an.predict_minutes(time_model, **task_features(task))
        task_html = (f'<div class="card accent hero"><div class="label">Current task · {task.task_id} · {task.status}</div>'
                     f'<div class="big">{task.task_type} · {task.site}</div>'
                     f'<div class="eta" style="margin:.3rem 0 .25rem 0">ETA <b>{eta:.0f} min</b> '
                     f'<span class="meta">model · planner {task.estimated_time_min:.0f} min</span></div>'
                     f'<div class="meta">start {task.scheduled_start:%H:%M} · {task.volume_m3} m³ {task.soil.lower()} · slope {task.slope_deg}°'
                     f'{" · 📌 " + task.notes if task.notes else ""}</div>'
                     f'<div style="margin-top:.55rem"><span class="meta" style="margin-right:.4rem">Site conditions · {worst}</span>'
                     f'{cond_chips}</div></div>')
    else:
        task_html = (f'<div class="card accent hero"><div class="label">Current task</div><div class="big">All tasks for today are done</div>'
                     f'<div style="margin-top:.55rem">{cond_chips}</div></div>')
    live_panel(task_html)
    if warnings:
        with st.expander(f"Site condition details ({len(warnings)})"):
            for level, icon, msg in warnings:
                getattr(st, level)(f"{icon} {msg}")
    st.button("☕ Log a break (resets time since break)", on_click=lambda: st.session_state.update(demo_since_break=0.0))


def sensor_states(r, nearest, limit):
    """(signal, value, rule, kind) for one live reading, using the same thresholds as the Live Cab alerts."""
    return [("Seatbelt", "ON" if r["seatbelt"] else "OPEN", "must be fastened while the engine runs", "ok" if r["seatbelt"] else "crit"),
            ("Proximity", f"{nearest[1]:.1f} m · {nearest[2]}", "stop < 3 m · caution < 6 m",
             "crit" if nearest[1] < 3 else "warn" if nearest[1] < 6 else "ok"),
            ("Tilt", f"{r['tilt_deg']}°", "rollover warning > 15°", "crit" if r["tilt_deg"] > 15 else "ok"),
            ("Speed", f"{r['speed_kmh']} km/h", f"site limit {limit} km/h", "warn" if r["speed_kmh"] > limit else "ok"),
            ("Engine coolant", f"{r['engine_temp_c']}°C", "warning > 98°C", "warn" if r["engine_temp_c"] > 98 else "ok")]


@st.fragment(run_every=2)
def live_panel(task_html=""):
    tick = st.session_state.get("tick", 0) + 1
    st.session_state.tick = tick
    r = data.live_reading(mtype, tick, np.random.default_rng(tick), demo)
    nearest = min(r["objects"], key=lambda o: o[1])

    # ---- active alerts (simulated interlock signal) with the sensor evidence behind each one ----
    limit = data.SPEED_LIMIT[mtype]
    active = []  # (colour, type, message, why)
    if not r["seatbelt"]:
        active.append(("red", "Seatbelt", "🪢 SEATBELT UNFASTENED: buckle up now. Travel/hydraulics lock signal raised (simulated interlock)",
                       "Seat-belt switch reports OPEN while the engine is running."))
    if nearest[1] < 3:
        active.append(("red", "Proximity", f"🛑 STOP: {nearest[2]} {nearest[1]:.1f} m away at {nearest[0]:.0f}°. Check before moving",
                       f"Closest detected object {nearest[1]:.1f} m, inside the 3 m stop zone."))
    elif nearest[1] < 6:
        active.append(("amber", "Proximity", f"⚠️ {nearest[2]} within {nearest[1]:.1f} m at {nearest[0]:.0f}°",
                       f"Closest detected object {nearest[1]:.1f} m, inside the 6 m caution zone."))
    if r["tilt_deg"] > 15:
        active.append(("red", "Tilt", f"⛰️ ROLLOVER RISK: tilt {r['tilt_deg']}°. Lower the bucket and move to level ground",
                       f"Inclinometer {r['tilt_deg']}° is above the 15° warning threshold."))
    if r["speed_kmh"] > limit:
        active.append(("amber", "Overspeed", f"🏎️ Overspeed: {r['speed_kmh']} km/h (site limit {limit})",
                       f"Ground speed {r['speed_kmh']} km/h is {r['speed_kmh'] / limit - 1:.0%} above the site limit of {limit} km/h."))
    if r["engine_temp_c"] > 98:
        active.append(("amber", "Engine temp", f"🌡️ Engine temperature {r['engine_temp_c']}°C. Reduce load and let it idle to cool",
                       f"Coolant temperature {r['engine_temp_c']}°C is above the 98°C warning level (ambient {temp_c}°C)."))
    st.session_state.active_alerts = [(typ, msg, why) for _, typ, msg, why in active]
    st.session_state.last_reading = {**r, "nearest": nearest, "limit": limit, "time": datetime.now().strftime("%H:%M:%S")}
    # Edge-triggered logging: record a condition only on its inactive → active transition. Each condition type
    # is tracked independently; while it stays active nothing is re-logged, and once it clears it can log again.
    was_active = st.session_state.get("alert_active", set())
    for _, typ, msg, why in active:
        if typ not in was_active:
            st.session_state.live_alerts.append({"time": datetime.now().strftime("%H:%M:%S"), "type": typ, "detail": msg, "why": why})
    st.session_state.alert_active = {typ for _, typ, _, _ in active}

    # ---- 1. current task (hero) + overall machine/safety state ----
    level = "CRITICAL" if any(k == "red" for k, *_ in active) else "CAUTION" if active else "NORMAL"
    sig = [(n, v, k) for n, v, _, k in sensor_states(r, nearest, limit)]
    top_l, top_r = st.columns([1.3, 1])
    with top_l:
        st.markdown(task_html, unsafe_allow_html=True)
    with top_r:
        state_panel(level, "All systems normal. Safe to operate" if not active else
                    f"{len(active)} active safety condition{'s' if len(active) > 1 else ''}. Act on the red items first",
                    "".join(chip(f"{n}: {v}", k) for n, v, k in sig)
                    + f" <span class='chip sim'>simulated reading #{tick} · {datetime.now():%H:%M:%S}</span>")

    # ---- 2. active safety conditions dominate everything below ----
    for kind, typ, msg, why in sorted(active, key=lambda x: x[0] != "red"):
        banner(msg, kind)
        st.caption(f"Why: {why}")
    if any(typ == "Tilt" for _, typ, _, _ in active):
        if st.button("🎓 Terrain awareness · 42 sec lesson: Safe operation on sloped terrain", key="tilt_lesson"):
            navigate("🎓 Training Hub", "terrain")
            st.rerun(scope="app")

    # Micro-learning: only while parked and idling (never while the machine is moving)
    st.session_state.idle_ticks = st.session_state.get("idle_ticks", 0) + 1 if r["idling"] else 0
    idle_s = st.session_state.idle_ticks * 2
    if r["idling"] and r["speed_kmh"] == 0 and idle_s >= 4:
        tip = IDLE_TIPS[(tick // 4) % len(IDLE_TIPS)]
        st.info(f"💤 **Parked & idling for {idle_s // 60}m {idle_s % 60:02d}s.** Shut down if you'll wait more than 5 minutes "
                f"(idling burns ~3.5 L/h).  \n🎓 **Quick lesson while you wait:** {tip}")

    # ---- 3. hazard awareness (radar) + critical telemetry + supporting readouts ----
    g_radar, g_tel, g_side = st.columns([1.3, 1.05, .85])
    with g_radar:
        fig = go.Figure()
        for radius, color in [(3, "rgba(229,72,77,.30)"), (6, "rgba(245,165,36,.18)"), (15, "rgba(47,180,99,.07)")]:
            fig.add_trace(go.Barpolar(r=[radius], theta=[0], width=[360], marker_color=color,
                                      hoverinfo="skip", showlegend=False, base=0))
        fig.data = fig.data[::-1]
        th, rr, kinds = zip(*r["objects"])
        colors = [RED if d < 3 else AMBER if d < 6 else GREEN for d in rr]
        symbols = {"Worker": "circle", "Vehicle": "square", "Structure": "diamond"}
        fig.add_trace(go.Scatterpolar(r=[min(d, 14.5) for d in rr], theta=th, mode="markers+text",
                                      text=[f"{k} {d:.1f}m" for k, d in zip(kinds, rr)], textposition="top center",
                                      marker=dict(size=14, color=colors, symbol=[symbols[k] for k in kinds],
                                                  line=dict(color="white", width=1)), showlegend=False))
        fig.add_trace(go.Scatterpolar(r=[0], theta=[0], mode="markers", marker=dict(size=22, color=CAT_YELLOW,
                                      symbol="square", line=dict(color=CAT_BLACK, width=2)), showlegend=False))
        fig.update_layout(title="Proximity radar · 360° (simulated sensors)", height=410, margin=dict(t=48, b=16, l=28, r=28),
                          polar=dict(radialaxis=dict(range=[0, 15], ticksuffix=" m"),
                                     angularaxis=dict(direction="clockwise", rotation=90)))
        hmi_chart(st, fig, width="stretch")
    with g_tel:
        section("Critical telemetry")
        c = st.columns(2)
        c[0].metric("Speed", f"{r['speed_kmh']} km/h", f"limit {limit} km/h", delta_color="off", delta_arrow="off")
        c[1].metric("Tilt", f"{r['tilt_deg']}°", "warn > 15°", delta_color="off", delta_arrow="off")
        c[0].metric("Engine temp", f"{r['engine_temp_c']}°C", "warn > 98°C", delta_color="off", delta_arrow="off")
        c[1].metric("Engine rpm", f"{r['engine_rpm']}")
        rows = [("Load", f"{r['load_pct']}%"), ("Fuel rate", f"{r['fuel_rate_lph']} L/h"),
                ("Seatbelt", status_chip("NORMAL", "ON") if r["seatbelt"] else status_chip("CRITICAL", "OPEN")),
                ("State", "Idle" if r["idling"] else "Working")]
        card("".join(f'<div class="row"><span class="meta">{n}</span><span class="v">{v}</span></div>' for n, v in rows))
    with g_side:
        section("Nearest object")
        card(f'<div class="big">{nearest[2]} · {nearest[1]:.1f} m</div>'
             f'<div class="meta">bearing {nearest[0]:.0f}° · stop &lt; 3 m · caution &lt; 6 m</div>')
        fr, flevel, factors = fatigue_indicator()
        fk = {"Low": "ok", "Elevated": "warn", "High": "crit"}[flevel]
        section("Fatigue risk indicator")
        st.markdown(f'<div class="card"><div class="big">{chip(flevel.upper(), fk)} {fr:.0f}/100</div>'
                    f'<div class="meta">Operational indicator, not a medical assessment</div></div>', unsafe_allow_html=True)
        st.caption(f"Fatigue risk indicator: {flevel} ({fr:.0f}/100)")
        st.progress(fr / 100)
        with st.popover("What is this based on?", width="stretch"):
            st.caption("A rule-based operational risk indicator from observable shift signals. It is NOT a medical "
                       "or validated measure of fatigue: take a break whenever you feel tired.")
            st.dataframe(pd.DataFrame(factors, columns=["factor", "points", "value"]), hide_index=True)

    with st.expander("Alert thresholds used by this screen"):
        st.markdown(f"- **Seatbelt:** open while the engine runs → red (travel and hydraulics lock signal; UI only in this prototype)\n"
                    f"- **Proximity:** < 3 m → red STOP · < 6 m → amber caution\n- **Tilt:** > 15° → red rollover warning\n"
                    f"- **Speed:** > {limit} km/h (site limit for {mtype}) → amber\n- **Engine coolant:** > 98 °C → amber\n"
                    "- Readings come from the built-in simulator (`data.live_reading`) every 2 s; demo controls change them.")
    if st.session_state.live_alerts:
        # Open/closed state is kept in session_state so the 2 s telemetry refresh doesn't collapse it
        with st.expander(f"📜 Alert log this shift ({len(st.session_state.live_alerts)}), recorded automatically",
                         expanded=st.session_state.get("alert_log_open", False), key="alert_log_exp",
                         on_change=lambda: st.session_state.update(alert_log_open=bool(st.session_state.get("alert_log_exp")))):
            st.dataframe(pd.DataFrame(st.session_state.live_alerts).iloc[::-1], hide_index=True, width="stretch")


# ============================ 2. MY DAY ============================
PRIORITY_KIND = {"High": "crit", "Medium": "warn", "Low": "info"}


def page_day():
    t = todays_tasks()
    last_h, due = machine_hours()
    n_done = int((t.status == "Done").sum())
    page_header(f"Hello, {op['name'].split()[0]}", "Operation · My Day",
                f"{now:%A %d %b} · {weather}, {temp_c}°C · estimates from the task-time model (±{time_mae:.0f} min typical error)",
                chip(f"{n_done}/{len(t)} tasks done", "ok" if n_done == len(t) else "")
                + chip(f"🔧 service estimate · {due:.0f} engine h", "warn" if due < 60 else ""))
    k = st.columns(4)
    k[0].metric("Tasks today", len(t), f"{n_done} done")
    k[1].metric("Planned work", f"{t.est_min.sum() / 60:.1f} h", "AI estimate")
    k[2].metric("Service estimate", f"{due:.0f} h", "engine hours remaining", delta_color="off", delta_arrow="off")
    k[3].metric("Site warnings", len(warnings))
    if due < 60:
        st.warning(f"🔧 Service estimate: {machine_id} is due in about {due:.0f} engine hours (from the seeded service history). Plan maintenance this week.")

    nxt = t[t.status != "Done"].head(1)
    if len(nxt):
        n = nxt.iloc[0]
        a, b = st.columns([2.2, 1])
        with a:
            status_kind = "cat" if n.status == "In progress" else ""
            card(f'<div class="label">{"Active task" if n.status == "In progress" else "Up next"} · {n.task_id}</div>'
                 f'<div class="big">{n.task_type} · {n.site}</div>'
                 f'<div style="margin:.35rem 0">{chip(n.status.upper(), status_kind)}{chip(n.priority.upper() + " PRIORITY", PRIORITY_KIND[n.priority])}'
                 f'{chip(f"start {n.scheduled_start:%H:%M}")}{chip(f"{n.volume_m3} m³ {n.soil.lower()}")}{chip(f"slope {n.slope_deg}°")}</div>'
                 f'<div class="eta">ETA <b>{n.est_min:.0f} min</b> <span class="meta">model ETA · planner '
                 f'{n.estimated_time_min:.0f} min · {weather.lower()}, {temp_c}°C · ±{time_mae:.0f} min typical error</span></div>',
                 accent=True, extra="hero")
            if n.status == "In progress" and isinstance(n.started_at, str) and n.started_at:
                elapsed = (datetime.now() - pd.Timestamp(n.started_at)).total_seconds() / 60
                st.progress(min(1.0, max(0.0, elapsed / n.est_min)),
                            text=f"{elapsed:.0f} min elapsed of ~{n.est_min:.0f} min (model ETA)"
                                 + (f" · {elapsed - n.est_min:.0f} min over" if elapsed > n.est_min else ""))
            else:
                st.progress(0.0, text="Not started")
            if n.notes:
                st.warning(f"📌 Site note: {n.notes}")
            with st.expander("Why this estimate? (factors the model used)"):
                _, why = an.explain_prediction(time_model, task_features(n), tmod["reference"])
                st.caption("Each row shows how many minutes the estimate changes if that input were at the site-typical value. "
                           "Only inputs the model actually uses are listed. The weather and temperature come from the sidebar.")
                st.dataframe(why.rename(columns={"effect_min": "effect (min)"}), hide_index=True, width="stretch")
        with b:
            if n.status == "Pending" and st.button("▶️ Start task", type="primary", width="stretch"):
                data.update_task(n.task_id, status="In progress", started_at=datetime.now().strftime("%Y-%m-%d %H:%M"))
                st.rerun()
            if n.status == "In progress" and st.button("✅ Mark complete", type="primary", width="stretch"):
                data.update_task(n.task_id, status="Done", completed_at=datetime.now().strftime("%Y-%m-%d %H:%M"))
                st.balloons()
                st.rerun()
            upcoming = t[(t.status != "Done") & (t.task_id != n.task_id)]
            rows = "".join(
                f'<div style="display:flex;justify-content:space-between;gap:.5rem;padding:.4rem 0;border-top:1px solid var(--border)">'
                f'<div><b>{r.scheduled_start:%H:%M}</b> {r.task_type}<div class="meta">{r.site} · {r.task_id}</div></div>'
                f'<div style="text-align:right">{r.est_min:.0f} min<div class="meta">planner {r.estimated_time_min:.0f}</div></div></div>'
                for r in upcoming.itertuples())
            card(f'<div class="label">Upcoming ({len(upcoming)})</div>{rows or "<div class=meta>Nothing else scheduled</div>"}')
    else:
        state_panel("NORMAL", "All tasks for today are done")

    gap = t.est_min.sum() - t.estimated_time_min.sum()
    if abs(gap) > 15:
        pace_txt = f", your recent pace ({MY_PACE:.2f}× planner estimates)" if not np.isnan(MY_PACE) else ""
        st.info(f"🤖 Given {weather.lower()} weather, {temp_c}°C, your skill level ({skill}){pace_txt} and the machine's age "
                f"({machine_age} yrs), the AI expects today's work to take **{abs(gap):.0f} min {'longer' if gap > 0 else 'less'}** "
                "than the planner's schedule.")
    overlap = (t.est_finish.iloc[:-1].values > t.scheduled_start.iloc[1:].values).sum()
    if overlap:
        st.warning(f"⚠️ With today's conditions, {overlap} task(s) will run into the next scheduled task. "
                   "The assistant suggests starting high-priority work first and moving low-priority tasks.")
    tl = t.assign(label=t.task_id + " · " + t.task_type)
    fig = px.timeline(tl, x_start="scheduled_start", x_end="est_finish", y="label", color="status",
                      color_discrete_map={"Done": GREEN, "In progress": CAT_YELLOW, "Pending": GREY},
                      hover_data=["site", "volume_m3", "estimated_time_min"], title="Timeline with model-estimated durations")
    fig.update_yaxes(autorange="reversed", title=None)
    fig.add_vline(x=datetime.now(), line_dash="dot", line_color=CAT_YELLOW)
    hmi_chart(st, fig, width="stretch")

    with st.expander("Full schedule table"):
        icon = {"Done": "✅", "In progress": "🔄", "Pending": "⏳"}
        st.dataframe(t.assign(status=t.status.map(lambda s: f"{icon[s]} {s}"), start=t.scheduled_start.dt.strftime("%H:%M"),
                              est=t.est_min.round(), finish=t.est_finish.dt.strftime("%H:%M"))
                     [["task_id", "start", "task_type", "site", "soil", "volume_m3", "priority", "status",
                       "estimated_time_min", "est", "finish", "notes"]],
                     hide_index=True, width="stretch",
                     column_config={"est": st.column_config.NumberColumn("🤖 AI est. (min)", format="%d"),
                                    "estimated_time_min": st.column_config.NumberColumn("Planner est. (min)", format="%d"),
                                    "volume_m3": "m³"})


# ============================ 3. SAFETY CENTER ============================
KIND_LEVEL = {"ok": "NORMAL", "warn": "CAUTION", "crit": "CRITICAL"}
LEVEL_RANK = {"NORMAL": 0, "CAUTION": 1, "CRITICAL": 2}
CONDITION_RULES = [("🌡️", "Heat", lambda: f"{temp_c}°C", "≥ 35°C caution · ≥ 40°C critical"),
                   ("🌧️", "Slippery ground", lambda: f"{weather} · {ground}", "Rainy weather or soft/muddy ground"),
                   ("💨", "Wind", lambda: weather, "Windy weather"),
                   ("🌫️", "Visibility", lambda: f"{weather} · {visibility}", "Foggy/Dusty or poor visibility"),
                   ("⛰️", "Steep slope", lambda: ground, "Ground marked slope > 15°"),
                   ("⏱️", "Shift length", lambda: f"{hours_on_shift:.1f} h (demo slider)", "≥ 8 h caution · ≥ 10 h critical")]


def page_safety():
    rd = st.session_state.get("last_reading")
    sensors = sensor_states(rd, rd["nearest"], rd["limit"]) if rd else []
    by_icon = {icon: (lvl, msg) for lvl, icon, msg in warnings}
    cond_rows = [(name, value(), rule, ("crit" if by_icon[icon][0] == "error" else "warn") if icon in by_icon else "ok")
                 for icon, name, value, rule in CONDITION_RULES]
    levels = [KIND_LEVEL[k] for *_, k in sensors] + [KIND_LEVEL[k] for *_, k in cond_rows]
    overall = max(levels, key=LEVEL_RANK.get) if levels else "NORMAL"
    n_crit, n_warn = levels.count("CRITICAL"), levels.count("CAUTION")
    page_header("Safety Center", "Operation", "Machine status, site conditions, history and incidents",
                SIM_CHIP + chip(overall, STATE_CLASS[overall]))
    state_panel(overall, "No active safety conditions" if overall == "NORMAL" else
                f"{n_crit} critical · {n_warn} caution condition(s)",
                "Combines the last simulated sensor reading from Live Cab with today's site conditions.")

    def rows_html(rows):
        return "".join(f'<div style="display:flex;justify-content:space-between;align-items:center;gap:.6rem;padding:.45rem 0;'
                       f'border-top:1px solid var(--border)"><div><b>{n}</b><div class="meta">{rule}</div></div>'
                       f'<div style="text-align:right"><div style="font-family:var(--display);font-size:1.05rem">{v}</div>'
                       f'{chip(KIND_LEVEL[k], k)}</div></div>' for n, v, rule, k in rows)

    a, b = st.columns(2)
    with a:
        if rd:
            card(f'<div class="label">Machine sensors · last simulated reading {rd["time"]}</div>{rows_html(sensors)}')
        else:
            card('<div class="label">Machine sensors</div><div class="big" style="font-size:1.1rem">No live reading yet</div>'
                 '<div class="meta">Open Live Cab (after the pre-start inspection) to stream simulated telemetry. '
                 'This panel then shows the latest reading.</div>')
    with b:
        card(f'<div class="label">Site conditions · manual input + shift slider</div>{rows_html(cond_rows)}')
    todo = [SAFETY_ACTIONS[{"Speed": "Overspeed", "Engine coolant": "Engine temp"}.get(n, n)] for n, _, _, k in sensors if k != "ok"]
    if todo:
        section("What to do now")
        card("".join(f'<div class="row"><span>{t}</span></div>' for t in todo), accent=True)
    section("Site guidance")
    for level, icon, msg in warnings:
        getattr(st, level)(f"{icon} {msg}")
    if not warnings:
        st.success("✅ Site conditions are normal. No condition-based warnings.")

    k = st.columns(4)
    k[0].metric("Seatbelt compliance (30d)", f"{(my30.seatbelt_status == 'Fastened').mean():.0%}")
    k[1].metric("Sessions with alerts", f"{(my30.safety_alert_triggered == 'Yes').mean():.0%}")
    k[2].metric("Proximity alerts", int(my30.proximity_alerts.sum()))
    k[3].metric("Safety discipline", f"{standards.loc[my30.index, 'safety'].mean() * 100:.0f}/100",
                help="Share of your sessions in the last 30 days with seatbelt fastened, speed within the limit and no overload")

    tab_trend, tab_prox, tab_inc = st.tabs(["📈 Trends (history)", "📡 Proximity history", "📝 Incident log"])
    with tab_trend:
        st.caption("From recorded (synthetic) session history.")
        a, b = st.columns(2)
        with a:
            wk = my_hist.set_index("timestamp").resample("W").agg(
                seatbelt=("seatbelt_status", lambda x: (x == "Fastened").mean() * 100)).reset_index()
            fig = px.line(wk, x="timestamp", y="seatbelt", markers=True, title="Weekly seatbelt compliance (%)",
                          color_discrete_sequence=[STEEL])
            fig.add_hline(y=100, line_dash="dot", line_color=GREEN)
            fig.update_yaxes(range=[0, 105], title=None)
            hmi_chart(st, fig, width="stretch")
        with b:
            al = my_hist[my_hist.alert_types != ""].assign(alert=lambda d: d.alert_types.str.split(", ")).explode("alert")
            al["week"] = al.timestamp.dt.to_period("W").dt.start_time
            fig = px.bar(al.groupby(["week", "alert"]).size().reset_index(name="count"), x="week", y="count",
                         color="alert", title="My safety alerts by type",
                         color_discrete_sequence=[RED, AMBER, CAT_YELLOW, STEEL, GREY])
            hmi_chart(st, fig, width="stretch")
    with tab_prox:
        st.subheader("Proximity hazards: closest approaches")
        fig = px.scatter(my_hist, x="timestamp", y="min_proximity_m", color=my_hist.min_proximity_m < 3,
                         color_discrete_map={True: RED, False: GREY}, hover_data=["site", "task_type"],
                         labels={"min_proximity_m": "Closest person/object (m)", "color": "< 3 m"})
        fig.add_hrect(y0=0, y1=3, fillcolor="red", opacity=.08, line_width=0)
        hmi_chart(st, fig, width="stretch")
    with tab_inc:
        with st.form("incident", clear_on_submit=True):
            a, b, c = st.columns(3)
            typ = a.selectbox("Type", ["Near miss", "Equipment damage", "Injury", "Unsafe condition", "Environmental", "Other"])
            sev = b.select_slider("Severity", ["Low", "Medium", "High", "Critical"])
            loc = c.selectbox("Location", list(data.SITES))
            desc = st.text_area("What happened?", placeholder="Describe what happened and any immediate action taken")
            if st.form_submit_button("Log incident", type="primary") and desc.strip():
                data.append("incidents", {"time": datetime.now().strftime("%Y-%m-%d %H:%M"), "operator_id": op_id,
                                          "machine_id": machine_id, "type": typ, "severity": sev,
                                          "description": f"[{loc}] {desc}"})
                st.success("Incident saved to the local incident log. Supervisor notification isn't connected in this prototype.")
        inc = data.read("incidents")
        st.dataframe(inc.iloc[::-1], hide_index=True, width="stretch")


# ============================ 4. MACHINE INSIGHTS ============================
def page_insights():
    ev = an.evaluate_detector(sessions)
    page_header("Machine Insights", "Intelligence", "Idle cost, unusual machine usage (Isolation Forest) and maintenance · "
                "computed from recorded synthetic history", chip(f"{int(sessions.is_anomaly.sum())} sessions flagged", "warn")
                + chip(f"detector recall {ev['recall_usage']:.0%} on synthetic labels", "info"))
    fleet = last30.groupby("machine_id").agg(idle=("idle_ratio", "mean"), idle_fuel=("idle_fuel_l", "sum"),
                                             fuel=("fuel_used_l", "sum")).reset_index()
    fleet["idle"] *= 100
    mine = fleet.set_index("machine_id").loc[machine_id]
    k = st.columns(4)
    k[0].metric("My idle time (30d)", f"{mine.idle:.0f}%", f"{mine.idle - 20:+.0f} pts vs 20% standard", delta_color="inverse")
    k[1].metric("Fuel burned idling", f"{mine.idle_fuel:.0f} L")
    k[2].metric("Estimated idling cost", f"₹{mine.idle_fuel * an.FUEL_PRICE:,.0f}", help="Assumes 3.5 L/h idle burn and ₹95/L")
    k[3].metric("Estimated CO₂ from idling", f"{mine.idle_fuel * an.CO2_PER_L:.0f} kg", help="2.68 kg CO₂ per litre of diesel")

    a, b = st.columns(2)
    with a:
        f = fleet.sort_values("idle")
        fig = px.bar(f, x="idle", y="machine_id", orientation="h", title="Fleet idle time, last 30 days (%)",
                     color=f.idle > 20, color_discrete_map={True: RED, False: CAT_YELLOW}, hover_data=["idle_fuel"])
        fig.add_vline(x=20, line_dash="dot", annotation_text="excessive")
        fig.update_layout(showlegend=False, yaxis_title=None)
        hmi_chart(st, fig, width="stretch")
    with b:
        d = my_hist.set_index("timestamp").resample("D").agg(idle=("idling_time_min", "sum"),
                                                            total=("duration_min", "sum")).query("total > 0")
        d["idle_pct"] = d.idle / d.total * 100
        fig = px.area(d.reset_index(), x="timestamp", y="idle_pct", title=f"{machine_id} daily idle %",
                      color_discrete_sequence=[CAT_YELLOW])
        hmi_chart(st, fig, width="stretch")

    st.subheader("🧠 AI-detected unusual machine behaviour")
    st.caption("An Isolation Forest (5% contamination) scores every session on robust z-scores of idle share, fuel burn, "
               "load-cycle rate, speed vs limit, tilt and engine temperature, each computed within the machine type.")
    scope = st.radio("Scope", ["My machine", "Whole fleet"], horizontal=True)
    an_df = sessions[sessions.is_anomaly & ((sessions.machine_id == machine_id) | (scope == "Whole fleet"))] \
        .sort_values("timestamp", ascending=False)
    fig = px.scatter(sessions[(sessions.machine_id == machine_id) | (scope == "Whole fleet")], x="timestamp",
                     y="anomaly_score", color="is_anomaly", color_discrete_map={True: RED, False: "#d0d0d0"},
                     hover_data=["machine_id", "operator_id", "task_type", "reason"], title="Anomaly score per session")
    hmi_chart(st, fig, width="stretch")
    if len(an_df):
        pick = st.selectbox("Inspect a flagged session", an_df.index,
                            format_func=lambda i: f"{an_df.loc[i, 'timestamp']:%d %b %H:%M} · {an_df.loc[i, 'machine_id']} · "
                                                  f"{an_df.loc[i, 'task_type']} · {an_df.loc[i, 'reason']}")
        ex = an.explain_anomaly(sessions, pick)
        with st.container(border=True):
            st.markdown(f"#### ⚠️ {ex['title']}")
            st.markdown("**Evidence:** this session vs the operator's own median and the site median for this machine type "
                        "(both computed from recorded sessions, excluding this one)")
            st.dataframe(ex["evidence"], hide_index=True, width="stretch")
            st.markdown("**Context:** " + " · ".join(f"{k}: {v}" for k, v in ex["context"].items()))
            st.markdown(f"**Recommendation:** {ex['recommendation']}")
    with st.expander("How well does the detector work? (validation on labelled synthetic anomalies)"):
        ev = an.evaluate_detector(sessions)
        st.markdown(f"- The data generator secretly injected **{ev['n_usage']} abnormal idle/fuel sessions**. The detector flagged "
                    f"**{ev['recall_usage']:.0%}** of them.\n"
                    f"- Of the **{ev['n_flagged']} flagged sessions**, **{ev['flag_explained']:.0%}** have a known cause (an injected "
                    f"anomaly or a safety-threshold breach), vs a {ev['base_rate_known']:.0%} base rate across all sessions.\n"
                    "- The labels exist only because the data is synthetic. On real machines this would need labelled incidents.")

    st.subheader("⚠️ Unusual operation patterns (30 days)")
    pats = pd.DataFrame({
        "Pattern": ["Seatbelt unfastened", "Proximity < 3 m", "Excessive tilt > 15°", "Overspeed", "Overload", "Harsh braking/turning"],
        "Me": [int((my30.seatbelt_status == "Unfastened").sum()), int(my30.proximity_alerts.sum()),
               int((my30.max_tilt_deg > 15).sum()), int((my30.speed_vs_limit > 1).sum()),
               int(my30.overload_events.sum()), int(my30.harsh_events.sum())],
    })
    per_op = last30.groupby("operator_id")
    pats["Fleet average"] = [round(v, 1) for v in [
        per_op.seatbelt_status.apply(lambda x: (x == "Unfastened").sum()).mean(), per_op.proximity_alerts.sum().mean(),
        per_op.max_tilt_deg.apply(lambda x: (x > 15).sum()).mean(), per_op.speed_vs_limit.apply(lambda x: (x > 1).sum()).mean(),
        per_op.overload_events.sum().mean(), per_op.harsh_events.sum().mean()]]
    hmi_chart(st, px.bar(pats.melt("Pattern"), x="Pattern", y="value", color="variable", barmode="group",
                           color_discrete_sequence=[STEEL, CAT_YELLOW]), width="stretch")

    last_h, due = machine_hours()
    st.subheader("🔧 Maintenance")
    st.progress(min(1.0, (data.SERVICE_INTERVAL_H - due) / data.SERVICE_INTERVAL_H),
                text=f"Service estimate · {due:.0f} engine hours remaining (engine hours {last_h:.0f}; {data.SERVICE_INTERVAL_H} h interval; seeded service history)")


# ============================ 5. TASK ESTIMATOR ============================
def page_estimator():
    page_header("Task Time Estimator", "Intelligence", "HistGradientBoosting model vs the planner baseline · "
                "evaluated on held-out later sessions of synthetic data",
                chip(f"MAE {tm['ai_mae']:.1f} vs {tm['planner_mae']:.1f} min", "cat") + chip("synthetic evaluation", "sim"))
    lo, hi = tm["reduction_ci"]
    (tr0, tr1), (te0, te1) = tm["train_period"], tm["test_period"]
    k = st.columns(4)
    k[0].metric("🤖 Model MAE", f"{tm['ai_mae']:.1f} min", f"{tm['ai_mape']:.0%} of task time", delta_color="off")
    k[1].metric("📋 Planner MAE", f"{tm['planner_mae']:.1f} min", f"{tm['planner_mape']:.0%} of task time", delta_color="off")
    k[2].metric("MAE reduction vs planner", f"{tm['reduction']:.1%}", f"95% CI {lo:.1%} to {hi:.1%}", delta_color="off")
    k[3].metric("Tasks within ±10%", f"{tm['ai_within_10']:.0%}", f"planner: {tm['planner_within_10']:.0%}", delta_color="off")
    st.caption(f"On our held-out **synthetic** test set ({tm['n_test']} sessions from {te0:%d %b}–{te1:%d %b}, all later than the "
               f"{tm['n_train']} training sessions from {tr0:%d %b}–{tr1:%d %b}), mean absolute error fell from "
               f"{tm['planner_mae']:.1f} min for the planner baseline to {tm['ai_mae']:.1f} min for the model. A task-type "
               f"median baseline scores {tm['type_median_mae']:.1f} min. The confidence interval is a 1,000-sample bootstrap.")

    tab_pred, tab_eval, tab_batch = st.tabs(["🔮 Predict a task", "📈 How we evaluated it", "📂 Estimate a task list"])
    with tab_pred:
        a, b, c = st.columns(3)
        own = data.TASK_TYPES[mtype]
        e_task = a.selectbox("Task type", data.ALL_TASKS, index=data.ALL_TASKS.index(own[0]))
        e_weather = a.selectbox("Weather ", data.WEATHER, index=data.WEATHER.index(weather))
        e_skill = b.selectbox("Operator skill", data.SKILLS, index=data.SKILLS.index(skill))
        e_age = b.slider("Machine age (yrs)", 0, 15, machine_age)
        e_vol = c.slider("Volume (m³)", 20, 200, 80, 5)
        fits = [t for t, tasks in data.TASK_TYPES.items() if e_task in tasks]
        with st.expander("Site & operating context"):
            x, y, z = st.columns(3)
            e_mtype = x.selectbox("Machine type", fits, index=fits.index(mtype) if mtype in fits else 0)
            e_soil = x.selectbox("Soil", data.SOILS, index=2)
            e_slope = y.slider("Slope (°)", 0, 20, 4)
            e_temp = z.slider("Temperature (°C) ", 5, 50, temp_c)
            use_pace = y.checkbox(f"Use my past pace ({MY_PACE:.2f}× planner)", value=not np.isnan(MY_PACE),
                                  disabled=bool(np.isnan(MY_PACE)))
        params = dict(task_type=e_task, weather=e_weather, operator_skill=e_skill, machine_age_yrs=e_age,
                      machine_type=e_mtype, soil=e_soil, temp_c=e_temp, slope_deg=e_slope, volume_m3=e_vol,
                      operator_pace_hist=MY_PACE if use_pace else np.nan)
        est, why = an.explain_prediction(time_model, params, tmod["reference"])
        planner = data.planner_estimate_min(e_task, e_soil, e_vol, e_weather)
        m1, m2, m3 = st.columns(3)
        m1.metric("🤖 Model estimate", f"{est:.0f} min", f"typical error ±{time_mae:.0f} min", delta_color="off")
        m2.metric("📋 Planner's standard estimate", f"{planner:.0f} min", f"{planner - est:+.0f} min vs model", delta_color="off")
        m3.metric("Estimated finish if started now", (datetime.now() + timedelta(minutes=est)).strftime("%H:%M"))
        st.markdown("**Contributing factors for this prediction**")
        st.caption("Minutes added (+) or saved (−) compared with the site-typical value of each input. Only the model's inputs "
                   "are shown. Values are computed by substitution, so they are indicative and don't add up exactly.")
        st.dataframe(why.rename(columns={"effect_min": "effect (min)"}), hide_index=True, width="stretch")

        p, q = st.columns(2)
        with p:
            grid = pd.DataFrame([[an.predict_minutes(time_model, **{**params, "weather": w, "operator_skill": s_})
                                  for w in data.WEATHER] for s_ in data.SKILLS], index=data.SKILLS, columns=data.WEATHER)
            fig = px.imshow(grid.round(), text_auto=True, aspect="auto", color_continuous_scale=["#FFF8D6", CAT_YELLOW, RED],
                            title="What if? Minutes by weather × operator skill", labels=dict(color="min"))
            hmi_chart(st, fig, width="stretch")
        with q:
            hmi_chart(st, px.bar(importance, orientation="h", title="Global importance on the test set (% of permutation importance)",
                                   color_discrete_sequence=[STEEL]).update_layout(showlegend=False, yaxis_title=None,
                                                                                      xaxis_title=None), width="stretch")
    with tab_eval:
        st.markdown(f"""
- **Target:** actual task time (min). **Model:** scikit-learn HistGradientBoostingRegressor with one-hot encoded categories.
- **Inputs (all known before a task starts):** {', '.join(an.FEATURE_LABELS[f] for f in an.TIME_FEATURES)}.
  Nothing measured during or after the task (idle time, fuel, cycles, alerts) is used.
- **Operator's past pace** is the median actual ÷ planner ratio over that operator's previous {an.PACE_WINDOW} sessions from *earlier days only*.
- **Split:** temporal. Train on the first 80% of days, test on the last 20%. The deployed model is then refit on all history.
- **Baselines:** the planner's estimate (standard rate × soil, plus a rain/fog allowance) and the task-type median.
- **Bias:** model {tm['ai_bias']:+.1f} min, planner {tm['planner_bias']:+.1f} min (negative = underestimate).
- **Caveat:** the data is synthetic. The generator has an observable part the model can learn, plus unobserved
  operator pace, machine condition, daily site disruption, ~10% per-task noise and 5% random delays, so a perfect score is impossible.
""")
        te = sessions[sessions.in_test_set]
        lim = [0, float(te.duration_min.quantile(.99))]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=te.duration_min, y=te.estimated_time_min, mode="markers", name="📋 Planner estimate",
                                 marker=dict(color=CAT_YELLOW, size=7, line=dict(color="#b38f00", width=1))))
        fig.add_trace(go.Scatter(x=te.duration_min, y=te.predicted_min, mode="markers", name="🤖 Model prediction",
                                 marker=dict(color=STEEL, size=6, opacity=.7)))
        fig.add_trace(go.Scatter(x=lim, y=lim, mode="lines", name="Perfect estimate", line=dict(dash="dot", color=GREY)))
        fig.update_layout(title="Estimate vs actual on the held-out later sessions (closer to the line is better)",
                          xaxis_title="Actual time (min)", yaxis_title="Estimated time (min)", xaxis_range=lim, yaxis_range=lim)
        hmi_chart(st, fig, width="stretch")
        err = pd.concat([pd.DataFrame({"error_min": te.predicted_min - te.duration_min, "who": "🤖 Model"}),
                         pd.DataFrame({"error_min": te.estimated_time_min - te.duration_min, "who": "📋 Planner"})])
        fig = px.histogram(err, x="error_min", color="who", barmode="overlay", nbins=60, opacity=.75,
                           color_discrete_map={"🤖 Model": STEEL, "📋 Planner": CAT_YELLOW},
                           title="Estimation error on the test set (min)")
        fig.add_vline(x=0, line_dash="dot")
        hmi_chart(st, fig, width="stretch")
        st.markdown("**Test-set sample in the organisers' format, with the model's prediction added**")
        st.dataframe(data.task_format(te).assign(**{"🤖 Model Predicted (min)": te.predicted_min.round().astype(int)}).head(12),
                     hide_index=True, width="stretch")
    with tab_batch:
        st.caption("Upload a task list in the organisers' format (Task ID, Task Type, Weather, Operator Skill, Machine Age (yrs), "
                   "Estimated Time (min)). The model adds its own prediction for each task. The organisers' example is loaded by default.")
        example = pd.DataFrame({"Task ID": ["T001", "T002", "T003", "T004", "T005"],
                                "Task Type": ["Earth Excavation", "Trenching", "Material Loading", "Grading", "Demolition"],
                                "Weather": ["Sunny", "Rainy", "Cloudy", "Sunny", "Windy"],
                                "Operator Skill": ["Expert", "Intermediate", "Beginner", "Expert", "Intermediate"],
                                "Machine Age (yrs)": [2, 4, 3, 5, 6], "Estimated Time (min)": [60, 45, 30, 35, 90],
                                "Actual Time (min)": [58, 52, 42, 33, 105]})
        up = st.file_uploader("Task list (CSV)", type="csv")
        tl = pd.read_csv(up) if up else example
        if not up:
            st.download_button("⬇️ Download template", example.drop(columns="Actual Time (min)").to_csv(index=False),
                               file_name="task_list_template.csv")
        tl["🤖 Model Predicted (min)"] = [round(an.predict_minutes(time_model, **organiser_task_features(r))) for _, r in tl.iterrows()]
        st.dataframe(tl, hide_index=True, width="stretch")
        st.caption("The organisers' format has no soil, slope or volume columns, so these use typical values (gravel, 3°) and the "
                   "volume is back-calculated from the planner's estimate. The temperature comes from the sidebar and there's "
                   "no operator pace history. With only 5 rows and these assumptions, this list is an illustration, not an accuracy test.")


def organiser_task_features(r):
    """Map one row in the organisers' task format to model inputs (missing columns get stated defaults)."""
    task, wx = r["Task Type"], r["Weather"]
    wx = {"Rain": "Rainy", "Sun": "Sunny", "Wind": "Windy", "Fog": "Foggy", "Dust": "Dusty"}.get(wx, wx)
    return dict(task_type=task, weather=wx, operator_skill=r["Operator Skill"], machine_age_yrs=r["Machine Age (yrs)"],
                machine_type=data.machine_for_task(task), soil="Gravel", temp_c=temp_c, slope_deg=3,
                volume_m3=data.volume_from_estimate(task, "Gravel", r["Estimated Time (min)"], wx), operator_pace_hist=np.nan)


# ============================ 6. TRAINING HUB ============================
YT = "https://www.youtube.com/watch?v="
VIDEO_DIR = data.ROOT / "training_videos"
LESSONS = [
    {"id": "terrain", "title": data.TRAINING_MODULES["terrain"], "video": None, "local": "terrain.mp4", "duration": "42 sec",
     "source": "CAT Operator Assistant micro-lesson (stored locally, plays offline)",
     "points": ["Travel straight up or down a slope, never across it", "Keep the bucket or blade low when travelling",
                "Slow down on slopes: stay below 95% of the site speed limit", "Tilt warning at 15°: stop, lower the bucket, move to level ground"],
     "quiz": [("How should you travel on a slope?", ["Across the slope", "Straight up or down", "Diagonally, quickly"], 1),
              ("Where should the bucket be when travelling on a slope?", ["Raised high for visibility", "Low, close to the ground", "Fully extended"], 1),
              ("The tilt warning shows 17°. First action?", ["Keep going to finish", "Stop, lower the bucket, move to level ground", "Turn across the slope"], 1)]},
    {"id": "safety", "title": data.TRAINING_MODULES["safety"], "video": YT + "CJM_qHYXJDA",
     "source": "Cat® official: Safety Tips for Your Cat® Excavator (YouTube)",
     "points": ["Wear the seatbelt whenever the engine is running", "Walk around the machine before moving",
                "Keep people out of the swing radius", "Lower attachments to the ground before leaving the cab"],
     "quiz": [("When must the seatbelt be fastened?", ["Only on slopes", "Whenever the engine is running", "Only when travelling"], 1),
              ("A worker enters your swing radius. First action?", ["Sound the horn and continue", "Stop all motion", "Swing faster"], 1),
              ("Before leaving the cab you should…", ["Lower attachments to the ground", "Keep the boom raised", "Leave it at high idle"], 0)]},
    {"id": "fuel", "title": data.TRAINING_MODULES["fuel"], "video": YT + "T_D_XImk9Y0",
     "source": "Cat®: Your Cat® Pro Knows Excavators, Ch. 2: Fuel Efficiency (YouTube)",
     "points": ["Idling burns fuel with zero output (we assume ~3.5 L/h)", "Shut down if you'll wait more than 5 minutes",
                "Use ECO / auto-idle modes", "Short swing and dig paths save fuel"],
     "quiz": [("You'll wait 12 min for a truck. Best action?", ["Keep idling", "Shut the engine down", "Rev to keep warm"], 1),
              ("What does idling produce?", ["Useful work", "Fuel burn and engine hours with no output", "Better fuel economy"], 1),
              ("Which saves the most fuel?", ["Max power mode always", "Shorter swing & dig paths", "Higher idle speed"], 1)]},
    {"id": "walkaround", "title": data.TRAINING_MODULES["walkaround"], "video": YT + "7Au0F9yR5xc",
     "source": "Cat® 336 Walkaround Video (YouTube)",
     "points": ["Know every inspection point on your machine", "Check for leaks, damage and loose parts",
                "Check fluid levels on level ground", "Report defects before starting work"],
     "quiz": [("When do you do the walkaround inspection?", ["Once a month", "Before every shift", "Only after a breakdown"], 1),
              ("Fluid levels should be checked…", ["On level ground", "On a slope", "While working"], 0),
              ("You find a hydraulic leak. What do you do?", ["Ignore small leaks", "Report it before operating", "Top up and keep quiet"], 1)]},
    {"id": "operation", "title": data.TRAINING_MODULES["operation"], "video": YT + "1zD0G5uKxvQ",
     "source": "Cat®: How to Operate Your Cat® Wheeled Excavator (YouTube)",
     "points": ["Adjust the seat and mirrors before starting", "Use smooth, combined movements: avoid harsh braking and turning",
                "Fill the bucket fully on each pass: fewer, fuller cycles", "Match the power mode to the job"],
     "quiz": [("What should you adjust before starting?", ["Seat & mirrors", "Nothing", "Only the radio"], 0),
              ("Good control technique is…", ["Jerky single movements", "Smooth combined movements", "Always full throttle"], 1),
              ("Half-filled buckets mean…", ["More cycles for the same volume", "Less fuel used", "Faster work"], 0)]},
]
LESSON_BY_ID = {l["id"]: l for l in LESSONS}
IDLE_TIPS = [
    "Before you move off, check both mirrors and the rear camera. Blind spots can hide a person completely.",
    "On slopes, travel straight up or down with the bucket low. Never turn across the slope.",
    "Keep the seatbelt on whenever the engine runs. ROPS only protects you if you stay inside it.",
    "Loading trucks? Position them so your swing is 90° or less. It's faster and uses less fuel.",
    "Feeling tired? Tiredness slows your reactions. Take your break.",
    "Lower the bucket to the ground whenever you leave the cab, even for a minute.",
]
SCENARIOS = [
    ("A ground worker walks into your swing radius while you're loading a truck. What do you do?",
     ["Finish the swing quickly", "Stop, lower the bucket, and make eye contact before continuing", "Sound the horn and keep working"], 1,
     "Stop all motion first. The horn alone doesn't guarantee they've seen you."),
    ("You need to cross a 20° slope to reach the next work area.",
     ["Drive diagonally across it", "Travel straight up/down and reposition", "Cross quickly with the bucket raised"], 1,
     "Travelling across a slope is a major rollover risk. Go straight up or down with the bucket low."),
    ("The truck you're loading is 15 minutes late.",
     ["Keep the engine idling", "Shut down the engine and radio dispatch", "Rev the engine to keep it warm"], 1,
     "Idling burns fuel and adds engine hours with no output. Shut down if you'll wait more than 5 minutes."),
    ("It starts raining heavily while you're trenching next to an open trench.",
     ["Continue at the same pace", "Move back from the trench edge and reassess the ground", "Speed up to finish early"], 1,
     "Wet trench walls can collapse. Increase your distance from the edge and check with the supervisor."),
    ("Strong wind picks up while you're doing demolition work.",
     ["Carry on as normal", "Pause, lower the boom, and check for loose debris", "Work faster to finish"], 1,
     "Wind can carry debris and destabilise high loads. Lower the boom and reassess."),
]


@st.cache_data(ttl=60, show_spinner=False)
def online():
    """Is YouTube reachable? Checked at most once a minute. CAT_OFFLINE=1 forces offline mode."""
    if os.getenv("CAT_OFFLINE") == "1":
        return False
    import socket
    try:
        socket.create_connection(("www.youtube.com", 443), timeout=1.5).close()
        return True
    except OSError:
        return False


def local_video(lesson):
    """A local copy wins: training_videos/<lesson id>.mp4 (or the lesson's bundled file)."""
    for name in (f"{lesson['id']}.mp4", lesson.get("local")):
        if name and (VIDEO_DIR / name).exists():
            return VIDEO_DIR / name
    return None


def certificate_html(module, score):
    return f"""<html><body style="font-family:Segoe UI,Arial;text-align:center;padding:60px;border:14px solid {CAT_YELLOW}">
<div style="font-size:30px;font-weight:900"><span style="background:{CAT_YELLOW};padding:0 8px">CAT</span> Operator Training</div>
<h1 style="margin-top:40px">Certificate of Completion</h1><p style="font-size:20px">This certifies that</p>
<h2>{op['name']} ({op_id})</h2><p style="font-size:20px">has completed</p><h2>{module}</h2>
<p>Knowledge check score: <b>{score:.0f}%</b> · {datetime.now():%d %B %Y}</p></body></html>"""


def completed_modules():
    log = data.read("training_log")
    return log[log.operator_id == op_id]


def render_loop(row, loops, key_prefix):
    """One competency's closed-loop card: rail, provenance, verification numbers, evidence (expandable), next action."""
    stage, label, adapt = sk.loop_stage(row, loops)
    mine = [l for l in loops if l["comp"] == row["id"]]
    review = review_of(op_id, mine[-1] if mine else None)  # supervisor checkpoint; never a statistical verdict
    prov = "".join(chip("NEW · completed this session", "cat") if is_new_training(l) else
                   chip("SEEDED HISTORY · synthetic", "sim") for l in mine[-1:]) or (chip("GAP DETECTED FROM SESSIONS", "warn")
                                                                                   if row["gap"] else "")
    if review:
        prov += chip(*REVIEW_CHIP[review])
    with st.container(border=True):
        st.markdown(f'<div class="card" style="border:0;background:transparent;padding:0;margin:0">'
                    f'<div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:.4rem;align-items:flex-start">'
                    f'<div><div class="label">{row["competency"]}</div><div class="big">{row["score"]:.0f}'
                    f'<span class="meta" style="font-size:.9rem"> /100 · last {row["n"]} applicable sessions</span></div></div>'
                    f'<div>{prov}</div></div></div>', unsafe_allow_html=True)
        st.markdown(loop_rail(row, loops, stage, adapt, review), unsafe_allow_html=True)
        st.caption(label)
        if review:
            kind, text = REVIEW_TEXT[review]
            getattr(st, kind)(text)
        for l in mine:
            if l["pre_rate"] is not None and l["post_rate"] is None:
                st.markdown(f"**Baseline before '{l['module']}'** (completed {l['completed'][:10]}): {l['pre_rate']:.0f}% of your "
                            f"last {l['n_pre']} sessions met the standard ({l['metric']}: {l['fmt'].format(l['pre_metric'])}). "
                            f"The comparison starts once {sk.MIN_SESSIONS} sessions have been recorded after the training.")
            elif l["pre_rate"] is not None:
                fmt = l["fmt"]
                pv = l["p_rate"]
                p_txt = "" if pv is None else f" · one-sided Fisher exact p {'< 0.001' if pv < 0.001 else f'= {pv:.3f}'}"
                st.markdown(f"**Before vs after '{l['module']}'** (completed {l['completed'][:10]}): sessions meeting the standard "
                            f"{l['pre_rate']:.0f}% (last {l['n_pre']} before) → {l['post_rate']:.0f}% (first {l['n_post']} after){p_txt}. "
                            f"{l['metric']}: {fmt.format(l['pre_metric'])} → {fmt.format(l['post_metric'])}.")
            if is_new_training(l):
                st.info("This training was completed after the last recorded session. Live Cab sessions aren't saved in this "
                        "prototype, so the check stays at 0 post-training sessions until real session data is recorded. "
                        "No improvement is claimed until then.")
            else:
                st.caption("Seeded synthetic history: the behaviour change after this training was generated to demonstrate "
                           "verification. The verdict itself is computed from those recorded sessions.")
        with st.expander("Evidence and standard"):
            st.markdown(f"**Standard:** {row['standard']}\n" + "\n".join(f"- {e}" for e in row["evidence"]))
        mod = row["module"]
        if adapt or mod is None or review == "instructor":
            st.button("👨‍🏫 Book instructor coaching", key=f"{key_prefix}_coach_{row['id']}",
                      on_click=navigate, args=("🎓 Training Hub",), kwargs={"lesson": "book"})
        elif row["gap"] and (stage < 2 or review == "retraining"):
            st.button(f"▶️ Start: {data.TRAINING_MODULES[mod]}", key=f"{key_prefix}_start_{row['id']}", type="primary",
                      on_click=navigate, args=("🎓 Training Hub", mod))


LOOP_LEGEND = ('<div class="rail">' + "".join(
    f'<div class="step">{n}<small>{s}</small></div>' for n, s in [
        ("OBSERVE", "every session vs written standards"), ("DIAGNOSE", "score < 70 = skill gap"),
        ("TRAIN", "matched lesson + quiz"), ("VERIFY", "before vs after, significance test"),
        ("ADAPT", "close the gap or escalate")]) + "</div>")


def comp_review(comp, loops):
    """Supervisor review state of the latest training for one competency (None if untrained or seeded history)."""
    mine = [l for l in loops if l["comp"] == comp]
    return review_of(op_id, mine[-1]) if mine else None


def loop_summary_chips(prof, loops):
    scored = [r for _, r in prof.iterrows() if r["score"] is not None and not np.isnan(r["score"])]
    stages = [(*sk.loop_stage(r, loops), comp_review(r["id"], loops)) for r in scored]
    gaps = sum(1 for s, _, _, rv in stages if s == 1 or rv == "retraining")
    verified = sum(1 for s, _, _, _ in stages if s == 4)
    escalated = sum(1 for _, _, a, _ in stages if a)
    awaiting = sum(1 for s, _, a, rv in stages if s == 3 and not a and rv == "awaiting")
    monitoring = sum(1 for s, _, a, rv in stages if s == 3 and not a and rv in (None, "approved"))
    return (chip(f"{gaps} gap{'' if gaps == 1 else 's'} to train", "warn" if gaps else "ok")
            + (chip(f"{awaiting} awaiting supervisor review", "warn") if awaiting else "")
            + chip(f"{monitoring} monitoring", "info") + chip(f"{verified} verified", "ok")
            + chip(f"{escalated} escalated", "crit" if escalated else ""))


def page_training():
    prof, loops = my_profile()
    page_header("Training Hub", "Development", "Observe → Diagnose → Train → Verify → Adapt, built from your own sessions",
                loop_summary_chips(prof, loops))
    focus = prof[prof.gap | prof.id.isin([l["comp"] for l in loops])]
    st.markdown(LOOP_LEGEND, unsafe_allow_html=True)
    rec = next(((r, LESSON_BY_ID[r["module"]]) for _, r in prof.iterrows()
                if r["gap"] and r["module"] in LESSON_BY_ID
                and (sk.loop_stage(r, loops)[0] < 2 or comp_review(r["id"], loops) == "retraining")), None)
    if rec:
        r, l = rec
        how_long = (f'{l["duration"]} video · plays offline' if l.get("duration") else "YouTube video (length varies) · needs internet")             + " · 3-question check"
        card(f'<div class="label">Recommended now · because of your recorded sessions</div><div class="big">{l["title"]}</div>'
             f'<div class="kv"><span>WHY</span><span>{r["competency"]} {r["score"]:.0f}/100 · {r["evidence"][1] if len(r["evidence"]) > 1 else r["evidence"][0]}</span></div>'
             f'<div class="kv"><span>WHAT</span><span>{l["points"][0]} · {l["points"][1]}</span></div>'
             f'<div class="kv"><span>HOW LONG</span><span>{how_long}</span></div>'
             f'<div class="kv"><span>NEXT</span><span>Pass the check (≥ 66%) → supervisor review → VERIFY: Monitoring 0/{sk.MIN_SESSIONS}. '
             f'The before/after comparison runs once {sk.MIN_SESSIONS} sessions are recorded after training.</span></div>',
             accent=True, extra="hero")
        st.button(f"▶️ Open lesson: {l['title']}", key="rec_open", type="primary",
                  on_click=lambda lid=l["id"]: st.session_state.update(lesson=lid))
    st.subheader("🔁 Your closed-loop training plan")
    st.caption("Skill gaps are detected from your recorded sessions, training is matched to the gap, and your sessions after "
               "training are compared with the sessions before it.")
    if len(focus):
        for _, row in focus.iterrows():
            render_loop(row, loops, "hub")
    else:
        st.success("No skill gaps detected in your last 30 sessions. Refresher lessons are below.")

    tab_vid, tab_sim, tab_book, tab_rec = st.tabs(["🎥 Lessons", "🕹️ Scenario simulator",
                                                   "👨‍🏫 Book an instructor", "📜 My training record"])
    done_ids = set(completed_modules().module_id)
    with tab_vid:
        is_online = online()
        left, right = st.columns([1, 2.4])
        with left:
            st.markdown("**Lessons**")
            for l in LESSONS:
                icon = "✅" if l["id"] in done_ids else "▶️"
                offline_ok = " · 📁 offline" if local_video(l) else ""
                if st.button(f"{icon} {l['title']}{offline_ok}", key=f"pick_{l['id']}", width="stretch"):
                    st.session_state.lesson = l["id"]
            st.caption(("🌐 Online: YouTube lessons available." if is_online else "📴 Offline: local lessons play; YouTube "
                        "lessons show their key points only.") + " Drop `<lesson id>.mp4` into `training_videos/` for offline copies.")
        with right:
            cur = st.session_state.get("lesson")
            if cur not in LESSON_BY_ID:
                gaps = [m for m in prof[prof.gap].module if m in LESSON_BY_ID]
                cur = gaps[0] if gaps else LESSONS[0]["id"]
            l = LESSON_BY_ID[cur]
            st.subheader(l["title"])
            vid = local_video(l)
            if vid:
                st.video(str(vid))
                st.caption(f"Source: {l['source']} · playing the local file {vid.name}")
            elif l["video"] and is_online:
                st.video(l["video"])
                st.caption(f"Source: {l['source']}")
            else:
                st.warning("📴 This video needs internet and no local copy is installed. The key points and knowledge "
                           "check below still count towards your training.")
            st.markdown("**Key takeaways**\n" + "\n".join(f"- {p}" for p in l["points"]))
            st.markdown("**✍️ Knowledge check**")
            with st.form(f"quiz_{cur}"):
                answers = [st.radio(q, opts, index=None, key=f"q_{cur}_{i}") for i, (q, opts, _) in enumerate(l["quiz"])]
                if st.form_submit_button("Submit answers", type="primary"):
                    score = sum(a == opts[c] for a, (_, opts, c) in zip(answers, l["quiz"])) / len(l["quiz"]) * 100
                    st.session_state[f"score_{cur}"] = score
                    if score >= 66:
                        data.log_training(op_id, cur, score)
                        st.rerun()  # redraw the loop cards above with the new training record
            score = st.session_state.get(f"score_{cur}")
            if score is not None:
                if score >= 66:
                    st.success(f"🎉 Passed with {score:.0f}%. Training recorded and sent to your supervisor for review. "
                               "After approval, your next sessions are compared with your sessions before this training to "
                               "check whether the behaviour improves.")
                    st.download_button("📜 Download certificate", certificate_html(l["title"], score),
                                       file_name=f"certificate_{op_id}_{cur}.html", mime="text/html")
                    st.button("🧭 See my updated skill profile", on_click=navigate, args=("🧭 My Skill Profile",))
                else:
                    st.error(f"Score {score:.0f}%. Review the key points and try again (pass mark 66%).")
    with tab_sim:
        st.caption("Make decisions in real on-site situations. You get instant feedback on each one.")
        score = 0
        for i, (q, opts, correct, why) in enumerate(SCENARIOS):
            st.markdown(f"**Scenario {i + 1}.** {q}")
            ans = st.radio("Your action", opts, index=None, key=f"sc{i}", label_visibility="collapsed")
            if ans is not None:
                if opts.index(ans) == correct:
                    score += 1
                    st.success(f"✅ Correct. {why}")
                else:
                    st.error(f"❌ Unsafe. {why}")
        answered = sum(st.session_state.get(f"sc{i}") is not None for i in range(len(SCENARIOS)))
        if answered == len(SCENARIOS):
            st.metric("Simulator score", f"{score}/{len(SCENARIOS)}")
            if st.button("Save result"):
                data.log_training(op_id, "simulator", score / len(SCENARIOS) * 100)
                st.success("Result saved to your training record.")
    with tab_book:
        if st.session_state.get("lesson") == "book":
            st.info("Instructor coaching was recommended: by your supervisor, or because training alone hasn't produced a "
                    "measurable improvement yet.")
        booking_form(op_id)
        bk = data.read("bookings")
        if len(bk[bk.operator_id == op_id]):
            st.dataframe(bk[bk.operator_id == op_id], hide_index=True, width="stretch")
    with tab_rec:
        rec = completed_modules()
        n_done = len(set(rec.module_id) & set(LESSON_BY_ID))
        st.progress(n_done / len(LESSONS), text=f"{n_done}/{len(LESSONS)} lessons completed")
        if len(rec):
            st.dataframe(rec.iloc[::-1][["time", "module", "score"]], hide_index=True, width="stretch")
        else:
            st.caption("No training completed yet.")


# ============================ 7. SKILL PROFILE ============================
def page_profile():
    prof, loops = my_profile()
    page_header("My Skill Profile", "Development", "Share of your last 30 applicable sessions meeting each written standard · "
                "site median is anonymous (no names, no ranking)", loop_summary_chips(prof, loops))
    st.markdown(LOOP_LEGEND, unsafe_allow_html=True)
    st.subheader("🔁 Closed-loop status")
    for _, row in prof.iterrows():
        if row["score"] is not None and not np.isnan(row["score"]) and (row["gap"] or any(l["comp"] == row["id"] for l in loops)):
            render_loop(row, loops, "profile")
    section("Supporting evidence · competency profile")
    scored = prof[prof.score.notna()]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=list(scored.site_median) + [scored.site_median.iloc[0]],
                                  theta=list(scored.competency) + [scored.competency.iloc[0]], name="Site median (anonymous)",
                                  line=dict(color=STEEL, dash="dot")))
    fig.add_trace(go.Scatterpolar(r=list(scored.score) + [scored.score.iloc[0]],
                                  theta=list(scored.competency) + [scored.competency.iloc[0]], name="You (last 30 sessions)",
                                  fill="toself", line=dict(color=CAT_YELLOW), fillcolor="rgba(255,205,17,.25)"))
    fig.update_layout(polar=dict(radialaxis=dict(range=[0, 100])), height=420, margin=dict(t=40, b=40, l=90, r=90),
                      legend=dict(orientation="h", y=-0.05))
    a, b = st.columns([1.1, 1])
    hmi_chart(a, fig, width="stretch")
    with b:
        for r in prof.itertuples():
            if r.score is None or np.isnan(r.score):
                st.markdown(f"**{r.competency}**: not enough applicable sessions yet ({r.n})")
                continue
            trend = "" if r.previous is None or np.isnan(r.previous) else f" ({r.score - r.previous:+.0f} vs previous 30)"
            st.progress(r.score / 100, text=f"{'🔴' if r.gap else '🟢'} {r.competency}: {r.score:.0f}/100{trend}")
        st.caption(f"🔴 = below {sk.GAP_THRESHOLD} (skill gap: targeted training recommended)")
    with st.expander("All competencies: standards and evidence"):
        for _, row in prof.iterrows():
            st.markdown(f"**{row['competency']}** (standard: {row['standard']})\n" + "\n".join(f"- {e}" for e in row["evidence"]))

    st.subheader("📈 Personal improvement: your latest 30 sessions vs the 30 before")
    imp = sk.personal_improvement(sessions, standards, op_id)
    if imp is None:
        st.caption("Not enough history yet.")
    else:
        st.dataframe(imp, hide_index=True, width="stretch")
    st.subheader("🎖️ Milestones")
    st.caption("Based on machine sensor data only, never on self-reported incidents, so reporting a near miss never costs you anything.")
    b_ = an.badges(my_hist)
    st.markdown("".join(f'<span class="badge" title="{d}">{i} {n}</span>' for i, n, d in b_) or "No milestones yet.",
                unsafe_allow_html=True)


# ============================ 8. ASSISTANT ============================
# Natural-language, operator-aware assistant. `route()` is the source of truth: it classifies the question
# (with conversational follow-up context), retrieves facts from the app's own engines and answers
# deterministically offline. If a Claude API key is present, Claude only rephrases those retrieved facts.
import re

TOPIC_LESSONS = [(("slope", "tilt", "terrain", "rollover", "incline"), "terrain"),
                 (("seatbelt", "belt", "swing", "safety", "people", "worker"), "safety"),
                 (("fuel", "idle", "idling", "diesel"), "fuel"),
                 (("walkaround", "inspection", "inspect", "check", "leak"), "walkaround"),
                 (("control", "cycle", "bucket", "harsh", "smooth", "brak"), "operation")]
COMP_WORDS = [(("terrain", "slope", "slopes", "tilt", "rollover"), "terrain"), (("fuel", "idle", "idling"), "fuel"),
              (("seatbelt", "safety discipline", "overspeed", "overload"), "safety"), (("cycle", "bucket", "fill"), "cycle"),
              (("handling", "harsh", "smooth"), "handling"), (("execution", "pace"), "execution")]
SENSOR_WORDS = [(("tilt", "inclin", "angle"), "tilt"), (("speed", "fast"), "speed"), (("rpm", "revs"), "rpm"),
                (("engine temp", "coolant", "temperature", "overheat"), "temp"), (("load",), "load"),
                (("fuel rate", "burn rate"), "fuel"), (("seatbelt", "belt"), "seatbelt"),
                (("proximity", "nearest", "closest", "distance", "how close"), "proximity")]
OFFLINE_SCOPE = ("I can help with your machine, safety alerts, tasks, anomalies, skills, training and shift status while offline.")


def _has(ql, *terms):
    return any(re.search(r"\b" + re.escape(t), ql) for t in terms)


def _ctx():
    return st.session_state.setdefault("asst_ctx", {})


def _task_estimate_text(task_id):
    t = todays_tasks()
    if task_id in set(t.task_id):
        r = t[t.task_id == task_id].iloc[0]
        est, why = an.explain_prediction(time_model, task_features(r), tmod["reference"])
        factors = "; ".join(f"{w.factor} {w.value} ({w.effect_min:+.0f} min)" for w in why.head(3).itertuples())
        return (f"**{task_id}: {r.task_type} at {r.site}**. Model estimate **{est:.0f} min** (planner {r.estimated_time_min:.0f} min, "
                f"typical model error ±{time_mae:.0f} min) under current conditions ({weather}, {temp_c}°C). Biggest factors: {factors}.")
    sample = {"T001": ("Earth Excavation", "Sunny", "Expert", 2, 60), "T002": ("Trenching", "Rainy", "Intermediate", 4, 45),
              "T003": ("Material Loading", "Cloudy", "Beginner", 3, 30), "T004": ("Grading", "Sunny", "Expert", 5, 35),
              "T005": ("Demolition", "Windy", "Intermediate", 6, 90)}
    if task_id in sample:
        tt, wx, sk_, age, est_pl = sample[task_id]
        row = {"Task Type": tt, "Weather": wx, "Operator Skill": sk_, "Machine Age (yrs)": age, "Estimated Time (min)": est_pl}
        est = an.predict_minutes(time_model, **organiser_task_features(row))
        return (f"**{task_id}** (organisers' example: {tt}, {wx}, {sk_}, {age}-year-old machine): model estimate **{est:.0f} min** vs "
                f"the planner's {est_pl} min. Soil, slope and volume aren't in that format, so typical values are assumed.")
    hist = sessions[sessions.task_id == task_id]
    if len(hist):
        h = hist.iloc[0]
        return (f"**{task_id}** was a past {h.task_type} task on {h.timestamp:%d %b}: actual {h.duration_min:.0f} min, "
                f"planner {h.estimated_time_min:.0f} min, model-expected {h.expected_min_oof:.0f} min (out-of-fold).")
    return f"I couldn't find task {task_id}. Today's tasks are {', '.join(t.task_id)}."


# ---------------------------------------------------------------- answer builders (all facts come from the app)
def a_safety(mode):
    live = st.session_state.get("active_alerts", [])
    rd = st.session_state.get("last_reading")
    _ctx()["topic"] = "safety"
    if rd is None:
        return "There's no live reading yet. Open Live Cab (after the pre-start inspection) to start the simulated telemetry.", []
    if not live:
        logged = st.session_state.get("live_alerts", [])[-3:]
        txt = f"No safety alert is active on the latest simulated reading (#{st.session_state.get('tick')} at {rd['time']})."
        if logged:
            txt += " Recent alerts this shift:\n" + "\n".join(f"- {a['time']} **{a['type']}**: {a.get('why', a['detail'])}" for a in logged)
        return txt, []
    acts = [("🎓 Lesson: sloped terrain", "🎓 Training Hub", "terrain")] if any(t == "Tilt" for t, _, _ in live) else []
    if mode == "action":
        return ("Do this now, most critical first:\n" + "\n".join(f"- **{t}**: {SAFETY_ACTIONS.get(t, 'Follow the on-screen alert.')}"
                                                               for t, _, _ in live)), acts
    return ("These alerts are active right now, based on the latest sensor reading:\n"
            + "\n".join(f"- **{t}**: {why}" for t, _, why in live)
            + "\n\nAsk \"what should I do?\" for the actions."), acts


def a_telemetry(sensor):
    rd = st.session_state.get("last_reading")
    if rd is None:
        return "There's no live reading yet. Open Live Cab to start the simulated telemetry.", []
    n = rd["nearest"]
    val = {"tilt": f"Tilt is **{rd['tilt_deg']}°** (warning above 15°).",
           "speed": f"Speed is **{rd['speed_kmh']} km/h** (site limit {rd['limit']} km/h).",
           "rpm": f"Engine speed is **{rd['engine_rpm']} rpm**.",
           "temp": f"Engine coolant is **{rd['engine_temp_c']}°C** (warning above 98°C).",
           "load": f"Load is **{rd['load_pct']}%**.", "fuel": f"Fuel rate is **{rd['fuel_rate_lph']} L/h**.",
           "seatbelt": f"The seatbelt is **{'fastened' if rd['seatbelt'] else 'OPEN'}**.",
           "proximity": f"The nearest object is a **{n[2]} at {n[1]:.1f} m** (bearing {n[0]:.0f}°; stop < 3 m, caution < 6 m)."}[sensor]
    _ctx()["topic"] = "safety"
    return f"{val} (Simulated reading at {rd['time']}.)", []


def a_task(kind, task_id=None):
    t = todays_tasks()
    ctx = _ctx()
    ctx["topic"] = "task"
    if kind == "schedule":
        return "Here's the rest of your day:\n" + "\n".join(
            f"- **{r.task_id} {r.scheduled_start:%H:%M}** {r.task_type} at {r.site} (~{r.est_min:.0f} min, {r.priority})"
            + (f". ⚠️ {r.notes}" if r.notes else "") for r in t[t.status != "Done"].itertuples()), [("📋 My Day", "📋 My Day", None)]
    if task_id is None:
        task_id = ctx.get("task_id")
        if task_id is None:
            nxt = t[t.status != "Done"].head(1)
            if not len(nxt):
                return "All of today's tasks are done.", []
            task_id = nxt.iloc[0].task_id
    ctx["task_id"] = task_id
    if kind == "why" and task_id in set(t.task_id):
        r = t[t.task_id == task_id].iloc[0]
        est, why = an.explain_prediction(time_model, task_features(r), tmod["reference"])
        diff = est - r.estimated_time_min
        lines = "\n".join(f"- {w['factor']}: {w['value']} (site typical {w['site typical']}) → {w['effect_min']:+.0f} min"
                          for _, w in why.head(4).iterrows())
        return (f"For **{task_id}** the model expects **{est:.0f} min**, {abs(diff):.0f} min {'more' if diff > 0 else 'less'} than the "
                f"planner's {r.estimated_time_min:.0f} min. The planner uses a standard rate and soil only; the model also weighs these "
                f"inputs (effects are indicative, not causal):\n{lines}"), [("📋 My Day", "📋 My Day", None)]
    if kind == "action" and task_id in set(t.task_id):
        r = t[t.task_id == task_id].iloc[0]
        step = {"Pending": "press **▶️ Start task** in My Day when you begin", "In progress": "press **✅ Mark complete** in My Day when you finish",
                "Done": "it's already done"}[r.status]
        return (f"**{task_id}** ({r.task_type} at {r.site}) is {r.status.lower()}: {step}."
                + (f" Site note: {r.notes}." if r.notes else "")), [("📋 My Day", "📋 My Day", None)]
    return _task_estimate_text(task_id), [("⏱️ Open estimator", "⏱️ Task Estimator", None)]


def a_anomaly(mode):
    ctx = _ctx()
    ctx["topic"] = "anomaly"
    flagged = sessions[sessions.is_anomaly].sort_values("timestamp", ascending=False)
    mine = flagged[flagged.machine_id == machine_id]
    idx = ctx.get("anomaly_idx")
    if idx is None:
        pick = mine if len(mine) else flagged
        if not len(pick):
            return "No sessions are flagged as unusual.", []
        idx = pick.index[0]
        ctx["anomaly_idx"] = idx
    ex = an.explain_anomaly(sessions, idx)
    row = sessions.loc[idx]
    acts = [("📊 Machine Insights", "📊 Machine Insights", None)]
    if mode == "action":
        return f"Suggested follow-up for that session: {ex['recommendation']}", acts
    if mode == "why":
        ev = "\n".join(f"- {e['signal']}: {e['this session']} vs your usual {e['operator baseline']} and the site's "
                       f"{e['site baseline']} ({e['vs site']} vs site)" for _, e in ex["evidence"].iterrows())
        return (f"It was flagged because it sits far from normal behaviour for a {row.machine_type} (Isolation Forest on "
                f"robust z-scores):\n{ev}\n\nUnusual doesn't automatically mean unsafe.", acts)
    return (f"{len(mine)} of your machine's sessions are flagged as unusual ({len(flagged)} across the fleet). The most recent one "
            f"on {machine_id} is **{row.timestamp:%d %b %H:%M}, {row.task_type} at {row.site}**: {ex['title'].lower()} "
            f"({row.reason}). Ask \"why?\" for the evidence. The detector was validated on synthetic labels only."), acts


def a_skill(comp=None, mode="status"):
    prof, loops = my_profile()
    ctx = _ctx()
    ctx["topic"] = "skill"
    comp = comp or ctx.get("comp")
    if comp is None:
        gaps = prof[prof.gap]
        if not len(gaps):
            return "No skill gaps in your last 30 sessions: every competency meets its standard in at least 70% of sessions.", []
        ctx["comp"] = gaps.iloc[0]["id"]
        lines, acts = [], []
        for _, g in gaps.iterrows():
            lines.append(f"- **{g['competency']} {g['score']:.0f}/100** ({sk.loop_stage(g, loops)[1]}). "
                         f"Evidence: {g['evidence'][0]}; {g['evidence'][1]}")
            if g["module"]:
                acts.append((f"▶️ {data.TRAINING_MODULES[g['module']]}", "🎓 Training Hub", g["module"]))
        verified = [l for l in loops if l["verdict"] == "verified"]
        tail = ("\n\nAlready improved after training (seeded synthetic history): " +
                ", ".join(f"{l['competency']} ({l['pre_rate']:.0f}% → {l['post_rate']:.0f}%)" for l in verified)) if verified else ""
        return "Based on your last 30 sessions, focus on:\n" + "\n".join(lines) + tail, acts
    ctx["comp"] = comp
    row = prof.set_index("id").loc[comp]
    stage = sk.loop_stage({**row.to_dict(), "id": comp}, loops)[1]
    mod = row["module"]
    acts = [(f"▶️ {data.TRAINING_MODULES[mod]}", "🎓 Training Hub", mod)] if mod else []
    if mode == "why":
        return (f"**{row['competency']}** counts a session as meeting the standard when: {row['standard']}. "
                f"Only {row['score']:.0f}% of your last {row['n']} applicable sessions did:\n"
                + "\n".join(f"- {e}" for e in row["evidence"])), acts
    if mode == "action":
        if mod is None:
            return "For task execution, the recommended step is instructor coaching (Training Hub → Book an instructor).", []
        return (f"Your recommended lesson is **{data.TRAINING_MODULES[mod]}**. After you pass its 3-question check, the loop moves to "
                f"VERIFY: Monitoring 0/{sk.MIN_SESSIONS}."), acts
    return (f"Your **{row['competency']}** score is **{row['score']:.0f}/100** over your last {row['n']} applicable sessions "
            f"({'a skill gap' if row['gap'] else 'meets the standard'}). Status: {stage}. Ask \"why?\" for the evidence."), acts


def a_training(ql):
    prof, loops = my_profile()
    ctx = _ctx()
    ctx["topic"] = "training"
    topic = next((lid for keys, lid in TOPIC_LESSONS if any(k in ql for k in keys)), None)
    if topic and _has(ql, "teach", "lesson", "video", "show me", "learn about", "about"):
        l = LESSON_BY_ID[topic]
        dur = f" ({l['duration']}, plays offline)" if l.get("duration") else ""
        return (f"Here's the lesson **{l['title']}**{dur}. Key points:\n" + "\n".join(f"- {p}" for p in l["points"]),
                [(f"▶️ Open: {l['title']}", "🎓 Training Hub", topic)])
    gaps = prof[prof.gap & prof.module.notna()]
    if not len(gaps):
        todo = [l for l in LESSONS if l["id"] not in set(completed_modules().module_id)]
        refresher = f" A refresher you haven't done yet: **{todo[0]['title']}**." if todo else ""
        return ("No skill gaps in your last 30 sessions: every competency meets its standard in at least 70% of sessions."
                + refresher), ([(f"▶️ Open: {todo[0]['title']}", "🎓 Training Hub", todo[0]["id"])] if todo else [])
    lines, acts = [], []
    for _, g in gaps.iterrows():
        l = LESSON_BY_ID.get(g["module"])
        dur = f", {l['duration']}" if l and l.get("duration") else ""
        lines.append(f"- **{data.TRAINING_MODULES[g['module']]}**{dur}: recommended because {g['competency']} is "
                     f"{g['score']:.0f}/100 ({g['evidence'][1] if len(g['evidence']) > 1 else g['evidence'][0]}).")
        acts.append((f"▶️ {data.TRAINING_MODULES[g['module']]}", "🎓 Training Hub", g["module"]))
    ctx["comp"] = gaps.iloc[0]["id"]
    return "Recommended training, based on your recorded sessions:\n" + "\n".join(lines) + \
        "\n\nAsk \"what happens after training?\" to see how it's verified.", acts


def a_loop():
    prof, loops = my_profile()
    _ctx()["topic"] = "loop"
    mine = "\n".join(f"- {l['module']} ({l['completed'][:10]}) → {l['competency']}: {l['verdict_text']}"
                     + (" (completed this session; live sessions aren't saved in this prototype)" if is_new_training(l)
                        else " (seeded synthetic history)") for l in loops)
    return ("After you pass a lesson's check, your supervisor reviews the training (approval is not verification), "
            "then the loop moves to **VERIFY**. Your sessions after the training are compared with your "
            f"last 30 sessions before it (Fisher exact test on the share meeting the standard, Mann-Whitney U on the key metric). "
            f"The verdict needs at least {sk.MIN_SESSIONS} post-training sessions (**Monitoring k/{sk.MIN_SESSIONS}**). "
            f"A significant improvement is **Verified**. With no measurable change after {sk.ADAPT_AFTER} sessions, the system "
            "**escalates to instructor coaching** instead of claiming success."
            + (f"\n\nYour training loops:\n{mine}" if mine else "")), [("🧭 My Skill Profile", "🧭 My Skill Profile", None)]


def a_shift():
    _ctx()["topic"] = "shift"
    start = st.session_state.get("shift_start")
    fr, level, _ = fatigue_indicator()
    login = (f"You started this shift in the app at **{start:%H:%M}** ({(datetime.now() - start).seconds // 60} min ago). "
             if start else "")
    return (f"{login}The shift clock used by the safety rules is the demo setting: **{hours_on_shift:.1f} h on shift**, "
            f"**{hours_since_break:.1f} h since your last break**. Fatigue risk indicator: **{level}** ({fr:.0f}/100, an operational "
            "indicator, not a medical assessment). Use ☕ Log a break in Live Cab after a break."), []


def a_machine():
    _ctx()["topic"] = "machine"
    last_h, due = machine_hours()
    return (f"You're on **{machine_id}**, a {M.loc[machine_id, 'model']} {mtype} ({machine_age} years old). Engine hours "
            f"{last_h:.0f}; service estimate: about **{due:.0f} engine hours** remaining (from the seeded service history). "
            "Live readings on this screen are simulated."), []


def a_conditions():
    _ctx()["topic"] = "safety"
    fr, level, _ = fatigue_indicator()
    cond = "\n".join(f"- {i} {m}" for _, i, m in warnings) or "- No site-condition warnings."
    return (f"{cond}\n- Fatigue risk indicator: **{level}** ({fr:.0f}/100, operational indicator based on shift time, "
            f"time since break, heat and alerts; not a medical assessment)."), []


def a_idle():
    _ctx()["topic"] = "skill"
    _ctx()["comp"] = "fuel"
    return (f"Your idle share over the last 30 days is {my30.idle_ratio.mean():.0%} (standard ≤ 20% per session). "
            f"That's about {my30.idle_fuel_l.sum():.0f} L of fuel at an assumed 3.5 L/h. Shut down if you'll wait more than 5 minutes."), \
        [("▶️ Lesson: fuel efficiency", "🎓 Training Hub", "fuel")]


def a_help():
    return ("I'm the operator-aware assistant. I answer from this app's own data, and I work offline. Try:\n"
            "- **Safety:** \"Why is the machine warning me?\" · \"What's my current tilt?\" · \"What should I do?\"\n"
            "- **Tasks:** \"How long will my next task take?\" · \"Why is this ETA higher than the planner?\"\n"
            "- **Unusual behaviour:** \"Why was this session flagged?\"\n"
            "- **Skills & training:** \"Why is my terrain score low?\" · \"Which training should I take?\" · "
            "\"What happens after training?\"\n- **Shift & machine:** \"How long have I been working?\" · \"What machine am I using?\""), []


def route(q):
    """Classify a free-text question (with follow-up context) and answer from app data. Returns (markdown, actions)."""
    ql = " " + q.lower().strip() + " "
    ctx = _ctx()
    task_id = re.search(r"\b([td]\d{3,4})\b", ql)
    wants_action = _has(ql, "what should i do", "what do i do", "what to do", "what now", "how do i fix", "handle", "next step",
                        "what next", "do next", "should i do")
    wants_why = _has(ql, "why", "how come", "explain", "reason")
    comp = next((c for keys, c in COMP_WORDS if any(k in ql for k in keys)), None)
    sensor = next((s for keys, s in SENSOR_WORDS if any(k in ql for k in keys)), None)

    if _has(ql, "what can you do", "help", "what do you do", "how do you work", "what can i ask"):
        return a_help()
    if _has(ql, "closed loop", "the loop", "after training", "after i finish", "after the training", "happens after",
            "verify", "verification", "verified", "monitoring"):
        return a_loop()
    if _has(ql, "been working", "working for", "how long have i", "last break", "my break", "my shift", "shift", "tired", "fatigue"):
        return a_shift()
    if _has(ql, "what machine", "which machine", "my machine", "machine am i", "machine age", "engine hours", "service", "maintenance"):
        return a_machine()
    if sensor and not wants_why and _has(ql, "current", "now", "what's my", "whats my", "what is my", "reading", "how fast",
                                         "how close", "level", "value", "my tilt", "my speed"):
        return a_telemetry(sensor)
    if task_id:
        return a_task("why" if wants_why else "eta", task_id.group(1).upper())
    if _has(ql, "warning", "warn", "alert", "alarm", "danger", "hazard", "worker", "person", "critical", "beeping", "stop sign"):
        return a_safety("action" if wants_action else "why")
    if _has(ql, "flagged", "anomal", "unusual", "odd", "strange", "weird", "abnormal", "outlier", "looks off"):
        return a_anomaly("why" if wants_why else "action" if wants_action else "status")
    if _has(ql, "eta", "estimate", "how long", "finish", "next task", "my task", "this task", "that task", "planner", "job"):
        if _has(ql, "schedule", "today", "rest of", "all my tasks"):
            return a_task("schedule")
        return a_task("why" if (wants_why or _has(ql, "higher", "longer", "lower", "shorter")) else "eta")
    if _has(ql, "schedule", "tasks today", "my tasks", "plan for today", "what's next", "whats next", "rest of the day"):
        return a_task("schedule")
    if _has(ql, "teach", "lesson", "video", "learn about", "show me how") and next(
            (lid for keys, lid in TOPIC_LESSONS if any(k in ql for k in keys)), None):
        return a_training(ql)
    if _has(ql, "training", "train", "course", "learn", "lesson", "quiz", "teach"):
        return a_training(ql)
    if _has(ql, "improve", "skill", "score", "weak", "gap", "profile", "competenc", "better at"):
        if comp:
            return a_skill(comp, "why" if wants_why or _has(ql, "low", "bad") else "action" if wants_action else "status")
        return a_skill(None)
    if _has(ql, "idle", "idling", "fuel"):
        return a_idle()
    if _has(ql, "safe to work", "is it safe", "weather", "rain", "raining", "heat", "hot", "visibility", "wind", "conditions"):
        return a_conditions()

    # ---- follow-ups: resolve "why?", "what should I do?", "tell me more" against the last topic
    topic = ctx.get("topic")
    short = len(q.split()) <= 8
    if short and (wants_why or wants_action or _has(ql, "more", "it", "that", "this", "then", "and")):
        if topic == "safety":
            return a_safety("action" if wants_action else "why")
        if topic == "task":
            return a_task("action" if wants_action else "why")
        if topic == "anomaly":
            return a_anomaly("action" if wants_action else "why")
        if topic == "skill":
            return a_skill(None if ctx.get("comp") is None else ctx["comp"], "action" if wants_action else "why")
        if topic in ("training", "loop"):
            return a_loop() if wants_action or _has(ql, "then", "next", "after") else a_skill(ctx.get("comp"), "why")
        if topic in ("shift", "machine"):
            return (a_shift() if topic == "shift" else a_machine())
        return ("Do you mean the current safety alert, your next task, a flagged session or your skill profile? "
                "Tell me which and I'll explain."), []
    return OFFLINE_SCOPE + " Try \"what can you do?\" for examples.", []


def context():
    prof, loops = my_profile()
    t = todays_tasks()
    return (f"Operator {op['name']} ({op_id}, {skill}, {op.experience_yrs} yrs) on {machine_id} ({M.loc[machine_id, 'model']} {mtype}).\n"
            f"Now {datetime.now():%H:%M}. Conditions: {weather}, {temp_c}°C, visibility {visibility}, ground {ground}.\n"
            "Today's tasks: " + "; ".join(f"{r.task_id} {r.task_type} at {r.site} {r.scheduled_start:%H:%M} (~{r.est_min:.0f} min, "
                                          f"{r.status})" for r in t.itertuples()) +
            "\nCompetencies (last 30 sessions): " + "; ".join(f"{r.competency} {r.score:.0f}{' GAP' if r.gap else ''}"
                                                               for r in prof.itertuples() if r.score is not None) +
            "\nTraining loops: " + "; ".join(f"{l['module']} → {l['verdict_text']}" for l in loops) +
            f"\nActive alerts: {st.session_state.get('active_alerts', [])}\nSite warnings: {[m for _, _, m in warnings]}")


def ask_claude(msgs, retrieved):
    import anthropic
    client = anthropic.Anthropic()
    resp = client.beta.messages.create(
        model="claude-opus-5", max_tokens=1024,
        system="You are the language layer of an operator-aware assistant in a Caterpillar machine cab. The application has "
               "already retrieved the facts below; they are the only source of truth. Rephrase them conversationally in short, "
               "practical sentences, safety first. Resolve follow-up wording using the conversation. Never invent sensor "
               "readings, estimates, scores, anomaly results or training outcomes; never make or override safety decisions; "
               "never claim real CAT telemetry, medical fatigue detection or real-world training effects. Telemetry is "
               "simulated and data is synthetic. If the facts don't answer the question, say so.\n\n"
               + context() + "\n\nFacts the app retrieved for this question:\n" + retrieved,
        messages=msgs, betas=["server-side-fallback-2026-07-01"], fallbacks="default",
    )
    if resp.stop_reason == "refusal":
        return retrieved
    return "".join(b.text for b in resp.content if b.type == "text") or retrieved


def page_assistant():
    has_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    page_header("Ask Assistant", "Intelligence", "Natural-language operator assistant · answers come from your live (simulated) "
                "sensors, tasks, skill profile and lessons",
                chip("works offline", "ok") + (chip("Claude phrasing on", "info") if has_key else chip("Claude off (optional)", "sim")))
    st.caption("Ask in your own words. Follow-ups like \"why?\" or \"what should I do?\" use the conversation so far. " +
               ("Claude rephrases the app's facts; the app stays the source of truth." if has_key else
                "Works fully offline. Add ANTHROPIC_API_KEY to .env for more natural phrasing."))
    quick = st.columns(4)
    preset = None
    for col, q in zip(quick, ["Why am I getting this warning?", "How long will my next task take?",
                              "What should I improve?", "Teach me about slopes"]):
        if col.button(q, width="stretch"):
            preset = q
    for m in st.session_state.chat:
        st.chat_message(m["role"]).markdown(m["content"])
    prompt = st.chat_input("Ask anything about your machine, safety, tasks, skills, training or shift…") or preset
    if prompt:
        st.session_state.chat.append({"role": "user", "content": prompt})
        st.chat_message("user").markdown(prompt)
        retrieved, actions = route(prompt)
        ans = retrieved
        if has_key:
            with st.spinner("Thinking…"):
                try:
                    ans = ask_claude(st.session_state.chat, retrieved)
                except Exception as e:  # no network / bad key: the offline answer is already computed
                    ans = retrieved + f"\n\n_(Online AI unavailable ({type(e).__name__}), so this is the offline answer.)_"
        st.session_state.chat.append({"role": "assistant", "content": ans})
        st.session_state.chat_actions = actions
        st.chat_message("assistant").markdown(ans)
    for i, (label, page_, lesson) in enumerate(st.session_state.get("chat_actions", [])):
        st.button(label, key=f"act_{i}", on_click=navigate, args=(page_, lesson))


{"🚜 Live Cab": page_live, "📋 My Day": page_day, "🦺 Safety Center": page_safety, "📊 Machine Insights": page_insights,
 "⏱️ Task Estimator": page_estimator, "🎓 Training Hub": page_training, "🧭 My Skill Profile": page_profile,
 "🤖 Ask Assistant": page_assistant}[page]()
