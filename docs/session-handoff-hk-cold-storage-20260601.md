# 港股冷存储冻结记录 - 2026-06-01

## 结果

中国香港市场数据资产已从活跃共享数据根目录移入独立冷存储：

```text
active root: /home/richard/data/market-data-platform
cold snapshot: /home/richard/data/market-data-platform-cold/hk-freeze-20260526
freeze marker: /home/richard/data/market-data-platform/metadata/frozen_markets/hk.json
freeze manifest: /home/richard/data/market-data-platform-cold/hk-freeze-20260526/freeze-manifest.json
```

冻结清单：

```text
paths: 330
files: 85889
symlinks: 19
bytes: 6922830594
checksum: sha256
```

活跃根目录中的 `metadata/dataset_registry.csv` 已重建为 A 股 contract 索引。冷存储保留：

```text
metadata/current_assets/hk_current.json
metadata/dataset_registry.hk.csv
metadata/dataset_registry.pre-freeze.csv
```

## Tick-Depth 限制

港股 tick-depth 平台资产只保留索引、manifest 和派生产物。manifest 中记录的原始盘口缓存路径已经不在本机：

```text
/home/richard/code/research-workspace/rqdata-hk-depth-snapshots/artifacts/cache/rqdata/hk_tick_depth
```

不要把本次冻结描述为已经归档约 41.1GB 的原始盘口缓存。

## 恢复

恢复前先查看计划：

```bash
marketdata migration hydrate-hk \
  --artifacts-root /home/richard/data/market-data-platform \
  --json
```

确认活跃根目录没有港股路径冲突后，显式恢复：

```bash
marketdata migration hydrate-hk \
  --artifacts-root /home/richard/data/market-data-platform \
  --apply
```

恢复命令会重建中国香港市场 / A 股双市场 registry。

## 冻结后验证

```text
active root size: 1.6G
cold snapshot size: 6.7G
A-share contract health: green
A-share assets checked: 10
A-share missing assets: 0
A-share stale assets: 0
workspace smoke contracts: errors=0 warnings=0
```

迁移后的 A 股 health 报告：

```text
/home/richard/data/market-data-platform/reports/a_share_current_health_20260529_after_hk_freeze_20260601.json
```
