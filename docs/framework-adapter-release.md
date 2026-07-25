# 外部框架适配器候选发布

> status: superseded
> owner: workspace
> last_verified: 2026-07-19
> source_of_truth: `framework-adapter-release.yml`
> current_status: [外部框架支持矩阵](framework-support-matrix.md)

`framework-adapters-2026-07` 是一批已经终止的历史候选。相关改动后来合入不同的堆叠式开发分支，但候选实现没有共同形成当前职责仓原生 `main` 上可验证的发布组合。当前子模块指针也已正常前进到后续提交。

清单继续保存当时的分支、候选提交和合并前快照，用于解释历史。它不再承担当前功能声明，也不要求工作区回退到旧基线提交。

## 当前处理方式

- `scripts/framework_adapter_release_gate.py` 会校验历史清单结构，并把该批次报告为 `superseded`
- 严格模式不再阻止正常的工作区检查
- 当前能力以 [外部框架支持矩阵](framework-support-matrix.md) 为准
- 新的适配器发布需要创建新的发布标识、当前职责仓原生候选提交和真实运行时证据

运行历史清单检查：

```bash
python scripts/framework_adapter_release_gate.py --strict
```

## 重新启动适配器发布时

1. 在负责仓库的当前 `main` 上建立职责仓原生实现。
2. 记录可选依赖、无框架导入测试和真实运行时测试。
3. 生成框架中立的差分或恢复证据。
4. 先把负责仓库提交推入 `main`，再更新工作区 Git 子模块指针（gitlink）。
5. 运行原生路径和适配器路径的组合检查。
6. 把证据文件、安全哈希算法（SHA-256）和回滚方法写入新的发布清单。

旧批次没有生成 `docs/evidence/framework-adapters/framework-adapters-2026-07.json`。测试中的合成回执（receipt）只验证 schema 和 gate 行为，不构成 Qlib、LEAN 或 vn.py 的运行时证据。

## 回退原则

适配器验证失败时，继续使用最近一次已验证的原生组合并保留失败证据。既有产物（artifact）schema、执行日志和幂等键不得静默改写。
