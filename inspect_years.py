import io, requests, pandas as pd
BASE='https://raw.githubusercontent.com/worldtradingchampion-source/btcdata/main/ES_1min_{}.csv'
for y in range(2021,2027):
    url=BASE.format(y)
    r=requests.get(url,timeout=120)
    print('\nYEAR',y,'status',r.status_code,'bytes',len(r.content))
    r.raise_for_status()
    first='\n'.join(r.text.splitlines()[:5])
    print(first)
    try:
        df=pd.read_csv(io.StringIO(r.text),nrows=5)
        print('columns',list(df.columns))
    except Exception as e:
        print('read_csv_error',repr(e))
