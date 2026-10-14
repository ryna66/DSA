"use strict";
const $ = id => document.getElementById(id);
const NS = "http://www.w3.org/2000/svg";
let graph = null, results = null, selected = "greedy", cursor = 0, timer = null, busy = false, dirty = false;
let measurements = [], measurementMeta = null;
const examples = {
  cycle: { n: 9, halls: 3, edges: Array.from({length: 9}, (_, i) => [i + 1, (i + 1) % 9 + 1]) },
  capacity: { n: 10, halls: 3, edges: [] },
  complete: { n: 6, halls: 3, edges: Array.from({length: 6}, (_, i) => Array.from({length: 5 - i}, (_, j) => [i + 1, i + j + 2])).flat() },
  improvement: { n: 7, halls: 3, edges: [[1,3],[1,4],[1,6],[2,4],[2,5],[2,7],[3,4],[5,6],[5,7],[6,7]] },
  single: { n: 1, halls: 2, edges: [] }, empty: { n: 0, halls: 3, edges: [] },
};
function svg(name, attrs = {}, text) { const node = document.createElementNS(NS, name); Object.entries(attrs).forEach(([k,v]) => node.setAttribute(k,v)); if (text !== undefined) node.textContent = text; return node; }
function colors(slot) { const hue = (slot * 137.508 + 195) % 360; return { solid: `hsl(${hue} 57% 60%)`, light: `hsl(${hue} 65% 94%)`, border: `hsl(${hue} 55% 73%)`, dark: `hsl(${hue} 37% 36%)` }; }
function status(message, error = false) { $("status").textContent = message; $("status").classList.toggle("error", error); }
function pause() { clearTimeout(timer); timer = null; $("play").textContent = "▶ Play"; }
function setBusy(value) {
  busy = value;
  for (const id of ["n","halls","edges","budget","density","seed","example","solve","generate","benchmark-run","sizes","benchmark-budget"]) $(id).disabled = value;
  controls();
}
function number(id, min, max) { const raw = $(id).value.trim(), n = Number(raw); if (!raw || !Number.isSafeInteger(n) || n < min || n > max) throw new Error(`${id}: enter an integer from ${min} to ${max}.`); return n; }
async function api(endpoint, payload) {
  const response = await fetch(`/api/${endpoint}`, { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8" }, body: new URLSearchParams(payload) });
  const data = await response.json(); if (!response.ok) throw new Error(data.error || "Request failed."); return data;
}
function install(data) {
  graph = data; results = null; cursor = 0; dirty = false; pause();
  $("n").value = data.n; $("halls").value = data.halls; $("edges").value = data.edges.map(e => e.join(",")).join("\n");
  renderCards(); render();
}
function inputChanged() { pause(); results = null; cursor = 0; dirty = true; renderCards(); render(); status("Input changed. Compare algorithms to apply it."); }
function active() { return results?.[selected]; }
function controls() {
  const total = active()?.events.length || 0;
  for (const id of ["play","timeline"]) $(id).disabled = busy || !total;
  for (const id of ["first","back"]) $(id).disabled = busy || !total || cursor === 0;
  for (const id of ["last","next"]) $(id).disabled = busy || !total || cursor === total;
  $("timeline").max = total; $("timeline").value = cursor;
  $("frame-label").textContent = `${cursor} / ${total} courses`;
  $("percent").textContent = `${total ? Math.round(cursor / total * 100) : 0}%`;
  $("download").disabled = busy || !results;
  for (const key of ["greedy","exact"]) { $("view-"+key).setAttribute("aria-pressed", selected === key); $("view-"+key).disabled = busy; }
}
function renderCards() {
  for (const key of ["greedy","exact"]) {
    const result = results?.[key];
    $(key+"-slots").textContent = result?.slots ?? "—";
    $(key+"-time").textContent = result ? `${result.timeMs.toFixed(3)} ms` : "— ms";
    $(key+"-proof").textContent = !result ? "Waiting to compare" : result.optimal ? "✓ Proven optimal" : result.timedOut ? `Time limit · best found (lower bound ${result.lowerBound})` : `Valid heuristic · not proved optimal (lower bound ${result.lowerBound})`;
    $(key+"-proof").classList.toggle("unproven", result && !result.optimal);
  }
}
function render() {
  const result = active(), events = result?.events.slice(0,cursor) || [], current = events.at(-1);
  const assignment = Array(graph?.n || 0).fill(0); events.forEach(e => { assignment[e.course-1] = e.slot; });
  renderGraph(assignment, current); renderTable(assignment);
  $("graph-badge").textContent = graph ? `${graph.n} COURSES · ${graph.edges.length} CONFLICTS` : "NO GRAPH";
  $("phase").textContent = dirty ? "INPUT CHANGED" : !result ? "READY" : cursor === result.events.length ? "TIMETABLE COMPLETE" : "ASSIGNING";
  $("phase-text").textContent = dirty ? "Previous graph shown. Compare to apply the edited constraints." : !result ? "Choose an algorithm to replay its assignments." : current ? `Course ${current.course} → Slot ${current.slot} · ${selected === "greedy" ? "DSatur greedy" : "branch & bound"}` : graph.n ? "All courses start unassigned." : "No courses need scheduling.";
  $("assigned").textContent = cursor; $("lower-bound").textContent = result?.lowerBound ?? "—";
  $("capacity").textContent = graph?.halls ?? $("halls").value;
  $("timetable-note").textContent = !result ? "The graph and timetable use the same colors for each slot." : result.optimal ? `Minimum of ${result.slots} slots proved. CSV exports the complete timetable.` : `${result.slots} slots found; at least ${result.lowerBound} needed. Optimality is not proved. CSV exports this best-known timetable.`;
  $("decision-title").textContent = current ? `Course ${current.course} takes Slot ${current.slot}.` : result && graph.n === 0 ? "An empty timetable needs zero slots." : "A place for every course.";
  const load = current ? assignment.filter(s => s === current.slot).length : 0;
  $("decision-text").textContent = current ? `${load} of ${graph.halls} halls used in this slot. Conflicting courses occupy other slots. This replays the returned timetable’s assignment order${selected === "exact" && result?.timedOut ? "; the exact search reached its time limit" : ""}.` : "The animation replays the selected algorithm’s final valid timetable, in assignment order.";
  controls();
}
function renderGraph(assignment, current) {
  const plot = $("graph"); plot.replaceChildren();
  for (let x=30;x<760;x+=30) for(let y=25;y<470;y+=30) plot.append(svg("circle",{cx:x,cy:y,r:1,fill:"#edf1f8"}));
  if (!graph || graph.n === 0) { plot.append(svg("text",{x:380,y:232,class:"empty-message"},graph ? "No courses. No slots required." : "Create a graph to begin.")); $("slot-legend").replaceChildren(); return; }
  const positions = Array.from({length:graph.n},(_,i) => graph.n===1 ? {x:380,y:235} : {x:380+195*Math.cos(i*2*Math.PI/graph.n-Math.PI/2), y:235+185*Math.sin(i*2*Math.PI/graph.n-Math.PI/2)});
  for (const [u,v] of graph.edges) { const a=positions[u-1],b=positions[v-1]; plot.append(svg("line",{x1:a.x,y1:a.y,x2:b.x,y2:b.y,class:`conflict-edge ${current && (u===current.course||v===current.course)?"active":""}`})); }
  const radius = graph.n>30 ? 9 : graph.n>16 ? 13 : 18;
  positions.forEach((p,i)=>{
    const slot=assignment[i],color=slot ? colors(slot) : null;
    const g=svg("g"); const circle=svg("circle",{cx:p.x,cy:p.y,r:radius,class:"course-circle"});
    if(color){ circle.style.fill=color.light;circle.style.stroke=color.solid; }
    g.append(circle);
    if(current?.course===i+1)g.append(svg("circle",{cx:p.x,cy:p.y,r:radius+6,class:"active-ring"}));
    const label=svg("text",{x:p.x,y:p.y,class:"course-number",style:`font-size:${graph.n>30?9:12}px`},i+1); if(color)label.style.fill=color.dark;g.append(label);
    g.append(svg("title",{},`Course ${i+1}${slot?` · Slot ${slot}`:" · unassigned"}`));plot.append(g);
  });
  plot.setAttribute("aria-label",`${graph.n} courses and ${graph.edges.length} conflicts. ${cursor} courses assigned using ${selected}.`);
  const legend=$("slot-legend");legend.replaceChildren();
  for(let slot=1;slot<=(active()?.slots||0);slot++){const item=document.createElement("span"),dot=document.createElement("i");dot.className="slot-dot";dot.style.background=colors(slot).solid;item.append(dot,document.createTextNode(`Slot ${slot}`));legend.append(item);}
}
function renderTable(assignment) {
  const head=$("timetable").querySelector("thead"),body=$("timetable").querySelector("tbody");head.replaceChildren();body.replaceChildren();
  const result=active();
  if(!graph||!result){const tr=document.createElement("tr"),td=document.createElement("td");td.colSpan=1;td.textContent="Compare algorithms to build the timetable.";tr.append(td);body.append(tr);return;}
  const header=document.createElement("tr");for(let h=0;h<=graph.halls;h++){const th=document.createElement("th");th.scope="col";th.textContent=h?`Hall ${h}`:"Slot";header.append(th);}head.append(header);
  for(let slot=1;slot<=result.slots;slot++){
    const color=colors(slot),row=document.createElement("tr"),label=document.createElement("th");label.scope="row";label.textContent=`Slot ${slot}`;label.style.color=color.dark;row.append(label);
    // Fixed hall positions from the final timetable keep courses stationary during replay.
    const courses=result.assignment.map((s,i)=>s===slot?i+1:null).filter(x=>x!==null);
    for(let h=0;h<graph.halls;h++){const td=document.createElement("td"),course=courses[h],chip=document.createElement("span");
      if(course&&assignment[course-1]){chip.className="course-chip";chip.style.setProperty("--slot-light",color.light);chip.style.setProperty("--slot-border",color.border);chip.style.setProperty("--slot-dark",color.dark);chip.textContent=`Course ${course}`;}
      else{chip.className="empty-hall";chip.textContent="—";}td.append(chip);row.append(td);
    }body.append(row);
  }
  if(!result.slots){const tr=document.createElement("tr"),td=document.createElement("td");td.colSpan=graph.halls+1;td.textContent="No exams to schedule.";tr.append(td);body.append(tr);}
}
async function solve() {
  if(busy)return;pause();setBusy(true);status("Java is building the greedy timetable and searching for a proven minimum…");
  try{
    const data=await api("solve",{n:number("n",0,60),halls:number("halls",1,20),edges:$("edges").value,budget:number("budget",0,60000)});
    graph=data.graph;results=data;dirty=false;cursor=active().events.length;renderCards();render();
    status(data.exact.optimal?`Exact minimum proved: ${data.exact.slots} slots. Select an algorithm and press Play.`:`Time limit reached. Best found: ${data.exact.slots} slots; lower bound: ${data.exact.lowerBound}. Optimality is not proved.`);
  }catch(error){status(error.message,true);}finally{setBusy(false);}
}
async function generate(){
  if(busy)return;pause();setBusy(true);let success=false;
  try{const data=await api("generate",{n:number("n",0,60),halls:number("halls",1,20),density:number("density",0,100)/100,seed:number("seed",-Number.MAX_SAFE_INTEGER,Number.MAX_SAFE_INTEGER)});install(data);$("example").value="";success=true;}catch(error){status(error.message,true);}finally{setBusy(false);}
  if(success)await solve();
}
function seek(value){if(busy||!active())return;pause();cursor=Math.max(0,Math.min(value,active().events.length));render();}
function play(){if(busy||!active()?.events.length)return;if(timer){pause();return;}if(cursor===active().events.length){cursor=0;render();}$("play").textContent="Ⅱ Pause";const tick=()=>{cursor++;render();if(cursor===active().events.length)pause();else timer=setTimeout(tick,1000/Number($("speed").value));};timer=setTimeout(tick,1000/Number($("speed").value));}
function download(text,name){const url=URL.createObjectURL(new Blob([text],{type:"text/csv;charset=utf-8"}));const link=document.createElement("a");link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function drawChart(id,field,label){
  const plot=$(id);plot.replaceChildren();const b={l:57,r:590,t:27,b:247};const maxN=Math.max(1,...measurements.map(r=>r.n));const maxY=Math.max(field==="slots"?1:.001,...measurements.flatMap(r=>[r.greedy[field],r.exact[field]]));
  for(let i=0;i<=4;i++){const y=b.b-(b.b-b.t)*i/4;plot.append(svg("line",{x1:b.l,y1:y,x2:b.r,y2:y,class:"plot-grid"}));plot.append(svg("text",{x:b.l-8,y:y+3,"text-anchor":"end",class:"axis-text"},measurements.length?(maxY*i/4).toFixed(field==="slots"?1:2):""));}
  plot.append(svg("path",{d:`M${b.l} ${b.t}V${b.b}H${b.r}`,fill:"none",class:"plot-axis"}));plot.append(svg("text",{x:10,y:15,class:"axis-text"},label));plot.append(svg("text",{x:320,y:292,"text-anchor":"middle",class:"axis-text"},"Courses (N)"));
  if(!measurements.length)plot.append(svg("text",{x:320,y:145,class:"empty-message"},"Run a comparison to measure this."));
  for(const[key,color]of[["greedy","#dc8c5d"],["exact","#6289ce"]]){const coords=measurements.map(row=>[b.l+row.n/maxN*(b.r-b.l),b.b-row[key][field]/maxY*(b.b-b.t)]);plot.append(svg("polyline",{points:coords.map(p=>p.join(",")).join(" "),fill:"none",stroke:color,"stroke-width":key==="greedy"?4:2.5,"stroke-dasharray":key==="exact"?"6 3":"none"}));coords.forEach(([x,y],i)=>{const entry=measurements[i][key];const dot=svg("circle",{cx:x,cy:y,r:key==="greedy"?5:3.5,fill:key==="exact"&&!entry.optimal?"white":color,stroke:color,"stroke-width":1.7});dot.append(svg("title",{},`${key} · N=${measurements[i].n} · ${field==="slots"?entry.slots:entry.timeMs.toFixed(6)} ${label} · ${entry.optimal?"optimal proved":"not proved optimal"}`));plot.append(dot);});}
  measurements.forEach(row=>plot.append(svg("text",{x:b.l+row.n/maxN*(b.r-b.l),y:267,"text-anchor":"middle",class:"axis-text"},row.n)));
}
function renderBenchmarks(){
  drawChart("slots-chart","slots","Slots");drawChart("time-chart","timeMs","Time (ms)");const body=$("benchmark-table");body.replaceChildren();
  measurements.forEach(row=>{const tr=document.createElement("tr");for(const value of[row.n,row.edges,row.greedy.slots,row.exact.slots,row.greedy.timeMs.toFixed(3),row.exact.timeMs.toFixed(3),row.exact.optimal?"Yes":`No · lower bound ${row.exact.lowerBound}`]){const td=document.createElement("td");td.textContent=value;tr.append(td);}body.append(tr);});$("download-benchmark").disabled=!measurements.length;
}
async function benchmark(){
  if(busy)return;
  let sizes,meta;
  try{sizes=[...new Set($("sizes").value.split(",").map(s=>Number(s.trim())))].sort((a,b)=>a-b);if(!sizes.length||sizes.length>12||sizes.some(n=>!Number.isInteger(n)||n<1||n>60))throw new Error("Enter 1–12 course counts between 1 and 60.");meta={halls:number("halls",1,20),density:number("density",0,100)/100,seed:number("seed",-1000000000,1000000000),budget:number("benchmark-budget",0,60000)};}catch(error){$("benchmark-status").textContent=error.message;return;}
  pause();setBusy(true);measurements=[];measurementMeta=meta;renderBenchmarks();
  try{for(const n of sizes){$("benchmark-status").textContent=`Measuring N = ${n} · ${measurements.length} / ${sizes.length} graphs complete…`;measurements.push(await api("benchmark",{...meta,n,seed:meta.seed+n*31}));renderBenchmarks();}const proven=measurements.filter(r=>r.exact.optimal).length;$("benchmark-status").textContent=`${sizes.length} graphs measured · ${proven} exact optima proved · R=${meta.halls}, density=${Math.round(meta.density*100)}%, seed=${meta.seed}. One run per size; timings include exact initialization.`;}catch(error){$("benchmark-status").textContent=`Comparison stopped: ${error.message}. Completed measurements remain available.`;}finally{setBusy(false);}
}
$("solve").addEventListener("click",solve);$("generate").addEventListener("click",generate);
for(const id of["n","halls","edges"])$(id).addEventListener("input",inputChanged);
$("example").addEventListener("change",async e=>{if(!e.target.value)return;install(examples[e.target.value]);await solve();});
for(const key of["greedy","exact"])$("view-"+key).addEventListener("click",()=>{pause();selected=key;cursor=active()?.events.length||0;render();});
$("play").addEventListener("click",play);$("first").addEventListener("click",()=>seek(0));$("back").addEventListener("click",()=>seek(cursor-1));$("next").addEventListener("click",()=>seek(cursor+1));$("last").addEventListener("click",()=>seek(active().events.length));$("timeline").addEventListener("input",e=>seek(Number(e.target.value)));$("speed").addEventListener("input",()=>{$("speed-value").textContent=`${$("speed").value} / sec`;});
$("download").addEventListener("click",()=>{if(active())download(active().csv,`${selected}_timetable.csv`);});
$("benchmark-run").addEventListener("click",benchmark);
$("download-benchmark").addEventListener("click",()=>{if(!measurements.length)return;const header="N,conflicts,R,density,seed,exact_budget_ms,greedy_slots,exact_slots,greedy_ms,exact_ms,greedy_optimal,exact_optimal,exact_lower_bound,timed_out\n";download(header+measurements.map(row=>[row.n,row.edges,measurementMeta.halls,measurementMeta.density,measurementMeta.seed+row.n*31,measurementMeta.budget,row.greedy.slots,row.exact.slots,row.greedy.timeMs.toFixed(6),row.exact.timeMs.toFixed(6),row.greedy.optimal,row.exact.optimal,row.exact.lowerBound,row.exact.timedOut].join(",")).join("\n")+"\n","timetable_comparison.csv");});
$("help-button").addEventListener("click",()=>$("help").showModal());$("close-help").addEventListener("click",()=>$("help").close());document.addEventListener("visibilitychange",()=>{if(document.hidden)pause();});
install(examples.improvement);$("example").value="improvement";renderBenchmarks();solve();
