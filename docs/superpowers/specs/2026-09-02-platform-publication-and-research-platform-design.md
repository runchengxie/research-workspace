# Research Platform Publication and Integration Design

## Context

`research-workspace`, `market-intel`, and `trading-research-dashboard` form one logical investment-research platform but have different lifecycle and deployment constraints:

- `research-workspace` owns market data, PIT semantics, alpha research, portfolio/backtest evidence, strategy lifecycle, and execution handoff.
- `market-intel` owns market/news context, report assembly, delivery, freshness, idempotency, and operator recovery.
- `trading-research-dashboard` owns the interactive static research UI and must remain deployable from one Vite build to GitHub Pages and Cloudflare Workers Static Assets.

The three repositories remain independent. No new nested superproject or runtime source import is introduced.

## Goal

Create a narrow, versioned publication boundary so research evidence can move from owner repositories to public/static and internal/distribution surfaces without copying research algorithms or making the Dashboard depend on a live research runtime.

## Platform planes

```text
Research plane
research-workspace
  market-data-platform -> alpha-research -> portfolio-backtester
  -> strategy-app -> strategy-pipeline -> execution
          |
          | versioned owner artifacts
          v
Publication projection
research.platform-publication.v1
          |
          +-----------------------+
          |                       |
          v                       v
Intelligence plane          Presentation plane
market-intel                trading-research-dashboard
reports / Feishu            static interactive UI
```

`market-intel` may publish a separate digest projection for the Dashboard, but neither downstream repository may import owner implementation modules from `research-workspace`.

## Publication contract

`research.platform-publication.v1` is a manifest of already-produced projection files. It contains:

- producer repository, commit, run id, and timezone-aware generation time;
- artifact id and versioned schema id;
- safe relative POSIX path;
- SHA-256 content identity;
- media type;
- explicit disclosure audience: `public` or `internal`;
- explicit consumer list.

It intentionally does not contain:

- raw market data;
- model files or private parameters;
- broker/account information;
- third-party framework objects;
- path resolution into sibling repositories;
- research algorithms or helper imports.

Public consumers fail closed if an artifact targeted at them is marked `internal`. Absolute paths, path traversal, duplicate ids, and duplicate paths are invalid.

## Static Dashboard deployment

The Dashboard remains a static consumer:

```text
research-workspace / market-intel
        |
        | publication artifact
        v
Dashboard build workflow
  download -> validate manifest -> verify SHA-256 -> copy approved files
        |
        v
Vite dist/
  |             |
  v             v
GitHub Pages    Cloudflare Workers Static Assets
```

The repository keeps the most recent stable checked-in/demo projection as fallback where appropriate. A deployment may overlay a newer validated publication before the Vite build. Large research outputs remain outside the Dashboard repository; only plot-ready summaries and evidence projections are published.

## Research evidence ownership

Research computations remain in their current owners:

- walk-forward, CPCV, PBO, leakage controls, feature evidence: `alpha-research`;
- PSR/DSR, transaction costs, turnover, capacity, MFE/MAE, execution realism, portfolio evaluation: `portfolio-backtester`;
- claims, counterexamples, invalidation conditions, outcome profiles, lifecycle decisions: `strategy-research`;
- orchestration and publication: `strategy-pipeline` / workspace contracts;
- UI projection and visualization: `trading-research-dashboard`;
- report rendering and delivery: `market-intel`.

Dashboard `research-core` contracts describe presentation projections. Workspace contracts describe research facts and cross-repository handoffs. The Dashboard must not become a second research engine.

## Framework adoption boundaries

### vectorbt

Role: optional experiment/screening backend for parameter surfaces, large technical-rule grids, and fast hypothesis triage.

Not authoritative for A-share execution semantics. Any candidate that survives screening must be rerun through owner research/backtest gates before promotion.

### RQAlpha

Role: planned A-share differential backtest reference for fixed scenarios. Compare fills, positions, cash, fees, turnover, market-rule blocking, and NAV against the native backend.

