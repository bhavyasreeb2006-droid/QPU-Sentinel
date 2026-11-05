# Incremental Implementation Roadmap

This roadmap preserves the current notebook, QAOA module, saved results, and
submission mirror. It follows the requested phase order. No source changes
were made as part of the current audit.

## Milestone 0 - Audit (complete)

- Inspected Python, static frontend, API, tests, notebook, docs, results,
  presentation, and submission mirror.
- Ran `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`:
  **15 passed**.
- Independently verified all 16 default-instance QUBO energies and covariance
  eigenvalues.
- Recorded findings in this folder.

## Milestone 1 - Mathematical and QAOA validation (in progress)

Priority files:

- `src/portfolio_workflow.py`
- `src/qaoa_portfolio.py`
- `tests/test_portfolio_workflow.py`
- `tests/test_benchmark_workflow.py`

Penalty diagnostics and their conservative-bound explanation are implemented;
the default penalty is certified and an uncertified value is surfaced to the
API/UI without being silently changed. The full suite now has **16 passing
tests**. Still needed: bounded exact/proof paths, direct helper input
validation, bit-order tests, and odd/even/multiple-cardinality fixtures. Keep
current default result assertions. Do not change the mathematical objective
without documenting and testing the derivation.

## Milestone 2 - Experiment records and jobs

Priority files:

- `src/benchmark_workflow.py`
- `src/webapp.py`
- new `src/experiment_store.py` (only after choosing a minimal schema)
- `tests/test_benchmark_workflow.py`
- new focused persistence/API tests
- `requirements.txt` only if a chosen test/runtime dependency is genuinely
  required (prefer stdlib `sqlite3` initially)

Persist dataset + full parameters + raw results + lifecycle state. Add
configurable exact work limits and timeouts. Keep the current deterministic
60-case catalog as a preset, not completed data.

## Milestone 3 - Fair classical comparisons and hardware details

Priority files:

- `src/benchmark_workflow.py`
- `src/portfolio_workflow.py`
- `src/qaoa_portfolio.py`
- `src/hardware_suitability.py`
- relevant tests and `ARCHITECTURE.md`/`RESULTS.md`

Implement a shared experiment contract and only display algorithms proven
implemented. Add greedy/random feasible baselines first; assess simulated
annealing dependencies separately. Extend circuit metrics from actual
transpilation. Keep real-provider execution opt-in and separate from Aer and
illustrative profiles.

## Milestone 4 - Frontend expansion and API integration

Priority files:

- `src/static/index.html`
- `src/static/app.js`
- `src/static/styles.css`
- `src/webapp.py`
- browser/API tests

Expand the existing application (do not create a detached demo), starting
with run status/history and a dynamic asset/matrix editor. Then add experiment
building, matched algorithm comparisons, circuit detail selection, report
export, and the requested overview/settings workspaces. Maintain the current
brand palette and preserve all current tabs.

## Milestone 5 - AI (after persisted context is real)

Priority files:

- new `src/ai_service.py`
- `src/webapp.py`
- `src/static/` assets
- tests for missing provider, failures, context grounding
- `requirements.txt` only after a provider SDK is selected

Use environment configuration and explicit provider state. Never simulate
results or expose credentials.

## Milestone 6 - Documentation, submission and competition preparation

Update root documentation, add the requested mathematics/methodology/API/demo/
judge materials, regenerate notebook outputs only when intentionally rerun,
and synchronize `submission/` after each verified feature. Run the existing
suite plus targeted new tests. Keep results and claims tied to actual saved
measurements.

## Checkpoint requirement

No Git executable or repository metadata is present in the workspace. Before
substantial source changes, make a narrowly scoped backup of files to be
modified or obtain approval to restore Git metadata/tooling. Never replace
the project or bulk-copy new code over the submission mirror without
reviewing the diff.

## Current checkpoint

The statuses above are the original audit-time plan. The requested core
implementation has since been completed in-place:

- **Mathematics/QAOA:** Independent default-instance QUBO verification remains
  16/16; the same QAOA module is used by the notebook, existing Portfolio Lab,
  and new Experiment Studio.
- **Engine/comparison:** Implemented for 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, and
  20 assets; supports valid cardinalities, exact search under a candidate
  limit, greedy/random/annealing/QAOA methods, matched seeds and repeated-run
  metrics. QUBO verification is explicitly exhaustive only through 12 assets.
- **Persistence/API:** SQLite-backed Studio job/results and history routes
  are implemented. The legacy 60-case benchmark job store remains in-memory.
- **Frontend:** Eight workspaces are connected to the Python API and retain
  the requested palette. The Experiment Studio flow was exercised in a
  browser and created the saved record documented in `RESULTS.md`.
- **Assistant:** Implemented as an opt-in OpenAI-compatible provider with
  consent, selected-record grounding, unconfigured/error states, and a local
  mock-provider HTTP test. No external provider has been used.
- **Documentation:** Root README, architecture, results, competition
  walkthrough, and audit reports now describe the implementation and its
  limits.

Remaining work/limitations are not hidden: browser automation coverage is
absent; Studio lacks cancellation, hard deadlines, retries, and
cross-process admission control; the legacy Benchmark Lab remains a distinct
in-memory workflow; QAOA is local Aer with an unconstrained mixer; hardware
profiles are fictional; live AI-provider behavior is unverified. Validation
completed: the root and self-contained submission test suites each pass all
33 tests; `compileall` succeeds; Pylance reports no root-source diagnostics;
browser checks confirmed the eight-workspace UI, saved-history loading, and
the assistant's unconfigured state. The 27-file source/test/document/presentation/
notebook/database mirror check found only the intentional README difference
(the submission README links to `DEMO_GUIDE.md`). The notebook and database
copies are byte-identical.
