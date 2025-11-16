#db.py 

import json
import os
import threading

file_lock = threading.Lock()
DATA_DIR = 'data'
SAMPLES_FILE = os.path.join(DATA_DIR, 'samples.json')

def ensure_data_dir_exists():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    if not os.path.exists(SAMPLES_FILE):
        with open(SAMPLES_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)

def read_json_file(file_path):
    with file_lock:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

def write_json_file(file_path, data):
    with file_lock:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

def get_samples():
    return read_json_file(SAMPLES_FILE)

def save_sample(sample_data):
    samples = get_samples()
    samples.append(sample_data)
    write_json_file(SAMPLES_FILE, samples)
    
def update_sample(sample_id, updated_data):
    samples = get_samples()
    for i, sample in enumerate(samples):
        if sample.get('sample_id') == sample_id:
            samples[i].update(updated_data)
            break
    write_json_file(SAMPLES_FILE, samples)