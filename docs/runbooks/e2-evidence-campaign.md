# E2 Evidence Campaign

E2 is a production-readiness audit for a selected strategy candidate. It is not a strategy definition and it does not turn a diagnostic run into a promotion decision.

The 2026-08-28 campaign status is recorded in `docs/evidence/e2-execution-evidence-20260828.json`. It references the local diagnostic run `a_share_e2_promotion_candidate_20260825_20260826_001524_ab70c882` and records its observed metrics and limitations.

The run is intentionally marked `diagnostic`. Its outputs are under ignored local artifacts, A-share lot, T+1, price-limit, and listing-status rules were inactive, and broker execution was disabled. These facts prevent a canonical promotion receipt.

Before promotion review, rerun the selected candidate with durable hashed inputs and outputs, enable the approved market rules, materialize `strategy_promotion_evidence.v2`, and validate every declared lineage path. A failed or incomplete dimension must remain visible in `limitations`.
