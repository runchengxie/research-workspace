# AGENTS.md

本文件给维护者、外部贡献者和代码代理使用。它描述 superproject 层级的协作规则；各子仓库仍以自己的 `AGENTS.md` 为准。

## Workspace scope

本工作区是多仓库集成层，主要负责：

- 维护 `market-data-platform`、`cross-sectional-trees`、`quant-execution-engine` 的子模块边界。
- 记录跨仓库数据契约、运行路径、release checklist 和工作区健康检查。
- 协调从数据平台到策略研究再到交易执行的 contract handoff。

不要在 superproject 层级放置大体积市场数据、研究 run、交易审计日志或 provider cache。这些内容应留在各子仓库约定的产物目录或共享数据根目录。

## Market wording

文档、注释、报错信息和面向用户的说明文字应使用清晰、稳妥的市场称谓：

- 优先写“中国香港市场”“港股”“港股通”“中国大陆市场”“A 股”等表述。
- 避免把中国大陆市场与中国香港市场写成政治或地域对立关系。
- 面向用户的正文先写业务含义；命令、路径、配置键、资产键、provider API 和历史文件名只用于说明现有接口。
- 不要为了润色而顺手重命名公开接口、路径、asset key 或历史产物；命名变更应单独评估兼容影响。

## Cross-repo contracts

跨仓库改动应优先按边界验证：

1. superproject 文档、doctor 或 checklist 明确 canonical contract 名称。
2. `market-data-platform` 负责生产、检查和发布数据资产 contract。
3. `cross-sectional-trees` 只读消费平台资产，并负责研究输出与执行目标导出。
4. `quant-execution-engine` 读取标准 `targets.json`，负责解析、dry-run、风控、执行与审计。

当前 A 股 canonical current contract 名称是：

```text
metadata/current_assets/a_share_current.json
```

旧称 `cn_current.json` 不应再作为权威入口写入新文档；如确需兼容旧产物，必须明确标注为 alias 或历史兼容。

## Commands

superproject 层级常用检查：

```bash
uv run --with pytest python -m pytest tests/test_workspace_doctor.py -q
```

子仓库检查应进入对应目录后执行该仓库自己的命令，例如：

```bash
cd market-data-platform && uv run python -m pytest
cd cross-sectional-trees && uv run python -m pytest
cd quant-execution-engine && uv run pytest
```

如果只改跨仓库 contract，优先运行每个边界的 focused tests，再按需要扩大到完整 pytest、Ruff、Pyright 或治理脚本。

## Editing rules

- 先确认改动属于 superproject 还是某个子仓库；不要把子仓库内部规则复制到顶层文档。
- 顶层 `docs/` 只写跨仓库协作、contract 和 release/checklist 事项。
- 临时交接、冻结记录、release note 和历史复查材料应放入 `docs/archive/`，活跃文档只链接归档入口。
- 修改 submodule 内容后，要同时注意 superproject 的 submodule gitlink 状态。
- 不要提交 `.pytest_cache/`、`__pycache__/`、`artifacts/`、`outputs/`、provider credentials 或本地 `.env*`。
- 文档改动至少检查路径、contract 名称和市场称谓是否一致。

## User-facing summary

汇报跨仓库工作时，按“数据平台 -> 策略研究 -> 交易执行 -> 顶层文档/doctor -> 剩余限制”的顺序说明，且用真实命令输出支撑完成状态。
