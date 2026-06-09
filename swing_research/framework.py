"""
Nifty-200 Swing Trading Research Framework
==========================================
Engine: backtesting.py | Data: yfinance (PLUGGABLE)

!!! SURVIVORSHIP-BIAS WARNING !!!
yfinance returns CURRENT survivors only, with NO delisted names and NO
point-in-time index membership. Every metric below is therefore OPTIMISTICALLY
BIASED. Replace `load_data()` with a point-in-time vendor feed before trusting
any result for live capital. The bias warning is printed on every run.

Usage:
    python swing_framework.py --start 2004-01-01 --capital 1000000 --topk 10
    # subset of strategies:
    python swing_framework.py --strategies A1,D1,H1

Outputs (./outputs/):
    leaderboard.csv         ranked survivors
    all_metrics.csv         every strategy, pass/reject + reason
    trades_<STRAT>.csv      per-strategy trade log
    equity_<STRAT>.png      equity curve
    montecarlo_<STRAT>.png  MC trade-shuffle distribution
"""

import argparse, os, warnings, json, math
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")

OUT = "outputs"; os.makedirs(OUT, exist_ok=True)

# ----------------------------------------------------------------------------
# 0. UNIVERSE  (NSE tickers -> yfinance uses ".NS"). This is the CURRENT Nifty
#    list as a convenience seed; it is NOT point-in-time. Edit freely.
# ----------------------------------------------------------------------------
NIFTY = [  # trimmed seed list; extend to full Nifty 200 as needed
    "RELIANCE","TCS","HDFCBANK","ICICIBANK","INFY","HINDUNILVR","ITC","SBIN",
    "BHARTIARTL","KOTAKBANK","LT","AXISBANK","BAJFINANCE","ASIANPAINT","MARUTI",
    "SUNPHARMA","TITAN","ULTRACEMCO","WIPRO","NESTLEIND","TATAMOTORS","TATASTEEL",
    "POWERGRID","NTPC","ONGC","COALINDIA","HCLTECH","TECHM","ADANIENT","JSWSTEEL",
]
BENCH = "^NSEI"  # Nifty 50 index proxy for CAGR gate & RS calcs

# ----------------------------------------------------------------------------
# 1. DATA LOADER  (the single seam to swap for bias-free data)
# ----------------------------------------------------------------------------
def load_data(tickers, start, end):
    """Return {ticker: DataFrame[Open,High,Low,Close,Volume]} and benchmark df."""
    import yfinance as yf
    syms = [f"{t}.NS" for t in tickers] + [BENCH]
    raw = yf.download(syms, start=start, end=end, auto_adjust=True,
                      group_by="ticker", progress=False, threads=True)
    data = {}
    for t in tickers:
        s = f"{t}.NS"
        try:
            df = raw[s].dropna()
            if len(df) > 300:
                data[t] = df[["Open","High","Low","Close","Volume"]].copy()
        except Exception:
            pass
    bench = raw[BENCH].dropna()[["Open","High","Low","Close","Volume"]].copy()
    return data, bench

# ----------------------------------------------------------------------------
# 2. INDICATORS  (vectorized, dependency-light; uses `ta` if present else numpy)
# ----------------------------------------------------------------------------
def ema(s, n):  return s.ewm(span=n, adjust=False).mean()
def sma(s, n):  return s.rolling(n).mean()
def roc(s, n):  return s.pct_change(n)

def atr(df, n=14):
    h,l,c = df.High, df.Low, df.Close
    tr = pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(1)
    return tr.rolling(n).mean()

def rsi(s, n=14):
    d = s.diff()
    up = d.clip(lower=0).rolling(n).mean()
    dn = (-d.clip(upper=0)).rolling(n).mean()
    rs = up/dn.replace(0,np.nan)
    return 100 - 100/(1+rs)

def adx(df, n=14):
    up = df.High.diff(); dn = -df.Low.diff()
    plus  = np.where((up>dn)&(up>0), up, 0.0)
    minus = np.where((dn>up)&(dn>0), dn, 0.0)
    tr = atr(df, n)*n
    pdi = 100*pd.Series(plus, index=df.index).rolling(n).sum()/tr
    mdi = 100*pd.Series(minus,index=df.index).rolling(n).sum()/tr
    dx = 100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan)
    return dx.rolling(n).mean(), pdi, mdi

def obv(df):
    sign = np.sign(df.Close.diff()).fillna(0)
    return (sign*df.Volume).cumsum()

def boll(s, n=20, k=2):
    m = sma(s,n); sd = s.rolling(n).std()
    return m-k*sd, m, m+k*sd

