# CloudBackup

> 自动备份 Minecraft 存档到阿里云 OSS 的 MCDR 插件

## 功能特性
- 支持备份 Minecraft 存档到阿里云 OSS
- 分片上传、断点续传、上传进度实时回显
- 上传完成后可自动删除本地压缩包，或自动保留最新 N 个本地包
- 插件卸载/重载/服务端关闭时自动检测未完成任务并保存断点，重启后可续传或放弃
- 配置项可通过MCDR指令动态设置

## 目录结构
```
cloudbackup/
    cloudbackup.py         # 插件入口
    config.py             # 配置模型
    core/
        backup_task.py    # 备份主流程
        core.py           # 统一接口导出
        resume_util.py    # 断点信息管理
        continue_abort.py # 断点续传/放弃命令
    cmd/
        command_tree.py   # 命令树注册
        list_cmd.py       # 备份列表命令
    model/
        record.py         # 备份记录管理
    oss/
        oss_util.py       # OSS 上传工具
    utils/
        utils.py          # 工具函数
    resume/               # 断点续传信息存放目录
    backups/              # 本地备份/压缩包目录
mcdreforged.plugin.json
requirements.txt
```

## 安装与依赖
1. 本项目依赖`alibabacloud-oss-v2`
2. 将release中的.mcdr文件放入 MCDR 服务器的 plugins 目录。
3. 配置 `config.json`（首次启动会自动生成）。

## 配置说明（config.json）

同时也提供通过指令修改配置的途径，见下文。

- `AccessKeyID`/`AccessKeySecret`：阿里云 OSS 访问密钥
- `BucketName`：OSS 存储桶名
- `Endpoint`：OSS 区域节点（如 oss-cn-hangzhou.aliyuncs.com）
- `BackupPath`：OSS 备份路径前缀
- `LocalBackupDir`：本地备份目录（如 backups）
- `ZipPrefix`：压缩包文件名前缀
- `DeleteLocalAfterUpload`：上传后自动删除本地包（true/false）
- `LocalBackupKeepCount`：本地最多保留 N 个压缩包
- `BackupSourceDir`：自定义需要备份的目录（绝对路径，留空则默认备份 ./server/world 目录）
- `MultipartChunkSize`：分片上传的单片大小（单位：字节，建议 5~50MB，默认 10MB）。可通过指令动态调整。

## 常用命令
- `!!cb start`         启动一次备份

  本命令将配置文件中`BackupSourceDir`所指路径的所有文件（session.lock除外）复制到`LocalBackupDir`并重命名添加随机生成的唯一任务ID（`Task ID`），随后将此文件夹添加至压缩文件，重命名为`[ZipPrefix]-[YYYYMMDD]-[HHmmss]-[Task ID].zip`，随后尝试分片上传。分片大小可以通过配置文件中的`MultipartChunkSize`指定。

- `!!cb stop`          请求停止备份
  
- `!!cb list`          查看云端备份列表
  从云端获取文件列表

- `!!cb status`        查看当前备份状态

- `!!cb history`       查看本地备份历史

- `!!cb config <项> <值>` 设置配置项

- `!!cb continue <id>` 断点续传指定任务

- `!!cb abort <id>`    放弃断点任务

### 配置项动态设置示例
- `!!cb config bucketName my-bucket`

- `!!cb config region cn-hangzhou`

  此配置会自动转义为`Endpoint`

- `!!cb config localBackupPath backups`

- `!!cb config fileNamePrefix world`

- `!!cb config deleteLocalAfterUpload true/false`

  设为true时，每当一个备份文件上传完毕，会尝试将本地相应的zip文件删除

- `!!cb config localBackupKeepCount 5`

  本地最多存储多少个备份zip文件，超出此数字时会尝试将最早的删除

- `!!cb config backupSourceDir C:/absolute/path/to/your/world`   设置自定义备份源目录，需要绝对路径

- `!!cb config multipartChunkSize 10485760`   设置分片大小为 10MB

## 分片上传与断点说明
- 分片上传支持自定义分片大小（`MultipartChunkSize`），可通过指令动态调整，单位为字节。
- 断点文件（如 `resume/c228fcea.json`）中会记录 upload_id、已上传分片、分片大小、zip 路径等信息，便于多次中断与恢复。

## 断点续传说明
- 上传过程中如遇插件卸载/重载/服务端关闭，断点信息会自动保存在 `resume/` 目录下。
- 重启后会自动提示断点任务，可用 `!!cb continue <id>` 续传，或 `!!cb abort <id>` 放弃。
- 支持多次中断与恢复，断点文件会持续更新。

## 备份源目录自定义说明
- 默认备份 `server/world` 目录。
- 可通过 `!!cb config backupSourceDir <绝对路径>` 指定任意需要备份的文件夹。
- 适用于多世界、特殊存档或自定义数据目录的备份需求。

## 适配环境
- MCDReforged >= 2.1.0
- Python 3.9+
- 阿里云 OSS Python SDK（alibabacloud-oss-v2）

## 开发/维护
- 作者：caikun233 in GRUnion
- 欢迎issues

