# 港股业务隔离方案

> status: draft decision memo
> owner: workspace
> last_reviewed: 2026-06-13
> scope: research-workspace, market-data-platform, cross-sectional-trees, quant-execution-engine

## 结论

这个想法可行，但推荐拆的是“工作区和生命周期”，不是第一步就按文件把每个仓库里的
`hk_*` 代码硬拆出去。

当前更成熟的路线是：

1. 保留 `research-workspace` 作为活跃 A 股主工作区。
2. 为港股建立独立、私有、paused-maintenance、restore-only 的归档工作区或归档仓库。
3. 当前 A 股工作区只保留恢复证据、删除门禁、必要的共享执行契约和明确的兼容入口。
4. 等 private archive、public demo、consumer audit 和 focused tests 都补齐后，再逐步移除活跃工作区里的港股业务入口。

不建议现在直接把 `market-data-platform`、`cross-sectional-trees`、`quant-execution-engine`
分别拆出一套活跃港股 repo。港股业务已经暂停，继续维护一组活跃平行仓库会增加 CI、依赖、安全更新和文档同步成本；而且当前港股实现依赖大量共享管线、路径契约和执行 contract，直接拆文件容易得到一个表面独立、实际不可恢复的代码集合。

## 推荐目标形态

```text
research-workspace
  status: active
  focus: A 股
  submodules:
    market-data-platform
    cross-sectional-trees
    quant-execution-engine
  keeps:
    docs/archive/hk/**
    docs/hk-public-split-manifest.yml
    docs/hk-private-archive-manifest.yml
    docs/evidence/hk-*.json

hk-research-workspace-archive
  status: private, paused-maintenance, restore-only
  focus: 港股历史复现
  submodules:
    market-data-platform @ hk freeze tag or commit
    cross-sectional-trees @ hk freeze tag or commit
    quant-execution-engine @ hk freeze tag or commit
  keeps:
    README restore guide
    version matrix
    archive evidence
    no market data, no provider cache, no credentials

hk-cross-sectional-strategy-demo
  status: public, paused-maintenance
  focus: synthetic demo only
  source:
    demo/hk-public-demo-template-v1/**
    demo/hk-research-lane-template-v1/**
  excludes:
    real provider code
    broker runtime
    real market data
    historical run output
```

如果维护者只需要“未来能恢复”，`hk-quant-legacy-archive` 这类 private archive 就足够；
如果维护者希望保留完整子模块组合和恢复顺序，再新增 `hk-research-workspace-archive`
作为港股 superproject 更清晰。

## 当前证据

顶层已经有港股隔离的主要控制面：

- `docs/archive/hk/README.md` 是中国香港市场归档入口。
- `docs/hk-public-split-manifest.yml` 记录公开 demo、保留、删除、禁止公开的 surface。
- `docs/hk-private-archive-manifest.yml` 记录真实业务代码的 private archive gate。
- `docs/deprecations.md` 记录 `hkdata`、`rqdata-hk-*`、`cstree alloc-hk` 等兼容入口。
- `demo/hk-public-demo-template-v1/` 和 `demo/hk-research-lane-template-v1/` 已经是 synthetic-only staging。

当前仓库扫描也显示港股 surface 分布在三个子模块：

- `market-data-platform`: `hk_assets`、`hk_depth`、`hk_data_platform`、`configs/presets/release/hk_*.yml`、`configs/presets/universe/hk_*.yml`。
- `cross-sectional-trees`: `configs/**/hk*.yml`、`configs/field_profiles/hk_*`、`src/cstree/research/hk_*.py`、`docs/archive/research/hk/**`。
- `quant-execution-engine`: `broker/longport*.py`、LongPort 文档和测试。

这些 surface 目前不是同一种生命周期：

