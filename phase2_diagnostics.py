import numpy as np
import pandas as pd
import multiyear_backtest as mb

POS_LEVELS=[0.25,0.5,0.75,1.0,1.5,2.0,3.0]
NEG_LEVELS=[0.25,0.5,0.75,1.0]
RNG=np.random.default_rng(42)


def k(x):
    return str(x).replace('.','_')


def pf_stats(vals):
    vals=pd.Series(vals,dtype=float).dropna()
    if vals.empty:return {'n':0,'avgR':np.nan,'PF':np.nan,'totalR':0.0,'maxDD_R':np.nan,'win_pct':np.nan}
    wins=vals[vals>0]; losses=vals[vals<=0]
    pf=wins.sum()/abs(losses.sum()) if len(losses) and abs(losses.sum())>0 else np.inf
    eq=vals.cumsum(); dd=eq-eq.cummax()
    return {'n':len(vals),'avgR':vals.mean(),'PF':pf,'totalR':vals.sum(),'maxDD_R':dd.min(),'win_pct':100*(vals>0).mean()}


def fmt_stats(vals):
    s=pf_stats(vals)
    return ' '.join(f'{a}={b:.4f}' if isinstance(b,(float,np.floating)) else f'{a}={b}' for a,b in s.items())


def add_features(frame):
    pieces=[]
    daily=[]
    for sess,d in frame.groupby('session',sort=False):
        d=d.copy().sort_index()
        prev=d.close.shift(1)
        tr=pd.concat([(d.high-d.low),(d.high-prev).abs(),(d.low-prev).abs()],axis=1).max(axis=1)
        d['atr30']=tr.rolling(30,min_periods=10).mean()
        d['vol_mean20']=d.volume.rolling(20,min_periods=5).mean()
        d['vol_rel20']=d.volume/d.vol_mean20.replace(0,np.nan)
        d['vwap_slope30_z']=(d.vwap-d.vwap.shift(30))/d.sd.replace(0,np.nan)
        d['ret30_z']=(d.close-d.close.shift(30))/d.sd.replace(0,np.nan)
        d['range_sofar']=d.high.cummax()-d.low.cummin()
        side=np.sign(d.close-d.vwap)
        d['vwap_cross']=((side!=side.shift(1)) & side.ne(0) & side.shift(1).ne(0)).astype(int)
        d['vwap_crosses_sofar']=d.vwap_cross.cumsum()
        pieces.append(d)
        first30=d[(d.index.hour==9)&(d.index.minute>=30)&(d.index.minute<=59)]
        daily.append({'session':sess,'day_range':float(d.high.max()-d.low.min()),
                      'or30':float(first30.high.max()-first30.low.min()) if len(first30) else np.nan})
    x=pd.concat(pieces).sort_index()
    day=pd.DataFrame(daily).sort_values('session').set_index('session')
    day['prior20_day_range_med']=day.day_range.shift(1).rolling(20,min_periods=10).median()
    day['prior20_or30_med']=day.or30.shift(1).rolling(20,min_periods=10).median()
    return x,day


def path_metrics(d,entry_i,dirn,entry,risk):
    first_pos={z:None for z in POS_LEVELS}; first_neg={z:None for z in NEG_LEVELS}
    mfe=0.0; mae=0.0
    for j in range(entry_i,len(d)):
        r=d.iloc[j]
        fav=((r.high-entry)/risk) if dirn==1 else ((entry-r.low)/risk)
        adv=((entry-r.low)/risk) if dirn==1 else ((r.high-entry)/risk)
        mfe=max(mfe,float(fav)); mae=min(mae,-float(adv))
        for z in POS_LEVELS:
            if first_pos[z] is None and fav>=z:first_pos[z]=j
        for z in NEG_LEVELS:
            if first_neg[z] is None and adv>=z:first_neg[z]=j
    out={'MFE_EOD_R':mfe,'MAE_EOD_R':mae}
    stop_j=first_neg[1.0]
    for z in POS_LEVELS:
        pj=first_pos[z]
        # Conservative: if target and stop first occur in the same 1m bar, stop wins.
        success=(pj is not None) and (stop_j is None or pj<stop_j)
        out[f'plus_{k(z)}_before_stop']=bool(success)
        out[f'first_plus_{k(z)}_min']=np.nan if pj is None else int(pj-entry_i)
    for z in NEG_LEVELS:
        nj=first_neg[z]
        out[f'first_minus_{k(z)}_min']=np.nan if nj is None else int(nj-entry_i)
    out['stop_before_eod']=stop_j is not None
    return out


