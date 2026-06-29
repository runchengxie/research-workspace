# AGENTS.md

本文件给维护者、外部贡献者和代码代理使用。它描述顶层工作区的协作规则；各子仓库仍以自己的 `AGENTS.md` 为准。

## 工作区范围

本工作区是多仓库集成层，主要负责：

- 维护 `market-data-platform`、`alpha-research`、`portfolio-backtester`、`strategy-pipeline`、`quant-execution-engine` 的子模块边界。
- 维护顶层 `src/research_contracts` 薄包，用于校验跨仓库产物契约清单。
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
3. `alpha-research` 负责特征、模型、研究评估、稳健性诊断和信号产物。
4. `portfolio-backtester` 负责组合构造、回测、容量、暴露、换手和报告。
5. `strategy-pipeline` 只读消费平台资产，编排研究流程，并导出执行目标文件。
6. `quant-execution-engine` 读取标准 `targets.json`，负责解析、dry-run、风控、执行与审计。

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
cd market-data-platform && uv run --extra dev python -m pytest
cd alpha-research && uv run --extra dev python -m pytest
cd portfolio-backtester && uv run --extra dev python -m pytest
cd strategy-pipeline && scripts/dev/run_tests.sh all
cd quant-execution-engine && uv run --group dev python -m pytest
```

如果只改跨仓库文件约定，优先运行对应边界的定点测试，再按需要扩大到完整 pytest、Ruff、ty、BasedPyright advisory 或治理脚本。顶层统一委托入口是：

```bash
python scripts/run_submodule_checks.py --profile smoke
python scripts/run_submodule_checks.py --profile full --dry-run
python scripts/run_submodule_checks.py --profile release_typecheck --dry-run
```

## TuShare 凭证约定

- TuShare 本地凭证由 `market-data-platform` 负责管理；不要在顶层仓库新增或提交 `.env*`。
- 需要真实 TuShare 请求时，优先进入 `market-data-platform` 使用该仓库 CLI。CLI 会读取当前工作目录和
  `market-data-platform` 根目录下未跟踪的 `.env.local` / `.env`。
- 15000 分账户使用 `TUSHARE_TOKEN_2`，并依赖匹配的 `TUSHARE_API_URL_2` 中转地址；命令应显式传
  `--token-env TUSHARE_TOKEN_2`，或在验证命令中传 `--env TUSHARE_TOKEN_2`。不要因为默认官方 API
  域名返回 token 错误就判断 token 失效。
- Codex / MCP connector 的 TuShare token 配置和本地 `.env` 分属两套环境；如果 connector 报缺少 token，应改用 `market-data-platform` CLI，或先确认 connector 侧配置。不要读取或打印本地 token。

## 编辑规则

- 先确认改动属于顶层工作区还是某个子仓库；不要把子仓库内部规则复制到顶层文档。
- 顶层 `docs/` 只写跨仓库协作、文件约定和发布检查事项。
- `strategy-pipeline/docs/` 当前仍保留部分历史研究、alpha 和回测说明；新增或大改这类说明时，优先放到 `alpha-research` 或 `portfolio-backtester`。留在 `strategy-pipeline` 的内容应聚焦编排、CLI、配置、产物和执行目标导出。
- 临时交接、冻结记录、发布说明和历史复查材料应放入 `docs/archive/`，活跃文档只链接归档入口。
- 修改 submodule 内容后，要同时注意 superproject 的 submodule gitlink 状态。
- 不要提交 `.pytest_cache/`、`__pycache__/`、`artifacts/`、`outputs/`、provider 凭证或本地 `.env*`。
- 文档改动至少检查路径、文件约定名称和市场称谓是否一致。

## 对用户汇报

汇报跨仓库工作时，按 数据平台 -> 策略研究 -> 交易执行 -> 顶层文档/doctor -> 剩余限制 的顺序说明，并用真实命令输出支撑完成状态。