| surface | 生命周期 | 推荐动作 |
| --- | --- | --- |
| 港股真实数据生产和恢复能力 | restore-sensitive | private archive + 活跃恢复门禁 |
| 港股历史研究配置和笔记 | archived provenance | 归档保留，公开只放审查后的 excerpt |
| `hkdata`、`rqdata-hk-*`、`alloc-hk` | deprecated compatibility | consumer audit 后删除 |
| LongPort broker runtime | private runtime / shared execution concern | 不进 public demo；是否从活跃 qexec 移除单独评审 |
| `targets.json`、FX、risk、dry-run | shared active | 保留在执行引擎 |

## 分阶段操作

### 阶段 0：停止继续扩展港股主线

目标是先冻结新增入口：

- 不新增港股默认配置。
- 不把港股放入 A 股主线 CI 必跑路径。
- 不继续扩大 `hk_*` research surface。
- 不把真实港股 provider / broker 代码复制到 public demo。

阶段 0 不删除代码，只明确生命周期。

### 阶段 1：给当前组合打 freeze tag

在真实 Git 仓库中操作，不能用 zip 快照替代。每个 repo 先确认工作树干净，再打 tag：

```bash
git status --short
git tag -a hk-freeze-20260613 -m "Freeze HK restore state before A-share workspace cleanup"
git push origin hk-freeze-20260613
```

需要覆盖：

- `research-workspace`
- `market-data-platform`
- `cross-sectional-trees`
- `quant-execution-engine`

同时更新或生成 version matrix，记录 tag、commit、验证命令和限制。

### 阶段 2：建立港股 restore-only workspace

如果决定保留完整子模块组合，创建新的 private repo，例如：

```text
hk-research-workspace-archive
```

初始化方式：

```bash
git init hk-research-workspace-archive
cd hk-research-workspace-archive

git submodule add git@github.com:runchengxie/market-data-platform.git market-data-platform
git submodule add git@github.com:runchengxie/cross-sectional-trees.git cross-sectional-trees
git submodule add git@github.com:runchengxie/quant-execution-engine.git quant-execution-engine

git -C market-data-platform checkout hk-freeze-20260613
git -C cross-sectional-trees checkout hk-freeze-20260613
git -C quant-execution-engine checkout hk-freeze-20260613

git add .gitmodules market-data-platform cross-sectional-trees quant-execution-engine
git commit -m "Create frozen HK research workspace"
```

新 workspace 的 README 必须写清：

- `status: private, paused-maintenance, restore-only`
- 不纳入当前 A 股 workspace 的 submodule、CI、release matrix。
- 不提交行情数据、provider cache、研究 run、交易审计日志、`.env*` 或券商凭证。
- 恢复前先读 `docs/archive/hk/README.md` 和 archive evidence。

### 阶段 3：保留 public demo clean-room 路线

公开展示继续走 synthetic demo，而不是从真实港股业务代码直接拆出 public repo：

```bash
python scripts/export_hk_public_demo.py --out /tmp/hk-cross-sectional-strategy-demo
python scripts/export_hk_public_demo.py --scan-only /tmp/hk-cross-sectional-strategy-demo
python scripts/run_quality_checks.py --profile secrets --demo-stage /tmp/hk-cross-sectional-strategy-demo
```

发布前要求：

- `export-manifest.json` 存在。
- scan、offline smoke、quality checks 均通过。
- staged tree 不包含真实行情、provider cache、Parquet、pickle、压缩包、本地绝对路径、broker/provider runtime import、workspace import。

### 阶段 4：清理当前 A 股 workspace 的入口

清理顺序应从低风险入口开始：

1. 文档默认路径改成 A 股主线，港股只指向归档入口。
2. CI / release checklist 不再把港股业务测试作为 A 股主线必跑项。
3. 标记或隐藏废弃 CLI：`hkdata`、`rqdata-hk-*`、`cstree alloc-hk`。
4. 运行 consumer audit，确认没有 repo-local 或下游调用。
5. 满足 deletion gate 后删除兼容入口和业务代码。

删除前必须由对应 manifest 证明 gate ready。private staging 或 public demo 成功都不是删除充分条件。

### 阶段 5：分仓库删除或保留策略

