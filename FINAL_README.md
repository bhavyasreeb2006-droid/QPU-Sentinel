# QPU Sentinel — Competition Handover

QPU Sentinel is a local QAOA portfolio experiment and research interface. The
preserved notebook, Python application, and existing PowerPoint are separate
deliverables. This handover does not replace the notebook or rebuild the deck.

## Requirements and launch

The verified environment is Windows, Python 3.12.10, Qiskit 2.6.1, and Qiskit
Aer 0.18.2. From the project root, launch the local application with:

```powershell
.\.venv\Scripts\python.exe -m src.webapp --port 8000
```

Open <http://127.0.0.1:8000>. The server binds to localhost. If setting up a
fresh environment, use:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Stop the server with Ctrl+C in its terminal. Do not stop an arbitrary process
if the port is occupied; first identify the listener and verify which
application owns it.

## Deliverables and records

- `notebooks/qpu_sentinel_qaoa.ipynb` is the validated four-asset notebook
  with its saved outputs. The root and submission copies were verified
  byte-identical; this release did not edit either copy.
- `src/` contains the application and actual QAOA implementation.
- `results/experiments.sqlite3` contains the three reconciled Experiment
  Studio records. A pre-release SQLite backup is in
  `results/release-backups/`.
- `submission/` contains its own application, notebook, and SQLite copy. Its
  pre-release database backup is in
  `submission/results/release-backups/`.
- `presentation/QPU_Sentinel_Presentation.pptx` remains a separate existing
  deliverable and was not rebuilt.

See [COMPETITION_STATUS.md](COMPETITION_STATUS.md) for verified measurements
and limits, [DEMO_SCRIPT.md](DEMO_SCRIPT.md) for the live sequence,
[JUDGE_QA.md](JUDGE_QA.md) for technical answers, and
[RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) for the final checks.

## Scope and limitations

All reported quantum runs use local Qiskit Aer simulation; no physical QPU was
used and no quantum advantage or speedup is claimed. The hardware-analysis
profiles are explicitly illustrative fictional profiles, not real backends.
The AI assistant is implemented but has no provider configured in the
verified environment; its status is shown in the UI, and it requires explicit
consent before sending saved experiment data to a configured provider.

The portfolios use synthetic/hypothetical data and are not investment advice.
The assistant's hosted-provider behavior was not verified. Do not present
local simulation, fictional profiles, or mocked-provider tests as hardware
or hosted-service results.

## Validation commands

Run from the project root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q src tests
```

Both commands passed during this release check. Do not execute the notebook
with an in-place command during the demonstration; its saved outputs are
preserved as part of the deliverable.
