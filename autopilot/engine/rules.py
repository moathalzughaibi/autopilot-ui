
import os, yaml, json, numpy as np, pandas as pd
from datetime import timedelta

PROC   = "/workspace/data/processed"
CONFIG = "/workspace/data/autopilot/config/rules.yaml"

def _load_yaml(path=CONFIG):
    import yaml
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def _last_row(df):
    return df.iloc[-1].to_dict() if not df.empty else {}

def _days_since_last_event(ev: pd.DataFrame, types=("UP",), asof=None):
    if ev.empty: return None
    e = ev[ev["type"].isin(types)]
    if e.empty: return None
    d = pd.to_datetime(asof) if asof is not None else pd.to_datetime(e["Date"].max())
    last_ev = pd.to_datetime(e["Date"].max())
    return (d - last_ev).days

def decide_today(symbol: str, cfg: dict | None = None):
    cfg = cfg or _load_yaml()

    # --- read features
    fp = os.path.join(PROC, f"{symbol}_features.parquet")
    if not os.path.exists(fp): 
        return {"symbol":symbol,"decision":"FLAT","reason":["no features"]}
    feat = pd.read_parquet(fp).sort_values("Date").reset_index(drop=True)

    # --- read flow
    ff = os.path.join(PROC, f"{symbol}_flow.parquet")
    flow = pd.read_parquet(ff) if os.path.exists(ff) else pd.DataFrame()

    # --- read cases
    fc = os.path.join(PROC, f"{symbol}_cases.parquet")
    cases = pd.read_parquet(fc) if os.path.exists(fc) else pd.DataFrame()

    last = _last_row(feat)
    reasons = []
    decision = "FLAT"

    # guards
    for col in ("Close","SMA_20","RSI_14","MACD","MACD_SIG","ATR_14"):
        if col not in feat.columns:
            return {"symbol":symbol,"decision":"FLAT","reason":[f"missing {col}"]}

    close  = float(last["Close"])
    sma20  = float(last["SMA_20"])
    rsi    = float(last["RSI_14"])
    macd   = float(last["MACD"])
    macsig = float(last["MACD_SIG"])
    atr    = float(last["ATR_14"]) if pd.notna(last["ATR_14"]) else np.nan

    flow_z = None
    if not flow.empty and "dollar_z" in flow.columns:
        flow_z = float(flow["dollar_z"].iloc[-1])

    # entry conditions (long-only v1)
    ok_rsi   = (rsi >= cfg["entry"]["rsi_min"]);                  reasons += [f"RSI≥{cfg['entry']['rsi_min']} = {ok_rsi}"]
    ok_sma20 = (close > sma20) if cfg["entry"].get("above_sma20",True) else True;  reasons += [f"Close>SMA20 = {ok_sma20}"]
    ok_macd  = (macd > macsig) if cfg["entry"].get("macd_above_signal",True) else True; reasons += [f"MACD>Signal = {ok_macd}"]
    ok_flow  = True
    if flow_z is not None:
        ok_flow = (flow_z >= cfg["entry"]["flow_z_min"]);         reasons += [f"flow_z≥{cfg['entry']['flow_z_min']} = {ok_flow}"]
    else:
        reasons += ["flow_z N/A"]

    days_ev = _days_since_last_event(cases, tuple(cfg["entry"]["event_allow"]), asof=feat["Date"].iloc[-1])
    ok_ev   = True if days_ev is None else (days_ev <= cfg["entry"]["event_lookback_days"])
    reasons += [f"recent_event≤{cfg['entry']['event_lookback_days']}d = {ok_ev}"]

    bullish = ok_rsi and ok_sma20 and ok_macd and ok_flow and ok_ev

    # exit hints (للعرض – الباك-تست هو الذي يطبّقها فعلياً)
    ex_rsi  = (rsi < cfg["exit"]["rsi_below"]);             reasons += [f"RSI<{cfg['exit']['rsi_below']} = {ex_rsi}"]
    ex_sma  = (close < sma20) if cfg["exit"].get("fall_below_sma20",True) else False;  reasons += [f"Close<SMA20 = {ex_sma}"]
    ex_macd = (macd < macsig) if cfg["exit"].get("macd_cross_down",True) else False;   reasons += [f"MACD<Signal = {ex_macd}"]

    if bullish:
        decision = "BUY"
    elif ex_rsi or ex_sma or ex_macd:
        decision = "SELL"
    else:
        decision = "FLAT"

    stop = close - cfg["risk"]["stop_atr"]*atr if np.isfinite(atr) else None
    take = close + cfg["risk"]["take_atr"]*atr if np.isfinite(atr) else None

    out = dict(symbol=symbol, decision=decision, close=close, rsi=rsi, macd=macd,
               flow_z=flow_z, days_since_event=days_ev, stop=stop, take=take,
               reason=reasons, asof=str(feat["Date"].iloc[-1]))
    # تخزين قرار اليوم
    with open(os.path.join(PROC, f"{symbol}_decision.json"),"w",encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    return out
