from mcdreforged.api.all import *

def register_cb_command(server, config, start_backup, stop_backup, list_backups, status_backup, query_backup_records, config_setter, continue_cmd, abort_cmd):
    # !!cb config ...
    config_branch = (
        Literal('config')
        .then(Literal('bucketName').then(Text('bucketName').runs(lambda src, ctx: config_setter(src, 'bucketName', ctx['bucketName']))))
        .then(Literal('region').then(Text('region').runs(lambda src, ctx: config_setter(src, 'region', ctx['region']))))
        .then(Literal('targetBackupPath').then(Text('targetBackupPath').runs(lambda src, ctx: config_setter(src, 'targetBackupPath', ctx['targetBackupPath']))))
        .then(Literal('localBackupPath').then(Text('value').runs(lambda src, ctx: config_setter(src, 'localBackupPath', ctx['localBackupPath']))))
        .then(Literal('fileNamePrefix').then(Text('fileNamePrefix').runs(lambda src, ctx: config_setter(src, 'fileNamePrefix', ctx['fileNamePrefix']))))
        .then(
            Literal('accesskey')
            .then(Literal('id').then(Text('AccessKeyID').runs(lambda src, ctx: config_setter(src, 'accesskey id', ctx['AccessKeyID']))))
            .then(Literal('secret').then(Text('AccessKeySecret').runs(lambda src, ctx: config_setter(src, 'accesskey secret', ctx['AccessKeySecret']))))
        )
        .then(Literal('deleteLocalAfterUpload').then(Boolean('Boolean').runs(lambda src, ctx: config_setter(src, 'deleteLocalAfterUpload', ctx['Boolean']))))
        .then(Literal('localBackupKeepCount').then(Text('value').runs(lambda src, ctx: config_setter(src, 'localBackupKeepCount', ctx['value']))))
        .then(Literal('backupSourceDir').then(Text('abs_path').runs(lambda src, ctx: config_setter(src, 'backupSourceDir', ctx['abs_path']))))
        .then(Literal('multipartChunkSize').then(Text('value').runs(lambda src, ctx: config_setter(src, 'multipartChunkSize', ctx['value']))))
    )
    # 主命令树
    tree = (
        Literal('!!cb')
        .runs(lambda src, ctx: src.reply('§a[CloudBackup] 用法: !!cb <start|stop|list|status|history|config ...|continue <id>|abort <id>>'))
        .then(Literal('start').runs(lambda src, ctx: start_backup(server, src, config)))
        .then(Literal('stop').runs(lambda src, ctx: stop_backup(server, src)))
        .then(Literal('list').runs(lambda src, ctx: list_backups(server, src, config)))
        .then(Literal('status').runs(lambda src, ctx: status_backup(server, src)))
        .then(Literal('history').runs(lambda src, ctx: query_backup_records(server, src, 5)))
        .then(config_branch)
        .then(Literal('continue').then(Text('task_id').runs(continue_cmd)))
        .then(Literal('abort').then(Text('task_id').runs(abort_cmd)))
    )
    server.register_command(tree)
