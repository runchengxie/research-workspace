import pandas as pd, glob, concurrent.futures

DATA_DIR = '/home/richard/data/market-data-platform/assets/tushare/a_share/daily/a_share_all_daily_clean_latest/data'
OUT = '/home/richard/code/research-workspace-combo/strategy-research/experiments/qlib_pilot/universe_top800_by_date.csv'
TOP_N = 800

files = sorted(glob.glob(f'{DATA_DIR}/*.parquet'))
print('files:', len(files))

def read_date(f):
    d = pd.read_parquet(f, columns=['trade_date','symbol','amount'])
    return d[d['trade_date']>='20220101'][d['trade_date']<='20260529']

with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
    parts = list(ex.map(read_date, files))

big = pd.concat(parts, ignore_index=True)
print('total rows:', len(big))

# 按日期分组，每日期按amount降序取top800
big = big.sort_values(['trade_date','amount'], ascending=[True,False])
top = big.groupby('trade_date', sort=True).head(TOP_N)
top = top[['trade_date','symbol']].copy()
print('top rows:', len(top))
print('unique dates:', top['trade_date'].nunique())
top.to_csv(OUT, index=False)
print('saved:', OUT)
# 抽查
s = top[top['trade_date']=='20260529'].head(5)
print(s)
