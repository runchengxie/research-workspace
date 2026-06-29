# 维护债治理

本页汇总维护债相关的活跃治理入口。各子模块仍分别负责自己的代码、文档、测试和运行行为。

## 登记清单

| 领域 | 权威入口 |
| --- | --- |
| 废弃兼容入口 | [deprecations.md](deprecations.md)、[deprecations.yml](deprecations.yml) |
| 兼容 facade 和 wrapper | [compatibility-facades.yml](compatibility-facades.yml) |
| 脚本生命周期和安全边界 | [script-lifecycle.yml](script-lifecycle.yml) |
| 质量覆盖和排除项 | [quality-coverage-governance.yml](quality-coverage-governance.yml) |
| 大文件和重构路线图 | [maintainability-refactor-roadmap.yml](maintainability-refactor-roadmap.yml) |
| 生成的维护债基线 | [evidence/maintainability/baseline-20260617.json](evidence/maintainability/baseline-20260617.json) |
| 中国香港市场归档路由 | [archive/hk/README.md](archive/hk/README.md) |
| 港股公开拆分边界 | [hk-public-split-manifest.yml](hk-public-split-manifest.yml) |
| 港股私有 legacy archive 门禁 | [hk-private-archive-manifest.yml](hk-private-archive-manifest.yml) |

## 基线命令

```bash
python scripts/maintainability_baseline.py --out docs/evidence/maintainability/baseline-20260617.json
```

报告使用标准库 AST 解析，记录 Python LOC、港股相关文件数量、大文件、长函数、近似复杂度热点、大类热点、热点计数预算输入、质量配置和脚本清单。

## 规则

- 新增 deprecated surface 需要 owner、replacement、removal condition、rollback path 和 focused tests。
- 新增或保留兼容 facade、wrapper、星号重导出时，需要登记 replacement、consumer audit、removal condition、rollback path 和 focused tests。
- 新增非平凡脚本并用于发布或迁移流程前，需要补齐 lifecycle 元数据。
- 新增大范围 Ruff、BasedPyright 或 mypy 排除项，需要 owner、reason、review milestone 和 next include target。
- 大文件、大类、长函数和复杂度热点由路线图预算 ratchet 约束；计数下降时同步下调预算，不保留松动空间。
- 删除 restore-sensitive 港股兼容代码需要后续变更，并附上负责仓库的证据。
