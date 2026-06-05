import streamlit as st
import os
import json
from pathlib import Path
from datetime import datetime
from database import (
    get_case_by_id, get_all_cases, add_document,
    get_documents_by_case, log_audit
)
from classifier import classify_document
from ocr_engine import extract_text_from_file
from extractor import extract_fields
from rules_engine import validate_checklist

st.set_page_config(page_title="Upload Documents", page_icon="📄", layout="wide")

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

st.title("📄 Upload Documents")
st.markdown("Attach scanned documents to a case and trigger automated processing.")
st.markdown("---")

# ── Case selector ───────────────────────────────────────────────────────────────
try:
    all_cases = get_all_cases()
except Exception:
    all_cases = []

if not all_cases:
    st.warning("⚠️ No cases found. Please create a case first.")
    st.stop()

case_options = {
    f"{c['case_id']} - {c['provisional_customer_name']} ({c['product_type']})": c['case_id']
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

# ── Upload widget ─────────────────────────────────────────────────────────────────
st.subheader("⬆️ Upload New Documents")
uploaded_files = st.file_uploader(
    "Drop PDF / JPG / PNG files here",
    type=["pdf", "jpg", "jpeg", "png"],
    accept_multiple_files=True,
)

DOC_TYPE_OPTIONS = [
    "Auto-detect",
    "GST Registration Certificate",
    "PAN Card",
    "Incorporation Certificate",
    "Board Resolution",
    "Bank Account Proof",
    "Authorised Signatory KYC",
    "Trade License",
    "MSME Certificate",
    "SEZ Approval Letter",
    "Other",
]

doc_type_override = st.selectbox(
    "Document Type (leave Auto-detect to let the classifier decide)",
    DOC_TYPE_OPTIONS,
)

if uploaded_files:
    if st.button("⚙️ Process & Save Documents", use_container_width=True):
        progress = st.progress(0)
        status_area = st.empty()
        results = []

        for idx, uf in enumerate(uploaded_files):
            status_area.info(f"Processing {uf.name} …")

            # Save to disk
            case_dir = UPLOAD_DIR / str(case_id)
            case_dir.mkdir(exist_ok=True)
            save_path = case_dir / uf.name
            save_path.write_bytes(uf.getbuffer())

            # OCR
            try:
                raw_text = extract_text_from_file(str(save_path))
            except Exception as exc:
                raw_text = ""
                st.warning(f"OCR failed for {uf.name}: {exc}")

            # Classify
            if doc_type_override == "Auto-detect":
                try:
                    detected_type = classify_document(raw_text)
                except Exception:
                    detected_type = "Unknown"
            else:
                detected_type = doc_type_override

            # Extract fields
            try:
                extracted = extract_fields(raw_text, detected_type)
            except Exception:
                extracted = {}

            # Persist document record
            doc_id = add_document(
                case_id=case_id,
                file_name=uf.name,
                file_path=str(save_path),
                doc_type=detected_type,
                raw_text=raw_text,
                extracted_fields=extracted,
            )

            log_audit(
            case_id=case_id,
            event_type="DOCUMENT_UPLOADED",
            actor_id=st.session_state.get("username", "system"),
            old_val="",
            new_val="",
            comment=f"{uf.name} | type={detected_type} | doc_id={doc_id}"
            )

            results.append(
                {
                    "File": uf.name,
                    "Detected Type": detected_type,
                    "Fields Extracted": len(extracted),
                    "doc_id": doc_id,
                }
            )
            progress.progress((idx + 1) / len(uploaded_files))

        status_area.success(f"✅ {len(results)} file(s) processed successfully.")

        import pandas as pd
        st.dataframe(pd.DataFrame(results), use_container_width=True)
        st.info("👉 Go to **Review Workspace** to inspect extracted data and validate the checklist.")

st.markdown("---")

# ── Existing documents for this case ────────────────────────────────────────────
st.subheader("🗂️ Documents Already Attached")
try:
    docs = get_documents_by_case(case_id)
    if docs:
        import pandas as pd
        df = pd.DataFrame(docs)
        show_cols = ["doc_id", "file_name", "doc_type", "status", "uploaded_at"]
        existing = [c for c in show_cols if c in df.columns]
        st.dataframe(df[existing], use_container_width=True, height=250)
    else:
        st.info("No documents uploaded yet for this case.")
except Exception as exc:
    st.warning(f"Could not load documents: {exc}")
