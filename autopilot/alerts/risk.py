
import os, json, numpy as np, pandas as pd, yaml

BASE = "/workspace/data"
PROC = f"{BASE}/processed"
CFG  = f"{BASE}/autopilot/config/risk_alerts.yaml"

def _load_cfg():
    return yaml.safe_load(open(CFG,"r",encoding="utf-8"))

def _zscore(s, win=60):
    r = s.rolling(win).mean(); v = s.rolling(win).std(ddof=0)
    return (s - r) / v

def compute_risk_alerts(symbol: str) -> dict:
    cfg = _load_cfg(); th = cfg.get("thresholds", {}); lb = cfg.get("lookbacks", {})
    fp = os.path.join(PROC, f"{symbol}_features.parquet")
    if not os.path.exists(fp): return {"symbol": symbol, "asof": None, "alerts": []}

    df = pd.read_parquet(fp).sort_values("Date").reset_index(drop=True)
    if df.empty: return {"symbol": symbol, "asof": None, "alerts": []}

    if "dollar_vol" not in df.columns and {"Close","Volume"}.issubset(df.columns):
        df["dollar_vol"] = df["Close"] * df["Volume"]

    last = df.iloc[-1]; asof = str(pd.to_datetime(last["Date"]).date())
    alerts = []

    # 1) فجوة يومية
    if {"Open","Close"}.issubset(df.columns) and len(df) >= 2:
        prev_close = float(df["Close"].iloc[-2]) if pd.notna(df["Close"].iloc[-2]) else np.nan
        if prev_close and prev_close == prev_close and prev_close > 0:
            gap = abs(float(last["Open"]) - prev_close) / prev_close
            if gap == gap and gap >= th.get("gap_pct", 0.04):
                alerts.append({"type":"gap","sev":"warning","msg":f"فجوة {gap:.1%}","value":round(gap,4)})

    # 2) ATR spike
    if "ATR_14" in df.columns:
        atr = df["ATR_14"]; ma = atr.rolling(60).mean()
        base = ma.iloc[-1] if len(ma) else np.nan
        if base and base == base and base > 0:
            ratio = float(atr.iloc[-1] / base)
            if ratio == ratio and ratio >= th.get("atr_spike", 1.8):
                alerts.append({"type":"atr_spike","sev":"warning","msg":f"ATR spike ×{ratio:.2f}","value":round(ratio,2)})

    # 3) Illiquidity (حجم ضعيف)
    if "Volume" in df.columns:
        vol_sma = df["Volume"].rolling(20).mean().iloc[-1]
        if vol_sma and vol_sma == vol_sma and vol_sma > 0 and float(last["Volume"]) < th.get("illiq_vol_ratio",0.30)*vol_sma:
            alerts.append({"type":"illiquidity","sev":"info","msg":"حجم أقل بكثير من المعتاد"})

    # 4) قرب الوقف (تقريبيًا حسب ATR)
    if {"Close","ATR_14"}.issubset(df.columns):
        if pd.notna(last["ATR_14"]) and float(last["ATR_14"]) > 0:
            stop = float(last["Close"]) - 2.5 * float(last["ATR_14"])
            dist = (float(last["Close"]) - stop) / float(last["ATR_14"])
            if dist == dist and dist <= th.get("near_stop_atr", 0.50):
                alerts.append({"type":"near_stop","sev":"warning","msg":f"قريب من الوقف ({dist:.2f}×ATR)","value":round(dist,2)})

    # 5) Z-score لتدفّق الدولار
    if "dollar_vol" in df.columns:
        z = _zscore(df["dollar_vol"], 60).iloc[-1]
        if z == z and z >= th.get("z_dollar", 2.0):
            alerts.append({"type":"dollar_flow","sev":"warning","msg":f"تدفّق نقدي مرتفع (Z={float(z):.2f})","value":round(float(z),2)})

    # 6) أرباح قريبة (تعامل مع NaN بأمان)
    cases_p = os.path.join(PROC, f"{symbol}_cases.parquet")
    if os.path.exists(cases_p):
        ce = pd.read_parquet(cases_p)
        if "earnings_days" in ce.columns and not ce.empty:
            ed = pd.to_numeric(ce["earnings_days"], errors="coerce").dropna()
            if not ed.empty:
                near = float(ed.abs().min())
                if np.isfinite(near) and near <= th.get("earnings_days", 5):
                    alerts.append({"type":"earnings","sev":"info","msg":f"أرباح قريبة (±{int(round(near))} يوم)","value":int(round(near))})

    out = {"symbol": symbol, "asof": asof, "alerts": alerts}

    # حفظ JSON
    json.dump(out, open(os.path.join(PROC, f"{symbol}_alerts.json"), "w"), ensure_ascii=False, indent=2)

    # سجل تاريخي
    hist_p = os.path.join(PROC, "alerts_history.parquet")
    row = pd.DataFrame([{
        "Date": pd.to_datetime(asof),
        "Symbol": symbol,
        "n_alerts": len(alerts),
        "types": ",".join(a["type"] for a in alerts) if alerts else ""
    }])
    if os.path.exists(hist_p):
        h = pd.read_parquet(hist_p)
        h = pd.concat([h, row], ignore_index=True)
        h = h.sort_values(["Symbol","Date"]).drop_duplicates(subset=["Symbol","Date"], keep="last").reset_index(drop=True)
    else:
        h = row
    h.to_parquet(hist_p, index=False)
    return out
