"use strict";

const $ = (id) => document.getElementById(id);
const letters = "abcdef";
const keyIcon = '<svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="6" cy="7" r="3.5"/><path d="m8.5 9.5 7 7m-3-3 2-2m-4 0 2-2"/></svg>';
const lockIcon = '<svg viewBox="0 0 20 20" aria-hidden="true"><rect x="4" y="9" width="12" height="8" rx="2"/><path d="M6 9V6a4 4 0 0 1 8 0v3M10 12v2"/></svg>';
const unlockIcon = '<svg viewBox="0 0 20 20" aria-hidden="true"><rect x="4" y="9" width="12" height="8" rx="2"/><path d="M6 9V5a4 4 0 0 1 7-2m-6 10 2 2 4-4"/></svg>';
let grid = [], result = null, cursor = 0, timer = null, busy = false, dirty = false;
let playback = null;
const algorithms = {
  bfs: ["BFS", "Breadth-first search", "Explores every branch in distance order. Guarantees a shortest path."],
  dfs: ["DFS", "Depth-first search", "Follows one branch deeply, then backtracks. The first route may be longer than the shortest."],
  dijkstra: ["Dijkstra", "Dijkstra’s algorithm", "Expands the lowest-cost state. With one-step moves, its order matches BFS."],
  astar: ["A*", "A* search", "Uses distance traveled + Manhattan distance to the exit. Guarantees a shortest path."],
};
let examples = [], activeTab = "manual", cellNodes = [], lastCursor = -1;

