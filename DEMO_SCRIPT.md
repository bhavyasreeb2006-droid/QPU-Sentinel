# Live Demonstration Script

## Before the audience arrives

1. From `C:\QubitForge`, start the local application:

   ```powershell
   .\.venv\Scripts\python.exe -m src.webapp --port 8000
   ```

2. In another PowerShell window, confirm the local server responds:

   ```powershell
   Invoke-RestMethod http://127.0.0.1:8000/api/health
   ```

   Expected status is `ok`, with execution described as local Qiskit Aer.
3. Open <http://127.0.0.1:8000> in the browser. The service is local; it does
   not submit work to a QPU.
4. As a preflight, manually click a workspace tab and run the four-asset
   Portfolio Lab once. The browser automation harness could exercise the
   click handlers and render results but did not deliver native pointer
   clicks. Confirm the manual interactions before the audience arrives.

## Demonstration sequence

1. **Portfolio Lab:** show the four hypothetical assets and K=2. Run the
   configured experiment. Point out the classical reference `0110`, the best
   feasible QAOA sample, feasibility, and the local-simulator notice. The
   validated run used 8,192 final shots and measured 7,068 feasible samples;
   the recorded best feasible objective was `-0.093`.
2. **Circuit Explorer:** show the compiled-circuit resource summary. For the
   saved notebook run, p=2, transpiled depth 15, and 12 two-qubit gates.
3. **Hardware Analysis:** explicitly identify the candidate cards as
   illustrative fictional profiles. Explain that this ranks a circuit
   against sample inputs and does not connect to a device.
4. **Run History:** show the three completed persisted Experiment Studio
   records: two three-asset runs and one 20-asset run. Open a saved result to
   discuss its configuration and measured methods.
5. **Experiment Studio:** show the supported asset sizes and selectable valid
   cardinalities. Avoid starting another run during the release demo; the
   saved records already demonstrate persistence and comparisons.
6. **Benchmark Lab:** explain that recipes run on demand and are not a
   precomputed benchmark suite. Do not launch an uncontrolled batch.
7. **Research Report:** compare the saved notebook output with its exact
   classical reference. Keep it separate from the Studio database results.
8. **Research Assistant:** show “Provider not configured.” Do not present a
   mocked test as a live answer or submit a question without a configured
   provider and explicit consent.
9. End by stating that all quantum execution shown is local Aer simulation;
   there is no physical QPU result, speedup claim, or quantum-advantage claim.
   Stop the server with Ctrl+C.

## If something fails

Do not silently switch to another process on port 8000 or edit the notebook.
Check the health endpoint and the server terminal first. The exact launch
command is in [FINAL_README.md](FINAL_README.md), and verified behavior and
limitations are in [COMPETITION_STATUS.md](COMPETITION_STATUS.md).