def generate_diagnostic_trades(frame,day):
    trades=[]
    for sess,d in frame.groupby('session',sort=False):
        d=d.copy(); busy=-1; excursion=None
        if len(d)<120:continue
        dayref=day.loc[sess] if sess in day.index else None
        for i in range(60,len(d)-1):
            if i<=busy:continue
            row=d.iloc[i]
            if not np.isfinite(row.u2) or not np.isfinite(row.l2):continue
            below=row.low<row.l2; above=row.high>row.u2
            if excursion is None:
                if below and not above:
                    prior=d.iloc[max(0,i-20):i]
                    if prior.empty:continue
                    idx=prior.low.idxmin()
                    excursion={'dir':1,'extreme':float(row.low),'cvd_ext':float(row.cvd_proxy),
                               'ref_price':float(prior.loc[idx,'low']),'ref_cvd':float(prior.loc[idx,'cvd_proxy']),
                               'start_i':i}
                elif above and not below:
                    prior=d.iloc[max(0,i-20):i]
                    if prior.empty:continue
                    idx=prior.high.idxmax()
                    excursion={'dir':-1,'extreme':float(row.high),'cvd_ext':float(row.cvd_proxy),
                               'ref_price':float(prior.loc[idx,'high']),'ref_cvd':float(prior.loc[idx,'cvd_proxy']),
                               'start_i':i}
                continue
            if excursion['dir']==1 and row.low<excursion['extreme']:
                excursion['extreme']=float(row.low); excursion['cvd_ext']=float(row.cvd_proxy)
            if excursion['dir']==-1 and row.high>excursion['extreme']:
                excursion['extreme']=float(row.high); excursion['cvd_ext']=float(row.cvd_proxy)
            dirn=excursion['dir']
            inside1=(row.close>row.l2) if dirn==1 else (row.close<row.u2)
            vals=[row.get('close5'),row.get('u2_5'),row.get('l2_5'),row.get('close30'),row.get('u2_30'),row.get('l2_30')]
            if not inside1 or any(pd.isna(v) for v in vals):continue
            inside5=(row.close5>row.l2_5) if dirn==1 else (row.close5<row.u2_5)
            inside30=(row.close30>row.l2_30) if dirn==1 else (row.close30<row.u2_30)
            if not(inside5 and inside30):continue
            if dirn==1:
                div=excursion['extreme']<excursion['ref_price'] and excursion['cvd_ext']>excursion['ref_cvd']
            else:
                div=excursion['extreme']>excursion['ref_price'] and excursion['cvd_ext']<excursion['ref_cvd']
            if not div:
                excursion=None; continue
            entry_i=i+1; entry=float(d.iloc[entry_i].open)
            stop=(excursion['extreme']-mb.TICK) if dirn==1 else (excursion['extreme']+mb.TICK)
            risk=(entry-stop) if dirn==1 else (stop-entry)
            target=float(row.vwap)
            if risk<mb.TICK or (dirn==1 and target<=entry) or (dirn==-1 and target>=entry):
                excursion=None; continue
            base=mb.simulate(d,entry_i,dirn,stop,target)
            if base is None:
                excursion=None; continue
            rr,j,why,mfe,mae=base
            pm=path_metrics(d,entry_i,dirn,entry,risk)
            sd=float(row.sd) if pd.notna(row.sd) and row.sd>0 else np.nan
            prior_range=np.nan if dayref is None else dayref.prior20_day_range_med
            prior_or=np.nan if dayref is None else dayref.prior20_or30_med
            or30=np.nan if dayref is None else dayref.or30
            ext_depth=((row.l2-excursion['extreme'])/sd) if dirn==1 and pd.notna(sd) else ((excursion['extreme']-row.u2)/sd if pd.notna(sd) else np.nan)
            cvd_diff=(excursion['cvd_ext']-excursion['ref_cvd'])*dirn
            vol_scale=max(float(row.vol_mean20)*20,1.0) if pd.notna(row.vol_mean20) else np.nan
            rec={
                'session':pd.Timestamp(sess),'year':int(pd.Timestamp(sess).year),'signal_time':d.index[i],
                'entry_time':d.index[entry_i],'exit_time':d.index[j],'direction':'long' if dirn==1 else 'short',
                'entry_hour':int(d.index[i].hour),'R':float(rr),'exit_reason':why,'entry_price':entry,
                'stop_price':stop,'target_price':target,'risk_pts':risk,'symbol':row.symbol,
                'baseline_MFE_R':mfe,'baseline_MAE_R':mae,'atr30':float(row.atr30) if pd.notna(row.atr30) else np.nan,
                'risk_atr30':risk/row.atr30 if pd.notna(row.atr30) and row.atr30>0 else np.nan,
                'vol_rel20':float(row.vol_rel20) if pd.notna(row.vol_rel20) else np.nan,
                'vwap_slope30_z':float(row.vwap_slope30_z) if pd.notna(row.vwap_slope30_z) else np.nan,
                'ret30_z':float(row.ret30_z) if pd.notna(row.ret30_z) else np.nan,
                'dir_vwap_slope30_z':dirn*float(row.vwap_slope30_z) if pd.notna(row.vwap_slope30_z) else np.nan,
                'range_ratio_prior20':float(row.range_sofar/prior_range) if pd.notna(prior_range) and prior_range>0 else np.nan,
                'or_ratio_prior20':float(or30/prior_or) if pd.notna(or30) and pd.notna(prior_or) and prior_or>0 else np.nan,
                'vwap_crosses_sofar':int(row.vwap_crosses_sofar),
                'excursion_bars':int(i-excursion['start_i']),
                'excursion_depth_sd':float(ext_depth) if pd.notna(ext_depth) else np.nan,
                'cvd_div_norm':float(cvd_diff/vol_scale) if pd.notna(vol_scale) else np.nan,
            }
            rec.update(pm); trades.append(rec)
            busy=j; excursion=None
    return pd.DataFrame(trades)


