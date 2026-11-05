# QPU Sentinel Submission Demo

## What is included

- `notebooks/qpu_sentinel_qaoa.ipynb` is the primary executable experiment
  with its saved outputs.
- `src/` contains the QAOA implementation, scalable matched experiment engine,
  SQLite persistence, consent-gated research assistant, and browser app.
- `tests/` covers the experiment engine/store/API, assistant, scoring,
  compatibility, exact optimization, and QUBO encoding.
- `presentation/QPU_Sentinel_Presentation.pptx` is the eight-slide Fall Fest
  presentation; `presentation/diagrams/` contains its source diagrams.
- `ARCHITECTURE.md`, `RESULTS.md`, and `requirements.txt` accompany the
  reproducible project.

## Exact demonstration workflow

Open a terminal in this folder. In PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m src.webapp
```

Open `http://127.0.0.1:8000` in a browser. The app opens directly in
**Portfolio Lab**. Use the example portfolio and click **Run Experiment**.
Then use **Experiment Studio** for the separate scalable workflow. Walk
through:

1. The input values and the exact six-portfolio classical ranking.
2. The current-run QAOA output distribution and feasibility rate.
3. The portfolio-composition ring (selected assets, not capital weights), the
   risk/return scatter, and objective gap.
4. Open **Circuit Explorer** for the parameter-bound logical Qiskit circuit,
   gate counts, measurements, and separately measured transpiled metrics.
5. Open **Hardware Analysis** for circuit measurements and the three clearly
   labelled illustrative profiles.
6. Open **Benchmark Lab**, select a small scope such as 3 assets and
   Independent assets, then choose **Generate & run selected cases**. Follow
   the progress indicator; only completed Aer executions populate results.
   The all-filter suite has 60 planned configurations and may take longer.
   Sorting and CSV export work on completed rows.
7. In **Experiment Studio**, run a bounded seeded comparison. Supported asset
   counts are 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, and 20; choose any valid
   cardinality. Exact search is capped at 250,000 candidates by the API.
   The generated instance is shared by exact, greedy, random, annealing, and
   selected QAOA methods; completed records persist in
   `results/experiments.sqlite3`.
8. Open **Run History** to inspect saved experiments and **Research Report**
   for the saved notebook measurements.
9. **Research Assistant** requires `QPU_SENTINEL_AI_API_KEY` and explicit
   consent before sending the selected experiment summary and question to an
   OpenAI-compatible provider. No key is required to run the rest of the app.

Benchmark cases are deterministic synthetic inputs but their runtime,
feasibility, objective gap, circuit depth, and gate counts are measured when
the case actually runs. Do not describe planned recipes as completed results.

The server is local and contacts no quantum hardware. Stop it with Ctrl+C.
For the saved reference experiment, open the notebook and run its cells from
top to bottom. Running it again refreshes outputs and may produce different
shot samples if the random seed or execution settings change.

## Likely judging questions

**Did you execute on an IBM QPU?**  
No. The saved experiment and interface use the local Qiskit Aer simulator.
No hardware job IDs or calibration records exist in this submission.

**Are the three backend profiles actual IBM devices?**  
No. They are explicitly labelled fictional simulated profiles, with
illustrative capacities, couplers, and error inputs. Their scores demonstrate
the analyzer only; they are not device benchmarks.

**Did QAOA outperform the classical solver?**  
No. The exact classical search is the reference for this small problem. In
the saved simulator run, the best feasible QAOA sample matched the classical
optimum; that is not evidence of speedup or quantum advantage.

**Are the 60 benchmark results already available?**  
No. The app defines 60 deterministic configurations. Benchmark Lab generates
and executes selected cases on local Aer; it reports only cases that have
actually completed. The saved four-asset example has six feasible portfolios.

**Does Experiment Studio have a result database?**  
Yes. Completed Studio jobs, specifications, generated instances, and metrics
are stored in SQLite. The repository includes a three-asset comparison and a
bounded 20-asset pilot; these two runs are not a broad statistical benchmark.

**Is the research assistant connected to a live provider?**  
Not by default. It requires environment configuration and explicit consent.
The provider request was tested with a local mock; a hosted model response has
not been tested.

**Does the donut chart show investment weights?**  
No. It counts which binary assets are selected. Allocation weights are not
part of the portfolio model.

**What is the next credible hardware step?**  
Choose a real backend, transpile to its target, collect backend/job and
calibration metadata, and evaluate repeated noise-aware runs against fair
classical baselines. Do not mix those future results with this simulator run.
