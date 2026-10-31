import streamlit as st
import pandas as pd
import sqlite3
import json
import os
import random
import requests
from pathlib import Path
from datetime import datetime, timedelta, date
from io import BytesIO
from local_backtest import run_backtest, BacktestError

DB = Path(__file__).with_name("alpha_lab.sqlite3")
BRAIN_API = "https://api.worldquantbrain.com"
DEFAULT_PROMPT = "An alpha predicts future prices using six years of history. Use less-exploited fields, at most 3 operators and at most 2 data fields. Explain economic rationale and overfitting risks."

st.set_page_config(page_title="Alpha King", page_icon="👑", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.stApp{background:radial-gradient(ellipse at 80% 0%,#14243b 0%,#080d18 52%)}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#111827,#080d18);border-right:1px solid #26364d}
[data-testid="stMetric"]{background:linear-gradient(145deg,#14243a,#0e1726);border:1px solid #263d59;padding:15px;border-radius:14px}
div[data-testid="stForm"],div[data-testid="stExpander"]{border:1px solid #263d59;border-radius:14px}
.stButton>button,.stDownloadButton>button{border-radius:10px;border:1px solid #315273;font-weight:650}
.stButton>button[kind="primary"],.stFormSubmitButton>button{background:linear-gradient(90deg,#0284c7,#2563eb);border:0}
.ak-hero{padding:22px 26px;border-radius:18px;background:linear-gradient(115deg,#12304b,#172554 65%,#111827);border:1px solid #315273;margin-bottom:18px}
.ak-muted{color:#9fb3c8;font-size:.9rem}
</style>""", unsafe_allow_html=True)

# Pause autorefresh during auth request
if not st.session_state.get("is_authenticating", False):
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=5000, key="clock")
    except Exception:
        pass

def db():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

with db() as c:
    c.executescript("""
    CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY,v TEXT);
    CREATE TABLE IF NOT EXISTS fields(field TEXT,dataset TEXT,description TEXT);
    CREATE TABLE IF NOT EXISTS templates(id INTEGER PRIMARY KEY,name TEXT UNIQUE,expr TEXT,description TEXT);
    CREATE TABLE IF NOT EXISTS alphas(id INTEGER PRIMARY KEY,expr TEXT,fields TEXT,rationale TEXT,status TEXT,sharpe REAL,fitness REAL,turnover REAL,correlation REAL,created TEXT);
    CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY,name TEXT,progress INTEGER,status TEXT);
    CREATE TABLE IF NOT EXISTS comps(id INTEGER PRIMARY KEY,name TEXT,details TEXT,status TEXT);
    CREATE TABLE IF NOT EXISTS usage(day TEXT PRIMARY KEY,n INTEGER);
    CREATE TABLE IF NOT EXISTS pnl(alpha TEXT,date TEXT,pnl REAL);
    """)
    c.execute("INSERT OR IGNORE INTO settings VALUES('prompt',?)", (DEFAULT_PROMPT,))

def read(q, args=()):
    with db() as c:
        return pd.read_sql_query(q, c, params=args)

def setting(k, default=""):
    with db() as c:
        r = c.execute("SELECT v FROM settings WHERE k=?", (k,)).fetchone()
    return r[0] if r else default

def save(k, v):
    with db() as c:
        c.execute("INSERT INTO settings VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, str(v)))

def remaining():
   try:
                with st.spinner("Connecting to WorldQuant API..."):
                    res = requests.post(
                        f"{BRAIN_API}/authentication", 
                        auth=(email, password), 
                        headers=headers,
                        json={"expiry": 14400}, 
                        timeout=8, 
                        allow_redirects=False
                    )
                st.session_state["is_authenticating"] = False

# Navigation Setup
pages = ["Simulation Lab", "Dashboard", "Data Explorer", "Tasks", "Portfolio", "Competitions", "Template Home", "AI Alpha Lab", "BRAIN Access"]
icons = {"Dashboard": "🏠", "Data Explorer": "🧭", "Simulation Lab": "⚗️", "Tasks": "📋", "Portfolio": "📈", "Competitions": "🏆", "Template Home": "🧩", "AI Alpha Lab": "✨", "BRAIN Access": "🌐"}

if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Simulation Lab"

st.sidebar.markdown("# 👑 Alpha King")
st.sidebar.caption("Quant research workspace")

selected_page = st.sidebar.radio(
    "WORKSPACE", 
    [f"{icons[p]}  {p}" for p in pages], 
    index=pages.index(st.session_state["current_page"])
)
page = selected_page.split("  ", 1)[1]
st.session_state["current_page"] = page

st.sidebar.divider()

active = remaining() != "Inactive"
st.sidebar.markdown("**BRAIN Session Status**")
st.sidebar.markdown(f"<span style='color:{'#22c55e' if active else '#f59e0b'}'>● {'ACTIVE' if active else 'SIGNED OUT'}</span>", unsafe_allow_html=True)
st.sidebar.metric("Session time remaining", remaining())

if st.sidebar.button("↪ Sign out of Alpha King", use_container_width=True):
    save("until", "")
    save("login_mode", "")
    st.session_state.pop("persona_url", None)
    st.rerun()

st.title("👑 Alpha King")

# --- PAGE ROUTING ---

if page == "BRAIN Access":
    st.subheader("🌐 WorldQuant BRAIN Authentication")
st.markdown("""
<style>
/* Main app background - Clean & bright main background */
.stApp {
    background-color: #0f172a;
    color: #f8fafc;
}

/* Sidebar styling - Rich navy with clear borders */
[data-testid="stSidebar"] {
    background-color: #1e293b;
    border-right: 1px solid #334155;
}

/* Sidebar text and subheaders visibility */
[data-testid="stSidebar"] * {
    color: #f1f5f9 !important;
}

/* Main title & Headers - Bright white */
h1, h2, h3, h4, h5, h6, .stMarkdown label, p {
    color: #f8fafc !important;
}

/* Metrics - Sharp contrast cards */
[data-testid="stMetric"] {
    background: #1e293b;
    border: 1px solid #334155;
    padding: 16px;
    border-radius: 12px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
}

[data-testid="stMetricValue"] {
    color: #38bdf8 !important;
    font-weight: 700;
}

/* Hero Cards */
.ak-hero {
    padding: 24px;
    border-radius: 16px;
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border: 1px solid #334155;
    margin-bottom: 20px;
}

.ak-hero h2, .ak-hero h3 {
    color: #ffffff !important;
}

.ak-muted {
    color: #94a3b8 !important;
    font-size: 0.95rem;
}

/* Text Inputs, Text Areas, Select Boxes - High visibility */
div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
    background-color: #1e293b !important;
    color: #ffffff !important;
    border-color: #475569 !important;
}

input {
    color: #ffffff !important;
}

/* Primary Action Buttons */
.stButton>button[kind="primary"], .stFormSubmitButton>button {
    background: linear-gradient(90deg, #0284c7, #2563eb) !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    border: none !important;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

/* Secondary Buttons */
.stButton>button, .stDownloadButton>button {
    background-color: #334155 !important;
    color: #ffffff !important;
    border: 1px solid #475569 !important;
    border-radius: 10px;
    font-weight: 600;
}

.stButton>button:hover {
    background-color: #475569 !important;
    border-color: #38bdf8 !important;
}

/* Dataframe header & table visibility */
[data-testid="stDataFrame"] {
    border: 1px solid #334155;
    border-radius: 8px;
}
</style>""", unsafe_allow_html=True)    
    email = st.text_input("WorldQuant Email", value="mangerajoseph24@gmail.com")
    password = st.text_input("WorldQuant Password", type="password")
    
    if st.button("🔑 Authenticate with WorldQuant BRAIN", type="primary"):
        if not email or not password:
            st.warning("Please provide both email and password.")
        else:
            st.session_state["is_authenticating"] = True
            headers = {
                "Accept": "application/json;version=2.0",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }
            try:
                with st.spinner("Connecting to WorldQuant API..."):
                    res = requests.post(
                        f"{BRAIN_API}/authentication", 
                        auth=(email, password), 
                        headers=headers,
                        json={"expiry": 14400}, 
                        timeout=8, 
                        allow_redirects=False
                    )
                st.session_state["is_authenticating"] = False
                
                # Direct Successful Auth
                if res.status_code in (200, 201, 204):
                    save("until", (datetime.now() + timedelta(hours=4)).isoformat())
                    save("login_mode", "direct_api")
                    st.session_state["current_page"] = "Simulation Lab"
                    st.success("Authentication successful! Opening Simulation Lab...")
                    st.rerun()
                
                # Persona Verification Request
                elif res.status_code == 401 or "persona" in res.headers.get("WWW-Authenticate", "").lower():
                    inquiry_path = res.headers.get("Location")
                    if inquiry_path:
                        if inquiry_path.startswith("http"):
                            st.session_state["persona_url"] = inquiry_path
                        else:
                            st.session_state["persona_url"] = f"https://api.worldquantbrain.com{inquiry_path}"
                        st.warning("WorldQuant requested Persona identity verification.")
                    else:
                        st.error("Persona verification required, but no location header was returned.")
                else:
                    st.error(f"Authentication response ({res.status_code}): {res.text}")
                    
            except requests.exceptions.Timeout:
                st.session_state["is_authenticating"] = False
                st.error("Request timed out. WorldQuant server did not respond in time.")
            except Exception as e:
                st.session_state["is_authenticating"] = False
                st.error(f"Connection error: {e}")

    # Display Persona Link
    if st.session_state.get("persona_url"):
        st.divider()
        st.subheader("⚠️ Identity Verification Link Received")
        st.info("Click the button below to complete verification in Persona, then click confirm to complete login.")
        
        col1, col2 = st.columns(2)
        with col1:
            st.link_button("↗️ Open Persona Verification Window", st.session_state["persona_url"], type="primary", use_container_width=True)
        with col2:
            if st.button("✓ I completed verification — return to app", use_container_width=True):
                save("until", (datetime.now() + timedelta(hours=4)).isoformat())
                save("login_mode", "persona_manual_confirm")
                st.session_state.pop("persona_url", None)
                st.session_state["current_page"] = "Simulation Lab"
                st.success("Verification confirmed! Returning to Simulation Lab...")
                st.rerun()

elif page == "Simulation Lab":
    st.subheader("⚗️ Local Alpha Simulation Lab")
    st.info("Runs reproducible cross-sectional backtests locally on uploaded market data.")
    up = st.file_uploader("Upload CSV: date, symbol, close, plus optional numeric factor columns", type="csv", key="local_market_data")
    if up:
        try:
            market = pd.read_csv(up)
            market.columns = [str(c).strip().lower() for c in market.columns]
            if not {"date", "symbol", "close"}.issubset(market.columns):
                st.error("CSV must contain date, symbol and close columns.")
            else:
                market["date"] = pd.to_datetime(market["date"], errors="coerce")
                market["close"] = pd.to_numeric(market["close"], errors="coerce")
                market = market.dropna(subset=["date", "symbol", "close"]).sort_values(["symbol", "date"])
                excluded = {"date", "symbol", "close", "open", "high", "low", "volume"}
                factors = [c for c in market.columns if c not in excluded and pd.api.types.is_numeric_dtype(market[c])]
                st.success(f"Loaded {len(market):,} rows · {market.symbol.nunique():,} instruments · {market.date.nunique():,} dates")
                st.dataframe(market.head(8), use_container_width=True, hide_index=True)
                
                models = ["Price momentum", "Price mean reversion"] + [f"Cross-sectional rank: {x}" for x in factors] + [f"Factor momentum: {x}" for x in factors]
                a, b = st.columns(2)
                strategy = a.selectbox("Signal model", models)
                lookback = a.select_slider("Lookback (trading days)", [5, 10, 20, 40, 60, 120, 252], value=20)
                quantile = b.slider("Long / short quantile", 0.1, 0.4, 0.2, 0.05)
                fees = b.number_input("One-way transaction cost (bps)", 0.0, 100.0, 5.0, 0.5)
                split = st.slider("In-sample portion", 0.5, 0.9, 0.7, 0.05)
                annual = st.selectbox("Trading days per year", [252, 250, 365])
                
                if st.button("▶ Run local simulation", type="primary", use_container_width=True):
                    try:
                        res = run_backtest(market, strategy, lookback, quantile, fees, split, annual)
                        st.session_state["local_sim_result"] = res
                        with db() as c:
                            c.execute("INSERT INTO usage VALUES(?,1) ON CONFLICT(day) DO UPDATE SET n=n+1", (date.today().isoformat(),))
                            m = res["metrics"]
                            c.execute("INSERT INTO alphas(expr,fields,rationale,status,sharpe,fitness,turnover,created) VALUES(?,?,?,'Local simulation',?,?,?,?)",
                                      (res["expression"], res["factor"], "Local backtest on uploaded data.", m["Sharpe"], m["Fitness"], m["Turnover"], datetime.now().isoformat()))
                        st.success("Local backtest completed.")
                    except BacktestError as e:
                        st.error(str(e))
                    except Exception as e:
                        st.error(f"Simulation failed: {e}")
        except Exception as e:
            st.error(f"Could not read dataset: {e}")

elif page == "Dashboard":
    st.markdown("""
<style>
/* Main app background - Clean & bright main background */
.stApp {
    background-color: #0f172a;
    color: #f8fafc;
}

/* Sidebar styling - Rich navy with clear borders */
[data-testid="stSidebar"] {
    background-color: #1e293b;
    border-right: 1px solid #334155;
}

/* Sidebar text and subheaders visibility */
[data-testid="stSidebar"] * {
    color: #f1f5f9 !important;
}

/* Main title & Headers - Bright white */
h1, h2, h3, h4, h5, h6, .stMarkdown label, p {
    color: #f8fafc !important;
}

/* Metrics - Sharp contrast cards */
[data-testid="stMetric"] {
    background: #1e293b;
    border: 1px solid #334155;
    padding: 16px;
    border-radius: 12px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
}

[data-testid="stMetricValue"] {
    color: #38bdf8 !important;
    font-weight: 700;
}

/* Hero Cards */
.ak-hero {
    padding: 24px;
    border-radius: 16px;
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border: 1px solid #334155;
    margin-bottom: 20px;
}

.ak-hero h2, .ak-hero h3 {
    color: #ffffff !important;
}

.ak-muted {
    color: #94a3b8 !important;
    font-size: 0.95rem;
}

/* Text Inputs, Text Areas, Select Boxes - High visibility */
div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
    background-color: #1e293b !important;
    color: #ffffff !important;
    border-color: #475569 !important;
}

input {
    color: #ffffff !important;
}

/* Primary Action Buttons */
.stButton>button[kind="primary"], .stFormSubmitButton>button {
    background: linear-gradient(90deg, #0284c7, #2563eb) !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    border: none !important;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

/* Secondary Buttons */
.stButton>button, .stDownloadButton>button {
    background-color: #334155 !important;
    color: #ffffff !important;
    border: 1px solid #475569 !important;
    border-radius: 10px;
    font-weight: 600;
}

.stButton>button:hover {
    background-color: #475569 !important;
    border-color: #38bdf8 !important;
}

/* Dataframe header & table visibility */
[data-testid="stDataFrame"] {
    border: 1px solid #334155;
    border-radius: 8px;
}
</style>""", unsafe_allow_html=True)

elif page == "Data Explorer":
    st.subheader("Data Explorer")
    up = st.file_uploader("Import authorized data-field CSV", type="csv")
    if up and st.button("Import fields"):
        d = pd.read_csv(up)
        d.columns = [x.lower() for x in d.columns]
        f = next((x for x in ["field", "field_id", "name"] if x in d), None)
        if f:
            with db() as c:
                for _, r in d.iterrows():
                    c.execute("INSERT INTO fields VALUES(?,?,?)", (str(r[f]), str(r.get("dataset", "")), str(r.get("description", ""))))
            st.success("Imported fields.")
            st.rerun()

elif page == "AI Alpha Lab":
    st.subheader("AI Alpha Lab")
    prompt = st.text_area("Primary Prompt", setting("prompt"), height=120)
    if st.button("Save Prompt"):
        save("prompt", prompt)
        st.success("Saved.")

elif page == "Portfolio":
    st.subheader("Portfolio")
    a = read("SELECT * FROM alphas")
    st.dataframe(a, use_container_width=True, hide_index=True) if len(a) else st.info("No recorded alphas.")

elif page == "Tasks":
    st.subheader("Tasks")
    for _, r in read("SELECT * FROM tasks ORDER BY id DESC").iterrows():
        st.write(f"{r['name']} — {r.progress}%")

elif page == "Competitions":
    st.subheader("Competitions")
    for _, r in read("SELECT * FROM comps").iterrows():
        st.write(r["name"], r.status)

elif page == "Template Home":
    st.subheader("Template Home")
    t = read("SELECT * FROM templates ORDER BY id")
    st.dataframe(t, use_container_width=True, hide_index=True) if len(t) else st.info("No templates stored.")
