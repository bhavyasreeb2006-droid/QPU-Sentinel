# QAOA and Qiskit Audit

## Implemented circuit

`src/qaoa_portfolio.py:12-188` implements standard QAOA on `AerSimulator`.
Each portfolio variable maps to one qubit. The sequence is:

1. Prepare `|+>^N` with Hadamard gates (`circuit.h`, line 47).
2. Convert the binary QUBO to an Ising cost Hamiltonian using `x=(1-Z)/2`
   (lines 34-42).
3. For each layer `p`, apply `RZ(2*gamma*c_i)` for linear Z terms (line 53)
   and `RZZ(2*gamma*c_ij)` for pair ZZ terms (line 57).
4. Apply `RX(2*beta)` to each qubit (line 59).
5. Add all-qubit measurements (line 61), transpile for Aer with optimization
   level 1 and a seeded transpiler (lines 63-66).
6. Use SciPy COBYLA to minimize a finite-shot estimate of penalized QUBO
   energy; use the optimized angles for a separate final sampling run
   (lines 71-104).

The rotation factors of two follow Qiskit's convention that `RZ(theta)` and
`RZZ(theta)` implement an exponential with angle `theta/2`; the mapping of
`x_i x_j` contributes `q_ij/4 * Z_i Z_j` and adjusts both single-Z terms.
The constant energy offset does not affect the circuit's state and is
included in classical sampled-energy evaluation through `qubo_energy`.

## Constraint behavior

The mixer is standard transverse-field `RX`, not a cardinality-preserving
mixer. Hadamard initialization covers all bitstrings, and the `RX` layers
preserve neither Hamming weight nor `sum(x)=K`. The code correctly labels
samples as feasible/infeasible and raises if no feasible sample is observed.
There is no implemented warm-start or XY/constraint-preserving variant.

## Bit order, randomness, and metrics

Qiskit count strings are converted to asset order by removing spaces and
reversing the string (`selection_from_count`, line 68). Both optimizer and
final sampling use explicit simulator seeds; the optimizer seed advances with
each evaluation and the final run uses `seed + 100_000` (lines 80, 102).
Transpilation is also seeded.

Current results report depth, two-qubit gate count, optimizer success and
evaluation count, sample objective estimate, final shots, feasibility and
optimal-selection frequencies. The optional logical circuit report includes
logical gate counts, operations, measurement count, and depth. No noisy Aer
model or hardware execution is configured. Compiled single-qubit gate counts,
compiled qubit count, native-target compatibility, and routing/transpilation
metadata are not returned.

## Findings

### Q-01 - Standard mixer generates infeasible bitstrings

- **File / lines:** `src/qaoa_portfolio.py:47-61, 108-128`.
- **Evidence:** H initialization and per-qubit `RX` mixer act on the full
  computational basis; feasibility is computed after measurement.
- **Expected:** A cardinality-preserving algorithm would remain in the
  feasible subspace; otherwise the application must identify the algorithm
  as standard unconstrained QAOA and report infeasible mass.
- **Actual:** The implementation is standard QAOA and reports feasibility,
  but no constraint-preserving variant exists.
- **Severity:** Medium (important experimental interpretation).
- **Recommended:** Preserve standard QAOA as the baseline, label it clearly,
  and implement constrained mixers only as separately tested algorithms.

### Q-02 - QAOA runner has incomplete parameter validation

- **File / lines:** `src/qaoa_portfolio.py:12-32`.
- **Evidence:** It checks coefficient array shapes and that depth and shot
  counts compare positive, but does not check coefficient finiteness,
  `max_iterations`, seed type/range, or integer-ness of depth/shots. Boolean
  values pass Python's integer comparisons.
- **Expected:** Invalid parameter values should fail with stable,
  understandable validation errors before building/running a circuit.
- **Actual:** Some invalid inputs fail later in Qiskit/SciPy or can be accepted
  unintentionally.
- **Severity:** Medium.
- **Recommended:** Add explicit finite/type/range validation with direct tests;
  preserve currently valid seeded call behavior.

### Q-03 - Measurement mapping lacks a dedicated regression test

- **File / lines:** `src/qaoa_portfolio.py:68-69, 82-86, 107-110`;
  `tests/test_portfolio_workflow.py:78-106`.
- **Evidence:** Bit reversal is central to mapping Qiskit count strings to
  asset order. Existing app tests check the default best selection but do not
  exercise known asymmetric bit patterns or all measured indices.
- **Expected:** Each qubit-to-asset index should be verified independently.
- **Actual:** The current mapping follows Qiskit's count convention but is
  indirectly tested only through a stochastic small run.
- **Severity:** Medium.
- **Recommended:** Add deterministic unit tests for counts such as a single
  excited qubit at each index, and preserve arbitrary asset count coverage.

### Q-04 - Circuit resource report is incomplete for hardware planning

- **File / lines:** `src/qaoa_portfolio.py:135-186`.
- **Evidence:** Only transpiled depth and two-qubit operation count are
  surfaced. Logical gate counts are present, but not transpiled gate counts by
  operation, transpiled width, target basis, or routing overhead.
- **Expected:** Hardware resource analysis should derive requested metrics
  from a target-aware transpiled circuit, with simulator/hardware context
  explicit.
- **Actual:** The current report is an Aer-transpiled logical circuit summary,
  not a target-specific hardware estimate.
- **Severity:** Medium.
- **Recommended:** Extend metrics from actual Qiskit transpilation properties
  only; label simulator and illustrative-profile estimates separately.

## Compatibility and preserved behavior

The installed manifests pin Qiskit 2.6.1 and Qiskit Aer 0.18.2. The current
runner uses supported `QuantumCircuit`, `ParameterVector`, `transpile`,
`AerSimulator`, and SciPy `minimize` APIs, and the existing QAOA integration
test passes. Do not replace the implementation with a different Qiskit
Algorithms package or downgrade dependencies without a compatibility need.

## Current implementation update

The shared runner now includes stronger type/range/finiteness and seed-bound
validation and reports compiled qubit count and gate counts by operation in
addition to transpiled depth and two-qubit gates. The Experiment Studio uses
this same `src/qaoa_portfolio.py` implementation for every QAOA run; QAOA is
not notebook-only. The 20-asset pilot configuration remains bounded by the
engine's QAOA settings and is local Aer simulation.

The standard RX mixer remains unconstrained. Feasibility is measured from
samples and can be zero; engine records can represent a missing feasible
selection rather than pretending one was found. The historical notebook's
saved run still reports 8,192 shots, depth 15, and 12 two-qubit gates; the
separate persisted 3-asset Studio run reports depth 7 and 3 two-qubit gates.
Those are distinct local simulator executions. No target-aware hardware
transpilation or QPU results are present.
