import streamlit as st
import os
from database import init_db

# Initialize database on startup
init_db()
os.makedirs('/tmp/storage/uploads', exist_ok=True)
os.makedirs('/tmp/storage/pages', exist_ok=True)
os.makedirs('/tmp/storage/crops', exist_ok=True)
os.makedirs('/tmp/storage/cmr_output', exist_ok=True)
os.makedirs('/tmp/templates', exist_ok=True)