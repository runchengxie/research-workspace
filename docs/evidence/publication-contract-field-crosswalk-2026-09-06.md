# 发布契约字段对照表

> status: staging-only
> verified: 2026-09-06

架构有意使用两层相互独立的元数据。通用的 `research.platform-publication.v1` 清单是传输和披露契约，每个投影的语义来源仍保留在对应领域的资产契约或配套凭证中。

| 要求 | 权威位置 | 用途 |
| --- | --- | --- |
| `artifact_type`、`schema_version` | 投影模式和 `PlatformPublicationArtifact.schema_version` | 识别语义文件类型及其版本 |
| `producer_commit` | `PlatformPublicationManifest.producer_commit` | 固定生产仓库版本 |
| `strategy_id` | 策略注册表和配套策略凭证 | 识别策略，同时不暴露实现路径 |
| `as_of` | 领域投影或凭证 | 识别数据或研究时间 |
| `created_at` | 发布清单的 `generated_at` 和领域凭证的 `generated_at` | 识别传输层和领域层的创建时间 |
| `quality_status` | 领域凭证契约 | 在渲染或投递前采用失败即关闭策略 |
| `source_manifest` | 领域凭证的 `inputs`/`artifacts` 血缘 | 描述已批准的源资产，不暴露本地文件系统路径 |
| SHA-256 和 audience | `PlatformPublicationArtifact` | 验证内容身份和披露边界 |

对于 DailyWatch20，`selection_receipt.json` 是 `watchlist_20.csv` 的语义配套文件。其契约要求质量、时点、模型、特征、血缘和来源信息。通用发布清单包装这两个文件，并增加生产者身份、消费者目标、相对路径和内容哈希。这保留了现有规则：公开传输契约不得包含策略逻辑、供应商凭证或本地源路径。

本对照表是本次迁移的兼容规则。未来资产可以使用单个自描述封装，但不能悄悄将语义来源移入通用传输清单，也不能削弱配套凭证门禁。
