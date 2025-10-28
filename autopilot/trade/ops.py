
import os, pandas as pd, numpy as np
from datetime import datetime
from . import paper as P  # نعيد استخدام وظائف التحميل/الحفظ

def open_long(symbol: str, qty: int, price: float | None = None):
    acc = P._load_account() or dict(cash=100000.0, equity=100000.0, last_date=None)
    led = P._load_ledger()
    last = P._prices_last_row(symbol)
    px = float(price if price is not None else last.get("Close", np.nan))
    if px!=px: raise ValueError("no price")
    if acc["cash"] < qty*px: raise ValueError("insufficient cash")
    # افتراض وقف/هدف بسيطين
    atr = float(last.get("ATR_14", np.nan))
    stop_dist = (atr*2.5 if atr==atr and atr>0 else px*0.04)
    stop = px - stop_dist
    take = px + 2*stop_dist
    acc["cash"] = float(acc["cash"] - qty*px)
    led = P._place_buy(led, symbol, qty, px, stop, take)
    P._save_ledger(led)
    acc["equity"] = P._equity_now(acc["cash"], led[led["Status"]=="OPEN"], {symbol:px})
    # تاريخ اليوم/آخر تاريخ متاح
    d = last.get("Date")
    if d is None:
        d = datetime.utcnow().strftime("%Y-%m-%d")
    else:
        try:
            d = pd.to_datetime(d).strftime("%Y-%m-%d")
        except Exception:
            d = str(d)
    acc["last_date"] = d
    P._save_account(acc)
    P._append_equity(d, acc["cash"], acc["equity"])
    return dict(ok=True, cash=acc["cash"], equity=acc["equity"])

def close_all(symbol: str, price: float | None = None):
    acc = P._load_account() or dict(cash=100000.0, equity=100000.0, last_date=None)
    led = P._load_ledger()
    last = P._prices_last_row(symbol)
    px = float(price if price is not None else last.get("Close", np.nan))
    if px!=px: raise ValueError("no price")
    led, pnl, qty = P._close_position(led, symbol, px, reason="MANUAL")
    P._save_ledger(led)
    acc["cash"] = float(acc["cash"] + pnlsum(led, symbol, px))  # تصحيح شامل للكاش
    # حساب equity
    open_pos = led[led["Status"]=="OPEN"].copy()
    acc["equity"] = P._equity_now(acc["cash"], open_pos, {symbol:px})
    # تاريخ
    d = last.get("Date")
    if d is None:
        d = datetime.utcnow().strftime("%Y-%m-%d")
    else:
        try:
            d = pd.to_datetime(d).strftime("%Y-%m-%d")
        except Exception:
            d = str(d)
    acc["last_date"] = d
    P._save_account(acc)
    P._append_equity(d, acc["cash"], acc["equity"])
    return dict(ok=True, cash=acc["cash"], equity=acc["equity"], closed_qty=int(qty))

def pnlsum(ledger: pd.DataFrame, sym: str, px: float) -> float:
    # اجمع الكلفة/العائد للصفقات المغلقة حديثًا (حالات بسيطة)
    df = ledger[(ledger["Symbol"]==sym) & (ledger["Status"]=="CLOSED")].copy()
    if df.empty: return 0.0
    df["PnL"] = df["PnL"].astype(float)
    return float(df["PnL"].iloc[-1])
