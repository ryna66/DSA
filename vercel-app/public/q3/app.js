"use strict";
const $ = id => document.getElementById(id);
const NS = "http://www.w3.org/2000/svg";
let graph = null, result = null, examples = [], cursor = 0, progress = 0;
let playing = false, raf = null, previousTime = null, busy = false, dirty = false;
let positions = [], geometries = [];
const format = value => value === null || value === undefined ? "—" : value.toLocaleString();
function svg(name, attributes = {}, text) {
  const node = document.createElementNS(NS, name);
  Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value));
  if (text !== undefined) node.textContent = text;
  return node;
}
function status(message, error = false) { $("status").textContent = message; $("status").classList.toggle("error", error); }
function setBusy(value) {
  busy = value;
  for (const id of ["cities", "stops", "coupons", "flight-input", "flight-count", "seed", "generate-button", "solve-button", "clear-button", "examples", "csv-file"]) $(id).disabled = value;
  controls();
}
function settings() {
  const values = {};
  for (const [id, name, minimum] of [["cities", "n", 1], ["stops", "k", 0], ["coupons", "coupons", 0]]) {
    const raw = $(id).value.trim(), value = Number(raw);
    if (!raw || !Number.isSafeInteger(value) || value < minimum) throw new Error(`${id}: enter an integer of at least ${minimum}.`);
    values[name] = value;
  }
  return values;
}
async function api(endpoint, data) {
  const response = await fetch(`/api/q3/${endpoint}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || "Request failed.");
  return value;
}
function stop() {
  cancelAnimationFrame(raf); raf = null; previousTime = null; playing = false;
  $("play").textContent = "▶ Play";
}
function resetResult() { stop(); result = null; cursor = 0; progress = 0; render(); }
function inputChanged() {
  dirty = true; resetResult();
  status("Input changed. Find the cheapest route to apply your changes.");
}
function install(data) {
  graph = { n: data.n, edges: data.edges };
  $("cities").value = data.n;
  $("flight-count").value = data.edges.length;
  $("flight-input").value = data.edges.map(edge => edge.join(",")).join("\n");
  if (data.k !== undefined) $("stops").value = data.k;
  if (data.coupons !== undefined) $("coupons").value = data.coupons;
  dirty = false; resetResult();
}
function controls() {
  const count = result?.path.length || 0;
  const canPlay = count > 0 && !busy;
  $("play").disabled = !canPlay;
  $("timeline").disabled = !canPlay;
  for (const id of ["first", "back"]) $(id).disabled = !canPlay || (cursor === 0 && progress === 0);
  for (const id of ["next", "last"]) $(id).disabled = !canPlay || cursor === count;
  $("timeline").max = count; $("timeline").value = cursor;
  $("frame-label").textContent = `Flight ${cursor} / ${count}`;
  $("percent").textContent = `${count ? Math.round(cursor / count * 100) : 0}%`;
  $("download-route").disabled = !result || busy;
  $("download-input").disabled = !graph || dirty || busy;
  $("route-only").disabled = !count;
  document.querySelectorAll(".leg-button").forEach(button => { button.disabled = busy; });
}
function cityPositions(n) {
  if (n === 1) return [null, { x: 400, y: 230 }];
  const points = [null, { x: 95, y: 235 }], columns = Math.ceil((n - 2) / 2);
  for (let id = 2; id < n; id++) points[id] = { x: 95 + 610 * (Math.floor((id - 2) / 2) + 1) / (columns + 1), y: id % 2 === 0 ? 100 : 370 };
  points[n] = { x: 705, y: 235 }; return points;
}
function edgeGeometry(u, v, lane, count) {
  const a = positions[u], b = positions[v];
  if (u === v) {
    const height = 55 + lane * Math.min(16, 40 / Math.max(1, count - 1));
    return { a: { x: a.x + 16, y: a.y - 17 }, b: { x: a.x - 16, y: a.y - 17 },
      c: { x: a.x + 65, y: a.y - height }, d: { x: a.x - 65, y: a.y - height } };
  }
  const low = positions[Math.min(u, v)], high = positions[Math.max(u, v)];
  const dx = high.x - low.x, dy = high.y - low.y, length = Math.hypot(dx, dy);
  const offset = count > 1 ? (lane - (count - 1) / 2) * Math.min(47, 180 / Math.max(1, count - 1)) : 18;
  const control = { x: (a.x + b.x) / 2 - dy / length * offset, y: (a.y + b.y) / 2 + dx / length * offset };
  const sa = Math.hypot(control.x - a.x, control.y - a.y), sb = Math.hypot(b.x - control.x, b.y - control.y);
  return { a: { x: a.x + (control.x - a.x) / sa * 25, y: a.y + (control.y - a.y) / sa * 25 },
    b: { x: b.x - (b.x - control.x) / sb * 28, y: b.y - (b.y - control.y) / sb * 28 }, c: control };
}
function pointAt(g, t) {
  const q = 1 - t;
  if (g.d) return { x: q ** 3 * g.a.x + 3*q*q*t*g.c.x + 3*q*t*t*g.d.x + t ** 3*g.b.x,
    y: q ** 3*g.a.y + 3*q*q*t*g.c.y + 3*q*t*t*g.d.y + t ** 3*g.b.y };
  return { x: q*q*g.a.x + 2*q*t*g.c.x + t*t*g.b.x, y: q*q*g.a.y + 2*q*t*g.c.y + t*t*g.b.y };
}
function pathData(g) { return g.d ? `M${g.a.x},${g.a.y} C${g.c.x},${g.c.y} ${g.d.x},${g.d.y} ${g.b.x},${g.b.y}` : `M${g.a.x},${g.a.y} Q${g.c.x},${g.c.y} ${g.b.x},${g.b.y}`; }
function moveTraveler() {
  const traveler = $("traveler"); if (!traveler || !result) return;
  const leg = result.path[cursor];
  if (leg && (playing || progress > 0)) {
    const g = geometries[leg.edge_id], p = pointAt(g, progress), ahead = pointAt(g, Math.min(1, progress + .001)), behind = pointAt(g, Math.max(0, progress - .001));
    const angle = Math.atan2(ahead.y - behind.y, ahead.x - behind.x) * 180 / Math.PI;
    traveler.setAttribute("transform", `translate(${p.x} ${p.y})`);
    $("traveler-plane").setAttribute("transform", `rotate(${angle})`);
  } else {
    const city = cursor ? result.path[cursor - 1].to : 1;
    traveler.setAttribute("transform", `translate(${positions[city].x} ${positions[city].y - 35})`);
    $("traveler-plane").setAttribute("transform", "rotate(0)");
  }
}
function renderGraph() {
  const map = $("flight-map"); map.replaceChildren();
  const defs = svg("defs");
  for (const [id, color] of [["normal", "#bac9df"], ["chosen", "#7999da"], ["travelled", "#3261da"], ["gold", "#d9a336"]]) {
    const marker = svg("marker", { id: `arrow-${id}`, viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto-start-reverse" });
    marker.append(svg("path", { d: "M0 0L10 5L0 10Z", fill: color })); defs.append(marker);
  }
  map.append(defs);
  for (let x = 30; x < 800; x += 30) for (let y = 20; y < 490; y += 30) map.append(svg("circle", { cx: x, cy: y, r: 1, class: "map-dot" }));
  if (!graph) { map.append(svg("text", { x: 400, y: 240, "text-anchor": "middle", fill: "#9aabc4", "font-size": 15 }, "Create a network to begin your journey.")); return; }
  positions = cityPositions(graph.n); geometries = [];
  const chosen = new Map((result?.path || []).map(leg => [leg.edge_id, leg]));
  const visited = new Set((result?.path.slice(0, cursor) || []).map(leg => leg.to));
  const groups = new Map();
  graph.edges.forEach(([u, v], index) => { const key = [Math.min(u, v), Math.max(u, v)].join(","); if (!groups.has(key)) groups.set(key, []); groups.get(key).push(index); });
  const lines = svg("g"), labels = svg("g"); map.append(lines, labels);
  graph.edges.forEach(([u, v, price], index) => {
    const group = groups.get([Math.min(u, v), Math.max(u, v)].join(","));
    const geometry = edgeGeometry(u, v, group.indexOf(index), group.length); geometries[index] = geometry;
    const leg = chosen.get(index), current = leg?.step === cursor + 1 && (playing || progress > 0), completed = leg && leg.step <= cursor;
    if ($("route-only").checked && result?.path.length && !leg) return;
    const gold = leg?.coupon && (completed || current);
    const edgeClass = gold ? "discounted" : completed ? "travelled" : leg ? "chosen" : "";
    const line = svg("path", { d: pathData(geometry), class: `flight-edge ${edgeClass}`, "marker-end": `url(#arrow-${gold ? "gold" : completed ? "travelled" : leg ? "chosen" : "normal"})` });
    const detail = `Flight ${index + 1}: ${u} → ${v}; price ${price}${leg ? `; route step ${leg.step}; ${leg.coupon ? `coupon pays ${leg.paid}` : "full price"}` : ""}`;
    line.append(svg("title", {}, detail)); lines.append(line);
    const middle = pointAt(geometry, .5), label = gold ? `${price} → ${leg.paid}` : String(price);
    const width = Math.max(24, label.length * 7 + 12);
    const g = svg("g"); g.append(svg("rect", { x: middle.x - width / 2, y: middle.y - 10, width, height: 20, rx: 5, class: "edge-label-bg" }));
    g.append(svg("text", { x: middle.x, y: middle.y + 4, "text-anchor": "middle", class: `edge-label ${gold ? "discounted" : leg ? "chosen" : ""}` }, label));
    g.append(svg("title", {}, detail)); labels.append(g);
  });
  for (let city = 1; city <= graph.n; city++) {
    const pos = positions[city], type = city === 1 ? "start" : city === graph.n ? "destination" : visited.has(city) ? "stop" : "";
    const g = svg("g");
    g.append(svg("circle", { cx: pos.x, cy: pos.y, r: 23, class: `city-ring ${type}` }));
    if (graph.n === 1) g.append(svg("circle", { cx: pos.x, cy: pos.y, r: 28, fill: "none", stroke: "#da7b87", "stroke-width": 2 }));
    g.append(svg("text", { x: pos.x, y: pos.y, class: `city-number ${type}` }, city));
    const caption = graph.n === 1 ? "START + DESTINATION" : city === 1 ? "START" : city === graph.n ? "DESTINATION" : visited.has(city) ? "STOP" : `CITY ${city}`;
    g.append(svg("text", { x: pos.x, y: pos.y + 41, class: "city-caption" }, caption));
    g.append(svg("title", {}, `City ${city}: ${caption.toLowerCase()}`)); map.append(g);
  }
  if (result && result.cost >= 0) {
    const traveler = svg("g", { id: "traveler", "pointer-events": "none" });
    traveler.append(svg("circle", { r: 16, class: "traveler-halo" }));
    traveler.append(svg("text", { id: "traveler-plane", class: "traveler-icon" }, "✈")); map.append(traveler); moveTraveler();
  }
  map.setAttribute("aria-label", `${graph.n} cities and ${graph.edges.length} directed flights. ${result ? result.cost < 0 ? "No valid route." : `Minimum cost ${result.cost}. ${cursor} flights completed.` : "No route computed."}`);
}
function render() {
  renderGraph();
  const valid = result && result.cost >= 0, path = result?.path || [];
  const completed = path.slice(0, cursor), last = completed.at(-1);
  const active = (playing || progress > 0) ? path[cursor] : null;
  $("graph-count").textContent = graph ? `${graph.n} CITIES · ${graph.edges.length} FLIGHTS` : "NO NETWORK";
  $("minimum-cost").textContent = result ? format(result.cost) : "—";
  $("cost-subtitle").textContent = !result ? "Ready to find your route" : !valid ? "No route within the stop limit" : graph.n === 1 ? "Already at your destination" : `${path.length} flights · ${result.stops} stops · ${result.coupons_used} coupons`;
  $("full-price").textContent = valid ? format(result.full_price) : "—";
  $("savings").textContent = valid ? format(result.full_price - result.cost) : "—";
  $("result-message").textContent = !result ? "Respecting your stop and coupon limits." : !valid ? "Try allowing more stops or adding a connecting flight." : `Cheapest valid route confirmed · ${format(result.states)} states checked.`;
  $("result-message").classList.toggle("error", result && !valid);
  $("running-cost").textContent = format(last?.running_cost || 0);
  $("stops-used").textContent = `${last?.stops_used || 0} / ${result?.k ?? $("stops").value}`;
  $("coupons-left").textContent = format((result?.coupons ?? Number($("coupons").value)) - completed.filter(leg => leg.coupon).length);
  const ticket = active || last;
  $("ticket").classList.toggle("gold", Boolean(ticket?.coupon));
  $("ticket").textContent = ticket ? `Flight ${ticket.step}: city ${ticket.from} → ${ticket.to} · ${ticket.coupon ? `${format(ticket.price)} → ${format(ticket.paid)} with a coupon` : `${format(ticket.price)} at full price`}${active ? " · in flight" : " · arrived"}` : valid && !path.length ? "No ticket needed. You are already there." : result && !valid ? "No valid itinerary under these limits." : "At the start. Press Play to begin your journey.";
  $("phase").textContent = dirty ? "INPUT CHANGED" : !result ? "READY" : !valid ? "NO ROUTE" : active ? playing ? "IN FLIGHT" : "PAUSED" : cursor === path.length ? "ARRIVED" : "READY TO FLY";
  $("phase-description").textContent = dirty ? "Previous network shown. Solve to apply the edited input." : active ? `Flying ${active.from} → ${active.to}${active.coupon ? " · half-price ticket" : ""}` : valid ? cursor === path.length ? `Destination reached. Total paid: ${format(result.cost)}.` : `At city ${last?.to || 1}. ${path.length - cursor} flights remaining.` : result ? "No journey satisfies the stop limit." : "Each arrow is a one-way flight. Prices label the edges.";
  $("leg-count").textContent = `${path.length} FLIGHTS`;
  const list = $("itinerary"); list.replaceChildren();
  if (!path.length) { const item = document.createElement("li"); item.className = "empty-itinerary"; item.textContent = !result ? "Your journey will appear here." : valid ? "City 1 is also the destination. Cost: 0." : "No valid route found."; list.append(item); }
  path.forEach((leg, i) => {
    const item = document.createElement("li"), button = document.createElement("button");
    button.className = `leg-button ${i < cursor ? "completed" : ""} ${i === cursor ? "current" : ""}`;
    button.disabled = busy;
    const number = document.createElement("span"); number.className = "leg-number"; number.textContent = i + 1;
    const details = document.createElement("span"); details.className = "leg-details";
    const name = document.createElement("span"); name.textContent = `City ${leg.from} → City ${leg.to}`;
    const note = document.createElement("small"); note.textContent = `Ticket #${leg.edge_id + 1} · ${leg.coupon ? "coupon applied" : "full price"}`;
    details.append(name, note);
    const price = document.createElement("span"); price.className = `leg-price ${leg.coupon ? "gold" : ""}`; price.textContent = format(leg.paid);
    button.append(number, details, price); button.addEventListener("click", () => seek(i + 1));
    item.append(button); list.append(item);
  });
  controls();
}
async function solveGraph() {
  if (busy) return;
  stop(); setBusy(true); status("Finding the cheapest route within your limits…");
  try {
    const data = await api("solve", { ...settings(), text: $("flight-input").value });
    install(data); result = data; render();
    status(data.cost < 0 ? "No route fits the stop limit (−1)." : `Minimum cost: ${format(data.cost)}. Press Play to take the journey.`, data.cost < 0);
  } catch (error) { status(error.message, true); }
  finally { setBusy(false); }
}
async function generateGraph() {
  if (busy) return;
  stop(); setBusy(true); let success = false;
  try {
    const values = settings(), m = Number($("flight-count").value), seed = Number($("seed").value);
    if (!$("flight-count").value.trim() || !Number.isInteger(m) || m < 0 || !$("seed").value.trim() || !Number.isSafeInteger(seed)) throw new Error("Enter a nonnegative flight count and an integer seed.");
    const data = await api("generate", { ...values, m, seed });
    install(data); $("examples").value = ""; success = true;
  } catch (error) { status(error.message, true); }
  finally { setBusy(false); }
  if (success) await solveGraph();
}
function seek(count) {
  if (!result || busy) return;
  stop(); cursor = Math.max(0, Math.min(count, result.path.length)); progress = 0; render();
}
function play() {
  if (!result?.path.length || busy) return;
  if (playing) { stop(); render(); return; }
  if (cursor === result.path.length) { cursor = 0; progress = 0; }
  playing = true; previousTime = null; $("play").textContent = "Ⅱ Pause"; render();
  const tick = now => {
    if (!playing) return;
    if (previousTime !== null) progress += (now - previousTime) / (1400 / Number($("speed").value));
    previousTime = now;
    if (progress >= 1) {
      cursor++; progress = 0;
      if (cursor === result.path.length) { stop(); render(); status(`Arrived at city ${graph.n}. Total cost: ${format(result.cost)}.`); return; }
      render();
    } else moveTraveler();
    raf = requestAnimationFrame(tick);
  };
  raf = requestAnimationFrame(tick);
}
function download(text, filename) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a"); a.href = url; a.download = filename; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
$("solve-button").addEventListener("click", solveGraph);
$("generate-button").addEventListener("click", generateGraph);
for (const id of ["cities", "stops", "coupons", "flight-input"]) $(id).addEventListener("input", inputChanged);
$("clear-button").addEventListener("click", () => { graph = null; dirty = false; $("flight-input").value = ""; $("examples").value = ""; $("csv-file").value = ""; resetResult(); status("Network cleared. Enter flights or generate a graph."); });
$("examples").addEventListener("change", async e => { if (e.target.value === "") return; install(examples[Number(e.target.value)]); await solveGraph(); });
$("csv-file").addEventListener("change", async e => {
  const file = e.target.files[0]; if (!file || busy) return;
  if (file.size > 90_000) { status("Choose a CSV file smaller than 90 KB.", true); e.target.value = ""; return; }
  stop(); setBusy(true); let success = false;
  try { const data = await api("import_csv", { csv: await file.text() }); install(data); $("examples").value = ""; success = true; }
  catch (error) { status(error.message, true); }
  finally { setBusy(false); e.target.value = ""; }
  if (success) await solveGraph();
});
$("play").addEventListener("click", play);
$("first").addEventListener("click", () => seek(0));
$("back").addEventListener("click", () => seek(progress > 0 ? cursor : cursor - 1));
$("next").addEventListener("click", () => seek(cursor + 1));
$("last").addEventListener("click", () => seek(result.path.length));
$("timeline").addEventListener("input", e => seek(Number(e.target.value)));
$("speed").addEventListener("input", () => { $("speed-value").textContent = `${$("speed").value}×`; });
$("route-only").addEventListener("change", renderGraph);
$("download-route").addEventListener("click", () => { if (result) download(result.csv, "flight_path.csv"); });
$("download-input").addEventListener("click", () => { if (graph && !dirty) download(`#cities,${graph.n}\nu,v,price\n` + graph.edges.map(e => e.join(",")).join("\n") + "\n", "flights.csv"); });
$("help-button").addEventListener("click", () => $("help-dialog").showModal());
$("close-help").addEventListener("click", () => $("help-dialog").close());
document.addEventListener("visibilitychange", () => { if (document.hidden) { stop(); render(); } });
async function init() {
  setBusy(true);
  let success = false;
  try {
    const response = await fetch("/api/q3/examples"); if (!response.ok) throw new Error("Could not load examples.");
    examples = await response.json();
    examples.forEach((example, i) => { const option = document.createElement("option"); option.value = i; option.textContent = example.title; $("examples").append(option); });
    install(examples[0]); $("examples").value = "0"; success = true;
  } catch (error) { render(); status(`${error.message} Start python3 question3/app.py, then reload.`, true); }
  finally { setBusy(false); }
  if (success) await solveGraph();
}
render(); init();
