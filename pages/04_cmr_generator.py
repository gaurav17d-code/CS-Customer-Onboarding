import streamlit as st
import pandas as pd
from database import get_case_by_id, get_all_cases, get_documents_by_case, log_audit
from cmr_mapper import populate_cmr_template
from report_generator import generate_exception_report
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="CMR Generator", page_icon="📊", layout="wide")

st.title("📊 CMR Generator & Exception Report")
st.markdown(
    "Generate the final Customer Master Record (CMR) Excel and produce an exception report."
)
st.markdown("---")

# ── Case selector ───────────────────────────────────────────────────────────────
try:
    all_cases = get_all_cases()
except Exception:
    all_cases = []

if not all_cases:
    st.warning("⚠️ No cases found.")
    st.stop()

case_options = {
    f"{c['case_id']} - {c['customer_name']} ({c['product_type']})": c['case_id']
    for c in all_cases
}

default_key = None
if "selected_case_id" in st.session_state:
    for k, v in case_options.items():
        if v == st.session_state["selected_case_id"]:
            default_key = k
            break

selected_label = st.selectbox(
    "Select Case",
    options=list(case_options.keys()),
    index=list(case_options.keys()).index(default_key) if default_key else 0,
)
case_id = case_options[selected_label]
case = get_case_by_id(case_id)
st.session_state["selected_case_id"] = case_id

if case:
    c1, c2, c3 = st.columns(3)
    c1.metric("Customer", case.get("customer_name", "-"))
    c2.metric("Product Type", case.get("product_type", "-"))
    c3.metric("Status", case.get("status", "-"))

st.markdown("---")

# ── Get documents ───────────────────────────────────────────────────────────────────
try:
    docs = get_documents_by_case(case_id)
except Exception:
    docs = []

if not docs:
    st.info("No documents available for this case. Upload and review documents first.")
    st.stop()

# ── Validate that case is complete ─────────────────────────────────────────────────
case_status = case.get("status", "New")
if case_status != "Complete":
    st.warning(
        f"⚠️ Case status is **{case_status}**. "
        "Please complete document review in the Review Workspace before generating CMR."
    )
    st.info("👉 Navigate to **Review Workspace** to finalize the case.")
    # Allow generation anyway for testing/demo purposes
    st.warning("⚠️ You can still generate a preview CMR/report below for testing.")

st.markdown("---")

# ── CMR Generation ───────────────────────────────────────────────────────────────
st.subheader("📄 Generate CMR Excel")

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

if st.button("🚀 Generate CMR Excel", use_container_width=True):
    with st.spinner("Generating CMR Excel file..."):
        try:
            output_file = populate_cmr_template(case, docs)
            st.success(f"✅ CMR Excel generated successfully: **{output_file}**")

            log_audit(
                case_id=case_id,
                action="CMR_GENERATED",
                performed_by=st.session_state.get("username", "system"),
                details=f"CMR file: {output_file}",
            )

            # Offer download
            if Path(output_file).exists():
                with open(output_file, "rb") as f:
                    st.download_button(
                        label="📥 Download CMR Excel",
                        data=f,
                        file_name=Path(output_file).name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
        except Exception as exc:
            st.error(f"❌ CMR generation failed: {exc}")

st.markdown("---")

# ── Exception Report ─────────────────────────────────────────────────────────────────
st.subheader("⚠️ Generate Exception Report")
st.markdown(
    "This report highlights missing documents, rejected items, and cross-verification conflicts."
)

if st.button("📄 Generate Exception Report", use_container_width=True):
    with st.spinner("Generating exception report..."):
        try:
            report_file = generate_exception_report(case, docs)
            st.success(f"✅ Exception report generated: **{report_file}**")

            log_audit(
                case_id=case_id,
                action="EXCEPTION_REPORT_GENERATED",
                performed_by=st.session_state.get("username", "system"),
                details=f"Report file: {report_file}",
            )

            # Offer download
            if Path(report_file).exists():
                with open(report_file, "rb") as f:
                    st.download_button(
                        label="📥 Download Exception Report (PDF)",
                        data=f,
                        file_name=Path(report_file).name,
                        mime="application/pdf",
                        use_container_width=True,
                    )
        except Exception as exc:
            st.error(f"❌ Exception report generation failed: {exc}")

st.markdown("---")

# ── Documents summary ──────────────────────────────────────────────────────────────
st.subheader("📊 Document Summary")
if docs:
    df = pd.DataFrame(docs)
    show_cols = ["doc_id", "file_name", "doc_type", "status"]
    existing = [c for c in show_cols if c in df.columns]
    st.dataframe(df[existing], use_container_width=True, height=250)
else:
    st.info("No documents attached to this case.")
