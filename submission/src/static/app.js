const $ = (selector) => document.querySelector(selector);
const SVG_NS = "http://www.w3.org/2000/svg";
const JADE = "#74FFED";
const PINK = "#FEB1D1";
let benchmarkRows = [];
let sortKey = "case_id";
let sortAscending = true;
let assistantConfigured = false;

function svgElement(name, attributes = {}, text = null) {
  const element = document.createElementNS(SVG_NS, name);
  Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, value));
  if (text !== null) element.textContent = text;
  return element;
}

function setNotice(text, error = false) {
  const notice = $("#run-notice");
  notice.textContent = text;
  notice.classList.toggle("error", error);
  notice.classList.remove("hidden");
}

function setTab(tabName, focus = false) {
  document.querySelectorAll(".tab").forEach((tab) => {
    const active = tab.dataset.tab === tabName;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-selected", String(active));
    tab.tabIndex = active ? 0 : -1;
    if (active && focus) tab.focus();
  });
  document.querySelectorAll(".tab-workspace").forEach((workspace) => {
    workspace.hidden = workspace.id !== `workspace-${tabName}`;
  });
  if (tabName === "history") refreshExperimentHistory();
  if (tabName === "assistant") refreshAssistantExperiments();
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

function renderAssets(assets, returns) {
  const editor = $("#asset-editor");
  editor.replaceChildren();
  assets.forEach((asset, index) => {
    const row = document.createElement("div");
    row.className = "asset-row";
    row.innerHTML = `<label>Asset ${index + 1}<input data-asset="${index}" aria-label="Asset ${index + 1} name" value="${escapeHtml(asset)}"></label>
      <label>Expected return<input data-return="${index}" aria-label="Asset ${index + 1} expected return" type="number" step="0.01" value="${returns[index]}"></label>`;
    editor.append(row);
  });
}

async function loadDefaults() {
  const response = await fetch("/api/defaults");
  if (!response.ok) throw new Error("Could not load example inputs.");
  const defaults = await response.json();
  renderAssets(defaults.assets, defaults.expected_returns);
  $("#covariance").value = JSON.stringify(defaults.covariance, null, 2);
  ["cardinality", "risk_aversion", "penalty", "depth", "optimizer_shots", "final_shots", "max_iterations", "seed"]
    .forEach((key) => { $(`#${key.replaceAll("_", "-")}`).value = defaults[key]; });
}

function numberValue(selector, label) {
  const value = Number($(selector).value);
  if (!Number.isFinite(value)) throw new Error(`${label} must be a finite number.`);
  return value;
}

function collectInputs() {
  const assets = [...document.querySelectorAll("[data-asset]")].map((input) => input.value.trim());
  const expectedReturns = [...document.querySelectorAll("[data-return]")].map((input) => Number(input.value));
  if (assets.some((asset) => !asset) || expectedReturns.some((value) => !Number.isFinite(value))) {
    throw new Error("Every asset needs a name and a finite expected return.");
  }
  let covariance;
  try { covariance = JSON.parse($("#covariance").value); } catch { throw new Error("Covariance must be valid JSON."); }
  return {
    assets,
    expected_returns: expectedReturns,
    covariance,
    cardinality: numberValue("#cardinality", "Assets to select"),
    risk_aversion: numberValue("#risk-aversion", "Risk aversion"),
    penalty: numberValue("#penalty", "QUBO penalty"),
    depth: numberValue("#depth", "QAOA depth"),
    optimizer_shots: numberValue("#optimizer-shots", "Optimizer shots"),
    final_shots: numberValue("#final-shots", "Final shots"),
    max_iterations: numberValue("#max-iterations", "Optimizer iterations"),
    seed: numberValue("#seed", "Random seed"),
  };
}

function makeCell(value, className = "") {
  const cell = document.createElement("td");
  cell.textContent = value;
  if (className) cell.className = className;
  return cell;
}

function renderSummary(target, cards) {
  const container = $(target);
  container.replaceChildren(...cards.map(([label, value, note]) => {
    const card = document.createElement("div");
    card.className = "summary-card";
    const heading = document.createElement("span");
    heading.textContent = label;
    const strong = document.createElement("strong");
    strong.textContent = value;
    const small = document.createElement("small");
    small.textContent = note;
    card.append(heading, strong, small);
    return card;
  }));
}

function renderDonut(assets, best, cardinality) {
  const chart = $("#allocation-chart");
  chart.replaceChildren();
  const selected = new Set(best.Selection.split("").flatMap((bit, index) => bit === "1" ? [index] : []));
  const center = 110;
  const outer = 83;
  const inner = 61;
  const segment = 360 / assets.length;
  const polar = (radius, angle) => {
    const radians = (angle - 90) * Math.PI / 180;
    return [center + radius * Math.cos(radians), center + radius * Math.sin(radians)];
  };
  assets.forEach((asset, index) => {
    const start = index * segment + 2;
    const end = (index + 1) * segment - 2;
    const a = polar(outer, start + 90);
    const b = polar(outer, end + 90);
    const c = polar(inner, end + 90);
    const d = polar(inner, start + 90);
    const color = selected.has(index) ? JADE : PINK;
    const path = svgElement("path", {
      d: `M ${a[0]} ${a[1]} A ${outer} ${outer} 0 0 1 ${b[0]} ${b[1]} L ${c[0]} ${c[1]} A ${inner} ${inner} 0 0 0 ${d[0]} ${d[1]} Z`,
      fill: color, opacity: selected.has(index) ? ".92" : ".34", stroke: "#171F44", "stroke-width": "2",
    });
    path.append(svgElement("title", {}, `${asset}: ${selected.has(index) ? "selected" : "not selected"}`));
    chart.append(path);
  });
  chart.append(
    svgElement("text", { x: center, y: center - 3, class: "donut-center-value" }, `${cardinality}/${assets.length}`),
    svgElement("text", { x: center, y: center + 15, class: "donut-center-label" }, "SELECTED"),
  );
  const legend = $("#allocation-legend");
  legend.replaceChildren();
  assets.forEach((asset, index) => {
    const row = document.createElement("div");
    row.className = "legend-item";
    row.innerHTML = `<span class="legend-swatch${selected.has(index) ? "" : " pink-swatch"}"></span><span>${escapeHtml(asset)}</span><span class="legend-value">${selected.has(index) ? "IN" : "OUT"}</span>`;
    legend.append(row);
  });
}

function renderScatter(results, best) {
  const chart = $("#risk-return-chart");
  chart.replaceChildren();
  const width = 520;
  const height = 285;
  const margin = { left: 52, right: 20, top: 18, bottom: 43 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const variances = results.map((row) => Number(row["Portfolio Variance"]));
  const returns = results.map((row) => Number(row["Expected Return"]));
  const xMin = Math.min(...variances), xMax = Math.max(...variances);
  const yMin = Math.min(...returns), yMax = Math.max(...returns);
  const xScale = (value) => margin.left + ((value - xMin) / (xMax - xMin || 1)) * plotWidth;
  const yScale = (value) => margin.top + plotHeight - ((value - yMin) / (yMax - yMin || 1)) * plotHeight;
  for (let tick = 0; tick <= 4; tick += 1) {
    const y = margin.top + (plotHeight * tick) / 4;
    chart.append(svgElement("line", { x1: margin.left, y1: y, x2: width - margin.right, y2: y, class: "chart-grid-line" }));
    chart.append(svgElement("text", { x: margin.left - 7, y: y + 3, class: "chart-tick", "text-anchor": "end" }, (yMax - ((yMax - yMin) * tick) / 4).toFixed(2)));
  }
  chart.append(
    svgElement("line", { x1: margin.left, y1: margin.top, x2: margin.left, y2: height - margin.bottom, class: "chart-axis" }),
    svgElement("line", { x1: margin.left, y1: height - margin.bottom, x2: width - margin.right, y2: height - margin.bottom, class: "chart-axis" }),
    svgElement("text", { x: margin.left + plotWidth / 2, y: height - 7, class: "chart-label", "text-anchor": "middle" }, "Portfolio variance"),
    svgElement("text", { x: 13, y: margin.top + plotHeight / 2, class: "chart-label", "text-anchor": "middle", transform: `rotate(-90 13 ${margin.top + plotHeight / 2})` }, "Expected return"),
  );
  results.forEach((row) => {
    const x = xScale(Number(row["Portfolio Variance"]));
    const y = yScale(Number(row["Expected Return"]));
    const isBest = row.Selection === best.Selection;
    const point = svgElement("circle", { cx: x, cy: y, r: isBest ? 7 : 5, class: `chart-point${isBest ? " optimum" : ""}` });
    point.append(svgElement("title", {}, `${row.Selection}: return ${Number(row["Expected Return"]).toFixed(3)}, variance ${Number(row["Portfolio Variance"]).toFixed(4)}`));
    chart.append(point, svgElement("text", { x: x + 7, y: y - 6, class: "chart-point-label" }, row.Selection));
  });
  for (let tick = 0; tick <= 4; tick += 1) {
    const x = margin.left + (plotWidth * tick) / 4;
    chart.append(svgElement("text", { x, y: height - margin.bottom + 14, class: "chart-tick", "text-anchor": "middle" }, (xMin + ((xMax - xMin) * tick) / 4).toFixed(3)));
  }
}

function renderComparison(metrics) {
  const chart = $("#comparison-chart");
  chart.replaceChildren();
  const rows = [
    { label: "Classical exact", value: Number(metrics.exact_objective), y: 58, color: "comparison-classical", selection: metrics.exact_selection },
    { label: "Best feasible QAOA", value: Number(metrics.best_feasible_objective), y: 112, color: "comparison-qaoa", selection: metrics.best_feasible_selection },
  ];
  const values = rows.map((row) => row.value);
  const min = Math.min(...values), span = Math.max(...values) - min || Math.max(Math.abs(min) * .1, .01);
  const left = 185, right = 700;
  rows.forEach((row) => {
    const x = left + ((row.value - min) / span) * (right - left);
    chart.append(
      svgElement("text", { x: 7, y: row.y + 3, class: "comparison-label" }, row.label),
      svgElement("line", { x1: left, y1: row.y, x2: right, y2: row.y, class: "comparison-track" }),
      svgElement("line", { x1: left, y1: row.y, x2: x, y2: row.y, class: row.color }),
      svgElement("circle", { cx: x, cy: row.y, r: 7, fill: row.color === "comparison-classical" ? JADE : "#171F44", stroke: row.color === "comparison-classical" ? JADE : PINK, "stroke-width": "3" }),
      svgElement("text", { x: right + 8, y: row.y + 3, class: "comparison-value" }, `${row.value.toFixed(4)} · ${row.selection}`),
    );
  });
  const gap = Number(metrics.best_feasible_objective) - Number(metrics.exact_objective);
  $("#comparison-footnote").textContent = `Best-feasible objective gap: ${gap >= 0 ? "+" : ""}${gap.toFixed(6)}. No speedup or quantum advantage is inferred.`;
}

function renderPortfolio(result) {
  const classical = result.classical_results;
  const metrics = result.qaoa_metrics;
  const exact = classical[0];
  const gap = Number(metrics.best_feasible_objective) - Number(metrics.exact_objective);
  renderSummary("#summary-cards", [
    ["Classical optimum", exact.Selection, exact.Assets.join(" + ")],
    ["QAOA best feasible", metrics.best_feasible_selection, `Objective ${Number(metrics.best_feasible_objective).toFixed(4)}`],
    ["Objective gap", gap.toFixed(6), "QAOA minus exact"],
    ["Feasibility", `${(Number(metrics.feasibility_rate) * 100).toFixed(2)}%`, `${Number(metrics.feasible_shots).toLocaleString()} / ${Number(metrics.final_shots).toLocaleString()} shots`],
  ]);
  $("#portfolio-state").classList.add("hidden");
  $("#portfolio-results").classList.remove("hidden");
  $("#classical-count").textContent = `(${classical.length} feasible)`;
  $("#qaoa-count-label").textContent = `(${result.qaoa_results.length} observed bitstrings)`;
  $("#classical-rows").replaceChildren(...classical.map((row) => {
    const tr = document.createElement("tr");
    if (row.Selection === exact.Selection) tr.className = "best-row";
    tr.append(makeCell(row.Selection, "bitstring"), makeCell(row.Assets.join(", ")),
      makeCell(Number(row["Expected Return"]).toFixed(4)),
      makeCell(Number(row["Portfolio Variance"]).toFixed(5)),
      makeCell(Number(row.Objective).toFixed(5)));
    return tr;
  }));
  $("#qaoa-rows").replaceChildren(...result.qaoa_results.map((row) => {
    const tr = document.createElement("tr");
    tr.append(makeCell(row.Selection, "bitstring"), makeCell(Number(row.Shots).toLocaleString()),
      makeCell(`${(Number(row.Probability) * 100).toFixed(2)}%`),
      makeCell(row.Feasible ? "Yes" : "No", row.Feasible ? "feasible-yes" : "feasible-no"),
      makeCell(Number(row.Objective).toFixed(5)));
    return tr;
  }));
  renderDonut(result.input_summary.assets, exact, result.input_summary.cardinality);
  renderScatter(classical, exact);
  renderComparison(metrics);
  renderCircuit(result.circuit_explorer, metrics);
  renderHardware(result.hardware_analysis, metrics, result.input_summary.assets.length);
  setNotice(result.execution_notice);
}

function renderCircuit(explorer, metrics) {
  $("#circuit-state").classList.add("hidden");
  $("#circuit-results").classList.remove("hidden");
  $("#circuit-run-label").textContent = `${explorer.qubits.length} qubits · optimized parameters`;
  $("#measurement-label").textContent = `${explorer.measurement_count} measurements · ${explorer.logical_depth} logical depth`;
  renderSummary("#circuit-summary", [
    ["Qubits", String(explorer.qubits.length), "Portfolio variables"],
    ["Logical depth", String(explorer.logical_depth), "Before transpilation"],
    ["Transpiled depth", String(metrics.circuit_depth), "Measured on Aer basis"],
    ["Two-qubit gates", String(metrics.two_qubit_gates), "After transpilation"],
  ]);
  const chart = $("#circuit-chart");
  chart.replaceChildren();
  const y0 = 45, yStep = 45, x0 = 150, xStep = 42;
  const operations = explorer.operations;
  const width = Math.max(760, x0 + (operations.length + 1) * xStep);
  const height = y0 * 2 + (explorer.qubits.length - 1) * yStep;
  chart.setAttribute("viewBox", `0 0 ${width} ${height}`);
  explorer.qubits.forEach((qubit) => {
    const y = y0 + qubit.index * yStep;
    chart.append(
      svgElement("text", { x: 8, y: y + 3, class: "circuit-qubit-label" }, `q${qubit.index} · ${qubit.label}`),
      svgElement("line", { x1: x0 - 14, y1: y, x2: width - 18, y2: y, class: "circuit-wire" }),
    );
  });
  operations.forEach((operation, index) => {
    const x = x0 + index * xStep;
    const ys = operation.qubits.map((qubit) => y0 + qubit * yStep);
    if (ys.length > 1) {
      chart.append(svgElement("line", { x1: x, y1: Math.min(...ys), x2: x, y2: Math.max(...ys), class: "circuit-link" }));
      ys.forEach((y) => chart.append(svgElement("circle", { cx: x, cy: y, r: 3, fill: PINK })));
      const gate = operation.gate.toUpperCase();
      const y = (Math.min(...ys) + Math.max(...ys)) / 2;
      chart.append(
        svgElement("rect", { x: x - 19, y: y - 11, width: 38, height: 22, class: "circuit-gate" }),
        svgElement("text", { x, y, class: "circuit-gate-text" }, gate),
      );
      return;
    }
    const gate = operation.gate.toUpperCase();
    const label = gate === "MEASURE" ? "M" : gate;
    ys.forEach((y) => {
      const klass = gate === "RX" ? "circuit-gate-mixer" : gate === "MEASURE" ? "circuit-measure" : "circuit-gate";
      const title = `${gate} on q${operation.qubits[0]}${operation.parameters.length ? ` · ${operation.parameters.map((value) => Number.isFinite(Number(value)) ? Number(value).toFixed(3) : value).join(", ")}` : ""}`;
      const rect = svgElement("rect", { x: x - 15, y: y - 11, width: 30, height: 22, class: klass });
      chart.append(
        rect,
        svgElement("text", { x, y, class: `circuit-gate-text${gate === "RX" ? " pink-text" : ""}` }, label),
      );
      rect.append(svgElement("title", {}, title));
    });
  });
  const gateCounts = $("#gate-counts");
  gateCounts.replaceChildren();
  Object.entries(explorer.gate_counts).sort(([a], [b]) => a.localeCompare(b)).forEach(([gate, count]) => {
    const item = document.createElement("span");
    item.className = "gate-count";
    item.innerHTML = `${escapeHtml(gate.toUpperCase())}<strong>${Number(count)}</strong>`;
    gateCounts.append(item);
  });
  const measure = document.createElement("span");
  measure.className = "gate-count";
  measure.innerHTML = `MEASURE<strong>${Number(explorer.measurement_count)}</strong>`;
  gateCounts.append(measure);
}

function renderHardware(analysis, metrics, qubitCount) {
  $("#hardware-state").classList.add("hidden");
  $("#hardware-results").classList.remove("hidden");
  renderSummary("#measured-circuit-indicator", [
    ["QAOA depth p", String(metrics.depth_p), "Algorithm layers"],
    ["Circuit qubits", String(qubitCount), "Measured input size"],
    ["Transpiled depth", String(metrics.circuit_depth), "Aer transpilation"],
    ["Two-qubit gates", String(metrics.two_qubit_gates), `${Number(metrics.final_shots).toLocaleString()} Aer shots`],
  ]);
  $("#recommendation").textContent = analysis.recommendation;
  $("#backend-cards").replaceChildren(...analysis.ranked_profiles.map((profile) => {
    const card = document.createElement("article");
    card.className = "backend-card";
    const head = document.createElement("div");
    head.className = "backend-head";
    const title = document.createElement("strong");
    title.textContent = `${profile.name} · SIMULATED PROFILE · ${profile.compatible ? "Compatible" : "Not compatible"}`;
    const score = document.createElement("span");
    score.className = "backend-score";
    score.textContent = `${Number(profile.score).toFixed(1)} / 100`;
    head.append(title, score);
    const meta = document.createElement("div");
    meta.className = "backend-meta";
    Object.entries(profile.component_scores).forEach(([key, value]) => {
      const item = document.createElement("span");
      item.textContent = `${key.replaceAll("_", " ")} ${Number(value).toFixed(0)}`;
      meta.append(item);
    });
    const reasons = document.createElement("ul");
    reasons.className = "backend-reasons";
    profile.reasons.forEach((reason) => {
      const item = document.createElement("li");
      item.textContent = reason;
      reasons.append(item);
    });
    card.append(head, meta, reasons);
    return card;
  }));
}

async function resetExperiment() {
  try {
    await loadDefaults();
    $("#portfolio-results").classList.add("hidden");
    $("#portfolio-state").classList.remove("hidden");
    $("#portfolio-state").querySelector("strong").textContent = "No experiment run";
    $("#portfolio-state").querySelector("span").textContent = "Run the configured portfolio to calculate and display measured results.";
    $("#run-notice").classList.add("hidden");
    $("#circuit-results").classList.add("hidden");
    $("#circuit-state").classList.remove("hidden");
    $("#circuit-run-label").textContent = "No circuit generated";
    $("#hardware-results").classList.add("hidden");
    $("#hardware-state").classList.remove("hidden");
  } catch (error) {
    setNotice(error.message, true);
  }
}

async function runExperiment() {
  const button = $("#run");
  button.disabled = true;
  button.querySelector("span").textContent = "Running Aer…";
  $("#portfolio-state").classList.remove("hidden");
  $("#portfolio-state").querySelector("strong").textContent = "Experiment running";
  $("#portfolio-state").querySelector("span").textContent = "Classical search, QUBO verification and QAOA simulation are in progress.";
  $("#portfolio-results").classList.add("hidden");
  $("#run-notice").classList.add("hidden");
  try {
    const response = await fetch("/api/run", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(collectInputs()),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "The experiment did not complete.");
    renderPortfolio(result);
    $("#portfolio-state").classList.add("hidden");
  } catch (error) {
    $("#portfolio-state").querySelector("strong").textContent = "Experiment failed";
    $("#portfolio-state").querySelector("span").textContent = error.message;
    setNotice(error.message, true);
  } finally {
    button.disabled = false;
    button.querySelector("span").textContent = "Run Experiment";
  }
}

function renderBenchmarkCharts(rows) {
  const groups = [...new Set(rows.map((row) => row.problem_label))];
  const drawBars = (selector, key, formatter, suffix) => {
    const chart = $(selector);
    chart.replaceChildren();
    const values = groups.map((group) => {
      const sameType = rows.filter((row) => row.problem_label === group);
      return sameType.reduce((sum, row) => sum + Number(row[key]), 0) / sameType.length;
    });
    const max = Math.max(...values.map(Math.abs), 1e-12);
    groups.forEach((group, index) => {
      const y = 35 + index * 54;
      const width = Math.max(2, Math.abs(values[index]) / max * 250);
      chart.append(
        svgElement("text", { x: 4, y: y + 4, class: "chart-label" }, group),
        svgElement("rect", { x: 205, y: y - 9, width, height: 16, rx: 3, fill: index === 1 ? PINK : JADE, opacity: ".8" }),
        svgElement("text", { x: 465, y: y + 4, class: "chart-label" }, `${formatter(values[index])}${suffix}`),
      );
    });
  };
  drawBars("#benchmark-gap-chart", "objective_gap_percent", (value) => value.toFixed(2), "%");
  drawBars("#benchmark-feasibility-chart", "feasibility_rate", (value) => (value * 100).toFixed(1), "%");
}

function visibleSortedBenchmarkRows() {
  return [...benchmarkRows].sort((a, b) => {
    const left = a[sortKey], right = b[sortKey];
    const order = typeof left === "number" ? left - right : String(left).localeCompare(String(right));
    return sortAscending ? order : -order;
  });
}

function renderBenchmarkRows() {
  $("#benchmark-rows").replaceChildren(...visibleSortedBenchmarkRows().map((row) => {
    const tr = document.createElement("tr");
    tr.append(
      makeCell(row.case_id, "bitstring"),
      makeCell(String(row.asset_count)),
      makeCell(row.problem_label),
      makeCell(`${Number(row.objective_gap).toFixed(5)} (${Number(row.objective_gap_percent).toFixed(2)}%)`),
      makeCell(row.penalty_sufficiency_guaranteed ? "Bound passes" : "Not certified"),
      makeCell(`${(Number(row.feasibility_rate) * 100).toFixed(1)}%`, "feasible-yes"),
      makeCell(`${Number(row.runtime_seconds).toFixed(2)} s`),
      makeCell(String(row.circuit_depth)),
      makeCell(String(row.two_qubit_gates)),
    );
    return tr;
  }));
}

function renderBenchmarkResults(rows) {
  benchmarkRows = rows;
  $("#benchmark-state").classList.add("hidden");
  $("#benchmark-results").classList.remove("hidden");
  $("#benchmark-export").disabled = rows.length === 0;
  $("#benchmark-row-count").textContent = `${rows.length} executed · Aer`;
  const average = (key) => rows.reduce((sum, row) => sum + Number(row[key]), 0) / rows.length;
  renderSummary("#benchmark-summary", [
    ["Executed cases", String(rows.length), "Generated and run"],
    ["Mean objective gap", `${average("objective_gap_percent").toFixed(2)}%`, "QAOA minus exact · relative"],
    ["Mean feasibility", `${(average("feasibility_rate") * 100).toFixed(1)}%`, "Measured shots"],
    ["Mean runtime", `${average("runtime_seconds").toFixed(2)} s`, "Per case · local machine"],
  ]);
  renderBenchmarkCharts(rows);
  renderBenchmarkRows();
}

async function runBenchmark() {
  const button = $("#benchmark-run");
  button.disabled = true;
  button.textContent = "Starting benchmark…";
  $("#benchmark-state").classList.remove("hidden");
  $("#benchmark-state").querySelector("strong").textContent = "Benchmark running";
  $("#benchmark-state").querySelector("span").textContent = "Generating and executing selected synthetic cases on local Aer.";
  $("#benchmark-results").classList.add("hidden");
  $("#benchmark-progress-wrap").classList.remove("hidden");
  $("#benchmark-progress").value = 0;
  try {
    const start = await fetch("/api/benchmark/run", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ asset_count: $("#benchmark-assets").value, problem_type: $("#benchmark-type").value }),
    });
    const job = await start.json();
    if (!start.ok) throw new Error(job.error || "Could not start benchmark.");
    $("#benchmark-progress").max = Number(job.total);
    while (true) {
      await new Promise((resolve) => setTimeout(resolve, 350));
      const response = await fetch(`/api/benchmark/jobs?id=${encodeURIComponent(job.job_id)}`);
      const status = await response.json();
      if (!response.ok) throw new Error(status.error || "Could not read benchmark progress.");
      const complete = Number(status.completed);
      const total = Number(status.total);
      $("#benchmark-progress").value = complete;
      $("#benchmark-progress-count").textContent = `${complete} / ${total}`;
      $("#benchmark-progress-text").textContent = status.status === "completed" ? "Benchmark complete" : "Generating and measuring cases…";
      if (status.status === "failed") {
        if (status.results?.length) renderBenchmarkResults(status.results);
        throw new Error(status.error || "Benchmark failed.");
      }
      if (status.status === "completed") {
        renderBenchmarkResults(status.results);
        $("#benchmark-plan").textContent = `${total} cases executed`;
        break;
      }
    }
  } catch (error) {
    $("#benchmark-state").querySelector("strong").textContent = "Benchmark failed";
    $("#benchmark-state").querySelector("span").textContent = error.message;
    $("#benchmark-plan").textContent = "Run incomplete";
  } finally {
    button.disabled = false;
    button.textContent = "Generate & run selected cases";
  }
}

