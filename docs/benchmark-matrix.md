# 统一考试表（Benchmark Matrix）

> status: active
> owner: workspace
> last_verified: 2026-08-11
> source_of_truth: yes
> superseded_by: n/a

本页说明统一考试表的标准格式与生成方式。统一考试表对应论文 FinBENCH 的思路：
同一个模型要在多个股票池、预测周期、市场状态和成本假设下报告一组成绩，禁止只报单个数字。

## 为什么需要统一考试表

单个回测数字无法回答换股票池、换周期、换市场状态还有没有效，扣掉成本还剩多少。
统一考试表把这些维度固定成一张标准表，让模型表现可以公平比较，也让"某个策略在什么
条件下有效"这种问题可以被回答。

## 四根轴

每一条结果是四个维度的组合加上一个指标：

| 轴 | 含义 |
| --- | --- |
| `universe` | 股票池 |
| `horizon` | 预测周期 |
| `regime` | 市场状态 |
| `cost_bps` | 交易成本（基点） |

指标默认为 `sharpe`，也可以用 `--metric` 换成其他数值，例如 `ic` 或 `return`。

## 输入格式

生成器读取 `benchmark_rows.v1` 原始结果，例如：

```json
{
  "schema_version": "benchmark_rows.v1",
  "rows": [
    {"universe": "csi300", "horizon": "h5", "regime": "bull", "cost_bps": 20, "sharpe": 0.7},
    {"universe": "csi500", "horizon": "h5", "regime": "bull", "cost_bps": 20, "sharpe": 1.1},
    {"universe": "csi500", "horizon": "h20", "regime": "bear", "cost_bps": 50, "sharpe": -0.2}
  ]
}
```

每条结果必须包含四根轴和一个数值指标，四根轴完全相同的重复行会被拒绝。

## 生成命令

```bash
python scripts/benchmark_matrix_build.py --input rows.json
```

检查是否满足考试表要求，不满足时以退出码 1 结束：

```bash
python scripts/benchmark_matrix_build.py --input rows.json --check
```

写出标准矩阵文件：

```bash
python scripts/benchmark_matrix_build.py --input rows.json --output matrix.json
```

换成其他指标：

```bash
python scripts/benchmark_matrix_build.py --input rows.json --metric ic --check
```

## 输出格式

输出是 `benchmark_matrix.v1`，`cells` 直接兼容证据门禁的 `benchmark_matrix` 检查项：

```json
{
  "schema_version": "benchmark_matrix.v1",
  "metric": "sharpe",
  "axes": ["universe", "horizon", "regime", "cost_bps"],
  "cells": []
}
```

## 考试规则

一条结果或只有一根轴在变化都不能算考试表。`--check` 要求至少两条结果且覆盖至少两个
维度，与证据门禁的 `benchmark_matrix` 检查规则一致。先跑生成器自检，再把结果放进
证据包，避免把单点结果写进策略证据。

## 与证据门禁的关系

- 生成器负责把原始回测结果汇成标准考试表，见本页
- 证据门禁负责在策略评审时要求这张表，见 [strategy-evidence-gate.md](strategy-evidence-gate.md)
- 实验说明书描述实验做了什么，见 [research-spec.md](research-spec.md)

三条链路共用 universe、horizon、regime、cost 词汇，实验说明书声明维度，生成器汇总
结果，门禁审查证据是否达标。
