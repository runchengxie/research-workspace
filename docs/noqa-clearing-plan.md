# 子模块 noqa 清债计划

> status: reference
> owner: workspace
> last_verified: 2026-08-17
> source_of_truth: no
> superseded_by: maintainability-governance.md

本页保留 2026-08-11 的专项盘点和执行记录。当前债务数量、预算与行动状态以[维护性治理](maintainability-governance.md)、`maintainability-refactor-roadmap.yml` 和[工作区路线图](roadmap.md)为准。

## 当前结论（2026-08-11 复核后）

- `market-data-platform` 的 `F401` 经 worktree 实测后确认是 facade re-export 壳重新导出拆分符号的标准写法（27/30 个文件 docstring 已声明），并非技术债。这部分已通过 `pyproject.toml` 的 28 条 `per-file-ignores` 收口并合并（PR #13），不再作为清债目标。
- 实测复核：按各仓库 tracked Python 文件统计，`market-data-platform` 当前共 68 处内联 `# noqa`，其中 52 处为 `PLR0913`，其余主要是组合复杂度与分支类抑制。`src/` 内零内联 `F401`。早期「1036 处、F401 占 951」是未收口前的口径，已不反映现状，仅保留作历史记录。
- 其余子模块自有代码 # noqa 本来极少，门禁在子模块层有效。本计划的实际清债空间很小，重点转为「让设计类告警浮现、后续做函数拆分」。

## 与现有治理文件的关系

本计划与以下文件互补，不重叠：

- `maintainability-refactor-roadmap.yml`：用 ratchet-only 预算管体量热点（大文件、长函数、复杂度）。本计划不管体量，只清 `# noqa` 压制的 lint 告警。
- `submodule-refactor-plan.md` 与 `code-size-review.md`：管子模块巨型文件拆分，是 roadmap 文件拆分的落地设计。本计划不拆分文件。

两者是不同维度。本计划清理后若某文件因移除 dead import 而跌破大文件阈值，按 roadmap 规则在同一次提交下调对应 budget，不在本计划预改 roadmap 数字。

## 现状数据

各子模块自有代码 `# noqa` 真实数量（仅统计 tracked Python 文件，`git grep` 实测，2026-08-11）：

| 子模块 | `# noqa` 真实量 | 主要规则 | 预推送门禁命令来源 |
| --- | --- | --- | --- |
| `market-data-platform` | 68 | `PLR0913`(52)，其余主要是 `C901`/`PLR0912`/`PLR0915` 组合 | `scripts/submodule_checks.json` 的 `full` profile |
| `strategy-pipeline` | 16 | `F403`(15)、`F401`(1) | 仓库 `scripts/dev/run_tests.sh` |
| `alpha-research` | 5 | `F403`(2)，以及 `F401`/`E402`/`C416` 各 1 | `scripts/submodule_checks.json` 的 `full` profile |
| `quant-execution-engine` | 10 | `E402`(6)、`F403`(2) | 同左 |
| `portfolio-backtester` | 7 | `F403`(3)、`F401`(3) | 同左 |
| `strategy-app` | 0 | 无 | 仓库自有 `scripts/dev/check.py` |

规则类别分布（仅自有代码，排除 `.venv`）：

- `F401` 未使用导入：market-data-platform 的 facade re-export 已通过显式配置收口，当前内联项只在其他仓库零星存在。
- `F403` 星号导入：`strategy-pipeline`（15）、`alpha-research`（2）、`quant-execution-engine`（2）、`portfolio-backtester`（3）。
- `PLR0913`/`PLR0915` 参数/分支过多：主要集中在 `market-data-platform`，属设计类告警。
- `E402` 模块级导入不在文件顶部：`quant-execution-engine`（6，多为测试/脚本引导）。
- `RUF002` 非 ASCII 名称无备注：`alpha-research`（5）。

## 关键发现：此前列报被 `.venv` 夸大

