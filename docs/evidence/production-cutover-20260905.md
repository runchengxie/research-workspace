# 公共 strategy-pipeline production cutover 记录

## 结论

2026-09-05，`research-workspace` 已将 production 的 `current` 指针切换到
`9b50e2ef9a533faad624b1f7e525ccc174ccbfe7`。这个版本使用公共
`strategy-pipeline`，不需要 `strategy-pipeline-internal` checkout、安装包或私有凭证。

## 发布组合

| 组件 | production 提交 |
| --- | --- |
| `research-workspace` | `9b50e2ef9a533faad624b1f7e525ccc174ccbfe7` |
| `strategy-pipeline` | `1c1da3b243dffd89a496aeda5849e3ec8ca0c3b5` |
| `market-data-platform` | `51e583197986f8b22be1305b6bfd4a093cf4f32d` |
| `portfolio-backtester` | `750b8219c71db875088739d0df46117770a7e278` |
| `quant-execution-engine` | `18db8b9bbc20cf0febc5811c3d1b889aad4a6303` |
| `strategy-app` | `442f38d08881d15aac130b5d1de01dc1d5bac9cd` |
| `alpha-research` | `1a424e513c35cd5c732f1a9f51c67ac2e68e3e2a` |
| `strategy-research` | `75ea3a52561fdc5f7c70160f70fce0c25a57b24b` |

production 共享环境位于 `/home/richard/code/production/shared/venvs/`，由发布脚本按提交指纹管理。运行代码只从
`/home/richard/code/production/research-workspace/current/` 读取。

## 发布验证

- 公共 readiness gate：通过
- 公共历史敏感信息审计：`outcome=direct-public-safe`，`findings=[]`
- 公共控制面测试：21 passed
- production CLI 帮助 smoke：通过
- workspace 完整门禁：根测试 420 passed，研究层 391 passed
- workspace quality、边界、架构、doctor、契约、策略证据和敏感信息检查：通过

当前仍保留 4 个已登记 warning，包括可选 CLI 未安装和质量预算中的文件忽略项。这些 warning 没有阻断本次发布。

## 回滚

上一个已保留的 workspace release 是：
`5e73f98b70ffc6af495016f335b943bcbbc50918`。

回滚时将 `current` 原子切回该 release，并重新确认子模块状态：

```bash
ln -sfn releases/5e73f98b70ffc6af495016f335b943bcbbc50918 \
  /home/richard/code/production/research-workspace/current
git -C /home/richard/code/production/research-workspace/current \
  submodule update --init --recursive
```

回滚后需要重新执行公共 CLI help、控制面测试和对应日报或周报 smoke。production release 目录按保留策略保留，便于恢复。

## 发布限制

- 本次切换只发布公共控制面和 workspace 版本组合，不代表任何策略已经获得实盘资格。
- `strategy-pipeline` 只负责通用运行编排、artifact 发布和下游交接，策略代码、数据 provider 和券商执行仍由对应 owner 维护。
- 真实券商下单仍由 `quant-execution-engine` 的独立门禁、模拟盘流程和人工确认控制。
- `strategy-pipeline-internal` 仍处于迁移退役流程中，本记录不代表它已经完成冻结或删除。