def control_candidates(frame):
    out={}; sessions={}
    for sess,d in frame.groupby('session',sort=False):
        d=d.copy(); sessions[sess]=d
        if len(d)<120:continue
        y=int(pd.Timestamp(sess).year)
        for i in range(60,len(d)-1):
            out.setdefault((y,int(d.index[i].hour)),[]).append((sess,i))
    return out,sessions


def make_controls(frame,trades,n_each=10):
    cand,sessions=control_candidates(frame); rows=[]
    for tid,t in trades.iterrows():
        pool=cand.get((int(t.year),int(t.entry_hour)),[])
        if not pool:continue
        valid=[x for x in pool if pd.Timestamp(x[0])!=pd.Timestamp(t.session)]
        if not valid:valid=pool
        picks=RNG.integers(0,len(valid),size=n_each)
        dirn=1 if t.direction=='long' else -1
        for q in picks:
            sess,i=valid[int(q)]; d=sessions[sess]; entry_i=i+1
            entry=float(d.iloc[entry_i].open); risk=float(t.risk_pts)
            pm=path_metrics(d,entry_i,dirn,entry,risk)
            rec={'trade_id':int(tid),'year':int(t.year),'entry_hour':int(t.entry_hour),'direction':t.direction,
                 'control_session':pd.Timestamp(sess),'control_signal_time':d.index[i],'risk_pts':risk}
            for z in [0.5,1.0,2.0]:rec[f'plus_{k(z)}_before_stop']=pm[f'plus_{k(z)}_before_stop']
            rows.append(rec)
    return pd.DataFrame(rows)


