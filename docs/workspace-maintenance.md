# 工作区维护

本页说明 superproject 的日常维护动作：什么时候改顶层，怎样更新子模块版本，以及发布前应该跑哪些检查。

## 什么时候改顶层

适合放在顶层的改动：

- 跨仓库 contract、工作流、release checklist 或 doctor 规则。
- 子模块 gitlink，也就是锁定 `market-data-platform`、`cross-sectional-trees`、`quant-execution-engine` 的具体提交。
- 顶层 `docs/` 中的协作说明和版本组合记录。
- 只依赖公开 CLI 或文档化文件输出的轻量检查脚本。

不适合放在顶层的改动：

- 子项目内部架构、依赖、lint、type check 或业务参数。
- 市场数据本体、研究输出、provider cache、交易审计日志。
- 直接导入子模块内部 Python 包的顶层脚本。
- 自动绕过执行引擎门禁的模拟盘或实盘操作。

## 子模块版本锁定

本仓库通过 Git submodule 固定三个子项目的提交版本。子项目仍在各自目录里独立开发、测试和发布；顶层仓库记录的是“这几个提交可以一起使用”的组合。

日常开发通常在子项目目录中完成：

```bash
cd cross-sectional-trees
git status
git add <files>
git commit -m "..."
git push
```

确认子项目版本后，再回到顶层仓库提交新的子模块指针：

```bash
cd ..
git status
git add cross-sectional-trees
git commit -m "Bump cross-sectional-trees"
git push
```

如果一次更新多个子项目，建议先分别完成子项目自己的测试，再回到顶层更新所有相关 gitlink，并在 [version-matrix.md](version-matrix.md) 记录验证结论。

## 顶层健康检查

顶层检查只验证工作区层面的边界：

```bash
python scripts/workspace_doctor.py
python scripts/smoke_contracts.py
python -m unittest discover -s tests
python scripts/run_quality_checks.py --profile hard
```

发布前或更新子模块指针前建议使用严格模式：

```bash
python scripts/workspace_doctor.py --strict
python scripts/smoke_contracts.py --strict
```

## 委托子项目检查

如果已经安装了各子项目依赖，可以从顶层统一委托子项目自己的检查：

```bash
python scripts/run_submodule_checks.py --list-profiles
python scripts/run_submodule_checks.py --profile smoke
python scripts/run_submodule_checks.py --profile full --dry-run
```

配置文件是 [../scripts/submodule_checks.json](../scripts/submodule_checks.json)。顶层脚本只进入对应子项目目录并运行 manifest 中声明的命令；`ruff`、`pytest`、`pyright`、`mypy` 等规则仍由各子项目自己的配置和依赖环境决定。

检查分为 hard、advisory 和 manual 三类。仓库级 ownership、secret scan、依赖审计 baseline
以及执行引擎迁移后的 mypy advisory 见 [quality-governance.md](quality-governance.md)。

## 常见术语

| 术语 | 在本工作区中的意思 |
| --- | --- |
| submodule | Git 子模块；顶层仓库用它锁定各子项目的具体提交。 |
| contract | 文件约定；下游按这个约定读取上游输出。 |
| registry | 已发布数据资产索引，主要用于查找和审计。 |
| `targets.json` | 研究系统导出的目标持仓文件，执行引擎按它生成调仓计划。 |
| paper / live | 模拟盘 / 实盘。实盘必须通过执行引擎自己的安全门禁。 |
| lineage | 记录一个输出来自哪些输入、配置和运行过程的审计信息。 |
