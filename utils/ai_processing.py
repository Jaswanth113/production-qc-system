#ai_processing

import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
# --- FIX #1: Corrected the model name to the official, available version ---
model = genai.GenerativeModel('gemini-2.0-flash-lite')

def summarize_document_context(markdown_text):
    prompt = f"Analyze the document content. Find the main title and document number. Write a single, concise paragraph summarizing the document's purpose.\n\nDocument Content:\n{markdown_text}"
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Could not generate summary: {e}"

def extract_specs_from_text(document_text):
    prompt = f"""
    You are a meticulous data extraction robot. Your task is to analyze the provided Markdown, which contains HTML tables, and convert the relevant information into a single JSON object.

    Follow these steps precisely:
    1.  Identify the main material name, which might include a stage (e.g., "Methanol (R2)").
    2.  Locate the primary specification table, which will have columns like "Name of the test" and "Specification".
    3.  Iterate through each row of that table. For each row, extract the test name and its specification text.
    4.  Determine the `type` for each specification ('text', 'numeric_range', 'numeric_max').
    5.  Format everything into a single JSON object. The top-level key for the list of tests MUST be "parameters".

    Here is an example of the perfect output format:
    {{
      "material": "Methanol (R2)",
      "stage": "R2",
      "parameters": [
        {{
          "name": "Description",
          "spec": "Clear colorless liquid free from suspended matter",
          "type": "text"
        }},
        {{
          "name": "Relative Density",
          "spec": "0.78 – 0.81",
          "type": "numeric_range",
          "min": 0.78,
          "max": 0.81
        }}
      ]
    }}

    You MUST return ONLY the JSON object and nothing else.

    ## Document Content:
    {document_text}
    
    ## JSON Output:
    """
    try:
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        parsed_json = json.loads(cleaned_response)

        param_list = parsed_json.get('parameters')
        if not param_list:
            error_msg = f"AI returned valid JSON, but the required 'parameters' key was missing.\n\nAI's Response:\n---\n{cleaned_response}\n---"
            return False, error_msg

        return True, parsed_json

    except Exception as e:
        raw_response = "N/A"
        if 'response' in locals():
            raw_response = response.text
        error_msg = f"AI FAILED TO PRODUCE VALID JSON.\n\nPython Error: {e}\n\nAI's Raw, Unfiltered Response:\n---\n{raw_response}\n---"
        return False, error_msg

def validate_qc_results(specifications, qc_results):
    print("\n--- Entering Upgraded AI Validation ---")
    results_breakdown = []
    # --- FIX #2: Using the correct en-dash '–' to match the UI code ---
    final_decision = "Pass – Proceed to Next Stage"
    
    text_params_to_validate = []
    
    #Step 1: Instantly process all numeric parameters
    for spec in specifications:
        param_name = spec.get('name')
        param_type = spec.get('type')
        qc_result = qc_results.get(param_name)
        pass_fail = "Fail"
        remarks = ""

        if param_type in ['numeric_range', 'numeric_max', 'numeric_min']:
            if qc_result is None or str(qc_result).strip() == "":
                remarks = "Input not provided."
            else:
                try:
                    qc_value = float(qc_result)
                    if param_type == 'numeric_range':
                        if spec.get('min') <= qc_value <= spec.get('max'):
                            pass_fail = "Pass"; remarks = "Value is within range."
                        else: remarks = f"Value is outside the range of {spec.get('min')} - {spec.get('max')}."
                    elif param_type == 'numeric_max':
                        if qc_value <= spec.get('max'):
                            pass_fail = "Pass"; remarks = f"Value is not more than {spec.get('max')}."
                        else: remarks = f"Value exceeds the maximum of {spec.get('max')}."
                except (ValueError, TypeError): remarks = "Invalid numeric input."
            
            results_breakdown.append({"Parameter": param_name, "Spec": spec.get('spec'), "QC Result": qc_result, "Pass/Fail": pass_fail, "Remarks": remarks})
        elif param_type == 'text':
            text_params_to_validate.append({"name": param_name, "spec": spec.get('spec'), "observation": qc_result})

    #Step 2: Batch process all text parameters in a single AI call
    if text_params_to_validate:
        prompt = f"""
        You are an intelligent Quality Control validation system. Analyze the following list of parameters. 
        For each one, semantically compare the user's observation with the official specification. 
        Understand the meaning, not just keywords.

        INPUT JSON:
        {json.dumps(text_params_to_validate, indent=2)}

        When validating the observation, you must use a balanced approach. 
        The observation should be marked as Pass only if its meaning strongly matches the specification, 
        or if the user gives a simple confirmation such as "yes", "ok", "done", "same", "matches", or anything that clearly indicates compliance. 
        Shorter or simplified descriptions are acceptable as long as the meaning clearly fits within the boundaries defined by the specification. 
        However, if the observation introduces anything new, unusual, unclear, or outside the specification—even slightly—it should be marked as Fail. 
        If the observation partially matches but includes any contradictory detail, or conflicts with any part of the specification, 
        it should also be marked as Fail.

        EXAMPLE OUTPUT JSON:
        {{
          "validation_results": [
            {{
              "name": "Description",
              "decision": "Pass",
              "remark": "The user's observation 'clear liquid' matches the specification."
            }},
            {{
              "name": "Residue on Evaporation",
              "decision": "Fail",
              "remark": "The observation 'some particles' contradicts the 'No residue' specification."
            }}
          ]
        }}

        You MUST return ONLY the JSON object and nothing else.
        """
        try:
            response = model.generate_content(prompt)
            cleaned_text = response.text.strip().replace('```json', '').replace('```', '')
            ai_results = json.loads(cleaned_text).get("validation_results", [])
            
            ai_results_map = {res["name"]: res for res in ai_results}

            for param in text_params_to_validate:
                param_name = param["name"]
                ai_result = ai_results_map.get(param_name)
                if ai_result:
                    pass_fail = ai_result.get("decision", "Fail")
                    remarks = ai_result.get("remark", "No remark from AI.")
                else:
                    pass_fail = "Fail"
                    remarks = "AI did not return a result for this parameter."
                
                results_breakdown.append({"Parameter": param_name, "Spec": param["spec"], "QC Result": param["observation"], "Pass/Fail": pass_fail, "Remarks": remarks})

        except Exception as e:
            remarks = f"A batch AI validation error occurred: {e}"
            for param in text_params_to_validate:
                 results_breakdown.append({"Parameter": param["name"], "Spec": param["spec"], "QC Result": param["observation"], "Pass/Fail": "Fail", "Remarks": remarks})

    #Step 3: Determine final decision
    for result in results_breakdown:
        if result["Pass/Fail"] == "Fail":
            # --- FIX #2: Using the correct en-dash '–' to match the UI code ---
            final_decision = "Fail – Material Rejected"
            break
            
    return final_decision, results_breakdown