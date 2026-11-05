# Benchmark Audit

## Current benchmark engine

`src/benchmark_workflow.py` defines three deterministic synthetic covariance
families (`independent`, `correlated`, `mixed`), asset counts 3-6, five
replicates per pair, and 60 recipes. Dataset generation uses
`numpy.random.default_rng(seed)` and constructs symmetric PSD matrices by
diagonal or factor-model construction. Cases select `K=max(1,N//2)` and use
fixed risk-aversion choices. Every executed case uses exact feasible search
and one standard-QAOA run with depth 2, 64 optimizer shots, 256 final shots,
and at most 8 COBYLA iterations.

No experiment row is stored in `results/` or a database. The suite has no
executed result set in the repository; the 60 entries are planned recipes.
The benchmark test suite runs one 3-asset case as a test, not as a completed
research result.

## Findings

### BM-01 - Fixed sizes and cardinalities restrict the research design

- **File / lines:** `src/benchmark_workflow.py:17-49, 52-77`;
  `src/webapp.py:171-189`.
- **Evidence:** The catalog fixes `ASSET_COUNTS=(3,4,5,6)`, `REPLICATES=5`,
  and one cardinality rule; the API filters only those counts and three types.
- **Expected:** Research experiments should vary valid `(N,K)` pairs and
  covariance structures under configurable safe limits.
- **Actual:** Odd/even sizes are both represented in recipes, but arbitrary
  sizes/cardinalities and user-configurable seeds/algorithms/noise are not.
- **Severity:** Medium.
- **Recommended:** Keep the existing 60 recipes as a reproducible preset and
  add a parameterized experiment specification rather than deleting or
  renumbering them.

### BM-02 - Result record is missing reproducibility-critical fields

- **File / lines:** `src/benchmark_workflow.py:79-126`.
- **Evidence:** Returned fields include case ID, N, problem type, replicate,
  exact/QAOA objective, gap, feasibility, runtime, depth, two-qubit count,
  feasible shots, total shots, and execution label. Dataset contents/ID,
  cardinality, seed, risk aversion, penalty, optimizer parameters, best
  bitstring, optimizer evaluation count, raw samples, and detailed error are
  omitted. A post-audit update adds a conservative penalty-guarantee flag and
  exclusive threshold, but not the other missing fields.
- **Expected:** Every result should be reproducible and independently
  auditable from its stored instance and settings.
- **Actual:** The case ID/recipe can regenerate some inputs, but the result
  itself is not a complete record and cannot be queried after restart.
- **Severity:** High for reproducibility.
- **Recommended:** Persist immutable problem data, complete parameter JSON,
  algorithm version, raw sample counts, objective conventions, and error
  details alongside measured metrics.

### BM-03 - Benchmark comparisons include only QAOA versus exact search

- **File / lines:** `src/benchmark_workflow.py:79-126`;
  `src/static/index.html:91-130`.
- **Evidence:** Each case computes one exact portfolio and one QAOA result.
  The table/charts show gap, feasibility, runtime, depth, and two-qubit gates.
- **Expected:** A shared instance should be evaluated by each implemented
  classical and quantum method before making algorithm comparisons.
- **Actual:** Greedy, random feasible, simulated annealing, warm-start QAOA,
  constrained-mixer QAOA, multiple repetitions, optimal-solution probability,
  and repeatability statistics are absent.
- **Severity:** Medium.
- **Recommended:** Add algorithms only when implemented/tested; seed and store
  each run; report mean/std/worst-case over matched instances and seeds.

### BM-04 - Full 60-case suite can be launched with no run budget

- **File / lines:** `src/webapp.py:171-231`;
  `src/benchmark_workflow.py:23-34, 79-126`.
- **Evidence:** An `all` filter enqueues all 60 cases. Each executes a COBYLA
  loop and final Aer run. There is no queue limit, timeout, cancellation, or
  admission check.
- **Expected:** Expensive work should have an explicit user-visible budget and
  a way to stop or bound it.
- **Actual:** The whole catalog may execute on demand in a daemon thread.
- **Severity:** Medium.
- **Recommended:** Require a configurable case/job budget and per-case
  deadline, keep the 60-case recipe catalog, and expose real cancellation/
  failure states.

### BM-05 - Relative gap is unstable near a zero exact objective

- **File / lines:** `src/benchmark_workflow.py:105-108`.
- **Evidence:** Percentage gap divides by `max(abs(exact_objective), 1e-12)`.
- **Expected:** A relative metric should have a defined interpretation when
  the reference is zero or near zero.
- **Actual:** A small absolute gap can be rendered as an arbitrarily large
  percentage near zero.
- **Severity:** Medium.
- **Recommended:** Report absolute gap as primary; define and label a
  scale-aware relative gap policy (or mark it undefined at/near zero) and test
  positive, negative, and zero references.

## Post-audit update

The benchmark record and table now include the conservative penalty
certificate and its strict threshold. The field is also included in CSV
export. The results remain in-memory only, and the remaining reproducibility
fields listed above are still outstanding.

## Data integrity status

The API and frontend distinguish recipes from completed executions and show
partial rows on failure. This is useful behavior to preserve. At audit time
there are **zero persisted benchmark results**; this is not a claim that the
60 catalog items have run.

## Separate Experiment Studio engine

The current `src/experiment_engine.py` addresses the broader scalable
comparison request without replacing `src/benchmark_workflow.py` or its 60
recipes. It supports asset counts 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, and 20,
arbitrary valid cardinalities, and independent/correlated/mixed synthetic
instances. Each instance is evaluated by exact feasible search and selected
greedy, random feasible, simulated annealing, and QAOA methods with matched
inputs. Repeated seeds produce per-run results and summaries.

Exact search is explicitly limited by candidate count; the API default is
250,000. QUBO identity checks are exhaustive through 12 assets and use 512
deterministic checks above that, recorded with `exhaustive: false`. Reports
include objective gaps, runtime, feasibility, optimality, repeatability, and
transpiled QAOA depth/gate counts. QAOA remains an unconstrained-mixer
simulator baseline, not a feasibility-preserving method.

One 3-asset, cardinality-2 Studio experiment and one bounded 20-asset pilot
are persisted in `results/experiments.sqlite3`; neither is part of the 60-case
recipe suite. The larger pilot used 184,756 exact candidates, 512
non-exhaustive QUBO checks, and low-shot QAOA; it did not match the exact
solution and is not a scaling-performance claim.
Remaining gaps: no timeout/cancellation or cross-process admission control,
no arbitrary user-entered covariance matrix in Experiment Studio, and no
statistical claim based on the single saved Studio instance. The earlier
in-memory status above continues to apply specifically to the legacy
Benchmark Lab.