function exportBenchmarkCsv() {
  const headers = ["case_id", "asset_count", "problem_label", "penalty_sufficiency_guaranteed", "required_penalty_exclusive", "exact_objective", "qaoa_objective", "objective_gap", "objective_gap_percent", "feasibility_rate", "runtime_seconds", "circuit_depth", "two_qubit_gates", "execution"];
  const lines = [headers.join(","), ...benchmarkRows.map((row) => headers.map((key) => {
    const value = String(row[key] ?? "");
    return `"${value.replaceAll('"', '""')}"`;
  }).join(","))];
  const blob = new Blob([lines.join("\r\n")], { type: "text/csv" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "qpu-sentinel-benchmark.csv";
  document.body.append(link);
  link.click();
  const objectUrl = link.href;
  link.remove();
  setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

function formatMetric(value, digits = 5) {
  return value === null || value === undefined ? "N/A" : Number(value).toFixed(digits);
}

function renderExperimentRecord(record) {
  const result = record.result;
  const exact = result.exact_reference;
  const qaoa = result.runs.filter((run) => run.algorithm === "qaoa");
  renderSummary("#experiment-summary", [
    ["Exact feasible optimum", exact.selection, `Objective ${formatMetric(exact.objective)}`],
    ["Instance", `${record.asset_count} assets · K=${record.cardinality}`, result.instance.covariance_structure],
    ["QUBO checks", `${result.qubo_validation.checked_configurations.toLocaleString()} / ${result.qubo_validation.total_configurations.toLocaleString()}`, result.qubo_validation.exhaustive ? "Exhaustive identity check" : "Seeded sample checks"],
    ["Penalty certificate", result.penalty_diagnostic.certified_sufficient ? "Certified" : "Not certified", `Strict threshold ${formatMetric(result.penalty_diagnostic.strict_sufficient_threshold, 4)}`],
  ]);
  $("#experiment-state").classList.add("hidden");
  $("#experiment-result").classList.remove("hidden");
  $("#experiment-id-label").textContent = `${record.experiment_id} · ${record.status}`;
  $("#experiment-summary-rows").replaceChildren(...result.summaries.map((summary) => {
    const row = document.createElement("tr");
    row.append(
      makeCell(summary.algorithm),
      makeCell(String(summary.runs)),
      makeCell(formatMetric(summary.mean_objective)),
      makeCell(formatMetric(summary.mean_objective_gap)),
      makeCell(`${(Number(summary.feasibility_rate) * 100).toFixed(1)}%`),
      makeCell(`${(Number(summary.optimal_run_rate) * 100).toFixed(1)}%`),
      makeCell(`${(Number(summary.selection_repeatability) * 100).toFixed(1)}%`),
      makeCell(`${Number(summary.mean_runtime_seconds).toFixed(3)} s`),
    );
    if (summary.algorithm === "exact") row.className = "best-row";
    return row;
  }));
  $("#experiment-run-rows").replaceChildren(...result.runs.map((run) => {
    const row = document.createElement("tr");
    row.append(
      makeCell(run.algorithm),
      makeCell(String(run.seed)),
      makeCell(run.selection ?? "No feasible sample", "bitstring"),
      makeCell(formatMetric(run.objective)),
      makeCell(formatMetric(run.objective_gap)),
      makeCell(run.feasible ? "Yes" : "No", run.feasible ? "feasible-yes" : "feasible-no"),
      makeCell(`${Number(run.runtime_seconds).toFixed(3)} s`),
      makeCell(run.circuit_depth === undefined ? "—" : String(run.circuit_depth)),
      makeCell(run.two_qubit_gates === undefined ? "—" : String(run.two_qubit_gates)),
    );
    return row;
  }));
  $("#experiment-run").dataset.lastExperimentId = record.experiment_id;
  if (qaoa.length) {
    $("#experiment-id-label").textContent += ` · QAOA: ${qaoa.length} sampled run(s), local Aer`;
  }
}

async function loadExperimentRecord(experimentId) {
  const response = await fetch(`/api/experiments/${encodeURIComponent(experimentId)}`);
  const record = await response.json();
  if (!response.ok) throw new Error(record.error || "Could not load the saved experiment.");
  if (record.status !== "completed") throw new Error(record.error || `Experiment status: ${record.status}.`);
  renderExperimentRecord(record);
}

async function refreshExperimentHistory() {
  const state = $("#history-state");
  state.classList.remove("hidden");
  state.querySelector("strong").textContent = "Loading saved runs";
  state.querySelector("span").textContent = "Reading local SQLite experiment records.";
  $("#history-panel").classList.add("hidden");
  try {
    const response = await fetch("/api/experiments?limit=100");
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not load saved runs.");
    const experiments = data.experiments;
    if (!experiments.length) {
      state.querySelector("strong").textContent = "No saved experiments";
      state.querySelector("span").textContent = "Completed and failed experiments will appear here.";
      return;
    }
    $("#history-rows").replaceChildren(...experiments.map((experiment) => {
      const row = document.createElement("tr");
      row.append(
        makeCell(experiment.experiment_id.slice(0, 12), "bitstring"),
        makeCell(experiment.status),
        makeCell(String(experiment.asset_count)),
        makeCell(String(experiment.cardinality)),
        makeCell(String(experiment.seed)),
        makeCell(experiment.specification.algorithms.join(", ")),
        makeCell(new Date(experiment.created_at).toLocaleString()),
      );
      const action = document.createElement("td");
      const button = document.createElement("button");
      button.className = "text-button";
      button.type = "button";
      button.textContent = experiment.status === "completed" ? "Open result" : "View status";
      button.addEventListener("click", async () => {
        try {
          setTab("experiments");
          await loadExperimentRecord(experiment.experiment_id);
        } catch (error) {
          state.querySelector("strong").textContent = "Could not open experiment";
          state.querySelector("span").textContent = error.message;
          state.classList.remove("hidden");
        }
      });
      action.append(button);
      row.append(action);
      return row;
    }));
    state.classList.add("hidden");
    $("#history-panel").classList.remove("hidden");
  } catch (error) {
    state.querySelector("strong").textContent = "History unavailable";
    state.querySelector("span").textContent = error.message;
  }
}

async function runScalabilityExperiment() {
  const button = $("#experiment-run");
  const state = $("#experiment-state");
  const setState = (title, message) => {
    state.querySelector("strong").textContent = title;
    state.querySelector("span").textContent = message;
    state.classList.remove("hidden");
  };
  const algorithms = [...document.querySelectorAll("[name='experiment-algorithm']:checked")]
    .map((input) => input.value);
  if (!algorithms.length) {
    setState("Select a method", "Choose at least one baseline or QAOA method.");
    return;
  }
  button.disabled = true;
  button.textContent = "Submitting experiment…";
  $("#experiment-result").classList.add("hidden");
  try {
    const payload = {
      asset_count: numberValue("#experiment-assets", "Assets"),
      cardinality: numberValue("#experiment-cardinality", "Assets to select"),
      covariance_structure: $("#experiment-covariance").value,
      seed: numberValue("#experiment-seed", "Base seed"),
      repetitions: numberValue("#experiment-repetitions", "Repeated runs"),
      risk_aversion: numberValue("#experiment-risk", "Risk aversion"),
      algorithms,
      random_samples: numberValue("#experiment-random-samples", "Random candidates"),
      annealing_steps: numberValue("#experiment-annealing-steps", "Annealing steps"),
      qaoa_optimizer_shots: numberValue("#experiment-optimizer-shots", "QAOA optimizer shots"),
      qaoa_final_shots: numberValue("#experiment-final-shots", "QAOA final shots"),
      qaoa_max_iterations: numberValue("#experiment-qaoa-iterations", "QAOA iterations"),
    };
    const response = await fetch("/api/experiments/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const created = await response.json();
    if (!response.ok) throw new Error(created.error || "Could not submit experiment.");
    setState("Experiment queued", `Saved experiment ${created.experiment_id}. Waiting for local computation.`);
    button.textContent = "Experiment running…";
    while (true) {
      await new Promise((resolve) => setTimeout(resolve, 350));
      const statusResponse = await fetch(`/api/experiments/${encodeURIComponent(created.experiment_id)}`);
      const record = await statusResponse.json();
      if (!statusResponse.ok) throw new Error(record.error || "Could not read experiment status.");
      if (record.status === "failed") throw new Error(record.error || "Experiment failed.");
      if (record.status === "completed") {
        renderExperimentRecord(record);
        await refreshExperimentHistory();
        break;
      }
      setState(`Experiment ${record.status}`, `Computing ${record.asset_count} assets with cardinality ${record.cardinality}; results will be saved automatically.`);
    }
  } catch (error) {
    setState("Experiment failed", error.message);
  } finally {
    button.disabled = false;
    button.textContent = "Run matched experiment";
  }
}

function updateAssistantButton() {
  $("#assistant-ask").disabled = !assistantConfigured
    || !$("#assistant-consent").checked
    || !$("#assistant-experiment").value
    || !$("#assistant-question").value.trim();
}

async function loadAssistantStatus() {
  const response = await fetch("/api/assistant/status");
  const status = await response.json();
  if (!response.ok) throw new Error(status.error || "Could not read AI provider status.");
  assistantConfigured = Boolean(status.configured);
  $("#assistant-provider-label").textContent = assistantConfigured
    ? `${status.provider} · ${status.model}`
    : "Provider not configured";
  $("#assistant-status").textContent = assistantConfigured
    ? `${status.provider} is configured at ${status.base_url}. Experiment evidence is sent only after explicit consent.`
    : `${status.setup} Assistant requests are disabled until a provider is configured.`;
  updateAssistantButton();
}

async function loadExperimentOptions() {
  const response = await fetch("/api/experiment/options");
  const options = await response.json();
  if (!response.ok) throw new Error(options.error || "Could not load experiment options.");
  const assets = $("#experiment-assets");
  const selectedSize = assets.value;
  assets.replaceChildren(...options.asset_counts.map((size) => new Option(String(size), String(size))));
  assets.value = options.asset_counts.map(String).includes(selectedSize)
    ? selectedSize
    : String(options.asset_counts[0]);
  $("#experiment-cardinality").max = assets.value;
  const covariance = $("#experiment-covariance");
  const names = {
    independent: "Independent",
    correlated: "Positive correlation",
    mixed: "Mixed factors",
  };
  covariance.replaceChildren(...options.covariance_structures.map(
    (structure) => new Option(names[structure] || structure, structure),
  ));
  $("#experiment-state").querySelector("span").textContent =
    `${options.execution}; supported sizes: ${options.asset_counts.join(", ")} assets.`;
}

async function refreshAssistantExperiments() {
  try {
    const response = await fetch("/api/experiments?limit=100");
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not load saved experiments.");
    const completed = data.experiments.filter((item) => item.status === "completed");
    const select = $("#assistant-experiment");
    select.replaceChildren();
    if (!completed.length) {
      select.add(new Option("No completed experiments", ""));
    } else {
      completed.forEach((item) => {
        select.add(new Option(
          `${item.experiment_id.slice(0, 12)} · ${item.asset_count} assets · K=${item.cardinality}`,
          item.experiment_id,
        ));
      });
    }
    updateAssistantButton();
  } catch (error) {
    $("#assistant-status").textContent = error.message;
  }
}

async function askResearchAssistant() {
  const button = $("#assistant-ask");
  button.disabled = true;
  $("#assistant-answer").textContent = "Contacting the configured provider with the selected experiment evidence…";
  $("#assistant-answer-source").textContent = "";
  try {
    const response = await fetch("/api/assistant/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        experiment_id: $("#assistant-experiment").value,
        question: $("#assistant-question").value.trim(),
        external_data_consent: $("#assistant-consent").checked,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Assistant request failed.");
    $("#assistant-answer").textContent = data.answer;
    $("#assistant-answer-source").textContent = `Experiment ${data.experiment_id}`;
    $("#assistant-status").textContent = data.notice;
  } catch (error) {
    $("#assistant-answer").textContent = error.message;
    $("#assistant-answer-source").textContent = "Request not completed";
  } finally {
    updateAssistantButton();
  }
}

document.querySelectorAll(".tab").forEach((tab, index, tabs) => {
  tab.addEventListener("click", () => setTab(tab.dataset.tab));
  tab.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1
      : (index + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
    setTab(tabs[next].dataset.tab, true);
  });
});
$("#reset").addEventListener("click", resetExperiment);
$("#run").addEventListener("click", runExperiment);
$("#benchmark-run").addEventListener("click", runBenchmark);
$("#benchmark-export").addEventListener("click", exportBenchmarkCsv);
$("#experiment-run").addEventListener("click", runScalabilityExperiment);
$("#history-refresh").addEventListener("click", refreshExperimentHistory);
$("#assistant-ask").addEventListener("click", askResearchAssistant);
$("#assistant-consent").addEventListener("change", updateAssistantButton);
$("#assistant-experiment").addEventListener("change", updateAssistantButton);
$("#assistant-question").addEventListener("input", updateAssistantButton);
$("#experiment-assets").addEventListener("change", () => {
  const size = Number($("#experiment-assets").value);
  const cardinality = $("#experiment-cardinality");
  cardinality.max = String(size);
  if (Number(cardinality.value) > size) cardinality.value = String(size);
});
document.querySelectorAll(".sort-button").forEach((button) => {
  button.addEventListener("click", () => {
    if (sortKey === button.dataset.sort) sortAscending = !sortAscending;
    else { sortKey = button.dataset.sort; sortAscending = true; }
    renderBenchmarkRows();
  });
});
loadDefaults().catch((error) => {
  $("#portfolio-state").querySelector("strong").textContent = "Could not load inputs";
  $("#portfolio-state").querySelector("span").textContent = error.message;
});
fetch("/api/benchmark/types").then((response) => response.json()).then((data) => {
  $("#benchmark-plan").textContent = `${data.planned_configurations} planned recipes · not executed`;
}).catch(() => { $("#benchmark-plan").textContent = "Benchmark catalog unavailable"; });
loadAssistantStatus().catch((error) => {
  assistantConfigured = false;
  $("#assistant-status").textContent = error.message;
  updateAssistantButton();
});
loadExperimentOptions().catch((error) => {
  $("#experiment-state").querySelector("strong").textContent = "Experiment options unavailable";
  $("#experiment-state").querySelector("span").textContent = error.message;
});