#### market-data-platform

短期保留：

- `metadata/frozen_markets/hk.json` 相关恢复控制面。
- `marketdata migration freeze-hk` / `hydrate-hk`。
- `docs/archive/hk/**` 指向的 restore evidence。

候选删除必须等 gate ready：

- `src/hk_data_platform/**`
- `src/market_data_platform/hk_assets/**`
- `src/market_data_platform/hk_depth/**`
- `configs/presets/release/hk_*.yml`
- `configs/presets/universe/hk_*.yml`
- `rqdata-hk-*` 兼容命令

#### cross-sectional-trees

短期保留：

- 明确 restore 用的港股 preset。
- 历史研究归档索引。
- `docs/evidence/hk-research-archive-manifest-20260601.json`。

候选删除必须等 gate ready：

- `configs/experiments/**/*hk*.yml`
- `configs/field_profiles/hk_*`
- `src/cstree/research/hk_*.py`
- `src/cstree/liveops/alloc_hk*.py`
- `cstree alloc-hk`

#### quant-execution-engine

不建议用“港股暂停”作为理由直接拆执行引擎。

保留：

- 标准 `targets.json` 解析。
- FX、risk、rebalance、dry-run、audit contract。

LongPort 可选两种路径：

- 保留为 optional broker，但从 A 股主线文档入口降级。
- 在确认没有活跃执行需求后，按 qexec 自己的 broker deprecation 流程移除。

LongPort 不进入 public demo，也不应被当作港股研究代码公开迁出。

## 删除门禁

任何 restore-sensitive 或 compatibility surface 删除前，必须同时具备：

- restore evidence；
- consumer audit；
- replacement docs；
- rollback notes；
- owning repo focused tests；
- private archive staging evidence；
- 需要公开承接时的 public split evidence；
- 至少一个约定的 zero-usage release window。

当前 manifest 中多个记录仍是 `blocked_pending_audit` 或 `follow_up_required`，所以现在不应直接删除港股业务代码。

## 建议验证命令

顶层：

```bash
uv run --with pytest python -m pytest tests/test_workspace_doctor.py -q
uv run --with pytest python -m pytest tests -q
python scripts/hk_archive_gate.py --check --format json
python scripts/hk_research_lane_inventory.py --check --format json
```

数据平台：

```bash
cd market-data-platform
uv run python -m pytest tests/test_cold_storage.py tests/test_hk_asset_workflow.py tests/test_hk_depth.py -q
```

策略研究：

```bash
cd cross-sectional-trees
uv run python -m pytest tests/test_alloc_hk.py tests/test_docs_contracts.py tests/test_repo_path_references.py -q
```

交易执行：

```bash
cd quant-execution-engine
uv run pytest tests/unit/test_targets_contract.py tests/unit/test_longport_adapter.py tests/unit/test_longport_symbols.py -q
```

A 股主线清理后再做全局扫描：

```bash
rg -n "hk|HK|Hong Kong|港股|中国香港|longport|rqdata-hk|hkdata|alloc-hk|alloc_hk" .
```

允许保留的命中应集中在：

- `docs/archive/hk/**`
- `docs/evidence/hk-*.json`
- `docs/hk-*-manifest.yml`
- 明确的 deprecation / restore 说明
- qexec 中仍被正式保留的 broker 或 shared execution contract

## 操作判断

当前最佳动作不是立刻拆代码，而是：

1. 补齐 freeze tag 和 version matrix。
2. 决定是否需要 `hk-research-workspace-archive` 这个 superproject；如果只是恢复证据，现有 private archive 清单已经覆盖大部分需求。
3. 把 active A 股 workspace 的默认文档、CI、release checklist 收敛到 A 股。
4. 逐个推进 manifest gate，把 `blocked_pending_audit` 变成 `ready` 后再删除。

这样能让 A 股工作区变干净，同时保留港股历史复现能力，并避免把共享数据平台和执行引擎拆成难维护的平行体系。
