"use strict";

// Reconstruct a search at any point without storing a full grid per frame.
class SearchPlayback {
  constructor(result) {
    this.result = result;
    this.reset();
  }
  reset() {
    this.applied = -1;
    this.visited = new Set();
    this.pending = new Set([0]);
  }
  get total() { return this.result.trace.length + this.result.path.length; }
  branch(nodeId) {
    const path = [];
    while (nodeId !== null) {
      const node = this.result.nodes[nodeId];
      path.push(node);
      nodeId = node.parent;
    }
    return path.reverse();
  }
  snapshot(cursor) {
    cursor = Math.max(0, Math.min(cursor, this.total));
    const end = Math.min(cursor - 1, this.result.trace.length - 1);
    if (end < this.applied) this.reset();
    while (this.applied < end) {
      const event = this.result.trace[++this.applied];
      const node = this.result.nodes[event.node];
      if (event.kind === "expand" || event.kind === "goal") {
        this.visited.add(`${node.row},${node.col}`);
        this.pending.delete(event.node);
        event.removed.forEach((id) => this.pending.delete(id));
        event.added.forEach((id) => this.pending.add(id));
      }
    }
    const event = end >= 0 ? this.result.trace[end] : null;
    const routeStep = cursor - this.result.trace.length - 1;
    const isRoute = routeStep >= 0;
    const branch = isRoute ? this.result.path.slice(0, routeStep + 1) : this.branch(event?.node ?? 0);
    return {
      phase: isRoute ? "route" : cursor === 0 ? "ready" : "search",
      event, branch, current: branch.at(-1), routeStep,
      visited: this.visited,
      frontier: new Set([...this.pending].map((id) => {
        const node = this.result.nodes[id]; return `${node.row},${node.col}`;
      })),
      expanded: event?.expanded || 0,
      frontierCount: this.pending.size,
      finished: cursor === this.total,
      searchDone: cursor >= this.result.trace.length,
    };
  }
}
