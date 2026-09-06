# Task 7 实施报告：quant-platform 公共迁移本地试点

## 状态与裁定

Task 7 已按本地 migration prototype 范围实施。`quant-platform/` 是当前 superproject 中的普通
staging tree，不是独立仓库，没有 remote、push、发布、gitlink 或 workspace 切换。计划中“新仓库”
和真实历史导入被缩减为本地目录与只读历史导出演练；该裁定已同步到权威计划。

只迁移 `portfolio_backtester.style_factors_backtest` 纵切面：量化分组组合回测内核、原 upstream
测试、合成 CSV、一个 v1 JSON artifact contract 和一个确定性 CLI。没有迁移 data provider、alpha、
真实策略/参数、orchestration 或 execution runtime。Python namespace 保持 `portfolio_backtester`。

## 历史、回滚和发布边界

回滚源保持为未修改的 `portfolio-backtester` commit
`91a4fa4f1d57c074c991546c381a3d90a3b6adfb`。通过 `git fast-export` 对所选源码和测试进行了
只读历史导出演练：8 个 commit records、9 个 blob records，导出 SHA-256 为
`9a3545ca2553ad876f02dc7fec1c42660e8c04c7052afe1647704d4bfc29b786`。导出文件只存在 `/tmp`，
未导入或创建仓库；未来获准建仓时可用 fast-import 保留提交元数据。

迁移源码和 upstream 测试与源文件逐字节一致，SHA-256 分别为
`1282301429a9f0ace377e18c2a72407446a212fee4204423b1abd06121e21d04` 和
`a2ab0a7d893c62ad0fa1faf814d624e997101ca8e5689b93ddbc7110d55252ac`。
详细 provenance 位于 `quant-platform/migration/provenance.json`。

源 commit 没有 exact tag，源仓也没有 `LICENSE` 或 `LICENSE.md`。因此本试点不能声明公开发布
就绪，也没有虚构 tag 或许可证。CLI 和 artifact schema 是 staging slice 的新增兼容面；源 slice
此前没有对应 CLI/schema，比较结果为“无旧接口可破坏”，而非声称既有 CLI/schema 完全相同。

## Public CI 与依赖

`.github/workflows/ci.yml` 使用 `uv sync --locked --all-groups`、Ruff 和 pytest。锁文件只解析
PyPI/本地 staging package；运行时依赖仅 NumPy/Pandas，dev 依赖为 jsonschema/pytest/Ruff，
不包含 Git URL、workspace path source、私有 index、私有包、provider、凭证或私有服务。
Fix round 1 逐个解析 `uv.lock` 的 package source：除本包只允许 `editable = "."` 外，其余只允许
`registry = "https://pypi.org/simple"`，并用负例证明 git、workspace/directory、私有 index 和
unexpected editable source 会失败。

## 验证

本报告的正确路径为
`/home/richard/code/.worktrees/architecture-consolidation/.superpowers/sdd/2026-09-06-architecture-consolidation/task-7-report.md`。

Fix round 1 TDD red（新增 validator 依赖前）：

```text
$ uv run pytest tests/test_public_distribution.py -q
E   ModuleNotFoundError: No module named 'jsonschema'
1 error in 0.08s
exit 2
```

源轨 focused tests：

```text
$ .venv/bin/pytest tests/test_style_factors_backtest.py -q
...............                                                          [100%]
15 passed in 1.61s
exit 0
```

新轨 focused tests：

```text
$ uv run pytest tests/test_style_factors_backtest.py tests/test_style_factor_slice.py tests/test_public_distribution.py -q
............................                                             [100%]
28 passed in 2.69s
exit 0
```

依赖与 schema focused tests：

```text
$ uv run pytest tests/test_public_distribution.py -q
..........                                                               [100%]
10 passed in 1.35s
exit 0
```

Ruff：

```text
$ uv run ruff check .
All checks passed!
exit 0
```

CLI 与真实 artifact Draft 2020-12 校验：

```text
$ uv run portfolio-style-factor --input examples/synthetic-style-factor.csv --output "$artifact_file" --signal size --quantiles 2
[backtest] size ...
$ uv run python - "$artifact_file"  # Draft202012Validator(schema).validate(artifact)
Draft 2020-12 validation passed; observations=1; cumulative_return=0.02
exit 0
```

`test_schema_rejects_additional_properties_and_type_drift` 对顶层额外字段、顶层错误类型和嵌套收益
错误类型分别断言 `ValidationError`。`test_lock_source_policy_rejects_nonpublic_or_unexpected_sources`
覆盖 git、workspace/directory、private index 和 unexpected editable source。provenance 仍通过源/目标
SHA-256 对比；源 submodule 最终保持 clean。

diff checks：

```text
$ git diff --check
exit 0 (no output)
$ git diff --cached --check
exit 0 (no output)
```

按用户要求没有运行 workspace doctor、contract smoke、workspace tests 或其他 broad checks，且没有
触碰任何 remote。

## Concerns

- 缺少 LICENSE 和稳定 source tag，禁止把 staging tree 当作可公开发布仓库。
- 独立提交图尚未 fast-import；当前只保留可复核的 history export 证据和源 commit 回滚点。
- 新 CLI/schema 没有旧版对应物，只验证其自身契约和底层 upstream 行为一致性。
