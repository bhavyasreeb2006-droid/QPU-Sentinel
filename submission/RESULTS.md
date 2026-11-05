# Results Summary

## Run scope

This summary records the outputs saved in
[`notebooks/qpu_sentinel_qaoa.ipynb`](notebooks/qpu_sentinel_qaoa.ipynb) after
the notebook's complete execution on **November 3, 2026**. The execution used
Qiskit Aer locally with the dependencies in `requirements.txt`. There are no
hardware measurements in this report.

The input returns and covariance values are **hypothetical**. They are only
used to demonstrate a small optimization workflow and do not represent live
market data or investment guidance.

## Application and analyzer status

The project now includes an optional localhost browser interface. It runs the
shared classical/QUBO workflow and the existing `src/qaoa_portfolio.py` QAOA
implementation, then passes that run's circuit metrics to the suitability
analyzer. The notebook remains the primary executable deliverable and now
shows the same analyzer against its recorded circuit metrics.

The analyzer's three candidates are explicitly fictional simulated profiles.
Their capacities, coupling maps, budgets, and gate/readout error values are
illustrative inputs only. They are not IBM backend listings, live properties,
or hardware execution results. The ranking is a deterministic application of
the documented scoring weights to the chosen profile data, not a measured
device benchmark. See `ARCHITECTURE.md` for the scoring rubric.

With the recorded circuit (4 qubits, transpiled depth 15, and 12 two-qubit
gates) and all six pairwise QUBO interactions, the notebook produced:

| Fictional simulated profile | Score | Compatibility |
|---|---:|---|
| Simulated Profile A - low-error line | 82.17 / 100 | Compatible in this scenario |
| Simulated Profile B - balanced ring | 79.80 / 100 | Compatible in this scenario |
| Simulated Profile C - compact dense | 67.00 / 100 | Compatible in this scenario |

These are scores over illustrative input values, not device performance
measurements. The interface's error, connectivity, capacity, and budget
visuals must be interpreted in that context.

## Dashboard and benchmark scope

The local interface is organized into Portfolio Lab, Benchmark Lab, Circuit
Explorer, Hardware Analysis, and Research Report. Portfolio charts and circuit
views are rendered from a completed experiment; the donut depicts binary
selection status only and does not compute capital allocation weights. The
four-asset reference has six exact feasible portfolios.

Benchmark Lab defines 60 deterministic generation recipes: asset counts 3-6,
three covariance structures (independent, positively correlated, and
mixed-factor), and five replicates per combination. Recipes are generated and
executed on demand with local Aer. Each completed row reports its exact and
QAOA objectives, objective gap, measured feasibility, local wall-clock
runtime, transpiled circuit depth, and two-qubit gate count. The repository
does not contain a persisted 60-case execution result set; the saved
measurements below are the notebook reference experiment, not benchmark-suite
results.

## Classical exhaustive reference

The problem selects exactly two of four assets and minimizes

`2.0 * x.T @ covariance @ x - expected_returns @ x`.

The classical enumeration checks all six feasible combinations. Its best
selection is `0110` (ASSET_B and ASSET_C):

| Selection | Assets | Expected return | Portfolio variance | Objective |
|---|---|---:|---:|---:|
| `0110` | ASSET_B, ASSET_C | 0.17 | 0.0385 | -0.093 |
| `1010` | ASSET_A, ASSET_C | 0.19 | 0.0580 | -0.074 |
| `1100` | ASSET_A, ASSET_B | 0.22 | 0.0745 | -0.071 |
| `0011` | ASSET_C, ASSET_D | 0.22 | 0.0765 | -0.067 |
| `0101` | ASSET_B, ASSET_D | 0.25 | 0.0950 | -0.060 |
| `1001` | ASSET_A, ASSET_D | 0.27 | 0.1185 | -0.033 |

The covariance eigenvalues were `0.00907687`, `0.02072788`, `0.03889644`,
and `0.06629881`; the notebook's positive-semidefinite check passed.

## QUBO verification

The notebook verified the QUBO energy against the original objective plus the
cardinality penalty for all 16 binary configurations. All assertions passed.
The lowest-energy configuration is `0110`, with energy `-0.093`.

## QAOA-on-Aer measurements

| Metric | Recorded value |
|---|---:|
| Backend | Qiskit Aer `AerSimulator` (local simulation) |
| QAOA depth, `p` | 2 |
| COBYLA objective evaluations | 39 |
| Optimizer success flag | `True` |
| Sampled optimizer energy estimate | 0.07979199218750001 |
| Transpiled circuit depth | 15 |
| Transpiled two-qubit gates | 12 |
| Final shots | 8,192 |
| Feasible shots (`K = 2`) | 7,068 / 8,192 |
| Feasibility rate | 86.2793% |
| Exact optimum selection | `0110` |
| Shots measuring `0110` | 1,189 / 8,192 |
| Exact optimum sample rate | 14.5142% |
| Best feasible sampled selection | `0110` |
| Best feasible objective | -0.093 |

The final sample frequencies by bitstring were:

