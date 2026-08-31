# research-workspace：把能跑变成能复现

> status: active
> owner: workspace
> last_verified: 2026-08-31
> source_of_truth: no
> superseded_by: n/a

八个仓库都可以各自通过测试。

系统仍然可能在第九个动作失败：把一个仓库的结果交给下一个仓库。

数据版本可能变了，特征定义可能变了，回测仍在读取旧接口，策略编排导出的目标文件又来自另一组提交。每一段单独看都合理，最后却无法回答一个最简单的问题：这次研究结果，到底由哪一组数据、代码、策略规格和执行契约共同产生。

`research-workspace` 用来固定这个答案。

它把八个独立仓库锁成一组经过约定的版本组合，维护跨仓库契约、质量门禁和文档边界，让一条研究链路可以被检查、复现和继续交给执行层。

## 为什么需要一个顶层工作区

量化系统扩张以后，最先增加的是能力。

数据平台可以发布更多资产，研究仓可以训练更多模型，回测仓可以加入成本和容量，策略应用可以承载更多策略逻辑，执行引擎可以连接更多交易流程。

同时增加的还有另一笔成本：一致性。

一个模型能运行，不代表它读取了正确的数据版本。一个回测能结束，不代表它消费的是当前信号契约。一个 `targets.json` 能被解析，也不代表生成它的研究过程仍然能够复现。

因此这个工作区主要维护四件事：

1. 用 Git submodule 锁定各 owner 仓库的提交版本。
2. 用稳定文件和公开 API 约束跨仓库交接。
3. 用顶层 doctor、契约测试和本地质量门禁检查组合是否仍然成立。
4. 用架构、ADR、版本矩阵和发布文档记录这组组合为什么可以被信任。

它不接管子仓库内部实现。每个 owner 仍然维护自己的代码、依赖、测试和业务参数。

## 八个仓库，只有一条交接链

当前工作区锁定八个 submodule：

```text
strategy-research
  维护策略身份、投资假设、生命周期和证据导航
        ↓
market-data-platform
  发布数据资产和 current 契约
        ↓
deep-learning-tick-data-prediction
  处理 L2 事件流、模型和预测产物
        ↓
alpha-research
  生成特征、模型评估和信号产物
        ↓
portfolio-backtester
  构造组合并评估成本、容量和风险
        ↓
strategy-app
  把策略规格翻译为策略特有的纯计算
        ↓
strategy-pipeline
  编排研究流程并导出 targets.json
        ↓
quant-execution-engine
  解析 targets.json，完成预演、风控、执行和审计
```

这里最重要的对象往往不是某个 Python 类，而是几个很普通的文件。

A 股研究首先要知道当前允许消费哪一版数据：

```text
metadata/current_assets/a_share_current.json
```

研究准备交给执行层时，最终要落到：

```text
targets.json
```

工作区本身再用 gitlink 固定八个仓库的提交。

数据契约、目标文件和提交指针看起来都很小。真正的复现能力就压在这些小对象上。

## 两本账

维护这套系统时，可以同时看两本账。

第一本是能力账。

它记录系统又多了什么：新的数据资产、新的因子、新的模型、新的策略应用、新的组合约束、新的执行适配器。

第二本是一致性账。

它记录每次新增能力以后，是否还能回答下面这些问题：

- 输入数据来自哪个发布版本。
- 当前代码组合由哪些 submodule commit 构成。
- 策略身份、假设和生命周期记录在哪里。
- 信号、组合和目标文件分别由谁生产、谁消费。
- 研究结果交给执行层以后，哪一层还可以修改它。
- 出现异常时，能否从结果回到对应的输入、代码和质量检查记录。

能力账一直增长并不困难。

一致性账如果欠得太久，系统最后会出现一种很昂贵的状态：每个组件都能运行，但没有人敢确认整条链路仍然代表同一次研究。

`research-workspace` 的价值主要体现在第二本账。

## 边界比共享代码更重要

这个工作区刻意减少跨仓库的隐式共享。

研究、回测、策略应用和编排使用各自的权威命名空间：

```text
alpha_research
portfolio_backtester
strategy_app
strategy_pipeline
```

跨仓库协作优先使用稳定文件或公开 API。第三方框架对象不进入跨仓库契约。

这条规则看起来保守，但它降低了一种常见风险：某个内部对象改了字段，六个下游调用仍然能够 import，直到运行到真实数据才一起出问题。人类通常会把这种情况称为灵活，直到凌晨两点开始找谁改了 dataclass。

工作区还明确留下几条硬边界：

