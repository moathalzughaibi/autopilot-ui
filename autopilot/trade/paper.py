
import os, json, math
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, Tuple

BASE = "/workspace/data"
PROC = f"{BASE}/processed"
CFG  = f"{BASE}/autopilot/config/trade.yaml"

def _load_yaml(path):
    import yaml
    return yaml.safe_load(open(path, "r", encoding="utf-8"))

def _jsonify(x):
    import numpy as _np
    import pandas as _pd
    from datetime import datetime as _dt
    if isinstance(x, (_np.floating, float)): return float(x)
    if isinstance(x, (_np.integer, int)):   return int(x)
    if isinstance(x, (_pd.Timestamp, _dt)): return x.strftime("%Y-%m-%d")
    if x is None: return None
    if x != x: return None  # NaN
    return x

def _prices_last_row(sym) -> Dict[str, Any]:
    p = os.path.join(PROC, f"{sym}_features.parquet")
    if not os.path.exists(p):
        p = os.path.join(PROC, f"{sym}_prices.parquet")
    if not os.path.exists(p): return {}
    df = pd.read_parquet(p).sort_values("Date").reset_index(drop=True)
    return df.iloc[-1].to_dict() if not df.empty else {}

def _load_ledger() -> pd.DataFrame:
    p = os.path.join(PROC, "trades_ledger.parquet")
    if os.path.exists(p): return pd.read_parquet(p)
    cols = ["Date","Symbol","Side","Qty","Entry","Stop","Take","Exit","ExitReason","Status","PnL"]
    return pd.DataFrame(columns=cols)

def _save_ledger(df: pd.DataFrame):
    df.to_parquet(os.path.join(PROC,"trades_ledger.parquet"), index=False)

def _load_account():
    p = os.path.join(PROC,"trades_account.json")
    if os.path.exists(p):
        try: return json.load(open(p, "r"))
        except Exception: return None
    return None

def _save_account(acc: dict):
    acc2 = {k: _jsonify(v) for k,v in acc.items()}
    import json, os
    json.dump(acc2, open(os.path.join(PROC,"trades_account.json"),"w"),
              ensure_ascii=False, indent=2)

def _append_equity(day: str, cash: float, equity: float):
    import pandas as pd, os
    fp = os.path.join(PROC, "trades_equity.parquet")
    row = pd.DataFrame([{"Date": pd.to_datetime(day), "cash": float(cash), "equity": float(equity)}])
    if os.path.exists(fp):
        df = pd.read_parquet(fp)
        df = pd.concat([df, row], ignore_index=True)
        df = df.sort_values("Date").drop_duplicates(subset=["Date"], keep="last").reset_index(drop=True)
    else:
        df = row
    df.to_parquet(fp, index=False)

def _equity_now(acc_cash: float, open_pos: pd.DataFrame, last_prices: Dict[str,float]) -> float:
    val = float(acc_cash)
    for _,r in open_pos.iterrows():
        px = last_prices.get(r["Symbol"])
        if px is None or px != px: continue
        val += float(r["Qty"]) * float(px)
    return float(val)

def _place_buy(ledger: pd.DataFrame, sym: str, qty: int, price: float, stop=None, take=None, when=None) -> pd.DataFrame:
    when = when or datetime.utcnow().strftime("%Y-%m-%d")
    row = dict(Date=when, Symbol=sym, Side="LONG", Qty=int(qty), Entry=float(price),
               Stop=(None if stop is None else float(stop)),
               Take=(None if take is None else float(take)),
               Exit=None, ExitReason=None, Status="OPEN", PnL=None)
    return pd.concat([ledger, pd.DataFrame([row])], ignore_index=True)