| Selection | Shots | Probability | Feasible | Objective |
|---|---:|---:|:---:|---:|
| `0101` | 1,235 | 15.0757% | Yes | -0.060 |
| `1001` | 1,204 | 14.6973% | Yes | -0.033 |
| `0110` | 1,189 | 14.5142% | Yes | -0.093 |
| `1010` | 1,170 | 14.2822% | Yes | -0.074 |
| `1100` | 1,162 | 14.1846% | Yes | -0.071 |
| `0011` | 1,108 | 13.5254% | Yes | -0.067 |
| `1000` | 180 | 2.1973% | No | -0.040 |
| `0001` | 160 | 1.9531% | No | -0.025 |
| `0010` | 147 | 1.7944% | No | -0.050 |
| `0100` | 135 | 1.6479% | No | -0.055 |
| `1101` | 119 | 1.4526% | No | -0.044 |
| `0111` | 108 | 1.3184% | No | -0.090 |
| `1011` | 103 | 1.2573% | No | -0.059 |
| `1110` | 72 | 0.8789% | No | -0.093 |
| `0000` | 53 | 0.6470% | No | 0.000 |
| `1111` | 47 | 0.5737% | No | -0.058 |

## Interpretation and limitations

- The best feasible sampled QAOA bitstring matched the exhaustive classical
  optimum in this run. The optimum appeared in 1,189 of the 8,192 final shots.
- Feasibility was not guaranteed: 1,124 final shots violated the exactly-two
  constraint.
- This is a four-variable simulator experiment with a classical exhaustive
  solution. It does **not** show quantum advantage, a speedup, or better
  financial decisions.
- The run is not evidence of QPU execution. No hardware backend or noise model
  was used, and no physical-device calibration or job metadata is available.
- The values depend on the defined toy inputs, simulator, optimizer, seed, and
  shot counts. They should not be generalized beyond this experiment.

## Application validation

The automated suite verifies that the shared exact optimizer preserves the
recorded classical optimum (`0110`), that the QUBO agrees with the penalized
objective for all 16 configurations, that compatibility and scoring account
for capacity/depth/gate/connectivity/error inputs, and that a small seeded
application run completes through QAOA and profile analysis. That reduced-shot
test run is a validation check; it is not a replacement for, or an additional
claim about, the saved 8,192-shot notebook run.

## Persisted Experiment Studio run

The local application created and completed a separate experiment record in
`results/experiments.sqlite3`. It is independent of the four-asset notebook
reference and must not be combined with its shot statistics.

| Field | Saved result |
|---|---|
| Experiment ID | `214e1db019c8481497ca72702bd568f3` |
| Instance | 3 synthetic assets, cardinality 2, mixed covariance, seed 2026 |
| Exact feasible candidates | 3 |
| Exact selection / objective | `110` / -0.2197078076 |
| QAOA best feasible selection / objective | `110` / -0.2197078076 |
| QAOA feasibility rate | 64.0625% |
| QAOA measured runtime | 0.4333 seconds (local run) |
| Transpiled QAOA depth / two-qubit gates | 7 / 3 |
| Compared methods | Exact, greedy, random feasible, simulated annealing, QAOA |

This is one seeded synthetic instance and one QAOA repetition. It is evidence
that the Experiment Studio path generated, measured, and persisted a result;
it is not a statistical benchmark or a performance claim. The generated
instance, method configuration, individual runs, and summaries are stored
with the record. The original notebook and its saved outputs remain
unchanged.

## Persisted 20-asset pilot

A second bounded Experiment Studio record exercises the largest supported
asset count. It uses a synthetic mixed-covariance instance, `N=20`, `K=10`,
seed 2030, one repetition, and depth-1 QAOA with 64 optimizer/final shots.
The exact candidate search completed and the QUBO check is explicitly
non-exhaustive.

| Field | Saved result |
|---|---|
| Experiment ID | `d178d82070f443a6af789b157a4b1bd0` |
| Exact candidates evaluated | 184,756 |
| QUBO configurations checked | 512 / 1,048,576 (non-exhaustive) |
| Exact selection / objective | `01100110011010001110` / -1.2728654566 |
| Best feasible QAOA selection / objective | `10100100011010101101` / -1.0114589901 |
| Objective gap from exact reference | 0.2614064664 |
| Feasible QAOA samples | 2 / 64 (3.125%) |
| QAOA runtime | 1.0265 seconds (local run) |
| Transpiled QAOA depth / two-qubit gates | 41 / 190 |

This pilot demonstrates that a bounded 20-asset run can complete and persist;
it also shows that this low-shot QAOA run did not match the exact optimum and
had low feasibility. It is not evidence of quantum advantage, scaling
performance, or statistical significance. The full parameters and actual
instance are stored in SQLite.

## Experiment-engine scope and limits

The implemented engine accepts asset counts 3, 4, 5, 6, 7, 8, 9, 10, 12,
15, and 20, and valid cardinalities from 1 through `N`. It compares exact
search with any selected combination of greedy selection, random feasible
sampling, simulated annealing, and standard QAOA on one generated instance.
Repeated seeded runs report per-run objective gap, runtime, feasibility,
optimality, and selection repeatability; QAOA runs include measured
transpiled depth and two-qubit gate counts.

Exact search is bounded by the configured feasible-candidate limit (250,000
through the API). The 20-asset, cardinality-10 case has 184,756 candidates
and fits that limit. QUBO identity checks are exhaustive through 12 assets;
larger instances use 512 deterministic checks and are explicitly marked
non-exhaustive. The app allows one active Experiment Studio job per server
process; cancellation and hard wall-clock deadlines are not implemented.
The separate 60-case Benchmark Lab catalog remains on-demand and is not
represented by the persisted Studio record above.

## Research assistant status

The assistant implementation only accepts a selected completed experiment,
requires explicit consent before provider transmission, and returns a clear
unconfigured state when no provider key is set. Its OpenAI-compatible request
path was tested with a local mock provider. No hosted provider credentials or
live external response were used or verified.
