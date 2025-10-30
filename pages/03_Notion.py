
import os, subprocess, pandas as pd, streamlit as st

st.set_page_config(page_title="Notion Sync", page_icon="🧩", layout="wide")
st.title("🧩 Notion — مزامنة واستعراض")

OUTDIR = "/workspace/data/processed/notion"
G = os.path.join(OUTDIR, "glossary.csv")
V = os.path.join(OUTDIR, "variables.csv")
T = os.path.join(OUTDIR, "tasks.csv")

col1, col2 = st.columns([1,3])
with col1:
    st.subheader("مزامنة يدوية")
    if st.button("🔄 Sync from Notion"):
        cmd = ["bash","-lc","source /workspace/data/.venv/bin/activate && python /workspace/data/bin/notion_sync.py"]
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
            st.success("تمت المزامنة.")
            st.code(out[-2000:], language="bash")
        except subprocess.CalledProcessError as e:
            st.error("فشل المزامنة.")
            st.code(e.output[-3000:], language="bash")

with col2:
    st.info("تلميح: المزامنة يدوية بالكامل لتقليل استهلاك البيانات. اضغط الزر عند الحاجة.")

st.markdown("---")
st.subheader("Glossary")
if os.path.exists(G):
    st.dataframe(pd.read_csv(G), use_container_width=True, height=260)
else:
    st.warning("لا يوجد glossary.csv بعد")

st.subheader("Variables")
if os.path.exists(V):
    st.dataframe(pd.read_csv(V), use_container_width=True, height=260)
else:
    st.warning("لا يوجد variables.csv بعد")

st.subheader("Tasks")
if os.path.exists(T):
    st.dataframe(pd.read_csv(T), use_container_width=True, height=260)
else:
    st.warning("لا يوجد tasks.csv بعد")
