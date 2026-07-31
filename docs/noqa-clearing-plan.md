# 子模块 noqa 清债计划

本计划处理六个子模块里大量 `# noqa` 注释导致的质量门禁失效问题。顶层工作区自身只有 3 处 `# noqa`，门禁有效。子模块底层几乎全靠 `# noqa` 压制告警，新人接手时提示被淹没，不敢改动旧代码。这是阻碍多人协作的主要技术债。

## 与现有治理文件的关系

本计划与以下文件互补，不重叠：

- `maintainability-refactor-roadmap.yml`：用 ratchet-only 预算管体量热点（大文件、长函数、复杂度）。本计划不管体量，只清 `# noqa` 压制的 lint 告警。
- `submodule-refactor-plan.md` 与 `code-size-review.md`：管子模块巨型文件拆分，是 roadmap 文件拆分的落地设计。本计划不拆分文件。

两者是不同维度。本计划清理后若某文件因移除 dead import 而跌破大文件阈值，按 roadmap 规则在同一次提交下调对应 budget，不在本计划预改 roadmap 数字。

## 现状数据

各子模块 `# noqa` 总量（按从少到多排列，便于排期）：

| 子模块 | `# noqa` 总量 | 预推送门禁命令来源 |
| --- | --- | --- |
| `quant-execution-engine` | 74 | `scripts/submodule_checks.json` 的 `full` profile |
| `portfolio-backtester` | 1204 | 同左 |
| `market-data-platform` | 2498 | 同左 |
| `research-apps` | 3108 | 仓库自有 `scripts/dev/check.py` |
| `strategy-pipeline` | 3129 | 仓库 `scripts/dev/run_tests.sh` |
| `alpha-research` | 4244 | `scripts/submodule_checks.json` 的 `full` profile |

规则类别分布（每个子模块的前几类，`grep` 实测）：

- `F401` 未使用导入：每个子模块 1000 条左右（alpha-research 1279、research-apps 1173、strategy-pipeline 1129、market-data-platform 1016、portfolio-backtester 202、quant-execution-engine 16）
- `E501` 行过长：market-data-platform 91、portfolio-backtester 251、research-apps 465、strategy-pipeline 469
- `D102`/`D205`/`D107` 缺失文档字符串：alpha-research 177+95+58、market-data-platform 194+96+59、research-apps 177+95+58、strategy-pipeline 196+95+58
- `F403`/`F405` 星号导入：strategy-pipeline 148、market-data-platform 71、research-apps 64、portfolio-backtester 56、alpha-research 含 71
- `F821`/`F822` 未定义或仅在测试定义：各子模块 50 到 95 条
- `S101` 生产代码使用 assert：portfolio-backtester 56、research-apps 57、alpha-research 56
- `PLR0913` 参数过多：market-data-platform 121、research-apps 43、strategy-pipeline 43、alpha-research 43

## 关键发现：幽灵债务

所有六个子模块的 `pyproject.toml` 都没有在 `select` 里启用 pydocstyle（D 类规则），但统计里却有大量 `D102`/`D205`/`D107` 的 `# noqa`。这些注释是历史残留：曾经启用过 D 类，后来关闭，但 `# noqa` 没有清理。删除这类注释零风险，且不需要改任何代码。

`quality-governance.md` 已记录顶层预推送门禁会运行各子模块登记的 `full` profile，子模块清理后门禁才能真实发现问题。

## 清债三原则

1. 分批推进，每批只动一个子模块的一个规则类别，配套运行该子模块测试，避免一次性大改动难以回滚。
2. 先清幽灵债务（D 类），再清机械可修（`F401`/`E501` 中客观超长的），最后处理需人工判断的（`F403` 星号导入、`F821`/`S101`/`PLR0913`）。
3. 每批清理后必须让该子模块的预推送 `full` profile 通过，再提交。不要跳过仓库原有门禁。

## 规则分类与处理方式

### 第一类：幽灵债务（直接删注释，零代码改动）

- `D102`/`D205`/`D107` 及任何子模块 `select` 未启用的规则对应的 `# noqa`。
- 处理：用脚本扫描每个 `# noqa` 的规则码，若码不在该子模块 `select` 内，直接删除该码（多码时只删对应码，保留其余）。
- 风险：无。处理完 ruff 行为不变。

### 第二类：机械可修（工具自动修，需复核）

- `F401` 未使用导入：ruff 自带 `--fix` 可移除。移除前要确认不是 re-export（有些 `__init__.py` 故意导出供外部 import）。对 `src/*/__init__.py` 的 `F401` 需人工核对再删。
- `E501` 行过长：优先用 `ruff format` 自动折行。个别无法折行的长字符串保留 `# noqa: E501` 并补原因。
- `F811` 重复定义、`F841` 赋值未使用：ruff `--fix` 可处理大部分，但 `F841` 有时是故意占位，需看上下文。

