import io
import requests
import numpy as np
import pandas as pd

BASE = "https://raw.githubusercontent.com/worldtradingchampion-source/btcdata/main/ES_1min_{}.csv"
YEARS = [2021, 2022, 2023]
NY = "America/New_York"
TICK = 0.25

NAMES = {
    "R2S1": "RTH gap-fill confirmed",
    "R2S2": "Overnight range break-retest",
    "R2S3": "Initial-balance accepted-break",
    "R2S4": "Prior-day level break-retest",
    "R2S5": "ADX/VWAP/EMA20 trend pullback",
    "R2S6": "EMA9/19 retest scalp",
}

def load_all():
    full_parts=[]
    rth_parts=[]
    meta=[]
    for y in YEARS:
        r=requests.get(BASE.format(y),timeout=180); r.raise_for_status()
        d=pd.read_csv(io.StringIO(r.text))
        d["datetime_et"]=pd.to_datetime(d["datetime_et"],utc=True).dt.tz_convert(NY)
        for c in ["open","high","low","close","volume"]:
            d[c]=pd.to_numeric(d[c],errors="coerce")
        d=d.dropna(subset=["datetime_et","open","high","low","close","volume","symbol"]).copy()
        d["rth_bool"]=d["rth"].astype(str).str.lower().eq("true")
        d=d.sort_values(["datetime_et","symbol"])
        rth=d[d.rth_bool].copy()
        rth["session"]=rth.datetime_et.dt.date
        ns=rth.groupby("session").symbol.nunique()
        roll=set(ns[ns>1].index)
        if roll:
            print("excluding roll-switch sessions",y,len(roll),sorted(roll))
        rth=rth[~rth.session.isin(roll)].copy()
        before=len(rth)
        rth=(rth.sort_values(["datetime_et","volume"],ascending=[True,False])
                .drop_duplicates("datetime_et",keep="first").sort_values("datetime_et"))
        print("loaded",y,"RTH rows",len(rth),"sessions",rth.session.nunique(),"duplicates_resolved",before-len(rth))
        sm=rth.groupby("session").symbol.first()
        for sess,sym in sm.items():
            meta.append({"session":sess,"symbol":sym,"year":y})
        rth_parts.append(rth)
        full_parts.append(d)
    full=pd.concat(full_parts,ignore_index=True).sort_values(["datetime_et","volume"],ascending=[True,False])
    full=full.drop_duplicates(["datetime_et","symbol"],keep="first").sort_values("datetime_et")
    rth=pd.concat(rth_parts,ignore_index=True).sort_values("datetime_et")
    rth=rth.drop_duplicates("datetime_et",keep="first").set_index("datetime_et")
    rth["session"]=rth.index.date
    meta=pd.DataFrame(meta).sort_values("session").reset_index(drop=True)
    return full, rth, meta

def rth_resample(d, minutes):
    r=d[["open","high","low","close","volume"]].resample(
        f"{minutes}min",origin="start_day",offset="30min",label="left",closed="left"
    ).agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
    r["end"]=r.index+pd.Timedelta(minutes=minutes)
    return r

def eth_resample(z, minutes):
    r=z[["open","high","low","close","volume"]].resample(
        f"{minutes}min",origin="start_day",label="left",closed="left"
    ).agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
    r["end"]=r.index+pd.Timedelta(minutes=minutes)
    return r

def adx(frame, n=14):
    x=frame.copy()
    up=x.high.diff()
    down=-x.low.diff()
    plus_dm=pd.Series(np.where((up>down)&(up>0),up,0.0),index=x.index)
    minus_dm=pd.Series(np.where((down>up)&(down>0),down,0.0),index=x.index)
    prev=x.close.shift(1)
    tr=pd.concat([(x.high-x.low).abs(),(x.high-prev).abs(),(x.low-prev).abs()],axis=1).max(axis=1)
    atr=tr.ewm(alpha=1/n,adjust=False,min_periods=n).mean()
    p=plus_dm.ewm(alpha=1/n,adjust=False,min_periods=n).mean()
    m=minus_dm.ewm(alpha=1/n,adjust=False,min_periods=n).mean()
    pdi=100*p/atr
    mdi=100*m/atr
    dx=100*(pdi-mdi).abs()/(pdi+mdi)
    return dx.ewm(alpha=1/n,adjust=False,min_periods=n).mean()

def session_vwap(d):
    tp=(d.high+d.low+d.close)/3.0
    cv=d.volume.cumsum()
    return (tp*d.volume).cumsum()/cv

