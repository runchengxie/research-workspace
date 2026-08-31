# Production 更新规范

## 目录职责

`/home/richard/code/research-workspace` 是完整的 `main` 主工作树，用于阅读、检查和创建新的 agent worktree。

`/home/richard/code/.worktrees/` 用于并行开发。worktree 可以被清理，因此未提交代码不能只保存在这里。

`/home/richard/code/production/research-workspace` 是定时任务使用的发布副本。它保持 clean 和 detached，不在其中直接开发。

## 为什么 push 后还要更新 production

`git push` 只把提交和分支引用发送到远端。已经 checkout 的 production worktree 不会因为远端 `main` 前进而自动改变。这样设计是为了让运行中的版本保持稳定，避免 agent 或远端新提交未经检查直接进入日报、周报和数据任务。

## 标准流程

代码合入远端 `main` 并确认检查通过后，在主机上执行：

```bash
/home/richard/code/research-workspace/scripts/promote-production.sh --dry-run
/home/richard/code/research-workspace/scripts/promote-production.sh
```

脚本会：

1. 检查 production 没有未提交或未追踪内容。
2. 拉取远端 `main`。
3. 将父仓库切换到远端 `main` 的 detached 提交。
4. 按父仓库 gitlink 初始化并更新所有 submodule。
5. 输出父仓库和 submodule revision manifest。

如果检查失败，脚本会停止，不会清理或覆盖 production 中的内容。更新前后的 manifest 应随运行记录保存，便于复现和回滚。

## 回滚

先确定需要恢复的父仓库提交，再临时指定 revision：

```bash
git -C /home/richard/code/production/research-workspace fetch github
git -C /home/richard/code/production/research-workspace checkout --detach <known-good-commit>
git -C /home/richard/code/production/research-workspace submodule update --init --recursive
```

回滚后重新运行对应的日报或周报 smoke check，确认服务仍读取该版本的公开 artifact 和 receipt。

## 服务约束

定时任务必须引用 `/home/richard/code/production/` 下的运行代码。研究实验可以使用独立 worktree，但不得被 cron 或 systemd 无意间调用。
