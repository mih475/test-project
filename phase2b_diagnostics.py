import numpy as np
import pandas as pd
import multiyear_backtest as mb

THRESHOLDS=(0.25,0.5,0.75,1.0,1.5,2.0,3.0)
RNG=np.random.default_rng(20260922)


def basic_stats(t, col='R'):
    if len(t)==0:
        return {'n':0}
    v=pd.to_numeric(t[col],errors='coerce').dropna()
    if len(v)==0:
        return {'n':0}
    wins=v[v>0]; losses=v[v<=0]
    pf=wins.sum()/abs(losses.sum()) if len(losses) and abs(losses.sum())>0 else np.inf
    eq=v.cumsum(); dd=eq-eq.cummax()
    return {'n':len(v),'win_pct':100*(v>0).mean(),'avgR':v.mean(),'PF':pf,'totalR':v.sum(),'maxDD_R':dd.min()}


def print_stats(label,t,col='R'):
    s=basic_stats(t,col)
    print(label, ' '.join(f'{k}={v:.4f}' if isinstance(v,(float,np.floating)) else f'{k}={v}' for k,v in s.items()))


def barrier_outcome(d, entry_i, direction, risk, positive_r):
    """Conservative 1-minute barrier test: +X R before -1R, ignoring VWAP target.
    If both barriers occur in the same 1-minute bar, count as failure because intrabar order is unknown.
    """
    entry=float(d.iloc[entry_i].open)
    for j in range(entry_i,len(d)):
        r=d.iloc[j]
        if direction==1:
            fav=(r.high-entry)/risk; adv=(r.low-entry)/risk
        else:
            fav=(entry-r.low)/risk; adv=(entry-r.high)/risk
        hit_pos=fav>=positive_r
        hit_neg=adv<=-1.0
        if hit_pos and hit_neg:
            return 0,j-entry_i,'ambiguous_same_bar'
        if hit_neg:
            return 0,j-entry_i,'stop_first'
        if hit_pos:
            return 1,j-entry_i,'positive_first'
    return 0,len(d)-1-entry_i,'neither_before_eod'


def simulate_path(d, entry_i, direction, stop, target):
    entry=float(d.iloc[entry_i].open)
    risk=(entry-stop) if direction==1 else (stop-entry)
    if risk<mb.TICK:
        return None
    mfe=0.0; mae=0.0
    first_times={}
    rr=None; exit_i=None; why=None
    for j in range(entry_i,len(d)):
        r=d.iloc[j]
        if direction==1:
            fav=(r.high-entry)/risk; adv=(r.low-entry)/risk
            hit_s=r.low<=stop; hit_t=r.high>=target
        else:
            fav=(entry-r.low)/risk; adv=(entry-r.high)/risk
            hit_s=r.high>=stop; hit_t=r.low<=target
        mfe=max(mfe,fav); mae=min(mae,adv)
        for th in THRESHOLDS:
            if th not in first_times and fav>=th:
                first_times[th]=j-entry_i
        if hit_s and hit_t:
            rr=-1.0; exit_i=j; why='ambiguous_stop_first'; break
        if hit_s:
            rr=-1.0; exit_i=j; why='stop'; break
        if hit_t:
            rr=((target-entry)/risk) if direction==1 else ((entry-target)/risk)
            exit_i=j; why='target'; break
    if rr is None:
        px=float(d.iloc[-1].close)
        rr=((px-entry)/risk) if direction==1 else ((entry-px)/risk)
        exit_i=len(d)-1; why='eod'
    return rr,exit_i,why,mfe,mae,first_times,entry,risk