def simulate(d, entry_time, entry, direction, stop, target):
    risk=(entry-stop) if direction==1 else (stop-entry)
    if risk < TICK-1e-12:
        return None
    z=d[d.index>=entry_time]
    if len(z)==0: return None
    mfe=0.0; mae=0.0
    for ts,r in z.iterrows():
        if direction==1:
            mfe=max(mfe,(r.high-entry)/risk); mae=min(mae,(r.low-entry)/risk)
            hs=r.low<=stop; ht=r.high>=target
        else:
            mfe=max(mfe,(entry-r.low)/risk); mae=min(mae,(entry-r.high)/risk)
            hs=r.high>=stop; ht=r.low<=target
        if hs and ht: return -1.0,ts,"ambiguous_stop_first",mfe,mae
        if hs: return -1.0,ts,"stop",mfe,mae
        if ht:
            rr=((target-entry)/risk) if direction==1 else ((entry-target)/risk)
            return rr,ts,"target",mfe,mae
    ts=z.index[-1]; px=float(z.iloc[-1].close)
    rr=((px-entry)/risk) if direction==1 else ((entry-px)/risk)
    return rr,ts,"eod",mfe,mae

def add(out,sid,sess,dirn,signal_time,entry_time,entry,stop,target,sim,note=""):
    rr,exit_time,why,mfe,mae=sim
    out.append({
        "strategy":sid,"strategy_name":NAMES[sid],"session":pd.Timestamp(sess),
        "year":pd.Timestamp(sess).year,"direction":"long" if dirn==1 else "short",
        "signal_time":signal_time,"entry_time":entry_time,"exit_time":exit_time,
        "entry":float(entry),"stop":float(stop),"target":float(target),
        "risk_pts":abs(float(entry)-float(stop)),"R":float(rr),
        "MFE_R":float(mfe),"MAE_R":float(mae),"exit_reason":why,"note":note
    })

def get_prev(meta, idx):
    if idx<=0: return None
    cur=meta.iloc[idx]; prev=meta.iloc[idx-1]
    if cur.symbol!=prev.symbol: return None
    return prev

def full_for_session(full,sess,symbol):
    day=pd.Timestamp(sess,tz=NY)
    start=day-pd.Timedelta(days=1)+pd.Timedelta(hours=18)
    end=day+pd.Timedelta(hours=16)
    z=full[(full.symbol==symbol)&(full.datetime_et>=start)&(full.datetime_et<end)].copy()
    return z.sort_values("datetime_et").set_index("datetime_et")

def s1_gapfill(d,sess,prev_d):
    out=[]
    if prev_d is None or len(prev_d)==0 or len(d)==0: return out
    prev_close=float(prev_d.iloc[-1].close)
    day_open=float(d.iloc[0].open)
    gap=day_open-prev_close
    if abs(gap)/prev_close < 0.001: return out
    b5=rth_resample(d,5)
    conf=None
    for ts,b in b5.iterrows():
        end=b["end"]
        if end>pd.Timestamp(f"{sess} 10:00",tz=NY): break
        if gap>0 and float(b.close)<day_open:
            conf=(ts,end,b,-1); break
        if gap<0 and float(b.close)>day_open:
            conf=(ts,end,b,1); break
    if conf is None: return out
    ts,end,b,dirn=conf
    er=d[d.index>=end]
    if len(er)==0:return out
    entry=float(er.iloc[0].open)
    upto=d[(d.index>=pd.Timestamp(f"{sess} 09:30",tz=NY))&(d.index<end)]
    if len(upto)==0:return out
    stop=float(upto.high.max())+TICK if dirn==-1 else float(upto.low.min())-TICK
    target=prev_close
    if (dirn==1 and target<=entry) or (dirn==-1 and target>=entry): return out
    sim=simulate(d,end,entry,dirn,stop,target)
    if sim: add(out,"R2S1",sess,dirn,end,end,entry,stop,target,sim,f"gap={gap:.2f}")
    return out

