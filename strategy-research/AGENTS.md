# AGENTS.md

本文件说明 `strategy-research` 的协作边界与开发流程。它是顶层 `research-workspace`
的 tracked 目录，不是独立子模块，没有自己的 Git 历史，改动随顶层提交与合并。

## 仓库职责

本目录是工作区内策略身份、投资假设、生命周期、评审结论和证据导航的权威入口。
可执行代码仍按职责放在各子模块，策略是否生产化由 `catalog.json` 的显式字段决定，
代码位置不表达生命周期。

- 策略想法、参数语义、生命周期、评审结论、证据索引归本目录
- 被生产进程导入的运行时代码不归本目录（例如 `style_factors` 表现层只复用内核，
  不自写因子计算）
- 跨仓计算内核归 `alpha-research`、组合回测归 `portfolio-backtester`、编排发布归
  `strategy-pipeline`、数据归 `market-data-platform`、执行归 `quant-execution-engine`

详细定位与策略地图见 `README.md`，三层职责边界见 `README.md` 的对应章节。

## Git 工作流

本目录随顶层 `research-workspace` 管理，不独立开 worktree 或拉取请求。多个 agent
并行开发时，每个 agent 必须在不同的顶层 worktree 内改动本目录文件，各自开顶层
PR，避免在同一检出目录竞争同一组文件。

流程遵循顶层 `AGENTS.md` 的 Git 工作流章节（远端名为 `github`，`main` 受保护，改动
走 worktree + PR）。要点：

1. 在顶层目录新建 worktree 与功能分支：

   ```bash
   git fetch github
   git worktree add <path> -b feat/<主题> github/main
   ```

2. 在 worktree 内改动 `strategy-research/` 下文件，运行本目录检查。
3. 提交并推送功能分支：

   ```bash
   git push -u github feat/<主题>
   ```

4. 用 `gh pr create` 开顶层拉取请求，合并到 `main`。
5. 合并完成后删除功能分支并移除 worktree。

本目录有独立的 `pyproject.toml` 与 `tests/`，pre-push 会额外运行 `research-layer-tests`
与 `research-layer-quality` 门禁。改动本目录 Python 或文档时，至少运行：

```bash
uv run --project strategy-research --extra dev python -m pytest tests -q
```

同一仓库的多个 worktree 共享主工作树的 `core.hooksPath` 配置。不要在独立 worktree
内重装或改写 hook。新的并行任务必须新建 worktree，不要直接在主检出目录的 `main`
上提交改动。

## 文档规则

- 中文正文使用中文标点，避免双引号、加粗、分号和破折号
- 避免中英混杂长句、翻译腔和先否定再转折的表达
- 命令、路径、配置键和 API 名称保留行内代码
- 文档中的事实必须能从代码或测试核对
- 阶段记录和历史证据放入 `archive/` 或 `evidence/`

## 编辑规则

- 修改 `catalog.json` 时同步更新 `README.md` 的策略地图与对应 `strategies/*/README.md`
- 不把通用数据、alpha、统计、组合或执行能力写入本目录
- 修改 Python 文件后运行与影响范围匹配的测试
- 修改文档后至少检查路径、配置引用和测试入口
