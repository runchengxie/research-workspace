# Architecture as Code

本工作区把架构约束分成可执行的源，并用 `scripts/workspace_architecture.py` 生成统一视图。统一视图直接来自治理和运行所使用的事实，手工架构图只作为辅助阅读材料。

## 权威来源

- `docs/architecture-model.yml`：组件身份、仓库路径、架构 plane、Python package/source roots。
- `scripts/import_boundary_rules.yml`：禁止的跨仓 Python import 方向。
- `docs/artifact-contracts.yml`：跨仓 artifact owner、producer、consumer 和 schema。
- Git submodule gitlink：workspace 模式下子仓库的源码组合版本。
- superproject `HEAD`：`research-contracts` 这类根仓 Git subdirectory package 的 workspace 版本。
- 各子仓 `pyproject.toml` 的 `[tool.uv.sources]`：子仓 standalone 模式的 Git pin。

`architecture-model.yml` 刻意不复制 artifact schema 或 forbidden import 规则，避免出现多份互相校验的“唯一真相”。

## 四张图

运行：

```bash
python scripts/workspace_architecture.py --out-dir /tmp/research-workspace-architecture
```

会生成：

- `import_graph.json`：组件之间实际出现的 first-party Python import。
- `call_graph.json`：通过显式 imported symbol/module alias 能静态解析到的直接调用。该图标记为 `conservative-static`，不声称覆盖反射、动态 dispatch、subprocess 或 monkeypatch。
- `artifact_graph.json`：producer -> artifact -> consumer 的文件/数据交接图。
- `version_graph.json`：workspace gitlink / root `HEAD` 与各 repo standalone Git pin 的版本图。
- `report.md`：错误、warning 和图规模摘要。

## 检查模式

```bash
python scripts/workspace_architecture.py --check
```

以下情况返回非零：

- 架构 registry 重复 component/package ownership；
- artifact manifest 引用了未知的 component；
- Python 源文件存在 syntax error；
- runtime component import graph 出现环；
- import-boundary rule 的 repo 没被 component registry 覆盖。

以下情况只报告 warning：

- source snapshot 没有初始化某个 submodule source root；
- source archive 没有 `.git`，因此无法读取 workspace revision；
- 子仓 standalone Git pin 与对应 workspace gitlink 或 root `HEAD` 不同。

最后一项目前故意不作为失败条件。workspace composition 和 repo-local pin 服务于两种不同的可复现模式；在正式统一 resolution policy 之前，把差异先变成可见证据，比擅自重写 lockfile 更安全。

## 质量门

现有 architecture profile 会依次运行：

```text
workspace-import-boundaries
workspace-ownership-boundaries
workspace-architecture
```

完整 hard profile 也包含这三项。现有 AST boundary checker 仍负责精确的 forbidden-import budget；combined scanner 负责跨 import/artifact/version 来源的结构一致性。

## 阅读原则

单独一张图都不是完整系统：

- Import Graph 说明代码怎么耦合。
- Call Graph 说明静态可见的直接调用怎么走。
- Artifact Graph 说明不经过 import 的数据依赖怎么走。
- Version Graph 说明 workspace 和 standalone 环境到底可能运行哪一版代码。

分析跨仓问题时，应同时查看四者，而不是把“没有 Python import”误解成“没有依赖”。
