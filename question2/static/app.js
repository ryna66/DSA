"use strict";
const $ = (id) => document.getElementById(id);
const svgNS = "http://www.w3.org/2000/svg";
let points = [], result = null, cursor = 0, timer = null, busy = false, measuring = false;
let measurements = [], bounds = null, benchmarkMeta = null;
const W = 800, H = 490, area = { left: 60, right: 770, top: 25, bottom: 440 };

function svg(name, attrs = {}, text) {
  const node = document.createElementNS(svgNS, name);
  Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
  if (text !== undefined) node.textContent = text;
  return node;
}
function fmt(value, digits = 6) {
  if (value === null || value === undefined) return "—";
  return Math.abs(value) >= 1e9 ? value.toExponential(digits) : value.toFixed(digits);
}
function coord(value) { return Math.abs(value) >= 1e6 || (value !== 0 && Math.abs(value) < .001) ? value.toExponential(2) : value.toFixed(2); }
function status(message, error = false) { $("status").textContent = message; $("status").classList.toggle("error", error); }
function setBusy(value) {
  busy = value;
  for (const id of ["point-count", "seed", "distribution", "generate-button", "solve-button", "manual-button", "apply-points"]) $(id).disabled = value;
  $("benchmark-button").disabled = value || measuring;
  updateControls();
}
async function api(endpoint, payload) {
  const response = await fetch(`/api/${endpoint}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "The request failed.");
  return data;
}
function pause() { clearTimeout(timer); timer = null; $("play").textContent = "▶ Play"; }
function setPoints(values) {
  pause(); points = values; result = null; cursor = 0;
  $("point-count").value = values.length;
  $("point-badge").textContent = `${values.length} POINT${values.length === 1 ? "" : "S"}`;
  renderResults(); render();
}
function updateControls() {
  const total = result?.events.length || 0;
  for (const id of ["play", "timeline"]) $(id).disabled = busy || !total;
  for (const id of ["first", "back"]) $(id).disabled = busy || !total || cursor === 0;
  for (const id of ["last", "next"]) $(id).disabled = busy || !total || cursor === total;
  $("timeline").max = total; $("timeline").value = cursor;
  $("frame-label").textContent = `Frame ${cursor} / ${total}`;
  $("percent").textContent = `${total ? Math.round(cursor / total * 100) : 0}%`;
}
function scale() {
  const xs = points.map(p => p[0]), ys = points.map(p => p[1]);
  const minX = points.length ? Math.min(...xs) : -100, maxX = points.length ? Math.max(...xs) : 100;
  const minY = points.length ? Math.min(...ys) : -100, maxY = points.length ? Math.max(...ys) : 100;
  const units = Math.max((maxX - minX) / (area.right - area.left), (maxY - minY) / (area.bottom - area.top)) * 1.18 || .4;
  const cx = minX / 2 + maxX / 2, cy = minY / 2 + maxY / 2;
  const xMin = cx - units * (area.right - area.left) / 2;
  const yMin = cy - units * (area.bottom - area.top) / 2;
  bounds = { units, xMin, yMin };
  return { x: v => area.left + (v - xMin) / units, y: v => area.bottom - (v - yMin) / units };
}
function drawAxes(plot, project) {
  const background = svg("g");
  for (let i = 0; i <= 5; i++) {
    const x = area.left + (area.right - area.left) * i / 5;
    const y = area.bottom - (area.bottom - area.top) * i / 5;
    background.append(svg("line", { x1: x, y1: area.top, x2: x, y2: area.bottom, class: "plot-grid" }));
    background.append(svg("line", { x1: area.left, y1: y, x2: area.right, y2: y, class: "plot-grid" }));
    background.append(svg("text", { x, y: area.bottom + 22, "text-anchor": "middle", class: "axis-text" }, coord(bounds.xMin + (x - area.left) * bounds.units)));
    background.append(svg("text", { x: area.left - 10, y: y + 4, "text-anchor": "end", class: "axis-text" }, coord(bounds.yMin + (area.bottom - y) * bounds.units)));
  }
  background.append(svg("path", { d: `M${area.left} ${area.top}V${area.bottom}H${area.right}`, fill: "none", class: "plot-axis" }));
  background.append(svg("text", { x: 787, y: area.bottom + 4, class: "axis-text" }, "x"));
  background.append(svg("text", { x: area.left - 3, y: 14, class: "axis-text" }, "y"));
  plot.append(background);
}
function pairLine(plot, pair, project, className) {
  if (!pair) return;
  const a = points[pair[0]], b = points[pair[1]];
  plot.append(svg("line", { x1: project.x(a[0]), y1: project.y(a[1]), x2: project.x(b[0]), y2: project.y(b[1]), class: className }));
}
function pairRings(plot, pair, project, className, radius) {
  if (!pair) return;
  for (const id of pair) {
    const [x, y] = points[id];
    const ring = svg("circle", { cx: project.x(x), cy: project.y(y), r: radius, class: `point ${className}`, "pointer-events": "none" });
    ring.append(svg("title", {}, `P${id + 1} (${x}, ${y})`)); plot.append(ring);
  }
}
function render() {
  const plot = $("point-plot"); plot.replaceChildren();
  const project = scale(); drawAxes(plot, project);
  const event = cursor > 0 ? result.events[cursor - 1] : null;
  const active = event ? new Set(result.order.slice(event.lo, event.hi)) : null;
  const defs = svg("defs"); const clip = svg("clipPath", { id: "plane-clip" });
  clip.append(svg("rect", { x: area.left, y: area.top, width: area.right - area.left, height: area.bottom - area.top })); defs.append(clip); plot.append(defs);
  const region = svg("g", { "clip-path": "url(#plane-clip)" }); plot.append(region);
  if (event?.strip_d !== undefined) {
    const left = Math.max(area.left, project.x(event.split_x - event.strip_d));
    const right = Math.min(area.right, project.x(event.split_x + event.strip_d));
    region.append(svg("rect", { x: left, y: area.top, width: Math.max(0, right - left), height: area.bottom - area.top, class: "strip-region" }));
    region.append(svg("text", { x: Math.max(area.left + 15, Math.min(area.right - 30, project.x(event.split_x))), y: area.top + 17, "text-anchor": "middle", fill: "#7591c7", "font-size": 11 }, "← 2d →"));
  }
  if (event?.split_x !== undefined) {
    region.append(svg("line", { x1: project.x(event.split_x), x2: project.x(event.split_x), y1: area.top, y2: area.bottom, class: "split-line" }));
  }
  if (result && $("show-brute").checked) pairLine(region, result.brute.pair, project, "pair-brute");
  if (event?.best && $("show-divide").checked) pairLine(region, event.best, project, cursor === result.events.length ? "pair-divide" : "pair-local");
  if (event?.checking) pairLine(region, event.checking, project, "pair-check");
  points.forEach(([x, y], id) => {
    const circle = svg("circle", { cx: project.x(x), cy: project.y(y), r: points.length > 400 ? 2.4 : 4,
      class: `point ${active ? active.has(id) ? "active" : "faded" : ""} ${event?.checking?.includes(id) ? "comparing" : ""}` });
    circle.append(svg("title", {}, `P${id + 1}: (${x}, ${y})`)); region.append(circle);
    if (points.length <= 12) region.append(svg("text", { x: project.x(x) + 8, y: project.y(y) - 7, class: "axis-text" }, `P${id + 1}`));
  });
  if (result && $("show-brute").checked) pairRings(region, result.brute.pair, project, "brute", 9);
  if (event?.best && $("show-divide").checked) pairRings(region, event.best, project, "divide", 5.5);
  if (!points.length) plot.append(svg("text", { x: 415, y: 245, "text-anchor": "middle", fill: "#a0aec3", "font-size": 15 }, "No points yet. Click the plane to add one."));
  const descriptions = {
    split: "Split the x-sorted points into two balanced halves.", base: "Three or fewer points: compare each pair directly.",
    compare: event?.strip_d !== undefined ? "Check nearby points in the strip, in y order." : "Check a pair in this small subproblem.",
    strip: "Merge the halves. Search within distance d of the dividing line.", merge: "Return this region’s closest pair to its parent.",
    complete: "Recursion complete. Both algorithms’ final pairs are highlighted.", duplicate: "Duplicate coordinates found. Zero is the smallest possible distance.",
    insufficient: "Fewer than two points: no closest pair or minimum distance exists.",
  };
  $("phase").textContent = event ? event.kind.toUpperCase() : "READY";
  $("phase-description").textContent = event ? descriptions[event.kind] : "Animate divide-and-conquer to see every split and merge.";
  $("event-description").textContent = event ? descriptions[event.kind] + (event.checking ? ` Comparing P${event.checking[0] + 1} and P${event.checking[1] + 1}.` : "") : "Press Play to animate divide-and-conquer. The orange pair is the brute-force reference.";
  $("depth").textContent = event?.depth ?? "—";
  $("region-size").textContent = event ? event.hi - event.lo : "—";
  $("local-distance").textContent = fmt(event?.distance);
  $("strip-width").textContent = fmt(event?.strip_d !== undefined ? 2 * event.strip_d : null);
  plot.setAttribute("aria-label", `${points.length} points. ${$("phase-description").textContent}`);
  updateControls();
}
function renderResults() {
  $("agreement").classList.toggle("error", result && !result.agree);
  $("agreement").textContent = !result ? "Ready to compare" : !result.agree ? "Algorithms disagree — inspect input" : points.length < 2 ? "Both agree: no pair exists" : "✓ Both minimum distances agree";
  for (const name of ["brute", "divide"]) {
    const data = result?.[name];
    $(name + "-distance").textContent = data ? data.distance === null ? "No pair" : fmt(data.distance) : "—";
    $(name + "-time").textContent = data ? fmt(data.time_ms, 3) : "—";
    $(name + "-comparisons").textContent = data ? `${data.comparisons.toLocaleString()} comparisons` : "— comparisons";
    const pair = $(name + "-pair"); pair.replaceChildren();
    if (data?.pair) data.pair.forEach(id => { const row = document.createElement("div"); row.textContent = `P${id + 1} (${coord(points[id][0])}, ${coord(points[id][1])})`; row.title = `(${points[id][0]}, ${points[id][1]})`; pair.append(row); });
    else pair.textContent = data ? "At least two points are required." : name === "brute" ? "Every possible pair is checked." : "Split, solve, and check the strip.";
  }
}
async function solvePoints() {
  if (busy) return;
  pause(); setBusy(true); status("Computing both algorithms and recording the recursion…");
  try {
    result = await api("solve", { points }); cursor = result.events.length;
    renderResults(); render();
    status(result.agree ? "Results agree. Press Play to explore the recursion." : "The algorithms disagree. Inspect the result before using it.", !result.agree);
  } catch (error) { status(error.message, true); }
  finally { setBusy(false); }
}
async function generate() {
  if (busy) return;
  const n = Number($("point-count").value), seed = Number($("seed").value);
  if (!$("point-count").value.trim() || !Number.isInteger(n) || n < 0 || n > 2000 || !$("seed").value.trim() || !Number.isSafeInteger(seed)) { status("Use integer N from 0–2000 and a whole-number seed.", true); return; }
  pause(); setBusy(true); let succeeded = false;
  try {
    const data = await api("generate", { n, seed, distribution: $("distribution").value });
    setPoints(data.points); succeeded = true;
  } catch (error) { status(error.message, true); }
  finally { setBusy(false); }
  if (succeeded) await solvePoints();
}
function seek(frame) {
  if (!result || busy) return;
  pause(); cursor = Math.min(result.events.length, Math.max(0, frame)); render();
}
function play() {
  if (!result || busy) return;
  if (timer) { pause(); return; }
  if (cursor === result.events.length) { cursor = 0; render(); }
  $("play").textContent = "Ⅱ Pause";
  const tick = () => { cursor++; render(); if (cursor >= result.events.length) pause(); else timer = setTimeout(tick, 1000 / Number($("speed").value)); };
  timer = setTimeout(tick, 1000 / Number($("speed").value));
}
function download(text, filename, mime = "text/csv") {
  const url = URL.createObjectURL(new Blob([text], { type: mime }));
  const anchor = document.createElement("a"); anchor.href = url; anchor.download = filename; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function renderBenchmark() {
  const chart = $("timing-plot"); chart.replaceChildren();
  const box = { l: 62, r: 730, t: 30, b: 285 };
  const maxN = Math.max(1, ...measurements.map(r => r.n)), maxTime = Math.max(.001, ...measurements.flatMap(r => [r.brute_ms, r.divide_ms]));
  for (let i = 0; i <= 4; i++) {
    const y = box.b - (box.b - box.t) * i / 4;
    chart.append(svg("line", { x1: box.l, y1: y, x2: box.r, y2: y, class: "plot-grid" }));
    chart.append(svg("text", { x: box.l - 9, y: y + 3, "text-anchor": "end", class: "axis-text" }, measurements.length ? (maxTime * i / 4).toFixed(2) : ""));
  }
  chart.append(svg("path", { d: `M${box.l} ${box.t}V${box.b}H${box.r}`, fill: "none", class: "plot-axis" }));
  chart.append(svg("text", { x: 18, y: 22, class: "axis-text" }, "Time (ms)"));
  chart.append(svg("text", { x: 395, y: 331, "text-anchor": "middle", class: "axis-text" }, "Number of points (N)"));
  if (!measurements.length) chart.append(svg("text", { x: 395, y: 160, "text-anchor": "middle", fill: "#a2afc3", "font-size": 13 }, "Your measurements will appear here."));
  for (const [key, color, label] of [["brute_ms", "#df754e", "Brute force"], ["divide_ms", "#3261da", "Divide and conquer"]]) {
    const coords = measurements.map(r => [box.l + r.n / maxN * (box.r - box.l), box.b - r[key] / maxTime * (box.b - box.t)]);
    chart.append(svg("polyline", { points: coords.map(p => p.join(",")).join(" "), fill: "none", stroke: color, "stroke-width": 2.5 }));
    coords.forEach(([x, y], i) => { const dot = svg("circle", { cx: x, cy: y, r: 4, fill: color }); dot.append(svg("title", {}, `${label} · N=${measurements[i].n} · ${measurements[i][key].toFixed(6)} ms`)); chart.append(dot); });
  }
  measurements.forEach(row => chart.append(svg("text", { x: box.l + row.n / maxN * (box.r - box.l), y: 304, "text-anchor": "middle", class: "axis-text" }, row.n)));
  const table = $("timing-table"); table.replaceChildren();
  measurements.forEach(row => { const tr = document.createElement("tr"); for (const val of [row.n, row.brute_ms.toFixed(3), row.divide_ms.toFixed(3), row.agree ? "✓" : "NO"]) { const td = document.createElement("td"); td.textContent = val; tr.append(td); } table.append(tr); });
  if (!measurements.length) { const tr = document.createElement("tr"); const td = document.createElement("td"); td.colSpan = 4; td.textContent = "No measurements yet"; tr.append(td); table.append(tr); }
  $("download-benchmark").disabled = !measurements.length;
}
async function runBenchmark() {
  if (measuring || busy) return;
  const sizes = [...new Set($("sizes").value.split(",").map(s => Number(s.trim())))].sort((a,b) => a-b);
  const repeats = Number($("repeats").value), seed = Number($("seed").value);
  if (!sizes.length || sizes.length > 12 || sizes.some(n => !Number.isInteger(n) || n < 2 || n > 3000) || !$("seed").value.trim() || !Number.isSafeInteger(seed)) { $("benchmark-status").textContent = "Enter 1–12 sizes between 2 and 3000, and a whole-number seed."; return; }
  measuring = true; pause(); setBusy(true); $("benchmark-button").disabled = true; $("sizes").disabled = true; $("repeats").disabled = true;
  measurements = []; benchmarkMeta = { repeats, seed }; renderBenchmark();
  $("performance-insight").textContent = "Measuring both algorithms on identical point sets…";
  try {
    for (const n of sizes) {
      $("benchmark-status").textContent = `Measuring N = ${n.toLocaleString()} · ${measurements.length} / ${sizes.length} sizes complete…`;
      const data = await api("benchmark", { sizes: [n], repeats, seed, distribution: "uniform" });
      measurements.push(data.rows[0]); renderBenchmark();
      if (!data.agree) throw new Error(`Distance mismatch detected at N = ${n}.`);
    }
    $("benchmark-status").textContent = `All ${sizes.length * repeats} runs agree on minimum distance. Median of ${repeats} runs per size · uniform random data · seed ${seed}.`;
    const last = measurements.at(-1), ratio = last.divide_ms ? last.brute_ms / last.divide_ms : null;
    $("performance-insight").textContent = ratio ? `At N = ${last.n}, ${ratio >= 1 ? "divide-and-conquer" : "brute force"} was ${(ratio >= 1 ? ratio : 1/ratio).toFixed(1)}× faster in this measurement. Timings depend on input size and your machine.` : "Measurement complete. See the table for exact timings.";
  } catch (error) { $("benchmark-status").textContent = `Test stopped: ${error.message} Any completed measurements remain available.`; }
  finally { measuring = false; setBusy(false); $("benchmark-button").disabled = false; $("sizes").disabled = false; $("repeats").disabled = false; }
}

$("generate-button").addEventListener("click", generate);
$("solve-button").addEventListener("click", solvePoints);
$("play").addEventListener("click", play);
$("first").addEventListener("click", () => seek(0));
$("back").addEventListener("click", () => seek(cursor - 1));
$("next").addEventListener("click", () => seek(cursor + 1));
$("last").addEventListener("click", () => seek(result.events.length));
$("timeline").addEventListener("input", e => seek(Number(e.target.value)));
$("speed").addEventListener("input", () => { $("speed-value").textContent = `${$("speed").value} frames/s`; });
for (const id of ["show-brute", "show-divide"]) $(id).addEventListener("change", render);
$("point-plot").addEventListener("click", event => {
  if (busy || !bounds || points.length >= 2000) return;
  const plot = $("point-plot"), transform = plot.getScreenCTM(); if (!transform) return;
  const location = new DOMPoint(event.clientX, event.clientY).matrixTransform(transform.inverse());
  if (location.x < area.left || location.x > area.right || location.y < area.top || location.y > area.bottom) return;
  const x = bounds.xMin + (location.x - area.left) * bounds.units, y = bounds.yMin + (area.bottom - location.y) * bounds.units;
  if (Math.abs(x) > 1e100 || Math.abs(y) > 1e100) { status("New point would exceed the coordinate limit (±1e100).", true); return; }
  setPoints([...points, [x, y]]); status("Point added. Compare algorithms to recompute the closest pair.");
});
$("download-points").addEventListener("click", () => download(points.map(p => p.join(",")).join("\n") + (points.length ? "\n" : ""), "points.csv"));
$("manual-button").addEventListener("click", () => { $("coordinates").value = points.map(p => p.join(",")).join("\n"); $("manual-error").textContent = ""; $("manual-dialog").showModal(); });
$("close-manual").addEventListener("click", () => $("manual-dialog").close());
$("apply-points").addEventListener("click", async () => {
  const lines = $("coordinates").value.split(/\r?\n/).filter(line => line.trim());
  try {
    if (lines.length > 2000) throw new Error("Use at most 2000 points.");
    const values = lines.map((line, i) => {
      const parts = line.trim().split(/[,\s]+/);
      if (parts.length !== 2 || parts.some(p => !p || !Number.isFinite(Number(p)) || Math.abs(Number(p)) > 1e100)) throw new Error(`Line ${i + 1}: enter two finite numbers within ±1e100.`);
      return parts.map(Number);
    });
    setPoints(values); $("manual-dialog").close(); await solvePoints();
  } catch (error) { $("manual-error").textContent = error.message; }
});
$("help-button").addEventListener("click", () => $("help-dialog").showModal());
$("close-help").addEventListener("click", () => $("help-dialog").close());
$("benchmark-button").addEventListener("click", runBenchmark);
$("download-benchmark").addEventListener("click", () => {
  const header = "N,brute_force_ms,divide_conquer_ms,distances_agree,repeats,seed\n";
  download(header + measurements.map(r => [r.n,r.brute_ms.toFixed(6),r.divide_ms.toFixed(6),r.agree,benchmarkMeta.repeats,benchmarkMeta.seed].join(",")).join("\n") + "\n", "performance.csv");
});
document.addEventListener("visibilitychange", () => { if (document.hidden) pause(); });
renderBenchmark(); render(); generate();
