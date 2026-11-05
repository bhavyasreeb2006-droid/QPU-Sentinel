# QPU Sentinel Project Audit

## Status and scope

Audit performed against the workspace at `C:\QubitForge` on 2026-11-05.
No application source, tests, notebook, recorded result, or submission file was
modified during this audit. The reports in this folder are the only planned
changes for this milestone.

The root contains a Python 3.12 project, a saved-output Jupyter notebook, a
local browser interface, tests, a presentation, documentation, and a
self-contained `submission/` copy. `src/`, `tests/`, `notebooks/`,
`presentation/`, `submission/`, `README.md`, `ARCHITECTURE.md`, `RESULTS.md`,
and `requirements.txt` were inspected. The empty `research/` and `results/`
directories contain no standalone artifacts. The notebook and `RESULTS.md`
hold the recorded simulator results.

There is no `.git` directory or Git executable in this environment, so no Git
status or commit checkpoint could be obtained. The main implementation and
notebook files checked against `submission/` are byte-identical. Root and
submission `README.md` differ only in the submission README's additional
`DEMO_GUIDE.md` link.

## Current verified behavior

- `src/portfolio_workflow.py` validates portfolio dimensions, finiteness,
  covariance symmetry/PSD, cardinality, and risk-aversion sign; enumerates
  feasible bitstrings; builds the quadratic-penalty QUBO; and checks QUBO
  equivalence over every bitstring.
- `src/qaoa_portfolio.py` creates standard, unconstrained QAOA with a uniform
  Hadamard initial state, `RZ`/`RZZ` cost layers, an `RX` mixer, COBYLA, and
  local Qiskit Aer sampling. Counts are reversed into asset-index order before
  objective evaluation.
- `src/benchmark_workflow.py` declares 60 deterministic synthetic recipes
  (3-6 assets, three covariance structures, five replicates) and executes a
  bounded QAOA configuration when requested.
- `src/hardware_suitability.py` ranks three explicitly fictional profiles
  using visible compatibility rules and scoring weights.
- `src/webapp.py` serves a localhost-only standard-library HTTP application.
  Portfolio requests run synchronously. Benchmark requests use in-process
  background threads and in-memory job state.
- `src/static/` presents Portfolio Lab, Benchmark Lab, Circuit Explorer,
  Hardware Analysis, and a static report of the saved notebook run. The
  charts use the current portfolio API response except the historical report,
  which is deliberately hard-coded to the recorded notebook data.
- The notebook contains saved executions. Its classical enumeration code is
  duplicated in cells 4 and 5.

## Baseline tests

Command:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Result: **15 tests passed** in 1.752 seconds. The tests cover the saved exact
optimum, default-instance QUBO equivalence, selected validation failures,
basic benchmark generation/execution, simulated-profile scoring, and one
small seeded application run.

An exploratory `pytest` invocation did not run because `pytest` is not
installed. This is not the documented runner; the documented `unittest`
command completed successfully.

## Findings

### A-01 - Unbounded exponential work on the synchronous portfolio route

- **File / lines:** `src/portfolio_workflow.py:54-84, 123-168`;
  `src/webapp.py:81-120, 308-330`.
- **Evidence:** Exact portfolio enumeration iterates over all `2^N` bitstrings.
  `prepare_portfolio` unconditionally invokes exhaustive QUBO verification,
  also over `2^N`. The `/api/run` handler executes the whole workflow before
  returning its response. The HTTP handler has no asset-count or combination
  limit.
- **Expected:** User-controlled requests should have explicit computational
  bounds and expensive jobs should not block the request thread; exact
  verification should remain limited to tractable instances.
- **Actual:** A valid, large input can cause unbounded CPU/memory/time growth
  before QAOA starts. UI limits constrain QAOA parameters but not `N`.
