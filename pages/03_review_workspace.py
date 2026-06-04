import streamlit as st
import json
import pandas as pd
from database import (
    get_case_by_id, get_all_cases, get_documents_by_case,
    update_document_field, log_audit, update_case_status
)
from rules_engine import validate_checklist
from cross_verifier import cross_verify_data
import base64
from pathlib import Path

st.set_page_config(page_title="Review Workspace", page_icon="🔍", layout="wide")

st.title("🔍 Review Workspace")
st.markdown("Evidence-first review: Validate extracted data, verify checklist, and approve or reject documents.")
st.markdown("---")

# ── Case selector ────────────────────────────────────────────────────────────────
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
    c3.metric("Status", case.get("status", "-"), delta=None)

st.markdown("---")

# ── Get documents and run checklist validation ──────────────────────────────────
try:
    docs = get_documents_by_case(case_id)
except Exception:
    docs = []

product_type = case.get("product_type", "Bitumen")

try:
    checklist_result = validate_checklist(product_type, docs)
    cross_check_result = cross_verify_data(docs)
except Exception as e:
    st.error(f"Validation failed: {e}")
    checklist_result = {"checklist": [], "missing": []}
    cross_check_result = {"conflicts": []}

# ── Checklist Status ──────────────────────────────────────────────────────────
st.subheader("✅ Checklist Status")
checklist_items = checklist_result.get("checklist", [])
missing_items = checklist_result.get("missing", [])

if checklist_items:
    df_checklist = pd.DataFrame(checklist_items)
    st.dataframe(df_checklist, use_container_width=True, height=200)
else:
    st.info("No checklist items defined for this product type.")

if missing_items:
    st.warning(f"⚠️ **{len(missing_items)} item(s) missing or not uploaded:**")
    for m in missing_items:
        st.markdown(f"- {m}")
else:
    st.success("✅ All checklist items satisfied.")

# ── Cross-verification conflicts ───────────────────────────────────────────────────
st.markdown("---")
st.subheader("⚠️ Cross-Verification")
conflicts = cross_check_result.get("conflicts", [])
if conflicts:
    for c in conflicts:
        st.warning(f"**{c.get('field', 'Field')}:** {c.get('message', 'Mismatch detected')}")
else:
    st.success("✅ No cross-verification conflicts detected.")

st.markdown("---")

# ── Document-level review ─────────────────────────────────────────────────────────
st.subheader("🗑️ Evidence Panel & Document Review")

if not docs:
    st.info("No documents uploaded yet for this case.")
    st.stop()

# Select document to review
doc_options = {f"{d['doc_id']} - {d['file_name']} ({d['doc_type']})": d for d in docs}
sel_doc_label = st.selectbox("Select Document to Review", list(doc_options.keys()))
doc = doc_options[sel_doc_label]

left_col, right_col = st.columns([1, 1])

with left_col:
    st.markdown("### 🗎 Evidence (Document Preview)")
    file_path = Path(doc.get("file_path", ""))
    if file_path.exists():
        file_ext = file_path.suffix.lower()
        if file_ext in [".jpg", ".jpeg", ".png"]:
            st.image(str(file_path), use_column_width=True, caption=doc.get("file_name"))
        elif file_ext == ".pdf":
            st.info("📝 PDF preview: Use external viewer or convert pages to images for inline display.")
            # For a real app, integrate pdf2image to convert and show pages
            st.markdown(f"**File:** {file_path.name}")
        else:
            st.warning("Unsupported file format for preview.")
    else:
        st.error(f"File not found: {file_path}")

    st.markdown("---")
    st.markdown("### 📋 Raw OCR Text (Sample)")
    raw_text = doc.get("raw_text", "")
    st.text_area("OCR Output", value=raw_text[:1000], height=200, disabled=True)

with right_col:
    st.markdown("### ✏️ Extracted Fields (Editable)")
    extracted = doc.get("extracted_fields", {})
    if isinstance(extracted, str):
        extracted = json.loads(extracted) if extracted else {}

    updated_fields = {}
    for field, value in extracted.items():
        updated_fields[field] = st.text_input(field.replace("_", " ").title(), value=str(value), key=f"field_{doc['doc_id']}_{field}")

    st.markdown("---")
    st.markdown("### ✅ Review Decision")
    review_status = st.radio(
        "Document Status",
        ["Pending Review", "Approved", "Rejected"],
        index=["Pending Review", "Approved", "Rejected"].index(doc.get("status", "Pending Review")),
        key=f"status_{doc['doc_id']}"
    )
    rejection_reason = st.text_area("Rejection Reason (if rejected)", height=80, key=f"reject_{doc['doc_id']}")

    if st.button("💾 Save Changes", key=f"save_{doc['doc_id']}", use_container_width=True):
        # Update extracted fields and status
        update_document_field(doc["doc_id"], "extracted_fields", updated_fields)
        update_document_field(doc["doc_id"], "status", review_status)
        if review_status == "Rejected":
            update_document_field(doc["doc_id"], "rejection_reason", rejection_reason)

        log_audit(
            case_id=case_id,
            action="DOCUMENT_REVIEWED",
            performed_by=st.session_state.get("username", "system"),
            details=f"doc_id={doc['doc_id']} | status={review_status}"
        )
        st.success(f"✅ Document {doc['doc_id']} updated successfully.")
        st.rerun()

st.markdown("---")

# ── Case-level approval ───────────────────────────────────────────────────────────
st.subheader("✅ Final Case Approval")
all_approved = all(d.get("status") == "Approved" for d in docs)
if all_approved and not missing_items:
    if st.button("🚀 Mark Case as Complete", use_container_width=True):
        update_case_status(case_id, "Complete")
        log_audit(
            case_id=case_id,
            action="CASE_COMPLETED",
            performed_by=st.session_state.get("username", "system"),
            details="All documents approved and checklist satisfied."
        )
        st.success("✅ Case marked as Complete. Proceed to CMR Generation.")
        st.balloons()
else:
    st.info("⚠️ All documents must be approved and checklist satisfied before completing the case.")
