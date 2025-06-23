from .backup_task import do_backup, start_backup, stop_backup, status_backup
from ..cmd.list_cmd import list_backups
from ..model.record import query_backup_records
from .continue_abort import continue_cmd_factory, abort_cmd_factory, register_resume_commands

# 兼容原有接口名
#list_backups = list_backups_cmd

# ...如需其它接口可继续导入
