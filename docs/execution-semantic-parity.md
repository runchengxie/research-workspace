# 执行语义一致性

`tests/fixtures/execution_parity_cases.json` is a comparison-only fixture. It records the expected normalized result for semantics that must agree between `portfolio-backtester` research simulation and `quant-execution-engine` execution planning.

The fixture currently covers target quantities, A-share lot rounding, T+1 sell blocking, delayed fills, unfilled quantity, and cash movement. It does not create a runtime import between the two repositories and it does not replace either repository's native tests.

执行规则发生变化时，应同时更新两个系统的快照，并复核产生的语义差异。只有在相同输入下由两个原生运行时共同生成后，测试案例才能作为生产就绪证据。
