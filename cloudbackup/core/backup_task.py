import os
import shutil
import threading
from datetime import datetime
from ..utils.utils import gen_task_id, get_timestamp
from ..oss.oss_util import get_oss_client, upload_file_multipart, check_cloud_file_size
from ..model.record import backup_records, save_backup_records
from mcdreforged.api.all import PluginServerInterface
from ..config import CloudBackupConfig
from .resume_util import save_resume_info, load_resume_info, remove_resume_info

backup_thread = None
backup_running = False
backup_status = 'stopped'
backup_task_id = None
backup_start_time = None
backup_end_time = None
backup_upload_speed = None
backup_error_msg = None
stop_flag = threading.Event()

def do_backup(server, src, config, task_id=None, resume_info=None):
    global backup_status, backup_task_id, backup_start_time, backup_end_time, backup_upload_speed, backup_error_msg, stop_flag
    stop_flag.clear()
    backup_status = 'running'
    backup_start_time = datetime.now()
    backup_end_time = None
    backup_upload_speed = None
    backup_error_msg = None
    if task_id is None:
        task_id = gen_task_id(config)
    backup_task_id = task_id
    def progress_callback(uploaded, total, part, total_parts, resume_info=None):
        percent = int(uploaded * 100 / total)
        src.reply(f'§e[CloudBackup] 上传进度: §b{percent}% §8({part}/{total_parts}分片)')
        # 实时保存断点
        if resume_info is not None:
            save_resume_info(task_id, resume_info)
    try:
        try:
            client = get_oss_client(config)
        except Exception:
            src.reply('§c请先安装 alibabacloud_oss_v2: pip install alibabacloud_oss_v2')
            backup_status = 'error: no oss2'
            backup_error_msg = 'no oss2'
            return
        # 断点续传时直接用上次的 zip 文件
        if resume_info and 'local_zip_path' in resume_info and os.path.exists(resume_info['local_zip_path']):
            local_zip_path = resume_info['local_zip_path']
            zip_name = os.path.basename(local_zip_path)
            oss_path = resume_info.get('oss_path') or os.path.join(config.BackupPath, zip_name).replace('\\', '/').replace('\\', '/')
            src.reply(f'§e检测到断点续传，直接上传本地压缩包: {zip_name}')
        else:
            # 支持自定义备份源目录
            if getattr(config, 'BackupSourceDir', None):
                world_dir = config.BackupSourceDir
            else:
                world_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))), 'server', 'world')
            if not os.path.exists(world_dir):
                backup_status = 'error: world目录不存在'
                backup_error_msg = 'world目录不存在'
                src.reply('§cworld目录不存在，无法备份')
                src.reply(f'§7{world_dir}')
                return
            timestamp = get_timestamp()
            zip_prefix = getattr(config, 'ZipPrefix', 'world')
            # 临时目录直接用 LocalBackupDir
            temp_dir = config.LocalBackupDir
            zip_name = f"{zip_prefix}-{timestamp}-{task_id}.zip"
            local_zip_path = os.path.join(config.LocalBackupDir, zip_name)
            os.makedirs(config.LocalBackupDir, exist_ok=True)
            # 复制 world 到 LocalBackupDir 下的 world_<task_id> 再压缩
            tmp_world = os.path.join(temp_dir, f'world_{task_id}')
            if os.path.exists(tmp_world):
                shutil.rmtree(tmp_world)
            def ignore_session_lock(dir, files):
                return ['session.lock'] if 'session.lock' in files else []
            shutil.copytree(world_dir, tmp_world, ignore=ignore_session_lock)
            shutil.make_archive(base_name=local_zip_path[:-4], format='zip', root_dir=temp_dir, base_dir=f'world_{task_id}')
            shutil.rmtree(tmp_world)
            src.reply(f'§a压缩完成: §b{zip_name}§a，开始上传...')
            oss_path = os.path.join(config.BackupPath, zip_name).replace('\\', '/').replace('\\', '/')
        file_size, upload_start, upload_end, resume_info_out = upload_file_multipart(
            client, config, local_zip_path, oss_path, progress_callback=progress_callback, resume_info=resume_info, stop_flag=stop_flag)
        backup_end_time = datetime.now()
        if resume_info_out:
            # 上传未完成，保存断点信息
            save_resume_info(task_id, resume_info_out)
            src.reply(f'§c上传中断，断点信息已保存。可用 !!cb continue {task_id} 续传，或 !!cb abort {task_id} 放弃。')
            backup_status = 'interrupted'
            return
        else:
            remove_resume_info(task_id)
        # 上传完成后校验云端文件大小
        cloud_check_passed = False
        try:
            oss_file_size = check_cloud_file_size(client, config, oss_path)
            if oss_file_size is not None and oss_file_size == file_size:
                server.logger.info(f'§a云端校验成功: 文件大小一致 {oss_file_size} 字节')
                cloud_check_passed = True
            else:
                server.logger.warning(f'§e云端校验失败: 本地 {file_size} 字节, 云端 {oss_file_size if oss_file_size is not None else "未找到"}')
        except Exception as check_e:
            server.logger.warning(f'§e云端校验异常: {check_e}')
            cloud_check_passed = False
        # 仅在云端校验通过时删除本地压缩包
        local_deleted = False
        if cloud_check_passed and getattr(config, 'DeleteLocalAfterUpload', False):
            try:
                os.remove(local_zip_path)
                local_deleted = True
            except Exception as del_e:
                server.logger.warning(f'§e本地压缩包删除失败: {del_e}')
        else:
            if not cloud_check_passed:
                server.logger.warning('§e云端校验未通过，本地压缩包已保留')
            elif not getattr(config, 'DeleteLocalAfterUpload', False):
                server.logger.info('§e配置为上传完成后保留本地文件')
        duration = (upload_end - upload_start).total_seconds()
        speed = file_size / duration if duration > 0 else 0
        backup_upload_speed = speed
        backup_status = 'finished'
        backup_error_msg = None
        server.logger.info('§a备份完成' + (f'，本地压缩包已删除' if local_deleted else '，本地压缩包已保留'))
        # 记录备份
        backup_records.append({
            'time': backup_start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'file': zip_name,
            'success': True,
            'error': None,
            'upload_speed': round(speed/1024/1024, 2),
            'duration': round((backup_end_time-backup_start_time).total_seconds(), 2)
        })
        save_backup_records()
        # 自动清理本地多余压缩包（保留最新 N 个）
        try:
            keep_count = getattr(config, 'LocalBackupKeepCount', 5)
            backup_dir = config.LocalBackupDir
            prefix = getattr(config, 'ZipPrefix', 'world')
            files = [f for f in os.listdir(backup_dir) if f.endswith('.zip') and f.startswith(prefix)]
            files_full = [os.path.join(backup_dir, f) for f in files]
            files_full.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            for old_file in files_full[keep_count:]:
                try:
                    os.remove(old_file)
                    server.logger.info(f'§e本地备份超出保留数量，已自动删除: {os.path.basename(old_file)}')
                except Exception as e:
                    server.logger.warning(f'§e自动清理本地备份失败: {old_file} | {e}')
        except Exception as e:
            server.logger.warning(f'§e自动清理本地备份异常: {e}')
    except Exception as e:
        backup_end_time = datetime.now()
        backup_status = f'error: {e}'
        backup_error_msg = str(e)
        server.logger.error(f'§c备份失败: {e}')
        src.reply(f'§c备份失败: {e}')
        # 记录失败
        backup_records.append({
            'time': backup_start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'file': zip_name if 'zip_name' in locals() else '',
            'success': False,
            'error': str(e),
            'upload_speed': 0,
            'duration': round((backup_end_time-backup_start_time).total_seconds(), 2)
        })
        save_backup_records()

