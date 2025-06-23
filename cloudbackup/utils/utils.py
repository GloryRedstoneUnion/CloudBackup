import time
import random
import re
try:
    import alibabacloud_oss_v2 as oss2
except ImportError:
    oss2 = None

def gen_task_id(config=None):
    """
    生成唯一任务ID，防止重复（从云端OSS文件名正则提取）
    config: CloudBackupConfig 实例
    """
    existing_ids = set()
    try:
        if oss2 and config:
            oss_cfg = oss2.config.load_default()
            oss_cfg.region = config.Endpoint.replace('oss-', '').replace('.aliyuncs.com', '')
            oss_cfg.credentials_provider = oss2.credentials.StaticCredentialsProvider(
                config.AccessKeyID, config.AccessKeySecret
            )
            client = oss2.Client(oss_cfg)
            paginator = client.list_objects_v2_paginator()
            pattern = re.compile(r'-([0-9a-f]{8})\\.zip$')
            for page in paginator.iter_page(oss2.ListObjectsV2Request(bucket=config.BucketName, prefix=config.BackupPath)):
                if page.contents:
                    for o in page.contents:
                        m = pattern.search(o.key)
                        if m:
                            existing_ids.add(m.group(1))
    except Exception:
        pass
    while True:
        task_id = ''.join(random.choices('0123456789abcdef', k=8))
        if task_id not in existing_ids:
            return task_id

def get_timestamp():
    return time.strftime('%Y%m%d-%H%M%S', time.localtime())
