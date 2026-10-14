const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { execFileSync } = require('node:child_process');
const root = path.resolve(__dirname, '..');
const SearchPlayback = vm.runInNewContext(fs.readFileSync(path.join(root, 'static/playback.js'), 'utf8') + '\nSearchPlayback;');
const results = JSON.parse(execFileSync('python3', ['-c', `
import json
from maze import solve, parse_grid
grids = ['S,a,A,E\\n#,#,#,#\\n#,#,#,#\\n#,#,#,#',
         '#######\\n#S.A.E#\\n#.#####\\n#a#####\\n#######\\n#######\\n#######',
         'S..##\\n.#.##\\na#.##\\n#####\\n####E']
print(json.dumps([solve(parse_grid(g),1,a) for g in grids for a in ('bfs','dfs','dijkstra','astar')]))
`], { cwd: root, encoding: 'utf8' }));

test('search begins empty and reveals only states expanded so far', () => {
  for (const result of results) {
    const player = new SearchPlayback(result);
    const initial = player.snapshot(0);
    assert.equal(initial.visited.size, 0);
    assert.equal(initial.frontierCount, 1);
    assert.equal(initial.searchDone, false);
    const visited = new Set();
    result.trace.forEach((event, i) => {
      const node = result.nodes[event.node];
      if (['expand', 'goal'].includes(event.kind)) visited.add(`${node.row},${node.col}`);
      const view = player.snapshot(i + 1);
      assert.equal(view.expanded, event.expanded);
      assert.equal(view.frontierCount, event.frontier);
      assert.deepEqual([...view.visited].sort(), [...visited].sort());
      assert.equal(view.current.mask, node.mask);
      assert.equal(view.searchDone, i === result.trace.length - 1);
    });
  }
});

test('rewind restores keys, doors, visited cells, and pending states', () => {
  for (const result of results) {
    const player = new SearchPlayback(result);
    player.snapshot(player.total);
    let view = player.snapshot(0);
    assert.equal(view.current.mask, 0);
    assert.equal(view.branch.length, 1);
    assert.equal(view.visited.size, 0);
    assert.equal(view.frontierCount, 1);
    view = player.snapshot(1);
    assert.equal(view.visited.size, 1);
    assert.equal(view.expanded, 1);
    if (result.path.length) {
      view = player.snapshot(result.trace.length + 1);
      assert.equal(view.phase, 'route');
      assert.equal(view.current.mask, 0);
      view = player.snapshot(player.total);
      assert.equal(view.routeStep, result.length);
      assert.equal(view.current.mask, result.path.at(-1).mask);
      assert.equal(view.finished, true);
    }
  }
});

test('impossible mazes still animate the complete search', () => {
  for (const result of results.filter(r => r.length === -1)) {
    const player = new SearchPlayback(result);
    assert.ok(player.total > 1);
    const end = player.snapshot(player.total);
    assert.equal(end.finished, true);
    assert.equal(end.phase, 'search');
    assert.equal(end.event.kind, 'exhausted');
    assert.equal(end.frontierCount, 0);
    assert.equal(end.expanded, result.states_explored);
  }
});