def _close_position(ledger: pd.DataFrame, sym: str, price: float, reason="RULE_EXIT", when=None) -> Tuple[pd.DataFrame, float, int]:
    when = when or datetime.utcnow().strftime("%Y-%m-%d")
    mask = (ledger["Symbol"]==sym) & (ledger["Status"]=="OPEN")
    if not mask.any(): 
        return ledger, 0.0, 0
    idx  = ledger[mask].index[-1]
    qty  = int(ledger.loc[idx,"Qty"])
    entry= float(ledger.loc[idx,"Entry"])
    pnl  = (float(price) - entry) * qty
    ledger.loc[idx,"Exit"]       = float(price)
    ledger.loc[idx,"ExitReason"] = reason
    ledger.loc[idx,"Status"]     = "CLOSED"
    ledger.loc[idx,"PnL"]        = float(pnl)
    ledger.loc[idx,"Date"]       = when
    return ledger, float(pnl), qty

def daily_run(symbols):
    cfg     = _load_yaml(CFG)
    port    = cfg["portfolio"]
    sizing  = cfg["sizing"]
    policy  = cfg["policy"]

    acc = _load_account() or dict(cash=float(port["initial_cash"]), equity=float(port["initial_cash"]), last_date=None)
    ledger = _load_ledger()

    last_rows   = {s:_prices_last_row(s) for s in symbols}
    last_prices = {s:(None if not last_rows[s] else float(last_rows[s].get("Close", np.nan))) for s in symbols}
    atrs        = {s:(None if not last_rows[s] else float(last_rows[s].get("ATR_14", np.nan))) for s in symbols}

    decs = {}
    for s in symbols:
        p = os.path.join(PROC, f"{s}_decision.json")
        decs[s] = json.load(open(p,"r")) if os.path.exists(p) else {}

    open_pos = ledger[ledger["Status"]=="OPEN"].copy()

    # أخرج أولاً إن لزم
    for s in symbols:
        dec = decs.get(s,{}).get("decision")
        px  = last_prices.get(s)
        if px is None or px != px: 
            continue
        if dec == policy.get("exit_on","SELL"):
            if not open_pos[open_pos["Symbol"]==s].empty:
                ledger, pnl, q = _close_position(ledger, s, price=px, reason="RULE_EXIT")
                acc["cash"] = float(acc["cash"] + float(px) * int(q))
                open_pos = ledger[ledger["Status"]=="OPEN"].copy()

    # ثم ادخل إن لزم وبحدود المخاطر
    for s in symbols:
        dec = decs.get(s,{}).get("decision")
        px  = last_prices.get(s)
        if px is None or px != px: 
            continue
        if dec == policy.get("entry_on","BUY") and policy.get("allow_shorts", False) is False:
            if open_pos[open_pos["Symbol"]==s].empty and open_pos.shape[0] < int(port.get("max_open_positions", 10)):
                risk_amt = float(acc["cash"] * float(port["risk_per_trade"]))
                atr = atrs.get(s)
                if atr is not None and atr==atr and float(atr)>0:
                    stop_dist = float(atr) * float(sizing.get("atr_multiple",2.5))
                else:
                    stop_dist = float(px) * 0.04
                shares = max(1, int(math.floor(risk_amt / max(stop_dist,1e-9))))
                shares = min(shares, int(acc["cash"] // px))
                if shares >= 1:
                    stop = px - stop_dist
                    take = px + (stop_dist * 2.0)
                    acc["cash"] = float(acc["cash"] - shares * px)
                    ledger = _place_buy(ledger, s, shares, px, stop, take)
                    open_pos = ledger[ledger["Status"]=="OPEN"].copy()

    acc["equity"]    = _equity_now(acc["cash"], open_pos, last_prices)
    # last_date قد تكون Timestamp — نحولها لنص
    dates = [r.get("Date") for r in last_rows.values() if r.get("Date") is not None]
    if dates:
        try:
            from pandas import to_datetime
            acc["last_date"] = to_datetime(max(dates)).strftime("%Y-%m-%d")
        except Exception:
            acc["last_date"] = str(max(dates))
    _save_ledger(ledger)
    _save_account(acc)
    return dict(cash=acc["cash"], equity=acc["equity"], open=int(open_pos.shape[0]))
