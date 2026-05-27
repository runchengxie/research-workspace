# Release Checklist

本清单用于 bump submodule 指针或声明一组 workspace 版本组合已验证前的人工检查。

## Workspace

- [ ] 顶层 `git status --short` 只包含预期的文档、脚本、测试或 submodule 指针变更。
- [ ] `git submodule status` 中所有 submodule 指针符合本次要锁定的版本。
- [ ] `python scripts/workspace_doctor.py --strict` 通过，或所有 warning 都有明确记录。
- [ ] `python scripts/print_version_matrix.py` 输出已复制到 [version-matrix.md](version-matrix.md) 或对应发布记录。
- [ ] 顶层没有 `.env`、`.env.*`、`artifacts/`、`outputs/`、`data/`、`cache/` 等误提交内容。

## Data Contracts

- [ ] `DATA_PLATFORM_ROOT` 指向本次验证使用的共享资产根目录。
- [ ] `metadata/current_assets/hk_current.json` 存在并指向预期 HK 资产版本。
- [ ] 如本次涉及 CN 数据，`metadata/current_assets/cn_current.json` 存在并指向预期 CN 资产版本。
- [ ] `metadata/dataset_registry.csv` 已更新或确认无需更新。
- [ ] `marketdata migration status --json` 可运行，并且 transition backend 状态符合预期。

## Research Contract

- [ ] `cross-sectional-trees` 已在子项目内完成相关研究、测试或人工验证。
- [ ] `positions_current*.csv` / live holdings 来源明确。
- [ ] `cstree export-targets` 已生成 canonical `targets.json`。
- [ ] `targets.json.lineage.json` 已保留，并包含 run、input、config、数据资产 lineage 信息。
- [ ] 导出的目标是 long-only，且权重、敞口、日期口径符合执行侧要求。

## Execution Handoff

- [ ] `quant-execution-engine` 已验证能解析本次 `targets.json`。
- [ ] 如涉及港股，HKD 到 USD FX 配置已显式提供或确认执行侧会阻断。
- [ ] 只做 dry-run / parser 验证时，没有使用 `--execute`。
- [ ] paper broker 验证如已执行，证据文件和操作记录已归档。
- [ ] live broker 路径未被顶层脚本自动触发。
- [ ] 任何实盘操作都由执行系统自己的 preflight、`QEXEC_ENABLE_LIVE=1` 和人工监督流程控制。

## Documentation

- [ ] [contracts.md](contracts.md) 仍准确描述跨模块边界。
- [ ] [platform-workflow.md](platform-workflow.md) 的执行验证状态没有夸大 paper / live 成熟度。
- [ ] [bootstrap.md](bootstrap.md) 中的初始化命令仍符合子项目当前依赖定义。
- [ ] 本次版本组合和验证结论已写入 [version-matrix.md](version-matrix.md)。