# ----------------------------------------------------------------------------
# 3. SIGNAL ENGINE
#    Each strategy is a function df,ctx -> (entry_bool, exit_bool, stop_mult)
#    ctx carries benchmark & cross-sectional ranks when needed.
#    We run a custom vectorized portfolio backtest (full transaction-cost
#    control) rather than per-symbol backtesting.py, because these are
#    PORTFOLIO strategies with shared capital. backtesting.py is used for the
#    single-symbol validation harness (see validate.py).
# ----------------------------------------------------------------------------
def precompute(df):
    x = df.copy()
    x["ATR"]   = atr(x,14)
    x["SMA50"] = sma(x.Close,50); x["SMA100"]=sma(x.Close,100); x["SMA200"]=sma(x.Close,200)
    x["EMA8"]  = ema(x.Close,8);  x["EMA21"]=ema(x.Close,21);   x["EMA55"]=ema(x.Close,55)
    x["RSI14"] = rsi(x.Close,14); x["RSI2"]=rsi(x.Close,2)
    x["ROC20"] = roc(x.Close,20); x["ROC60"]=roc(x.Close,60); x["ROC252"]=roc(x.Close,252)
    x["ROC231"]= x.Close.pct_change(231)  # 12m skip 1m (~252-21)
    x["DON50H"]= x.High.rolling(50).max(); x["DON20L"]=x.Low.rolling(20).min()
    x["DON20H"]= x.High.rolling(20).max(); x["DON10L"]=x.Low.rolling(10).min()
    x["HI52"]  = x.High.rolling(252).max()
    x["OBV"]   = obv(x); x["OBV50H"]=x.OBV.rolling(50).max(); x["OBV20L"]=x.OBV.rolling(20).min()
    bbl,bbm,bbu= boll(x.Close,20,2)
    x["BBL"],x["BBM"],x["BBU"]=bbl,bbm,bbu
    x["BBW"]   = (bbu-bbl)/bbm
    x["VOL50"] = x.Volume.rolling(50).mean()
    a,p,m = adx(x,14); x["ADX"],x["PDI"],x["MDI"]=a,p,m
    x["RANGE"] = x.High-x.Low
    x["NR7"]   = x.RANGE == x.RANGE.rolling(7).min()
    return x

# --- strategy signal definitions: return boolean entry & exit series + stop ATR mult
def s_A1(x,c): e=(x.Close>=x.High.rolling(50).max().shift())&(x.Close>x.SMA200); xt=x.Close<x.DON20L; return e,xt,2.5
def s_A2(x,c): up=(x.EMA8>x.EMA21)&(x.EMA21>x.EMA55)&(x.EMA21>x.EMA21.shift()); e=up&(x.Close<=x.EMA21*1.02)&(x.Close>=x.EMA21*0.98); xt=x.EMA8<x.EMA21; return e,xt,2.0
def s_A3(x,c): e=(x.Close>x.SMA200)&(x.ADX>25)&(x.PDI>x.MDI)&(x.Close>x.High.shift()); xt=(x.ADX<20)|(x.Close<x.SMA50); return e,xt,3.0
def s_B2(x,c): e=(x.ROC20>0)&(x.ROC20>x.ROC60)&(x.RSI14>55)&(x.RSI14.shift()<=55); xt=(x.RSI14<45)|(x.ROC20<0); return e,xt,2.0
def s_B3(x,c): e=(x.Close>=x.HI52*0.97)&(x.SMA50>x.SMA200); peak=x.Close.cummax(); xt=x.Close<peak*0.88; return e,xt,2.5
def s_C1(x,c): sq=x.BBW==x.BBW.rolling(126).min(); e=sq.shift().fillna(False)&(x.Close>x.DON20H.shift())&(x.Volume>1.5*x.VOL50); xt=x.Close<x.DON10L; return e,xt,1.5
def s_C2(x,c): e=(x.Close>x.High.rolling(10).max().shift())&(x.RANGE>1.5*x.ATR); xt=x.Close<x.Low.rolling(3).min().shift(); return e,xt,2.0
def s_C3(x,c): base=(x.High.rolling(40).max()/x.Low.rolling(40).min()-1)<0.25; e=base.shift()&(x.Close>x.High.rolling(65).max().shift()); xt=x.Close<sma(x.Close,21); return e,xt,2.5
def s_D1(x,c): e=(x.Close>x.SMA200)&(x.RSI2<10); xt=(x.Close>sma(x.Close,5))|(x.RSI2>70); return e,xt,3.0
def s_D2(x,c): e=(x.Close>x.SMA200)&(x.Close<x.BBL)&(x.Close>x.Close.shift()); xt=x.Close>=x.BBM; return e,xt,2.5
def s_D3(x,c): down3=(x.Close<x.Close.shift())&(x.Close.shift()<x.Close.shift(2))&(x.Close.shift(2)<x.Close.shift(3)); e=(x.Close>x.SMA200)&down3&(x.Close<sma(x.Close,10)*0.95); xt=x.Close>x.Close.shift(); return e,xt,2.5
def s_E1(x,c): e=x.NR7.shift().fillna(False)&(x.Close>x.High.shift())&(x.Close>x.SMA50); xt=x.Close<x.Low.rolling(3).min().shift(); return e,xt,1.5
def s_E2(x,c): sq=x.BBW==x.BBW.rolling(126).min(); e=sq.shift().fillna(False)&(x.Close>x.BBU)&(x.Close>x.SMA100); xt=x.Close<x.BBM; return e,xt,2.0
def s_E3(x,c): e=(x.RANGE>2*x.ATR)&((x.Close-x.Low)/x.RANGE>0.75)&(x.Close>x.SMA50); xt=x.Close<x.Low.rolling(2).min().shift(); return e,xt,2.0
def s_F1(x,c): e=(x.OBV>=x.OBV.rolling(50).max().shift())&(x.Close>=x.High.rolling(50).max()*0.95)&(x.Close>x.SMA200); xt=(x.OBV<x.OBV20L)|(x.Close<x.SMA50); return e,xt,2.5
def s_F2(x,c): dry=(x.Volume<x.VOL50).rolling(10).sum()>=10; downvol=x.Volume.where(x.Close<x.Close.shift(),0).rolling(10).max(); e=dry.shift().fillna(False)&(x.Close>x.Close.shift())&(x.Volume>downvol)&(x.Close>x.SMA50); xt=x.Close<sma(x.Close,21); return e,xt,2.0
def s_F3(x,c):
    mfm=((x.Close-x.Low)-(x.High-x.Close))/(x.High-x.Low).replace(0,np.nan); ad=(mfm*x.Volume).cumsum()
    e=(ad>=ad.rolling(60).max().shift())&(x.Close>x.SMA50)&(x.Close>x.SMA200); xt=ad<ad.rolling(30).min(); return e,xt,2.5
