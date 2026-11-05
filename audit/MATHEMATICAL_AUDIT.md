# Mathematical Audit

## Model and interpretation

The implementation solves a binary subset-selection model:

`f(x) = lambda * x.T @ Sigma @ x - mu.T @ x`, subject to `sum(x) = K`,
with each `x_i` in `{0, 1}`.

This is a discrete, equal-unit-cost selection variant of mean-variance
portfolio optimization. It is not the full continuous-weight Markowitz
allocation problem: selected assets have implicit equal unit holdings, and
there are no prices, transaction costs, budget weights, or continuous
allocation variables. Binary variables encode inclusion; the cardinality
constraint fixes the number of selected assets. Off-diagonal covariance
terms affect risk through pair interactions; correlation is covariance
normalized by the individual volatilities, but the current UI does not display
a correlation matrix.

The mathematical problem and financial inputs are illustrative. No live data
or investment recommendation is present.

## QUBO derivation

For binary variables, `x_i^2 = x_i`. Assuming symmetric covariance,

`lambda * x.T @ Sigma @ x - mu.T @ x`

has diagonal coefficient `lambda * Sigma_ii - mu_i` and upper-triangle
pair coefficient `2 * lambda * Sigma_ij`. Expanding

`A * (sum_i x_i - K)^2`

adds constant `A*K^2`, linear coefficient `A*(1 - 2K)` for each `x_i`, and
pair coefficient `2A`. Thus the implementation's coefficients are:

- `constant = A*K^2`
- `linear_i = lambda*Sigma_ii - mu_i + A*(1 - 2K)`
- `quadratic_ij = 2*lambda*Sigma_ij + 2A` for `i < j`

The implementation stores only the upper triangle of the pair matrix and its
energy evaluator reads only that triangle. This convention is internally
consistent for symmetric covariance matrices.

## Independent numerical check

For the saved four-asset fixture (`lambda=2`, `K=2`, `A=1`), an independent
enumeration verified QUBO energy equals the penalized objective for all 16
bitstrings. Results:

- Linear coefficients: `[-3.04, -3.055, -3.05, -3.025]`
- Upper-triangle pair coefficients in index order:
  `[2.024, 2.016, 2.032, 2.012, 2.02, 2.008]`
- Constant: `4.0`
- Covariance eigenvalues:
  `[0.0090768657, 0.0207278846, 0.0388964382, 0.0662988115]`
- Exact feasible minimum: `0110`, objective approximately `-0.093`
- All 16 identities passed `numpy.isclose`.

The notebook cell 7 independently asserts the same QUBO equality; the existing
test asserts it for the default instance. The existing suite does not perform
randomized small-instance QUBO tests.

## Post-audit penalty diagnostic

`src/portfolio_workflow.py` now reports a conservative certificate. For binary
`x`, the financial objective has the lower bound

`lambda * sum(min(Sigma_ij, 0)) - sum(max(mu_i, 0))`.

Every infeasible cardinality has `(sum(x)-K)^2 >= 1`. If `f*` is the exact
best feasible objective, any penalty strictly greater than
`max(0, f* - lower_bound)` therefore puts all infeasible penalized energies
above `f*`. The diagnostic does not change the supplied penalty. A failed
certificate means the conservative bound could not prove sufficiency; it
does not prove the penalty is actually insufficient.

For the saved four-asset inputs, the lower bound is `-0.44`, the strict
threshold is `0.347`, and the default penalty `1.0` is certified. A value of
`0.1` is flagged and the live UI warns the user. This does not replace the
separate requirement to bound exponential enumeration.

## Input validation audit

`src/portfolio_workflow.py:9-39` rejects empty/blank or duplicate names,
dimension mismatches, non-finite returns/covariances, covariance asymmetry
beyond tolerance, covariance eigenvalues below `-1e-10`, non-integer or
out-of-range cardinality, and negative/non-finite risk aversion.

Negative expected return is not inherently invalid in finance; finite
negative values should not be rejected merely for being negative. Zero
assets are rejected. Risk aversion is constrained nonnegative; that is an
implementation choice that should be documented because a negative value
would reward risk rather than penalize it.

### M-01 - Penalty identity and penalty certification are separate

- **File / lines:** `src/portfolio_workflow.py:85-120, 123-140`;
  `src/webapp.py:37-43`.
- **Evidence at audit baseline:** `build_qubo` required finite positive `A`;
  `verify_qubo` confirmed the exact identity for any such `A`, but did not
  estimate whether infeasible assignments could beat the feasible optimum.
- **Expected:** The system should distinguish algebraic equivalence from a
  valid penalty strength that makes the unconstrained optimum feasible.
