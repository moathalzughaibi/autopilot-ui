
import os, json, numpy as np, pandas as pd

PROC = "/workspace/data/processed"

def _ann_stats(r, periods=252):
    r = r.dropna()
    if len(r)==0: return {"cagr":None,"vol":None,"sharpe":None}
    eq = (1+r).cumprod()
    yrs = max(len(r)/periods, 1e-9)
    cagr = eq.iloc[-1]**(1/yrs)-1
    vol  = r.std()*np.sqrt(periods)
    sharpe = (r.mean()*periods)/vol if vol and vol==vol and vol!=0 else None
    return {"cagr":float(cagr), "vol":float(vol) if vol==vol else None, "sharpe": float(sharpe) if sharpe==sharpe else None}

def run_rules_backtest(symbol: str, cfg: dict):
    fp = os.path.join(PROC, f"{symbol}_features.parquet")
    ff = os.path.join(PROC, f"{symbol}_flow.parquet")
    fc = os.path.join(PROC, f"{symbol}_cases.parquet")

    feat = pd.read_parquet(fp).sort_values("Date").reset_index(drop=True)
    flow = pd.read_parquet(ff) if os.path.exists(ff) else pd.DataFrame()
    cases= pd.read_parquet(fc) if os.path.exists(fc) else pd.DataFrame()

    # نحتاج فقط Close/SMA20/RSI/MACD/ATR + flow_z و event recency
    df = feat[["Date","Close","SMA_20","RSI_14","MACD","MACD_SIG","ATR_14"]].copy()
    df["ret"] = df["Close"].pct_change()
    if not flow.empty and "dollar_z" in flow.columns:
        df = df.merge(flow[["Date","dollar_z"]], on="Date", how="left")
    else:
        df["dollar_z"] = np.nan

    # map nearest event days لكل يوم
    if not cases.empty:
        ce = cases[["Date","type"]].copy()
        ce["Date"] = pd.to_datetime(ce["Date"])
        df["days_since_event"] = np.nan
        last_up = None
        events = ce.sort_values("Date").to_records(index=False)
        j = 0
        for i, d in enumerate(pd.to_datetime(df["Date"])):
            while j < len(events) and events[j].Date <= d:
                if events[j].type in ("UP",):
                    last_up = events[j].Date
                j += 1
            if last_up is not None:
                df.loc[i,"days_since_event"] = (d - last_up).days
    else:
        df["days_since_event"] = np.nan

    # شروط الدخول/الخروج اليومية
    e = cfg["entry"]; x = cfg["exit"]; rsk = cfg["risk"]
    cond_buy = (
        (df["RSI_14"] >= e["rsi_min"]) &
        ((df["Close"] > df["SMA_20"]) if e.get("above_sma20",True) else True) &
        ((df["MACD"] > df["MACD_SIG"]) if e.get("macd_above_signal",True) else True) &
        ((df["dollar_z"] >= e["flow_z_min"]) | df["dollar_z"].isna())
    )
    if e["event_lookback_days"]>0:
        cond_buy &= (df["days_since_event"] <= e["event_lookback_days"]) | df["days_since_event"].isna()

    cond_exit = (
        (df["RSI_14"] < x["rsi_below"]) |
        ((df["Close"] < df["SMA_20"]) if x.get("fall_below_sma20",True) else False) |
        ((df["MACD"] < df["MACD_SIG"]) if x.get("macd_cross_down",True) else False)
    )

    # توليد المراكز (long-only)
    pos = pd.Series(0, index=df.index, dtype=int)
    for i in range(1,len(df)):
        pos.iloc[i] = pos.iloc[i-1]
        if cond_buy.iloc[i-1]:     # دخول مع إشارة أمس
            pos.iloc[i] = 1
        if cond_exit.iloc[i-1]:    # خروج مع إشارة أمس
            pos.iloc[i] = 0

    str_ret = pos * df["ret"]
    eq = (1+str_ret).cumprod()
    bh = (1+df["ret"]).cumprod()
    dd = eq/eq.cummax() - 1.0

    metrics = _ann_stats(str_ret)
    metrics["maxdd"] = float(dd.min())
    out_eq = os.path.join(PROC, f"{symbol}_rules_bt.parquet")
    pd.DataFrame({"Date":df["Date"], "eq":eq, "bh":bh, "pos":pos}).to_parquet(out_eq, index=False)
    out_js = os.path.join(PROC, f"{symbol}_rules_metrics.json")
    with open(out_js,"w",encoding="utf-8") as f: json.dump(metrics, f, ensure_ascii=False)
    return out_eq, out_js, metrics
