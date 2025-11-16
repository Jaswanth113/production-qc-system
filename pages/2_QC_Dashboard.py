#qc dashboard

import streamlit as st
from utils import db, ai_processing
import pandas as pd

st.set_page_config(page_title="QC Dashboard", layout="wide")

if st.session_state.get('role') != 'QC':
    st.warning("Please select the 'QC' role from the main page sidebar.")
    st.stop()

st.title("Quality Control (QC) Dashboard")

if st.button("Refresh Pending Samples"):
    st.rerun()

all_samples = db.get_samples()
pending_samples = [s for s in all_samples if s and s.get('status') == "Sample Ready for Analysis"]

st.header("Pending Samples for Analysis")

if not pending_samples:
    st.info("There are no samples currently pending analysis. If a sample was just submitted, click 'Refresh'.")
else:
    for sample in pending_samples:
        with st.expander(f"**Sample ID:** {sample['sample_id']} | **Material:** {sample.get('material_info', {}).get('name', 'N/A')}"):
            
            st.subheader("Sample Details")
            col1, col2, col3 = st.columns(3)
            material_info = sample.get('material_info', {})
            col1.metric("Material Name", material_info.get('name', 'N/A'))
            col2.metric("Production Stage", material_info.get('stage', 'N/A'))
            col3.metric("Submitted By (Production)", sample.get('performed_by', 'N/A'))
            
            st.subheader("Specifications and Production Observations")