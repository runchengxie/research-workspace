# 发布检查清单

本清单用于更新子模块指针，或声明一组工作区版本组合已经验证前的人工检查。

## 工作区

- [ ] 顶层 `git status --short` 只包含预期的文档、脚本、测试或子模块指针变更。
- [ ] `git submodule status` 中所有子模块指针符合本次要锁定的版本。
- [ ] `python scripts/workspace_doctor.py --strict` 通过，或所有警告都有明确记录。
- [ ] `python scripts/smoke_contracts.py --strict` 通过，或所有警告都有明确记录。
- [ ] 如本次需要子项目质量 gate，`python scripts/run_submodule_checks.py --profile full` 已运行；失败项能定位到具体子项目和命令。
- [ ] `python scripts/print_version_matrix.py` 输出已复制到 [version-matrix.md](version-matrix.md) 或对应发布记录。
- [ ] 顶层没有 `.env`、`.env.*`、`artifacts/`、`outputs/`、`data/`、`cache/` 等误提交内容。
- [ ] `python scripts/a_share_readiness.py --artifacts-root "$DATA_PLATFORM_ROOT" --evidence-manifest <json> --pretty` 已运行，并保存所需 readiness 结论。

## 数据约定

- [ ] `DATA_PLATFORM_ROOT` 指向本次验证使用的共享资产根目录。
- [ ] `metadata/current_assets/hk_current.json` 存在并指向预期港股资产版本，或 `metadata/frozen_markets/hk.json` 明确记录冷存储位置。
- [ ] 如本次涉及 A 股数据，`metadata/current_assets/a_share_current.json` 存在并指向预期 A 股资产版本。
- [ ] 未把历史兼容 `metadata/current_assets/cn_current.json` 当作新的 A 股权威入口。
- [ ] `metadata/dataset_registry.csv` 已更新或确认无需更新。
- [ ] `marketdata migration status --json` 可运行，并且过渡期中国香港市场后端状态符合预期。

## 数据迁移优先级

- [ ] 已按 [data-transition-playbook.md](data-transition-playbook.md) 完成数据根目录审计。
- [ ] 如活跃根目录仍保留港股资产，`marketdata rqdata inspect-hk-current --artifacts-root "$DATA_PLATFORM_ROOT"` 已运行，或缺口已记录。
- [ ] 如港股已冻结，`marketdata migration freeze-hk ... --json` 清单、freeze marker 和冷存储 manifest 已保留。
- [ ] 如推进 A 股 baseline，`marketdata tushare validate-a-share-daily-clean ...` 已通过，或质量缺口已记录。
- [ ] 如推进 A 股 baseline，`baseline_reproducible` 已通过，或缺失 evidence 已逐项记录。
- [ ] 如推进 A 股研究，`cstree run --config default_next` 已产出 `summary.json`、`config.used.yml` 和持仓文件。
- [ ] 切换 `default` 前，`research_default_promotable` 已通过。
- [ ] 在 PIT fundamentals 和行业历史未补齐前，没有把 A 股 baseline 描述成完整 PIT 研究能力。

## 研究交接

- [ ] `cross-sectional-trees` 已在子项目内完成相关研究、测试或人工验证。
- [ ] `positions_current*.csv` / 已保存持仓的来源明确。
- [ ] `cstree export-targets` 已生成标准格式的 `targets.json`。
- [ ] `targets.json.lineage.json` 已保留，并包含运行编号、输入、配置和数据资产来源信息。
- [ ] 导出的目标只做多，且权重、敞口、日期口径符合执行侧要求。

## 执行交接

- [ ] `quant-execution-engine` 已验证能解析本次 `targets.json`。
- [ ] 如涉及港股，HKD 到 USD 汇率配置已显式提供，或确认执行侧会阻断。
- [ ] 如涉及 A 股，CNY 到 USD 汇率配置已显式提供，或确认执行侧会阻断。
- [ ] 只做预演或解析验证时，没有使用 `--execute`。
- [ ] 模拟盘验证如已执行，证据文件和操作记录已归档。
- [ ] 实盘券商路径未被顶层脚本自动触发。
- [ ] 任何实盘操作都由执行系统自己的执行前检查、`QEXEC_ENABLE_LIVE=1` 和人工监督流程控制。
- [ ] CN 文件契约 dry-run 没有被描述成 `broker_trading_enabled`。

## 文档

- [ ] [contracts.md](contracts.md) 仍准确描述跨模块边界。
- [ ] [platform-workflow.md](platform-workflow.md) 的执行验证状态没有夸大模拟盘 / 实盘成熟度。
- [ ] [bootstrap.md](bootstrap.md) 中的初始化命令仍符合子项目当前依赖定义。
- [ ] 本次版本组合和验证结论已写入 [version-matrix.md](version-matrix.md)。
