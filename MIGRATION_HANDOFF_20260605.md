# Migration Handoff - 2026-06-05

This file is for Codex on the new 32GB Windows + WSL machine.

## Objective

Restore the research workspace from the USB drive, configure WSL for the A-share 2015-2026 PIT top800 memory probe, and run focused validation before the long run.

## USB Files

Expected files on the mounted USB drive:

```text
research_migration_targeted_20260605.tar.zst
research_migration_targeted_20260605.tar.zst.sha256
```

Expected SHA256:

```text
765853fa0ce93e569d233571fdfebbc2ff7c1c8ee9e21feb4364069fcdd095a5
```

The archive is a targeted migration package. It includes the superproject code, subrepo code, cross-sectional-trees configs/universe/benchmarks, and the A-share TuShare 2015-2026 platform assets needed by the PIT top800 run. It excludes `.venv`, pytest/ruff/mypy caches, `.env` files, and `cross-sectional-trees/artifacts/cache`.

## Restore Steps

1. Mount the USB drive in WSL. Adjust `/mnt/d` if Windows assigns another drive letter.

```bash
df -hT /mnt/d
ls -lh /mnt/d
```

2. Verify the archive before extraction.

```bash
cd /home/richard
sha256sum -c /mnt/d/research_migration_targeted_20260605.tar.zst.sha256
```

If the checksum file contains `/mnt/d/...` from the old machine and fails only because the path differs, run:

```bash
sha256sum /mnt/d/research_migration_targeted_20260605.tar.zst
```

and compare it to:

```text
765853fa0ce93e569d233571fdfebbc2ff7c1c8ee9e21feb4364069fcdd095a5
```

3. Extract into `/home/richard`.

```bash
mkdir -p /home/richard
tar -I zstd -xf /mnt/d/research_migration_targeted_20260605.tar.zst -C /home/richard
```

4. Confirm key paths exist.

```bash
ls -ld /home/richard/code/research-workspace
ls -ld /home/richard/data/market-data-platform/assets/tushare/a_share/daily/a_share_all_20150101_20260529_daily_clean
ls -l /home/richard/data/market-data-platform/assets/tushare/a_share/daily/a_share_all_daily_clean_latest
ls -l /home/richard/data/market-data-platform/assets/tushare/a_share/instruments/a_share_all_instruments_latest.parquet
ls -l /home/richard/code/research-workspace/cross-sectional-trees/configs/local/a_share_pit_top800_2015_memory_probe.yml
```

## WSL Memory Setup

On Windows, edit:

```text
%UserProfile%\.wslconfig
```

Suggested contents for a 32GB physical-memory machine:

```ini
[wsl2]
memory=24GB
swap=8GB
processors=8

[experimental]
autoMemoryReclaim=dropCache
```

Then run from PowerShell:

```powershell
wsl --shutdown
```

Restart WSL and check:

```bash
free -h
```

## Environment

Use the extracted platform data root:

```bash
export DATA_PLATFORM_ROOT=/home/richard/data/market-data-platform
```

If you want this persistent, add it to the shell profile on the new machine after verifying the path.

## Dependency Setup

The migration package intentionally excludes virtual environments. Recreate them.

```bash
cd /home/richard/code/research-workspace/cross-sectional-trees
uv sync --extra dev
```

If optional extras are needed by the run, inspect the project docs and current `pyproject.toml`. For this A-share TuShare platform-assets run, no online provider credentials should be needed.

## First Checks

Start with lightweight checks before the long run.

```bash
cd /home/richard/code/research-workspace/cross-sectional-trees
DATA_PLATFORM_ROOT=/home/richard/data/market-data-platform uv run python -m pytest tests/test_pipeline_memory_path.py -q
```

Then run the existing small smoke config if desired:

```bash
DATA_PLATFORM_ROOT=/home/richard/data/market-data-platform \
uv run cstree run --config configs/local/a_share_pit_top800_memory_smoke.yml
```

## Long Run Target

The target config from the old machine:

```bash
cd /home/richard/code/research-workspace/cross-sectional-trees
DATA_PLATFORM_ROOT=/home/richard/data/market-data-platform \
uv run cstree run --config configs/local/a_share_pit_top800_2015_memory_probe.yml
```

The old 8GB-visible WSL machine failed near the 6.5GB guard rail:

```text
PIT pushdown: 9,322,611 -> 3,845,583 rows
Last peak: about 6.506GB
Stopped after Price column diagnostics, before Engineering features ...
```

On a 32GB physical-memory WSL machine with about 24GB assigned to WSL, this run is expected to be a reasonable next attempt.

## If Codex Is Asked To Continue

Suggested prompt for Codex on the new machine:

```text
请先阅读 /mnt/d/README_FOR_NEW_WSL_CODEX.md，然后按里面的迁移恢复步骤操作。目标是在新 WSL 中恢复 /home/richard/code/research-workspace 和 /home/richard/data/market-data-platform，跑 focused checks，再尝试 cross-sectional-trees 的 configs/local/a_share_pit_top800_2015_memory_probe.yml。不要把数据放到 /mnt/c 或 /mnt/d 下面运行，最终应放在 WSL ext4 路径 /home/richard/...。
```

## Notes

- Do not run the long pipeline directly from the USB drive.
- Keep data under `/home/richard/data/market-data-platform`, not under `/mnt/c` or `/mnt/d`.
- Rebuild `cross-sectional-trees/artifacts/cache` on the new machine; it was excluded intentionally.
- The migration package does not include `.env` or `.env.local`.
- If `sha256sum -c` fails only because the checksum file path differs, compare the hash manually.
