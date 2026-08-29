# StyleReplica legacy workspace smoke test

The former `tests/test_style_replica.py` was a pre-owner-boundary integration
test. It imported the removed `alpha_research.style_replica` portfolio surface
(`StyleReplicaPortfolioConfig`, theme quotas, and position construction), so it
could no longer run after StyleReplica was split across its owner repositories.

Coverage is now maintained by the owner-native tests:

- `alpha-research/tests/test_style_replica_signal_generator.py` covers signal
  generation and factor behavior.
- `strategy-pipeline/tests/test_style_replica_output_ownership.py` covers the
  pipeline output boundary.
- `portfolio-backtester` owns portfolio construction and execution behavior.

The legacy test is intentionally removed from the active workspace suite; the
current APIs must not be regressed merely to preserve this obsolete import
surface.
