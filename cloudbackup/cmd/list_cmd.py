from cloudbackup.oss.oss_util import get_oss_client, list_backups as oss_list_backups
try:
    import alibabacloud_oss_v2 as oss2
except ImportError:
    oss2 = None

def list_backups(server, src, config):
    if not oss2:
        src.reply('§c请先安装 alibabacloud_oss_v2: pip install alibabacloud_oss_v2')
        return
    try:
        client = get_oss_client(config)
        backups, total_size = oss_list_backups(client, config)
        if backups:
            lines = [f"§e云端备份列表 (共{len(backups)}个, 总计§b{round(total_size/1024/1024,2)}MB§e):"]
            for name, size in backups:
                lines.append(f"§b{name} §8| §e{size}MB")
            src.reply('\n'.join(lines))
        else:
            src.reply('§7云端无备份文件')
    except Exception as e:
        src.reply('§c获取备份列表失败: {}'.format(e))
