import numpy as np, pandas as pd
import orb_refinement_stage2 as s2

CFG={"orb":15,"exec":15,"ema":50,"atr_len":7,"tp_mult":1.5,
     "stop_mode":"or_opposite","stop_mult":1.0,"entry":"next_open"}
DISCOVERY=list(range(2016,2021))
VALIDATION=[2021,2022,2023]
CONFIRM=[2024,2025]
LATEST=[2026]
ALL=DISCOVERY+VALIDATION+CONFIRM+LATEST

def wilder(s,n):
    s=pd.Series(s,dtype=float)
    out=np.full(len(s),np.nan)
    if len(s)<n: return pd.Series(out,index=s.index)
    out[n-1]=np.nanmean(s.iloc[:n])
    for i in range(n,len(s)):
        out[i]=(out[i-1]*(n-1)+s.iloc[i])/n
    return pd.Series(out,index=s.index)

def add_indicators(ex):
    z=ex.copy()
    # Session VWAP
    tp=(z.high+z.low+z.close)/3.0
    z["cum_pv"]=(tp*z.volume).groupby(z.session).cumsum()
    z["cum_v"]=z.volume.groupby(z.session).cumsum()
    z["vwap"]=z.cum_pv/z.cum_v

    # RSI 14
    d=z.close.diff()
    up=d.clip(lower=0); dn=(-d).clip(lower=0)
    au=wilder(up,14); ad=wilder(dn,14)
    rs=au/ad.replace(0,np.nan)
    z["rsi14"]=100-(100/(1+rs))

    # DMI/ADX 14
    prev_close=z.close.shift(1)
    tr=pd.concat([(z.high-z.low),(z.high-prev_close).abs(),(z.low-prev_close).abs()],axis=1).max(axis=1)
    upmove=z.high.diff(); dnmove=-z.low.diff()
    pdm=pd.Series(np.where((upmove>dnmove)&(upmove>0),upmove,0.0),index=z.index)
    mdm=pd.Series(np.where((dnmove>upmove)&(dnmove>0),dnmove,0.0),index=z.index)
    atr14=wilder(tr,14)
    pdi=100*wilder(pdm,14)/atr14
    mdi=100*wilder(mdm,14)/atr14
    dx=100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan)
    z["pdi14"]=pdi; z["mdi14"]=mdi; z["adx14"]=wilder(dx,14)

    # EMA50 slope normalized by strategy ATR7
    z["ema50_slope4_atr7"]=(z["ema50"]-z["ema50"].shift(4))/z["atr7"]

    # Relative volume for same 15m clock slot, previous 20 occurrences only
    z["clock"]=z.index.strftime("%H:%M")
    z["slot_vol_med20"]=z.groupby("clock")["volume"].transform(lambda s:s.shift(1).rolling(20,min_periods=10).median())
    z["signal_rvol20"]=z.volume/z.slot_vol_med20
    return z

def daily_features(x):
    d=x.groupby("session").agg(open=("open","first"),high=("high","max"),low=("low","min"),
                                close=("close","last"),volume=("volume","sum"))
    d["prev_close"]=d.close.shift(1)
    d["prev_high"]=d.high.shift(1); d["prev_low"]=d.low.shift(1)
    tr=pd.concat([(d.high-d.low),(d.high-d.prev_close).abs(),(d.low-d.prev_close).abs()],axis=1).max(axis=1)
    d["daily_atr20"]=tr.shift(1).rolling(20,min_periods=10).mean()
    d["gap"]=d.open-d.prev_close
    d["gap_atr"]=d.gap/d.daily_atr20
    return d

def orb_session_features(x):
    rows=[]
    for sess,g in x.groupby("session",sort=True):
        st=pd.Timestamp(f"{sess} 09:30",tz=s2.NY)
        en=st+pd.Timedelta(minutes=15)
        q=g[(g.index>=st)&(g.index<en)]
        if len(q)<10: continue
        rows.append({"session":sess,"orh":float(q.high.max()),"orl":float(q.low.min()),
                     "or_width":float(q.high.max()-q.low.min()),"or_vol":float(q.volume.sum())})
    r=pd.DataFrame(rows).set_index("session").sort_index()
    r["or_vol_med20"]=r.or_vol.shift(1).rolling(20,min_periods=10).median()
    r["or_rvol20"]=r.or_vol/r.or_vol_med20
    return r

