import os, json
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import MACD
from ta.volatility import AverageTrueRange

PROC = "/workspace/data/processed"

def _add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("Date").reset_index(drop=True).copy()
    # مؤشرات أساسية
    rsi = RSIIndicator(close=df["Close"], window=14)
    macd = MACD(close=df["Close"], window_slow=26, window_fast=12, window_sign=9)
    atr  = AverageTrueRange(high=df["High"], low=df["Low"], close=df["Close"], window=14)

    df["RSI_14"]    = rsi.rsi()
    df["SMA_20"]    = df["Close"].rolling(20).mean()
    df["SMA_50"]    = df["Close"].rolling(50).mean()
    df["MACD"]      = macd.macd()
    df["MACD_SIG"]  = macd.macd_signal()
    df["MACD_DIFF"] = macd.macd_diff()
    df["ATR_14"]    = atr.average_true_range()

    # عوائد واستراتيجية بسيطة + equity curve
    df["ret"]       = df["Close"].pct_change()
    df["signal"]    = ((df["Close"] > df["SMA_20"]) & (df["RSI_14"] > 50) & (df["MACD"] > df["MACD_SIG"])).astype(int)
    df["pos"]       = df["signal"].shift(1).fillna(0)
    df["str_ret"]   = df["pos"] * df["ret"]
    df["eq_curve"]  = (1.0 + df["str_ret"]).cumprod()
    df["bh_curve"]  = (1.0 + df["ret"]).cumprod()

    # نبضة السيولة (زِد عليها لاحقًا بسهولة)
    df["dollar_vol"] = df["Close"] * df["Volume"]
    mu = df["dollar_vol"].rolling(60).mean()
    sd = df["dollar_vol"].rolling(60).std()
    df["liq_z"] = (df["dollar_vol"] - mu) / (sd.replace(0, np.nan))
    df["liq_pulse"] = df["liq_z"].clip(lower=-3, upper=3)

    return df

def compute_liquidity(symbol: str) -> str:
    """يقرأ prices.parquet لهذا الرمز، يبني الميزات + السيولة، ويحفظ features.parquet"""
    p_prices = os.path.join(PROC, f"{symbol}_prices.parquet")
    assert os.path.exists(p_prices), f"Missing prices: {p_prices}"
    df = pd.read_parquet(p_prices).copy()

    # توحيد أسماء الأعمدة لو كانت مثل Close_2010.SR
    ren = {c: c.split("_")[0] for c in df.columns if c!="Date" and "_" in c}
    df = df.rename(columns=ren)

    need = {"Date","Open","High","Low","Close","Volume"}
    miss = need - set(df.columns)
    if miss:
        raise ValueError(f"Missing columns for {symbol}: {miss}")

    df_feat = _add_features(df)
    out = os.path.join(PROC, f"{symbol}_features.parquet")
    df_feat.to_parquet(out, index=False)
    return out
