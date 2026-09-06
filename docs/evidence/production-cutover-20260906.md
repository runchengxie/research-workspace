# Production cutover and rollback window

> status: active rollback window
> T0: 2026-09-06T19:30:33+08:00
> rollback window closes: 2026-09-20T19:30:33+08:00

## Production pointers

The production promotion completed atomically using the remote `main` commits:

| Surface | Previous release | Active release |
| --- | --- | --- |
| `research-workspace` | `9267bbae5b03c092cc62b59d1d38f8e8158c5b55` | `b58831bcfaead16cdd3cafa08dd28139ba6e696f` |
| `market-intel` | `482cb31b5c1d8ac1681cebd28e96a31d808d12a0` | `89a35d97ca73f2533c74b487d16c785fab80d10e` |

The previous releases remain present and reachable. No legacy repository was
deleted, archived, renamed, or made inaccessible.

## Post-cutover checks

- workspace doctor: zero errors; six existing warnings, all non-blocking;
- contract smoke: zero errors and zero warnings;
- `market-intel` platform publication consumer tests: `5 passed`;
- the real DailyWatch20 publication bundle was re-verified by the active
  `market-intel` release with `allow_internal=True`;
- Hermes morning, evening, and weekly jobs were repointed to the active
  `market-intel` release.

## Rollback policy

During this window, keep both previous release directories, all legacy
repositories, and the production publication bundle unchanged. Roll back by
atomically repointing each affected `current` symlink to the corresponding
previous release and restoring the previous Hermes workdir if the consumer,
freshness, publication, delivery, output-drift, or recovery checks fail.

The window cannot close until two scheduled production cycles have completed,
a rollback rehearsal succeeds from the recorded previous manifests, and an
explicit closure record is approved.
