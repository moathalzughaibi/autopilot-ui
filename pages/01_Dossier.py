
import os, glob, json, pandas as pd, streamlit as st

st.set_page_config(page_title="Dossier", page_icon="📁", layout="wide")
st.title("📁 Dossier — ملف السهم")

PROC="/workspace/data/processed"

def _syms():
    xs = sorted([os.path.basename(p).split("_")[0] for p in glob.glob(os.path.join(PROC,"*_latest_signal.json"))])
    return xs or ["2010.SR"]

def _j(p, default=None):
    try: return json.load(open(p,"r",encoding="utf-8"))
    except: return default if default is not None else {}

def _parq(p):
    import pandas as pd
    try:
        return pd.read_parquet(p)
    except:
        return pd.DataFrame()

syms = _syms()
sym = st.selectbox("اختر الرمز", syms, index=0)

c1,c2,c3,c4 = st.columns(4)
profile = _j(os.path.join(PROC, f"{sym}_profile.json"), {})
name = profile.get("name") or sym
c1.metric("الاسم", name)
c2.metric("الدولة", profile.get("country","—"))
c3.metric("القطاع", profile.get("sector","—"))
c4.metric("تاريخ الإدراج", profile.get("listing_date","—"))

# تقني / قرار / تقييم
mtf   = _j(os.path.join(PROC, f"{sym}_mtf.json"), {})
dec   = _j(os.path.join(PROC, f"{sym}_decision.json"), {})
rules = _j(os.path.join(PROC, f"{sym}_rules_metrics.json"), {})
val   = _j(os.path.join(PROC, f"{sym}_valuation.json"), {})

st.markdown("### 📊 الفني (MTF & Decision)")
cc1,cc2,cc3,cc4 = st.columns(4)
cc1.metric("Daily",  str(mtf.get("daily","—")))
cc2.metric("Weekly", str(mtf.get("weekly","—")))
cc3.metric("Monthly",str(mtf.get("monthly","—")))
cc4.metric("Composite",str(mtf.get("composite","—")))
dc = dec.get("decision","—")
cc1,cc2,cc3 = st.columns(3)
cc1.metric("Decision", dc)
cc2.metric("Stop", f"{dec.get('stop'):.2f}" if isinstance(dec.get('stop'),(int,float)) else "—")
cc3.metric("Take", f"{dec.get('take'):.2f}" if isinstance(dec.get('take'),(int,float)) else "—")

st.markdown("### 💰 التقييم (Fair Value)")
fv = val.get("fair_value")
if isinstance(fv,(int,float)):
    # نحاول استخراج آخر إغلاق للعرض فقط
    close = None
    for cand in (f"{sym}_features.parquet", f"{sym}_prices.parquet"):
        p=os.path.join(PROC,cand)
        if os.path.exists(p):
            df=_parq(p).sort_values("Date")
            if "Close" in df.columns and len(df): close=float(df["Close"].iloc[-1]); break
    underr = (fv/close-1.0) if close else None
    st.metric("Fair Value", f"{fv:.2f}")
    st.metric("Under/Over", f"{underr*100:.1f}%" if isinstance(underr,(int,float)) else "—")
else:
    st.info("لا تتوفر قيمة تقديرية بعد.")

st.markdown("### 🧾 المالية — ربعي/سنوي")
fq = _parq(os.path.join(PROC, f"{sym}_fin_quarterly.parquet"))
fy = _parq(os.path.join(PROC, f"{sym}_fin_yearly.parquet"))
if len(fq):
    st.caption("Quarterly")
    st.dataframe(fq.tail(12), use_container_width=True, height=240)
if len(fy):
    st.caption("Yearly (ملخص)")
    st.dataframe(fy.tail(5), use_container_width=True, height=200)
if not len(fq) and not len(fy):
    st.info("لا توجد بيانات مالية مرفوعة بعد (استخدم Control Panel).")

st.markdown("### 💵 توزيعات الأرباح")
divs = _parq(os.path.join(PROC, f"{sym}_dividends.parquet"))
if len(divs):
    st.dataframe(divs.tail(10), use_container_width=True, height=220)
else:
    st.caption("لا يوجد سجل توزيعات.")

st.markdown("### 🧩 الإجراءات الرأسمالية")
corp = _parq(os.path.join(PROC, f"{sym}_corp_actions.parquet"))
if len(corp):
    st.dataframe(corp.tail(20), use_container_width=True, height=220)
else:
    st.caption("لا يوجد سجل إجراءات.")

st.markdown("### ⚖️ الشريعة & 🚨 التنبيهات")
sha = _j(os.path.join(PROC, f"{sym}_shariah.json"), {})
al  = _j(os.path.join(PROC, f"{sym}_alerts.json"), {"alerts":[]})
c1,c2 = st.columns(2)
c1.metric("Shariah", sha.get("status","—"))
c2.metric("Alerts", len(al.get("alerts",[])))

st.markdown("### 📰 الأخبار")
news = _j(os.path.join(PROC, f"{sym}_news.json"), {"items":[]}).get("items",[])
if news:
    for it in news[:8]:
        st.write(f"- [{it.get('title','خبر')}]({it.get('link','#')}) — {it.get('published','')}")
else:
    st.caption("لا يوجد أخبار محفوظة.")

st.markdown("### 📝 Journal")
try:
    from autopilot.journal.logger import add_event as _add_journal, load_journal as _load_journal
    c1,c2 = st.columns([3,1])
    note = c1.text_input("ملاحظة", "")
    et   = c2.selectbox("النوع", ["note","catalyst","mgmt","regulatory","rumor","earnings","other"])
    t    = st.text_input("وسوم (comma-separated)", "")
    if st.button("إضافة"):
        _add_journal(sym, etype=et, note=note, tags=t)
        st.toast("تمت الإضافة ✅")
    j = _load_journal(sym).get("events",[])
    if j:
        import pandas as _pd
        df=_pd.DataFrame(j); df["date"]=_pd.to_datetime(df["date"])
        st.dataframe(df.sort_values("date",ascending=False), use_container_width=True, height=240)
    else:
        st.caption("لا توجد ملاحظات.")
except Exception as e:
    st.caption(f"Journal غير متاح الآن: {e}")