def generate_diagnostic(frame):
    trades=[]
    for sess,d in frame.groupby('session',sort=False):
        d=d.copy(); busy=-1; excursion=None
        if len(d)<120:
            continue
        for i in range(60,len(d)-1):
            if i<=busy:
                continue
            row=d.iloc[i]
            if not np.isfinite(row.u2) or not np.isfinite(row.l2):
                continue
            below=row.low<row.l2; above=row.high>row.u2
            if excursion is None:
                if below and not above:
                    prior=d.iloc[max(0,i-20):i]
                    if len(prior)==0: continue
                    k=prior.low.idxmin()
                    excursion={'dir':1,'extreme':float(row.low),'cvd_ext':float(row.cvd_proxy),'ref_price':float(prior.loc[k,'low']),'ref_cvd':float(prior.loc[k,'cvd_proxy']),'start_i':i}
                elif above and not below:
                    prior=d.iloc[max(0,i-20):i]
                    if len(prior)==0: continue
                    k=prior.high.idxmax()
                    excursion={'dir':-1,'extreme':float(row.high),'cvd_ext':float(row.cvd_proxy),'ref_price':float(prior.loc[k,'high']),'ref_cvd':float(prior.loc[k,'cvd_proxy']),'start_i':i}
                continue
            if excursion['dir']==1 and row.low<excursion['extreme']:
                excursion['extreme']=float(row.low); excursion['cvd_ext']=float(row.cvd_proxy)
            if excursion['dir']==-1 and row.high>excursion['extreme']:
                excursion['extreme']=float(row.high); excursion['cvd_ext']=float(row.cvd_proxy)
            dirn=excursion['dir']
            inside1=(row.close>row.l2) if dirn==1 else (row.close<row.u2)
            vals=[row.get('close5'),row.get('u2_5'),row.get('l2_5'),row.get('close30'),row.get('u2_30'),row.get('l2_30')]
            if not inside1 or any(pd.isna(v) for v in vals):
                continue
            inside5=(row['close5']>row['l2_5']) if dirn==1 else (row['close5']<row['u2_5'])
            inside30=(row['close30']>row['l2_30']) if dirn==1 else (row['close30']<row['u2_30'])
            if not(inside5 and inside30):
                continue
            if dirn==1:
                div=excursion['extreme']<excursion['ref_price'] and excursion['cvd_ext']>excursion['ref_cvd']
            else:
                div=excursion['extreme']>excursion['ref_price'] and excursion['cvd_ext']<excursion['ref_cvd']
            if not div:
                excursion=None; continue
            entry_i=i+1; entry=float(d.iloc[entry_i].open)
            stop=(excursion['extreme']-mb.TICK) if dirn==1 else (excursion['extreme']+mb.TICK)
            target=float(row.vwap)
            if (dirn==1 and target<=entry) or (dirn==-1 and target>=entry):
                excursion=None; continue
            out=simulate_path(d,entry_i,dirn,stop,target)
            if out is None:
                excursion=None; continue
            rr,j,why,mfe,mae,first_times,entry,risk=out
            rec={
                'session':pd.Timestamp(sess),'year':pd.Timestamp(sess).year,
                'signal_time':d.index[i],'entry_time':d.index[entry_i],'exit_time':d.index[j],
                'direction':'long' if dirn==1 else 'short','dir_sign':dirn,'entry_hour':d.index[i].hour,
                'entry_price':entry,'stop_price':stop,'target_price':target,'risk_pts':risk,
                'target_R':abs(target-entry)/risk,'R':rr,'MFE_R':mfe,'MAE_R':mae,'exit_reason':why,
                'minutes_in_trade':j-entry_i,'symbol':row.symbol,
                'signal_vwap':float(row.vwap),'signal_sd':float(row.sd),
                'signal_close':float(row.close),'signal_volume':float(row.volume),
                'band_excursion_R':abs(excursion['extreme']-(row.l2 if dirn==1 else row.u2))/risk,
                'excursion_minutes':i-excursion['start_i'],
                'cvd_div_price_pts':abs(excursion['extreme']-excursion['ref_price']),
                'cvd_div_proxy':abs(excursion['cvd_ext']-excursion['ref_cvd'])
            }
            for th in THRESHOLDS:
                hit,mins,reason=barrier_outcome(d,entry_i,dirn,risk,th)
                key=str(th).replace('.','p')
                rec[f'hit_{key}R_before_stop']=hit
                rec[f'mins_to_{key}R_or_stop']=mins
                rec[f'barrier_{key}R_reason']=reason
                rec[f'first_{key}R_min']=first_times.get(th,np.nan)
            trades.append(rec)
            busy=j; excursion=None
    return pd.DataFrame(trades)


