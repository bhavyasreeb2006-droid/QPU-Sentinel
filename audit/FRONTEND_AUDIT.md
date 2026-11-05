# Frontend Audit

## Current UI and data flow

The current interface is a custom HTML/CSS/JavaScript application served
directly by `src/webapp.py`; no separate React/Vite build is present or
required by this implementation. The brand palette includes Aqua Jade
`#74FFED`, Midnight Abyss `#171F44`, and Baby Pink `#FEB1D1`, with restrained
navy, white, and blue-gray supporting colors.

Five workspaces are implemented: Portfolio Lab, Benchmark Lab, Circuit
Explorer, Hardware Analysis, and Research Report. `app.js` calls
`/api/defaults`, `/api/run`, `/api/benchmark/run`, `/api/benchmark/jobs`, and
`/api/benchmark/types`. Portfolio charts and circuit/hardware views use the
actual response to a completed backend run. The report tab is a clearly
labelled static copy of the saved notebook measurements.

## Findings

### F-01 - Portfolio editor does not support variable asset count

- **File / lines:** `src/static/index.html:33-35, 40-52`;
  `src/static/app.js:40-50, 67-80`.
- **Evidence:** Asset rows are created only from `/api/defaults`; each has a
  name and expected-return input. There are no add/remove controls and no
  covariance-matrix resize/edit workflow.
- **Expected:** Users should be able to create odd/even instances and
  consistently update assets, returns, and covariance dimensions.
- **Actual:** Existing four assets can be renamed/edited, but asset count
  cannot be changed through the UI.
- **Severity:** Medium.
- **Recommended:** Add/remove controls with synchronized matrix editing and
  backend validation; keep the Python API authoritative.

### F-02 - Required application workspaces are absent

- **File / lines:** `src/static/index.html:19-23, 91-162`.
- **Evidence:** The UI has five tabs and lacks Overview/Command Centre,
  Experiment Studio, Algorithm Comparison, AI Research Assistant, and
  Settings.
- **Expected:** The requested research product should expose those
  capabilities from actual backend endpoints.
- **Actual:** Existing pages provide only portfolio run, fixed benchmark
  recipes, circuit, illustrative hardware, and saved report.
- **Severity:** Medium (planned scope gap).
- **Recommended:** Expand the current application incrementally rather than
  replace it with a disconnected demo.

### F-03 - Circuit explorer is a diagram, not an interactive gate inspector

- **File / lines:** `src/static/app.js:260-341`;
  `src/static/index.html:132-143`.
- **Evidence:** The SVG renders operations and a hover title for single-qubit
  gates, but no selected-operation state, mathematical explanation, or
  purpose panel exists.
- **Expected:** Selecting a gate should explain its operation, qubits, and
  role in QAOA, using the backend's circuit record.
- **Actual:** Operations are drawn from backend data, but interaction is
  limited to hover text and there is no per-gate explanatory view.
- **Severity:** Low.
- **Recommended:** Add an accessible selection/detail view based on circuit
  metadata and gate definitions; do not fabricate gates.

### F-04 - Portfolio run is synchronous from the browser

- **File / lines:** `src/static/app.js:384-406`; `src/webapp.py:308-331`.
- **Evidence:** The frontend waits for a single `/api/run` response; unlike
  Benchmark Lab, no job ID is returned or polled.
- **Expected:** Long experiments should show actual progress and status and
  allow safe handling of long waits.
- **Actual:** The button reports a generic running state until completion;
  no portfolio progress, cancellation, or timeout is available.
- **Severity:** Medium.
- **Recommended:** Adopt an experiment-job endpoint before extending long
  benchmark workloads and make UI status match backend state.

### F-05 - Historical report and exports are limited

- **File / lines:** `src/static/index.html:156-170`;
  `src/static/app.js:510-529`.
- **Evidence:** The report is a static six-metric display of notebook
  measurements. CSV export exists for current benchmark rows only; there is
  no Markdown/PDF or current-experiment report export.
- **Expected:** Reports and exports should be generated from persisted
  experiment data and carry reproducibility metadata.
- **Actual:** The static saved-run report is accurate for its captured run,
  but can become stale if notebook results change.
- **Severity:** Low.
- **Recommended:** Preserve it as the historical reference, then add exports
  tied to experiment IDs and saved raw results.

### F-06 - Frontend behavior is not covered by automated tests

- **File / lines:** `src/static/app.js:1-569`; test inventory is
  `tests/`.
- **Evidence:** The existing tests are Python `unittest` modules. No browser,
  DOM, accessibility, responsive-layout, or UI state tests exist.
- **Expected:** Input editing, error/loading states, tabs, sorting, chart
  rendering, and exports should have automated coverage.
- **Actual:** Frontend correctness is currently manually observable only.
- **Severity:** Medium.
- **Recommended:** Add focused browser tests when introducing UI capabilities;
  preserve API-backed scientific result rendering.

## Verified behavior

The existing UI includes responsive CSS, keyboard arrow/Home/End tab
navigation, focus-visible outlines, reduced-motion handling, escaping for
asset labels, and explicit empty/error states. All existing workspace assets
are byte-identical to their submission copies. Retain the current color
palette and useful functionality while extending it.

## Post-audit update

The benchmark table and CSV now show whether the requested penalty passes the
conservative certificate. The portfolio response notice surfaces the same
warning when it does not. A browser check confirmed a low-penalty run displays
the warning while retaining the real classical/QAOA results.

## Current UI status

The implementation has since expanded the existing application (without a
separate frontend stack) to eight workspaces: Portfolio Lab, Benchmark Lab,
Experiment Studio, Run History, Research Assistant, Circuit Explorer,
Hardware Analysis, and Research Report. The requested Aqua Jade `#74FFED`,
Midnight Abyss `#171F44`, and Baby Pink `#FEB1D1` palette is retained.
Experiment Studio submits bounded specifications to the Python API and shows
completed saved records; Run History loads them from the SQLite-backed API.
The assistant reports provider configuration and sends a selected experiment
only after explicit consent.

The findings above remain useful residual/design notes where applicable:
there are still no automated browser/DOM tests, asset count editing is not
part of the existing Portfolio Lab, the older Benchmark Lab remains a
separate recipe workflow, and live hosted-provider UI behavior has not been
tested. A browser-driven Studio run and record persistence were verified.
