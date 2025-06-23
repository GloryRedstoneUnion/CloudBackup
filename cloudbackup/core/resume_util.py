import os
import json

RESUME_DIR = os.path.join(os.path.dirname(__file__), '..', 'resume')
RESUME_DIR = os.path.abspath(RESUME_DIR)
os.makedirs(RESUME_DIR, exist_ok=True)

def save_resume_info(task_id, info):
    with open(os.path.join(RESUME_DIR, f'{task_id}.json'), 'w', encoding='utf-8') as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

def load_resume_info(task_id):
    path = os.path.join(RESUME_DIR, f'{task_id}.json')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def remove_resume_info(task_id):
    path = os.path.join(RESUME_DIR, f'{task_id}.json')
    if os.path.exists(path):
        os.remove(path)
