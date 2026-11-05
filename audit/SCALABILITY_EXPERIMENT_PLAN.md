# Scalability Experiment Plan

## Research question

For fixed synthetic portfolio instances and matched seeds, how do solution
quality, cardinality feasibility, repeatability, runtime, and measured circuit
resources of standard QAOA change with asset count and covariance structure,
compared with transparent classical references?

## Current limits established by audit

- The current verified experiment has N=4, K=2.
- The 60 benchmark recipes cover only N=3..6 and one K per N.
- Exact portfolio enumeration and QUBO proof both scan `2^N` bitstrings.
- QAOA is standard unconstrained-mixer QAOA on local Aer only.
- No benchmark outputs persist; one run per recipe is not a repeatability
  study.
- Current benchmark rows have no raw count histogram or full parameter record.

## Proposed staged matrix

Keep the four-asset saved run as a regression reference. Extend synthetic
instances in controlled pilot batches, not as an automatic large sweep:

| Stage | Asset counts | Cardinalities | Purpose |
|---|---|---|---|
| Regression | N=3,4,5,6 | Existing preset plus boundary K=1 and K=N-1 | Preserve current recipes and test odd/even behavior |
| Pilot | N=8,10,12 | K near N/4, N/2, 3N/4, restricted to valid integers | Check feasibility and runtime with multiple methods |
| Stress (opt-in) | N=16,20 and then larger only after measured review | Same ratios | Measure scaling; do not assume statevector Aer will be practical |

For each size/cardinality, generate low-correlation, high-positive-correlation,
and mixed-factor PSD covariance instances from fixed seeds. Keep returns and
covariances synthetic and label them as such. Dataset generation must be a
pure seeded function and store the generated values or a stable content hash
plus generation version.

## Algorithms and fairness

Add algorithms only after implementation and tests. Initial comparison set:

1. Exact feasible search for small instances, with a configurable combination
   budget and an explicit timeout.
2. Greedy feasible selection.
3. Random feasible baseline.
4. Simulated annealing, if dependency/API and reproducibility are verified.
5. Existing standard QAOA.
6. Later, separately identified warm-start or constraint-preserving QAOA.

Every algorithm receives the exact same instance and objective convention.
Use at least three independent run seeds per instance in pilot analysis; store
each individual run and summarize mean, standard deviation, worst case, and
feasibility. Reference exact objective only when exact search completes;
otherwise record and name the best available reference algorithm, never label
it as an optimum.

## Resource and stop policy

Before any run, estimate:

- `C(N,K)` feasible exact candidates.
- `2^N` configurations required for exhaustive QUBO proof.
- QAOA qubits and dense pair-interaction count.
- optimizer evaluations times optimizer shots plus final shots.
- a wall-clock deadline and maximum job count.

Enforce configurable candidate, work, time, and job limits. For larger N,
skip exhaustive QUBO checks only with an explicit `not_exhaustively_verified`
result state and validate formula/energy against deterministic samples and
small-instance property tests. Never silently treat a sampled check as a
proof.

Start with one small pilot job at a time. Do not automatically launch hundreds
of simulator experiments. Cancel or stop expansion if memory/runtime limits
are reached, and record failures and partial completion rather than omitting
them.

## Required record shape

Persist experiment ID/time/status; dataset ID, values, generation seed,
structure, N and K; risk aversion and penalty plus adequacy status; algorithm
and version; QAOA depth/shots/optimizer/evaluations/seed; simulator/noise or
hardware execution label; exact/reference method and objective; best solution
and objective; objective gap and definition; feasible/optimal sample
probabilities; raw counts; runtime; logical/transpiled qubits, depth and gate
counts; and error/timeout/cancellation data.

## Analysis outputs

Plot completed runs only. Show instance-level distributions and confidence or
uncertainty summaries, not only pooled means. Separate runtime by machine and
execution backend. Report feasibility and conditional best-feasible quality
separately. Do not treat simulated profiles as hardware results or claim
quantum advantage.

## Implementation checkpoint

The planned initial comparison system is implemented in
`src/experiment_engine.py` and is reachable from Experiment Studio. Supported
sizes are 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, and 20, with any valid
cardinality; covariance generation supports the three planned structures.
Implemented methods are exact feasible search, greedy selection, random
feasible sampling, simulated annealing, and standard QAOA. Seeded repetitions
share the same generated instance. The result includes run-level gap,
feasibility, optimality, runtime, QAOA resources, and summary repeatability
metrics.

Exact feasible candidates are capped (250,000 via the API). QUBO identity
verification is exhaustive through 12 assets and is explicitly sampled and
non-exhaustive above that. SQLite persistence and history are implemented. The saved database includes
one browser-created three-asset comparison and one bounded 20-asset pilot in
`results/experiments.sqlite3`.

Not implemented: a per-job hard deadline, cancellation, retry, durable
cross-process queue/locking, custom user-entered datasets in Studio, and
large-scale statistical aggregation. The older 60-case Benchmark Lab remains
separate. No QPU/noise-model path or quantum-advantage claim is included.
