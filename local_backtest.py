"""Transparent local cross-sectional alpha backtester."""
import numpy as np
import pandas as pd

class BacktestError(ValueError): pass

def _metrics(r, turnover, annual):
 r=pd.to_numeric(r,errors="coerce").dropna()
 if len(r)<3: raise BacktestError("Not enough portfolio return dates.")
 vol=float(r.std(ddof=1)); sharpe=float(np.sqrt(annual)*r.mean()/vol) if vol>1e-12 else 0.0
 eq=(1+r).cumprod(); dd=eq/eq.cummax()-1
 ann=float(eq.iloc[-1]**(annual/len(r))-1) if eq.iloc[-1]>0 else -1.0
 down=float(r[r<0].std(ddof=1)) if (r<0).sum()>1 else 0.0
 fitness=sharpe*np.sqrt(max(0.0,abs(float(r.mean()))/max(float(r.std(ddof=1)),1e-12)))
 return {"Sharpe":sharpe,"Annual Return":ann,"Max Drawdown":float(dd.min()),"Turnover":float(turnover.mean()) if len(turnover) else 0.0,"Fitness":float(fitness),"Volatility":float(vol*np.sqrt(annual)),"Sortino":float(np.sqrt(annual)*r.mean()/down) if down>1e-12 else 0.0,"Win Rate":float((r>0).mean()),"Trading Days":int(len(r))}

def run_backtest(data,strategy,lookback,quantile,fee_bps,train_split,annualization):
 d=data.copy(); d.columns=[str(c).strip().lower() for c in d.columns]
 if not {"date","symbol","close"}.issubset(d.columns): raise BacktestError("CSV needs date, symbol and close.")
 d["date"]=pd.to_datetime(d["date"],errors="coerce"); d["close"]=pd.to_numeric(d["close"],errors="coerce"); d["symbol"]=d["symbol"].astype(str)
 d=d.dropna(subset=["date","symbol","close"]).sort_values(["symbol","date"]).drop_duplicates(["date","symbol"],keep="last")
 if d.symbol.nunique()<3: raise BacktestError("At least three instruments are required.")
 if d.date.nunique()<max(lookback+10,30): raise BacktestError(f"At least {max(lookback+10,30)} dates are needed.")
 d["forward_return"]=d.groupby("symbol").close.shift(-1)/d.close-1
 if strategy=="Price momentum":
  d["signal"]=d.groupby("symbol").close.transform(lambda x:x.pct_change(lookback)); factor=f"close momentum {lookback}d"; expr=f"rank(ts_delta(close,{lookback}))"
 elif strategy=="Price mean reversion":
  d["signal"]=-d.groupby("symbol").close.transform(lambda x:x.pct_change(lookback)); factor=f"negative close momentum {lookback}d"; expr=f"-rank(ts_delta(close,{lookback}))"
 elif strategy.startswith("Cross-sectional rank: "):
  factor=strategy.split(": ",1)[1]; d["signal"]=pd.to_numeric(d[factor],errors="coerce"); expr=f"rank({factor})"
 elif strategy.startswith("Factor momentum: "):
  factor=strategy.split(": ",1)[1]; d["signal"]=d.groupby("symbol")[factor].transform(lambda x:pd.to_numeric(x,errors="coerce").pct_change(lookback)); expr=f"rank(ts_delta({factor},{lookback}))"
 else: raise BacktestError("Unsupported model.")
 d=d.replace([np.inf,-np.inf],np.nan).dropna(subset=["signal","forward_return"])
 frames=[]
 for dt,g in d.groupby("date",sort=True):
  g=g.copy(); rank=g.signal.rank(pct=True); q=min(max(float(quantile),.05),.45); longs=rank>=1-q; shorts=rank<=q
  if longs.sum()==0 or shorts.sum()==0: continue
  g["weight"]=0.0; g.loc[longs,"weight"]=.5/longs.sum(); g.loc[shorts,"weight"]=-.5/shorts.sum(); frames.append(g)
 if not frames: raise BacktestError("No dates with valid cross-sectional ranks.")
 p=pd.concat(frames).sort_values(["date","symbol"])
 p["prev_weight"]=p.groupby("symbol").weight.shift(1).fillna(0); p["turnover_part"]=(p.weight-p.prev_weight).abs()
 daily=pd.DataFrame({"gross_return":(p.weight*p.forward_return).groupby(p.date).sum(),"turnover":p.groupby("date").turnover_part.sum()})
 daily["net_return"]=daily.gross_return-daily.turnover*float(fee_bps)/10000
 daily=daily.replace([np.inf,-np.inf],np.nan).dropna()
 if len(daily)<20: raise BacktestError("Fewer than 20 usable dates; inspect missing data/history.")
 cut=max(5,min(len(daily)-5,int(len(daily)*train_split))); split_metrics=[]
 for name,seg in [("In-sample",daily.iloc[:cut]),("Out-of-sample",daily.iloc[cut:]),("Full period",daily)]:
  split_metrics.append({"Period":name,**_metrics(seg.net_return,seg.turnover,annualization)})
 daily["equity"]=(1+daily.net_return).cumprod()
 curve=daily.reset_index(); curve["date"]=pd.to_datetime(curve.date).dt.strftime("%Y-%m-%d")
 export=p[["date","symbol","signal","weight","forward_return"]].merge(daily[["net_return","turnover"]],left_on="date",right_index=True,how="left")
 export["date"]=pd.to_datetime(export.date).dt.strftime("%Y-%m-%d")
 return {"metrics":split_metrics[-1],"split_metrics":split_metrics,"equity_curve":curve[["date","equity"]],"observations":len(p),"start":str(daily.index.min().date()),"end":str(daily.index.max().date()),"factor":factor,"expression":expr,"export_csv":export.to_csv(index=False)}
