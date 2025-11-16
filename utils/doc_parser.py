#doc_parser

import os
import subprocess
import sys
import shutil

TEMP_INPUT_DIR = 'temp_mineru_input'
TEMP_OUTPUT_DIR = 'temp_mineru_output'

def get_mineru_executable_path():
    scripts_dir = os.path.dirname(sys.executable)
    
    executable_name = "mineru.exe" if sys.platform == "win32" else "mineru"
    
    executable_path = os.path.join(scripts_dir, executable_name)
    
    if not os.path.exists(executable_path):
        print(f"FATAL ERROR: Could not find '{executable_path}'.")
        print("Please ensure Mineru is correctly installed in the active virtual environment.")
        return None
        
    return executable_path

def get_md_from_file_mineru(uploaded_file):
    if uploaded_file is None:
        return "Error: No file was uploaded."
    base_name = os.path.splitext(uploaded_file.name)[0]
    md_file_path = os.path.join(TEMP_OUTPUT_DIR, base_name, "auto", f"{base_name}.md")

    if os.path.exists(md_file_path):
        print(f"CACHE HIT: Using existing Markdown file: {md_file_path}")
        with open(md_file_path, "r", encoding="utf-8") as f:
            return f.read()

    print(f"CACHE MISS: Processing file with Mineru: {uploaded_file.name}")

    mineru_exe = get_mineru_executable_path()
    if not mineru_exe:
        return "Error: Could not locate the Mineru executable. Please check your installation."

    temp_input_path = os.path.join(TEMP_INPUT_DIR, uploaded_file.name)
    os.makedirs(TEMP_INPUT_DIR, exist_ok=True)
    with open(temp_input_path, "wb") as f:
        f.write(uploaded_file.getvalue())

    temp_output_path = os.path.join(TEMP_OUTPUT_DIR)

    try:
        command = [mineru_exe, "-p", temp_input_path, "-o", temp_output_path]
        
        result = subprocess.run(
            command, 
            check=True, 
            capture_output=True, 
            text=True, 
            encoding='utf-8'
        )
        print("Mineru stdout:", result.stdout)
        print("Mineru stderr:", result.stderr)
        print("Mineru processing completed successfully.")

    except subprocess.CalledProcessError as e:
        error_message = f"Mineru failed to process the file.\nCommand: {' '.join(command)}\nError: {e.stderr}"
        print(error_message)
        return error_message
    except Exception as e:
        return f"An unexpected error occurred while running Mineru: {e}"

    # After processing, read the newly created file
    if os.path.exists(md_file_path):
        with open(md_file_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        return f"Error: Mineru ran, but the output file was not found at {md_file_path}."