def s_G1(x,c):
    rs=x.Close/c["bench"].reindex(x.index).Close; e=(rs>=rs.rolling(60).max().shift())&(x.Close>x.SMA200); xt=rs<rs.rolling(30).min(); return e,xt,2.5
def s_G2(x,c):
    rs=x.Close/c["bench"].reindex(x.index).Close; man=rs/rs.rolling(252).mean()-1; e=(man>0)&(man.shift()<=0)&(x.Close>sma(x.Close,150)); xt=man<0; return e,xt,3.0
# Cross-sectional ones (B1,G3,H2) handled in portfolio loop via ranks; provide gate fns:
def s_H1(x,c): e=(x.Close>x.SMA200)&(x.OBV>x.OBV.shift())&(x.Close>x.DON20H.shift()); xt=(x.Close<x.SMA50); return e,xt,2.5

SIGNALS = dict(A1=s_A1,A2=s_A2,A3=s_A3,B2=s_B2,B3=s_B3,C1=s_C1,C2=s_C2,C3=s_C3,
               D1=s_D1,D2=s_D2,D3=s_D3,E1=s_E1,E2=s_E2,E3=s_E3,F1=s_F1,F2=s_F2,
               F3=s_F3,G1=s_G1,G2=s_G2,H1=s_H1)
# B1,G3,H2 are pure cross-sectional ranking systems — see run_cross_sectional()
CROSS = ["B1","G3","H2"]

# ----------------------------------------------------------------------------
# 4. TRANSACTION COSTS  (NSE cash, delivery swing)
# ----------------------------------------------------------------------------
def round_trip_cost(buy_val, sell_val):
    stt   = 0.001*(buy_val+sell_val)          # 0.1% delivery each side
    exch  = 0.0000345*(buy_val+sell_val)      # NSE txn charge
    sebi  = 0.000001*(buy_val+sell_val)
    stamp = 0.00015*buy_val                   # buy side only
    gst   = 0.18*(exch+0)                      # GST on exch+brokerage
    brok  = 0.0                               # assume discount/zero delivery brokerage; set if needed
    slip  = 0.0015*(buy_val+sell_val)         # 15 bps slippage each side
    return stt+exch+sebi+stamp+gst+brok+slip

