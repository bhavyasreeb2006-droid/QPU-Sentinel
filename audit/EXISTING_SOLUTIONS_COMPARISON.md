# Existing Solutions Comparison

## Sources reviewed

1. Qiskit Finance, **Portfolio Optimization tutorial**:
   <https://qiskit-community.github.io/qiskit-finance/tutorials/01_portfolio_optimization.html>
2. IBM Quantum, **Quantum approximate optimization algorithm**:
   <https://quantum.cloud.ibm.com/docs/en/tutorials/quantum-approximate-optimization-algorithm>
3. Woerner and Egger, **Improving Variational Quantum Optimization using
   CVaR**, *Quantum* 4, 256 (2020), arXiv:1907.04769:
   <https://arxiv.org/abs/1907.04769>
4. D-Wave, **Hybrid solvers**:
   <https://docs.dwavequantum.com/en/latest/concepts/hybrid.html>

The Qiskit Finance page demonstrates a binary mean-variance portfolio with a
cardinality budget, a quadratic penalty, an exact `NumPyMinimumEigensolver`
baseline, `SamplingVQE`, and QAOA. Its displayed environment is an older
Qiskit stack, so its example is a conceptual comparison, not a dependency
recommendation for this repository.

IBM's current QAOA tutorial teaches the QUBO-to-Hamiltonian and alternating
cost/mixer workflow using Max-Cut, and covers cloud hardware execution. It is
not itself a portfolio application. The paper by Woerner and Egger studies
CVaR aggregation for variational combinatorial optimization and includes
simulation and hardware experiments; it is methodological background rather
than evidence that this project's four-asset result generalizes.

D-Wave Leap's commercial hybrid service accepts quadratic and nonlinear
models, including constrained models, while direct QPU submissions use BQM
representations. It is a different quantum-computing approach/product from
gate-model QAOA and is an adjacent solver option, not a like-for-like
implementation comparison.

| Existing solution | Method | Capabilities evidenced by source | Limitations / distinction | Difference from QPU Sentinel |
|---|---|---|---|---|
| Qiskit Finance Portfolio Optimization tutorial | Binary mean-variance model; penalty conversion; exact NumPy baseline; SamplingVQE/QAOA | Directly addresses a closely matching portfolio formulation and shows exact and variational solutions with sample probabilities | Tutorial is a small example and its page shows older package versions; not a reproducible multi-size comparative study | The mathematical problem and QAOA approach are not novel relative to this example. QPU Sentinel's current added value is a local, inspectable notebook/UI with QUBO identity checks and measured circuit summaries, but only on a tiny instance |
| IBM Quantum QAOA tutorial | Gate-model QAOA with classical feedback, demonstrated on Max-Cut and a hardware workflow | Explains QUBO/Ising mapping, QAOA ansatz, transpilation/runtime, and a path to actual platform execution | Not a portfolio-specific product; cloud execution is dependent on account/plan and backend availability | QPU Sentinel currently targets portfolio subset-selection and local Aer, not IBM Runtime hardware jobs |
| Woerner & Egger (2020) | Variational quantum optimization with CVaR objective aggregation | Published method and simulation/hardware evaluation for combinatorial problems | CVaR is a distinct aggregation objective; results from their tested problems do not transfer to this project's settings | QPU Sentinel currently uses sampled mean QUBO energy with COBYLA; it does not implement CVaR or reproduce that study |
| D-Wave Leap Hybrid solvers | Commercial quantum-classical hybrid solvers over quadratic/nonlinear models; direct QPU BQM path | Handles broader constrained model forms through hybrid services and supplies a commercial optimization platform | Different hardware/algorithm stack; vendor service and resources differ from local Qiskit Aer; no benchmark comparison was run here | QPU Sentinel is currently a transparent gate-model QAOA research demonstrator, not a competing production solver |

## Research-gap assessment

The proposed direction—transparent measurement of solution quality,
feasibility, repeatability, and circuit resource scaling across sizes and
covariance structures—is a meaningful **experimental platform and study
design**, but is not yet a demonstrated scientific contribution. Existing
work already covers the same portfolio formulation and QAOA; the project must
not claim novelty for applying QAOA to portfolio selection, nor claim quantum
advantage.

To establish a stronger contribution, complete a pre-registered or otherwise
fully specified matched-instance study with multiple seeds, credible
classical baselines, exact optima where tractable, explicit timeout/reference
labels, saved experiment records, uncertainty summaries, and reproducible
hardware-resource accounting. The present code has only one active algorithm,
fixed N=3..6 recipes, no persistence, and no repeated-seed per-instance
statistics.

## Verification boundaries

No third-party software was installed or run. The comparison summarizes the
linked public documentation/paper; it does not benchmark any commercial
solver or infer performance from vendor examples. QPU Sentinel's measured
results remain those saved in its notebook and `RESULTS.md`.

## Implementation update

The codebase now contains the proposed local matched-instance engine,
classical baselines, repeated seeded runs, and SQLite persistence. This is a
software capability update, not evidence that the research gap has been
closed: the saved Studio evidence is one three-asset instance, and no broad
statistical study or external-solver comparison has been completed. The
notebook's four-asset QAOA run remains the preserved reference. No novelty,
speedup, or quantum-advantage claim is supported.