def add_regime_features(frame,t):
    rows=[]
    daily=[]
    for sess,d in frame.groupby('session',sort=False):
        d=d.copy().sort_index()
        d['ret1']=d.close.pct_change()
        d['vol20']=d.ret1.rolling(20,min_periods=10).std()
        d['vwap_slope30_z']=(d.vwap-d.vwap.shift(30))/d.sd.replace(0,np.nan)
        d['ret30_z']=(d.close-d.close.shift(30))/d.sd.replace(0,np.nan)
        d['range_sofar']=d.high.cummax()-d.low.cummin()
        d['relvol20']=d.volume/d.volume.rolling(20,min_periods=10).median()
        first30=d.iloc[:30]
        daily.append({'session':sess,'day_range':d.high.max()-d.low.min(),'or30':first30.high.max()-first30.low.min()})
        rows.append(d[['vwap_slope30_z','ret30_z','range_sofar','relvol20','vol20']].reset_index())
    f=pd.concat(rows,ignore_index=True).rename(columns={'datetime_et':'signal_time'})
    daily=pd.DataFrame(daily).sort_values('session')
    daily['prior20_range_med']=daily.day_range.shift(1).rolling(20,min_periods=10).median()
    daily['prior20_or_med']=daily.or30.shift(1).rolling(20,min_periods=10).median()
    x=t.merge(f,on='signal_time',how='left')
    x=x.merge(daily[['session','or30','prior20_range_med','prior20_or_med']],on='session',how='left')
    x['range_ratio_prior20']=x.range_sofar/x.prior20_range_med
    x['or_ratio_prior20']=x.or30/x.prior20_or_med
    x['dir_vwap_slope_z']=x.dir_sign*x.vwap_slope30_z
    x['distance_from_vwap_z']=(x.signal_close-x.signal_vwap).abs()/x.signal_sd.replace(0,np.nan)
    return x


def matched_random_controls(frame,t,reps=30):
    by_session={sess:d.copy().sort_index() for sess,d in frame.groupby('session',sort=False)}
    out=[]
    for ridx,tr in t.iterrows():
        sess=tr.session.date() if hasattr(tr.session,'date') else tr.session
        d=by_session.get(sess)
        if d is None or len(d)<120: continue
        candidates=np.arange(60,len(d)-1)
        candidates=candidates[[d.index[k].hour==int(tr.entry_hour) for k in candidates]]
        if len(candidates)==0: continue
        picks=RNG.choice(candidates,size=reps,replace=len(candidates)<reps)
        for p in picks:
            ei=int(p)+1
            for th in (0.5,1.0,2.0):
                hit,_,_=barrier_outcome(d,ei,int(tr.dir_sign),float(tr.risk_pts),th)
                out.append({'trade_id':ridx,'year':int(tr.year),'threshold_R':th,'hit':hit})
    return pd.DataFrame(out)


def barrier_report(t,controls):
    print('\n=== ENTRY EDGE: +X R BEFORE -1R (CONSERVATIVE SAME-BAR FAILURE) ===')
    for label,g in [('ALL',t),('2021-2023',t[t.year<=2023]),('2024',t[t.year==2024]),('2025',t[t.year==2025]),('2026',t[t.year==2026])]:
        print('\n',label)
        for th in (0.5,1.0,2.0,3.0):
            key=f"hit_{str(th).replace('.','p')}R_before_stop"
            actual=100*g[key].mean() if len(g) else np.nan
            if th in (0.5,1.0,2.0):
                cyears=set(g.year.astype(int).tolist())
                c=controls[controls.year.isin(cyears)&controls.threshold_R.eq(th)] if label!='ALL' else controls[controls.threshold_R.eq(th)]
                rnd=100*c.hit.mean() if len(c) else np.nan
                lift=actual-rnd
                print(f'+{th:.1f}R actual={actual:.2f}% matched_random={rnd:.2f}% lift={lift:+.2f}pp n={len(g)}')
            else:
                print(f'+{th:.1f}R actual={actual:.2f}% n={len(g)}')


def winner_concentration(t):
    print('\n=== WINNER CONCENTRATION ===')
    for y,g in t.groupby('year'):
        total=g.R.sum(); wins=g[g.R>0].sort_values('R',ascending=False)
        for n in (1,3,5):
            removed=g.drop(wins.head(n).index)
            print(y,'remove_top',n,'orig_totalR',round(total,2),'remaining_totalR',round(removed.R.sum(),2),'remaining_PF',round(basic_stats(removed)['PF'],3))
    wins=t[t.R>0].sort_values('R',ascending=False)
    n=max(1,int(np.ceil(len(t)*0.05)))
    removed=t.drop(wins.head(n).index)
    print('ALL remove_top_5pct_trades',n,'remaining_totalR',round(removed.R.sum(),2),'remaining_PF',round(basic_stats(removed)['PF'],3))