初版计划用 `grep -rc 'noqa' <子模块>` 统计，把每个子模块 `.venv` 里第三方包（pluggy、pygments、`_pytest`、packaging 等）的大量 `# noqa` 也算进项目代码，得出 alpha-research 4244、research-apps 3108 等数字。排除 `.venv` 后，真实自有代码仅约 1100 处，且 `market-data-platform` 占九成以上。

因此原先「子模块底层几乎全靠 `# noqa` 压制门禁、新人不敢改」的判断不成立。子模块自有代码基本没有被 `# noqa` 淹没，门禁在子模块层是有效的。真正的 noqa 集中在 `market-data-platform` 的 `F401`，清债价值在于顺带暴露未使用导入与潜在 dead code，而非恢复门禁能力。

所有子模块 `pyproject.toml` 的 `select` 都没有启用 pydocstyle（D 类），但自有代码里也几乎没有 D 类 `# noqa`（初版看到的 D102/D205/D107 全部来自 `.venv`）。所以本计划不存在「幽灵债务批量删注释」的空间，几乎每条 noqa 都对应真实启用的规则。

## 清债三原则

1. 分批推进，每批只动一个子模块的一个规则类别，配套运行该子模块测试，避免一次性大改动难以回滚。
2. 先机械可修（`F401` 未使用导入），再处理需人工判断的（`F403` 星号导入、`PLR0913` 参数过多、`E402` 导入位置）。
3. 每批清理后必须让该子模块的预推送 `full` profile 通过，再提交。不要跳过仓库原有门禁。

## 规则分类与处理方式

### 第一类：机械可修（工具自动修，需复核）

- `F401` 未使用导入：ruff 自带 `--fix` 可移除。移除前要确认不是 re-export（有些 `__init__.py` 故意导出供外部 import）。对 `src/*/__init__.py` 的 `F401` 需人工核对再删。集中在 `market-data-platform`（951 条）。
- `E501` 行过长：优先用 `ruff format` 自动折行。当前自有代码里此类极少，只在 `.venv` 出现，项目代码无需处理。

### 第二类：需人工判断（逐文件处理，谨慎解除）

- `F403` 星号导入：改为显式导入列表，或保留并登记 `per-file-ignores`（参考 `quant-execution-engine` 的做法，写清原因和移除条件）。集中在 `strategy-pipeline`（35 条）。
- `PLR0913`/`PLR0915` 参数/分支过多：属于设计问题，不在清债范围，只处理对应的 `# noqa`，让告警浮现，后续单独做函数拆分。集中在 `market-data-platform`（63 条）。
- `E402` 模块级导入不在文件顶部：多为测试/脚本引导，确认后保留并登记 `per-file-ignores`。集中在 `quant-execution-engine`（6 条）。
- `RUF002` 非 ASCII 名称无备注：按仓库规范补备注或改名，集中在 `alpha-research`（5 条）。

## 分批路线

按工作量从大到小排序，聚焦真正有量的两个子模块。

### 批次 1：market-data-platform（F401 已收口，剩余为设计类告警）

- `F401`（原 951 条）：已确认为 facade re-export，通过 `pyproject.toml` 的 28 条 `per-file-ignores` 收口并合并（PR #13），不再清理。误删会破坏对外 API。
- `PLR0913`/`PLR0915` 等设计类抑制当前约 66 条：后续以函数拆分为主，不在未改结构时机械删除有效 `# noqa`。
- 验证：`uv run --locked ruff check .` 与 `scripts/dev/check.py` 通过，跑该仓测试套件。

### 批次 2：strategy-pipeline（16 条）

- `F403`（15）星号导入：逐文件改为显式导入列表，对不便改的登记 `per-file-ignores`。
- 验证：仓库 `scripts/dev/run_tests.sh full` 通过。

### 批次 3：其余小量（alpha-research 5、quant-execution-engine 10、portfolio-backtester 7、strategy-app 0）

