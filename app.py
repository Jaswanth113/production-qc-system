import streamlit as st
from utils import db
import os

CACHE_INPUT_DIR = 'temp_mineru_input'
CACHE_OUTPUT_DIR = 'temp_mineru_output'

def ensure_cache_dirs_exist():
    for directory in [CACHE_INPUT_DIR, CACHE_OUTPUT_DIR]:
        os.makedirs(directory, exist_ok=True)

def main():
    st.sidebar.title("AI QC Workflow")
    
    role = st.sidebar.selectbox(
        "Select Your Role",
        ("Production", "QC"),
        key='role_selector'
    )
    st.session_state['role'] = role
    
    st.sidebar.info(f"You are currently in **{role}** mode.")
    
    st.title("Welcome to the AI-Powered Quality Control System")
    st.info("Please navigate to your dashboard using the links in the sidebar.")
    st.markdown("---")
    st.write("This system uses AI to streamline the quality control process, from document analysis to sample validation.")

if __name__ == "__main__":
    ensure_cache_dirs_exist()
    db.ensure_data_dir_exists()
    main()