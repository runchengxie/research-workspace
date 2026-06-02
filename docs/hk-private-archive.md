# 中国香港市场私有 legacy 归档

当前活跃主线是 A 股。中国香港市场真实业务代码进入“私有归档候选 + 显式恢复”治理阶段，
但本轮不直接删除恢复敏感实现或兼容入口。

## 仓库策略

私有候选仓库暂定为：

```text
hk-quant-legacy-archive
```

它必须是 private、paused-maintenance、restore-only 仓库。远端地址和访问控制 owner 在人工发布
前显式确认；该仓库不加入 superproject submodule、默认 CI、release matrix 或 A 股运行依赖。

私有归档和公开 demo 是两条不同路径：

- 私有归档可以保留经过清单约束的 provider 业务代码、历史配置和测试。
- 公开 demo 仍只承接 synthetic / public-safe clean-room 示例。
- 两条路径都不承接凭证、行情文件、provider cache、研究 run、券商 adapter 或交易审计日志。

## 清单和命令

私有清单：

```text
docs/hk-private-archive-manifest.yml
```

只读检查：

```bash
python scripts/hk_archive_gate.py --check --format json
```

在工作区外 staging：

```bash
python scripts/export_hk_legacy_archive.py \
  --out /tmp/hk-quant-legacy-archive-stage

python scripts/hk_archive_gate.py \
  --check \
  --export-manifest /tmp/hk-quant-legacy-archive-stage/archive-export-manifest.json \
  --format json
```

exporter 只从清单中 pin 的 Git revision 导出 allowlist 文件并生成 SHA-256；它不复制 `.git`，
不创建远端仓库，不修改 submodule，不删除源文件。

## 保留在活跃仓库的边界

以下能力不进入 legacy 私有归档迁出范围：

- `marketdata migration freeze-hk`、`hydrate-hk` 和 freeze marker；
- 标准 `targets.json` 多市场解析、FX、dry-run、风控和审计；
- `quant-execution-engine` 中的 LongPort broker runtime。

任何兼容入口的实际删除必须等待 restore evidence、consumer audit、replacement docs、
rollback notes、focused tests、私有 staging 证据和 zero-usage release window 全部完成，并在
单独 follow-up change 中实施。
