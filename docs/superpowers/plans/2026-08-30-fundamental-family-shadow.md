# Fundamental family shadow implementation plan

**Spec:** `docs/superpowers/specs/2026-08-30-fundamental-family-shadow-design.md`

## Global constraints

- No production preset, production feature schema, or automatic promotion state may change.
- Value, Quality, Growth, style controls, and fund context are separate named families.
- Quality and Growth must reuse the existing strict PIT implementation; no duplicate calculation path.
- P0 is the current production feature anchor. T0 is P0 with `value_yield` and `earnings_yield` removed.
- The fixed arms are exactly P0, T0, V, Q, G, VQ, VG, QG, VQG, and VQG_F. VQG_F is auxiliary only.
- The fixed horizons are 5 days diagnostic-only, 20 days primary, and 60 days preregistered challenger.
- All horizon-specific split protection must use the matching label maturity. Historical data through 2026-08-30 is `retrospective_diagnostic`; it is never new OOS.
- Missing, non-positive, non-finite, future-dated, duplicate, or conflicting source data must fail closed or produce a blocked receipt.
- Cross-repository code uses public owner APIs and stable contracts only. Do not import provider-private modules or reopen the closed fund-crowding branch.
- All new research outputs remain `production_eligible=false` and `automatic_promotion_allowed=false`.

## Tasks

### Task 1 — A1 market-data-platform valuation input

Inspect the current public A-share/DailyWatch20 loader. If `ps_ttm` is already exposed, add the missing contract and regression tests without creating a second loader. Otherwise expose it through the existing published-data API. Test missing columns, date bounds, stock/date uniqueness, and compatibility of `pb`/`pe_ttm`. Do not alter production asset semantics.

### Task 2 — A2 alpha-research family contract

Add a public alpha module for family constants and metadata. Implement finite-positive Value yields for PB, PE_TTM, and PS_TTM, preserving existing production yield names. Reuse the canonical PIT Quality/Growth feature constants/builders. Add P0/T0 helpers, exact family membership checks, and immutable 5/20/60 horizon profiles. Add focused tests first and keep the package importable without optional frameworks.

### Task 3 — B strategy-research V/Q/G ablation

Create `experiments/fundamental_family_shadow/` with frozen configuration, exact primary arm matrix excluding fund context, 20-day primary and 5-day diagnostic profiles, common evaluation-key/intersection checks, retrospective evidence classification, and a deterministic runner that consumes public feature frames. Keep model/portfolio calculations delegated to existing public APIs where available. Add tests for frozen arms, same keys, missing family columns, horizon semantics, blocked receipts, and production isolation.

### Task 4 — C slow horizon and fund auxiliary

Extend the experiment with preregistered 60-day configuration and matching purge/embargo. Add VQG_F only as an auxiliary arm. Require explicit fund provenance and `revision_safe=false` classification when a complete vintage ladder is unavailable. Add tests that prevent fund context from becoming a primary or production-eligible arm and prevent historical rows from being labeled new OOS.

### Task 5 — D workspace integration

Update workspace navigation/roadmap/evidence documentation to point to the implemented experiment and its current research-only lifecycle. Record owner commits and verification commands without claiming remote CI. Add or update integration checks for paths, production immutability, and cross-repository boundaries. Do not advance catalog lifecycle or production configuration.

## Verification

- Run each owner repository's focused tests and its documented quality checks where dependencies permit.
- Run the strategy-research full test suite after Tasks 3–4.
- Run workspace doctor, relevant contract/boundary checks, and the workspace tests after Task 5.
- Report any unavailable command or pre-existing failure explicitly.
