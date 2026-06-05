import streamlit as st
import pandas as pd
from datetime import datetime
from database import (
    create_case, get_all_cases, get_case_by_id,
    log_audit, get_db_connection, init_db
)
import json
import uuid

# Ensure database exists
init_db()

st.set_page_config(page_title="Create Case", page_icon="📋", layout="wide")

st.title("📋 Create New Onboarding Case")
st.markdown("Register a new customer onboarding request and assign a product type.")
st.markdown("---")

# ── Product definitions ──────────────────────────────────────────────────────
PRODUCT_TYPES = ["Bitumen", "Sulphur", "HSD", "SEZ"]

CUSTOMER_CATEGORIES = [
    "Road Contractor",
    "Industrial Consumer",
    "Trader / Reseller",
    "Government Entity",
    "Export Customer (SEZ)",
    "Other",
]

# ── Form ─────────────────────────────────────────────────────────────────────
with st.form("create_case_form", clear_on_submit=True):
    st.subheader("Customer Information")

    col1, col2 = st.columns(2)
    with col1:
        customer_name = st.text_input(
            "Customer / Company Name *",
            placeholder="e.g. ABC Infra Pvt. Ltd.",
        )
        gstin = st.text_input(
            "GSTIN",
            placeholder="15-character GST Identification Number",
            max_chars=15,
        )
        pan = st.text_input(
            "PAN",
            placeholder="10-character PAN",
            max_chars=10,
        )
        contact_person = st.text_input("Contact Person", placeholder="Full name")

    with col2:
        customer_category = st.selectbox("Customer Category *", CUSTOMER_CATEGORIES)
        product_type = st.selectbox("Product Type *", PRODUCT_TYPES)
        contact_email = st.text_input("Contact Email", placeholder="name@company.com")
        contact_phone = st.text_input("Contact Phone", placeholder="+91-XXXXXXXXXX")

    st.subheader("Address & Delivery")
    col3, col4 = st.columns(2)
    with col3:
        registered_address = st.text_area(
            "Registered Address", placeholder="Full registered address", height=80
        )
        delivery_location = st.text_input(
            "Delivery / Plant Location", placeholder="City, State"
        )
    with col4:
        pincode = st.text_input("Pincode", max_chars=6)
        state = st.text_input("State")
        annual_qty = st.number_input(
            "Estimated Annual Quantity (MT)", min_value=0, step=100
        )

    st.subheader("Additional Notes")
    remarks = st.text_area("Remarks / Special Instructions", height=80)

    submitted = st.form_submit_button("🚀 Create Case", use_container_width=True)

if submitted:
    # ── Validation ────────────────────────────────────────────────────────────
    errors = []
    if not customer_name.strip():
        errors.append("Customer / Company Name is required.")
    if not product_type:
        errors.append("Product Type is required.")
    if gstin and len(gstin) != 15:
        errors.append("GSTIN must be exactly 15 characters.")
    if pan and len(pan) != 10:
        errors.append("PAN must be exactly 10 characters.")

    if errors:
        for e in errors:
            st.error(e)
    else:
        # ── Persist ───────────────────────────────────────────────────────────
        metadata = {
            "customer_category": customer_category,
            "gstin": gstin.upper().strip(),
            "pan": pan.upper().strip(),
            "contact_person": contact_person.strip(),
            "contact_email": contact_email.strip(),
            "contact_phone": contact_phone.strip(),
            "registered_address": registered_address.strip(),
            "delivery_location": delivery_location.strip(),
            "pincode": pincode.strip(),
            "state": state.strip(),
            "annual_qty_mt": annual_qty,
            "remarks": remarks.strip(),
        }

        new_case_id = str(uuid.uuid4())[:8]
        case_id = create_case(
                    case_id=new_case_id,
                product_type=product_type,
                customer_name=customer_name.strip(),
                sales_officer=metadata.get("contact_person", "").strip(),
                sales_area=metadata.get("delivery_location", "").strip(),
                regional_office=metadata.get("state", "").strip(),
                remarks=remarks.strip(),
                created_by="admin")

        operator = st.session_state.get("username", "system")
        log_audit(
                case_id=case_id,
                event_type="CASE_CREATED",
                actor_id=operator,
                old_val="",
                new_val="",
                comment=f"Product: {product_type} | Category: {customer_category}"
            )

        st.success(
            f"✅ Case **{case_id}** created successfully for **{customer_name}** "
            f"({product_type})."
        )
        st.info(
            "👉 Navigate to **Upload Documents** in the sidebar to attach required documents."
        )
        st.session_state["selected_case_id"] = case_id

# ── Recent Cases Table ────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📂 Recent Cases")

try:
    cases = get_all_cases()
    if cases:
        df = pd.DataFrame(cases)
        display_cols = [
            "case_id", "customer_name", "product_type",
            "status", "created_at",
        ]
        existing = [c for c in display_cols if c in df.columns]
        st.dataframe(
            df[existing].sort_values("created_at", ascending=False).head(20),
            use_container_width=True,
            height=300,
        )
    else:
        st.info("No cases found. Create your first case above.")
except Exception as exc:
    st.warning(f"Could not load cases: {exc}")
