# Backend and API Audit

## Existing service

`src/webapp.py` uses Python's `ThreadingHTTPServer`, binds only to localhost
by default, serves static HTML/CSS/JavaScript, and returns JSON for:

- `GET /api/defaults`
- `GET /api/health`
- `GET /api/benchmark/types`
- `GET /api/benchmark/jobs?id=...`
- `POST /api/run`
- `POST /api/benchmark/run`

`run_application_workflow` validates selected fields, calls
`prepare_portfolio`, executes the existing QAOA runner, and passes the
transpiled metrics to the simulated-profile analyzer. Benchmark jobs execute
in daemon threads and update in-memory status and results under a lock.

## Findings

### B-01 - Main portfolio request has no job lifecycle or execution deadline

- **File / lines:** `src/webapp.py:81-169, 308-331`.
- **Evidence:** `/api/run` invokes the entire workflow before returning HTTP
  200. No timeout or cancellation parameter is passed to the QAOA runner.
- **Expected:** An expensive run should be submitted as a job, expose genuine
  status, and have a configured resource/time bound.
- **Actual:** The request thread remains occupied until classical exhaustive
  enumeration, QUBO checking, COBYLA and final simulation finish.
- **Severity:** High.
- **Recommended:** Introduce a persistent job service incrementally and
  preserve the existing workflow as its execution function.

### B-02 - Error mapping does not cover all runtime failures

- **File / lines:** `src/webapp.py:308-331`.
- **Evidence:** The POST handler maps `ValueError`/`TypeError`/JSON decode
  failures to 400 and `RuntimeError` to 422, but does not define a structured
  response for other unexpected numerical, simulator, serialization, or
  operating-system exceptions.
- **Expected:** Invalid input, failed execution, and unexpected server
  failures should be distinguishable and logged without returning
  success-shaped data.
- **Actual:** Unhandled exceptions fall through to the base HTTP handler's
  error behavior rather than a documented JSON error contract.
- **Severity:** Medium.
- **Recommended:** Add a centralized error response boundary with request/job
  IDs and explicit logging; do not silently substitute fallback results.

### B-03 - Benchmark job state is transient and lacks lifecycle controls

- **File / lines:** `src/webapp.py:26-27, 171-238`.
- **Evidence:** `_BENCHMARK_JOBS` is a process-local dictionary. The worker
  offers queued/running/completed/failed, but no cancellation, deadlines,
  retention policy, or persistence.
- **Expected:** Job state should survive restart and represent terminal
  failures/cancellation accurately.
- **Actual:** Restart loses jobs; a selected 60-case suite can run to
  completion without cancellation or time bound.
- **Severity:** High.
- **Recommended:** Persist job and experiment records, add bounded worker
  execution and cancellation where practical, and test every transition.

### B-04 - API does not expose comparison, history, or research surfaces

- **File / lines:** `src/webapp.py:276-335`.
- **Evidence:** Only the six routes listed above are implemented.
- **Expected:** The UI should be able to request experiment history,
  comparisons, circuit/hardware details, AI context, report generation and
  export from the Python source of truth.
- **Actual:** These endpoints do not exist; the research report is static
  markup, and there is no result database.
- **Severity:** Medium.
- **Recommended:** Add typed API contracts one domain at a time; make
  persistence and experiment identifiers prerequisites for history and
  comparison endpoints.

### B-05 - Request validation does not bound portfolio size or exact work

- **File / lines:** `src/webapp.py:81-105, 308-320`;
  `src/portfolio_workflow.py:54-84, 123-168`.
- **Evidence:** JSON body size is capped at 1 MB, but no maximum asset count
  or exact-enumeration budget is enforced before calling exponential
  algorithms.
- **Expected:** The service should reject or route work that exceeds a
  documented computational budget.
- **Actual:** A small body can describe a large portfolio that causes
  excessive work.
- **Severity:** High.
- **Recommended:** Validate combinatorial and simulator resource estimates
  before enqueueing work and return a clear 400/422 response.

## Current strengths to preserve

- Localhost-only binding is explicit (`main`, lines 337-359).
- The request body is capped at 1 MB (`do_POST`, lines 314-315).
- JSON responses reject NaN/Infinity (`_send_json`, line 251).
- Benchmark failures are logged and surfaced with a failed status and error
  text (lines 221-225).
- Portfolio and benchmark requests use existing shared Python workflows; the
  browser does not recompute the objective.

## Post-implementation status

The findings above describe the audit baseline and are superseded in part by
the current implementation:

- Added `POST /api/experiments/run`, `GET /api/experiments`,
  `GET /api/experiments/{id}`, `GET /api/experiment/options`,
  `GET /api/assistant/status`, and
  `POST /api/assistant/ask`.
- Experiment Studio requests validate supported asset counts/cardinality,
  algorithms, parameters, and the exact-candidate budget before work starts.
  One Studio job per process is admitted at a time; it runs in a background
  thread and returns a persisted ID/status.
- `ExperimentStore` persists Studio specifications, generated dataset IDs,
  results, and queued/running/completed/failed status in SQLite. A saved
  three-asset Studio record is present in `results/experiments.sqlite3`.
- The assistant status route exposes configuration without returning the
  API key. The ask route requires explicit data-sharing consent, resolves only
  a completed saved record, and reports missing provider/record states
  explicitly. A local mock-compatible endpoint verified transport.

The legacy `/api/benchmark/*` route remains process-memory-only and has no
cancellation or deadline. Studio jobs likewise currently have no cancellation,
hard deadline, retry, or cross-process admission control. The original
synchronous `/api/run` path remains for the four-asset Portfolio Lab. These
are residual limits; persistence and the new experiment routes do not imply
that every existing job surface is durable.
