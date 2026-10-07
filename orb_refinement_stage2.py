import io, math, requests, numpy as np, pandas as pd

BASE="https://raw.githubusercontent.com/worldtradingchampion-source/btcdata/main/ES_1min_{}.csv"
NY="America/New_York"
TICK=0.25
DISCOVERY=list(range(2016,2021))
VALIDATION=[2021,2022,2023]
CONFIRM=[2024,2025]
LATEST=[2026]
ALL_YEARS=DISCOVERY+VALIDATION+CONFIRM+LATEST
EMA_LENS=[9,20,50]
ATR_LENS=[7,10,14,21]
TP_MULTS=[0.50,0.75,1.00,1.25,1.50]
ATR_STOP_MULTS=[0.50,0.75,1.00,1.25,1.50]
ORB_MINS=[15,30]
EXEC_MINS=[5,15]
CUTOFF_MIN=15*60+30

def rma(s,n):
    x=pd.Series(s,dtype=float)
    out=np.full(len(x),np.nan)
    if len(x)<n: return pd.Series(out,index=x.index)
    vals=x.values
    out[n-1]=np.nanmean(vals[:n])
    for i in range(n,len(vals)):
        out[i]=(out[i-1]*(n-1)+vals[i])/n
    return pd.Series(out,index=x.index)

def load_year(y):
    q=requests.get(BASE.format(y),timeout=180)
    print("LOAD",y,q.status_code,len(q.content))
    q.raise_for_status()
    d=pd.read_csv(io.StringIO(q.text))
    d["datetime_et"]=pd.to_datetime(d["datetime_et"],utc=True).dt.tz_convert(NY)
    for c in ["open","high","low","close","volume"]:
        d[c]=pd.to_numeric(d[c],errors="coerce")
    d=d.dropna(subset=["datetime_et","open","high","low","close","volume","symbol"]).copy()
    d["rth_bool"]=d["rth"].astype(str).str.lower().eq("true")
    r=d[d.rth_bool].copy()
    r["session"]=r.datetime_et.dt.date
    ns=r.groupby("session").symbol.nunique()
    roll=set(ns[ns>1].index)
    if roll:
        print(" exclude roll sessions",len(roll))
        r=r[~r.session.isin(roll)].copy()
    before=len(r)
    r=(r.sort_values(["datetime_et","volume"],ascending=[True,False])
        .drop_duplicates("datetime_et",keep="first").sort_values("datetime_et"))
    print(" RTH rows",len(r),"sessions",r.session.nunique(),"dups_removed",before-len(r))
    return r[["datetime_et","open","high","low","close","volume","symbol","session"]].copy()

def load_all():
    parts=[load_year(y) for y in ALL_YEARS]
    x=pd.concat(parts,ignore_index=True).sort_values("datetime_et")
    x=x.drop_duplicates("datetime_et",keep="first").set_index("datetime_et")
    x["session"]=x.index.date
    return x

def resample_exec(x,mins):
    z=x[["open","high","low","close","volume"]].resample(
        f"{mins}min",origin="start_day",offset="30min",label="left",closed="left"
    ).agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
    z=z[(z.index.time>=pd.Timestamp("09:30").time())&(z.index.time<pd.Timestamp("16:00").time())].copy()
    z["session"]=z.index.date
    z["bar_end"]=z.index+pd.Timedelta(minutes=mins)
    prev=z.close.shift(1)
    tr=pd.concat([(z.high-z.low),(z.high-prev).abs(),(z.low-prev).abs()],axis=1).max(axis=1)
    for n in EMA_LENS:
        z[f"ema{n}"]=z.close.ewm(span=n,adjust=False).mean()
    for n in ATR_LENS:
        z[f"atr{n}"]=rma(tr,n)
    return z

def tod(ts): return ts.hour*60+ts.minute

def get_or(x_day,sess,orb):
    s=pd.Timestamp(f"{sess} 09:30",tz=NY)
    e=s+pd.Timedelta(minutes=orb)
    w=x_day[(x_day.index>=s)&(x_day.index<e)]
    if len(w)<max(8,orb-3): return None
    return float(w.high.max()),float(w.low.min()),e