- **Actual at audit baseline:** Any positive penalty was accepted with no
  strength diagnostic.
- **Severity:** High.
- **Recommended:** Continue to expose the distinction between "certified"
  and "not certified"; consider exact infeasible extrema only when the
  configured enumeration budget allows it.

**Post-audit status:** A conservative bound and regression tests were added as
described above. Exact penalty adequacy remains unknown when the conservative
bound fails.

### M-02 - Public QUBO helper validates fewer invariants than the workflow

- **File / lines:** `src/portfolio_workflow.py:85-99`.
- **Evidence:** `build_qubo` checks the covariance shape and penalty but does
  not itself validate finite/symmetric/PSD covariance, returns, cardinality,
  or risk aversion. `prepare_portfolio` validates inputs before calling it,
  but direct callers can bypass that validation.
- **Expected:** Public mathematical helpers should either enforce their
  preconditions or clearly have a private/prevalidated contract.
- **Actual:** Direct calls can produce coefficients from invalid inputs or
  fail later with low-level NumPy errors.
- **Severity:** Medium.
- **Recommended:** Reuse shared validation or make the precondition explicit
  in a typed internal API while preserving the existing workflow.

### M-03 - Tolerant symmetry test leaves the exact convention implicit

- **File / lines:** `src/portfolio_workflow.py:24-31, 99-110`.
- **Evidence:** Symmetry is accepted with `atol=1e-10`, but the objective uses
  the full matrix product while QUBO pair coefficients read `covariance[i,j]`
  only. The derivation assumes exact symmetry.
- **Expected:** A tolerated near-symmetric matrix should be handled using an
  explicitly defined symmetric matrix, or the accepted discrepancy should be
  bounded relative to the energy verification tolerance.
- **Actual:** Tiny asymmetry can mean the objective and QUBO use slightly
  different pair coefficients while default `np.isclose` may still pass.
- **Severity:** Low (near-tolerance numerical edge case).
- **Recommended:** Either reject asymmetry more strictly or symmetrize by a
  documented rule before both objective and QUBO construction; add boundary
  tests.

### M-04 - Validation tests do not cover the full stated invalid-input matrix

- **File / lines:** `tests/test_portfolio_workflow.py:43-61`.
- **Evidence:** Current invalid-input tests cover asymmetric covariance,
  non-PSD covariance, and excessive cardinality, but not zero assets,
  non-finite values, mismatched dimensions, duplicate names, invalid penalty,
  or invalid risk-aversion types.
- **Expected:** Each public validation contract should have regression tests.
- **Actual:** Several validation branches have no direct tests.
- **Severity:** Medium.
- **Recommended:** Add table-driven validation tests and include a clear
  decision that negative finite returns are valid data.

### M-05 - Feasible enumeration and QUBO verification have no size guard

- **File / lines:** `src/portfolio_workflow.py:54-84, 123-168`.
- **Evidence:** The exact feasible enumerator scans all `2^N` bitstrings and
  the QUBO verifier scans all `2^N` bitstrings on every `prepare_portfolio`
  call.
- **Expected:** Exhaustive proofs are appropriate for the small instances
  they cover, but production-sized inputs need explicit resource bounds.
- **Actual:** Work grows exponentially even when the feasible set is only
  `C(N,K)`; there is no configured cutoff.
- **Severity:** High.
- **Recommended:** Enumerate feasible subsets directly using combinations
  when exact search is selected; bound QUBO exhaustive verification and state
  when it was performed. Keep exhaustive equivalence tests on small instances.

## Limitations and scientific interpretation

Exact enumeration provides an exact reference only when it completes. The
QAOA samples come from a standard mixer and may be infeasible, so feasibility
rate and the best feasible sample must be reported separately. A QUBO
penalty-based optimum is only a constrained optimum if penalty adequacy is
established. Covariance PSD is a property of the supplied matrix; validation
does not establish that the hypothetical inputs are realistic financial
estimates.

## Current experiment-engine verification scope

The scalable engine reuses the objective
`risk_aversion * x.T @ covariance @ x - expected_returns @ x` and the shared
QUBO builder. It independently computes the exact feasible reference by
enumerating `C(N,K)` combinations, subject to a configured candidate limit.
QUBO identity checks are exhaustive for `N <= 12`; above 12, 512 deterministic
configurations are checked and the result is marked non-exhaustive. The
20-asset, cardinality-10 case evaluates 184,756 exact candidates, within the
250,000 API default.

The saved four-asset fixture's independent 16-configuration calculation and
the notebook's original output remain unchanged. The penalty diagnostic is a
conservative sufficient bound; failure to certify is not proof of an
insufficient penalty. No result from sampled large-instance verification is
described as an exhaustive proof.
