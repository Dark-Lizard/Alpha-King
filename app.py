import streamlit as st, pandas as pd, sqlite3, json, os, random, webbrowser
from pathlib import Path
from datetime import datetime,timedelta,date
from io import BytesIO
from local_backtest import run_backtest, BacktestError
DB=Path(__file__).with_name("alpha_lab.sqlite3"); BRAIN="https://platform.worldquantbrain.com/"
DEFAULT="An alpha predicts future prices using six years of history. Use less-exploited fields, at most 3 operators and at most 2 data fields. Explain economic rationale and overfitting risks. Never claim platform success without actual BRAIN results."
st.set_page_config(page_title="Alpha King",page_icon="👑",layout="wide",initial_sidebar_state="expanded")
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
</style>""",unsafe_allow_html=True)
try:
 from streamlit_autorefresh import st_autorefresh
 st_autorefresh(interval=1000,key="clock")
except: pass
if not st.session_state.get("opened",False): webbrowser.open(BRAIN); st.session_state.opened=True
def db():
 c=sqlite3.connect(DB,check_same_thread=False); c.row_factory=sqlite3.Row; return c
with db() as c:
 c.executescript("""CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY,v TEXT);
 CREATE TABLE IF NOT EXISTS fields(field TEXT,dataset TEXT,description TEXT);
 CREATE TABLE IF NOT EXISTS templates(id INTEGER PRIMARY KEY,name TEXT UNIQUE,expr TEXT,description TEXT);
 CREATE TABLE IF NOT EXISTS alphas(id INTEGER PRIMARY KEY,expr TEXT,fields TEXT,rationale TEXT,status TEXT,sharpe REAL,fitness REAL,turnover REAL,correlation REAL,created TEXT);
 CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY,name TEXT,progress INTEGER,status TEXT);
 CREATE TABLE IF NOT EXISTS comps(id INTEGER PRIMARY KEY,name TEXT,details TEXT,status TEXT);
 CREATE TABLE IF NOT EXISTS usage(day TEXT PRIMARY KEY,n INTEGER);
 CREATE TABLE IF NOT EXISTS pnl(alpha TEXT,date TEXT,pnl REAL);""")
 c.execute("INSERT OR IGNORE INTO settings VALUES('prompt',?)",(DEFAULT,))
 c.execute("INSERT OR IGNORE INTO templates(name,expr,description) VALUES(?,?,?)",("Single dataset","rank(ts_rank(ts_scale({x}, {d}), {d}))","{x}: random field from dataset 1; {d}: trading-day lookback."))
 c.execute("INSERT OR IGNORE INTO templates(name,expr,description) VALUES(?,?,?)",("Two datasets","Group_rank({x} + {x2}, industry)","{x}: random field from dataset 1; {x2}: random field from dataset 2."))
def read(q,args=()):
 with db() as c: return pd.read_sql_query(q,c,params=args)
def setting(k,default=""):
 with db() as c:
  r=c.execute("SELECT v FROM settings WHERE k=?",(k,)).fetchone()
 return r[0] if r else default
def save(k,v):
 with db() as c: c.execute("INSERT INTO settings VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",(k,str(v)))
def remaining():
 try:
  n=max(0,int((datetime.fromisoformat(setting("until"))-datetime.now()).total_seconds()))
  return f"{n//3600:02}:{n//60%60:02}:{n%60:02}"
 except: return "Inactive"
st.sidebar.markdown("# 👑 Alpha King")
st.sidebar.caption("Quant research workspace")
pages=["Dashboard","Data Explorer","Simulation Lab","Tasks","Portfolio","Competitions","Template Home","AI Alpha Lab","BRAIN Access"]
icons={"Dashboard":"🏠","Data Explorer":"🧭","Simulation Lab":"⚗️","Tasks":"📋","Portfolio":"📈","Competitions":"🏆","Template Home":"🧩","AI Alpha Lab":"✨","BRAIN Access":"🌐"}
page=st.sidebar.radio("WORKSPACE",[f"{icons[p]}  {p}" for p in pages])
page=page.split("  ",1)[1]
st.sidebar.divider()
active=remaining()!="Inactive"
st.sidebar.markdown("**BRAIN browser session**")
st.sidebar.markdown(f"<span style='color:{'#22c55e' if active else '#f59e0b'}'>● {'ACTIVE' if active else 'SIGNED OUT'}</span>",unsafe_allow_html=True)
st.sidebar.metric("Session time remaining",remaining())
if st.sidebar.button("🌐 Open BRAIN login",use_container_width=True):
 webbrowser.open(BRAIN); st.session_state["awaiting_browser_login"]=True
if st.sidebar.button("✓ I have logged in — start 4h session",use_container_width=True):
 if st.session_state.get("awaiting_browser_login") or st.session_state.get("manual_login_ack"):
  save("until",(datetime.now()+timedelta(hours=4)).isoformat()); save("login_mode","manual_browser_confirmation")
  st.session_state["awaiting_browser_login"]=False; st.session_state["manual_login_ack"]=True; st.rerun()
 else: st.sidebar.warning("Open the BRAIN login page first.")
if st.sidebar.button("↪ Sign out of Alpha King",use_container_width=True):
 save("until",""); save("login_mode","")
 for k in ["awaiting_browser_login","manual_login_ack"]: st.session_state.pop(k,None)
 st.rerun()
st.sidebar.caption("Local user-confirmed timer; not remote BRAIN session verification.")
st.title("👑 Alpha King")
if page=="Dashboard":
 st.markdown('<div class="ak-hero"><h2>Research smarter. Test rigorously. Build better alphas.</h2><div class="ak-muted">Factor discovery, transparent local backtesting and BRAIN browser workflows.</div></div>',unsafe_allow_html=True)
 a=read("SELECT * FROM alphas"); t=read("SELECT * FROM tasks")
 with db() as c: u=c.execute("SELECT n FROM usage WHERE day=?",(date.today().isoformat(),)).fetchone()
 used=u[0] if u else 0
 x,y,z,w=st.columns(4); x.metric("Local backtests",used); y.metric("Remaining of 5,000",max(0,5000-used)); z.metric("Alpha candidates",len(a)); w.metric("Completed tasks",int((t.status=="Completed").sum()) if len(t) else 0)
 st.progress(min(used/5000,1),text="Local backtest counter only; 5,000 is a planning target, not a BRAIN quota.")
 st.dataframe(a.tail(10),use_container_width=True,hide_index=True) if len(a) else st.info("No alpha records yet.")
elif page=="Data Explorer":
 st.subheader("Data Explorer")
 up=st.file_uploader("Import authorized data-field CSV",type="csv")
 if up and st.button("Import fields"):
  d=pd.read_csv(up); d.columns=[x.lower() for x in d.columns]
  f=next((x for x in ["field","field_id","name"] if x in d),None)
  if not f: st.error("CSV needs field, field_id or name.")
  else:
   with db() as c:
    for _,r in d.iterrows(): c.execute("INSERT INTO fields VALUES(?,?,?)",(str(r[f]),str(r.get("dataset","")),str(r.get("description",""))))
   st.success("Imported fields."); st.rerun()
 f=read("SELECT * FROM fields ORDER BY dataset,field")
 if len(f):
  ds=st.selectbox("Dataset",["All"]+sorted(f.dataset.fillna("").unique().tolist())); v=f if ds=="All" else f[f.dataset==ds]
  st.dataframe(v,use_container_width=True,hide_index=True); st.multiselect("Manual field selection",v.field.tolist())
 st.download_button("Download CSV template","field,dataset,description\nreturns,PRICE,Daily returns\nvolume,PRICE,Trading volume\n","fields_template.csv")
elif page=="Simulation Lab":
 st.subheader("⚗️ Local Alpha Simulation Lab")
 st.info("Runs a reproducible local backtest on uploaded market data. It does not submit to or synchronize with WorldQuant BRAIN.")
 up=st.file_uploader("Upload CSV: date, symbol, close, plus optional numeric factor columns",type="csv",key="local_market_data")
 if up:
  try:
   market=pd.read_csv(up); market.columns=[str(c).strip().lower() for c in market.columns]
   if not {"date","symbol","close"}.issubset(market.columns): st.error("CSV must contain date, symbol and close.")
   else:
    market["date"]=pd.to_datetime(market["date"],errors="coerce"); market["close"]=pd.to_numeric(market["close"],errors="coerce")
    market=market.dropna(subset=["date","symbol","close"]).sort_values(["symbol","date"])
    excluded={"date","symbol","close","open","high","low","volume"}
    factors=[c for c in market.columns if c not in excluded and pd.api.types.is_numeric_dtype(market[c])]
    st.success(f"Loaded {len(market):,} rows · {market.symbol.nunique():,} instruments · {market.date.nunique():,} dates")
    st.dataframe(market.head(8),use_container_width=True,hide_index=True)
    models=["Price momentum","Price mean reversion"]+[f"Cross-sectional rank: {x}" for x in factors]+[f"Factor momentum: {x}" for x in factors]
    a,b=st.columns(2)
    strategy=a.selectbox("Signal model",models)
    lookback=a.select_slider("Lookback (trading days)",[5,10,20,40,60,120,252],value=20)
    quantile=b.slider("Long / short quantile",0.1,0.4,0.2,0.05)
    fees=b.number_input("One-way transaction cost (bps)",0.0,100.0,5.0,0.5)
    split=st.slider("In-sample portion",0.5,0.9,0.7,0.05)
    annual=st.selectbox("Trading days per year",[252,250,365])
    if st.button("▶ Run local simulation",type="primary",use_container_width=True):
     try:
      res=run_backtest(market,strategy,lookback,quantile,fees,split,annual); st.session_state["local_sim_result"]=res
      with db() as c:
       c.execute("INSERT INTO usage VALUES(?,1) ON CONFLICT(day) DO UPDATE SET n=n+1",(date.today().isoformat(),))
       m=res["metrics"]
       c.execute("INSERT INTO alphas(expr,fields,rationale,status,sharpe,fitness,turnover,correlation,created) VALUES(?,?,?,'Local simulation',?,?,?,NULL,?)",(res["expression"],res["factor"],"Local backtest on uploaded data.",m["Sharpe"],m["Fitness"],m["Turnover"],datetime.now().isoformat()))
      st.success("Local backtest completed.")
     except BacktestError as e: st.error(str(e))
     except Exception as e: st.error(f"Simulation failed: {e}")
  except Exception as e: st.error(f"Could not read dataset: {e}")
 res=st.session_state.get("local_sim_result")
 if res:
  st.divider(); st.subheader("📊 Results")
  m=res["metrics"]; cols=st.columns(5)
  for col,(label,key,fmt) in zip(cols,[("Sharpe","Sharpe","{:.2f}"),("Annual return","Annual Return","{:.1%}"),("Max drawdown","Max Drawdown","{:.1%}"),("Turnover","Turnover","{:.1%}"),("Fitness","Fitness","{:.2f}")]): col.metric(label,fmt.format(m[key]))
  st.caption(f"{res['observations']:,} instrument-days · {res['start']} to {res['end']} · {res['factor']}")
  import plotly.express as px
  fig=px.line(res["equity_curve"],x="date",y="equity",title="Cumulative portfolio growth")
  fig.update_traces(line=dict(color="black",width=2)); fig.update_layout(template="plotly_white",font=dict(color="black"),yaxis_title="Growth of 1.0")
  st.plotly_chart(fig,use_container_width=True)
  st.dataframe(pd.DataFrame(res["split_metrics"]),use_container_width=True,hide_index=True)
  st.download_button("⬇ Export daily returns and positions",res["export_csv"],"alpha_king_local_backtest.csv","text/csv")
  st.caption("Local estimates only. Data quality, survivorship, corporate actions, execution and costs can materially change results.")
 else:
  st.caption("Upload a daily panel with multiple symbols. A sample CSV layout is available below.")
  st.download_button("⬇ Download sample CSV layout","date,symbol,close,volume,custom_factor\n2024-01-02,AAA,100,12000,0.2\n2024-01-03,AAA,101,13000,0.3\n2024-01-02,BBB,50,9000,-0.1\n2024-01-03,BBB,49,9500,0.1\n","alpha_king_market_data_template.csv","text/csv")

elif page=="Tasks":
 if st.button("Add task"):
  with db() as c: c.execute("INSERT INTO tasks(name,progress,status) VALUES('Research task',0,'Queued')")
  st.rerun()
 for _,r in read("SELECT * FROM tasks ORDER BY id DESC").iterrows():
  st.write(f"{r['name']} — {r.progress}%"); n=st.slider("Progress",0,100,int(r.progress),key=f"p{r.id}")
  if st.button("Save",key=f"s{r.id}"):
   with db() as c: c.execute("UPDATE tasks SET progress=?,status=? WHERE id=?",(n,"Completed" if n==100 else "In progress",int(r.id)))
   st.rerun()
elif page=="Portfolio":
 a=read("SELECT * FROM alphas"); x,y,z=st.columns(3)
 x.metric("Alpha records",len(a)); y.metric("Submitted",int((a.status=="Submitted").sum()) if len(a) else 0); z.metric("Completed pyramids",int((a.status=="Pyramid completed").sum()) if len(a) else 0)
 if len(a): st.dataframe(a,use_container_width=True,hide_index=True)
 st.subheader("PnL graphs — black")
 up=st.file_uploader("PnL CSV: date,pnl and optional alpha",type="csv")
 if up and st.button("Import PnL"):
  d=pd.read_csv(up); d.columns=[x.lower() for x in d.columns]
  if not {"date","pnl"}.issubset(d): st.error("CSV requires date and pnl.")
  else:
   with db() as c:
    for _,r in d.iterrows(): c.execute("INSERT INTO pnl VALUES(?,?,?)",(str(r.get("alpha","Portfolio")),str(r.date),float(r.pnl)))
   st.rerun()
 p=read("SELECT * FROM pnl ORDER BY date")
 if len(p):
  import plotly.express as px
  choice=st.selectbox("Series",["All"]+sorted(p.alpha.unique())); q=p if choice=="All" else p[p.alpha==choice]
  fig=px.line(q,x="date",y="pnl",color="alpha" if choice=="All" else None); fig.update_traces(line=dict(color="black",width=2)); fig.update_layout(template="plotly_white",font=dict(color="black"))
  st.plotly_chart(fig,use_container_width=True)
 else: st.caption("Import a PnL series to display a black line graph.")
 q=a[a.sharpe.notna()&(a.sharpe>=1.5)] if len(a) else pd.DataFrame()
 if len(q):
  b=BytesIO()
  with pd.ExcelWriter(b,engine="openpyxl") as w: q.to_excel(w,index=False)
  st.download_button("Export Sharpe ≥ 1.5 to Excel",b.getvalue(),"qualified_alphas.xlsx")
 up2=st.file_uploader("Import actual simulation CSV: expression,sharpe",type="csv",key="sim")
 if up2 and st.button("Import actual results"):
  d=pd.read_csv(up2); d.columns=[x.lower() for x in d.columns]
  if not {"expression","sharpe"}.issubset(d): st.error("Need expression and sharpe columns.")
  else:
   with db() as c:
    for _,r in d.iterrows(): c.execute("INSERT INTO alphas(expr,fields,rationale,status,sharpe,fitness,turnover,correlation,created) VALUES(?,?,?,'Brain simulated',?,?,?,?,?)",(r.expression,str(r.get("fields","")),str(r.get("rationale","")),float(r.sharpe),r.get("fitness"),r.get("turnover"),r.get("correlation"),datetime.now().isoformat()))
    c.execute("INSERT INTO usage VALUES(?,?) ON CONFLICT(day) DO UPDATE SET n=n+excluded.n",(date.today().isoformat(),len(d)))
   st.rerun()
elif page=="Competitions":
 st.warning("Live competitions require authorized Brain integration.")
 for _,r in read("SELECT * FROM comps").iterrows(): st.write(r["name"],r.status,r.details)
 with st.expander("Add competition"):
  n=st.text_input("Name"); d=st.text_area("Details"); s=st.selectbox("Status",["Available","Upcoming","In progress","Closed"])
  if st.button("Save competition"):
   with db() as c: c.execute("INSERT INTO comps(name,details,status) VALUES(?,?,?)",(n,d,s))
   st.rerun()
elif page=="Template Home":
 st.subheader("Template Home — edit your alpha templates")
 t=read("SELECT * FROM templates ORDER BY id")
 if len(t):
  name=st.selectbox("Template to edit",t.name.tolist()); r=t[t.name==name].iloc[0]
  nn=st.text_input("Template name",r["name"]); ex=st.text_area("Expression",r.expr); desc=st.text_area("Description",r.description)
  a,b=st.columns(2)
  if a.button("Save changes"):
   try:
    with db() as c: c.execute("UPDATE templates SET name=?,expr=?,description=? WHERE id=?",(nn,ex,desc,int(r.id)))
    st.success("Saved."); st.rerun()
   except sqlite3.IntegrityError: st.error("Name already exists.")
  if b.button("Delete template"):
   with db() as c: c.execute("DELETE FROM templates WHERE id=?",(int(r.id),))
   st.rerun()
 st.divider(); st.subheader("Add new template")
 n=st.text_input("New template name"); e=st.text_area("New expression","{x}"); d=st.text_input("Purpose")
 if st.button("Add template"):
  try:
   with db() as c: c.execute("INSERT INTO templates(name,expr,description) VALUES(?,?,?)",(n,e,d))
   st.rerun()
  except sqlite3.IntegrityError: st.error("Name already exists.")
 st.markdown("`{x}` = random field from dataset 1; `{x2}` = random field from dataset 2; `{d}` = trading-day lookback.")
 st.code("rank(ts_rank(ts_scale({x}, {d}), {d}))")
 st.code("Group_rank({x} + {x2}, industry)")
elif page=="AI Alpha Lab":
 st.subheader("Template-driven AI Alpha Lab")
 prompt=st.text_area("Editable primary prompt",setting("prompt"),height=160)
 if st.button("Save prompt"): save("prompt",prompt); st.success("Saved.")
 f=read("SELECT field,dataset FROM fields"); t=read("SELECT * FROM templates ORDER BY id")
 if len(f) and len(t):
  tn=st.selectbox("Template",t.name.tolist()); tr=t[t.name==tn].iloc[0]; st.code(tr.expr)
  ds=sorted(f.dataset.fillna("").unique().tolist()); mode=st.radio("Mode",["Single dataset","Two different datasets"],horizontal=True)
  d1=st.selectbox("Dataset 1",ds); d2=st.selectbox("Dataset 2",[x for x in ds if x!=d1]) if mode.startswith("Two") and len(ds)>1 else None
  days=st.text_input("Trading-day lookbacks", "5,10,20,60,120,252"); count=st.number_input("Candidates",1,30,5)
  key=st.text_input("Gemini API key (session only)",type="password",key="gemini_key")
  if st.button("Generate alpha candidates",type="primary"):
   try: look=[int(x.strip()) for x in days.split(",") if int(x.strip())>0]
   except: look=[]
   one=f[f.dataset.fillna("")==d1].field.astype(str).tolist(); two=f[f.dataset.fillna("")==d2].field.astype(str).tolist() if d2 else []
   if not look or not one or (mode.startswith("Two") and not two): st.error("Check selected datasets and trading-day lookbacks.")
   else:
    ideas=[]
    for _ in range(int(count)):
     x=random.choice(one); x2=random.choice(two) if two else ""; dd=random.choice(look)
     ideas.append({"expr":str(tr.expr).replace("{x}",x).replace("{x2}",x2).replace("{d}",str(dd)),"fields":x+(", "+x2 if x2 else ""),"why":"Template-instantiated hypothesis; not backtested."})
    try:
     if key:
      from google import genai
      client=genai.Client(api_key=key)
      result=client.models.generate_content(model="gemini-2.5-flash",contents=prompt+"\nReview these candidate expressions and explain risks. Return JSON array with expr, fields, why. Do not invent simulation metrics: "+json.dumps(ideas)).text
      result=result.replace("```json","").replace("```",""); ideas=json.loads(result[result.find("["):result.rfind("]")+1])
    except Exception as err: st.warning(f"Gemini review skipped: {err}")
    with db() as c:
     for v in ideas: c.execute("INSERT INTO alphas(expr,fields,rationale,status,created) VALUES(?,?,?,'Generated',?)",(v.get("expr",v.get("expression","")),str(v.get("fields","")),str(v.get("why",v.get("rationale",""))),datetime.now().isoformat()))
    st.success(f"Saved {len(ideas)} candidates."); st.rerun()
 else: st.info("Import field metadata and create templates to begin.")
elif page=="BRAIN Access":
 st.subheader("🌐 WorldQuant BRAIN browser access")
 st.markdown('<div class="ak-hero"><h3>Sign in securely on the official platform</h3><div class="ak-muted">Your credentials stay between you and WorldQuant. Alpha King never asks for or stores your BRAIN password.</div></div>',unsafe_allow_html=True)
 st.write("1. Open the official BRAIN login page.")
 if st.button("🌐 Open WorldQuant BRAIN",type="primary"):
  webbrowser.open(BRAIN); st.session_state["awaiting_browser_login"]=True
 st.write("2. Sign in directly on WorldQuant, complete any verification, then return here.")
 st.write("3. Confirm login to activate the four-hour local timer.")
 if st.button("✓ I have successfully logged in — activate session",use_container_width=True):
  save("until",(datetime.now()+timedelta(hours=4)).isoformat()); save("login_mode","manual_browser_confirmation")
  st.session_state["awaiting_browser_login"]=False; st.session_state["manual_login_ack"]=True
  st.success("Local session marked ACTIVE. Four-hour timer started."); st.rerun()
 if remaining()!="Inactive": st.success(f"🟢 ACTIVE · {remaining()} remaining")
 else: st.warning("🟠 INACTIVE · Open BRAIN and confirm login to start your session.")
 st.caption("This is a user-confirmed local status, not technical verification of the remote BRAIN login. The app does not read cookies or synchronize account data.")
 st.divider(); st.subheader("🔐 Account safety")
 st.markdown("- BRAIN password is never requested in Alpha King.\\n- Use the official BRAIN site for login and account security.\\n- Use **Sign out of Alpha King** in the sidebar to end the local timer.")
 st.link_button("Open official WorldQuant BRAIN",BRAIN)
 st.caption("Browser-only mode: live BRAIN data synchronization and remote simulation submission are disabled.")
