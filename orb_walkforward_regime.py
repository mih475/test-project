import numpy as np, pandas as pd
import orb_refinement_stage2 as s2
import orb_filter_diagnostics as fd

YEARS=list(range(2016,2027))
TEST_YEARS=list(range(2019,2027))
BASE_CFG={"orb":15,"exec":15,"ema":50,"atr_len":7,"tp_mult":1.5,
          "stop_mode":"or_opposite","stop_mult":1.0,"entry":"next_open"}
VARIANTS=["BASE","LONG_ONLY","ADX20_DMI","MODERATE_OR","LONG_ADX20_DMI","LONG_MODERATE_OR"]

def apply_variant(t,name,train=None):
    q=t.copy()
    if name=="BASE":
        return q
    if name=="LONG_ONLY":
        return q[q.direction=="L"].copy()
    if name=="ADX20_DMI":
        return q[q.dmi_aligned & (q.adx14>=20)].copy()
    if name=="LONG_ADX20_DMI":
        return q[(q.direction=="L") & q.dmi_aligned & (q.adx14>=20)].copy()
    if name in ("MODERATE_OR","LONG_MODERATE_OR"):
        if train is None or len(train)==0:
            return q.iloc[0:0].copy()
        vals=train.or_width_atr20.dropna()
        if len(vals)<100:
            return q.iloc[0:0].copy()
        lo=float(vals.quantile(.20)); hi=float(vals.quantile(.80))
        m=(q.or_width_atr20>=lo)&(q.or_width_atr20<=hi)
        if name=="LONG_MODERATE_OR":
            m=m&(q.direction=="L")
        out=q[m].copy()
        out["wf_or_lo"]=lo; out["wf_or_hi"]=hi
        return out
    raise ValueError(name)

def net_r(t,product="ES",slip=1):
    if len(t)==0: return pd.Series(dtype=float)
    point=50.0 if product=="ES" else 5.0
    comm=5.0 if product=="ES" else 1.50
    cost_pts=slip*s2.TICK+comm/point
    return t.raw_pnl_pts.astype(float)/t.risk_pts.astype(float)-cost_pts/t.risk_pts.astype(float)

def stat(t,product="ES",slip=1):
    r=net_r(t,product,slip)
    if len(r)==0:
        return {"n":0,"win":np.nan,"avgR":np.nan,"PF":np.nan,"totalR":0.0,"maxDD":np.nan,"avgPts":np.nan}
    w=r[r>0]; l=r[r<=0]
    pf=w.sum()/abs(l.sum()) if len(l) and abs(l.sum())>0 else np.inf
    eq=r.cumsum(); dd=eq-eq.cummax()
    pts=t.raw_pnl_pts.astype(float)-(slip*s2.TICK+(5.0 if product=="ES" else 1.5)/(50.0 if product=="ES" else 5.0))
    return {"n":len(r),"win":100*(r>0).mean(),"avgR":r.mean(),"PF":pf,"totalR":r.sum(),
            "maxDD":dd.min(),"avgPts":pts.mean()}

def annual_fixed(t):
    rows=[]
    for y in YEARS:
        train=t[t.year<y].copy()
        test=t[t.year==y].copy()
        for v in VARIANTS:
            q=apply_variant(test,v,train)
            s=stat(q)
            rows.append({"year":y,"variant":v,**s})
    return pd.DataFrame(rows)

def trailing_selector(t):
    # Start in 2019; each decision uses trailing 3 completed calendar years only.
    rows=[]; selected_trades=[]
    for y in TEST_YEARS:
        train=t[(t.year>=y-3)&(t.year<=y-1)].copy()
        test=t[t.year==y].copy()
        scores=[]
        for v in VARIANTS:
            tr=apply_variant(train,v,train)
            s=stat(tr)
            # minimum history gate; avoid selecting a tiny sample
            eligible=s["n"]>=120 and np.isfinite(s["PF"]) and np.isfinite(s["avgR"])
            # rank by conservative blend: worst of PF-edge and expectancy, with a small sample penalty
            score=(min(s["PF"],1.5)-1.0)*0.40 + s["avgR"] + min(s["n"],500)/50000.0 if eligible else -999
            scores.append({"year":y,"variant":v,"train_n":s["n"],"train_win":s["win"],
                           "train_avgR":s["avgR"],"train_PF":s["PF"],"score":score,"eligible":eligible})
        sc=pd.DataFrame(scores).sort_values(["score","train_PF","train_avgR"],ascending=False).reset_index(drop=True)
        pick=sc.iloc[0]["variant"]
        chosen=apply_variant(test,pick,train).copy()
        chosen["selected_variant"]=pick
        selected_trades.append(chosen)
        os=stat(chosen)
        row=sc.iloc[0].to_dict()
        row.update({f"test_{k}":v for k,v in os.items()})
        rows.append(row)
    return pd.DataFrame(rows),pd.concat(selected_trades,ignore_index=True) if selected_trades else pd.DataFrame()

