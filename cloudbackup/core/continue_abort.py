import threading
from mcdreforged.api.all import PluginServerInterface
from cloudbackup.core.resume_util import load_resume_info, remove_resume_info
from cloudbackup.config import CloudBackupConfig
from cloudbackup.core.backup_task import do_backup

backup_thread = None
backup_running = False
backup_status = 'stopped'
backup_task_id = None

def continue_cmd_factory(server):
    def continue_cmd(src, ctx):
        global backup_thread, backup_running, backup_status, backup_task_id
        task_id = ctx['task_id']
        info = load_resume_info(server, task_id)
        if not info:
            src.reply(f'§c未找到断点信息: {task_id}')
            return
        config = server.load_config_simple(target_class=CloudBackupConfig)
        src.reply(f'§e尝试续传任务: {task_id}')
        if backup_running:
            src.reply('已有备份任务正在进行，无法同时续传')
            return
        backup_running = True
        backup_status = 'running'
        backup_task_id = task_id
        def run():
            do_backup(server, src, config, task_id=task_id, resume_info=info)
            global backup_running
            backup_running = False
        backup_thread = threading.Thread(target=run)
        backup_thread.start()
    return continue_cmd

def abort_cmd_factory(server):
    def abort_cmd(src, ctx):
        task_id = ctx['task_id']
        remove_resume_info(server, task_id)
        src.reply(f'§a已放弃断点任务: {task_id}')
    return abort_cmd

def register_resume_commands(builder, server):
    builder.arg('task_id', str)
    builder.command('!!cb continue <task_id>', continue_cmd_factory(server))
    builder.arg('task_id', str)
    builder.command('!!cb abort <task_id>', abort_cmd_factory(server))