- **Severity:** High (availability/reliability and core scalability).
- **Recommended:** Use a configurable exact-search combination budget and
  verification-size limit; use a documented classical method when exact
  search exceeds that budget; validate an upper resource bound before work;
  make expensive portfolio runs jobs with timeout/status semantics.

### A-02 - Penalty guarantee needs a conservative-bound interpretation

- **File / lines:** `src/portfolio_workflow.py:85-120`; default penalty at
  `src/webapp.py:37-43`.
- **Evidence at audit baseline:** `build_qubo` checked only that the penalty
  was finite and positive; it did not compare the penalty with
  feasible/infeasible objective bounds.
- **Expected:** The unconstrained QUBO minimum should represent a feasible
  cardinality-constrained optimum, or the system should explicitly report that
  this is not guaranteed.
- **Actual at audit baseline:** A positive but too-small penalty could make an
  infeasible selection the QUBO ground state. Exhaustive identity verification
  proved the algebraic penalty encoding, not penalty strength.
- **Severity:** High (scientific correctness of the optimization result).
- **Recommended:** Keep penalty diagnostics visible and distinguish a
  conservative certificate from an exact penalty-strength determination.

**Post-audit status:** Partially addressed in
`src/portfolio_workflow.py`. The workflow reports a conservative sufficient-
penalty certificate based on a lower bound for the objective, and the
application warns when the selected value is not certified. It does not
silently alter the requested value. A failed certificate means "not
certified", not proof that the value is inadequate.

### A-03 - Experiment suite results are not persistent

- **File / lines:** `src/webapp.py:26-27, 193-238`; `src/benchmark_workflow.py:79-126`.
- **Evidence:** Jobs/results live only in `_BENCHMARK_JOBS`; there is no
  database or result-file writer. `results/` is empty.
- **Expected:** Completed, failed, and cancelled experiments should remain
  inspectable and reproducible after process restart.
- **Actual:** A restart loses job history and all benchmark measurements; only
  the saved notebook reference run persists in the repository.
- **Severity:** High (reproducibility and requested experiment history).
- **Recommended:** Add a versioned experiment schema and transactional SQLite
  persistence, keeping recipe definitions distinct from executed records.

### A-04 - Benchmark coverage is a recipe catalog, not a comparison engine

- **File / lines:** `src/benchmark_workflow.py:17-34, 52-77, 79-126`.
- **Evidence:** The fixed catalog supports only N=3..6, a single
  `max(1, N//2)` cardinality, one QAOA configuration, and one seed per
  replicate. The returned row omits dataset ID/data, full parameters, raw
  sample counts, best bitstring, optimizer evaluation count, and failure
  metadata.
- **Expected:** Benchmark records should identify the exact problem, all
  settings and measured outputs, and support fair multi-algorithm/repeat
  comparisons.
- **Actual:** Current rows measure a narrow single-algorithm recipe and do not
  support the study across cardinality, algorithm, or repeated-seed axes.
- **Severity:** Medium.
- **Recommended:** Generalize specifications around immutable dataset and
  algorithm configuration IDs; preserve raw counts and all run settings;
  expand only behind exact-search and runtime budgets.

### A-05 - API execution/status surfaces are incomplete

- **File / lines:** `src/webapp.py:81-169, 171-238, 276-359`.
- **Evidence:** Implemented APIs are defaults, health, benchmark types,
  benchmark creation/status, and synchronous portfolio run. There are no
  portfolio job/status/history, cancellation, benchmark history/filtering/
  deletion, comparison, circuit, hardware, AI, report, or report-export
  endpoints. The benchmark worker has no cancellation or timeout. `/api/run`
  executes synchronously.
- **Expected:** Long-running runs should have observable state and bounded
  execution; the API should expose the actual research workflow needed by the
  product rather than duplicate calculations in the browser.
- **Actual:** Portfolio runs can hold a request open; jobs are transient;
  several requested surfaces are absent.