def entry_edge_report(t,c):
    print('\n=== ENTRY EDGE VS MATCHED RANDOM CONTROLS ===')
    periods=[('ALL',pd.Series(True,index=t.index))]+[(str(y),t.year.eq(y)) for y in sorted(t.year.unique())]
    for label,mask in periods:
        a=t[mask]
        cc=c[c.year.isin(a.year.unique())] if label=='ALL' else c[c.year.eq(int(label))]
        print('\nPERIOD',label,'signal_n',len(a),'control_n',len(cc))
        for z in [0.5,1.0,2.0]:
            col=f'plus_{k(z)}_before_stop'
            ps=float(a[col].mean()) if len(a) else np.nan; pc=float(cc[col].mean()) if len(cc) else np.nan
            se=np.sqrt(ps*(1-ps)/max(1,len(a))+pc*(1-pc)/max(1,len(cc))) if np.isfinite(ps) and np.isfinite(pc) else np.nan
            zscore=(ps-pc)/se if se and se>0 else np.nan
            print(f'+{z}R before -1R signal={100*ps:.2f}% control={100*pc:.2f}% lift_pp={100*(ps-pc):.2f} z={zscore:.2f}')


def winner_fragility(t):
    print('\n=== WINNER CONCENTRATION / FRAGILITY ===')
    for y,g in t.groupby('year'):
        pos=g[g.R>0].sort_values('R',ascending=False)
        print(y,'totalR',round(g.R.sum(),2),'top1R',round(pos.R.head(1).sum(),2),'top3R',round(pos.R.head(3).sum(),2),
              'without_top1',fmt_stats(g.drop(pos.head(1).index).R),'without_top3',fmt_stats(g.drop(pos.head(3).index).R))
    pos=t[t.R>0].sort_values('R',ascending=False)
    for pct in [0.01,0.05,0.10]:
        n=max(1,int(np.ceil(len(t)*pct)))
        z=t.drop(pos.head(n).index)
        print('remove_top_winners_pct',int(pct*100),'n_removed',n,fmt_stats(z.R))


def longest_losing_streak(vals):
    best=cur=0
    for x in vals:
        if x<=0:cur+=1;best=max(best,cur)
        else:cur=0
    return best


def cost_stress(t):
    print('\n=== COST / SLIPPAGE STRESS ===')
    # Configurable representative round-trip commission assumptions; not broker quotes.
    scenarios=[
        ('gross',0,0,50),
        ('ES_comm5',0,5.00,50),('ES_1tick_each_side_comm5',1,5.00,50),('ES_2tick_each_side_comm5',2,5.00,50),
        ('MES_comm1.50',0,1.50,5),('MES_1tick_each_side_comm1.50',1,1.50,5),('MES_2tick_each_side_comm1.50',2,1.50,5),
    ]
    for name,slip_ticks_side,comm_usd,point_value in scenarios:
        cost_pts=2*slip_ticks_side*mb.TICK + comm_usd/point_value
        net=t.R-(cost_pts/t.risk_pts)
        print(name,'cost_points_per_roundtrip',round(cost_pts,4),fmt_stats(net),'longest_nonwin_streak',longest_losing_streak(net.to_numpy()))