- 合并处理：alpha 的 2 处 `F403` 与 3 处零星抑制逐项复核，qexec 的 6 处 `E402` 登记明确原因，portfolio 的 `F403`/`F401` 逐文件处理。
- 这些子模块量极小，可一次提交清完，不必单独排期。

## 与预推送门禁衔接

各子模块推送时运行 `scripts/submodule_checks.json` 登记的 `full` profile。清理过程中：

- 每批提交前在子模块内运行其 `full` profile 对应的命令（`uv run --locked ruff check .` 等），确保不引入新告警。
- 若清理导致某文件 `F401` 移除后暴露真正 dead code，单独开一个清理提交，不要混入门禁修复。
- `quant-execution-engine` 的 `per-file-ignores` 模式应作为其他子模块的范本：对确需保留的忽略项，登记原因、负责人和移除条件，避免散落 `# noqa`。

## 验证与回滚

- 每批用 `git diff --stat` 确认改动文件数可控，单批不超过一个子模块的一个规则类别。
- 清理后运行该子模块测试套件（命令见各子模块 `scripts/dev/` 或 `submodule_checks.json`）。
- 若 ruff 行为异常，单文件 `git checkout` 回滚，不整体 revert。
- 批次 1 完成后跑一次顶层 `python scripts/run_quality_checks.py --profile hard` 确认顶层不受影响。

## 不建议做的事

- 不要一次性全局删除所有 `# noqa`，会混入真实问题且难以 review。
- 不要为降低数量而扩大 `ignore` 或 `per-file-ignores` 的覆盖面，那只是把债藏得更深。
- 不要把 `PLR0913`/`C901` 等设计类告警用 `# noqa` 压回去，它们的浮现是清理的目的之一。
- 不要在未运行子模块测试的情况下提交清理结果。

## 进度记录

| 批次 | 子模块 | 规则类别 | 状态 | 削减条数 |
| --- | --- | --- | --- | --- |
| 1 | market-data-platform | F401/PLR0913 | 部分完成 | F401 已收口，现存 68 条设计类或特殊导入抑制待专项拆分 |
| 2 | strategy-pipeline | F403 | 自然收敛，待专项复核 | tracked Python 文件总量 38→16，其中 F403 35→15 |
| 3 | alpha-research / quant-execution-engine / portfolio-backtester / strategy-app | E402/F403/F401/C416 | 待专项复核 | 合计 26→22 |

## 执行记录与修正（2026-07-31）

在 `market-data-platform` 子仓库建独立 worktree（`feat/noqa-f401-cleanup`）实测，推翻了原计划关于 F401 的假设。

### 发现 1：早期「1020 处幽灵 noqa」是窄上下文误报

初版计划用 ruff RUF100 单独扫描，报 `market-data-platform` 有 1020 处 `# noqa` 压的规则码在当前 `select` 里未触发违规，判定为纯多余注释。后续在 worktree 内以项目完整配置（不限定 `--select`、不 `--isolated`）复测，结论相反：`ruff check src/` 在完整 `select`（含 `PLR0913`、`C901`、`PLR0912`、`PLR0915` 等）下直接全过，RUF100 实为 0。

根因：RUF100 判定「noqa 是否多余」依赖当前启用的规则集。用 `--select RUF100` 单独跑时，ruff 不知道项目还启用 `PLR0913` 等，便把 `# noqa: PLR0913` 误判为没在干活而标记 RUF100。但在完整配置里这些 noqa 是有效的。因此 1020 这个数字不可信，清债必须始终在完整项目配置下进行。

### 发现 2：F401 不是技术债，是 facade re-export

