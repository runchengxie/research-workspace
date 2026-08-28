# Execution Semantic Parity

`tests/fixtures/execution_parity_cases.json` is a comparison-only fixture. It records the expected normalized result for semantics that must agree between `portfolio-backtester` research simulation and `quant-execution-engine` execution planning.

The fixture currently covers target quantities, A-share lot rounding, T+1 sell blocking, delayed fills, unfilled quantity, and cash movement. It does not create a runtime import between the two repositories and it does not replace either repository's native tests.

When an execution rule changes, update the two system snapshots together and review the resulting semantic delta. A case is not evidence of production readiness until it has been generated from both native runtimes against the same input.
