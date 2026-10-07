import io, requests, numpy as np, pandas as pd

BASE="https://raw.githubusercontent.com/worldtradingchampion-source/btcdata/main/ES_1min_{}.csv"
YEARS=[2021,2022,2023,2024,2025]
NY="America/New_York"; TICK=0.25

def load():
    parts=[]
    for y in YEARS:
        r=requests.get(BASE.format(y),timeout=180); r.raise_for_status()
        d=pd.read_csv(io.StringIO(r.text))
        d["datetime_et"]=pd.to_datetime(d["datetime_et"],utc=True).dt.tz_convert(NY)
        if "rth" in d.columns:
            d=d[d["rth"].astype(str).str.lower().eq("true")]
        for c in ["open","high","low","close","volume"]: d[c]=pd.to_numeric(d[c],errors="coerce")
        d=d.dropna(subset=["datetime_et","open","high","low","close"]).copy()
        d["session"]=d.datetime_et.dt.date
        if "symbol" in d.columns:
            n=d.groupby("session").symbol.nunique()
            d=d[~d.session.isin(set(n[n>1].index))]
        d=(d.sort_values(["datetime_et","volume"],ascending=[True,False])
             .drop_duplicates("datetime_et",keep="first").sort_values("datetime_et"))
        parts.append(d)
    x=pd.concat(parts,ignore_index=True).sort_values("datetime_et").set_index("datetime_et")
    x["session"]=x.index.date
    return x

def bars(d,mins=5):
    r=d[["open","high","low","close","volume"]].resample(
        f"{mins}min",origin="start_day",offset="30min",label="left",closed="left"
    ).agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
    r["end"]=r.index+pd.Timedelta(minutes=mins)
    return r

def sim(d, entry_time, entry, direction, stop, target):
    risk=(entry-stop) if direction==1 else (stop-entry)
    if risk<TICK: return None
    z=d[d.index>=entry_time]
    for ts,r in z.iterrows():
        hs=(r.low<=stop) if direction==1 else (r.high>=stop)
        ht=(r.high>=target) if direction==1 else (r.low<=target)
        if hs and ht: return -1.0,ts,"ambiguous_stop_first"
        if hs: return -1.0,ts,"stop"
        if ht: return (target-entry)/risk if direction==1 else (entry-target)/risk,ts,"target"
    px=float(z.iloc[-1].close); ts=z.index[-1]
    rr=(px-entry)/risk if direction==1 else (entry-px)/risk
    return rr,ts,"eod"

def test_day(d, sess, orb_mins, target_r, ema_filter=False):
    start=pd.Timestamp(f"{sess} 09:30",tz=NY)
    end=start+pd.Timedelta(minutes=orb_mins)
    ox=d[(d.index>=start)&(d.index<end)]
    if len(ox)<max(10,orb_mins-3): return None
    orh,orl=float(ox.high.max()),float(ox.low.min())
    b=bars(d,5)
    b=b[b.index>=end]
    if ema_filter:
        b["ema9"]=b.close.ewm(span=9,adjust=False).mean()
    for i,(ts,r) in enumerate(b.iterrows()):
        if ts.hour*60+ts.minute>=12*60: break
        direction=0
        if float(r.close)>orh: direction=1
        elif float(r.close)<orl: direction=-1
        if direction==0: continue
        if ema_filter:
            if direction==1 and not (float(r.close)>float(r.ema9)): continue
            if direction==-1 and not (float(r.close)<float(r.ema9)): continue
        if i+1>=len(b): return None
        et=b.index[i+1]
        if et.hour*60+et.minute>=12*60: return None
        entry=float(b.iloc[i+1].open)
        stop=orl if direction==1 else orh
        risk=(entry-stop) if direction==1 else (stop-entry)
        if risk<TICK: continue
        target=entry+direction*target_r*risk
        s=sim(d,et,entry,direction,stop,target)
        if not s: return None
        rr,xt,why=s
        return {"session":str(sess),"year":sess.year,"orb":orb_mins,"targetR":target_r,
                "ema9":ema_filter,"direction":"L" if direction==1 else "S",
                "entry_time":str(et),"risk_pts":risk,"R":rr,"exit_reason":why}
    return None

def netr(df,product="ES",slip_ticks=1):
    point=50.0 if product=="ES" else 5.0
    comm=5.0 if product=="ES" else 1.50
    cost_pts=slip_ticks*TICK+comm/point
    return df.R-cost_pts/df.risk_pts

def stats(v):
    v=pd.Series(v,dtype=float).dropna()
    wins=v[v>0]; losses=v[v<=0]
    pf=wins.sum()/abs(losses.sum()) if len(losses) and abs(losses.sum())>0 else np.inf
    eq=v.cumsum(); dd=eq-eq.cummax()
    return dict(n=len(v),win=100*(v>0).mean() if len(v) else np.nan,
                avgR=v.mean() if len(v) else np.nan,PF=pf,totalR=v.sum(),
                maxDD=dd.min() if len(v) else np.nan)

def main():
    x=load(); trades=[]
    for sess,d in x.groupby("session",sort=True):
        sess=pd.Timestamp(sess).date()
        for orb in [15,30]:
            for tr in [1.0,1.5,2.0]:
                for ema in [False,True]:
                    z=test_day(d,sess,orb,tr,ema)
                    if z: trades.append(z)
    t=pd.DataFrame(trades); t.to_csv("orb_15v30_trades.csv",index=False)
    rows=[]
    for (orb,tr,ema),g in t.groupby(["orb","targetR","ema9"]):
        es=stats(netr(g,"ES",1)); mes=stats(netr(g,"MES",1))
        row={"ORB_min":orb,"target_R":tr,"EMA9_filter":ema,
             **{f"ES_{k}":v for k,v in es.items()},
             **{f"MES_{k}":v for k,v in mes.items()}}
        for y in YEARS:
            gy=g[g.year==y]; sy=stats(netr(gy,"ES",1))
            row[f"{y}_n"]=sy["n"]; row[f"{y}_avgR"]=sy["avgR"]; row[f"{y}_PF"]=sy["PF"]
        rows.append(row)
    out=pd.DataFrame(rows).sort_values(["EMA9_filter","target_R","ORB_min"])
    out.to_csv("orb_15v30_summary.csv",index=False)
    print("DATA",x.index.min(),x.index.max(),"sessions",x.session.nunique())
    print(out.round(4).to_string(index=False))
    print("\nPAIRWISE 30m - 15m (ES net avgR / PF / win)")
    for ema in [False,True]:
      for tr in [1.0,1.5,2.0]:
        a=out[(out.ORB_min==15)&(out.target_R==tr)&(out.EMA9_filter==ema)].iloc[0]
        b=out[(out.ORB_min==30)&(out.target_R==tr)&(out.EMA9_filter==ema)].iloc[0]
        print("ema9",ema,"target",tr,
              "d_avgR",round(b.ES_avgR-a.ES_avgR,4),
              "d_PF",round(b.ES_PF-a.ES_PF,4),
              "d_win_pp",round(b.ES_win-a.ES_win,2),
              "n15",int(a.ES_n),"n30",int(b.ES_n))

if __name__=="__main__": main()