def cost_stress(t):
    print('\n=== EXECUTION COST STRESS (ILLUSTRATIVE) ===')
    # Commission assumptions are explicit placeholders, not broker/prop quotes.
    # MES $5/point, ES $50/point. Round-turn commissions assumed MES=$1.50, ES=$5.00.
    specs=[('MES',5.0,1.50),('ES',50.0,5.00)]
    for name,point_value,rt_comm in specs:
        for slip_ticks in (0,1,2,4):
            point_penalty=slip_ticks*mb.TICK + rt_comm/point_value
            x=t.copy(); x['R_net']=x.R-point_penalty/x.risk_pts
            print_stats(f'{name} total_adverse_slip_ticks={slip_ticks} rt_comm=${rt_comm:.2f}',x,'R_net')


def regime_report(t):
    print('\n=== REGIME DIAGNOSTICS (BINS DEFINED ONLY FROM 2021-2023) ===')
    dev=t[t.year<=2023]
    features=['vwap_slope30_z','dir_vwap_slope_z','range_ratio_prior20','or_ratio_prior20','relvol20','vol20','distance_from_vwap_z','target_R','risk_pts']
    for feat in features:
        vals=dev[feat].replace([np.inf,-np.inf],np.nan).dropna()
        if len(vals)<50: continue
        qs=vals.quantile([.25,.5,.75]).to_numpy()
        if len(np.unique(qs))<3: continue
        bins=[-np.inf,qs[0],qs[1],qs[2],np.inf]
        labels=['Q1','Q2','Q3','Q4']
        tmp=t.copy(); tmp['_bucket']=pd.cut(tmp[feat],bins=bins,labels=labels,include_lowest=True,duplicates='drop')
        print('\nFEATURE',feat,'dev_quartiles',','.join(f'{q:.6g}' for q in qs))
        for b in labels:
            g=tmp[tmp._bucket.eq(b)]
            if not len(g): continue
            s=basic_stats(g)
            h25=100*g.hit_1p0R_before_stop.mean()
            print(b,'n',len(g),'avgR',round(s['avgR'],3),'PF',round(s['PF'],3),'+1R_before_stop',round(h25,1),'2025_avgR',round(g[g.year==2025].R.mean(),3) if len(g[g.year==2025]) else np.nan,'2026_avgR',round(g[g.year==2026].R.mean(),3) if len(g[g.year==2026]) else np.nan)


def validate_against_baseline(frame,t):
    base=mb.generate(frame,use_cvd=True)
    print('\n=== BASELINE REPRODUCTION CHECK ===')
    print('baseline_n',len(base),'diagnostic_n',len(t),'baseline_totalR',round(base.R.sum(),6),'diagnostic_totalR',round(t.R.sum(),6))
    print('count_match',len(base)==len(t),'totalR_abs_diff',round(abs(base.R.sum()-t.R.sum()),10))


def main():
    raw=mb.load_all()
    print('RAW',len(raw),'sessions',raw.session.nunique(),'start',raw.index.min(),'end',raw.index.max())
    frame=mb.build_frame(raw)
    t=generate_diagnostic(frame)
    t=add_regime_features(frame,t)
    validate_against_baseline(frame,t)
    print('\n=== BASELINE ===')
    print_stats('ALL',t)
    for y,g in t.groupby('year'): print_stats(str(y),g)
    controls=matched_random_controls(frame,t,reps=30)
    barrier_report(t,controls)
    winner_concentration(t)
    cost_stress(t)
    regime_report(t)
    print('\n=== STOPPED-TRADE EXCURSION ===')
    stopped=t[t.exit_reason.isin(['stop','ambiguous_stop_first'])]
    print('stopped_n',len(stopped),'of',len(t))
    for th in (0.5,1.0,2.0):
        key=f"hit_{str(th).replace('.','p')}R_before_stop"
        print(f'stopped_reached_+{th:.1f}R_before_stop_pct',round(100*stopped[key].mean(),2))
    t.to_csv('phase2b_enriched_trades.csv',index=False)
    controls.to_csv('phase2b_random_controls.csv',index=False)

if __name__=='__main__':
    main()