def regime_report(t):
    print('\n=== 2025 VS 2026 REGIME MEDIANS ===')
    feats=['atr30','risk_pts','risk_atr30','vol_rel20','vwap_slope30_z','ret30_z','range_ratio_prior20','or_ratio_prior20',
           'vwap_crosses_sofar','excursion_bars','excursion_depth_sd','cvd_div_norm','MFE_EOD_R','MAE_EOD_R']
    for f in feats:
        a=t.loc[t.year==2025,f].median(); b=t.loc[t.year==2026,f].median()
        print(f,'2025',round(float(a),4) if pd.notna(a) else 'nan','2026',round(float(b),4) if pd.notna(b) else 'nan')

    print('\n=== PREDEFINED REGIME BUCKETS (DIAGNOSTIC ONLY) ===')
    specs={
        'abs_vwap_slope':(t.vwap_slope30_z.abs(),[-np.inf,.15,.35,.70,np.inf]),
        'range_ratio_prior20':(t.range_ratio_prior20,[-np.inf,.5,.8,1.2,np.inf]),
        'or_ratio_prior20':(t.or_ratio_prior20,[-np.inf,.7,1.4,np.inf]),
        'vol_rel20':(t.vol_rel20,[-np.inf,.75,1.0,1.5,np.inf]),
        'risk_pts':(t.risk_pts,[-np.inf,1,2,4,8,np.inf]),
        'excursion_depth_sd':(t.excursion_depth_sd,[-np.inf,.10,.25,.50,np.inf]),
        'excursion_bars':(t.excursion_bars,[-np.inf,3,10,30,np.inf]),
        'vwap_crosses':(t.vwap_crosses_sofar,[-np.inf,2,5,10,np.inf]),
    }
    for name,(vals,bins) in specs.items():
        cats=pd.cut(vals,bins,include_lowest=True)
        print('\nFEATURE',name)
        for cat in cats.dropna().unique():
            g=t[cats==cat]
            if len(g)<10:continue
            p1=100*g.plus_1_0_before_stop.mean()
            print(str(cat),'ALL',fmt_stats(g.R),'plus1_before_stop',round(p1,2),
                  '|2025',fmt_stats(g[g.year==2025].R),'|2026',fmt_stats(g[g.year==2026].R))


def path_report(t):
    print('\n=== EXCURSION PATH SUMMARY ===')
    for label,g in [('ALL',t)]+[(str(y),t[t.year==y]) for y in sorted(t.year.unique())]:
        print('\n',label,'n',len(g),'MFE_EOD_med',round(g.MFE_EOD_R.median(),3),'MAE_EOD_med',round(g.MAE_EOD_R.median(),3))
        for z in [0.25,0.5,0.75,1.0,1.5,2.0,3.0]:
            col=f'plus_{k(z)}_before_stop'; tm=f'first_plus_{k(z)}_min'
            print(f'+{z}R_before_stop={100*g[col].mean():.2f}% median_minutes_to_touch={g[tm].median():.1f}')


def main():
    raw=mb.load_all()
    print('DATA rows',len(raw),'sessions',raw.session.nunique(),'start',raw.index.min(),'end',raw.index.max())
    frame=mb.build_frame(raw)
    frame,day=add_features(frame)
    trades=generate_diagnostic_trades(frame,day)
    print('DIAGNOSTIC_TRADES',len(trades))
    print('BASELINE',fmt_stats(trades.R))
    trades.to_csv('phase2_trades.csv',index=False)

    controls=make_controls(frame,trades,n_each=10)
    controls.to_csv('phase2_controls.csv',index=False)
    entry_edge_report(trades,controls)
    path_report(trades)
    regime_report(trades)
    winner_fragility(trades)
    cost_stress(trades)

    print('\n=== DECISION FLAGS ===')
    sig=trades.plus_1_0_before_stop.mean(); ctl=controls.plus_1_0_before_stop.mean()
    print('plus1_signal_vs_control_pp',round(100*(sig-ctl),2))
    print('baseline_positive_expectancy',bool(trades.R.mean()>0))
    print('2025_positive_expectancy',bool(trades.loc[trades.year==2025,'R'].mean()>0))
    print('2026_positive_expectancy',bool(trades.loc[trades.year==2026,'R'].mean()>0))
    print('NOTE: This run diagnoses the existing rules. It does not optimize filters, stops, targets, or exits.')
    print('NOTE: CVD remains the signed 1-minute bar-volume proxy, not true aggressor-side exchange delta.')

if __name__=='__main__':
    main()