def build_trade_features(x,ex):
    daily=daily_features(x)
    orb=orb_session_features(x)
    rows=[]
    for sess,xd in x.groupby("session",sort=True):
        de=ex[ex.session==sess]
        if len(de)==0: continue
        o=s2.get_or(xd,sess,15)
        if not o: continue
        orh,orl,orb_end=o
        sig=s2.signal_for(de,orh,orl,orb_end,50)
        if not sig: continue
        signal_ts,b,dirn=sig
        trade=s2.trade_for_session(xd,de,sess,CFG)
        if trade is None: continue
        br=ex.loc[signal_ts]
        dd=daily.loc[sess] if sess in daily.index else None
        oo=orb.loc[sess] if sess in orb.index else None
        direction=1 if trade["direction"]=="L" else -1
        trade.update({
            "signal_close":float(br.close),
            "signal_vwap":float(br.vwap),
            "vwap_aligned":bool((direction==1 and br.close>br.vwap) or (direction==-1 and br.close<br.vwap)),
            "dmi_aligned":bool((direction==1 and br.pdi14>br.mdi14) or (direction==-1 and br.mdi14>br.pdi14)),
            "adx14":float(br.adx14) if np.isfinite(br.adx14) else np.nan,
            "rsi14":float(br.rsi14) if np.isfinite(br.rsi14) else np.nan,
            "rsi_aligned":bool((direction==1 and br.rsi14>50) or (direction==-1 and br.rsi14<50)) if np.isfinite(br.rsi14) else False,
            "slope4":float(br.ema50_slope4_atr7) if np.isfinite(br.ema50_slope4_atr7) else np.nan,
            "slope_aligned":bool(direction*br.ema50_slope4_atr7>0) if np.isfinite(br.ema50_slope4_atr7) else False,
            "signal_rvol20":float(br.signal_rvol20) if np.isfinite(br.signal_rvol20) else np.nan,
            "or_rvol20":float(oo.or_rvol20) if oo is not None and np.isfinite(oo.or_rvol20) else np.nan,
            "or_width_atr20":float(oo.or_width/dd.daily_atr20) if oo is not None and dd is not None and np.isfinite(dd.daily_atr20) and dd.daily_atr20>0 else np.nan,
            "gap_atr":float(dd.gap_atr) if dd is not None and np.isfinite(dd.gap_atr) else np.nan,
            "gap_aligned":bool(direction*dd.gap>0) if dd is not None and np.isfinite(dd.gap) else False,
            "pdhpdl_break":bool((direction==1 and br.close>dd.prev_high) or (direction==-1 and br.close<dd.prev_low)) if dd is not None and np.isfinite(dd.prev_high) and np.isfinite(dd.prev_low) else False,
            "signal_minutes":signal_ts.hour*60+signal_ts.minute,
        })
        rows.append(trade)
    return pd.DataFrame(rows).sort_values("entry_time").reset_index(drop=True)

def net_r(t,product="ES",slip=1):
    if len(t)==0: return pd.Series(dtype=float)
    point=50.0 if product=="ES" else 5.0
    comm=5.0 if product=="ES" else 1.50
    cp=slip*s2.TICK+comm/point
    return t.raw_pnl_pts.astype(float)/t.risk_pts.astype(float)-cp/t.risk_pts.astype(float)

def stats(t,years,product="ES"):
    q=t[t.year.isin(years)].copy()
    r=net_r(q,product,1)
    if len(r)==0:
        return {"n":0,"win":np.nan,"avgR":np.nan,"PF":np.nan,"totalR":0,"maxDD":np.nan,"positive_years":0}
    w=r[r>0]; l=r[r<=0]
    pf=w.sum()/abs(l.sum()) if len(l) and abs(l.sum())>0 else np.inf
    eq=r.cumsum(); dd=eq-eq.cummax()
    pos=0
    for y in years:
        ry=net_r(q[q.year==y],product,1)
        if len(ry) and ry.sum()>0: pos+=1
    return {"n":len(r),"win":100*(r>0).mean(),"avgR":r.mean(),"PF":pf,"totalR":r.sum(),
            "maxDD":dd.min(),"positive_years":pos}

def filter_defs(t):
    dev=t[t.year.isin(DISCOVERY)]
    lo=float(dev.or_width_atr20.quantile(.20))
    hi=float(dev.or_width_atr20.quantile(.80))
    return [
      ("BASE",lambda q: pd.Series(True,index=q.index)),
      ("VWAP",lambda q:q.vwap_aligned),
      ("DMI",lambda q:q.dmi_aligned),
      ("ADX20_DMI",lambda q:q.dmi_aligned&(q.adx14>=20)),
      ("RSI50",lambda q:q.rsi_aligned),
      ("EMA50_SLOPE",lambda q:q.slope_aligned),
      ("SIGNAL_RVOL1",lambda q:q.signal_rvol20>=1.0),
      ("OR_RVOL1",lambda q:q.or_rvol20>=1.0),
      ("GAP_ALIGNED",lambda q:q.gap_aligned),
      ("PDH_PDL_BREAK",lambda q:q.pdhpdl_break),
      ("EARLY_1100",lambda q:q.signal_minutes<11*60),
      (f"MODERATE_OR_{lo:.3f}_{hi:.3f}",lambda q:(q.or_width_atr20>=lo)&(q.or_width_atr20<=hi)),
      ("VWAP_ADX20_DMI",lambda q:q.vwap_aligned&q.dmi_aligned&(q.adx14>=20)),
      ("VWAP_SLOPE",lambda q:q.vwap_aligned&q.slope_aligned),
      ("VWAP_SIGNAL_RVOL1",lambda q:q.vwap_aligned&(q.signal_rvol20>=1.0)),
      ("ADX20_DMI_SIGNAL_RVOL1",lambda q:q.dmi_aligned&(q.adx14>=20)&(q.signal_rvol20>=1.0)),
      ("VWAP_ADX20_DMI_SIGNAL_RVOL1",lambda q:q.vwap_aligned&q.dmi_aligned&(q.adx14>=20)&(q.signal_rvol20>=1.0)),
    ],lo,hi

