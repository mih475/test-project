import io
import math
import requests
import numpy as np
import pandas as pd

DATA_URL = "https://raw.githubusercontent.com/getdata-finance/es-1m-ohlcv-stocks-historical-data/main/ES_1m.csv"
TICK = 0.25


def load_data():
    r = requests.get(DATA_URL, timeout=60)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df['datetime'] = pd.to_datetime(df['datetime'], utc=True)
    df = df.sort_values('datetime').drop_duplicates('datetime').set_index('datetime')
    for c in ['open','high','low','close','volume']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df = df.dropna()
    df = df.tz_convert('America/New_York')
    # Regular trading hours only, to make the session anchor explicit and avoid overnight gaps.
    df = df.between_time('09:30', '16:00', inclusive='left')
    df['session'] = df.index.date
    return df


def session_bands(df):
    x = df.copy()
    tp = (x['high'] + x['low'] + x['close']) / 3.0
    pv = tp * x['volume']
    p2v = (tp ** 2) * x['volume']
    g = x.groupby('session', sort=False)
    cv = g['volume'].cumsum()
    cpv = pv.groupby(x['session']).cumsum()
    cp2v = p2v.groupby(x['session']).cumsum()
    vwap = cpv / cv
    var = (cp2v / cv) - vwap**2
    sd = np.sqrt(var.clip(lower=0))
    x['vwap'] = vwap
    x['sd'] = sd
    x['u1'] = vwap + sd
    x['l1'] = vwap - sd
    x['u2'] = vwap + 2*sd
    x['l2'] = vwap - 2*sd
    return x


def resample_bands(df, rule):
    pieces = []
    for sess, d in df.groupby('session', sort=False):
        # 09:30 aligned bars. label/closed right makes the value available only at bar completion.
        r = d[['open','high','low','close','volume']].resample(rule, origin='start_day', offset='30min', label='right', closed='right').agg({
            'open':'first','high':'max','low':'min','close':'last','volume':'sum'
        }).dropna()
        r['session'] = sess
        pieces.append(r)
    out = pd.concat(pieces).sort_index()
    return session_bands(out)


def attach_completed_tf(min1, tf):
    cols = ['close','vwap','sd','u1','l1','u2','l2']
    # merge_asof uses only already-completed higher-TF bars.
    left = min1.reset_index().rename(columns={'datetime':'ts'})
    right = tf[cols].reset_index().rename(columns={'datetime':'tf_ts'})
    m = pd.merge_asof(left.sort_values('ts'), right.sort_values('tf_ts'), left_on='ts', right_on='tf_ts', direction='backward', suffixes=('','_tf'))
    m = m.set_index('ts')
    return m


def build_frame(df):
    b1 = session_bands(df)
    b5 = resample_bands(df, '5min')
    b30 = resample_bands(df, '30min')

    x = b1.copy()
    # Attach last completed 5m and 30m values explicitly.
    for name, tf in [('5', b5), ('30', b30)]:
        right = tf[['close','vwap','u2','l2']].reset_index()
        right.columns = ['tf_ts',f'close{name}',f'vwap{name}',f'u2_{name}',f'l2_{name}']
        left = x.reset_index().rename(columns={'datetime':'ts'})
        merged = pd.merge_asof(left.sort_values('ts'), right.sort_values('tf_ts'), left_on='ts', right_on='tf_ts', direction='backward')
        x = merged.set_index('ts')
        x.index.name = 'datetime'

    # Approximate signed-volume CVD from 1-minute bars. This is NOT true bid/ask delta.
    sign = np.where(x['close'] > x['open'], 1, np.where(x['close'] < x['open'], -1, np.sign(x['close'].diff().fillna(0))))
    x['delta_proxy'] = sign * x['volume']
    x['cvd_proxy'] = x.groupby('session')['delta_proxy'].cumsum()
    return x


def first_touch_trade(d, entry_i, direction, stop, target, end_i):
    entry = float(d.iloc[entry_i]['open'])
    if direction == 1 and stop >= entry: return None
    if direction == -1 and stop <= entry: return None
    risk = (entry-stop) if direction==1 else (stop-entry)
    if risk < TICK: return None
    for j in range(entry_i, end_i+1):
        row = d.iloc[j]
        if direction == 1:
            hit_s = row['low'] <= stop
            hit_t = row['high'] >= target
        else:
            hit_s = row['high'] >= stop
            hit_t = row['low'] <= target
        if hit_s and hit_t:
            return -1.0, j, 'ambiguous_stop_first'
        if hit_s:
            return -1.0, j, 'stop'
        if hit_t:
            r = ((target-entry)/risk) if direction==1 else ((entry-target)/risk)
            return r, j, 'target'
    exit_px = float(d.iloc[end_i]['close'])
    r = ((exit_px-entry)/risk) if direction==1 else ((entry-exit_px)/risk)
    return r, end_i, 'eod'


