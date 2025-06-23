# MCDR CloudBackup 插件入口文件
# 支持阿里云OSS自动备份
from mcdreforged.api.all import *
from cloudbackup.core.core import start_backup, stop_backup, list_backups, status_backup, query_backup_records
from cloudbackup.config import CloudBackupConfig
from cloudbackup.core.backup_task import backup_running, backup_task_id, load_resume_info
from cloudbackup.cmd.command_tree import register_cb_command
import threading
import json
import os

PLUGIN_METADATA = {
    'id': 'cloudbackup',
    'version': '0.0.1',
    'name': 'CloudBackup',
    'description': '自动备份到云对象存储',
    'author': 'caikun233',
    'link': ''
}

def on_load(server: PluginServerInterface, old):
    server.logger.info('CloudBackup 插件已加载')
    config = server.load_config_simple(target_class=CloudBackupConfig)
    # 遍历数据目录 resume，提示所有断点任务
    resume_dir = os.path.join(server.get_data_folder(), 'resume')
    if os.path.exists(resume_dir):
        for fname in os.listdir(resume_dir):
            if fname.endswith('.json'):
                task_id = fname[:-5]
                server.logger.warning(f'检测到未完成分片上传任务: {task_id}，可用 !!cb continue {task_id} 续传，或 !!cb abort {task_id} 放弃。')

    def save_and_reload():
        # 保存配置并重新加载插件
        server.logger.info('§aCloudBackup 配置已更新，正在保存...')
        if hasattr(config, 'save') and callable(config.save):
            config.save()
        else:
            # 直接写入 config.json
            import json, os
            config_path = os.path.join(server.get_data_folder(), 'config.json')
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config.__dict__, f, ensure_ascii=False, indent=2)
        server.reload_plugin('cloudbackup')
    from cloudbackup.core.core import continue_cmd_factory, abort_cmd_factory
    # config_setter 回调
    def config_setter(src, key, value):
        key_map = {
            'accessKey': 'AccessKeyID',
            'bucketName': 'BucketName',
            'region': 'Endpoint',
            'targetBackupPath': 'BackupPath',
            'localBackupPath': 'LocalBackupDir',
            'fileNamePrefix': 'ZipPrefix',
            'accesskey id': 'AccessKeyID',
            'accesskey secret': 'AccessKeySecret',
            'deleteLocalAfterUpload': 'DeleteLocalAfterUpload',
            'localBackupKeepCount': 'LocalBackupKeepCount',
            'backupSourceDir': 'BackupSourceDir',
            'multipartChunkSize': 'MultipartChunkSize',
        }
        if key not in key_map:
            src.reply(f'§c未知配置项: {key}，支持: {list(key_map.keys())}')
            return
        field = key_map[key]
        # 类型转换
        if key == 'region':
            value = f"oss-{value}.aliyuncs.com"
        elif key == 'deleteLocalAfterUpload':
            value = True if value in (True, 'true', 'True', 1, '1') else False
        elif key == 'localBackupKeepCount':
            try:
                value = int(value)
            except Exception:
                src.reply('§c本地保留压缩包数量必须为整数')
                return
        elif key == 'multipartChunkSize':
            try:
                value = int(value)
            except Exception:
                src.reply('§c分片大小必须为整数（字节）')
                return
        elif key == 'backupSourceDir':
            value = str(value)
        setattr(config, field, value)
        save_and_reload()
        src.reply(f'§a{field} 已更新: §b{getattr(config, field)}')
    # 注册命令树
    register_cb_command(
        server,
        config,
        start_backup,
        stop_backup,
        list_backups,
        status_backup,
        query_backup_records,
        config_setter,
        continue_cmd_factory(server),
        abort_cmd_factory(server)
    )

def on_unload(server: PluginServerInterface):
    from cloudbackup.core.backup_task import backup_running, backup_task_id, stop_flag, load_resume_info, save_resume_info
    # 插件卸载时检查是否有未完成任务
    if backup_running and backup_task_id:
        server.logger.warning('§c卸载过程中检测到进行中的任务，正在请求安全终止...')
        stop_flag.set()  # 请求分片上传安全终止
        try:
            # 强制保存一次断点
            info = load_resume_info(backup_task_id)
            if info:
                save_resume_info(backup_task_id, info)
        except Exception as e:
            server.logger.error(f"写入未完成任务记录失败: {e}")
        server.logger.warning('检测到备份任务未完成，已请求中断。请手动检查上传状态。')

def on_server_startup(server: PluginServerInterface):
    # 启动时检测断点任务
    resume_dir = os.path.join(os.path.dirname(__file__), 'resume')
    if os.path.exists(resume_dir):
        for fname in os.listdir(resume_dir):
            if fname.endswith('.json'):
                task_id = fname[:-5]
                server.logger.warning(f'§e[CloudBackup] 检测到未完成的分片上传任务: {task_id}，可用 !!cb continue {task_id} 续传，或 !!cb abort {task_id} 放弃。')