- **Severity:** High for scalability; Medium for missing product surfaces.
- **Recommended:** Add typed request/result contracts, persistent job records,
  explicit queued/running/completed/failed/cancelled states, timeouts, and
  endpoints incrementally without replacing the existing HTTP server unless
  requirements justify it.

### A-06 - Frontend is an established but intentionally narrow application

- **File / lines:** `src/static/index.html:19-23, 33-52, 91-162`;
  `src/static/app.js:40-80, 284-342`; `src/static/styles.css:1-195`.
- **Evidence:** There are five tabs. Asset names/returns are rendered from
  defaults, but the UI has no add/remove controls or dynamic covariance
  editor. There is no Overview, Experiment Studio, Algorithm Comparison, AI
  Assistant, or Settings workspace. Circuit gates have no selected-gate detail
  view. The report is a fixed historical snapshot. There is no frontend test
  suite or charting-library dependency.
- **Expected:** The frontend should expose the supported experiment controls
  and show results only from the backend, including empty/loading/error states.
- **Actual:** Existing tabs are useful and data-driven for a current portfolio
  run, but do not cover the planned product scope. The historical report is
  intentionally not live.
- **Severity:** Medium (scope gap, not a defect in the current five tabs).
- **Recommended:** Expand the current static UI in-place and keep scientific
  calculations authoritative in Python; treat each requested workspace as a
  separately validated increment.

### A-07 - Test coverage does not match the research/API claims

- **File / lines:** `tests/test_portfolio_workflow.py:1-108`;
  `tests/test_benchmark_workflow.py:1-50`;
  `tests/test_hardware_suitability.py:1-127`.
- **Evidence:** Fifteen tests cover selected module workflows. There are no
  HTTP-handler, persistence, timeout/cancellation, failure-state, frontend,
  algorithm-comparison, or AI tests. Most portfolio correctness assertions
  exercise the one four-asset fixture.
- **Expected:** New behavior should have automated coverage for mathematical
  boundaries, API contracts, persistence, and job state transitions.
- **Actual:** Baseline passing tests establish the current small-instance
  behavior only; they do not establish the missing product features.
- **Severity:** Medium.
- **Recommended:** Preserve the existing suite and add targeted tests with each
  feature, including odd/even cases, malformed inputs, deterministic seeds,
  and API-level status/error checks.

### A-08 - Notebook has a duplicated classical enumeration cell

- **File / lines:** `notebooks/qpu_sentinel_qaoa.ipynb`, cells 4 and 5
  (40 source lines each; same classical enumeration code).
- **Evidence:** Both cells redefine `portfolio_objective`, enumerate the same
  feasible bitstrings, sort the same results, and display the same benchmark.
- **Expected:** A sequential notebook should have one authoritative
  implementation of each experiment stage.
- **Actual:** The notebook repeats the same stage and can make edits/results
  diverge or confuse readers.
- **Severity:** Low.
- **Recommended:** Remove or repurpose the duplicate only after preserving the
  saved outputs and checking notebook execution order; keep the notebook and
  submission copy synchronized.

### A-09 - Git checkpointing is unavailable in the current environment

- **File / lines:** Workspace root (not a source-code finding).
- **Evidence:** Root inventory has no `.git` directory and the `git` command
  is unavailable.
- **Expected:** A verified checkpoint should precede significant source
  changes.
- **Actual:** Git status/commit cannot be created here.
- **Severity:** Medium (change-management constraint).
- **Recommended:** Before the first substantial source edit, make a narrowly
  scoped backup of only the files being changed, or restore Git tooling/
  repository metadata if the user confirms that is appropriate. Do not create
  a new repository implicitly.

## Files and submission state

The existing Python modules, static assets, notebook, requirements, tests,
architecture, results, and slide deck are present. The corresponding source,
static, and notebook files checked in `submission/` are identical to the
workspace originals. `submission/README.md` alone has an additional link to
its demo guide. No benchmark database or executed 60-case result set is
present; the documented 60 are recipes only.