def backtest(frame, mode='1m', cvd=False):
    trades=[]
    for sess, d in frame.groupby('session', sort=False):
        d=d.copy()
        if len(d)<120: continue
        in_pos_until=-1
        excursion=None
        # wait 60 minutes for bands to stabilize and stop before final minute
        for i in range(60, len(d)-1):
            if i <= in_pos_until: continue
            row=d.iloc[i]
            if not np.isfinite(row['u2']) or not np.isfinite(row['l2']): continue
            # Start or update an excursion.
            below = row['low'] < row['l2']
            above = row['high'] > row['u2']
            if excursion is None:
                if below and not above:
                    # Reference prior 20-min low/CVD for a simple divergence proxy.
                    prior = d.iloc[max(0,i-20):i]
                    k = prior['low'].idxmin() if len(prior) else None
                    excursion={'dir':1,'start':i,'extreme':float(row['low']),'cvd_ext':float(row['cvd_proxy']),
                               'ref_price':float(prior.loc[k,'low']) if k is not None else np.nan,
                               'ref_cvd':float(prior.loc[k,'cvd_proxy']) if k is not None else np.nan}
                elif above and not below:
                    prior = d.iloc[max(0,i-20):i]
                    k = prior['high'].idxmax() if len(prior) else None
                    excursion={'dir':-1,'start':i,'extreme':float(row['high']),'cvd_ext':float(row['cvd_proxy']),
                               'ref_price':float(prior.loc[k,'high']) if k is not None else np.nan,
                               'ref_cvd':float(prior.loc[k,'cvd_proxy']) if k is not None else np.nan}
                continue
            else:
                if excursion['dir']==1 and row['low'] < excursion['extreme']:
                    excursion['extreme']=float(row['low']); excursion['cvd_ext']=float(row['cvd_proxy'])
                if excursion['dir']==-1 and row['high'] > excursion['extreme']:
                    excursion['extreme']=float(row['high']); excursion['cvd_ext']=float(row['cvd_proxy'])

            dirn=excursion['dir']
            inside1 = (row['close'] > row['l2']) if dirn==1 else (row['close'] < row['u2'])
            if not inside1: continue
            if mode=='mtf':
                vals=[row.get('close5'),row.get('u2_5'),row.get('l2_5'),row.get('close30'),row.get('u2_30'),row.get('l2_30')]
                if any(pd.isna(v) for v in vals): continue
                inside5 = (row['close5'] > row['l2_5']) if dirn==1 else (row['close5'] < row['u2_5'])
                inside30 = (row['close30'] > row['l2_30']) if dirn==1 else (row['close30'] < row['u2_30'])
                if not (inside5 and inside30): continue
            if cvd:
                # Price must exceed the prior 20m extreme while CVD fails to confirm it.
                if dirn==1:
                    div = excursion['extreme'] < excursion['ref_price'] and excursion['cvd_ext'] > excursion['ref_cvd']
                else:
                    div = excursion['extreme'] > excursion['ref_price'] and excursion['cvd_ext'] < excursion['ref_cvd']
                if not div:
                    # abandon this excursion once it has reclaimed without divergence
                    excursion=None
                    continue
            entry_i=i+1
            entry=float(d.iloc[entry_i]['open'])
            stop=(excursion['extreme']-TICK) if dirn==1 else (excursion['extreme']+TICK)
            # Primary target = current session VWAP at signal time. Require target in profitable direction.
            target=float(row['vwap'])
            if (dirn==1 and target<=entry) or (dirn==-1 and target>=entry):
                excursion=None; continue
            outcome=first_touch_trade(d,entry_i,dirn,stop,target,len(d)-1)
            if outcome is None:
                excursion=None; continue
            r,exit_i,why=outcome
            risk=(entry-stop) if dirn==1 else (stop-entry)
            trades.append({'session':sess,'signal_time':d.index[i],'entry_time':d.index[entry_i],'direction':'long' if dirn==1 else 'short',
                           'entry':entry,'stop':stop,'target':target,'risk_pts':risk,'R':r,'exit_reason':why,
                           'weekday':pd.Timestamp(sess).day_name()})
            in_pos_until=exit_i
            excursion=None
    return pd.DataFrame(trades)


