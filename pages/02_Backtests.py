
import os, glob, json, pandas as pd, streamlit as st

st.set_page_config(page_title="Backtests", page_icon="📈", layout="wide")
st.title("📈 Backtests — ملخّص تراكمي + تفاصيل")

PROC="/workspace/data/processed"
bs = os.path.join(PROC, "backtest_summary.csv")
if not os.path.exists(bs):
    st.info("لا يوجد backtest_summary.csv بعد.")
else:
    df = pd.read_csv(bs)
df.columns = [c.strip() for c in df.columns]
if 'symbol' not in df.columns:
    for c in list(df.columns):
        if c.lower() in ('symbol','ticker'):
            df = df.rename(columns={c:'symbol'})
            break

    # ربط بالدول (إن وُجدت ملفات profile)
    countries = {}
    for jf in glob.glob(os.path.join(PROC, "*_profile.json")):
        try:
            j = json.load(open(jf,"r",encoding="utf-8"))
            sym=j.get("symbol")
            c  = j.get("country") or "—"
            if sym: countries[sym]=c
        except Exception:
            pass
    if countries:
        df["country"]=df["symbol"].map(countries).fillna("—")
        filt = ["الكل"] + sorted(set(df["country"]) - {"—"}) + (["—"] if "—" in set(df["country"]) else [])
        pick = st.selectbox("فلترة حسب الدولة/السوق", filt, index=0)
        if pick != "الكل":
            df = df[df["country"]==pick]
    st.dataframe(df, use_container_width=True, height=350)

    st.markdown("---")
    st.subheader("تفاصيل رمز")
    symbols_sorted = sorted(df["symbol"].unique().tolist())
    sym = st.selectbox("اختر الرمز", symbols_sorted, index=0)
    rm  = os.path.join(PROC, f"{sym}_rules_metrics.json")
    bt  = os.path.join(PROC, f"{sym}_bt.parquet")
    if os.path.exists(rm):
        j=json.load(open(rm,"r",encoding="utf-8"))
        c1,c2,c3 = st.columns(3)
        c1.metric("CAGR", f"{j.get('CAGR',0)*100:.2f}%")
        c2.metric("MaxDD", f"{j.get('MaxDD',0)*100:.1f}%")
        c3.metric("Vol",   f"{j.get('Vol',0)*100:.1f}%")
    else:
        st.caption("ملخّص غير متاح.")
    if os.path.exists(bt):
        st.caption("منحنى Equity موجود (ملف bt.parquet) — سنضيف الرسم لاحقًا.")
    else:
        st.caption("لا يوجد bt.parquet لهذا الرمز بعد.")
