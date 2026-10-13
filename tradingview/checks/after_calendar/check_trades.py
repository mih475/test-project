"""Structural audit of TradingView emulator exports; not candle parity."""
import json
from pathlib import Path
import pandas as pd
root=Path(__file__).resolve().parent
out={}
for c in 'AB':
 d=pd.read_csv(root/f'candidate_{c}_trades.csv'); d['dt']=pd.to_datetime(d['Date and time'])
 e=d[d.Type=='Entry long'].set_index('Trade number'); x=d[d.Type=='Exit long'].set_index('Trade number'); m=e.dt.dt.hour*60+e.dt.dt.minute
 overnight=e.dt.dt.date!=x.dt.dt.date
 checks={'all_long':bool(d.Type.isin(['Entry long','Exit long']).all()),'one_contract':bool((d['Size (qty)']==1).all()),'one_entry_per_day':bool(e.groupby(e.dt.dt.date).size().max()==1),'entry_time_1000_through_1545':bool(m.between(600,945).all()),'quarter_hour_entries':bool((e.dt.dt.minute%15==0).all()),'same_day_exit':bool((~overnight).all()),'roundtrip_commission_1_50':bool((x['Commission USD']==1.5).all()),'rth_close_on_final_bar':bool((x[x.Signal=='RTH close'].dt.dt.strftime('%H:%M')=='15:45').all())}
 out[c]={'closed_trades':len(x),'first_entry':str(e.dt.min()),'last_entry':str(e.dt.max()),'rth_close_exits':int((x.Signal=='RTH close').sum()),'checks':checks,'overnight_exceptions':[{'trade_number':int(i),'entry':str(e.loc[i,'dt']),'exit':str(x.loc[i,'dt']),'exit_signal':x.loc[i,'Signal']} for i in e.index[overnight]]}
(root/'trade_checks.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
