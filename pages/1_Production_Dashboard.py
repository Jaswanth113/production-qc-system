#production dashboard

import streamlit as st
from utils.doc_parser import get_md_from_file_mineru
from utils import ai_processing, db
import datetime
import random
import pandas as pd

st.set_page_config(page_title="Production Dashboard", layout="wide")

if st.session_state.get('role') != 'Production':
    st.warning("Please select the 'Production' role from the main page sidebar.")
    st.stop()

if 'specs_data' not in st.session_state: st.session_state.specs_data = None
if 'validation_results' not in st.session_state: st.session_state.validation_results = None

st.title("Production Department Dashboard")

#Step 1: File Upload and Processing
st.header("Step 1: Upload and Process Document")
uploaded_file = st.file_uploader("Upload a Specification Sheet", type=['pdf', 'docx', 'doc'])

if uploaded_file:
    if st.button("Process Document"):
        st.session_state.specs_data = None
        st.session_state.validation_results = None
        
        with st.spinner("Processing document... (This may be instant if cached)"):
            markdown_content = get_md_from_file_mineru(uploaded_file)
            if "Error" in markdown_content:
                st.error(markdown_content)
            else:
                success, result = ai_processing.extract_specs_from_text(markdown_content)
                if success:
                    st.session_state.specs_data = result
                    st.success("Document processed! Please proceed to Step 2.")
                    st.rerun()
                else:
                    st.error("AI Extraction Failed. See details below:")
                    st.code(result, language='text')

#Step 2: User Input Form
if st.session_state.specs_data and st.session_state.validation_results is None:
    st.header("Step 2: Review and Pre-Validate Observations")
    
    summary = ai_processing.summarize_document_context(get_md_from_file_mineru(uploaded_file))
    if summary:
        st.info(f"**AI Document Summary:** {summary}")

    with st.form("pre_validation_form"):
        
        st.subheader("Sample Information")
        ai_material_name = st.session_state.specs_data.get('material', '')
        material_name = st.text_input("Material Name", value=ai_material_name, help="Enter the full, official material name.")
        performed_by = st.text_input("Performed By (Your Name)")
        
        st.subheader("Enter Your Observations")
        user_inputs = {}
        for i, param in enumerate(st.session_state.specs_data.get('parameters', [])):
            param_name = param.get('name')
            if param.get('type') == 'text':
                user_inputs[param_name] = st.text_input(label=f"Observation for '{param_name}' (Spec: {param.get('spec')})", key=f"text_{i}")
            else:
                user_inputs[param_name] = st.number_input(label=f"Value for '{param_name}' (Spec: {param.get('spec')})", value=None, format="%.4f", key=f"num_{i}")
        
        validate_button = st.form_submit_button("Validate My Observations")
        if validate_button:
            if not material_name or not performed_by:
                st.warning("Please fill in both 'Material Name' and 'Performed By' fields.")
            else:
                with st.spinner("AI is performing validation..."):
                    final_decision, results_breakdown = ai_processing.validate_qc_results(st.session_state.specs_data.get('parameters'), user_inputs)
                    st.session_state.validation_results = {
                        "decision": final_decision, "breakdown": results_breakdown, "inputs": user_inputs,
                        "material_name": material_name, "performed_by": performed_by
                    }
                    st.rerun()

if st.session_state.validation_results:
    st.header("Step 3: Pre-Validation Results")
    results = st.session_state.validation_results

    ai_extracted_stage = st.session_state.specs_data.get('stage', 'N/A')
    st.metric("Pre-Validation Decision", results['decision'])
    st.info(f"Analysis for **{results['material_name']} (Stage: {ai_extracted_stage})** performed by: **{results['performed_by']}**")

    df_results = pd.DataFrame(results['breakdown'])
    if 'QC Result' in df_results.columns:
        df_results['QC Result'] = df_results['QC Result'].astype(str)

    st.dataframe(df_results.style.map(lambda v: 'color: red' if v == 'Fail' else 'color: green', subset=['Pass/Fail']), use_container_width=True)

    if results['decision'] == "Pass – Proceed to Next Stage":
        st.success("All parameters passed.")
        if st.button("Confirm and Submit to QC"):
            with st.spinner("Submitting to QC..."):
                now = datetime.datetime.now()
                sample_id = f"SMP-{now.strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
                sample_data = {
                    "sample_id": sample_id,
                    "material_info": { 
                        "name": results['material_name'], 
                        "stage": st.session_state.specs_data.get('stage') 
                    },
                    "specifications": st.session_state.specs_data.get('parameters'),
                    "production_inputs": results['inputs'],
                    "performed_by": results['performed_by'],
                    "status": "Sample Ready for Analysis", "request_date": now.isoformat(),
                    "qc_inputs": {}, "analysis_results": None, "final_decision": None, 
                }
                db.save_sample(sample_data)
                st.success(f"Sample submitted to QC.")
                st.session_state.specs_data = None
                st.session_state.validation_results = None
                
    else:
        st.error("One or more parameters failed.")
        if st.button("Retry Validation"):
            st.session_state.validation_results = None
            st.rerun()