def friction_table(t):
    rows=[]
    for product in ["ES","MES"]:
        for slip in [0,1,2,4]:
            s=stat(t,product,slip)
            rows.append({"product":product,"slip_ticks":slip,**s})
    return pd.DataFrame(rows)

def max_losing_streak(r):
    m=0;c=0
    for x in r:
        if x<=0:
            c+=1; m=max(m,c)
        else:
            c=0
    return m

def monte_carlo(t,n=10000,seed=42):
    r=net_r(t,"MES",1).dropna().values
    if len(r)==0: return pd.DataFrame()
    rng=np.random.default_rng(seed)
    rows=[]
    # bootstrap with replacement preserves empirical win/loss magnitudes and estimates sequence risk
    for i in range(n):
        s=rng.choice(r,size=len(r),replace=True)
        eq=np.cumsum(s)
        dd=eq-np.maximum.accumulate(np.r_[0,eq])[:-1]
        rows.append({"totalR":s.sum(),"maxDD_R":dd.min(),"max_losing_streak":max_losing_streak(s)})
    return pd.DataFrame(rows)

def mc_summary(mc):
    if len(mc)==0: return pd.DataFrame()
    return pd.DataFrame([
        {"metric":"totalR","p05":mc.totalR.quantile(.05),"p50":mc.totalR.quantile(.50),"p95":mc.totalR.quantile(.95)},
        {"metric":"maxDD_R","p05":mc.maxDD_R.quantile(.05),"p50":mc.maxDD_R.quantile(.50),"p95":mc.maxDD_R.quantile(.95)},
        {"metric":"max_losing_streak","p05":mc.max_losing_streak.quantile(.05),"p50":mc.max_losing_streak.quantile(.50),"p95":mc.max_losing_streak.quantile(.95)}
    ])

def main():
    print("=== ORB WALK-FORWARD REGIME + DIRECTION TEST ===")
    print("Frozen entry/exit parameters:",BASE_CFG)
    print("Variants:",VARIANTS)
    print("Selector: each test year 2019-2026 uses only prior 3 completed years.")
    x=s2.load_all()
    ex=s2.resample_exec(x,15)
    ex=fd.add_indicators(ex)
    t=fd.build_trade_features(x,ex)
    t.to_csv("orb_wf_trade_features.csv",index=False)
    print("baseline trades",len(t),"range",t.year.min(),t.year.max())

    fixed=annual_fixed(t)
    fixed.to_csv("orb_wf_fixed_variants_by_year.csv",index=False)
    print("\nFIXED VARIANTS BY YEAR\n",fixed.round(4).to_string(index=False))

    sel,oos=trailing_selector(t)
    sel.to_csv("orb_wf_selector_by_year.csv",index=False)
    oos.to_csv("orb_wf_selected_oos_trades.csv",index=False)
    print("\nWALK-FORWARD SELECTIONS\n",sel.round(4).to_string(index=False))

    print("\nCOMBINED WALK-FORWARD OOS PERFORMANCE")
    for product in ["ES","MES"]:
        print(product,stat(oos,product,1))
    fr=friction_table(oos)
    fr.to_csv("orb_wf_friction.csv",index=False)
    print("\nFRICTION STRESS\n",fr.round(4).to_string(index=False))

    mc=monte_carlo(oos,10000,42)
    mcs=mc_summary(mc)
    mc.to_csv("orb_wf_monte_carlo_samples.csv",index=False)
    mcs.to_csv("orb_wf_monte_carlo_summary.csv",index=False)
    print("\nMONTE CARLO MES 1-TICK SUMMARY\n",mcs.round(4).to_string(index=False))

    # Also report simple fixed candidate aggregates over modern and recent blocks.
    rows=[]
    for v in VARIANTS:
        for label,yrs in [("2016_2020",range(2016,2021)),("2021_2023",range(2021,2024)),
                          ("2024_2025",[2024,2025]),("2026",[2026]),("2019_2026",range(2019,2027))]:
            train=t[t.year<min(yrs)].copy() if label!="2016_2020" else t[t.year<2021].copy()
            q=apply_variant(t[t.year.isin(list(yrs))],v,train)
            rows.append({"variant":v,"block":label,**stat(q)})
    agg=pd.DataFrame(rows)
    agg.to_csv("orb_wf_variant_blocks.csv",index=False)
    print("\nVARIANT BLOCKS\n",agg.round(4).to_string(index=False))

if __name__=="__main__":
    main()
