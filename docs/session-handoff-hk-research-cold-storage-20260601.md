# 港股研究产物冷存储冻结记录 - 2026-06-01

## 结果

`cross-sectional-trees` 中的中国香港市场历史研究产物已迁入独立冷存储：

```text
repo root: /home/richard/code/research-workspace/cross-sectional-trees
cold snapshot: /home/richard/data/cross-sectional-trees-cold/hk-research-freeze-20260601
freeze marker: artifacts/metadata/frozen_markets/hk_research.json
freeze manifest: /home/richard/data/cross-sectional-trees-cold/hk-research-freeze-20260601/research-freeze-manifest.json
```

冻结清单：

```text
paths: 879
files: 28695
directories: 554
symlinks: 0
bytes: 1997093905
checksum: sha256
```

迁出范围包括历史港股 runs、sweeps、reports、live runs、benchmarks、exports、残留 intraday cache 和港股 universe metadata。活跃仓库仍保留 A 股 cache、数据平台 asset symlink、`metadata/current_assets` symlink 和共享 catalog。

## Package

快照已经压缩为单文件归档，并附带 manifest、marker 和 SHA-256 清单：

```text
package dir: /home/richard/data/cross-sectional-trees-cold/packages/hk-research-freeze-20260601
archive: hk-research-freeze-20260601.tar.zst
archive bytes: 205106541
archive sha256: 32ff3cd048eb33d5aaa067449932e4528b91700ee07995de46289565f271c6f4
tar non-directory entries: 28696
compression: tar | zstd -12 -T0 --long=27
```

`28696` 个 tar 非目录条目由 `28695` 个冻结文件和快照内的一个 `research-freeze-manifest.json` 组成。

验证命令：

```bash
cd /home/richard/data/cross-sectional-trees-cold/packages/hk-research-freeze-20260601
sha256sum -c SHA256SUMS
zstd -t hk-research-freeze-20260601.tar.zst
```

## 与数据平台冻结的关系

研究包是数据平台 release 的补充，不是替代：

```text
data assets: /home/richard/data/market-data-platform-cold/packages/hk-freeze-20260526
research outputs: /home/richard/data/cross-sectional-trees-cold/packages/hk-research-freeze-20260601
```

`cross-sectional-trees/artifacts/migration_backups/20260525_hk_data_platform_pre_switch` 是迁移时代的平台审计备份，保留原位，不重复装入研究包。它仍有旧 symlink 拓扑的审计价值，但日常恢复优先使用数据平台 release。

## 恢复

恢复研究产物前先查看计划：

```bash
cd /home/richard/code/research-workspace/cross-sectional-trees
python scripts/internal/freeze_hk_research_outputs.py hydrate
```

确认活跃目录没有冲突后，显式恢复：

```bash
python scripts/internal/freeze_hk_research_outputs.py hydrate --apply
```

脚本遇到同名目标会拒绝覆盖。数据平台资产仍需单独运行 `marketdata migration hydrate-hk --apply` 恢复。
