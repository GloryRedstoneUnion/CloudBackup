from mcdreforged.api.utils.serializer import Serializable

class CloudBackupConfig(Serializable):
    AccessKeyID: str
    AccessKeySecret: str
    BucketName: str
    Endpoint: str
    BackupPath: str = '/'
    LocalBackupDir: str = './backups'
    ZipPrefix: str = 'world'
    MultipartChunkSize: int = 10 * 1024 * 1024  # 分片大小，单位字节，默认10MB
    DeleteLocalAfterUpload: bool = False  # 上传后删除本地压缩包
    LocalBackupKeepCount: int = 5        # 本地最多保留几个压缩包
    BackupSourceDir: str = ''  # 新增，备份源目录，留空时自动推断为默认 world 目录