## Conclusion

The project is a working small-instance Qiskit Aer demonstrator, not yet a
persistent research platform or multi-algorithm benchmark system. The formula,
QUBO conversion, QAOA gates, simulator-only claims, and baseline test status
are supportable. Penalty sufficiency, unbounded exhaustive work, persistence,
and experiment comparability are the highest-priority correctness and
reproducibility gaps. Keep the notebook, saved results, current QAOA module,
and submission mirror intact while addressing them.

## Post-audit implementation update

After freezing the audit baseline, the following files were updated to expose
the penalty guarantee and preserve the warning in benchmark output:

- `src/portfolio_workflow.py`
- `src/webapp.py`
- `src/benchmark_workflow.py`
- `src/static/index.html`
- `src/static/app.js`
- `tests/test_portfolio_workflow.py`
- `tests/test_benchmark_workflow.py`
- `ARCHITECTURE.md`

The regression suite now reports **16 passing tests**. A browser run with
penalty `0.1` displayed the warning and completed with backend results; the
default `1.0` penalty was certified above the conservative strict threshold
`0.347`. Exponential search and exhaustive verification remain unbounded.

## Current implementation status

The preceding audit sections are a historical baseline, not a description of
the current workspace. The requested development has since been implemented
in the Python source and connected frontend:

- `src/experiment_engine.py` runs supported asset counts 3, 4, 5, 6, 7, 8,
  9, 10, 12, 15, and 20 with any valid cardinality. It compares exact,
  greedy, random feasible, simulated annealing, and QAOA methods on the same
  seeded instance and supports repeated runs.
- Exact search enforces a feasible-candidate limit. QUBO verification is
  exhaustive through 12 assets and explicitly non-exhaustive (512 seeded
  checks) above that.
- `src/experiment_store.py` persists specifications, lifecycle state,
  instance and result data in `results/experiments.sqlite3`. One completed
  browser-created three-asset record and a separate 20-asset pilot are
  included.
- `src/webapp.py` exposes Experiment Studio, run history, and assistant
  status/ask routes. The eight-workspace frontend is served from
  `src/static/`.
- `src/research_assistant.py` is an opt-in OpenAI-compatible client grounded
  in one selected completed experiment. A local mock-provider path is tested;
  no hosted provider/key is configured or tested.

The saved four-asset notebook and its outputs remain unchanged. The saved
three-asset Studio result and bounded 20-asset pilot are separately
documented in `RESULTS.md`.

## Workspace-inventory discrepancy

The earlier inspection reported empty `src/` and `tests/` directories because
those directories were empty in that inspection's workspace snapshot; it was
not a claim that source lived only in the notebook. The subsequent workspace
contains Python modules, tests, frontend assets, audit reports, and a
submission mirror. This environment has no `.git` directory or Git executable,
so no revision history is available to identify when or by whom those files
were added. The earlier output cannot be retroactively attributed beyond the
observed empty-directory state.

## Remaining limitations

The older 60-case Benchmark Lab remains a distinct on-demand, in-memory
workflow; it is not the persisted Experiment Studio engine. Studio jobs do
not yet support cancellation, hard deadlines, retries, or cross-process
admission control. Exact search rejects instances over its configured
candidate budget rather than substituting an approximate "optimum." QAOA is
local Aer simulation with an unconstrained mixer. The three hardware profiles
remain fictional, and there is no hardware execution. The research assistant
requires explicit per-request consent and live provider behavior is unverified.

Final validation for this checkpoint: `python -m unittest discover -s tests -v`
passes **33 tests**. `python -m compileall -q src tests` completes successfully.
Workspace Pylance diagnostics found no issues in the root implementation; it
reported only unused-parameter warnings for the local mock HTTP handler's
required logging signature, in both root and mirrored tests. Browser
validation was completed for Experiment Studio, Run History, and the
assistant's unconfigured state; broader automated browser coverage remains
absent.
