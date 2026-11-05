# AI Research Assistant Architecture Audit

## Current state

There is no AI provider client, AI service, AI API route, environment-based
provider configuration, or assistant UI in the workspace. The current API is
limited to portfolio execution and benchmark recipe/job operations
(`src/webapp.py:276-335`). No simulated or decorative AI response exists.

## Recommended architecture

Implement only after experiment record and API contracts exist:

1. **Typed request modes:** explain result, compare experiments, explain
   algorithm, investigate failure, recommend experiment, draft report, and
   technical Q&A.
2. **Context assembler:** load persisted experiment/dataset/circuit records
   through repository functions; attach stable IDs and metric provenance.
   Never let the model author or recalculate scientific metrics.
3. **Provider interface:** one narrow `generate(messages, model, timeout)`
   interface with provider implementations selected by server configuration.
   Read provider credentials from environment variables or a local secret
   store; never return secrets to the frontend.
4. **Grounding contract:** pass only requested, relevant project data and
   documentation excerpts; require cited experiment IDs/field names in
   explanations. State clearly when records or evidence are missing.
5. **Failure behavior:** report missing provider/configuration, timeout,
   rate-limit, and provider errors explicitly. Do not return a fabricated
   response or label a fallback as AI output.
6. **Data minimization:** do not send provider credentials, raw private
   datasets, or unrelated experiment history. Make external-provider use
   explicit and configurable.
7. **Testing:** test absent provider, provider error/timeout, context
   selection, unsupported request, no matching experiment, and response
   grounding with deterministic fake-provider tests; fake provider is a test
   fixture only, not a product response.

## Preconditions and scope

The highest-priority prerequisite is persistent, typed experiment data with
stable identifiers. Without it, result explanation/comparison would be
unreliable and the assistant could appear to know results it cannot access.
Add the assistant after storage and read-only result/context endpoints; do not
add a model dependency or call a provider as part of this audit.

## Findings

### AI-01 - Requested assistant capability is not implemented

- **File / lines:** No AI module or route; inspect `src/webapp.py:276-335`
  for current route inventory and `src/static/index.html:19-23` for tabs.
- **Evidence:** No AI route, provider abstraction, configuration, or
  assistant tab exists.
- **Expected:** Assistant answers should be grounded in stored experiment and
  circuit context and clearly state when data is missing.
- **Actual:** No AI response is currently available, which is preferable to a
  simulated answer but leaves the requested feature absent.
- **Severity:** Medium (scope gap).
- **Recommended:** Implement after persistence and typed experiment APIs, with
  explicit provider setup and tests.

## Implementation status

The recommendation above is implemented in `src/research_assistant.py`, with
routes in `src/webapp.py` and the Research Assistant workspace in
`src/static/`. The provider is OpenAI-compatible and configured by
`QPU_SENTINEL_AI_API_KEY`, with optional base URL and model settings. There is
no configured provider by default. The API returns an explicit unconfigured
status and does not fabricate a response.

Each request names one completed saved experiment. The context builder
includes its dataset ID, objective/reference, penalty diagnostic, QUBO-check
scope, algorithm configuration, summaries, and selected run metrics; it
excludes raw covariance and sample-count histograms. The endpoint requires
`external_data_consent: true` before making a provider request, and the UI
displays the consent notice. The provider instructions request field-path
citations and explicitly prohibit claims of QPU execution or quantum
advantage.

Automated tests cover unconfigured state, consent, selected-record scoping,
and provider errors/response handling. The real HTTP request path was tested
against a local OpenAI-compatible mock, including authorization-header
transport; no key was sent to an external provider. Therefore hosted-provider
availability, policy behavior, and live answer quality remain unverified.
