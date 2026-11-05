# QPU Sentinel

**A reproducible, notebook-first QAOA experiment with a local product interface
and transparent hardware-suitability analysis.**

QPU Sentinel turns illustrative cardinality-constrained portfolio problems
into QUBOs, compares classical methods with QAOA on Qiskit Aer, and records
completed experiments in SQLite. The preserved four-asset notebook remains
the reference experiment; the local browser app also supports scalable
synthetic experiments, run history, and an opt-in research assistant.

> **Scope and claims:** This project has been run on a local quantum simulator.
> It has not been run on quantum hardware, and it does not demonstrate quantum
> advantage. The suitability profiles and their error/capacity data are
> fictional teaching examples, not IBM hardware listings or calibration data.
> The financial inputs are hypothetical and are not investment advice.

## Start here

The primary executable deliverable is
[`notebooks/qpu_sentinel_qaoa.ipynb`](notebooks/qpu_sentinel_qaoa.ipynb). Run
its cells from top to bottom in Jupyter or VS Code with the project environment
selected as the notebook kernel. The notebook includes the simulator
validation, problem definition, exhaustive classical benchmark, QUBO
verification, and QAOA experiment.

The notebook remains the primary executable deliverable. The optional local
interface is a second way to explore the same classical and QAOA workflow.

### Launch the local interface

After installing the requirements and activating the project environment,
run from the project root:

