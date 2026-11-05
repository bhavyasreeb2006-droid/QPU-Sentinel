# Release Checklist

## Application and demo

- [x] Replaced the stale port-8000 service with the application started by
  `.\.venv\Scripts\python.exe -m src.webapp --port 8000`.
- [x] Confirmed `/api/health`, `/api/assistant/status`,
  `/api/experiment/options`, and `/api/experiments?limit=10` return HTTP 200.
- [x] Browser-checked navigation handlers and visibility for all eight
  workspaces using dispatched click events.
- [x] Ran Portfolio Lab in the browser; it returned HTTP 200 and rendered the
  expected four-asset result.
- [x] Confirmed Run History displays all three saved experiment records.
- [x] Confirmed assistant status is explicitly unconfigured and hardware
  profiles are labelled illustrative/simulated.
- [x] Kept the live application server available at
  <http://127.0.0.1:8000> for demonstration.
- [ ] Before presenting, manually click a workspace tab and Run Experiment.
  The browser automation harness did not deliver native pointer clicks, so
  this manual interaction preflight remains unverified.

## Data, experiment, and deliverable integrity

- [x] Created and integrity-checked pre-reconciliation SQLite backups for
  both root and submission databases.
- [x] Reconciled the missing third completed experiment after confirming
  shared rows matched.
- [x] Added the verified generation version to the two legacy 3-asset
  instances; preserved their old dataset IDs as `legacy_dataset_id`.
- [x] Confirmed root and submission databases contain the same three records
  and pass `PRAGMA integrity_check`.
- [x] Replayed saved 3- and 20-asset configurations and matched their
  references, QAOA counts, and reported metrics.
- [x] Confirmed the notebook copies have matching SHA-256
  `c061e4fc1142be553386e54c09312d36ddd792fafb7d2a7f5326f189bb07b2e8`.
  Neither notebook nor its saved outputs were changed.
- [x] Kept the existing application, PowerPoint, and notebook as separate
  deliverables; did not rebuild the deck.

## Tests and checks

- [x] Root suite: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`
  — 33 tests passed.
- [x] Submission suite: from `submission`,
  `..\.venv\Scripts\python.exe -m unittest discover -s tests -v`
  — 33 tests passed.
- [x] Compilation: `.\.venv\Scripts\python.exe -m compileall -q src tests`
  — passed.
- [x] Browser smoke checks on the correct localhost application server:
  workspace navigation, Portfolio Lab output, Run History, assistant status,
  and hardware labels.

## Handover and claims

- [x] Added `FINAL_README.md`, `COMPETITION_STATUS.md`, `DEMO_SCRIPT.md`,
  `JUDGE_QA.md`, and this checklist.
- [x] Documented local Aer execution, fictional hardware profiles, and the
  unconfigured AI provider.
- [x] Distinguished exhaustive exact search from sampled QUBO checks and
  documented the separate exhaustive 20-asset release audit.
- [x] Made no physical-QPU, speedup, or quantum-advantage claim.
- [x] Avoided expensive additional experiments and did not rebuild the
  PowerPoint.

## Remaining release limitations

- The AI provider is unconfigured; live hosted-provider behavior is not
  validated.
- No physical hardware result exists; hardware profiles are fictional.
- The 20-asset QAOA run had 3.125% feasibility and did not sample the exact
  optimum. Its persisted QUBO check remains explicitly sampled.
- Benchmark recipes are on demand and are not a completed benchmark suite.

**Disposition:** conditionally ready for a controlled live demonstration of
the local simulator application. Complete the manual pointer preflight above
before the audience arrives, and state the limitations clearly.
