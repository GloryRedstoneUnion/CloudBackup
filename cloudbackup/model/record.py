import os
import json

BACKUP_RECORDS_FILE_NAME = 'backup_records.json'
backup_records = []

def get_backup_records_path(server):
    return os.path.join(server.get_data_folder(), BACKUP_RECORDS_FILE_NAME)

def save_backup_records(server):
    try:
        with open(get_backup_records_path(server), 'w', encoding='utf-8') as f:
            json.dump(backup_records, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def load_backup_records(server):
    global backup_records
    path = get_backup_records_path(server)
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                backup_records = json.load(f)
        except Exception:
            backup_records = []
    else:
        backup_records = []

def query_backup_records(server, src, count=5):
    load_backup_records(server)
    if not backup_records:
        src.reply('§7暂无备份记录')
        return
    lines = ['§e最近备份记录:']
    for rec in backup_records[-count:][::-1]:
        line = f"§7[{rec['time']}] §b{rec['file']} §8| §a{'成功' if rec['success'] else '失败'}"
        if rec['error']:
            line += f" §c{rec['error']}"
        line += f" §8| §e速度: §b{rec['upload_speed']}MB/s §8| §e耗时: §7{rec['duration']}s"
        lines.append(line)
    src.reply('\n'.join(lines))
