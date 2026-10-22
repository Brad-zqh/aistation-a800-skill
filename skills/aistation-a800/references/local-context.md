# 本机接入、平台与项目运行登记

本机已有连接时先复用，不向用户重复索取已登记信息。公有skill保存流程、字段和本机配置位置；真实地址、端口、认证文件引用和项目挂载由仓库外私有配置提供，不把密码或平台令牌写入公有skill。

## 信息入口

1. 环境变量`AISTATION_A800_PROFILE`；未设置则`E:/CodexData/private/aistation-a800/current.local.json`。
2. 默认同目录`operational-context.local.json`：已有平台操作脚本、记录来源、持久环境和目录的索引。先查索引指向的现有运维记录，再请求缺失信息；不扫描/导出其他项目正文。
3. profile的`project_runtimes`：按项目key登记持久root、python、启动入口、worker/supervisor状态相对路径、数据和输出目录、资源预算及所属平台任务。当前profile的默认remote可能属于另一项目，不能直接把那个项目的模型/输出当成本项目任务。
4. 用户2026-10-22提供的学院操作材料已登记于同目录`usage_materials_20261022/inventory.local.json`和`observations.local.json`，包含平台入口候选、凭据原件引用及录屏操作依据。先查材料和既存操作记录，不重复询问已有地址；教学账号/镜像/端口不能覆盖当前项目身份，来源存在也不等于当前认证已通过。

`python -B scripts/a800_context.py context`只报告入口是否配置和引用文件是否存在，不输出认证内容。`python -B scripts/a800_context.py worker --project <key>`只读核当前项目子作业身份及安全状态字段；返回结果不代表已通过科学验收。

## profile补充字段

保留既存schema_version、ssh、remote等字段，新增字段可以渐进填写，不改认证参数：

- `platform.base_url`、`task_console_url`：从实际平台界面或已有记录获得，附来源与核实时间；未知保持空，不能编造。
- `platform.known_operations_scripts`、`URL_evidence`：已经用过的运维入口及来源。先读具体脚本用途，不盲执行停止、重建、释放或重提其他任务的入口。
- `platform.authentication_reference`：现有浏览器会话或私有认证配置路径。保存引用，不复制口令。
- `project_runtimes.<key>`：`root`、`python`、`worker_state`、`supervisor_state`、`worker_entry`、`startup_entry`、`data_directory`、`output_directory`、`shared_existing_platform_task_authorized`、`platform_task_id`、`platform_task_id_verified`。
- 每次成功部署/恢复后记录真实任务ID（已核时）、镜像/环境版本、挂载、启动命令、当前容器hostname/PID1启动tick、子进程PID/starttick、代码/权重SHA和检查点位置。只能记录已经核实的字段。

没有独立提交视频任务时，写“在既有平台任务中运行的视频子作业”，不能写“新视频正式平台任务已创建”。用户允许共用一张卡时不必新建独立平台任务，但仍应准备可在该任务中执行的持久启动入口、环境和目录，并核其真实进程/吞吐。容器重建不保证手动启动的子作业自动恢复，恢复前核原进程已退出和完整检查点，保留未完成片段，不自动重复崩溃重启。