- 大型市场数据、研究输出、缓存和交易审计日志留在 Git 仓库之外。
- 凭证只进入对应的私有运行环境。
- 数据平台负责数据发布和数据质量语义，研究仓不能静默改写 eligibility。
- 研究侧可以生成执行目标，不能绕过执行引擎的 dry-run、paper 或 live 安全门禁。
- 策略知识与生命周期由 `strategy-research` 维护，运行时代码通过稳定边界消费需要的信息。

## 为什么使用 submodule

八个 owner 仓库需要独立演进。

如果把所有代码塞进同一个仓库，每次发布会得到一个统一提交，但仓库边界、依赖周期和负责人边界也会被重新耦合。

这里选择另一种方式：每个仓库自己演进，顶层只记录哪一组提交曾经一起工作。

因此顶层提交的意义并不只是改了几行文档。

当 submodule gitlink 发生变化，它实际上在声明一组新的系统组合：

```text
数据平台提交 A
+ L2 研究提交 B
+ alpha 提交 C
+ 回测提交 D
+ 策略研究提交 E
+ 策略应用提交 F
+ 编排提交 G
+ 执行提交 H
= 一组需要重新验证的工作区版本
```

版本矩阵、契约测试和发布检查负责给这条等式留下证据。

## 质量门禁放在哪里

当前工作区把主要质量门禁放在本地 pre-push 流程，而不是远端 GitHub Actions。

常用入口包括：

```bash
python scripts/workspace_doctor.py
python src/research_contracts/smoke_contracts.py
python scripts/run_quality_checks.py --profile hard
python scripts/run_submodule_checks.py --profile smoke
python scripts/run_submodule_checks.py --profile full --dry-run
```

根目录还提供不依赖 Git hook 的统一入口：

```bash
bash scripts/check.sh
```

跨仓库测试使用 `strategy-pipeline` 的环境运行：

```bash
uv run --project strategy-pipeline --extra dev python -m pytest tests -q
```

这些检查的目标不是证明每个子仓库内部实现都完美。子仓库已经有自己的测试。顶层更关心另一件事：这组版本放在一起以后，契约有没有断。

## 当前真正验证到了哪里

工作区当前活跃主线是 A 股数据、研究和执行交接。

已经确认的链路可以从已发布数据资产继续到研究、组合、策略应用和编排，再由 `strategy-pipeline` 导出标准 `targets.json`，最后由 `quant-execution-engine` 解析并生成离线调仓计划。

当前就绪度只确认 `baseline_reproducible`。

完整 PIT 研究数据、长窗口生产策略证据、真实模拟盘持续联调和实盘自动化仍然需要独立验收。一个离线计划能够生成，只证明研究到执行文件交接已经成立。它不会自动把系统升级成可以无人值守下单的生产交易平台。

这个边界故意留得很清楚。

## 第一次进入工作区

新环境先完整拉取 submodule：

```bash
git clone --recurse-submodules https://github.com/runchengxie/research-workspace.git
cd research-workspace
```

然后检查工作区基本状态和核心契约：

```bash
python scripts/workspace_doctor.py
python src/research_contracts/smoke_contracts.py
```

已有本地仓库时同步 submodule：

```bash
git submodule sync --recursive
git submodule update --init --recursive
```

新机器的依赖、环境变量和完整初始化流程见 [bootstrap.md](bootstrap.md)。

想先理解系统怎样流动，继续读 [platform-workflow.md](platform-workflow.md)。

想知道仓库之间为什么这样分工，读 [../ARCHITECTURE.md](../ARCHITECTURE.md)。

想核对当前锁定组合，读 [version-matrix.md](version-matrix.md)。

想修改跨仓库文件格式，先读 [contracts.md](contracts.md) 和对应 ADR，再同时检查生产方、消费方和顶层测试。

## 什么时候应该改这个仓库

下面这些变化属于顶层工作区：

- submodule 版本组合发生变化。
- 跨仓库文件契约发生变化。
- owner 边界、命名空间或端到端交接发生变化。
- 顶层质量检查、版本矩阵或发布流程发生变化。
- 一个新的跨仓库事实需要有唯一文档入口。

单个仓库内部的模型实现、业务参数、依赖和完整测试配置，继续留在对应 owner 仓库。

## 最后留下什么

一次研究运行结束以后，模型进程会退出，回测图会关闭，终端也会被清空。

真正需要留下来的东西很少：

```text
数据版本
策略规格和证据
submodule commit
质量检查结论
targets.json 及其 lineage
```

这些东西足够让下一次运行知道自己接过了什么。

这也是 `research-workspace` 存在的原因。
