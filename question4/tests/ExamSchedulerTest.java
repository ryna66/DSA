import java.nio.file.*;
import java.util.*;
import java.io.*;

/** No JUnit dependency: independent exhaustive checks and API/CLI integration. */
public class ExamSchedulerTest {
    static int checks;
    static void check(boolean condition, String message) {
        checks++;
        if (!condition) throw new AssertionError(message);
    }
    static void rejects(Runnable action) {
        try { action.run(); throw new AssertionError("Expected invalid input to be rejected"); }
        catch (IllegalArgumentException expected) { checks++; }
    }
    static boolean enumerate(ExamScheduler.Graph g, int course, int slots, int[] colors, int[] loads) {
        if (course == g.n()) return true;
        for (int slot = 1; slot <= slots; slot++) {
            if (loads[slot] == g.halls()) continue;
            boolean allowed = true;
            for (int v = 0; v < course; v++) if (g.conflicts()[course][v] && colors[v] == slot) { allowed = false; break; }
            if (!allowed) continue;
            colors[course] = slot; loads[slot]++;
            if (enumerate(g, course + 1, slots, colors, loads)) return true;
            colors[course] = 0; loads[slot]--;
            if (loads[slot] == 0) break;
        }
        return false;
    }
    static int reference(ExamScheduler.Graph graph) {
        if (graph.n() == 0) return 0;
        for (int slots = 1; slots <= graph.n(); slots++)
            if (enumerate(graph, 0, slots, new int[graph.n()], new int[slots + 1])) return slots;
        throw new AssertionError("Every loop-free graph must have a timetable");
    }
    static void valid(ExamScheduler.Graph graph, ExamScheduler.Result result) {
        int[] loads = new int[result.slots() + 1], replay = new int[graph.n()];
        check(result.assignment().length == graph.n(), "Every course must be represented");
        for (int i = 0; i < graph.n(); i++) {
            int slot = result.assignment()[i];
            check(slot >= 1 && slot <= result.slots(), "Assigned slot out of range");
            loads[slot]++;
        }
        for (int slot = 1; slot < loads.length; slot++) check(loads[slot] > 0 && loads[slot] <= graph.halls(), "Slot capacity violated");
        for (int[] edge : graph.edges()) check(result.assignment()[edge[0] - 1] != result.assignment()[edge[1] - 1], "Conflicting exams share a slot");
        for (var event : result.events()) {
            check(replay[event.course() - 1] == 0, "Animation assigns a course twice");
            replay[event.course() - 1] = event.slot();
            int count = 0;
            for (int s : replay) if (s == event.slot()) count++;
            check(count <= graph.halls(), "Playback violates capacity");
            for (int[] edge : graph.edges()) check(replay[edge[0]-1] == 0 || replay[edge[1]-1] == 0 || replay[edge[0]-1] != replay[edge[1]-1], "Playback conflict");
        }
        check(Arrays.equals(replay, result.assignment()), "Animation does not reconstruct final assignment");
        String[] lines = result.csv().split("\n");
        check(lines.length == result.slots() + 1, "CSV slot count");
        Set<Integer> courses = new HashSet<>();
        for (int row = 0; row < lines.length; row++) {
            String[] cells = lines[row].split(",", -1);
            check(cells.length == graph.halls() + 1, "CSV hall columns");
            if (row > 0) for (int c = 1; c < cells.length; c++) if (!cells[c].isEmpty()) check(courses.add(Integer.parseInt(cells[c])), "CSV duplicate exam");
        }
        check(courses.size() == graph.n(), "CSV missing course");
    }
    static void compareReference(ExamScheduler.Graph graph) {
        int optimum = reference(graph);
        var comparison = ExamScheduler.compare(graph, 2000);
        valid(graph, comparison.greedy()); valid(graph, comparison.exact());
        check(comparison.exact().optimal(), "Small exact search should finish");
        check(comparison.exact().slots() == optimum, "Exact answer disagrees with exhaustive reference");
        check(comparison.greedy().slots() >= optimum, "Greedy cannot beat optimum");
        check(comparison.greedy().lowerBound() <= optimum, "Invalid lower bound");
        check(!comparison.greedy().optimal() || comparison.greedy().slots() == optimum, "False optimality claim");
    }
    static void edgeCases() {
        for (int n : new int[]{0, 1, 2, 7, 9}) for (int halls : new int[]{1, 2, 3, 20}) {
            var empty = ExamScheduler.graph(n, halls, List.of());
            var full = ExamScheduler.randomGraph(n, halls, 1, 7);
            compareReference(empty); compareReference(full);
        }
        var cycle = ExamScheduler.parse("5 5 5\n1 2\n2 3\n3 4\n4 5\n5 1\n");
        var timeout = ExamScheduler.exact(cycle, 0);
        check(timeout.timedOut() && !timeout.optimal(), "Zero budget must not claim an unproved optimum");
        check(timeout.lowerBound() == 2 && timeout.slots() == 3, "Timeout should preserve valid bounds/incumbent");
        valid(cycle, timeout);
        check(ExamScheduler.exact(ExamScheduler.graph(7, 3, List.of()), 0).optimal(), "A bound may prove optimality without search");
        var duplicate = ExamScheduler.parse("3 3 2\n1 2\n2 1\n1 2\n");
        check(duplicate.edges().length == 1, "Conflict duplicates should be merged");
        rejects(() -> ExamScheduler.parse("2 1 1\n1 1"));
        rejects(() -> ExamScheduler.parse("2 1 1\n1 3"));
        rejects(() -> ExamScheduler.parse("2 1 0\n1 2"));
        rejects(() -> ExamScheduler.parse("2 2 1\n1 2"));
        rejects(() -> ExamScheduler.parse("2 0 1 extra"));
        rejects(() -> ExamScheduler.randomGraph(4, 2, Double.NaN, 1));
        rejects(() -> ExamScheduler.exact(cycle, -1));
    }
    static void exhaustiveAndRandom() {
        // All labeled undirected graphs on four vertices, with five capacities.
        for (int mask = 0; mask < 64; mask++) for (int r = 1; r <= 5; r++) {
            List<int[]> edges = new ArrayList<>(); int bit = 0;
            for (int u = 1; u <= 4; u++) for (int v = u + 1; v <= 4; v++, bit++)
                if ((mask & (1 << bit)) != 0) edges.add(new int[]{u, v});
            compareReference(ExamScheduler.graph(4, r, edges));
        }
        for (int n = 0; n <= 8; n++) for (int seed = 0; seed < 40; seed++)
            compareReference(ExamScheduler.randomGraph(n, seed % 5 + 1, (seed % 11) / 10.0, seed * 811L + n));
    }
    @SuppressWarnings("unchecked")
    static void apiTests() {
        var solved = (Map<String, Object>) ExamScheduler.api("/api/solve", Map.of("n", "7", "halls", "3", "edges", "1,3\n1,4\n1,6\n2,4\n2,5\n2,7\n3,4\n5,6\n5,7\n6,7", "budget", "1000"));
        var greedy = (Map<String, Object>) solved.get("greedy"); var exact = (Map<String, Object>) solved.get("exact");
        check(greedy.get("slots").equals(4) && exact.get("slots").equals(3), "Known greedy gap");
        check(Boolean.TRUE.equals(exact.get("optimal")) && Boolean.FALSE.equals(greedy.get("optimal")), "Proof labels");
        var generated = (Map<String, Object>) ExamScheduler.api("/api/generate", Map.of("n", "6", "halls", "3", "density", "1", "seed", "42"));
        check(((int[][]) generated.get("edges")).length == 15, "Complete random graph");
        var row = (Map<String, Object>) ExamScheduler.api("/api/benchmark", Map.of("n", "8", "halls", "3", "density", "0", "budget", "100"));
        check(row.containsKey("greedy") && row.containsKey("exact"), "Benchmark results missing");
        rejects(() -> ExamScheduler.api("/api/solve", Map.of("n", "3", "halls", "2", "edges", "1,2,3")));
        rejects(() -> ExamScheduler.api("/api/generate", Map.of("n", "61")));
        check(ExamScheduler.json(Map.of("message", "\"hello\"\n\\")).contains("\\n"), "JSON escaping");
    }
    static void cliTests() throws Exception {
        Path output = Files.createTempDirectory("examslot-test-");
        String java = Path.of(System.getProperty("java.home"), "bin", "java").toString();
        String cp = System.getProperty("java.class.path");
        Process process = new ProcessBuilder(java, "--add-modules", "jdk.httpserver", "-cp", cp, "ExamScheduler", "solve", "--out", output.toString()).start();
        try (var stdin = process.getOutputStream()) { stdin.write("3 2 2\n1 2\n2 3\n".getBytes()); }
        String text = new String(process.getInputStream().readAllBytes());
        String errors = new String(process.getErrorStream().readAllBytes());
        check(process.waitFor() == 0, "CLI failed: " + errors);
        check(text.contains("2 slots") && text.contains("proven optimal: yes"), "CLI result format");
        check(Files.exists(output.resolve("greedy_timetable.csv")) && Files.exists(output.resolve("exact_timetable.csv")), "CLI CSV outputs");
        process = new ProcessBuilder(java, "--add-modules", "jdk.httpserver", "-cp", cp, "ExamScheduler", "random", "--density", "0", "--seed", "42", "--out", output.toString()).start();
        try (var stdin = process.getOutputStream()) { stdin.write("7 3\n".getBytes()); }
        text = new String(process.getInputStream().readAllBytes()); errors = new String(process.getErrorStream().readAllBytes());
        check(process.waitFor() == 0, "Random CLI failed: " + errors);
        check(text.contains("3 slots"), "Random mode capacity constraint");
        try (var files = Files.list(output)) { for (Path file : files.toList()) Files.delete(file); }
        Files.delete(output);
    }
    public static void main(String[] args) throws Exception {
        edgeCases(); exhaustiveAndRandom(); apiTests(); cliTests();
        System.out.println("PASS: " + checks + " assertions; 680 exhaustive/random graph comparisons, edge cases, animation, CSV, API and CLI.");
    }
}
