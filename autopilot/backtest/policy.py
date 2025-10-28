
import os, json, numpy as np, pandas as pd, math

PROC = "/workspace/data/processed"

def _drawdown(equity: pd.Series) -> pd.Series:
    peak = equity.cummax()
    dd   = equity/peak - 1.0
    return dd

def _ann_stats(returns: pd.Series, periods_per_year=252):
    r = returns.dropna()
    if len(r)==0:
        return dict(cagr=None, vol=None, sharpe=None)
    # CAGR من منحنى العائد التراكمي
    eq = (1.0 + r).cumprod()
    n_years = max(len(r)/periods_per_year, 1e-9)
    cagr = eq.iloc[-1]**(1.0/n_years) - 1.0
    vol  = r.std() * math.sqrt(periods_per_year)
    sharpe = (r.mean()*periods_per_year)/vol if vol and not np.isnan(vol) and vol!=0 else None
    return dict(cagr=float(cagr), vol=float(vol) if vol==vol else None, sharpe=float(sharpe) if sharpe==sharpe else None)

def run_backtest(symbol: str, periods_per_year=252):
    f = os.path.join(PROC, f"{symbol}_features.parquet")
    if not os.path.exists(f):
        raise FileNotFoundError(f)
    df = pd.read_parquet(f).sort_values("Date").reset_index(drop=True)
    if "ret" not in df.columns:
        df["ret"] = df["Close"].pct_change()

    # إن لم توجد إشارات سابقة، استخدم سياسة بسيطة (Close>SMA20 & RSI>50 & MACD>MACD_SIG)
    if "signal" not in df.columns:
        close = df["Close"]
        sma20 = df["SMA_20"] if "SMA_20" in df else close.rolling(20).mean()
        rsi   = df["RSI_14"] if "RSI_14" in df else 50
        macd  = df["MACD"] if "MACD" in df else 0
        sig   = df["MACD_SIG"] if "MACD_SIG" in df else 0
        df["signal"] = ((close > sma20) & (rsi > 50) & (macd > sig)).astype(int)

    df["pos"]      = df["signal"].shift(1).fillna(0)
    df["str_ret"]  = df["pos"] * df["ret"]
    df["eq_curve"] = (1.0 + df["str_ret"]).cumprod()
    df["bh_curve"] = (1.0 + df["ret"]).cumprod()

    # قياسات
    eq = df["eq_curve"].fillna(1.0)
    bh = df["bh_curve"].fillna(1.0)
    dd = _drawdown(eq)
    maxdd = float(dd.min()) if len(dd) else None

    st = _ann_stats(df["str_ret"], periods_per_year)
    st_bh = _ann_stats(df["ret"], periods_per_year)

    metrics = {
        "symbol": symbol,
        "last_date": str(df["Date"].iloc[-1]) if "Date" in df.columns and len(df)>0 else None,
        "eq_final": float(eq.iloc[-1]) if len(eq) else None,
        "bh_final": float(bh.iloc[-1]) if len(bh) else None,
        "maxdd": maxdd,                 # قيمة سالبة (مثلاً -0.25 = -25%)
        "cagr": st["cagr"], "vol": st["vol"], "sharpe": st["sharpe"],
        "bh_cagr": st_bh["cagr"], "bh_vol": st_bh["vol"], "bh_sharpe": st_bh["sharpe"],
    }

    # حفظ النتائج
    out_parq = os.path.join(PROC, f"{symbol}_bt.parquet")
    out_json = os.path.join(PROC, f"{symbol}_bt.json")
    df_out = df[["Date","eq_curve","bh_curve","str_ret","ret"]].copy()
    df_out.to_parquet(out_parq, index=False)
    with open(out_json,"w") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    return out_parq, out_json, metrics
