import os
from datetime import datetime
try:
    import alibabacloud_oss_v2 as oss2
except ImportError:
    oss2 = None

def get_oss_client(config):
    oss_cfg = oss2.config.load_default()
    oss_cfg.region = config.Endpoint.replace('oss-', '').replace('.aliyuncs.com', '')
    oss_cfg.credentials_provider = oss2.credentials.StaticCredentialsProvider(
        config.AccessKeyID, config.AccessKeySecret
    )
    return oss2.Client(oss_cfg)

def upload_file(client, config, local_zip_path, oss_path):
    from alibabacloud_oss_v2 import PutObjectRequest
    file_size = os.path.getsize(local_zip_path)
    upload_start = datetime.now()
    with open(local_zip_path, 'rb') as f:
        req = PutObjectRequest(
            bucket=config.BucketName,
            key=oss_path,
            body=f
        )
        client.put_object(req)
    upload_end = datetime.now()
    return file_size, upload_start, upload_end

def upload_file_multipart(client, config, local_zip_path, oss_path, progress_callback=None, resume_info=None, stop_flag=None):
    """
    分片上传，支持断点续传和进度回调。
    progress_callback: (uploaded_bytes, total_bytes, part_number, total_parts, resume_info) -> None
    resume_info: dict, 断点续传信息（如有）
    stop_flag: threading.Event()，如被 set() 则中断上传
    """
    import alibabacloud_oss_v2 as oss
    file_size = os.path.getsize(local_zip_path)
    chunk_size = getattr(config, 'MultipartChunkSize', 5*1024*1024)
    upload_start = datetime.now()
    upload_id = None
    upload_parts = []
    uploaded_bytes = 0
    total_parts = (file_size + chunk_size - 1) // chunk_size
    try:
        # 1. 初始化分片上传或恢复
        if resume_info and resume_info.get('upload_id') and resume_info.get('uploaded_parts'):
            upload_id = resume_info['upload_id']
            upload_parts = [oss.UploadPart(part_number=p['part_number'], etag=p['etag']) for p in resume_info['uploaded_parts']]
            start_part = len(upload_parts) + 1
        else:
            result = client.initiate_multipart_upload(oss.InitiateMultipartUploadRequest(
                bucket=config.BucketName,
                key=oss_path,
            ))
            upload_id = result.upload_id
            upload_parts = []
            start_part = 1
        # 2. 逐分片上传
        part_number = start_part
        with open(local_zip_path, 'rb') as f:
            for start in range((part_number-1)*chunk_size, file_size, chunk_size):
                if stop_flag and stop_flag.is_set():
                    # 返回断点信息
                    return uploaded_bytes, upload_start, datetime.now(), {
                        'upload_id': upload_id,
                        'uploaded_parts': [{'part_number': p.part_number, 'etag': p.etag} for p in upload_parts],
                        'oss_path': oss_path,
                        'local_zip_path': local_zip_path,
                        'file_size': file_size,
                        'chunk_size': chunk_size
                    }
                n = min(chunk_size, file_size - start)
                reader = oss.io_utils.SectionReader(oss.io_utils.ReadAtReader(f), start, n)
                up_result = client.upload_part(oss.UploadPartRequest(
                    bucket=config.BucketName,
                    key=oss_path,
                    upload_id=upload_id,
                    part_number=part_number,
                    body=reader
                ))
                upload_parts.append(oss.UploadPart(part_number=part_number, etag=up_result.etag))
                uploaded_bytes = min(part_number*chunk_size, file_size)
                if progress_callback:
                    # 实时传递断点 resume_info
                    progress_callback(uploaded_bytes, file_size, part_number, total_parts, {
                        'upload_id': upload_id,
                        'uploaded_parts': [{'part_number': p.part_number, 'etag': p.etag} for p in upload_parts],
                        'oss_path': oss_path,
                        'local_zip_path': local_zip_path,
                        'file_size': file_size,
                        'chunk_size': chunk_size
                    })
                part_number += 1
        # 3. 完成分片上传
        parts = sorted(upload_parts, key=lambda p: p.part_number)
        result = client.complete_multipart_upload(oss.CompleteMultipartUploadRequest(
            bucket=config.BucketName,
            key=oss_path,
            upload_id=upload_id,
            complete_multipart_upload=oss.CompleteMultipartUpload(parts=parts)
        ))
        upload_end = datetime.now()
        return file_size, upload_start, upload_end, None
    except Exception as e:
        # 失败时尝试中止分片上传，避免OSS垃圾分片
        if upload_id:
            try:
                client.abort_multipart_upload(oss.AbortMultipartUploadRequest(
                    bucket=config.BucketName,
                    key=oss_path,
                    upload_id=upload_id
                ))
            except Exception:
                pass
        # 返回断点信息用于续传
        return uploaded_bytes, upload_start, datetime.now(), {
            'upload_id': upload_id,
            'uploaded_parts': [{'part_number': p.part_number, 'etag': p.etag} for p in upload_parts],
            'oss_path': oss_path,
            'local_zip_path': local_zip_path,
            'file_size': file_size,
            'chunk_size': chunk_size
        }

def check_cloud_file_size(client, config, oss_path):
    oss_file_size = None
    for page in client.list_objects_v2_paginator().iter_page(
        oss2.ListObjectsV2Request(bucket=config.BucketName, prefix=oss_path)):
        if page.contents:
            for o in page.contents:
                if o.key == oss_path:
                    oss_file_size = o.size
                    break
        if oss_file_size is not None:
            break
    return oss_file_size

def list_backups(client, config):
    paginator = client.list_objects_v2_paginator()
    backups = []
    total_size = 0
    for page in paginator.iter_page(oss2.ListObjectsV2Request(bucket=config.BucketName, prefix=config.BackupPath)):
        if page.contents:
            for o in page.contents:
                size_mb = round(o.size / 1024 / 1024, 2)
                backups.append((o.key, size_mb))
                total_size += o.size
    return backups, total_size