def signal_for(day_exec,orh,orl,orb_end,ema_len):
    q=day_exec[(day_exec.index>=orb_end)&(day_exec.index.map(tod)<CUTOFF_MIN)]
    for ts,b in q.iterrows():
        ev=float(b[f"ema{ema_len}"])
        if not np.isfinite(ev): continue
        c=float(b.close)
        if c>orh and c>ev: return ts,b,1
        if c<orl and c<ev: return ts,b,-1
    return None

def entry_info(x_day,signal_ts,b,exec_mins,mode):
    sig_end=signal_ts+pd.Timedelta(minutes=exec_mins)
    if mode=="close":
        return sig_end,float(b.close)
    nxt=x_day[x_day.index>=sig_end]
    if len(nxt)==0 or nxt.index[0].date()!=signal_ts.date(): return None
    return nxt.index[0],float(nxt.iloc[0].open)

def simulate(x_day,start_ts,entry,direction,stop,target):
    risk=(entry-stop) if direction==1 else (stop-entry)
    if risk<TICK-1e-9: return None
    z=x_day[x_day.index>=start_ts]
    if len(z)==0: return None
    for ts,r in z.iterrows():
        hs=(float(r.low)<=stop) if direction==1 else (float(r.high)>=stop)
        ht=(float(r.high)>=target) if direction==1 else (float(r.low)<=target)
        if hs and ht: return -risk,ts,"ambiguous_stop_first"
        if hs: return -risk,ts,"stop"
        if ht:
            pnl=(target-entry) if direction==1 else (entry-target)
            return pnl,ts,"target"
    px=float(z.iloc[-1].close)
    pnl=(px-entry) if direction==1 else (entry-px)
    return pnl,z.index[-1],"eod"

def trade_for_session(x_day,day_exec,sess,cfg):
    o=get_or(x_day,sess,cfg["orb"])
    if not o: return None
    orh,orl,orb_end=o
    s=signal_for(day_exec,orh,orl,orb_end,cfg["ema"])
    if not s: return None
    signal_ts,b,dirn=s
    a=entry_info(x_day,signal_ts,b,cfg["exec"],cfg["entry"])
    if not a: return None
    start_ts,entry=a
    atr=float(b[f"atr{cfg['atr_len']}"])
    if not np.isfinite(atr) or atr<TICK: return None
    if cfg["stop_mode"]=="or_opposite":
        stop=orl if dirn==1 else orh
    elif cfg["stop_mode"]=="signal_extreme":
        stop=float(b.low)-TICK if dirn==1 else float(b.high)+TICK
    elif cfg["stop_mode"]=="atr":
        stop=entry-dirn*cfg["stop_mult"]*atr
    else:
        raise ValueError(cfg["stop_mode"])
    risk=(entry-stop) if dirn==1 else (stop-entry)
    if risk<TICK: return None
    target=entry+dirn*cfg["tp_mult"]*atr
    sim=simulate(x_day,start_ts,entry,dirn,stop,target)
    if not sim: return None
    pnl_pts,exit_ts,reason=sim
    return {"session":pd.Timestamp(sess),"year":sess.year,"direction":"L" if dirn==1 else "S",
            "signal_time":signal_ts,"entry_time":start_ts,"exit_time":exit_ts,
            "entry":entry,"stop":stop,"target":target,"atr":atr,"risk_pts":risk,
            "raw_pnl_pts":pnl_pts,"raw_R":pnl_pts/risk,"exit_reason":reason}

def cost_points(product="ES",slip_ticks=1):
    point=50.0 if product=="ES" else 5.0
    comm=5.0 if product=="ES" else 1.50
    return slip_ticks*TICK+comm/point

def add_net(t,product="ES",slip=1):
    cp=cost_points(product,slip)
    v=t.raw_pnl_pts.astype(float)-cp
    r=v/t.risk_pts.astype(float)
    return v,r