function keyOf(token) {
  if (token === "D:e") return "e";
  if (/^[a-fA-DF]$/.test(token)) return token.toLowerCase();
  return null;
}
function kindOf(token) {
  if (token === "#") return "wall";
  if (token === "S") return "start";
  if (token === "E") return "exit";
  if (/^[a-f]$/.test(token)) return "key";
  return keyOf(token) ? "door" : "open";
}
function mazeTypes() { return [...new Set(grid.flat().map(keyOf).filter(Boolean))].sort(); }
function setStatus(message, kind = "") {
  $("status-text").textContent = message;
  $("status").className = `status ${kind}`;
}
function setBusy(value) {
  busy = value;
  for (const id of ["solve-button", "generate-button", "clear-button", "examples", "types", "maze-input", "csv-file", "maze-size", "seed", "algorithm"]) $(id).disabled = value;
}
async function api(endpoint, data) {
  const response = await fetch(`/api/${endpoint}`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "The request could not be completed.");
  return payload;
}
function csvOf(source) { return source.map((row) => row.join(",")).join("\n") + "\n"; }
function pause() {
  clearTimeout(timer);
  timer = null;
  $("play-button").innerHTML = '<span aria-hidden="true">▶</span> Play';
}
function invalidate() {
  pause(); result = null; playback = null; cursor = 0; lastCursor = -1;
  $("path-length").textContent = "—";
  $("distance-unit").textContent = "steps to the exit";
  $("result-label").textContent = "Waiting to solve";
  $("states-count").textContent = "—";
  $("export-button").disabled = true;
  $("show-route").disabled = true;
  $("timeline").value = 0;
  $("timeline").max = 0;
  render();
}
function inputChanged() {
  dirty = true;
  invalidate();
  $("download-original").disabled = true;
  setStatus("Input changed. Visualize the search to apply your changes.");
  $("board-caption").textContent = "Previous maze shown. Solve to apply the new input.";
}
function installGrid(source, types) {
  grid = source;
  dirty = false;
  $("types").value = types;
  $("maze-input").value = csvOf(grid);
  $("grid-size-badge").textContent = `${grid.length} × ${grid.length}`;
  $("download-original").disabled = false;
  buildGrid();
  buildInventory();
  invalidate();
  setStatus("Ready to explore. Solve the maze to begin.");
}
function buildGrid() {
  const board = $("grid"), original = $("original-grid");
  board.replaceChildren(); original.replaceChildren(); cellNodes = [];
  board.className = `grid${grid.length > 15 ? " dense" : ""}`;
  board.style.setProperty("--n", grid.length || 1);
  original.style.setProperty("--n", grid.length || 1);
  if (!grid.length) {
    board.className = "grid empty";
    board.innerHTML = '<span class="empty-grid-icon" aria-hidden="true">▦</span><span>Your next maze starts here.</span>';
    board.setAttribute("aria-label", "No maze loaded");
    return;
  }
  for (let r = 0; r < grid.length; r++) {
    for (let c = 0; c < grid.length; c++) {
      const token = grid[r][c], kind = kindOf(token), key = keyOf(token);
      const cell = document.createElement("div");
      cell.className = `cell ${kind}`;
      cell.title = `Row ${r + 1}, column ${c + 1}: ${kind}${key ? ` ${key}` : ""}`;
      if (key) cell.style.setProperty("--pair", `var(--key-${key})`);
      board.append(cell);
      cellNodes.push(cell);
      const mini = document.createElement("div");
      mini.className = kind;
      if (key) mini.style.setProperty("--pair", `var(--key-${key})`);
      original.append(mini);
    }
  }
  $("original-description").textContent = `${grid.length} × ${grid.length} · ${mazeTypes().length} key types`;
}
function buildInventory() {
  $("inventory").replaceChildren();
  for (const key of mazeTypes()) {
    const item = document.createElement("div");
    item.className = "inventory-key"; item.id = `inventory-${key}`;
    item.style.setProperty("--pair", `var(--key-${key})`);
    item.innerHTML = `${keyIcon}<span>${key}</span>`;
    item.setAttribute("aria-label", `Key ${key}: not collected`);
    $("inventory").append(item);
  }
}
function updateControls() {
  const total = playback?.total || 0;
  const canPlay = total > 0 && !busy;
  $("play-button").disabled = !canPlay;
  $("timeline").disabled = !canPlay;
  for (const id of ["skip-back", "step-back"]) $(id).disabled = !canPlay || cursor === 0;
  for (const id of ["skip-forward", "step-forward"]) $(id).disabled = !canPlay || cursor === total;
  $("step-label").textContent = `Frame ${cursor} / ${total}`;
  $("percent-label").textContent = `${total ? Math.round(cursor / total * 100) : 0}%`;
  $("timeline").max = total;
  $("timeline").value = cursor;
  $("show-route").disabled = !canPlay || result.length < 0;
}
function render() {
  const view = playback?.snapshot(cursor);
  const branch = view?.branch || [];
  const current = view?.current;
  const mask = current?.mask || 0;
  const trail = new Set(branch.map((step) => `${step.row},${step.col}`));
  const explored = $("show-explored").checked ? view?.visited || new Set() : new Set();
  const frontier = view?.phase === "route" ? new Set() : view?.frontier || new Set();
  const checks = view?.phase === "search" ? view.event?.checks || [] : [];
  const blocked = new Set(checks.filter((check) => ["wall", "locked"].includes(check.status)).map((check) => `${check.row},${check.col}`));
  const queued = new Set(checks.filter((check) => check.status === "queued").map((check) => `${check.row},${check.col}`));
  for (let r = 0; r < grid.length; r++) {
    for (let c = 0; c < grid.length; c++) {
      const token = grid[r][c], kind = kindOf(token), key = keyOf(token), pos = `${r},${c}`;
      const cell = cellNodes[r * grid.length + c];
      const collected = kind === "key" && trail.has(pos);
      const isOpen = kind === "door" && trail.has(pos);
      const plain = kind === "open" || collected;
      cell.className = `cell ${collected ? "open" : kind}`;
      if (plain && explored.has(pos)) cell.classList.add("searched");
      if (frontier.has(pos)) cell.classList.add("waiting");
      if (plain && trail.has(pos)) cell.classList.add(view?.phase === "route" ? "on-path" : "active-branch");
      if (isOpen) cell.classList.add("unlocked");
      if (blocked.has(pos)) cell.classList.add("checked-blocked");
      if (queued.has(pos)) cell.classList.add("checked-open");
      if (current && current.row === r && current.col === c) {
        cell.classList.add("current");
        if (view.phase !== "route") cell.classList.add("search-current");
        if (kind === "key" && cursor !== lastCursor) cell.classList.add("pickup");
        if (view.event?.kind === "backtrack" && view.phase === "search") cell.classList.add("backtracking");
      }
      let content = "";
      if (kind === "start") content = "S";
      if (kind === "exit") content = "E";
      if (kind === "key" && !collected) content = keyIcon + key;
      if (kind === "door") content = (isOpen ? unlockIcon : lockIcon) + key.toUpperCase();
      cell.innerHTML = `<span class="token">${content}</span>`;
      cell.title = `Row ${r + 1}, column ${c + 1}: ${collected ? "collected key" : isOpen ? "unlocked door" : kind}${key ? ` ${key}` : ""}${trail.has(pos) ? " · current branch" : ""}${frontier.has(pos) ? " · waiting state" : ""}${blocked.has(pos) ? " · move blocked" : ""}`;
    }
  }
  const keys = mazeTypes(), collectedCount = keys.filter((key) => mask & (1 << letters.indexOf(key))).length;
  for (const key of keys) {
    const collected = Boolean(mask & (1 << letters.indexOf(key)));
    $(`inventory-${key}`).classList.toggle("collected", collected);
    $(`inventory-${key}`).setAttribute("aria-label", `Key ${key}: ${collected ? "collected" : "not collected"} on this branch`);
    $(`inventory-${key}`).title = `Key ${key}: ${collected ? "collected" : "not collected"} on this branch`;
  }
  $("keys-count").textContent = `${collectedCount} / ${keys.length}`;
  $("inventory-label").textContent = collectedCount ? `${collectedCount} on this branch` : "Empty for now";
  $("inventory-help").textContent = view?.phase === "route" ? "Keys stay with you throughout this route." : "This is the current branch’s inventory. Other branches may hold different keys.";
  $("states-count").textContent = view ? view.expanded.toLocaleString() : "—";
  $("frontier-count").textContent = view?.frontierCount || 0;
  $("depth-count").textContent = current?.depth ?? Math.max(0, view?.routeStep || 0);
  $("path-length").textContent = view?.searchDone ? result.length : "—";
  $("distance-unit").textContent = view?.searchDone && result.length === -1 ? "no path found" : "steps to the exit";
  $("result-label").textContent = !view ? "Waiting to solve" : !view.searchDone ? "Exploring possible routes…" : result.length < 0 ? "Exit is unreachable" : result.optimal ? "Shortest route confirmed" : "DFS route · may not be shortest";
  $("result-heading").textContent = $("algorithm").value === "dfs" ? "DFS ROUTE LENGTH" : "SHORTEST PATH";
  $("export-button").disabled = !view?.searchDone;
  $("phase-badge").textContent = !view || view.phase === "ready" ? "READY" : view.phase === "route" ? view.finished ? "COMPLETE" : "FINAL ROUTE" : view.event.kind === "backtrack" ? "BACKTRACKING" : view.event.kind === "exhausted" ? "NO ROUTE" : view.event.kind === "goal" ? "EXIT FOUND" : "EXPLORING";
  $("phase-badge").classList.toggle("route-phase", view?.phase === "route");
  $("search-summary").textContent = !view ? "Watch the algorithm make its decisions" : view.phase === "route" ? `Route step ${view.routeStep} / ${result.length}` : `${view.expanded} states checked · ${view.frontierCount} waiting`;
  let caption = grid.length ? "Your maze is ready. Watch the search find its way." : "Enter a maze, upload a CSV, or generate something new.";
  if (view?.phase === "search") {
    const name = algorithms[result.algorithm][0];
    caption = view.event.kind === "backtrack" ? "Branch finished. Backtracking to explore another possibility." : view.event.kind === "exhausted" ? "Every reachable state checked. No route to the exit." : view.event.kind === "goal" ? "The search reached the exit. Next: replay the resulting route." : `${name} checks row ${current.row + 1}, column ${current.col + 1} · ${checks.filter((c) => c.status === "queued").length} new states discovered`;
  } else if (view?.phase === "route") {
    caption = current.pickup ? `Picked up key ${current.pickup}.` : current.door ? `Opened door ${current.door.toUpperCase()}.` : `Following the ${result.optimal ? "shortest" : "DFS"} route · step ${view.routeStep}`;
    if (view.finished) caption = `Exit reached in ${result.length} moves.${result.optimal ? " Shortest route confirmed." : " DFS does not guarantee a shortest route."}`;
  }
  if (dirty) caption = "Previous maze shown. Visualize search to apply the new input.";
  $("board-caption").textContent = caption;
  $("grid").setAttribute("aria-label", `${grid.length} by ${grid.length} maze. ${caption} ${collectedCount} keys on this branch.`);
  renderChecks(checks);
  renderLog(view);
  updateControls();
  lastCursor = cursor;
}
function renderChecks(checks) {
  const panel = $("neighbor-checks"); panel.replaceChildren();
  const names = ["↑ Up", "→ Right", "↓ Down", "← Left"];
  const labels = { boundary: "Edge of grid", wall: "Wall", locked: "Locked", seen: "Already seen", queued: "Add to frontier" };
  names.forEach((name, i) => {
    const check = checks[i];
    const item = document.createElement("div"); item.className = `neighbor-check ${check?.status || "idle"}`;
    const direction = document.createElement("span"); direction.textContent = name;
    const decision = document.createElement("strong"); decision.textContent = check ? labels[check.status] + (check.key ? ` · needs ${check.key}` : "") : "—";
    item.append(direction, decision); panel.append(item);
  });
}
function renderLog(view) {
  const log = $("event-log"); log.replaceChildren();
  const add = (message, step) => {
    const item = document.createElement("li");
    const text = document.createElement("span"); text.textContent = message; item.append(text);
    if (step !== undefined) { const badge = document.createElement("small"); badge.textContent = step; item.append(badge); }
    log.append(item);
  };
  if (!view || view.phase === "ready") add("Ready to explore branches and check neighboring cells.");
  else if (view.phase === "search") {
    result.trace.slice(Math.max(0, cursor - 6), cursor).forEach((event) => {
      const node = result.nodes[event.node];
      const where = `(${node.row + 1}, ${node.col + 1})`;
      add(event.kind === "backtrack" ? `Backtrack to ${where}` : event.kind === "exhausted" ? "No reachable states remain" : event.kind === "goal" ? `Exit found at ${where}` : `Check ${where} · ${event.added.length} new states`, `depth ${node.depth}`);
    });
  } else {
    add("Replaying the resulting route", "step 0");
    view.branch.forEach((step, index) => {
      if (step.pickup) add(`Collected key ${step.pickup}`, `step ${index}`);
      if (step.door) add(`Opened door ${step.door.toUpperCase()}`, `step ${index}`);
    });
    if (view.finished) add("Reached the exit!", `step ${result.length}`);
  }
  log.scrollTop = log.scrollHeight;
}
function goTo(step) {
  pause();
  if (!playback || busy) return;
  cursor = Math.max(0, Math.min(step, playback.total));
  render();
}
function play() {
  if (!playback || busy) return;
  if (timer) { pause(); return; }
  if (cursor === playback.total) { cursor = 0; render(); }
  $("play-button").innerHTML = '<span aria-hidden="true">Ⅱ</span> Pause';
  const tick = () => {
    cursor++;
    render();
    if (cursor === playback.total) {
      pause();
      setStatus(result.length < 0 ? "Search complete. No route exists (−1)." : `${algorithms[result.algorithm][0]} complete. Route length: ${result.length} moves.`, result.length < 0 ? "error" : "success");
    } else timer = setTimeout(tick, 1000 / Number($("speed").value));
  };
  timer = setTimeout(tick, 1000 / Number($("speed").value));
}
async function solveMaze(autoplay = true) {
  if (busy) return;
  pause(); setBusy(true); updateControls(); setStatus("Preparing the algorithm’s search decisions…");
  let succeeded = false;
  try {
    const data = await api("solve", { text: $("maze-input").value, types: Number($("types").value), algorithm: $("algorithm").value });
    installGrid(data.grid, data.types);
    result = data;
    playback = new SearchPlayback(data);
    setStatus(`${algorithms[data.algorithm][0]} is ready. Watch the search, then the resulting route.`);
    render();
    succeeded = true;
  } catch (error) { setStatus(error.message, "error"); }
  finally { setBusy(false); updateControls(); }
  if (succeeded && autoplay && !matchMedia("(prefers-reduced-motion: reduce)").matches) play();
}
async function generateMaze() {
  if (busy) return;
  const seedText = $("seed").value.trim();
  const seed = seedText === "" ? null : Number(seedText);
  if (seed !== null && !Number.isSafeInteger(seed)) { setStatus("Use a whole-number seed within JavaScript’s safe integer range.", "error"); return; }
  pause(); setBusy(true); setStatus("Carving a maze with a guaranteed route…");
  try {
    const data = await api("generate", { size: Number($("maze-size").value), types: Number($("types").value), seed });
    installGrid(data.grid, data.types);
    $("examples").value = "";
    setStatus("New maze generated. Visualize the search when you’re ready.", "success");
  } catch (error) { setStatus(error.message, "error"); }
  finally { setBusy(false); }
}
function selectTab(name, focus = false) {
  activeTab = name;
  document.querySelectorAll("[data-tab]").forEach((tab) => {
    const selected = tab.dataset.tab === name;
    tab.setAttribute("aria-selected", selected);
    tab.tabIndex = selected ? 0 : -1;
    $(`panel-${tab.dataset.tab}`).hidden = !selected;
    if (selected && focus) tab.focus();
  });
}
function download(content, filename) {
  const url = URL.createObjectURL(new Blob([content], { type: "text/csv;charset=utf-8" }));
  const anchor = document.createElement("a"); anchor.href = url; anchor.download = filename; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

$("algorithm").addEventListener("change", () => {
  const [tag, name, description] = algorithms[$("algorithm").value];
  $("algorithm-name").textContent = name;
  $("algorithm-tag").textContent = tag;
  $("algorithm-description").textContent = description;
  invalidate();
  setStatus(`${tag} selected. Visualize search to explore this maze.`);
});
$("show-route").addEventListener("click", () => goTo(result.trace.length + 1));
$("solve-button").addEventListener("click", () => solveMaze());
$("generate-button").addEventListener("click", generateMaze);
$("maze-input").addEventListener("input", inputChanged);
$("types").addEventListener("change", inputChanged);
$("clear-button").addEventListener("click", () => {
  pause(); grid = []; dirty = false; buildGrid(); buildInventory(); invalidate();
  $("maze-input").value = ""; $("csv-file").value = ""; $("examples").value = "";
  $("file-label").textContent = "Choose a maze CSV";
  $("grid-size-badge").textContent = "No maze";
  $("original-description").textContent = "Your starting point, preserved.";
  $("download-original").disabled = true;
  setStatus("Maze cleared. Enter a new grid or choose an example.");
  selectTab("manual"); $("maze-input").focus();
});
$("examples").addEventListener("change", (event) => {
  if (event.target.value === "") return;
  const example = examples[Number(event.target.value)];
  installGrid(example.grid, example.types); selectTab("manual");
});
$("csv-file").addEventListener("change", async (event) => {
  const file = event.target.files[0]; if (!file) return;
  if (file.size > 100_000) { setStatus("Choose a CSV file smaller than 100 KB.", "error"); event.target.value = ""; return; }
  pause(); setBusy(true);
  try {
    $("maze-input").value = await file.text();
    $("file-label").textContent = file.name;
    inputChanged();
    setStatus("CSV loaded. Set T to its key/door type count, then visualize the search.");
  } catch { setStatus("The file could not be read. Please choose it again.", "error"); }
  finally { setBusy(false); }
});
document.querySelectorAll("[data-tab]").forEach((tab) => {
  tab.addEventListener("click", () => selectTab(tab.dataset.tab));
  tab.addEventListener("keydown", (event) => {
    const names = ["manual", "csv", "random"];
    let next;
    if (event.key === "ArrowRight") next = (names.indexOf(activeTab) + 1) % 3;
    if (event.key === "ArrowLeft") next = (names.indexOf(activeTab) + 2) % 3;
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = 2;
    if (next !== undefined) { event.preventDefault(); selectTab(names[next], true); }
  });
});
$("play-button").addEventListener("click", play);
$("skip-back").addEventListener("click", () => goTo(0));
$("step-back").addEventListener("click", () => goTo(cursor - 1));
$("step-forward").addEventListener("click", () => goTo(cursor + 1));
$("skip-forward").addEventListener("click", () => goTo(playback.total));
$("timeline").addEventListener("input", (event) => goTo(Number(event.target.value)));
$("show-explored").addEventListener("change", render);
$("speed").addEventListener("input", () => { $("speed-value").textContent = `${$("speed").value} / sec`; });
$("export-button").addEventListener("click", () => { if (result) download(result.csv, result.optimal ? "shortest_path.csv" : "dfs_path.csv"); });
$("download-original").addEventListener("click", () => { if (grid.length) download(csvOf(grid), "maze.csv"); });
$("help-button").addEventListener("click", () => $("help-dialog").showModal());
$("close-help").addEventListener("click", () => $("help-dialog").close());
$("help-dialog").addEventListener("click", (event) => { if (event.target === $("help-dialog")) { const rect = event.target.getBoundingClientRect(); if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) event.target.close(); } });
document.addEventListener("visibilitychange", () => { if (document.hidden) pause(); });

async function init() {
  setBusy(true);
  try {
    const response = await fetch("/api/examples");
    if (!response.ok) throw new Error("Could not load examples.");
    examples = await response.json();
    examples.forEach((example, index) => {
      const option = document.createElement("option"); option.value = index; option.textContent = example.title; $("examples").append(option);
    });
    installGrid(examples[5].grid, examples[5].types);
    $("examples").value = "5";
  } catch (error) {
    buildGrid(); buildInventory(); invalidate();
    setStatus(`${error.message} Start the app with python3 app.py, then reload.`, "error");
  } finally { setBusy(false); }
}
init();