def start_backup(src, config):
    global backup_thread, backup_running, backup_status, backup_task_id
    server = PluginServerInterface.get_instance()
    if backup_running:
        src.reply('备份已在进行中')
        return
    backup_running = True
    backup_status = 'running'
    task_id = gen_task_id(config)
    backup_task_id = task_id
    server.logger.info(f'§e备份已开始 §8| §e任务ID: §b{task_id}')
    def run():
        do_backup(server, src, config, task_id)
        global backup_running
        backup_running = False
    backup_thread = threading.Thread(target=run)
    backup_thread.start()

def stop_backup(src):
    global backup_running, backup_status, stop_flag
    if not backup_running:
        src.reply('没有正在进行的备份')
        return
    backup_running = False
    backup_status = 'stopped by user'
    stop_flag.set()
    src.reply('尝试停止备份')

def status_backup(src):
    global backup_status, backup_task_id, backup_start_time, backup_end_time, backup_upload_speed
    if backup_task_id:
        msg = f'§e备份状态: §a{backup_status} §8| §e任务ID: §b{backup_task_id}'
        if backup_start_time:
            msg += f' §8| §e开始: §7{backup_start_time.strftime("%Y-%m-%d %H:%M:%S")}'
        if backup_end_time and backup_start_time:
            duration = (backup_end_time - backup_start_time).total_seconds()
            msg += f' §8| §e耗时: §7{round(duration,2)}s'
        if backup_upload_speed:
            msg += f' §8| §e平均上传: §b{round(backup_upload_speed/1024/1024,2)}MB/s'
        src.reply(msg)
    else:
        src.reply(f'§e备份状态: §a{backup_status}')
