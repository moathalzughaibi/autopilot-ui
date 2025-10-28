
import os, json, pandas as pd, streamlit as st
st.set_page_config(page_title="Control Panel", page_icon="🛠️", layout="wide")
st.title("🛠️ Control Panel — لوحـة التحكّم")
PROC="/workspace/data/processed"; INP="/workspace/data/input"; os.makedirs(INP, exist_ok=True)
from autopilot.admin.ingest import ingest_any

def _save_and_ingest(label, key, fname):
    f = st.file_uploader(label, type=["csv"], key=key)
    if f is not None:
        path = os.path.join(INP, fname)
        with open(path,"wb") as out: out.write(f.getbuffer())
        tag = ingest_any(path)
        st.success(f"تم الإدخال: {path} → {tag}")
        try:
            st.dataframe(pd.read_csv(path).head(20), use_container_width=True)
        except Exception as e:
            st.info(f"تم الحفظ (CSV قد لا يُعرض): {e}")

col1, col2 = st.columns(2)
with col1:
    st.subheader("Profiles")
    _save_and_ingest("ارفع profiles.csv", "profiles", "profiles.csv")
    st.caption("FORMAT: symbol,name,listing_date,exchange,sector,industry,country")
    st.subheader("Dividends")
    _save_and_ingest("ارفع dividends.csv", "divs", "dividends.csv")
    st.caption("FORMAT: symbol,ex_date,record_date,pay_date,amount,currency,type")
with col2:
    st.subheader("Quarterly Financials")
    _save_and_ingest("ارفع financials_quarterly.csv", "finq", "financials_quarterly.csv")
    st.caption("FORMAT: symbol,period_end,fiscal_q,fiscal_y,revenue,operating_income,net_income,eps,assets,liabilities,equity,cfo,capex,dividends_paid")
    st.subheader("Corporate Actions")
    _save_and_ingest("ارفع corporate_actions.csv", "corp", "corporate_actions.csv")
    st.caption("FORMAT: symbol,action_date,action_type,ratio,notes")

st.markdown("---")
st.subheader("تشغيل تحديث شامل (اختياري)")
if st.button("تشغيل update_all.py الآن"):
    import subprocess, sys
    try:
        out = subprocess.check_output([sys.executable, "/workspace/data/autopilot/jobs/update_all.py"], stderr=subprocess.STDOUT, text=True)
        st.code(out[-4000:], language="bash")
        st.success("تم التشغيل.")
    except subprocess.CalledProcessError as e:
        st.error("فشل التنفيذ")
        st.code(e.output[-4000:], language="bash")
