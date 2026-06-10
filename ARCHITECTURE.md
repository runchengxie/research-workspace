# 架构边界

本工作区协调数据平台、策略研究和交易执行之间的文件交接：

```text
market-data-platform
  生产并发布数据资产
        |
        v
cross-sectional-trees
  只读消费数据资产，并导出 targets.json
        |
        v
quant-execution-engine
  解析 targets.json，执行 dry-run、风控门禁和受控券商执行
```

## 代码边界

- 活跃代码：当前 A 股数据、研究、执行流程，以及多市场共享文件约定。
- 兼容代码：保留中的港股 deprecated surface。删除前需要完成 consumer audit、replacement docs、rollback notes、restore evidence 和 focused tests。
- 归档和来源说明：带日期的交接记录、冻结记录、恢复演练证据和历史研究背景。
- 演示仓库 staging：`demo/` 下的 clean-room synthetic public demo 模板，独立于活跃工作区，不作为子模块或发布门禁。
- 私有运行环境：provider adapter、broker adapter、凭证、本地数据根目录和执行审计日志。这些内容不进入公开演示仓库。

## 治理入口

- 废弃入口：[docs/deprecations.md](docs/deprecations.md)
- 港股公开拆分：[docs/hk-public-split-manifest.yml](docs/hk-public-split-manifest.yml)
- 脚本生命周期：[docs/script-lifecycle.yml](docs/script-lifecycle.yml)
- 质量覆盖和排除项：[docs/quality-coverage-governance.yml](docs/quality-coverage-governance.yml)
- 重构路线图：[docs/maintainability-refactor-roadmap.yml](docs/maintainability-refactor-roadmap.yml)
- 当前文件约定：[docs/contracts.md](docs/contracts.md)
