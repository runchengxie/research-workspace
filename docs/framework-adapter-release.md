# 外部框架适配器候选发布

> status: reference
> owner: workspace
> last_verified: 2026-07-16
> source_of_truth: `framework-adapter-release.yml`

`framework-adapters-2026-07` 仍处于 `blocked_on_downstream_merge`。清单保存当时的候选提交和 PR 记录，superproject 没有锁定这些提交。当前各远端只保留 `main`，清单中的功能分支名称属于历史候选记录。

## 责任边界

- `market-data-platform` 继续负责数据资产，可通过只读适配器向 Qlib 提供已发布数据。
- `alpha-research` 继续负责 PIT、防泄漏、CPCV、PBO、研究证据和晋级规则。Qlib 只作可选研究后端。
- `portfolio-backtester` 继续负责确定性 A 股回放，并可与 Qlib 或 LEAN 参考场景比较。
- `strategy-pipeline` 继续负责研究编排和确定性目标导出。
- `quant-execution-engine` 继续负责策略规则、审批、幂等、持久日志和对账。vn.py 只作可选传输层。

Qlib、vn.py 和 LEAN 的运行时对象不得进入跨仓库契约。原生路径继续保留，只有通过差分证据后才考虑启用适配器。

## 恢复候选发布的顺序

1. 在各负责仓库重新建立并评审候选改动。
2. 将真实合并提交写入清单的 `merged_commit`，并把 `merge_state` 更新为 `merged`。
3. 所有下游改动合并后，再更新五个子模块 gitlink。
4. 运行严格门禁：

   ```bash
   python scripts/framework_adapter_release_gate.py --strict
   ```

5. 生成各负责仓库的差分证据，再构建集成 envelope：

   ```bash
   python scripts/framework_adapter_evidence.py \
     --release-manifest docs/framework-adapter-release.yml \
     --alpha <backend-comparison-replay-receipt.json> \
     --backtest <backtest-differential.json> \
     --execution <execution-recovery-matrix.json> \
     --output <integration-evidence.json>
   ```

6. 将 envelope 路径和 SHA-256 写回清单，再次运行严格门禁。
7. 原生路径和适配器路径都通过后，将证据状态更新为 `accepted`，发布状态更新为 `verified`。
8. 在 `version-matrix.md` 记录最终合并、锁定和验证的版本组合。

普通门禁在阻塞状态下只报告现状。严格模式会持续失败，直到下游合并、gitlink 和证据全部完成。

## 回退

合并前可以关闭候选 PR，并在新的候选批次中重新登记。合并后若验证失败，应恢复最近一次已验证的子模块组合并保留失败证据。执行日志、幂等键和既有产物 schema 不得静默改写。
