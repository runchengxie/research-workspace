# 港股冷存储冻结记录 - 2026-06-01

> status: archived
> owner: market-data-platform
> last_verified: 2026-06-04
> source_of_truth: no
> superseded_by: ../README.md

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

## Release Package

冻结快照已经聚合为单文件归档，并附带便于单独审阅的 sidecar 元数据：

```text
package dir: /home/richard/data/market-data-platform-cold/packages/hk-freeze-20260526
archive: hk-freeze-20260526.tar.zst
archive bytes: 1939478781
archive sha256: cbbe642736c2d0f51c52cf8f0ee6113d5d85f77a1ce2c422e4fba5b82edd0184
tar entries: 86082
compression: tar | zstd -12 -T0 --long=27
```

主归档小于 GitHub Release 单附件 `2 GiB` 限制，不需要分片。上传前和下载后都应验证：

```bash
cd /home/richard/data/market-data-platform-cold/packages/hk-freeze-20260526
sha256sum -c SHA256SUMS
zstd -t hk-freeze-20260526.tar.zst
```

## 本地清理

归档已上传到 private GitHub Release：

```text
https://github.com/runchengxie/cross-sectional-trees/releases/tag/hk_cold_freeze_20260526_full
```

上传复核完成后，本地解包快照和 package 副本已经删除。活跃数据根目录中的 freeze marker 仍保留预期解压路径；恢复前必须先下载 release 附件、校验 SHA-256，并将主归档解压回该路径。

仓库内旧 `market-data-platform/artifacts/` 也已删除，`.env.local` 已切换到 `/home/richard/data/market-data-platform`。删除前，未进入外部迁移记录的 `39` 个文件和旧目录中的 `639` 条 symlink 拓扑已经保存到：

```text
/home/richard/data/market-data-platform/metadata/archive/repo_local_artifacts_pre_cleanup_20260601
```

该目录中的 `cleanup-manifest.json` 记录了保留文件、SHA-256、迁移记录和远端港股 freeze manifest 的关联。

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
