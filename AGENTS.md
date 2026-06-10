# AGENTS.md

本文件给维护者、外部贡献者和代码代理使用。它描述顶层工作区的协作规则；各子仓库仍以自己的 `AGENTS.md` 为准。

## 工作区范围

本工作区是多仓库集成层，主要负责：

- 维护 `market-data-platform`、`cross-sectional-trees`、`quant-execution-engine` 的子模块边界。
- 记录跨仓库数据文件约定、运行路径、发布检查清单和工作区健康检查。
- 协调数据平台、策略研究和交易执行之间的文件交接。

不要在顶层仓库放置大体积市场数据、研究 run、交易审计日志或 provider 缓存。这些内容应留在各子仓库约定的产物目录或共享数据根目录。

## 市场称谓

文档、注释、报错信息和面向用户的说明文字应使用清晰、稳妥的市场称谓：

- 优先写中国香港市场、港股、港股通、中国大陆市场、A 股等表述。
- 避免把中国大陆市场与中国香港市场写成政治或地域对立关系。
- 面向用户的正文先写业务含义；命令、路径、配置键、资产键、provider API 和历史文件名只用于说明现有接口。
- 不要为了润色而顺手重命名公开接口、路径、asset key 或历史产物；命名变更应单独评估兼容影响。

## 跨仓库文件约定

跨仓库改动应优先按边界验证：

1. 顶层文档、doctor 或检查清单明确权威文件约定名称。
2. `market-data-platform` 负责生产、检查和发布数据资产文件约定。
3. `cross-sectional-trees` 只读消费平台资产，并负责研究输出与执行目标导出。
4. `quant-execution-engine` 读取标准 `targets.json`，负责解析、dry-run、风控、执行与审计。

当前 A 股权威 current contract 文件名是：

```text
metadata/current_assets/a_share_current.json
```

旧称 `cn_current.json` 只作为 alias 或历史兼容说明，不作为新文档里的权威入口。

## 常用命令

顶层工作区常用检查：

```bash
uv run --with pytest python -m pytest tests/test_workspace_doctor.py -q
uv run --with pytest python -m pytest tests -q
```

子仓库检查应进入对应目录后执行该仓库自己的命令，例如：

```bash
cd market-data-platform && uv run python -m pytest
cd cross-sectional-trees && uv run python -m pytest
cd quant-execution-engine && uv run pytest
```

如果只改跨仓库文件约定，优先运行每个边界的 focused tests，再按需要扩大到完整 pytest、Ruff、Pyright 或治理脚本。

## 编辑规则

- 先确认改动属于顶层工作区还是某个子仓库；不要把子仓库内部规则复制到顶层文档。
- 顶层 `docs/` 只写跨仓库协作、文件约定和发布检查事项。
- 临时交接、冻结记录、发布说明和历史复查材料应放入 `docs/archive/`，活跃文档只链接归档入口。
- 修改 submodule 内容后，要同时注意 superproject 的 submodule gitlink 状态。
- 不要提交 `.pytest_cache/`、`__pycache__/`、`artifacts/`、`outputs/`、provider 凭证或本地 `.env*`。
- 文档改动至少检查路径、文件约定名称和市场称谓是否一致。

## 对用户汇报

汇报跨仓库工作时，按 数据平台 -> 策略研究 -> 交易执行 -> 顶层文档/doctor -> 剩余限制 的顺序说明，并用真实命令输出支撑完成状态。