`market-data-platform` 早期完整 ruff 报 1147 处真实告警，其中 `F401` 1061 处、设计类（PLR0913 等）约 84 处。核对 F401 涉及的 30 个文件，27 个的 docstring 明确声明自己是模块拆分后的 re-export 壳（如 `tushare_a_share.py` 头部写 "thin re-export shell over the split provider submodules"）。这些 `# noqa: F401` 是 facade 文件重新导出拆分符号的标准写法，删除会破坏对外应用程序接口（API）。因此 F401 不应作为债清理。该部分已通过方案 C（per-file-ignores）收口并合并（PR #13）。

### 发现 3：RUF100 --fix 在窄上下文下会误伤有效 noqa

用 `--select RUF100 --fix` 实测会把 43 处有效 `# noqa: PLR0913`、以及 `F403`/`F821` 抑制一并删光，制造 46 个新 lint 错误。在完整配置下跑 `ruff check --fix` 则不会改动任何文件（ruff 判定无真正多余 noqa）。因此绝不能用 `--select RUF100` 单独筛后再修，必须在项目完整配置下操作。

### 修正后的结论

- `market-data-platform` 在完整配置下 ruff 与 format 均已全过，真实 RUF100 债为 0。早期「1020 处幽灵 noqa」「46 处 RUF100」均为窄上下文误报，不应批量清理。
- `F401` 的 1061 处是 facade re-export，已用 per-file-ignores 收口（PR #13），不是债。
- 设计类约 84 处是真实复杂度告警（PLR0913 等被 noqa 有意压制），归 `maintainability-refactor-roadmap.yml` 的设计类拆分，本计划不处理。
- `strategy-pipeline` 的 `F403` 星号导入需逐文件确认是否 facade 再决定，且同样要在完整配置下判定。

### 后续建议

1. 清理 noqa 债的硬性前提：始终在项目的完整 lint 配置下运行 ruff（不加 `--select`、不 `--isolated`），否则 RUF100 会把有效 noqa 误判为多余。
2. facade 类 F401 优先走 `per-file-ignores` 配置级忽略（方案 C 已验证），意图清晰且对 ratchet 友好。
3. 暂停对 F401 的删除企图，避免破坏对外 API。

## facade F401 迁移实测（2026-07-31，refactor/facade-noqa-config 分支）

按上述建议 1，在 `market-data-platform` worktree 把 28 个 facade 文件的逐行 `# noqa: F401` 迁移为文件顶部 `# ruff: noqa: F401` 声明（纯注释改动，import 与 re-export 内容不变，行为等价）。ruff 检查、format 检查、导入冒烟均通过。

### 卡点：quality_baseline ratchet 拦截

push 触发 mdp 的 `full` profile 门禁，前 3 项（uv lock、ruff check、ruff format）通过，第 4 项 `scripts/dev/quality_debt.py --check-baseline --check-ratchet` 失败：

- 报错：`ty: excluded lines increased (44927 > 44903)`，增加 24 行。
- 根因：mdp 的 ty 只检查 `pyproject` 里 `ty.src.include` 列表的 34 个文件，其余 176 个文件全部计入 `excluded_lines`（`total_lines - included_lines`）。facade 文件不在 ty include 列表，迁移时给 28 个文件各加 1 行文件级声明（净增约 28 行），这些行全部算进 `excluded_lines`，触发 ratchet 的 excluded-lines 只降不升规则。
- 性质：这是统计口径副作用，不是真实质量退化（facade 文件本就不被 ty 检查，加 lint 声明不影响类型覆盖）。但 ratchet 机制无法区分良性增加与藏债，一律拦截。

### 结论与待办

- facade F401 迁移本身是正确且安全的重构，但 mdp 的 `quality_baseline.json` ratchet 要求 excluded-lines 只能降，良性增加也需 owner 决策重算基线。
- 若要推进此 PR，需在 mdp 分支内重算 `quality_baseline.json`（让 44927 成为新基线），同提交写明这是 facade 注释迁移的统计副作用而非质量退化，再走 owner 决策或 waiver。
- 这同时印证了原盘点判断：mdp 的治理机制对良性重构不够友好，加一行 lint 声明也要动基线。
- 当前状态：分支 `refactor/facade-noqa-config`（commit `f095a38`）留在外部 worktree `/home/richard/code/mdp-facade-worktree`，未推送成功，待决策。mdp 主目录已恢复 `main`，superproject gitlink 未变。