def s2_overnight(d,eth,sess):
    out=[]
    day=pd.Timestamp(sess,tz=NY)
    on=eth[(eth.index>=day-pd.Timedelta(days=1)+pd.Timedelta(hours=18))&(eth.index<day+pd.Timedelta(hours=9,minutes=30))]
    if len(on)<500:return out
    onh=float(on.high.max()); onl=float(on.low.min())
    b5=rth_resample(d,5)
    br=None
    for ts,b in b5.iterrows():
        end=b["end"]
        if end>pd.Timestamp(f"{sess} 12:00",tz=NY):break
        if float(b.close)>onh: br=(1,ts,end,b,onh);break
        if float(b.close)<onl: br=(-1,ts,end,b,onl);break
    if br is None:return out
    dirn,bts,bend,bb,boundary=br
    stop=float(bb.low)-TICK if dirn==1 else float(bb.high)+TICK
    risk=(boundary-stop) if dirn==1 else (stop-boundary)
    if risk<TICK:return out
    after=b5[b5.index>=bend]
    for ts,b in after.iterrows():
        if ts>=pd.Timestamp(f"{sess} 12:00",tz=NY):break
        end=b["end"]
        mins=d[(d.index>=ts)&(d.index<end)]
        touch=mins[(mins.low<=boundary)&(mins.high>=boundary)]
        if len(touch):
            et=touch.index[0]; target=boundary+dirn*2*risk
            sim=simulate(d,et,boundary,dirn,stop,target)
            if sim:add(out,"R2S2",sess,dirn,bend,et,boundary,stop,target,sim)
            return out
        invalid=(dirn==1 and float(b.close)<onl) or (dirn==-1 and float(b.close)>onh)
        if invalid:return out
    return out

def s3_ib(d,sess):
    out=[]
    st=pd.Timestamp(f"{sess} 09:30",tz=NY); cut=pd.Timestamp(f"{sess} 10:30",tz=NY)
    ib=d[(d.index>=st)&(d.index<cut)]
    if len(ib)<50:return out
    ibh=float(ib.high.max()); ibl=float(ib.low.min())
    b5=rth_resample(d,5)
    for ts,b in b5.iterrows():
        end=b["end"]
        if end<=cut: continue
        if end>pd.Timestamp(f"{sess} 14:00",tz=NY): break
        dirn=1 if float(b.close)>ibh else (-1 if float(b.close)<ibl else 0)
        if dirn==0:continue
        er=d[d.index>=end]
        if len(er)==0:return out
        entry=float(er.iloc[0].open)
        stop=ibh-TICK if dirn==1 else ibl+TICK
        risk=(entry-stop) if dirn==1 else (stop-entry)
        if risk<TICK:return out
        target=entry+dirn*1.5*risk
        sim=simulate(d,end,entry,dirn,stop,target)
        if sim:add(out,"R2S3",sess,dirn,end,end,entry,stop,target,sim)
        return out
    return out

def s4_pdh(d,sess,prev_d):
    out=[]
    if prev_d is None or len(prev_d)==0:return out
    pdh=float(prev_d.high.max()); pdl=float(prev_d.low.min())
    b5=rth_resample(d,5)
    br=None
    for ts,b in b5.iterrows():
        end=b["end"]
        if end>pd.Timestamp(f"{sess} 14:00",tz=NY):break
        if float(b.close)>pdh:br=(1,ts,end,b,pdh);break
        if float(b.close)<pdl:br=(-1,ts,end,b,pdl);break
    if br is None:return out
    dirn,bts,bend,bb,boundary=br
    stop=float(bb.low)-TICK if dirn==1 else float(bb.high)+TICK
    risk=(boundary-stop) if dirn==1 else (stop-boundary)
    if risk<TICK:return out
    for ts,b in b5[b5.index>=bend].iterrows():
        if ts>=pd.Timestamp(f"{sess} 14:00",tz=NY):break
        end=b["end"]
        mins=d[(d.index>=ts)&(d.index<end)]
        touch=mins[(mins.low<=boundary)&(mins.high>=boundary)]
        if len(touch):
            et=touch.index[0];target=boundary+dirn*2*risk
            sim=simulate(d,et,boundary,dirn,stop,target)
            if sim:add(out,"R2S4",sess,dirn,bend,et,boundary,stop,target,sim)
            return out
    return out