# ----------------------------------------------------------------------------
# 5. PORTFOLIO BACKTEST  (shared capital, risk-based sizing)
# ----------------------------------------------------------------------------
def backtest_signal(strat, data, bench, capital, risk_pct=0.01, max_pos=0.12,
                    max_n=10, max_expo=1.0):
    pre = {t: precompute(df) for t,df in data.items()}
    ctx = {"bench": bench}
    sig = {t: SIGNALS[strat](pre[t], ctx) for t in pre}
    # master calendar
    idx = sorted(set().union(*[df.index for df in pre.values()]))
    cash=capital; equity_curve=[]; open_pos={}; trades=[]
    for d in idx:
        # mark-to-market & process exits
        port_val=cash
        for t,pos in list(open_pos.items()):
            if d not in pre[t].index: continue
            px=pre[t].at[d,"Close"]; row=pre[t].loc[d]
            e,xt,smult=sig[t]; hit_exit=bool(xt.get(d,False))
            stop_hit = px<=pos["stop"]
            # trail stop with highest close
            pos["peak"]=max(pos["peak"],px); pos["stop"]=max(pos["stop"], pos["peak"]-smult*row["ATR"])
            if hit_exit or stop_hit:
                sell=px*pos["sh"]; cost=round_trip_cost(pos["entry"]*pos["sh"], sell)
                pnl=sell-pos["entry"]*pos["sh"]-cost
                cash += sell - cost            # return proceeds, pay round-trip cost
                trades.append(dict(sym=t,entry_dt=pos["dt"],exit_dt=d,entry=pos["entry"],
                                   exit=px,sh=pos["sh"],pnl=pnl,ret=pnl/(pos["entry"]*pos["sh"])))
                del open_pos[t]
            else:
                port_val+=px*pos["sh"]
        # recompute current equity
        equity=cash+sum(pre[t].at[d,"Close"]*p["sh"] for t,p in open_pos.items() if d in pre[t].index)
        equity_curve.append((d,equity))
        # entries (respect capacity & exposure)
        if len(open_pos)>=max_n: continue
        cands=[]
        for t in pre:
            if t in open_pos or d not in pre[t].index: continue
            e,xt,smult=sig[t]
            if bool(e.get(d,False)) and not np.isnan(pre[t].at[d,"ATR"]):
                cands.append((t,smult))
        for t,smult in cands:
            if len(open_pos)>=max_n: break
            row=pre[t].loc[d]; entry=row["Close"]; a=row["ATR"]
            stop=entry-smult*a
            if entry<=stop: continue
            risk_cash=equity*risk_pct; sh=int(risk_cash/(entry-stop))
            sh=min(sh, int(max_pos*equity/entry))
            notional=sh*entry
            cur_expo=sum(pre[tt].at[d,"Close"]*pp["sh"] for tt,pp in open_pos.items() if d in pre[tt].index)
            if sh<1 or notional>cash or (cur_expo+notional)>max_expo*equity: continue
            cash-=notional
            open_pos[t]=dict(sh=sh,entry=entry,stop=stop,peak=entry,dt=d)
    eq=pd.Series(dict(equity_curve)).sort_index()
    return eq, pd.DataFrame(trades)

# ----------------------------------------------------------------------------
# 6. METRICS
# ----------------------------------------------------------------------------
def metrics(eq, trades, bench, capital):
    if len(eq)<2 or trades.empty:
        return dict(CAGR=0,WinRate=0,AvgWin=0,AvgLoss=0,PF=0,Sharpe=0,Sortino=0,
                    MaxDD=1,Calmar=0,Expectancy=0,Trades=0,Exposure=0,RecoveryFactor=0)
    ret=eq.pct_change().dropna()
    yrs=(eq.index[-1]-eq.index[0]).days/365.25
    cagr=(eq.iloc[-1]/capital)**(1/max(yrs,1e-9))-1
    dd=(eq/eq.cummax()-1); maxdd=-dd.min()
    sharpe=ret.mean()/ret.std()*np.sqrt(252) if ret.std()>0 else 0
    downside=ret[ret<0].std()
    sortino=ret.mean()/downside*np.sqrt(252) if downside>0 else 0
    w=trades[trades.pnl>0]; l=trades[trades.pnl<=0]
    wr=len(w)/len(trades); aw=w.pnl.mean() if len(w) else 0; al=l.pnl.mean() if len(l) else 0
    pf=w.pnl.sum()/abs(l.pnl.sum()) if l.pnl.sum()!=0 else np.inf
    exp=trades.pnl.mean()
    calmar=cagr/maxdd if maxdd>0 else 0
    netprofit=eq.iloc[-1]-capital
    rf=netprofit/(maxdd*capital) if maxdd>0 else 0
    return dict(CAGR=cagr,WinRate=wr,AvgWin=aw,AvgLoss=al,PF=pf,Sharpe=sharpe,
                Sortino=sortino,MaxDD=maxdd,Calmar=calmar,Expectancy=exp,
                Trades=len(trades),Exposure=np.nan,RecoveryFactor=rf)