### 第三类：需人工判断（逐文件处理，谨慎解除）

- `F403`/`F405` 星号导入：改为显式导入列表，或保留并登记 `per-file-ignores`（参考 `quant-execution-engine` 的做法，写清原因和移除条件）。
- `F821`/`F822` 未定义名称：多为动态属性或测试夹具，确认后保留并登记 `per-file-ignores`。
- `S101` 生产代码 assert：能改为显式校验的就改，不能改的登记 `per-file-ignores`。
- `PLR0913` 参数过多：属于设计问题，不在清债范围，只处理对应的 `# noqa`，让告警浮现，后续单独做函数拆分。

## 分批路线

按风险从低到高、收益从高到低排序。

### 批次 0：幽灵债务清理（全子模块，低风险高收益）

- 范围：所有子模块里 `select` 未启用的规则码对应的 `# noqa`。
- 动作：脚本批量删除对应码。
- 预计削减：D 类约 1500 条以上（四个子模块的 D102+D205+D107 合计）。
- 验证：`uv run --locked ruff check <子模块>` 结果与清理前一致（告警数不增）。

### 批次 1：quant-execution-engine（74 条，练手）

- 已是全仓最干净，且唯一有 `per-file-ignores` 结构，适合作为模板。
- 先清 `F401`（16）和 `E402`（6），再处理 `F811`（6）、`E741`（4）等零星项。
- 目标：该子模块 `# noqa` 归零或仅剩登记在 `per-file-ignores` 的项。

### 批次 2：portfolio-backtester（1204 条）

- 先做批次 0 的幽灵债务。
- 再清 `E501`（251）和 `F401`（202），这两类占多数且机械可修。
- `F822`（94）多为动态注册，逐文件登记 `per-file-ignores`。

### 批次 3：market-data-platform（2498 条）

- 幽灵债务清理后，处理 `F401`（1016）和 `PLR0913`（121）。
- `FBT001`/`FBT002`（f-string 用于日志）按仓库日志规范决定保留或改。

### 批次 4：research-apps（3108 条）

- `select` 范围最宽（含 A/ARG/ASYNC/FA/FIX 等），先核对实际启用规则，再清幽灵债务。
- `F401`（1173）和 `E501`（465）机械可修。

### 批次 5：strategy-pipeline（3129 条）

- `F401`（1129）和 `E501`（469）为主。
- `F403`（148）星号导入需逐文件改显式导入。

### 批次 6：alpha-research（4244 条，最大量）

- 放最后，吸收前几批经验。
- `F401`（1279）机械可修，`F403`/`F405` 需逐文件处理。

## 与预推送门禁衔接

各子模块推送时运行 `scripts/submodule_checks.json` 登记的 `full` profile。清理过程中：

- 每批提交前在子模块内运行其 `full` profile 对应的命令（`uv run --locked ruff check .` 等），确保不引入新告警。
- 若清理导致某文件 `F401` 移除后暴露真正 dead code，单独开一个清理提交，不要混入门禁修复。
- `quant-execution-engine` 的 `per-file-ignores` 模式应作为其他子模块的范本：对确需保留的忽略项，登记原因、负责人和移除条件，避免散落 `# noqa`。

## 验证与回滚

- 每批用 `git diff --stat` 确认改动文件数可控，单批不超过一个子模块的一个规则类别。
- 清理后运行该子模块测试套件（命令见各子模块 `scripts/dev/` 或 `submodule_checks.json`）。
- 若 ruff 行为异常，单文件 `git checkout` 回滚，不整体 revert。
- 批次 0 完成后跑一次顶层 `python scripts/run_quality_checks.py --profile hard` 确认顶层不受影响。

## 不建议做的事

- 不要一次性全局删除所有 `# noqa`，会混入真实问题且难以 review。
- 不要为降低数量而扩大 `ignore` 或 `per-file-ignores` 的覆盖面，那只是把债藏得更深。
- 不要把 `PLR0913`/`C901` 等设计类告警用 `# noqa` 压回去，它们的浮现是清理的目的之一。
- 不要在未运行子模块测试的情况下提交清理结果。

## 进度记录

| 批次 | 子模块 | 规则类别 | 状态 | 削减条数 |
| --- | --- | --- | --- | --- |
| 0 | 全部 | 幽灵债务（D 类等） | 待开始 | |
| 1 | quant-execution-engine | 全部 | 待开始 | |
| 2 | portfolio-backtester | F401/E501/F822 | 待开始 | |
| 3 | market-data-platform | F401/PLR0913 | 待开始 | |
| 4 | research-apps | F401/E501 | 待开始 | |
| 5 | strategy-pipeline | F401/E501/F403 | 待开始 | |
| 6 | alpha-research | F401/F403 | 待开始 | |
