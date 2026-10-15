# ScoreSync Test Strategy

## Scope
In scope: normalization logic, ingestion pipeline, REST API, scheduled jobs, demo page.
Out of scope: correctness of third-party data (TMDB, OMDb, RAWG, OpenCritic, Steam).

## Risks
| Risk | Likelihood | Impact | How we catch it | Found in development? |
| --- | --- | --- | --- | --- |
| Source changes its response format | High | High | Contract tests on recorded fixtures; nightly live contract check | — |
| Score mis-scaled (7.8 stored as 7.8, not 78) | Medium | High | Boundary tests, Hypothesis properties, range data check | — |
| Scores silently empty, no error raised | Medium | High | Integration test saving through the pipeline and asserting scores exist | Yes: duplicate enum classes |
| Failure only when jobs run concurrently | Medium | Medium | Integration test with two concurrent sessions | Yes: genre insert race |
| One optional source failing drops whole titles | Medium | Medium | Unit test with a stubbed failing client | Yes: OpenCritic 429 |
| Small samples dominate rankings | Medium | Medium | Unit test on the Bayesian average | Yes: 100% user score topped chart |
| Ranking rule empties a category | Low | Medium | Data check: every medium has ranked titles | Yes: empty TV leaderboard |
| Security control fails open silently | Low | High | Smoke test: 61 requests expect a 429 | Yes: slowapi limited nothing |
| Secrets leak into logs | Medium | High | Log review; keys never in INFO-level URLs | Yes: httpx logged API keys |
| API returns 500 on unexpected input | Medium | Medium | Schemathesis fuzzing | — |
| Injection through upstream titles | Low | High | Playwright XSS test on demo page | — |

## Test levels
- Unit: pure logic, no I/O (tests/unit/)
- Contract: recorded upstream responses (tests/contract/)
- Integration: real MySQL and Redis (tests/integration/)
- End-to-end: Playwright on the demo page (tests/e2e/)
- Smoke: read-only checks against production (tests/smoke/)

## Environments
Local: Testcontainers. CI: GitHub Actions service containers. Production: smoke tests only.

## Entry and exit criteria
A PR merges only when lint, type checks, and all PR-level tests pass, and branch coverage on app/ is at least 85%.

## Defect workflow
Severity S1–S4 (impact), priority P1–P3 (urgency). Every fixed bug gets a regression test that names its issue.
