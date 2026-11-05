# Competition Status

## Release assessment

**Conditionally ready for a controlled local simulator demonstration.** The
active application on port 8000 passed health checks, all eight workspaces
rendered, Run History displayed all three persisted records, and a Portfolio
Lab run returned the expected four-asset result. The browser automation
environment did not deliver native pointer clicks, so an operator should
confirm a manual tab click and Run Experiment click before the live demo. The
application is not a hardware demonstration, and its optional AI provider is
unconfigured.

## Verified deliverables and application

- Root and submission notebook copies are byte-identical with SHA-256
  `c061e4fc1142be553386e54c09312d36ddd792fafb7d2a7f5326f189bb07b2e8`.
  Neither was modified for this release.
- The QAOA path is implemented in Python source and is used by the local
  application; the feature is not notebook-only.
- All eight workspace handlers were exercised on the current service using
  browser-dispatched click events:
  Portfolio Lab, Benchmark Lab, Experiment Studio, Run History, Research
  Assistant, Circuit Explorer, Hardware Analysis, and Research Report.
- `/api/health`, `/api/assistant/status`, `/api/experiment/options`, and
  `/api/experiments?limit=10` returned HTTP 200. Assistant status reported
  `configured: false`.
- A browser Portfolio Lab run returned HTTP 200 and rendered its results.
  The run was not added to Experiment Studio history; the history remained at
  three records.
- Hardware candidates are labelled `SIMULATED PROFILE` / illustrative.
  They are fabricated scoring inputs, not actual backend records.

## Experiment evidence

All records are local Aer results. Exact references enumerate feasible
portfolios, not necessarily every bitstring. For the 20-asset result, the
saved run's QUBO verification is non-exhaustive; a separate release audit
evaluated all 1,048,576 binary configurations.

| Case | Exact reference | QAOA settings and measured result | QUBO coverage and circuit |
|---|---|---|---|
| Notebook, 4 assets, K=2 | All 6 feasible portfolios; optimum `0110`, objective `-0.093` | p=2; optimizer/final shots 1,024/8,192; seed 42; 39 evaluations. Feasible 7,068/8,192 (86.2793%); optimum 1,189/8,192 (14.5142%); best feasible `0110`, `-0.093` | Exhaustive 16/16 bitstrings; transpiled depth 15, 12 two-qubit gates |
| Record `97bca51ef07e49018452e44b90de6ccc`, 3 assets, K=2 | All 3 feasible portfolios; optimum `101`, objective `-0.2026331093` | Independent covariance, instance seed 2026; p=1; optimizer/final shots 128/512; max 12 iterations. QAOA seeds 3035/4044/5053. Feasibility 80.46875%/2.734375%/4.6875%; optimum frequency 27.5391%/0.78125%/1.171875%. Best feasible selection was exact in all three runs | Exhaustive 8/8 bitstrings; depth 7, 3 two-qubit gates per run |
| Record `214e1db019c8481497ca72702bd568f3`, 3 assets, K=2 | All 3 feasible portfolios; optimum `110`, objective `-0.2197078076` | Mixed covariance, instance seed 2026; p=1; optimizer/final shots 32/128; max 4 iterations; run seed 3035. Feasible 82/128 (64.0625%); optimum 23/128 (17.96875%); best feasible `110` | Exhaustive 8/8 bitstrings; depth 7, 3 two-qubit gates |
| Record `d178d82070f443a6af789b157a4b1bd0`, 20 assets, K=10 | All C(20,10)=184,756 feasible portfolios; optimum `01100110011010001110`, objective `-1.2728654566` | Mixed covariance, instance seed 2030; p=1; optimizer/final shots 64/64; max 4 iterations; run seed 3039. Feasible 2/64 (3.125%); exact optimum sampled 0 times; best feasible `10100100011010101101`, objective `-1.0114589901`; gap `0.2614064664` | Saved check sampled 512/1,048,576; separate release audit exhaustive 1,048,576/1,048,576 with max identity error `2.984e-13`; depth 41, 190 two-qubit gates |

### 20-asset feasibility and penalty

The 3.125% result is 2 feasible samples out of 64, where feasibility is
exactly Hamming weight K=10 after converting Qiskit count keys into the
application's asset order. The count ordering and feasibility calculation
were checked; 2 of the 64 measured samples have weight 10. This low rate is a
measured outcome of a shallow, low-shot p=1 QAOA run with an unconstrained
mixer, not evidence that feasibility is guaranteed.

The exhaustive release QUBO comparison found no objective/penalty identity
error beyond floating-point tolerance. On this instance, the lowest
infeasible penalized energy was `-0.365742`, above the exact feasible
minimum `-1.2728654566`, so penalty 1.0 is sufficient for this instance.
The engine's conservative sufficient-penalty certificate does not pass
(threshold `2.107047`); that is an absence of a general certificate, not a
contradiction of the direct exhaustive check for this particular input.

### Database reconciliation and reproducibility

Root and submission databases now contain the same three experiment IDs
listed above and pass SQLite `integrity_check`. Before reconciliation,
verified SQLite backups were created at
`results/release-backups/experiments.sqlite3.before-release-20261105.sqlite3`
and
`submission/results/release-backups/experiments.sqlite3.before-release-20261105.sqlite3`.

The two historical three-asset records had no generation-version field. Their
stored arrays were verified against `synthetic-portfolio-v1`; the records
were updated with that version and their dataset IDs recomputed. The old IDs
are retained as `legacy_dataset_id`. Experiment IDs, configurations, and
measured result data were preserved. Deterministic replay of the saved
three- and twenty-asset specifications reproduced their recorded IDs,
references, QAOA counts, and metrics.

The notebook's four-asset measurements are a separate saved notebook run,
not an Experiment Studio database record. The browser Portfolio Lab check is
also separate and is not included in the persisted-record table.

## Quality assurance actually performed

- Root tests: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` —
  33 passed.
- Submission tests (from `submission`):
  `..\.venv\Scripts\python.exe -m unittest discover -s tests -v` — 33 passed.
- Compilation: `.\.venv\Scripts\python.exe -m compileall -q src tests` —
  passed.
- Browser smoke checks used the current port-8000 service. Navigation,
  results, history, assistant status, and illustrative hardware labels were
  inspected. The Portfolio Lab event handler issued a successful run request
  and rendered results. Native pointer-click actions in the browser
  automation did not reach the page (the instrumented click listener did not
  fire); perform a manual pointer check before presenting. The assistant is
  unconfigured; no hosted provider request was made.
- Test coverage includes local Aer, temporary SQLite, local HTTP API, and a
  mocked assistant-provider response. It does not certify external AI
  provider behavior, a physical QPU, or real hardware profiles.

## Outstanding limitations

- No quantum hardware was accessed; there is no speedup or quantum-advantage
  evidence.
- The 20-asset QAOA result has low measured feasibility and misses the exact
  optimum. Its saved QUBO verification is sampled, despite the separate
  exhaustive release audit.
- AI-provider credentials and a live hosted-provider path were not verified.
- Hardware suitability data is fictional and illustrative.
- Benchmark Lab recipes are on demand; they are not a completed benchmark
  suite. Do not claim they have all been run.
