"""Small UI sample comparison, original ES source and actual research indicators."""
import sys,types,json
from pathlib import Path
import pandas as pd,numpy as np
root=Path(__file__).resolve().parent
research=root.parent/'research_snapshot' if (root.parent/'research_snapshot').exists() else root.parents[1]
sys.path.insert(0,str(research))
req=types.ModuleType('requests');sys.modules['requests']=req
import orb_refinement_stage2 as s2
import orb_filter_diagnostics as fd
class Response:
 def __init__(self):self.text=(research/'data/ES_1min_2026.csv').read_text();self.content=self.text.encode();self.status_code=200
 def raise_for_status(self):pass
req.get=lambda *a,**kw:Response()
x=s2.load_year(2026).set_index('datetime_et')
x=x[x.index>=pd.Timestamp('2026-05-01',tz=s2.NY)]
ex=fd.add_indicators(s2.resample_exec(x,15))
ui=pd.read_csv(root/'selected_values.csv');out=[]
for _,r in ui.iterrows():
 t=pd.Timestamp(r.timestamp,tz=s2.NY)
 if t not in ex.index or t.strftime('%Y-%m-%d') not in ['2026-05-05','2026-05-06','2026-05-22','2026-06-01','2026-06-05']:continue
 p=ex.loc[t];row={'timestamp':r.timestamp,'source':'ES original versus MES TradingView; both initialized May 1','ohlc_delta_max':float(max(abs(r[c.title()]-p[c]) for c in ['open','high','low','close']))}
 for py,pine in [('ema50','EMA50'),('atr7','ATR7'),('adx14','ADX14'),('pdi14','+DI14'),('mdi14','-DI14')]:
  row[pine+'_ES']=float(p[py]);row[pine+'_MES']=float(r['B_Python-style RTH '+pine]);row[pine+'_delta']=row[pine+'_MES']-row[pine+'_ES']
 out.append(row)
(root/'reference_sample.json').write_text(json.dumps(out,indent=2)+'\n')
print('Compared',len(out),'sample candles; mismatches are data/history-sensitive, not certified parity.')
print([r for r in out if r['timestamp']=='2026-06-01 14:00:00'])
