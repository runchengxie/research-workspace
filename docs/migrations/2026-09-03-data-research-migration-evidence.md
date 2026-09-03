# 数据和研究证据迁移记录

> status: active
> owner: workspace
> last_verified: 2026-09-03

## 本次核对结论

数据生产能力已经由 `market-data-platform` 维护。当前 owner main 为 `dee7c61`，核心实现和测试覆盖 provider、PIT、数据契约、资产注册、资产发布、数据质量和恢复流程。

研究数据集结构已经由 `alpha-research` 维护。当前 owner main 为 `e2b71e6`，`alpha_research.dataset`、`modeling_dataset`、特征数据集和研究指标测试均已存在。

internal 的数据相关代码按职责分成三类：

| internal 路径 | 当前判断 | 新归属或处理 |
| --- | --- | --- |
| `data_interface.py` | 运行侧消费适配器 | 迁移期间保留在编排层，改由 `market_data_platform.data_providers_public_api` 提供数据能力 |
| `dataset.py` | 通用研究数据集兼容层 | 由 `alpha_research.dataset` 作为研究 owner，internal 只保留调用适配 |
| `legacy_rqdata_runtime.py` | 历史 provider 兼容实现 | 归档，不恢复为当前数据平台能力 |
| `pipeline/*` 中的数据加载和字段标准化调用 | 编排层调用 owner API | provider、PIT、symbol 规范化和资产 lineage 由 market-data-platform 提供 |

## 已完成的文档归属

internal 的以下 planned 文档已有对应 owner 页面，workspace 清单已标记为 `complete`：

| 原文档 | owner 页面 | 代码和测试证据 |
| --- | --- | --- |
| `docs/concepts/data-sources.md` | `market-data-platform/docs/contracts.md`、`docs/operations/a-share-tushare.md` | `tests/test_tushare_platform_assets.py`、`tests/test_data_providers_cache.py` |
| `docs/concepts/pit-coverage.md` | `market-data-platform/docs/a-share-fundamentals.md`、`docs/contracts.md` | `tests/test_tushare_a_share_fundamentals.py`、`tests/test_current_path_audit.py` |
| `docs/concepts/shared-hk-data-platform.md` | `market-data-platform/docs/operations/hk-archive-restore.md`、`docs/contracts.md` | `tests/test_quality_governance.py`、`tests/test_dataset_contracts.py` |
| `docs/providers.md` | `market-data-platform/docs/integrations.md`、`docs/operations/credentials.md` | `tests/test_data_providers_cache.py`、`tests/test_cli_dependency_boundaries.py` |
| `docs/reference/outputs/platform-assets.md` | `market-data-platform/docs/contracts.md`、`docs/data-warehouse.md` | `tests/test_paths.py`、`tests/test_data_warehouse.py` |

这些页面采用 owner 原有的文档结构，没有在 workspace 复制 provider 实现或凭证说明。workspace 只保留迁移索引和跨仓契约入口。

## 尚未完成的部分

- internal `data_interface.py` 仍是 active consumer，必须等所有 pipeline 调用切换到 owner-native API 后才能删除。
- `legacy_rqdata_runtime.py` 仍被历史 liveops 测试覆盖，需在执行交接切片中移入归档并移除 active CLI 引用。
- `alpha-research` 的 AFML、研究协议和证据文档仍属于后续研究证据切片，不能因为数据平台迁移完成而提前标记完成。