def stat_from(t,product="ES",slip=1):
    if t is None or len(t)==0:
        return dict(n=0,win=np.nan,avgR=np.nan,PF=np.nan,totalR=0,maxDD=np.nan,avgPts=np.nan,totalPts=0)
    pts,r=add_net(t,product,slip)
    wins=r[r>0]; losses=r[r<=0]
    pf=wins.sum()/abs(losses.sum()) if len(losses) and abs(losses.sum())>0 else np.inf
    eq=r.cumsum(); dd=eq-eq.cummax()
    return dict(n=len(r),win=100*(r>0).mean(),avgR=r.mean(),PF=pf,totalR=r.sum(),
                maxDD=dd.min(),avgPts=pts.mean(),totalPts=pts.sum())

def robustness(t,years):
    st=stat_from(t)
    yr=[]
    for y in years:
        s=stat_from(t[t.year==y])
        yr.append((y,s))
    positive=sum(1 for _,s in yr if s["totalR"]>0)
    pfs=[s["PF"] for _,s in yr if s["n"]>0 and np.isfinite(s["PF"])]
    floor_pf=min(pfs) if pfs else -np.inf
    z=t.copy()
    if len(z)>10:
        _,nr=add_net(z)
        keep=nr.sort_values(ascending=False).index[10:]
        drop=stat_from(z.loc[keep])
    else: drop=stat_from(z)
    return st,yr,positive,floor_pf,drop

def cfg_id(c):
    return f"ORB{c['orb']}_X{c['exec']}_EMA{c['ema']}_ATR{c['atr_len']}_TP{c['tp_mult']}_{c['stop_mode']}_SM{c['stop_mult']}_{c['entry']}"

def run_cfg(x,exec_cache,cfg,years):
    out=[]
    xs=x[x.index.year.isin(years)]
    ex=exec_cache[cfg["exec"]]
    for sess,xd in xs.groupby("session",sort=True):
        de=ex[ex.session==sess]
        if len(de)==0: continue
        q=trade_for_session(xd,de,sess,cfg)
        if q: out.append(q)
    return pd.DataFrame(out)

def summarize_cfg(t,cfg,years):
    st,yr,pos,floor,drop=robustness(t,years)
    score=(st["avgR"] if np.isfinite(st["avgR"]) else -9)
    score+=0.12*max(-1,min(2,(st["PF"] if np.isfinite(st["PF"]) else 0)-1))
    score+=0.03*(pos/len(years))
    score+=0.03*max(-1,min(2,floor-1 if np.isfinite(floor) else -1))
    score+=0.04*(drop["avgR"] if np.isfinite(drop["avgR"]) else -1)
    row={**cfg,"cfg":cfg_id(cfg),"score":score,"n":st["n"],"win":st["win"],"avgR":st["avgR"],
         "PF":st["PF"],"totalR":st["totalR"],"maxDD":st["maxDD"],"positive_years":pos,
         "floor_year_PF":floor,"drop10_avgR":drop["avgR"],"drop10_PF":drop["PF"]}
    for y,s in yr:
        row[f"{y}_n"]=s["n"]; row[f"{y}_avgR"]=s["avgR"]; row[f"{y}_PF"]=s["PF"]; row[f"{y}_win"]=s["win"]
    return row

def stage_a(x,cache):
    rows=[]
    for orb in ORB_MINS:
      for ex in EXEC_MINS:
       for ema in EMA_LENS:
        for sm in ["or_opposite","signal_extreme","atr"]:
          cfg={"orb":orb,"exec":ex,"ema":ema,"atr_len":14,"tp_mult":1.0,
               "stop_mode":sm,"stop_mult":1.0,"entry":"next_open"}
          t=run_cfg(x,cache,cfg,DISCOVERY)
          rows.append(summarize_cfg(t,cfg,DISCOVERY))
    return pd.DataFrame(rows).sort_values(["score","PF","avgR"],ascending=False).reset_index(drop=True)

def distinct_top(stage,n=6):
    picks=[]; seen=set()
    for _,r in stage.iterrows():
        family=(int(r.orb),int(r.exec),int(r.ema),r.stop_mode)
        if family in seen: continue
        picks.append(r.to_dict()); seen.add(family)
        if len(picks)>=n: break
    return picks

