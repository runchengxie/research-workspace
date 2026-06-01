# 港股研究产物冷存储快照 - 2026-06-01

## 状态

这是 `cross-sectional-trees` 中国香港市场历史研究产物的私有冷存储快照。Release 创建时暂不上传附件；待手工复核后，再上传下列文件。

本快照与港股数据平台 release `hk_cold_freeze_20260526_full` 配套使用。数据平台 release 保存输入数据资产，本 release 保存研究侧生成物。

```text
paths: 879
files: 28695
directories: 554
symlinks: 0
unpacked bytes: 1997093905
```

## 待上传附件

```text
hk-research-freeze-20260601.tar.zst
SHA256SUMS
research-freeze-manifest.json
hk-research-frozen-marker.json
../session-handoffs/hk-research-cold-storage-20260601.md
```

主归档使用 `tar | zstd -12 -T0 --long=27` 生成：

```text
archive bytes: 205106541
archive sha256: 32ff3cd048eb33d5aaa067449932e4528b91700ee07995de46289565f271c6f4
```

主归档小于 GitHub Release 单附件 `2 GiB` 限制，不需要分片。

## 内容

归档包含历史港股 runs、sweeps、reports、live runs、benchmarks、exports、残留 intraday cache 和港股 universe metadata。`research-freeze-manifest.json` 保留逐路径 SHA-256 树摘要，`hk-research-frozen-marker.json` 保留活跃研究仓库切换到冷存储后的定位信息。

## 排除项

本快照不包含 A 股 cache、数据平台 asset symlink、共享 catalog 或 `artifacts/migration_backups/20260525_hk_data_platform_pre_switch`。最后一项是迁移时代的平台审计备份，保留旧 symlink 拓扑价值，但不应重复装入研究包。

## 下载后验证

```bash
sha256sum -c SHA256SUMS
zstd -t hk-research-freeze-20260601.tar.zst
tar -I unzstd -xf hk-research-freeze-20260601.tar.zst
```

恢复研究产物前，先阅读 [`hk-research-cold-storage-20260601.md`](../session-handoffs/hk-research-cold-storage-20260601.md)，再运行：

```bash
python scripts/internal/freeze_hk_research_outputs.py hydrate
```

确认活跃目录没有冲突后，再显式加入 `--apply`。数据平台资产需要单独运行 `marketdata migration hydrate-hk --apply` 恢复。
