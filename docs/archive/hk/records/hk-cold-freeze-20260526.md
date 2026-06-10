# 港股冷存储快照 - 2026-05-26

> status: archived
> owner: market-data-platform
> last_verified: 2026-06-10
> source_of_truth: no
> superseded_by: ../README.md

## 状态

这是中国香港市场历史生成物的私有冷存储快照。Release 创建时暂不上传附件；待本地归档复核完成后，再手工上传下列文件。

冻结快照以 `20260526` 为目标日期，于 `2026-06-01` 完成迁移：

```text
paths: 330
files: 85889
symlinks: 19
unpacked bytes: 6922830594
```

## 待上传附件

```text
hk-freeze-20260526.tar.zst
SHA256SUMS
freeze-manifest.json
hk-frozen-marker.json
a_share_current_health_20260529_after_hk_freeze_20260601.json
hk-cold-storage-20260601.md
```

主归档使用 `tar | zstd -12 -T0 --long=27` 生成：

```text
archive bytes: 1939478781
archive sha256: cbbe642736c2d0f51c52cf8f0ee6113d5d85f77a1ce2c422e4fba5b82edd0184
```

主归档小于 GitHub Release 单附件 `2 GiB` 限制，不需要分片。

## 内容

归档包含港股数据平台冻结快照中的资产、港股 universe、style 产物、intraday cache、报告、current contract 和 registry 切片。`freeze-manifest.json` 保留逐路径 SHA-256 清单，`hk-frozen-marker.json` 保留活跃数据根目录切换到冷存储后的定位信息。

## Tick-Depth 限制

本快照不包含 manifest 中记录的约 `41.1GB` 原始盘口缓存。该来源路径冻结前已经不在本机。归档中仍保留港股 tick-depth 的索引、manifest 和派生产物，因此不要把本 Release 描述为完整原始盘口归档。

## 下载后验证

```bash
sha256sum -c SHA256SUMS
zstd -t hk-freeze-20260526.tar.zst
tar -I unzstd -xf hk-freeze-20260526.tar.zst
```

恢复到活跃共享数据根目录前，先阅读 [`hk-cold-storage-20260601.md`](hk-cold-storage-20260601.md)，并执行 `marketdata migration hydrate-hk` 的 dry-run。