def stage_b(x,cache,base_picks):
    rows=[]
    for b in base_picks:
      for al in ATR_LENS:
       for tp in TP_MULTS:
        for ent in ["close","next_open"]:
          sms=ATR_STOP_MULTS if b["stop_mode"]=="atr" else [1.0]
          for smult in sms:
            cfg={"orb":int(b["orb"]),"exec":int(b["exec"]),"ema":int(b["ema"]),"atr_len":al,
                 "tp_mult":tp,"stop_mode":b["stop_mode"],"stop_mult":smult,"entry":ent}
            t=run_cfg(x,cache,cfg,DISCOVERY)
            rows.append(summarize_cfg(t,cfg,DISCOVERY))
    return pd.DataFrame(rows).sort_values(["score","PF","avgR"],ascending=False).reset_index(drop=True)

def frozen_candidates(stageb,n=5):
    picks=[]; families=set()
    for _,r in stageb.iterrows():
        fam=(int(r.orb),int(r.exec),int(r.ema),r.stop_mode)
        if fam in families or r.n<500: continue
        picks.append(r.to_dict()); families.add(fam)
        if len(picks)>=n: break
    return picks

def to_cfg(r):
    return {"orb":int(r["orb"]),"exec":int(r["exec"]),"ema":int(r["ema"]),"atr_len":int(r["atr_len"]),
            "tp_mult":float(r["tp_mult"]),"stop_mode":r["stop_mode"],"stop_mult":float(r["stop_mult"]),
            "entry":r["entry"]}

def block_eval(x,cache,candidates,years,label):
    rows=[]
    for r in candidates:
        cfg=to_cfg(r)
        t=run_cfg(x,cache,cfg,years)
        row=summarize_cfg(t,cfg,years); row["block"]=label
        rows.append(row)
    return pd.DataFrame(rows)

def choose_after_validation(dev,val):
    m=dev[["cfg","avgR","PF","positive_years","floor_year_PF"]].merge(
        val[["cfg","avgR","PF","positive_years","floor_year_PF"]],on="cfg",suffixes=("_dev","_val"))
    m["passes_val"]=(m.avgR_val>0)&(m.PF_val>=1.02)&(m.positive_years_val>=2)
    m["worst_pf"]=m[["PF_dev","PF_val"]].min(axis=1)
    m["mean_avgR"]=m[["avgR_dev","avgR_val"]].mean(axis=1)
    return m.sort_values(["passes_val","worst_pf","mean_avgR"],ascending=[False,False,False]).reset_index(drop=True)

def rolling66(t):
    if len(t)<66: return {}
    t=t.sort_values("entry_time").copy()
    _,r=add_net(t,"ES",1)
    w=(r>0).astype(int).rolling(66).sum().dropna()
    pct=100*w/66
    return {"windows":len(pct),"median_win":float(pct.median()),"max_win":float(pct.max()),
            "p80plus_pct":float((pct>=80).mean()*100),"p8333plus_pct":float((pct>=83.3333).mean()*100),
            "count_55plus":int((w>=55).sum())}

def write_md(stagea,stageb,frozen,val,selection,confirm,latest,roll):
    def small(df,cols,n=10):
        if df is None or len(df)==0: return "No rows"
        return df[cols].head(n).round(4).to_markdown(index=False)
    wcfg=selection.iloc[0].cfg if len(selection) else "NONE"
    with open("orb_refinement_stage2_result.md","w") as f:
        f.write("# ORB Reddit Strategy Refinement — Stage 2\n\n")
        f.write("Discovery: 2016-2020 only. Validation: 2021-2023. Confirmation: 2024-2025. Latest check: 2026 YTD.\n\n")
        f.write("Prior broad ORB research already exposed some 2021-2025 behavior, so 2024-2025 are confirmation rather than pristine holdouts. 2026 YTD is the cleanest newer check.\n\n")
        f.write("## Stage A structural screen\n"+small(stagea,["cfg","n","win","avgR","PF","positive_years","floor_year_PF","drop10_avgR"],12)+"\n\n")
        f.write("## Stage B refined discovery\n"+small(stageb,["cfg","n","win","avgR","PF","positive_years","floor_year_PF","drop10_avgR"],15)+"\n\n")
        f.write("## Frozen candidates before validation\n"+small(frozen,["cfg","n","win","avgR","PF","positive_years","floor_year_PF"],10)+"\n\n")
        f.write("## 2021-2023 validation\n"+small(val,["cfg","n","win","avgR","PF","positive_years","floor_year_PF","drop10_avgR"],10)+"\n\n")
        f.write("## Predeclared selection after validation\n"+small(selection,["cfg","passes_val","PF_dev","PF_val","worst_pf","avgR_dev","avgR_val","mean_avgR"],10)+"\n\n")
        f.write("Selected configuration before opening 2024+: "+str(wcfg)+"\n\n")
        f.write("## 2024-2025 confirmation\n"+small(confirm,["cfg","n","win","avgR","PF","positive_years","floor_year_PF"],10)+"\n\n")
        f.write("## 2026 YTD latest check\n"+small(latest,["cfg","n","win","avgR","PF","positive_years","floor_year_PF"],10)+"\n\n")
        f.write("## 66-trade window diagnostic\n"+str(roll)+"\n")

