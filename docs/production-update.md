# Production 更新规范

## 目录职责

`/home/richard/code/research-workspace` 是完整的 `main` 主工作树，用于阅读、检查和创建新的 agent worktree。

`/home/richard/code/.worktrees/` 用于并行开发。worktree 可以被清理，因此未提交代码不能只保存在这里。

`/home/richard/code/production/` 是定时任务使用的发布根目录。两个项目分别使用：

```text
/home/richard/code/production/research-workspace/releases/<commit>/
/home/richard/code/production/research-workspace/current -> releases/<commit>
/home/richard/code/production/market-intel/releases/<commit>/
/home/richard/code/production/market-intel/current -> releases/<commit>
```

release worktree 保持 clean 和 detached，不在其中直接开发。服务只引用 `current`。

## 为什么 push 后还要更新 production

`git push` 只把提交和分支引用发送到远端。已经 checkout 的 production worktree 不会因为远端 `main` 前进而自动改变。这样设计是为了让运行中的版本保持稳定，避免 agent 或远端新提交未经检查直接进入日报、周报和数据任务。

## 标准流程

代码合入远端 `main` 并确认检查通过后，在主机上执行：

```bash
/home/richard/code/research-workspace/scripts/check-production-updates.sh
/home/richard/code/research-workspace/scripts/promote-production.sh --dry-run
/home/richard/code/research-workspace/scripts/promote-production.sh
```

更新检查只执行 fetch，不切换 production。promotion 脚本会：

1. 使用锁避免并发 promotion。
2. 拉取两个仓库的远端 `main`。
3. 在 `releases/<commit>` 创建新的 detached worktree。
4. 按父仓库 gitlink 初始化并更新所有 submodule，并准备运行环境。
5. 输出两个仓库的 revision manifest。
6. 原子切换 `current`，保留之前的 release。

如果检查失败，脚本会停止，不会清理或覆盖 production 中的内容。更新前后的 manifest 应随运行记录保存，便于复现和回滚。

## 回滚

先确定需要恢复的 release 目录，再切换 `current`：

```bash
ln -sfn releases/<known-good-commit> /home/richard/code/production/research-workspace/current
git -C /home/richard/code/production/research-workspace/current submodule update --init --recursive
```

回滚后重新运行对应的日报或周报 smoke check，确认服务仍读取该版本的公开 artifact 和 receipt。

## 服务约束

定时任务必须引用 `/home/richard/code/production/<repo>/current/` 下的运行代码。研究实验可以使用独立 worktree，但不得被 cron 或 systemd 无意间调用。

## 定期检查策略

`research-production-update-check.timer` 只负责定期 fetch 并把新版本写入 systemd journal。它不会自动切换 `current`。发现更新后，由人工或 agent 审核，再执行 promotion。

旧 release 在 promotion 成功后按保留策略自动清理。每周的
`production-maintenance.timer` 还会执行一次同样的清理，作为没有新 promotion 时的兜底。
默认保留最近 5 个 release，但共享虚拟环境默认只保留当前 release 和最新的一个回滚
release 使用的环境。可通过 `PRODUCTION_KEEP_VENVS` 或 `--keep-venvs` 调整，最小值为 2。
更老 release 仍保留代码、锁文件和 manifest，需要回滚时由 promotion 或维护流程按锁文件重建环境。

查看虚拟环境清理计划：

```bash
bash /home/richard/code/research-workspace/scripts/maintain-production.sh \
  --repo all --keep-venvs 2 --dry-run
```

更新检查和 promotion 使用同一个 fetch 入口。配置的 Git remote 失败时，会针对 GitHub
仓库依次尝试 GitHub CLI 提供的认证 HTTPS、SSH 和普通 HTTPS。fallback 仍然只更新本地
remote-tracking ref，不会修改 remote 配置。所有方式失败时会汇总错误并停止流程。

现有 release 的实体 `.venv` 可以用以下命令分批迁移。默认每次最多处理 2 个非 current
环境，先 dry-run 再执行：

```bash
bash /home/richard/code/research-workspace/scripts/migrate-production-venvs.sh --dry-run
bash /home/richard/code/research-workspace/scripts/migrate-production-venvs.sh --max 2
```

安装每周维护 timer：

```bash
bash /home/richard/code/research-workspace/scripts/install-production-maintenance.sh --dry-run
bash /home/richard/code/research-workspace/scripts/install-production-maintenance.sh
```