def stats(t):
    if t.empty: return {}
    wins=t[t.R>0].R
    losses=t[t.R<=0].R
    pf = wins.sum()/abs(losses.sum()) if len(losses) and abs(losses.sum())>0 else np.inf
    eq=t.R.cumsum(); dd=eq-eq.cummax()
    return {
        'trades':len(t),
        'win_rate_pct':100*(t.R>0).mean(),
        'avg_R':t.R.mean(),
        'median_R':t.R.median(),
        'profit_factor':pf,
        'total_R':t.R.sum(),
        'max_drawdown_R':dd.min(),
        'avg_win_R':wins.mean() if len(wins) else np.nan,
        'avg_loss_R':losses.mean() if len(losses) else np.nan,
    }


def fixed_r_outcomes(frame, mode='mtf', reward=2.0):
    # Same signal engine but use fixed reward:risk target, useful for testing the OP's 3R claim.
    trades=[]
    for sess,d in frame.groupby('session',sort=False):
        d=d.copy(); excursion=None; busy=-1
        for i in range(60,len(d)-1):
            if i<=busy: continue
            row=d.iloc[i]
            if not np.isfinite(row['u2']) or not np.isfinite(row['l2']): continue
            below=row['low']<row['l2']; above=row['high']>row['u2']
            if excursion is None:
                if below and not above: excursion={'dir':1,'extreme':float(row['low'])}
                elif above and not below: excursion={'dir':-1,'extreme':float(row['high'])}
                continue
            if excursion['dir']==1: excursion['extreme']=min(excursion['extreme'],float(row['low']))
            else: excursion['extreme']=max(excursion['extreme'],float(row['high']))
            dirn=excursion['dir']
            inside1=(row['close']>row['l2']) if dirn==1 else (row['close']<row['u2'])
            if not inside1: continue
            if mode=='mtf':
                vals=[row.get('close5'),row.get('u2_5'),row.get('l2_5'),row.get('close30'),row.get('u2_30'),row.get('l2_30')]
                if any(pd.isna(v) for v in vals): continue
                inside5=(row['close5']>row['l2_5']) if dirn==1 else (row['close5']<row['u2_5'])
                inside30=(row['close30']>row['l2_30']) if dirn==1 else (row['close30']<row['u2_30'])
                if not(inside5 and inside30): continue
            entry_i=i+1; entry=float(d.iloc[entry_i]['open'])
            stop=(excursion['extreme']-TICK) if dirn==1 else (excursion['extreme']+TICK)
            risk=(entry-stop) if dirn==1 else (stop-entry)
            if risk<TICK: excursion=None; continue
            target=entry+reward*risk if dirn==1 else entry-reward*risk
            out=first_touch_trade(d,entry_i,dirn,stop,target,len(d)-1)
            if out:
                r,j,why=out; trades.append({'session':sess,'R':r,'weekday':pd.Timestamp(sess).day_name()}); busy=j
            excursion=None
    return pd.DataFrame(trades)


def print_block(name,t):
    s=stats(t)
    print('\n===',name,'===')
    for k,v in s.items(): print(f'{k}: {v:.4f}' if isinstance(v,(float,np.floating)) else f'{k}: {v}')
    if not t.empty:
        print('weekday:')
        for wd,g in t.groupby('weekday'):
            ss=stats(g); print(wd, 'n=',ss['trades'],'win%=',round(ss['win_rate_pct'],1),'avgR=',round(ss['avg_R'],3),'PF=',round(ss['profit_factor'],3))


def main():
    df=load_data()
    print('rows',len(df),'sessions',df.session.nunique(),'start',df.index.min(),'end',df.index.max())
    print('volume note: source labels this field as tick/update volume; CVD and volume-profile conclusions are therefore provisional.')
    frame=build_frame(df)
    print_block('1m re-entry -> VWAP', backtest(frame,'1m',False))
    print_block('1m+5m+30m re-entry -> VWAP', backtest(frame,'mtf',False))
    print_block('MTF + signed-volume CVD proxy -> VWAP', backtest(frame,'mtf',True))
    for rr in [1.0,2.0,3.0]:
        print_block(f'MTF fixed {rr:.0f}R target', fixed_r_outcomes(frame,'mtf',rr))

if __name__=='__main__':
    main()