def s5_trend(d,eth,sess):
    out=[]
    if len(d)==0 or len(eth)==0:return out
    e5=eth_resample(eth,5); e15=eth_resample(eth,15)
    e5["ema20"]=e5.close.ewm(span=20,adjust=False).mean()
    e5["adx5"]=adx(e5,14); e5["adx5_prev"]=e5.adx5.shift(1)
    e15["adx15"]=adx(e15,14); e15["adx15_prev"]=e15.adx15.shift(1)
    dx=d.copy(); dx["vwap"]=session_vwap(dx)
    b5=rth_resample(dx,5)
    b5["ema20"]=np.nan;b5["adx5"]=np.nan;b5["adx5_prev"]=np.nan;b5["vwap"]=np.nan
    for ts in b5.index:
        if ts in e5.index:
            for c in ["ema20","adx5","adx5_prev"]:b5.loc[ts,c]=e5.loc[ts,c]
        end=b5.loc[ts,"end"]
        vv=dx[dx.index<end]
        if len(vv):b5.loc[ts,"vwap"]=float(vv.iloc[-1].vwap)
    busy=None; taken=0
    for i,(ts,b) in enumerate(b5.iterrows()):
        end=b["end"]
        if end<pd.Timestamp(f"{sess} 10:30",tz=NY):continue
        if end>pd.Timestamp(f"{sess} 15:00",tz=NY):break
        if taken>=2:break
        if busy is not None and ts<=busy:continue
        cands=e15[e15.end<=end]
        if len(cands)==0:continue
        a15=cands.iloc[-1]
        vals=[a15.adx15,a15.adx15_prev,b.adx5,b.adx5_prev,b.ema20,b.vwap]
        if any(pd.isna(v) for v in vals):continue
        if not (25<=a15.adx15<=35 and a15.adx15>a15.adx15_prev and b.adx5>b.adx5_prev):continue
        dirn=0
        if float(b.close)>b.vwap and b.ema20>b.vwap and float(b.low)<=b.ema20 and float(b.close)>b.ema20:
            dirn=1
        elif float(b.close)<b.vwap and b.ema20<b.vwap and float(b.high)>=b.ema20 and float(b.close)<b.ema20:
            dirn=-1
        if dirn==0:continue
        er=d[d.index>=end]
        if len(er)==0:continue
        entry=float(er.iloc[0].open)
        stop=float(b.low)-TICK if dirn==1 else float(b.high)+TICK
        risk=(entry-stop) if dirn==1 else (stop-entry)
        if risk<TICK:continue
        target=entry+dirn*2*risk
        sim=simulate(d,end,entry,dirn,stop,target)
        if sim:
            add(out,"R2S5",sess,dirn,end,end,entry,stop,target,sim)
            busy=sim[1];taken+=1
    return out

def s6_ema(d,sess):
    out=[]
    x=d.copy()
    x["ema9"]=x.close.ewm(span=9,adjust=False).mean()
    x["ema19"]=x.close.ewm(span=19,adjust=False).mean()
    busy=None;taken=0
    for i in range(2,len(x)-1):
        ts=x.index[i]; nxt=x.index[i+1]
        if ts<pd.Timestamp(f"{sess} 09:45",tz=NY):continue
        if nxt>=pd.Timestamp(f"{sess} 12:00",tz=NY):break
        if taken>=3:break
        if busy is not None and nxt<=busy:continue
        cur=x.iloc[i]; last3=x.iloc[i-2:i+1]
        dirn=0
        if cur.ema9>cur.ema19 and np.all(last3.close>last3.ema9) and np.all(last3.close>last3.ema19):
            dirn=1
        elif cur.ema9<cur.ema19 and np.all(last3.close<last3.ema9) and np.all(last3.close<last3.ema19):
            dirn=-1
        if dirn==0:continue
        entry=float(cur.ema9)
        stop=float(cur.ema19)-TICK if dirn==1 else float(cur.ema19)+TICK
        risk=(entry-stop) if dirn==1 else (stop-entry)
        if risk<TICK or risk>8.0:continue
        nr=x.iloc[i+1]
        touched=float(nr.low)<=entry<=float(nr.high)
        if not touched:continue
        target=entry+dirn*2*risk
        sim=simulate(d,nxt,entry,dirn,stop,target)
        if sim:
            add(out,"R2S6",sess,dirn,ts,nxt,entry,stop,target,sim)
            busy=sim[1];taken+=1
    return out

def net_r(g,product="ES",slip_ticks=1):
    point=50.0 if product=="ES" else 5.0
    comm=5.0 if product=="ES" else 1.50
    cost_pts=comm/point+slip_ticks*TICK
    return g.R.to_numpy(dtype=float)-cost_pts/g.risk_pts.to_numpy(dtype=float)

def stats(v):
    v=pd.Series(v,dtype=float).dropna()
    if len(v)==0:return {"n":0,"win":np.nan,"avgR":np.nan,"PF":np.nan,"totalR":np.nan,"DD":np.nan}
    w=v[v>0];l=v[v<=0]
    pf=w.sum()/abs(l.sum()) if len(l) and abs(l.sum())>0 else np.inf
    eq=v.cumsum();dd=eq-eq.cummax()
    return {"n":len(v),"win":100*(v>0).mean(),"avgR":v.mean(),"PF":pf,"totalR":v.sum(),"DD":dd.min()}

