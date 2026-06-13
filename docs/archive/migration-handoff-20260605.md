# 迁移交接 - 2026-06-05

> status: archived
> owner: workspace
> last_verified: 2026-06-13
> source_of_truth: no
> superseded_by: ../bootstrap.md

本历史交接记录保存 2026-06-05 使用的定向 USB 迁移包和 WSL 恢复步骤。
当前新机器初始化从 [bootstrap.md](../bootstrap.md) 开始；当前 A 股迁移和恢复决策从
[data-transition-playbook.md](../data-transition-playbook.md) 开始。

本文最初用于新 32GB Windows + WSL 机器上的 Codex 交接。

## 目标

从 USB 盘恢复研究工作区，为 A 股 2015-2026 PIT top800 内存探针配置 WSL，
并在长任务运行前完成聚焦验证。

## USB 文件

挂载后的 USB 盘应包含：

```text
research_migration_targeted_20260605.tar.zst
research_migration_targeted_20260605.tar.zst.sha256
```

预期 SHA-256：

```text
765853fa0ce93e569d233571fdfebbc2ff7c1c8ee9e21feb4364069fcdd095a5
```

该归档是定向迁移包，包含顶层仓库代码、子仓库代码、
`cross-sectional-trees` 的配置、股票池和基准文件，以及 PIT top800
运行所需的 A 股 TuShare 2015-2026 平台资产。它不包含 `.venv`、
pytest / ruff / mypy 缓存、`.env` 文件和 `cross-sectional-trees/artifacts/cache`。

## 恢复步骤

1. 在 WSL 中挂载 USB 盘。如果 Windows 分配了其他盘符，需要相应调整 `/mnt/d`。

```bash
df -hT /mnt/d
ls -lh /mnt/d
```

2. 解压前先校验归档。

```bash
cd /home/richard
sha256sum -c /mnt/d/research_migration_targeted_20260605.tar.zst.sha256
```

如果校验文件里包含旧机器上的 `/mnt/d/...` 路径，且失败原因只是路径不同，
则手动计算：

```bash
sha256sum /mnt/d/research_migration_targeted_20260605.tar.zst
```

并与下列值比较：

```text
765853fa0ce93e569d233571fdfebbc2ff7c1c8ee9e21feb4364069fcdd095a5
```

3. 解压到 `/home/richard`。

```bash
mkdir -p /home/richard
tar -I zstd -xf /mnt/d/research_migration_targeted_20260605.tar.zst -C /home/richard
```

4. 确认关键路径存在。

```bash
ls -ld /home/richard/code/research-workspace
ls -ld /home/richard/data/market-data-platform/assets/tushare/a_share/daily/a_share_all_20150101_20260529_daily_clean
ls -l /home/richard/data/market-data-platform/assets/tushare/a_share/daily/a_share_all_daily_clean_latest
ls -l /home/richard/data/market-data-platform/assets/tushare/a_share/instruments/a_share_all_instruments_latest.parquet
ls -l /home/richard/code/research-workspace/cross-sectional-trees/configs/local/a_share_pit_top800_2015_memory_probe.yml
```

## WSL 内存设置

在 Windows 中编辑：

```text
%UserProfile%\.wslconfig
```

32GB 物理内存机器可参考：

```ini
[wsl2]
memory=24GB
swap=8GB
processors=8

[experimental]
autoMemoryReclaim=dropCache
```

然后在 PowerShell 运行：

```powershell
wsl --shutdown
```

重启 WSL 后检查：

```bash
free -h
```

## 环境变量

使用解压后的平台数据根目录：

```bash
export DATA_PLATFORM_ROOT=/home/richard/data/market-data-platform
```

如果需要长期保留，先确认路径正确，再写入新机器的 shell 配置文件。

## 依赖设置

迁移包有意不包含虚拟环境，需要重新创建：

```bash
cd /home/richard/code/research-workspace/cross-sectional-trees
uv sync --extra dev
```

如果运行需要可选依赖 extras，查看项目文档和当前 `pyproject.toml`。这次 A 股
TuShare 平台资产运行不应需要在线数据源凭证。

## 首轮检查

长任务前先跑轻量检查：

```bash
cd /home/richard/code/research-workspace/cross-sectional-trees
DATA_PLATFORM_ROOT=/home/richard/data/market-data-platform uv run python -m pytest tests/test_pipeline_memory_path.py -q
```

如有需要，再运行已有的小型 smoke 配置：

```bash
DATA_PLATFORM_ROOT=/home/richard/data/market-data-platform \
uv run cstree run --config configs/local/a_share_pit_top800_memory_smoke.yml
```

## 长任务目标

旧机器上的目标配置：

```bash
cd /home/richard/code/research-workspace/cross-sectional-trees
DATA_PLATFORM_ROOT=/home/richard/data/market-data-platform \
uv run cstree run --config configs/local/a_share_pit_top800_2015_memory_probe.yml
```

旧 8GB 可见内存的 WSL 机器在接近 6.5GB 内存保护阈值时失败：

```text
PIT pushdown: 9,322,611 -> 3,845,583 rows
Last peak: about 6.506GB
Stopped after Price column diagnostics, before Engineering features ...
```

在 32GB 物理内存、约 24GB 分配给 WSL 的机器上，这个任务可以作为下一次合理尝试。

## 如果需要 Codex 继续

新机器上可以给 Codex 的提示：

```text
请先阅读 /mnt/d/README_FOR_NEW_WSL_CODEX.md，然后按里面的迁移恢复步骤操作。目标是在新 WSL 中恢复 /home/richard/code/research-workspace 和 /home/richard/data/market-data-platform，跑 focused checks，再尝试 cross-sectional-trees 的 configs/local/a_share_pit_top800_2015_memory_probe.yml。不要把数据放到 /mnt/c 或 /mnt/d 下面运行，最终应放在 WSL ext4 路径 /home/richard/...。
```

## 备注

- 不要直接从 USB 盘运行长流水线。
- 数据保留在 `/home/richard/data/market-data-platform`，不要放在 `/mnt/c` 或 `/mnt/d` 下运行。
- `cross-sectional-trees/artifacts/cache` 需要在新机器上重建；迁移包有意排除了它。
- 迁移包不包含 `.env` 或 `.env.local`。
- 如果 `sha256sum -c` 只因为校验文件路径不同而失败，手动比较哈希值。
