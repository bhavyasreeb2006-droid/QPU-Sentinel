# Judge Q&A

### Is this running on a quantum computer?

No. The verified application and notebook runs use Qiskit Aer locally. No
physical QPU was accessed, and no quantum speedup or advantage is claimed.

### Is the QAOA implementation only in the notebook?

No. The QAOA implementation is in `src/qaoa_portfolio.py` and is called by
the application workflow. The notebook is a preserved, independently
executable four-asset reference with saved outputs.

### What problem is being solved?

The demonstration minimizes
`risk_aversion * x.T @ covariance @ x - expected_returns @ x` subject to
`sum(x) = K`, for binary selections x. The inputs are synthetic/hypothetical,
and the app visualizes selection, not capital weights.

### How is the classical reference obtained?

The solver enumerates feasible combinations of size K. For 20 assets and
K=10, it evaluated all C(20,10)=184,756 feasible portfolios. That is an
exact constrained reference; it is not an enumeration of all 2^20 states.

### Was the 20-asset QUBO identity checked exhaustively?

The saved record says 512 of 1,048,576 configurations were checked, so that
record's check is sampled. Separately, the release audit compared all
1,048,576 configurations and found a maximum identity error of
`2.984e-13`. The saved coverage has not been relabelled as exhaustive.

### Why is the 20-asset feasibility only 3.125%?

Two of 64 measured p=1 shots had Hamming weight 10. The count-to-asset
bitstring conversion and feasibility calculation were checked. Standard
QAOA here uses an unconstrained mixer, so it does not preserve cardinality.
Penalty 1.0 is sufficient for the exact global minimum on this instance by
direct exhaustive checking, although the engine's conservative general
penalty certificate does not pass. Low feasibility in this small sampled
run is therefore not a proof of a penalty bug.

### Did the 20-asset QAOA find the optimum?

No. The exact optimum was `01100110011010001110` with objective
`-1.2728654566`; it appeared in 0/64 QAOA samples. The best feasible sampled
selection was `10100100011010101101`, objective `-1.0114589901`, a gap of
`0.2614064664`.

### What happened in the four-asset run?

Exhaustive classical search checked all six K=2 portfolios and found `0110`
with objective `-0.093`. The QUBO identity was checked for all 16 bitstrings.
The saved p=2 Aer run measured 7,068 feasible shots and 1,189 shots of the
optimum among 8,192; transpiled depth was 15 with 12 two-qubit gates.

### What are the other saved records?

There are two three-asset, K=2 records (different covariance configurations)
and one 20-asset, K=10 record. They are stored in the root SQLite database and
its submission copy. The three-asset exact checks cover all three feasible
selections and all eight QUBO bitstrings.

### Are repeated runs reproducible?

The saved Studio records include deterministic instance and algorithm
configurations with seeds. Replaying the saved three- and twenty-asset specs
reproduced the dataset IDs, exact references, QAOA counts, and metrics in the
release check. This demonstrates repeatability for those local environment
and configuration combinations, not universal reproducibility across
dependency or platform changes.

### Are the hardware profiles real?

No. They are explicitly labelled simulated/illustrative profiles with
fictional capacities, couplings, and error inputs. They exercise the scoring
logic and do not report backend availability, calibration, or execution.

### Is the research assistant configured?

No. The current environment reports “Provider not configured.” The
implementation requires an OpenAI-compatible provider and explicit
experiment-data consent. The automated test uses a local mocked provider;
no hosted-provider response was verified.

### Is this investment advice?

No. The example uses synthetic data and binary asset selection. It does not
produce personalized financial advice or capital-allocation weights.