It is a second opinion, not the platform source of truth.

### Qlib

Existing optional dataset/trainer integration remains. Qlib objects stay inside adapters; PIT semantics, CPCV/PBO, promotion evidence, and cross-repository artifacts remain platform-owned.

### Portfolio optimization libraries

`portfolio-backtester` should expose a framework-neutral optimizer boundary before adding external solvers. Candidate adapters:

- PyPortfolioOpt for conventional constrained mean/variance and Black-Litterman workflows;
- cvxportfolio for cost-aware and multi-period policy research;
- Riskfolio-Lib for research-only comparison of broader risk measures.

RQOptimizer is a domain-design reference for objectives, benchmark-relative constraints, industry/style exposure limits, tracking error, turnover, and transaction-cost penalties. Proprietary RQ objects must not enter public contracts.

### vn.py and NautilusTrader

vn.py remains the preferred China-market execution transport/gateway candidate under `quant-execution-engine` boundaries. NautilusTrader is a design reference for research/live parity and deterministic event semantics. Neither belongs in Dashboard or market-intel runtime.

## Capability roadmap

### 1. Risk model

Add a first-class risk-model contract before broad optimizer expansion:

- factor exposures;
- factor covariance;
- specific risk;
- stock covariance projection;
- as-of/PIT metadata and estimator provenance.

The risk model should be evaluated independently from portfolio optimization.

### 2. Portfolio optimization

Connect expected returns, risk, transaction cost, turnover, benchmark-relative exposure, and portfolio constraints through an explicit optimizer request/result boundary. Existing equal/rank/sleeve/HRP construction remains valid baselines.

### 3. Attribution

Systematize RQPAttr-like decomposition as platform-owned research output:

- benchmark vs active return;
- allocation vs selection where meaningful;
- style/industry/factor vs specific contribution;
- execution and transaction-cost drag;
- active risk contribution.

Dashboard renders attribution; it does not recompute it.

### 4. Factor catalog

Promote factors from loose functions to versioned assets with identity, dependencies, PIT semantics, universe, preprocessing, implementation hash, IC/ICIR, decay, turnover, grouped diagnostics, and lifecycle state. Alphalens Reloaded can serve as a differential tear-sheet reference.

### 5. Research/live drift

Add explicit expected-vs-realized monitoring for paper/live paths:

- feature/signal distribution drift;
- rolling live IC vs research IC;
- turnover and exposure drift;
- expected vs realized slippage;
- conditional-return decay;
- strategy evidence degradation.

Evidently is a design/optional computation reference; canonical decisions remain platform-owned.

### 6. Platform asset graph

Do not create a nested Git superproject. Introduce a logical asset registry instead, inspired by asset-oriented orchestration systems:

```text
market.a_share_daily_clean
  -> features.dailywatch20.v17
  -> model.dailywatch20.v8
  -> signals.dailywatch20.20260902
  -> positions.dailywatch20.20260902
  -> publication.dashboard.20260902
  -> report.morning.20260902
```

Each asset records owner, schema, dependencies, freshness, producer identity, and consumers. Git repository boundaries remain unchanged.

## Non-goals

- no live Dashboard dependency on research-workspace;
- no nested superproject/submodule layer around the three top-level systems;
- no second implementation of PBO, PSR/DSR, attribution, or A-share market rules in Dashboard;
- no automatic strategy score or single synthetic confidence number;
- no direct copying of proprietary Ricequant implementation code;
- no adoption of external frameworks without fixed-scenario differential evidence and rollback instructions.

## Acceptance criteria

1. Workspace exposes and tests `research.platform-publication.v1`.
2. Public/static consumers can reject internal projections and unsafe paths.
3. Dashboard can consume a publication bundle without a live research runtime and preserve Pages/Workers builds.
4. market-intel can consume the same manifest family without importing research implementation code.
5. Framework and new capability ownership are documented before adapters are added.