def main():
    print("=== STRATEGY TOURNAMENT ROUND 2 ===")
    print("Frozen development only: 2021-2023. 2024+ are not loaded.")
    full,rth,meta=load_all()
    print("DEV RTH rows",len(rth),"sessions",rth.session.nunique())
    trades=[]
    for idx,row in meta.iterrows():
        sess=row.session;sym=row.symbol
        d=rth[rth.session==sess].copy()
        if len(d)==0:continue
        eth=full_for_session(full,sess,sym)
        prev=get_prev(meta,idx)
        prev_d=None
        if prev is not None:
            prev_d=rth[rth.session==prev.session].copy()
        trades.extend(s1_gapfill(d,sess,prev_d))
        trades.extend(s2_overnight(d,eth,sess))
        trades.extend(s3_ib(d,sess))
        trades.extend(s4_pdh(d,sess,prev_d))
        trades.extend(s5_trend(d,eth,sess))
        trades.extend(s6_ema(d,sess))
    t=pd.DataFrame(trades)
    if len(t)==0:
        print("NO TRADES");return
    t=t.sort_values(["entry_time","strategy"]).reset_index(drop=True)
    t.to_csv("strategy_tournament_round2_trades.csv",index=False)
    rows=[]
    for sid in NAMES:
        g=t[t.strategy==sid].copy()
        es1=stats(net_r(g,"ES",1))
        pos_years=0;floor_pf=np.inf
        for y in YEARS:
            gy=g[g.year==y]
            sy=stats(net_r(gy,"ES",1))
            if sy["totalR"]>0:pos_years+=1
            if sy["n"]>0 and np.isfinite(sy["PF"]):floor_pf=min(floor_pf,sy["PF"])
        net=pd.Series(net_r(g,"ES",1),index=g.index) if len(g) else pd.Series(dtype=float)
        if len(net):
            ranked=net.sort_values(ascending=False)
            z=net.drop(index=ranked.index[:min(5,len(ranked))])
            drop5=stats(z)
            gross=net[net>0].sum()
            share=float(net.max()/gross) if gross>0 else np.nan
        else:
            drop5=stats([]);share=np.nan
        es4=stats(net_r(g,"ES",4));mes1=stats(net_r(g,"MES",1))
        nreq=75 if sid in ["R2S1","R2S2","R2S3","R2S4"] else 100
        survivor=bool(
            len(g)>=nreq and es1["avgR"]>0 and es1["PF"]>=1.10 and
            pos_years>=2 and (drop5["avgR"]>0 or drop5["PF"]>=1.05) and
            (np.isnan(share) or share<=0.20)
        )
        rows.append({
            "strategy":sid,"n":len(g),"net_win":es1["win"],"net_avgR":es1["avgR"],
            "net_PF":es1["PF"],"net_totalR":es1["totalR"],"net_DD":es1["DD"],
            "positive_years":pos_years,"floor_year_PF":floor_pf if np.isfinite(floor_pf) else np.nan,
            "drop5_avgR":drop5["avgR"],"drop5_PF":drop5["PF"],"max_winner_gross_share":share,
            "ES4_avgR":es4["avgR"],"MES1_avgR":mes1["avgR"],"MES1_PF":mes1["PF"],
            "survivor":survivor
        })
    lb=pd.DataFrame(rows).sort_values(["survivor","net_avgR","net_PF"],ascending=[False,False,False])
    lb.to_csv("strategy_tournament_round2_leaderboard.csv",index=False)
    print("\nLEADERBOARD -- ES $5 RT + 1 TICK TOTAL ADVERSE SLIPPAGE")
    print(lb.round(4).to_string(index=False))
    print("\nYEAR BY YEAR -- ES 1 TICK")
    yr=[]
    for sid in NAMES:
        row={"strategy":sid}
        g=t[t.strategy==sid]
        for y in YEARS:
            s=stats(net_r(g[g.year==y],"ES",1))
            for k in ["n","avgR","PF","totalR"]:row[f"{y}_{k}"]=s[k]
        yr.append(row)
    print(pd.DataFrame(yr).round(4).to_string(index=False))
    print("\nCOST SENSITIVITY")
    cr=[]
    for sid in NAMES:
        g=t[t.strategy==sid]
        row={"strategy":sid}
        for p in ["ES","MES"]:
            for slip in [0,1,2,4]:
                s=stats(net_r(g,p,slip))
                row[f"{p}{slip}_avgR"]=s["avgR"];row[f"{p}{slip}_PF"]=s["PF"]
        cr.append(row)
    print(pd.DataFrame(cr).round(4).to_string(index=False))
    print("\nROUND2_SURVIVORS",lb[lb.survivor].strategy.tolist())
    print("INTERPRETATION: freeze survivors before any 2024 validation; do not tune failed candidates.")

if __name__=="__main__":
    main()
