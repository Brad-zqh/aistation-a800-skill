---
name: aistation-a800
description: Connect to and operate authorized university AIStation A800 GPU jobs from a local machine, including persistent environments, verified SSH tunnels, reproducible LLM services, checkpoint monitoring and owned-resource recovery. Use for college GPU/AIStation workflows, not unrelated GPU purchases or local-only model selection.
---

# 学院 AIStation A800

把已获授权的运算可靠地转到学院 GPU，区分“平台任务、SSH 隧道、服务进程、实际计算和独立验收”。先读当前项目 AGENTS.md、README、冻结计划、状态及完成收据；已有授权继续有效，活跃任务不重复启动。

## 先选入口

- 已有任务/续跑：读 [运行与恢复](references/operations.md)，先实查身份、完整检查点和收据，正常进度保持安静。
- 新部署、保存镜像或正式任务：读 [部署要点](references/deployment.md)。只操作授权的任务和项目，不把临时开发实例当持续计算任务。
- LLM 标注或受限数据：再读 [复现与数据边界](references/reproducibility.md)，不要用模型一致性替代任务语义准确率。

连接参数仅从机器私有 profile 读取：优先环境变量 `AISTATION_A800_PROFILE`，其次本机 `E:/CodexData/private/aistation-a800/current.local.json`。文件缺失时用 [profile 示例](references/profile.example.json) 建立自己的配置；公有 skill 不保存真实地址、账户、密钥、口令或项目样本。认证已配置时直接使用，不让用户重复提供。截图里出现的口令不复制进代码或聊天。

## 只读核查助手

使用项目指定 Python；本用户机器上的临时文件、缓存和生成物实际写 E 盘，CPU 默认限2线程。帮助脚本仅使用标准库，不启动模型、重启服务或更改平台任务。

```powershell
$profilePath = 'E:/CodexData/private/aistation-a800/current.local.json'
& $projectPython -B -X utf8 scripts/a800_probe.py local --profile $profilePath
& $projectPython -B -X utf8 scripts/a800_probe.py remote --profile $profilePath
& $projectPython -B -X utf8 scripts/a800_probe.py count --profile $profilePath --path $checkpointPath
```

这里 `scripts/...` 相对于本 skill 目录；以实际绝对路径调用。`$projectPython` 从现有项目规则取得，不默认用共享 Python。`remote --hash-models` 在上传后或权重有变化时重算明确配置的权重 SHA；普通监测不反复扫描大权重。`count` 仅允许 profile 私有根下的 `NO_TEXT.jsonl`，只计完整行、不截断活跃写入。

## 行动边界

用正式任务当前映射的端口、已认证冻结的 known_hosts 和任务专用密钥。主机核验失败时核对平台证据，不能 `StrictHostKeyChecking=no`、清空 known_hosts 或换回旧开发端口。服务只绑定远端和本地 `127.0.0.1`，通过 SSH 传输敏感正文。

先验证资源属于谁：低 free 显存可能来自本任务已加载的模型；空闲显存也不表示 GPU 算力空闲。核 cgroup 限额和实际使用，不能只看宿主机 psutil 内存。不给其他实验腾显存或杀进程。只有确认自己的 worker 已退出、没有所属 child、没有完成收据且不会重复执行时，才按原入口恢复；正常 exit0 与关闭的完成服务无需恢复。

状态检查失败不等于实验失败。错误只报告安全类型、阶段和代码位置，不输出可能带正文/凭据的异常字符串。完成以成员、有效完整记录、重启、源和运行哈希、独立数值重放及真实收据判断，不能凭平台显示“运行中”、HTTP次数或文件数下结论。

默认仅在新故障、需要用户行动、核实恢复或整个登记范围完成时报告并去重。若需要自动跟进，使用客户端正式自动化工具，把长约束保存在项目 README，自动提示只引用该位置。释放自己的正式 GPU 任务和隧道前先完成收据、报告及所需备份；不影响其他仍获授权的实验。
