# Hardware Suitability Audit

## Current implementation

`src/hardware_suitability.py` defines three `SIMULATED PROFILE` records with
fictional capacities, depth/gate budgets, error inputs, and couplers. The
scorer validates some requirements, checks qubit capacity, depth and gate
budgets, validates error probabilities, checks graph connectivity and direct
coupling coverage, then computes a weighted 0-100 score. The weights and
missing-data neutral score are visible and documented. The current workflow
uses Aer-transpiled depth and two-qubit gate count plus QUBO interactions.

No IBM/provider account, credentials, real backend profile, noise model,
target-aware hardware transpilation, or physical QPU execution exists.

## Findings

### H-01 - Profile and error labels are illustrative, not device information

- **File / lines:** `src/hardware_suitability.py:11-96, 301-337`;
  `src/static/index.html:145-154`.
- **Evidence:** Profile constructors state they are fictional and the API
  response includes a notice. All three profiles are hard-coded teaching
  examples.
- **Expected:** Hardware assessments should be based on actual provider
  target/calibration data or clearly identified illustrative scenarios.
- **Actual:** Current output is an explainable profile-score demonstration;
  it is not device compatibility evidence or hardware benchmarking.
- **Severity:** Low (claim boundary is already disclosed).
- **Recommended:** Preserve the warning and do not rename these profiles as
  real backends.

### H-02 - Circuit metrics are not target-specific

- **File / lines:** `src/qaoa_portfolio.py:63-66, 135-186`;
  `src/webapp.py:125-136`.
- **Evidence:** The circuit is transpiled for `AerSimulator`, then depth and
  two-qubit operations are passed to fictional profiles. No hardware target,
  native-gate basis, layout, or routing pass is used.
- **Expected:** A hardware plan should transpile against an actual backend
  target and report the resulting width, native gate counts, layout, and
  routing.
- **Actual:** Analyzer input is useful for a simulated resource scenario but
  cannot establish hardware suitability.
- **Severity:** Medium.
- **Recommended:** Separate local simulator, noisy simulator, real QPU, and
  illustrative-profile modes. Only populate real-hardware metrics from a
  configured provider and saved job/target metadata.

### H-03 - Scoring weights and thresholds are policy choices

- **File / lines:** `src/hardware_suitability.py:170-288`.
- **Evidence:** Error thresholds (5% two-qubit, 15% readout), budget fractions,
  and weights are constants; score is a weighted combination.
- **Expected:** A recommendation should explain its assumptions and avoid
  implying that a score predicts actual success probability.
- **Actual:** Reasons and weights are exposed, but score calibration has not
  been empirically validated and there is no noise simulation.
- **Severity:** Medium.
- **Recommended:** Keep scores labeled heuristic/illustrative, document
  sensitivity, and add an actual noise-based study before claiming predictive
  value.

### H-04 - Requirements/profile validation permits malformed scalar types

- **File / lines:** `src/hardware_suitability.py:98-106, 136-168`.
- **Evidence:** Checks compare values but do not enforce integer types for
  qubit counts, circuit depth, gate budgets, or profile budgets; boolean values
  can satisfy Python numeric comparisons.
- **Expected:** Public profile and requirement records should reject
  booleans, fractional counts, and non-finite numeric values.
- **Actual:** Some malformed values may produce nonsensical scoring or
  low-level exceptions.
- **Severity:** Low.
- **Recommended:** Add explicit dataclass input validation and boundary tests
  before expanding provider integrations.

## Preserve

Keep the explicit fictional-profile labels, scoring weights, compatibility
reasons, and missing-data disclosures. Never present these scenarios as IBM
hardware data or actual QPU results.