def main():
    print("=== ORB REDDIT REFINEMENT STAGE 2 ===")
    print("Unknowns: ORB 15/30; execution 5/15; EMA 9/20/50; ATR 7/10/14/21; TP 0.5-1.5 ATR; stop family; close vs next-open.")
    x=load_all()
    cache={m:resample_exec(x,m) for m in EXEC_MINS}
    print("DATA",x.index.min(),x.index.max(),"sessions",x.session.nunique())
    a=stage_a(x,cache); a.to_csv("orb_refinement_stageA.csv",index=False)
    print("\nSTAGE A TOP\n",a.head(12)[["cfg","n","win","avgR","PF","positive_years","floor_year_PF","drop10_avgR"]].round(4).to_string(index=False))
    bases=distinct_top(a,6)
    b=stage_b(x,cache,bases); b.to_csv("orb_refinement_stageB.csv",index=False)
    print("\nSTAGE B TOP\n",b.head(20)[["cfg","n","win","avgR","PF","positive_years","floor_year_PF","drop10_avgR"]].round(4).to_string(index=False))
    cand=frozen_candidates(b,5)
    frozen=pd.DataFrame(cand); frozen.to_csv("orb_refinement_frozen_candidates.csv",index=False)
    print("\nFROZEN BEFORE 2021+\n",frozen[["cfg","n","win","avgR","PF","positive_years","floor_year_PF"]].round(4).to_string(index=False))
    val=block_eval(x,cache,cand,VALIDATION,"2021-2023"); val.to_csv("orb_refinement_validation_2021_2023.csv",index=False)
    print("\nVALIDATION\n",val[["cfg","n","win","avgR","PF","positive_years","floor_year_PF","drop10_avgR"]].round(4).to_string(index=False))
    sel=choose_after_validation(frozen,val); sel.to_csv("orb_refinement_selection.csv",index=False)
    print("\nSELECTION\n",sel.round(4).to_string(index=False))
    winner=sel.iloc[0].cfg
    winner_row=frozen[frozen.cfg==winner].iloc[0].to_dict()
    winner_cfg=to_cfg(winner_row)
    conf=block_eval(x,cache,[winner_row],CONFIRM,"2024-2025"); conf.to_csv("orb_refinement_confirmation_2024_2025.csv",index=False)
    lat=block_eval(x,cache,[winner_row],LATEST,"2026YTD"); lat.to_csv("orb_refinement_latest_2026.csv",index=False)
    print("\nWINNER FROZEN",winner)
    print("\n2024-2025\n",conf[["cfg","n","win","avgR","PF","positive_years","floor_year_PF"]].round(4).to_string(index=False))
    print("\n2026 YTD\n",lat[["cfg","n","win","avgR","PF","positive_years","floor_year_PF"]].round(4).to_string(index=False))
    all_t=run_cfg(x,cache,winner_cfg,ALL_YEARS)
    all_t.to_csv("orb_refinement_winner_all_trades.csv",index=False)
    roll=rolling66(all_t); print("\nROLLING66",roll)
    write_md(a,b,frozen,val,sel,conf,lat,roll)

if __name__=="__main__":
    main()
