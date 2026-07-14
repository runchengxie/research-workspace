# AGENTS.md

本文件说明顶层工作区的协作规则。子仓库内部改动仍以各自的 `AGENTS.md` 为准。

## 工作区职责

顶层仓库负责以下内容：

- 锁定五个子模块的提交版本
- 维护跨仓库文件约定和 `src/research_contracts`
- 维护工作区 doctor、质量检查和子仓库委托脚本
- 记录版本组合、发布检查和归档入口
- 说明数据、研究、回测、编排和执行之间的交接方式

子仓库内部实现、依赖、业务参数和完整测试配置留在对应仓库。

## 仓库边界

| 仓库 | 主要职责 |
| --- | --- |
| `market-data-platform` | 数据资产生产、检查、发布和读取 |
| `alpha-research` | 特征、模型、研究评估和信号产物 |
| `portfolio-backtester` | 组合构造、回测、成本、容量、暴露和报告 |
| `strategy-pipeline` | 研究编排、CLI、运行目录和 `targets.json` 导出 |
| `quant-execution-engine` | 预演、风控、券商执行、对账和审计 |

顶层不保存大型数据、研究运行产物、provider 缓存、券商凭证或交易审计日志。

## 常用检查

```bash
python scripts/workspace_doctor.py
python src/research_contracts/smoke_contracts.py
uv run --project strategy-pipeline --extra dev \
  --with 'matplotlib>=3.8' --with 'tabulate>=0.9' \
  python -m pytest tests -q
python scripts/run_quality_checks.py --profile hard
python scripts/run_quality_checks.py --profile basedpyright
python scripts/run_submodule_checks.py --profile smoke
python scripts/run_submodule_checks.py --profile full --dry-run
python scripts/run_submodule_checks.py --profile release_typecheck --dry-run
```

`run_submodule_checks.py` 只执行 `scripts/submodule_checks.json` 中登记的命令。不要在顶层复制子仓库内部检查逻辑。

当前没有启用顶层 GitHub Actions workflow。文档中不得把 `.github/workflows/superproject.yml.disabled` 描述为正在运行的 CI。

## 文件约定

A 股权威 current contract：

```text
metadata/current_assets/a_share_current.json
```

研究到执行的权威交接文件：

```text
targets.json
```

修改跨仓库产物格式时，应同步更新生产方、消费方、顶层契约文档和对应测试。

## 文档规则

- 根目录 `README.md` 只保留定位、快速开始、核心边界和文档入口
- `docs/README.md` 只做导航
- 顶层 `docs/` 只记录跨仓库协作、契约、版本和发布治理
- 子仓库实现细节放在子仓库文档
- 阶段记录和历史证据放入 `docs/archive/` 或 `docs/evidence/`
- 中文正文使用中文标点
- 保留必要的命令、路径、配置键和 API 名称
- 避免中英混杂的长句、翻译腔和先否定再转折的表达
- 尽量不用双引号、加粗、分号和破折号
- 文档中的命令、文件名和默认值必须能从代码或测试中核对

文档润色不得顺手修改公开接口、路径、资产键或历史产物名称。

## 测试与验证

- 文档改动至少运行链接检查、入口文档风格检查和相关事实测试
- 修改 `scripts/submodule_checks.json` 时同步更新 `tests/test_run_submodule_checks.py`
- 修改子模块列表时同步更新 `.gitmodules`、doctor、版本矩阵和测试
- 修改 Python 命名空间边界时运行 `tests/test_namespace_contracts.py` 和 `tests/test_workspace_import_boundaries.py`
- 修改 `targets.json` 或 current contract 时运行对应契约测试

## Git 工作流

跨多个仓库的文档和测试调整使用短期分支与 PR。子仓库改动合并后，再更新顶层 gitlink 和版本矩阵。

提交前检查暂存区，避免加入以下内容：

- `.env`、`.env.*`、`.envrc`
- API 密钥、访问令牌和券商凭证
- `artifacts/`、`outputs/`、缓存和大型数据文件
- 本地绝对路径、内部主机名和私有账户信息

## 汇报顺序

跨仓库工作按数据平台、alpha 研究、组合回测、策略编排、交易执行、顶层工作区的顺序汇报。完成状态应附真实命令结果或明确说明尚未运行的检查。
