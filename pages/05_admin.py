import streamlit as st
import pandas as pd
from database import get_all_cases, get_audit_log, get_db_connection
from datetime import datetime

st.set_page_config(page_title="Admin Dashboard", page_icon="⚙️", layout="wide")

st.title("⚙️ Admin Dashboard")
st.markdown("Monitor system activity, audit logs, and case statistics.")
st.markdown("---")

# ── Summary metrics ─────────────────────────────────────────────────────────────
st.subheader("📈 System Statistics")

try:
    all_cases = get_all_cases()
except Exception:
    all_cases = []

total_cases = len(all_cases)
if all_cases:
    df = pd.DataFrame(all_cases)
    new_count = len(df[df["status"] == "New"])
    in_review = len(df[df["status"] == "In Review"])
    complete = len(df[df["status"] == "Complete"])
else:
    new_count = in_review = complete = 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Cases", total_cases)
c2.metric("New", new_count)
c3.metric("In Review", in_review)
c4.metric("Complete", complete)

st.markdown("---")

# ── All cases table ─────────────────────────────────────────────────────────────────
st.subheader("📊 All Cases")
if all_cases:
    df = pd.DataFrame(all_cases)
    show_cols = [
        "case_id",
        "customer_name",
        "product_type",
        "status",
        "created_at",
        "updated_at",
    ]
    existing = [c for c in show_cols if c in df.columns]
    st.dataframe(
        df[existing].sort_values("created_at", ascending=False),
        use_container_width=True,
        height=300,
    )
else:
    st.info("No cases found.")

st.markdown("---")

# ── Audit log ──────────────────────────────────────────────────────────────────────
st.subheader("📜 Audit Log")
st.markdown(
    "All system actions are logged here for traceability and compliance."
)

try:
    audit_log = get_audit_log(limit=100)
except Exception:
    audit_log = []

if audit_log:
    df_audit = pd.DataFrame(audit_log)
    show_cols_audit = [
        "audit_id",
        "case_id",
        "action",
        "performed_by",
        "timestamp",
        "details",
    ]
    existing_audit = [c for c in show_cols_audit if c in df_audit.columns]
    st.dataframe(
        df_audit[existing_audit].sort_values("timestamp", ascending=False),
        use_container_width=True,
        height=350,
    )
else:
    st.info("No audit logs found.")

st.markdown("---")

# ── Database diagnostics ───────────────────────────────────────────────────────────
st.subheader("🔧 Database Diagnostics")

try:
    conn = get_db_connection()
    cursor = conn.cursor()

    # Count documents
    cursor.execute("SELECT COUNT(*) FROM documents")
    doc_count = cursor.fetchone()[0]

    # Count audit logs
    cursor.execute("SELECT COUNT(*) FROM audit_log")
    audit_count = cursor.fetchone()[0]

    conn.close()

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Total Documents", doc_count)
    col_b.metric("Audit Log Entries", audit_count)
    col_c.metric("Database", "onboarding.db")
except Exception as exc:
    st.error(f"Database diagnostics failed: {exc}")

st.markdown("---")
st.caption(
    f"🕒 Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)
