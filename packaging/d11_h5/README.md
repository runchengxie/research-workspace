# D11-H5 完整复现包

本包包含 `research-workspace`、六个子模块、D11-H5 冻结研究账本和所需日频数据。
市场数据与研究账本可以离线读取。首次创建 Python 环境时需要联网安装第三方依赖。

## 快速开始

需要 Linux、Bash 和 Python 3.12。解压后进入包目录：

```bash
./start.sh doctor
./start.sh demo
```

`demo` 会在 `.runtime/venv` 创建隔离环境，并使用 2026 年 8 月 3 日收盘数据生成
2026 年 8 月 4 日开盘目标。结果写入 `outputs/d11_h5_shadow`。
如 Python 3.12 的命令名或路径不同，可设置 `D11_H5_PYTHON`。启动脚本只安装
D11-H5 所需的五个项目和第三方依赖，包内仍保留六个子模块的完整源码。

指定日期运行：

```bash
./start.sh run --source-date 20260803 --signal-date 20260804
```

完整校验包内文件：

```bash
./start.sh verify
```

## 可选分钟包

分钟数据单独提供。将分钟压缩包解压到完整复现包所在的同一父目录，归档中的路径会自动合并到
本包。再次运行 `./start.sh doctor` 后，会显示 TuShare 一分钟快照已经安装。

分钟数据不参与当前 D11-H5 日频信号计算。它用于成交参与率、冲击和无法成交等执行研究。

## 目录说明

- `code/research-workspace`：主仓库和六个子模块的封存源码。
- `data/market-data-platform`：D11-H5 所需日频行情、股票名称和交易日历。
- `research-artifacts/strategy-pipeline`：冻结模型框架、评分账本及相关研究产物。
- `outputs`：本地复现结果，首次运行后创建。
- `package_manifest.json`：代码提交、数据来源、文件数量和逻辑大小。
- `PACKAGE_FILES.sha256`：包内静态文件校验清单。

## 复现边界

该命令复现研究影子信号和五个错峰袖套的合并目标。产物仍保留
`research_only=true` 和 `eligible_for_live=false`。包内没有券商委托回报，也未据此校准真实成交冲击。