def evaluate_all(t):
    defs,lo,hi=filter_defs(t)
    rows=[]
    masks={}
    for name,fn in defs:
        m=fn(t).fillna(False)
        masks[name]=m
        row={"filter":name,"or20":lo,"or80":hi}
        for label,years in [("DEV",DISCOVERY),("VAL",VALIDATION),("CONF",CONFIRM),("YTD26",LATEST)]:
            s=stats(t[m],years,"ES")
            for k,v in s.items(): row[f"{label}_{k}"]=v
        rows.append(row)
    return pd.DataFrame(rows),masks

def rank_dev(df):
    z=df.copy()
    z=z[z.DEV_n>=300].copy()
    z["DEV_score"]=z.DEV_avgR+0.12*(z.DEV_PF-1)+0.02*(z.DEV_positive_years/5)
    return z.sort_values(["DEV_score","DEV_PF","DEV_avgR"],ascending=False).reset_index(drop=True)

def select_after_validation(devrank,full):
    top=devrank.head(5)[["filter","DEV_avgR","DEV_PF","DEV_positive_years"]]
    m=top.merge(full[["filter","VAL_n","VAL_avgR","VAL_PF","VAL_positive_years"]],on="filter")
    m["passes_val"]=(m.VAL_n>=200)&(m.VAL_avgR>0)&(m.VAL_PF>=1.05)&(m.VAL_positive_years>=2)
    m["worst_pf"]=m[["DEV_PF","VAL_PF"]].min(axis=1)
    m["mean_avgR"]=m[["DEV_avgR","VAL_avgR"]].mean(axis=1)
    return m.sort_values(["passes_val","worst_pf","mean_avgR"],ascending=[False,False,False]).reset_index(drop=True)

def direction_diag(t):
    rows=[]
    for side in ["L","S"]:
        q=t[t.direction==side]
        row={"side":side}
        for label,years in [("DEV",DISCOVERY),("VAL",VALIDATION),("CONF",CONFIRM),("YTD26",LATEST)]:
            s=stats(q,years)
            for k,v in s.items(): row[f"{label}_{k}"]=v
        rows.append(row)
    return pd.DataFrame(rows)

def main():
    print("=== ORB FROZEN WINNER FILTER DIAGNOSTICS ===")
    print("Baseline frozen: ORB15 / 15m execution / EMA50 / ATR7 / 1.5 ATR TP / opposite OR stop / next-open / one trade per day.")
    print("Predeclared indicator candidates: VWAP, DMI/ADX, RSI50, EMA slope, signal & opening RVOL, gap, PDH/PDL, early signal, moderate OR width; limited logical combos.")
    x=s2.load_all()
    ex=s2.resample_exec(x,15)
    ex=add_indicators(ex)
    t=build_trade_features(x,ex)
    t.to_csv("orb_filter_trade_features.csv",index=False)
    print("BASE TRADES",len(t),"years",t.year.min(),t.year.max())

    full,masks=evaluate_all(t)
    full.to_csv("orb_filter_all_results.csv",index=False)
    dr=rank_dev(full)
    dr.to_csv("orb_filter_discovery_rank.csv",index=False)
    sel=select_after_validation(dr,full)
    sel.to_csv("orb_filter_selection.csv",index=False)
    ddiag=direction_diag(t)
    ddiag.to_csv("orb_filter_direction_diagnostic.csv",index=False)

    print("\nDISCOVERY RANK (2016-2020 only)\n",dr.head(12)[["filter","DEV_n","DEV_win","DEV_avgR","DEV_PF","DEV_positive_years","DEV_score"]].round(4).to_string(index=False))
    print("\nTOP-5 VALIDATION SELECTION\n",sel.round(4).to_string(index=False))
    print("\nALL BLOCKS\n",full[["filter","DEV_n","DEV_avgR","DEV_PF","VAL_n","VAL_avgR","VAL_PF","CONF_n","CONF_avgR","CONF_PF","YTD26_n","YTD26_avgR","YTD26_PF"]].round(4).to_string(index=False))
    print("\nDIRECTION DIAGNOSTIC\n",ddiag.round(4).to_string(index=False))

    winner=sel.iloc[0]["filter"]
    print("\nFROZEN FILTER WINNER AFTER DEV+VAL:",winner)
    wr=full[full["filter"]==winner].iloc[0]
    print("CONFIRM 2024-25 avgR/PF",round(wr.CONF_avgR,4),round(wr.CONF_PF,4))
    print("2026 YTD avgR/PF",round(wr.YTD26_avgR,4),round(wr.YTD26_PF,4))
    print("NOTE: 2024-25 are confirmation, not pristine holdout; 2026 YTD is the newest check.")

if __name__=="__main__":
    main()
