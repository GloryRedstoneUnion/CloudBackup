import json
import os

def get_resume_dir(server):
    resume_dir = os.path.join(server.get_data_folder(), 'resume')
    os.makedirs(resume_dir, exist_ok=True)
    return resume_dir

def save_resume_info(server, task_id, info):
    resume_dir = get_resume_dir(server)
    with open(os.path.join(resume_dir, f'{task_id}.json'), 'w', encoding='utf-8') as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

def load_resume_info(server, task_id):
    resume_dir = get_resume_dir(server)
    path = os.path.join(resume_dir, f'{task_id}.json')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def remove_resume_info(server, task_id):
    resume_dir = get_resume_dir(server)
    path = os.path.join(resume_dir, f'{task_id}.json')
    if os.path.exists(path):
        os.remove(path)