### 升级方案 C：per-file-ignores 绕过 ratchet（已实测通过）

重新评估「优解」后，放弃文件内声明，改用配置级 `per-file-ignores`，在 worktree 内实证：

- 做法：移除 28 个 facade 文件顶部的 `# ruff: noqa: F401`（共删 28 行），改为在 `pyproject.toml` 加 `[tool.ruff.lint.per-file-ignores]` 段，逐文件声明 `["F401"]`。配置写在 `pyproject.toml`，不计入源文件行数。
- 验证：`ruff check src/` 全过（F401 被 per-file-ignores 压住）。`ruff format --check` 全过。`quality_debt.py --check-baseline --check-ratchet` 退出码 0，`ty: excluded lines` 回到 44903（与基线一致，不再有 44927 的回归）。
- 收益：源文件行数零净增，ratchet 不再拦截。意图集中且可读。RUF100 不触及配置级忽略，杜绝误删有效抑制。完全符合最初「优解」意图。
- 注意：`quality_debt.py` 的 debt scan 仍会列出 1061 个 F401（它用 `--select F` 全量计数作债存量报告），但这只是信息性输出，不影响 ratchet 判定。
- 当前状态：方案 C 已提交为 worktree 分支新 commit `1a4b36d`（分支仍名 `refactor/facade-noqa-config`，待重命名为 `feat/facade-noqa-per-file-ignores` 以符合推送前缀规则）。下一步走 PR：推送、review、merge、删分支与 worktree，再开新 worktree 探索下一轮优化方向。

## 设计类复杂度（PLR0913）试点结论（2026-07-31）

按用户选定方向 A，在 worktree `feat/plr0913-pilot` 探查 `market-data-platform` 的设计类复杂度债。完整配置下被 `# noqa` 压制的设计类告警只有 `PLR0913`（函数参数过多），共 43 处，分布在 26 个文件，集中在 `providers/` 拆分后的 `_partNN` 文件与 `_mins_*`、`_campaign_*` 等。

对最集中的 `_mins_mirror.py`（5 处 PLR0913）做聚合重构试点分析，结论：

- 这 43 处函数均用 keyword-only 参数显式传递上下文（`options`、`sidecar`、`sidecar_identity`、`sidecar_binding`、`progress`、`trade_date` 等），语义正交。
- 它们是 `tushare_a_share_mins` 单文件拆分为 `_mins_*` 多 submodule 后的遗留：拆分后的函数仍保留原拆分工件的完整上下文签名，属合理的架构复杂度残留，不是代码劣化。
- 消除 PLR0913 需做 context dataclass 聚合（把 7-8 个上下文参降到 1 个对象）。但不同函数的参数组合各异，无统一 context 可复用，需多个 ad-hoc dataclass。且显式 keyword 传参比塞进对象更自解释（Python 之禅：显式优于隐式）。强行聚合会降低可读性、需连锁改 26 文件 43 处调用方，而运行时行为不变。

判定：43 处 PLR0913 为刻意且合理的设计选择，非真正技术债。处理方式改为「登记 intentional，不重构」：

- 保留 `# noqa: PLR0913` 作为有据可查的刻意抑制，不强行消除。
- 本计划不将 PLR0913 纳入重构范围（与 roadmap 的 `max_complexity_hotspots` 预算无关，后者数的是 C901 圈复杂度热点，不数 PLR0913 参数数）。
- 早期「84 处设计类复杂度债」的估计同样来自窄上下文误报，实测仅 43 处 PLR0913。

试点 worktree 已删除，无源码改动。
