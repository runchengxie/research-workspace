# Bootstrap

本文档只描述 `research-workspace` 这层如何在新机器上拉起一组可复现 checkout。各子项目的完整依赖、凭证和业务命令仍以各自 README / docs 为准。

## Clone

```bash
git clone --recurse-submodules https://github.com/runchengxie/research-workspace.git
cd research-workspace
```

如果已经克隆了顶层仓库：

```bash
git submodule sync --recursive
git submodule update --init --recursive
```

确认 submodule 指针和本地状态：

```bash
git submodule status
python scripts/workspace_doctor.py
```

发布前或 bump submodule 前建议使用严格模式：

```bash
python scripts/workspace_doctor.py --strict
```

## Dependencies

推荐在每个子项目目录中独立安装依赖，不在顶层创建共享 Python package 或共享虚拟环境。

```bash
cd market-data-platform
uv sync --extra dev

cd ../cross-sectional-trees
uv sync --extra dev --extra rqdata

cd ../rqdata-hk-depth-snapshots
uv sync --group dev --extra rqdata

cd ../quant-execution-engine
uv sync --group dev --extra cli

cd ..
```

如果只需要只读文档和顶层检查脚本，顶层不需要额外安装依赖；`scripts/` 和 `tests/` 只使用 Python 标准库。

## Environment

共享数据根目录应放在仓库外部或明确的 artifacts root 中，并通过环境变量传给各模块：

```bash
export DATA_PLATFORM_ROOT=/path/to/research-artifacts
```

常见共享路径：

```text
$DATA_PLATFORM_ROOT/
  assets/
  metadata/
    current_assets/
      hk_current.json
      cn_current.json
    dataset_registry.csv
  reports/
```

不要把以下内容提交到顶层 Git：

- `.env`、`.env.*`、`.envrc`、本地凭证文件。
- `artifacts/`、`outputs/`、`data/`、`cache/` 等大型产物或缓存。
- 券商实盘凭证。实盘凭证应遵循 `quant-execution-engine` 自身文档，放在用户私有位置。

## Smoke Checks

顶层只提供轻量检查，不替代子项目测试：

```bash
python scripts/workspace_doctor.py
python scripts/smoke_contracts.py
python -m unittest discover -s tests
```

`smoke_contracts.py` 只运行无写入、无真实下单的 CLI / contract 检查。任何需要凭证、网络、下载数据或提交订单的流程都必须在对应子项目内显式执行。
