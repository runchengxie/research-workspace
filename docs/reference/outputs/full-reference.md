# 输出产物总览与交接索引

本页是跨仓库产物契约索引，说明 run 目录布局、固定元数据、公共 pipeline 产物和各 owner 的维护边界。字段细节以实际维护仓库的文档为准。

## 产物目录

默认运行目录通常为：

```text
artifacts/runs/<run_name>_<timestamp>_<hash>/
```

数据平台根目录和 artifact 路径由 workspace 的运行配置决定。

## Pipeline 产物

公共 `strategy-pipeline` 负责通用产物写入和运行摘要组装，主要包括：

- `summary.json`
- `config.used.yml`
- `inputs.lock.json`
- `run.log`
- `latest.json`
- `dropped_dates.csv`
- 数据集、信号、评估、回测和诊断产物的文件落盘

公共 pipeline 不生成策略信号，也不决定特征、组合或执行规则。它接收 owner 提供的结果和产物引用，并写入统一的 run 目录。

## Owner 归属

- `eval`、`dataset`、`split`、信号和研究评估字段由 `alpha-research` 维护。
- `backtest`、执行模拟、容量、benchmark、暴露、持仓和调仓差异由 `portfolio-backtester` 维护。
- provider 资产、数据契约、缓存和输入路径由 `market-data-platform` 维护。
- 研究运行入口、workspace 集成、发布记录和跨仓库交接由本仓库维护。

各 owner 仓库的输出文档：

- [alpha-research 研究输出](https://github.com/runchengxie/alpha-research/blob/main/docs/reference/research-outputs.md)
- [portfolio-backtester 回测输出](https://github.com/runchengxie/portfolio-backtester/blob/main/docs/reference/outputs/backtest-outputs.md)
- [portfolio-backtester 持仓输出](https://github.com/runchengxie/portfolio-backtester/blob/main/docs/reference/outputs/positions.md)
- [market-data-platform 文档](https://github.com/runchengxie/market-data-platform/tree/main/docs)

## 复现入口

`summary.json`、`config.used.yml`、`inputs.lock.json` 和 `latest.json` 共同构成一次 run 的复现入口。`inputs.lock.json` 记录输入数据和依赖版本，配合保存的配置可以定位同一次运行使用的环境和数据。

## 交接规则

跨仓库交接时，应同时提供 run 目录、摘要、输入锁定文件和对应 owner 的证据文件。策略名称、研究假设、凭证和私有运行手册不属于公共产物索引，应留在相应私有仓库。