```powershell
.\.venv\Scripts\python.exe -m src.webapp
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The dashboard opens in
**Portfolio Lab** for the preserved four-asset workflow. **Experiment Studio**
supports 3-20 assets, valid cardinalities, repeated seeded runs, and matched
exact, greedy, random feasible, simulated-annealing, and QAOA results.
Completed Studio runs are saved in `results/experiments.sqlite3` and appear
in **Run History**. **Benchmark Lab** remains a separate 60-recipe preset
(asset counts 3-6), executed on demand; those recipes are not precomputed
results. The other tabs expose the circuit, illustrative hardware analysis,
saved notebook report, and opt-in research assistant. The app binds to
localhost and never contacts a QPU.

The assistant is unavailable until an OpenAI-compatible provider is
configured. Set `QPU_SENTINEL_AI_API_KEY` and, optionally,
`QPU_SENTINEL_AI_BASE_URL` and `QPU_SENTINEL_AI_MODEL`. The UI requires
explicit consent before sending the selected saved experiment summary and
question to that provider. No provider or credentials are configured by
default; assistant answers are not generated from unrecorded results.

### Setup

Python 3.12 is the tested runtime. From the project root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

In VS Code, open the notebook and select the `.venv` Python interpreter as its
kernel. To run the complete notebook headlessly and save its outputs:

```powershell
.\.venv\Scripts\python.exe -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1200 notebooks\qpu_sentinel_qaoa.ipynb
```

The saved results can vary if you change the simulator, seed, optimizer, or
shot counts. The notebook's saved outputs and [`RESULTS.md`](RESULTS.md)
describe the recorded run.

## Recorded simulator run

| Measurement | Result |
|---|---:|
| Classical optimum | `0110` — ASSET_B and ASSET_C |
| Best feasible QAOA sample | `0110` |
| Feasible QAOA samples | 7,068 / 8,192 (86.28%) |
| Optimal-selection samples | 1,189 / 8,192 (14.51%) |
| QAOA circuit | depth 2; transpiled depth 15; 12 two-qubit gates |

These are simulator measurements for a four-variable toy problem, not
hardware results or evidence of a speedup. See [`RESULTS.md`](RESULTS.md) for
the full metrics and interpretation.

## Project map

```text
notebooks/qpu_sentinel_qaoa.ipynb   Primary runnable experiment and outputs
src/qaoa_portfolio.py               Existing QAOA circuit, optimization, sampling
src/portfolio_workflow.py           Shared validation, classical search, QUBO
src/benchmark_workflow.py           Deterministic benchmark recipes and Aer runs
src/experiment_engine.py            Matched scalable classical/QAOA experiments
src/experiment_store.py             SQLite job and result persistence
src/research_assistant.py           Consent-gated, experiment-grounded assistant
src/hardware_suitability.py          Compatibility checks and explainable scoring
src/webapp.py                        Local standard-library HTTP interface
src/static/                          Browser UI (HTML, CSS, JavaScript)
tests/                               Engine, persistence, API, assistant, workflow tests
results/experiments.sqlite3          Persisted local experiment records (created on use)
ARCHITECTURE.md                      Design, data flow, and scoring approach
RESULTS.md                           Recorded measurements and limitations
requirements.txt                     Reproducible Python dependency versions
presentation/                        Deck, slide brief, and diagrams
audit/                               Project, math, QAOA, service, AI, and scale audits
```

## Problem at a glance

Select exactly two of four hypothetical assets, minimizing
`risk_aversion * x.T @ covariance @ x - expected_returns @ x`. The notebook
uses a quadratic penalty to convert the cardinality constraint into a QUBO,
then exhaustively checks all 16 bitstrings to verify the conversion. The
QAOA implementation uses parameterized `RZ`/`RZZ` cost layers, `RX` mixer
layers, COBYLA optimization, and Qiskit Aer sampling.

Read [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full execution flow and
[`RESULTS.md`](RESULTS.md) for recorded outputs. The interactive walkthrough
and answers to likely judging questions are in
[`presentation/slide-deck.md`](presentation/slide-deck.md).

## Hardware Suitability Analyzer

The analyzer checks qubit capacity, depth and two-qubit gate budgets,
two-qubit/readout error inputs, and coupler connectivity. It returns a
0-to-100 weighted score, compatibility status, a ranked list, component
scores, and plain-language reasons. Missing telemetry is scored neutrally
and called out. The weights and thresholds are visible in
[`src/hardware_suitability.py`](src/hardware_suitability.py).

All three bundled candidates are labelled **SIMULATED PROFILE**. Their
resource limits, coupling maps, and error values are fabricated illustrative
inputs. Suitability rankings are demonstrations of the scoring method, not
claims about actual devices or execution results. See the architecture
document for scoring weights and compatibility rules.

The interface includes Portfolio Lab, Benchmark Lab, Experiment Studio, Run
History, Research Assistant, Circuit Explorer, Hardware Analysis, and Research
Report. Its Experiment Studio supports asset counts 3, 4, 5, 6, 7, 8, 9, 10,
12, 15, and 20, with any valid cardinality. Exact search is bounded by a
candidate budget; QUBO equivalence is exhaustive through 12 assets and uses
512 deterministic checks above that, explicitly marked non-exhaustive.
The separate legacy benchmark catalog defines 60 deterministic recipes
(asset counts 3-6, three covariance types, five replicates each), executed
only when selected. The repository does not claim that all 60 were run.

Each Studio experiment uses one generated instance for all selected methods
and records per-run feasibility, objective gap, runtime, repeatability,
optimality, and QAOA circuit resources where applicable. Standard QAOA uses
an unconstrained mixer, so feasibility is measured rather than guaranteed.
Records include the instance and algorithm configuration in SQLite. The
20-asset, cardinality-10 case requires 184,756 exact candidates and is within
the default candidate limit; larger candidate sets are rejected rather than
misreported as exact.

## Automated checks

Run the unit and integration tests from the project root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

To re-execute the notebook and refresh its saved outputs, use the nbconvert
command in Setup. The application test runs a small seeded Aer job; its output
is a test run, not the recorded notebook experiment.

## Submission demonstration

1. Start the interface and inspect the preserved reference workflow in
   **Portfolio Lab**.
2. In **Experiment Studio**, run a bounded seeded comparison and confirm the
   exact method and selected baselines share one generated instance.
3. Inspect the persisted run in **Run History**, then review QAOA resources
   in **Circuit Explorer** and the explicitly fictional profiles in
   **Hardware Analysis**.
4. Optionally execute a small filtered group from **Benchmark Lab**.
5. Try **Research Assistant** only if a provider is configured; consent is
   required before selected experiment evidence is sent externally.
6. Open **Research Report** for saved notebook measurements. Do not equate
   simulator results or illustrative scores with hardware performance.

Likely judge questions and concise, evidence-based answers are included in the
presentation and submission guide.
