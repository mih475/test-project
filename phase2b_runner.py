from pathlib import Path

p=Path('phase2b_diagnostics.py')
s=p.read_text()
s=s.replace("daily=pd.DataFrame(daily).sort_values('session')", "daily=pd.DataFrame(daily).sort_values('session')\n    daily['session']=pd.to_datetime(daily['session'])\n    t=t.copy(); t['session']=pd.to_datetime(t['session'])")
exec(compile(s, str(p), 'exec'))
