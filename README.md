# 学院 A800 / AIStation Codex Skill

可复用的学院GPU工作流：正式任务部署、可信SSH连接、持久环境、LLM服务、检查点监测及仅本任务的恢复与收尾。

Skill 位于 [`skills/aistation-a800`](skills/aistation-a800/SKILL.md)，安装后可用 `$aistation-a800` 调用。支持正常自动发现，不等于授权提交或停止任意GPU任务。

## 安装

在 Codex 的 skill-installer 中指定此仓库及路径 `skills/aistation-a800`，或使用其 `install-skill-from-github.py --repo Brad-zqh/aistation-a800-skill --path skills/aistation-a800 --dest E:/CodexData/.codex/skills`。Windows 示例采用E盘；在这台机器设置 TEMP/TMP/TMPDIR 到E盘再执行。

认证与机器设置单独保存在仓库外的 `AISTATION_A800_PROFILE` 指向的 JSON；字段示例在 skill 的 references/profile.example.json。公有仓库没有真实地址、口令、密钥、数据、模型或运行检查点。

## 验证

标准库测试：`python -B -m unittest discover -s tests -v`。只读助手支持 `local`、`remote`、`count`，没有默认启动/终止任务或改配置功能。发布前另外使用 Codex skill-creator 的 quick_validate 校验。

技术经验来自已执行的单张A80080GB任务，但平台API、排队、映射端口、镜像和配额必须以当前环境为准。它不承诺模型语义准确率或研究性能。

已补充学院教程的界面操作映射：ATrust/平台分层接入、开发测试、保存镜像、正式任务的脚本/命令与持久挂载、SFTP完整性、离线Linux依赖及日志断点。教程中的原视频、截图、账户和内网配置不随仓库发布。

`scripts/a800_capacity.py --profile <私有profile> --samples 12 --interval 1`可在已授权任务中只读核连续GPU计算/显存/功耗、cgroup和已登记进程归属。它区分整卡采样与具体任务吞吐，也保留未知owner；不申请新卡或终止作业。