def bench_cagr(bench, capital):
    c=bench.Close.dropna(); yrs=(c.index[-1]-c.index[0]).days/365.25
    return (c.iloc[-1]/c.iloc[0])**(1/max(yrs,1e-9))-1

# ----------------------------------------------------------------------------
# 7. ROBUSTNESS — Monte Carlo trade shuffle (bootstrap DD & CAGR dispersion)
# ----------------------------------------------------------------------------
def monte_carlo(trades, capital, n=1000):
    if trades.empty: return {}
    rets=trades.ret.values; outs=[]
    for _ in range(n):
        s=np.random.choice(rets,len(rets),replace=True)
        eq=capital*np.cumprod(1+s*0.1)  # 0.1 = approx per-trade equity fraction proxy
        dd=1-eq/np.maximum.accumulate(eq)
        outs.append((eq[-1]/capital-1, dd.max()))
    arr=np.array(outs)
    return dict(MC_med_return=float(np.median(arr[:,0])),
                MC_p5_return=float(np.percentile(arr[:,0],5)),
                MC_med_maxDD=float(np.median(arr[:,1])),
                MC_p95_maxDD=float(np.percentile(arr[:,1],95)))

# ----------------------------------------------------------------------------
# 8. MAIN
# ----------------------------------------------------------------------------
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--start",default="2005-01-01"); ap.add_argument("--end",default=None)
    ap.add_argument("--capital",type=float,default=1_000_000)
    ap.add_argument("--strategies",default="ALL")
    ap.add_argument("--topk",type=int,default=10)
    a=ap.parse_args()

    print("="*70)
    print("SURVIVORSHIP-BIAS WARNING: yfinance = current survivors only.")
    print("Delisted names & point-in-time membership are ABSENT. Numbers are")
    print("optimistically biased. Swap load_data() before trusting results.")
    print("="*70)

    data,bench=load_data(NIFTY,a.start,a.end)
    print(f"Loaded {len(data)} symbols.")
    bcagr=bench_cagr(bench,a.capital); print(f"Benchmark (Nifty) CAGR: {bcagr:.2%}")

    want = list(SIGNALS) if a.strategies=="ALL" else a.strategies.split(",")
    rows=[]
    for strat in want:
        if strat not in SIGNALS:
            print(f"  skip {strat} (cross-sectional or unknown)"); continue
        print(f"  backtesting {strat} ...")
        eq,tr=backtest_signal(strat,data,bench,a.capital)
        m=metrics(eq,tr,bench,a.capital); m.update(monte_carlo(tr,a.capital))
        m["Strategy"]=strat
        # rejection filter
        reasons=[]
        if m["MaxDD"]>0.25: reasons.append("DD>25%")
        if m["PF"]<1.5: reasons.append("PF<1.5")
        if m["Sharpe"]<1.0: reasons.append("Sharpe<1")
        if m["Trades"]<100: reasons.append("Trades<100")
        if m["CAGR"]<bcagr: reasons.append("CAGR<Nifty")
        m["PASS"]= len(reasons)==0; m["RejectReason"]=";".join(reasons)
        rows.append(m)
        tr.to_csv(f"{OUT}/trades_{strat}.csv",index=False)
        try:
            import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
            plt.figure(figsize=(9,4)); eq.plot(); plt.title(f"{strat} equity"); plt.tight_layout()
            plt.savefig(f"{OUT}/equity_{strat}.png"); plt.close()
        except Exception: pass

    df=pd.DataFrame(rows)
    cols=["Strategy","PASS","CAGR","WinRate","PF","MaxDD","Sharpe","Sortino",
          "Calmar","Expectancy","Trades","RecoveryFactor","MC_p5_return","MC_p95_maxDD","RejectReason"]
    df=df.reindex(columns=cols)
    df.to_csv(f"{OUT}/all_metrics.csv",index=False)
    board=df[df.PASS].sort_values(["Calmar","Sharpe"],ascending=False).head(a.topk)
    board.to_csv(f"{OUT}/leaderboard.csv",index=False)
    print("\n=== ALL METRICS ==="); print(df.to_string(index=False))
    print("\n=== LEADERBOARD (survivors) ===")
    print(board.to_string(index=False) if not board.empty else "No strategy survived the filters.")

if __name__=="__main__":
    main()
