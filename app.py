import streamlit as st
import os
from database import init_db

# Initialize database on startup
init_db()
os.makedirs('storage/uploads', exist_ok=True)
os.makedirs('storage/pages', exist_ok=True)
os.makedirs('storage/crops', exist_ok=True)
os.makedirs('storage/cmr_output', exist_ok=True)
os.makedirs('templates', exist_ok=True)

st.set_page_config(
    page_title='CS Customer Onboarding',
    page_icon='📋',
    layout='wide',
    initial_sidebar_state='expanded'
)

# Session state defaults
if 'current_user' not in st.session_state:
    st.session_state['current_user'] = 'analyst_01'
if 'selected_case_id' not in st.session_state:
    st.session_state['selected_case_id'] = None

# Sidebar branding
with st.sidebar:
    st.markdown('## CS Customer Onboarding')
    st.markdown('---')
    st.markdown('**Logged in as:** ' + st.session_state['current_user'])
    st.markdown('---')
    st.markdown('### Navigation')
    st.markdown('Use the pages below to:')
    st.markdown('- Create Onboarding Case')
    st.markdown('- Upload Documents')
    st.markdown('- Review & Verify')
    st.markdown('- Generate Reports & CMR')
    st.markdown('- Admin Configuration')
    st.markdown('---')
    st.caption('Powered by Streamlit + Tesseract OCR')

# Dashboard home page
st.title('Customer Onboarding & Verification Portal')
st.markdown('### Welcome to the CS Customer Onboarding System')

from database import get_all_cases, get_case_stats
import pandas as pd

col1, col2, col3, col4 = st.columns(4)

all_cases = get_all_cases()
total = len(all_cases)
draft = sum(1 for c in all_cases if c['status'] == 'Draft')
in_review = sum(1 for c in all_cases if c['status'] == 'In Review')
complete = sum(1 for c in all_cases if c['status'] in ['Complete', 'CMR Generated'])

with col1:
    st.metric('Total Cases', total)
with col2:
    st.metric('Draft', draft)
with col3:
    st.metric('In Review', in_review)
with col4:
    st.metric('Complete', complete)

st.markdown('---')
st.subheader('Recent Cases')

if all_cases:
    df = pd.DataFrame(all_cases)[[
        'case_id', 'provisional_customer_name', 'product_type',
        'status', 'sales_officer', 'created_at'
    ]]
    df.columns = ['Case ID', 'Customer', 'Product', 'Status', 'Sales Officer', 'Created']
    df['Created'] = df['Created'].str[:16]

    def highlight_status(val):
        colors = {
            'Draft': 'background-color: #FFF3CD',
            'In Review': 'background-color: #D1ECF1',
            'Complete': 'background-color: #D4EDDA',
            'CMR Generated': 'background-color: #D4EDDA',
            'Rejected': 'background-color: #F8D7DA'
        }
        return colors.get(val, '')

    st.dataframe(
        df.style.applymap(highlight_status, subset=['Status']),
        use_container_width=True,
        height=400
    )

    # Quick case selector
    st.markdown('---')
    st.subheader('Quick Navigate to Case')
    case_options = {c['case_id']: f"{c['case_id']} - {c['provisional_customer_name']} ({c['product_type']})"
                   for c in all_cases}
    selected = st.selectbox('Select a Case', options=[''] + list(case_options.keys()),
                             format_func=lambda x: case_options.get(x, 'Select...') if x else 'Select...')
    if selected:
        st.session_state['selected_case_id'] = selected
        st.info(f'Case {selected} selected. Navigate to Upload Documents or Review Workspace.')
else:
    st.info('No cases yet. Click **Create Case** in the left navigation to get started.')

st.markdown('---')
st.caption('CS Customer Onboarding Portal | v1.0 | Built with Streamlit')
