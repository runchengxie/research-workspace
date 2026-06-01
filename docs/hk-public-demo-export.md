# 港股公开 demo clean-room export

港股公开展示库使用独立 clean-room export，不从历史仓库直接推送 Git 历史，也不作为
workspace submodule。当前 staging 目标是：

```text
https://github.com/runchengxie/hk-cross-sectional-strategy-demo
license: MIT
maintenance: paused
```

发布必须由维护者在检查 staged tree 后显式执行。本工作区脚本不会创建远端仓库或 push。
本工作区只把该仓库作为外部作品集 reference 链接，不把它加入 required submodule。

## 导出

```bash
python scripts/export_hk_public_demo.py --out /tmp/hk-cross-sectional-strategy-demo
```

版本化 allowlist 位于 `demo/hk-public-demo-allowlist-v1.txt`。模板只包含 synthetic fixture、
离线 workflow、样例输出生成器、架构说明、免责声明、MIT license 和最小 CI。

导出器会：

1. 仅复制 allowlist 文件，不复制 `.git`。
2. 运行 synthetic workflow，生成 `samples/summary.json` 与 `samples/targets.json`。
3. 运行标准库 `unittest` smoke。
4. 扫描凭证、`.env*`、provider cache、Parquet、私有输出、本地绝对路径、压缩包和超大文件。
5. 写入 `export-manifest.json`，记录 source revision、纳入文件、生成文件、扫描和 smoke 结果。

审查任意 staged tree：

```bash
python scripts/export_hk_public_demo.py --scan-only /tmp/hk-cross-sectional-strategy-demo
```

2026-06-01 的最新离线复核 staging 位于：

```text
/tmp/hk-cross-sectional-strategy-demo-verify-20260601-maintenance
export-manifest.json: scan=passed, offline_smoke=passed
```

## 边界

- 不包含真实行情、RQData / TuShare 数据、provider cache、凭证或历史收益宣传。
- 不包含券商 adapter，不声称可用于真实交易。
- 不与 A 股主项目双向同步需求；它是暂停维护的作品集展示和历史 reference。
