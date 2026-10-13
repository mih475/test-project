"""Read-only audit of selected UI candles; seed parity remains unverified."""
import json,re,sys
from pathlib import Path
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parent
RESEARCH = ROOT.parent/'research_snapshot' if (ROOT.parent/'research_snapshot').exists() else ROOT.parents[1]
sys.path.insert(0,str(RESEARCH))
import types
sys.modules.setdefault("requests", types.ModuleType("requests")) # Offline recurrence calls only.
import orb_refinement_stage2 as s2
import orb_filter_diagnostics as fd
# selected_values.csv contains values transcribed from Data Window UI snapshots.
d=pd.read_csv(ROOT/'selected_values.csv').set_index('timestamp').sort_index()
fail=[];counts={};details=[]
def check(name,ok,context):
 counts[name]=counts.get(name,0)+1
 if not ok:fail.append({'check':name,'context':context})
def close(a,b):return bool(np.isclose(a,b,atol=2e-8,rtol=0))
for t,r in d.iterrows():
 ts=pd.Timestamp(t);req=r.requested_session
 if str(ts.date())!=req:continue # Holiday missing candles map to next available bar.
 check('A_B_common_indicator_values',all(close(r['A_'+k],r['B_'+k]) for k in ['Parity OR high','Parity OR low / stop','Python-style RTH EMA50','Python-style RTH ATR7']),t)
 if ts.hour==9 and ts.minute==30:
  check('OR_equals_opening_candle',close(r['A_Parity OR high'],r.High) and close(r['A_Parity OR low / stop'],r.Low),t)
 prev=str(ts-pd.Timedelta(minutes=15))
 if prev in d.index:
  p=d.loc[prev]
  if p.requested_session!=req:continue
  ema=pd.Series([p['B_Python-style RTH EMA50'],r.Close]).ewm(span=50,adjust=False).mean().iloc[-1]
  tr=max(r.High-r.Low,abs(r.High-p.Close),abs(r.Low-p.Close))
  atr=s2.rma(pd.Series([p['B_Python-style RTH ATR7']]*7+[tr]),7).iloc[-1]
  di=r['B_Python-style RTH +DI14']+r['B_Python-style RTH -DI14']
  dx=100*abs(r['B_Python-style RTH +DI14']-r['B_Python-style RTH -DI14'])/di
  adx=fd.wilder(pd.Series([p['B_Python-style RTH ADX14']]*14+[dx]),14).iloc[-1]
  check('EMA50_python_recurrence',close(ema,r['B_Python-style RTH EMA50']),t)
  check('ATR7_python_recurrence',close(atr,r['B_Python-style RTH ATR7']),t)
  check('ADX14_python_recurrence',close(adx,r['B_Python-style RTH ADX14']),t)
  check('one_RTH_indicator_update_per_bar',r['B_Parity RTH bar count']==p['B_Parity RTH bar count']+1,t)
 for c in 'AB':
  if r[c+'_Parity long signal (1/0)']==1:
   ok=r.Close>r[c+'_Parity OR high'] and r.Close>r[c+'_Python-style RTH EMA50']
   if c=='B':ok=ok and r['B_Python-style RTH ADX14']>=20 and r['B_Python-style RTH +DI14']>r['B_Python-style RTH -DI14']
   check('signal_conditions',ok,c+' '+t)
   check('captured_ATR_equals_signal_ATR',close(r[c+'_Parity captured ATR'],r[c+'_Python-style RTH ATR7']),c+' '+t)
   nxt=str(ts+pd.Timedelta(minutes=15))
   if nxt in d.index:
    n=d.loc[nxt]; trades=pd.read_csv(ROOT/'after_calendar'/f'candidate_{c}_trades.csv')
    match=trades[(trades.Type=='Entry long')&(trades['Date and time']==nxt[:16])]
    check('signal_to_next_open',len(match)==1 and close(match.iloc[0]['Price USD'],n.Open),c+' '+t)
    if pd.notna(n[c+'_Parity target']):check('target_entry_plus_1_5_signal_ATR',close(n[c+'_Parity target'],n.Open+1.5*r[c+'_Parity captured ATR']),c+' '+t)
 for c in 'AB':
  if r[c+'_Parity skipped session (1/0)']==1:check('shortened_session_no_signal',r[c+'_Parity long signal (1/0)']==0,c+' '+t)
# Compare sampled exits to candle OHLC and stored frozen brackets.
for c in 'AB':
 trades=pd.read_csv(ROOT/'after_calendar'/f'candidate_{c}_trades.csv');entries=trades[trades.Type=='Entry long'].set_index('Trade number')
 for _,x in trades[trades.Type=='Exit long'].iterrows():
  t=x['Date and time']+':00'
  if t not in d.index:continue
  r=d.loc[t];e=entries.loc[x['Trade number']]; et=e['Date and time']+':00';st=str(pd.Timestamp(et)-pd.Timedelta(minutes=15))
  if st not in d.index:continue
  sig=d.loc[st];stop=sig[c+'_Parity OR low / stop'];target=e['Price USD']+1.5*sig[c+'_Parity captured ATR'];price=x['Price USD']
  if x.Signal=='RTH close':check('RTH_close_final_bar_close',pd.Timestamp(t).strftime('%H:%M')=='15:45' and close(price,r.Close),c+' '+t)
  elif abs(price-stop)<.251:check('stop_touched',r.Low<=stop,c+' '+t)
  elif abs(price-target)<.251:check('target_touched_with_tick_rounding',r.High>=target,c+' '+t)
  else:fail.append({'check':'unclassified_exit','context':c+' '+t})
  details.append({'candidate':c,'entry':et,'exit':t,'exit_signal':x.Signal,'stop':stop,'target_unrounded':target,'fill':price,'both_touched':bool(r.Low<=stop and r.High>=target)})
# Original Python exports use ES, not TradingView MES. Compare only sampled overlapping dates.
comparison=[]
for c in 'AB':
 pyfile=RESEARCH/f'candidate_{c}_frozen_rules.csv'
 if not pyfile.exists():continue # Generate offline frozen audit exports before this optional comparison.
 py=pd.read_csv(pyfile)
 tv=pd.read_csv(ROOT/'after_calendar'/f'candidate_{c}_trades.csv')
 for date in ['2026-05-05','2026-05-06','2026-05-22','2026-06-01','2026-06-05']:
  a=py[py.session==date];b=tv[(tv.Type=='Entry long')&tv['Date and time'].str.startswith(date)]
  comparison.append({'candidate':c,'date':date,'python_ES_entry':None if a.empty else a.iloc[0].entry_time,'tradingview_MES_entry':None if b.empty else b.iloc[0]['Date and time'],'python_ES_price':None if a.empty else float(a.iloc[0].entry),'tradingview_MES_price':None if b.empty else float(b.iloc[0]['Price USD'])})
report={'requested_sessions':10,'observed_candles':len(d),'checks':counts,'failures':fail,'exit_checks':details,'python_export_comparison':comparison,'limitations':['UI sample recurrence checks are seeded from the preceding observed Pine value; complete indicator seed/history parity is unverified.','DI values/filter observed; independent DI14 numeric parity needs identical source history and ATR14 state.','Original Python exports use ES feed; TradingView uses MES. Full same-feed parity and one-minute exit sequencing cannot be established.','Chart export and Bar Magnifier blocked by Essential plan.'],'status':'sample_checked_full_parity_unverified'}
(ROOT/'selected_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
