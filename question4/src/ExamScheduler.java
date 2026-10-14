import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;

/** Dependency-free Java exam timetabling with capacity-aware DSatur and exact search. */
public class ExamScheduler {
    public record Graph(int n, int halls, boolean[][] conflicts, int[][] edges) {}
    public record Event(int course, int slot) {}
    public record Result(String algorithm, int slots, boolean optimal, boolean timedOut,
                         int lowerBound, int[] assignment, List<Event> events,
                         double timeMs, long searchNodes, String csv) {}
    public record Comparison(Graph graph, Result greedy, Result exact) {}

    static void require(boolean condition, String message) {
        if (!condition) throw new IllegalArgumentException(message);
    }

    public static Graph graph(int n, int halls, List<int[]> edges) {
        require(n >= 0 && n <= 200, "N must be between 0 and 200.");
        require(halls >= 1 && halls <= 1000, "R must be between 1 and 1000.");
        boolean[][] adjacency = new boolean[n][n];
        List<int[]> unique = new ArrayList<>();
        for (int[] edge : edges) {
            require(edge.length == 2, "Each conflict needs exactly two course IDs.");
            int u = edge[0] - 1, v = edge[1] - 1;
            require(u >= 0 && v >= 0 && u < n && v < n, "Course IDs must be between 1 and N.");
            require(u != v, "A course cannot conflict with itself.");
            if (!adjacency[u][v]) {
                adjacency[u][v] = adjacency[v][u] = true;
                unique.add(new int[]{Math.min(u, v) + 1, Math.max(u, v) + 1});
            }
        }
        unique.sort(Comparator.<int[]>comparingInt(a -> a[0]).thenComparingInt(a -> a[1]));
        return new Graph(n, halls, adjacency, unique.toArray(int[][]::new));
    }

    public static Graph parse(String text) {
        Scanner scanner = new Scanner(text);
        try {
            int n = scanner.nextInt(), m = scanner.nextInt(), halls = scanner.nextInt();
            require(m >= 0 && m <= 40000, "M must be between 0 and 40000.");
            List<int[]> edges = new ArrayList<>();
            for (int i = 0; i < m; i++) edges.add(new int[]{scanner.nextInt(), scanner.nextInt()});
            require(!scanner.hasNext(), "Extra input after the M conflict rows.");
            return graph(n, halls, edges);
        } catch (NoSuchElementException e) {
            throw new IllegalArgumentException("Expected N M R, followed by exactly M pairs of integer course IDs.");
        } finally { scanner.close(); }
    }

    public static Graph randomGraph(int n, int halls, double density, long seed) {
        require(Double.isFinite(density) && density >= 0 && density <= 1, "Density must be from 0 to 1.");
        require(n >= 0 && n <= 200, "N must be between 0 and 200.");
        Random random = new Random(seed);
        List<int[]> edges = new ArrayList<>();
        for (int u = 1; u <= n; u++) for (int v = u + 1; v <= n; v++)
            if (random.nextDouble() < density) edges.add(new int[]{u, v});
        return graph(n, halls, edges);
    }

    static int[] degrees(Graph g) {
        int[] degree = new int[g.n];
        for (int u = 0; u < g.n; u++) for (boolean conflict : g.conflicts[u]) if (conflict) degree[u]++;
        return degree;
    }

    /** Choose unassigned course with highest saturation, then degree, then lowest ID. */
    static int choose(Graph g, int[] colors, int[] degree) {
        int chosen = -1, maximum = -1;
        boolean[] seen = new boolean[g.n + 1];
        for (int u = 0; u < g.n; u++) if (colors[u] == 0) {
            Arrays.fill(seen, false);
            int saturation = 0;
            for (int v = 0; v < g.n; v++) if (g.conflicts[u][v] && colors[v] != 0 && !seen[colors[v]]) {
                seen[colors[v]] = true; saturation++;
            }
            if (chosen < 0 || saturation > maximum || saturation == maximum && degree[u] > degree[chosen]) {
                chosen = u; maximum = saturation;
            }
        }
        return chosen;
    }

    static boolean fits(Graph g, int course, int slot, int[] colors, int[] loads) {
        if (loads[slot] >= g.halls) return false;
        for (int v = 0; v < g.n; v++) if (g.conflicts[course][v] && colors[v] == slot) return false;
        return true;
    }

    /** Valid lower bound from capacity and a constructed clique (not a maximum-clique claim). */
    static int lowerBound(Graph g, int[] degree) {
        int lower = (g.n + g.halls - 1) / g.halls;
        Integer[] order = new Integer[g.n];
        for (int i = 0; i < g.n; i++) order[i] = i;
        Arrays.sort(order, Comparator.<Integer>comparingInt(i -> degree[i]).reversed().thenComparingInt(i -> i));
        for (int seed : order) {
            List<Integer> clique = new ArrayList<>(); clique.add(seed);
            for (int v : order) if (v != seed) {
                boolean joins = true;
                for (int u : clique) if (!g.conflicts[u][v]) { joins = false; break; }
                if (joins) clique.add(v);
            }
            lower = Math.max(lower, clique.size());
        }
        return lower;
    }

    static Result result(String name, Graph graph, int slots, boolean optimal, boolean timeout,
                         int lower, int[] assignment, List<Event> events, long started, long nodes) {
        return new Result(name, slots, optimal, timeout, lower, assignment.clone(), List.copyOf(events),
                          (System.nanoTime() - started) / 1_000_000.0, nodes, csv(graph, assignment, slots));
    }

    public static Result greedy(Graph g) {
        long start = System.nanoTime();
        int[] degree = degrees(g), colors = new int[g.n], loads = new int[g.n + 1];
        int lower = lowerBound(g, degree), slots = 0;
        List<Event> events = new ArrayList<>();
        for (int i = 0; i < g.n; i++) {
            int u = choose(g, colors, degree), slot = 1;
            while (slot <= slots && !fits(g, u, slot, colors, loads)) slot++;
            slots = Math.max(slots, slot); colors[u] = slot; loads[slot]++;
            events.add(new Event(u + 1, slot));
        }
        return result("DSatur greedy", g, slots, slots == lower, false, lower, colors, events, start, g.n);
    }

    static final class Search {
        final Graph g;
        final int[] degree, colors, loads;
        final int lower;
        final long deadline;
        int bestSlots;
        int[] best;
        List<Event> bestOrder;
        final List<Event> path = new ArrayList<>();
        long nodes;
        boolean timedOut;
        Search(Graph g, Result initial, long deadline) {
            this.g = g; this.degree = degrees(g); this.colors = new int[g.n]; this.loads = new int[g.n + 1];
            this.lower = initial.lowerBound; this.bestSlots = initial.slots; this.best = initial.assignment.clone();
            this.bestOrder = initial.events; this.deadline = deadline;
        }
        void visit(int assigned, int used) {
            if (bestSlots == lower || timedOut) return;
            if (System.nanoTime() >= deadline) { timedOut = true; return; }
            nodes++;
            if (assigned == g.n) {
                bestSlots = used; best = colors.clone(); bestOrder = List.copyOf(path); return;
            }
            int free = 0;
            for (int slot = 1; slot <= used; slot++) free += g.halls - loads[slot];
            int extra = Math.max(0, g.n - assigned - free);
            if (used + (extra + g.halls - 1) / g.halls >= bestSlots) return;
            int course = choose(g, colors, degree);
            // Existing slot labels matter only through their members. A new slot
            // has one canonical label, eliminating permutations of empty slots.
            for (int slot = 1; slot <= used + 1 && slot < bestSlots; slot++) {
                if (!fits(g, course, slot, colors, loads)) continue;
                colors[course] = slot; loads[slot]++; path.add(new Event(course + 1, slot));
                visit(assigned + 1, Math.max(used, slot));
                path.remove(path.size() - 1); loads[slot]--; colors[course] = 0;
                if (timedOut || bestSlots == lower) return;
            }
        }
    }

    public static Result exact(Graph graph, long timeLimitMs) {
        require(timeLimitMs >= 0 && timeLimitMs <= 60000, "Exact search budget must be 0–60000 ms.");
        long started = System.nanoTime();
        // Include initialization/greedy incumbent in the exact algorithm's timing.
        Result initial = greedy(graph);
        Search search = new Search(graph, initial, started + timeLimitMs * 1_000_000L);
        search.visit(0, 0);
        boolean optimal = search.bestSlots == search.lower || !search.timedOut;
        return result("Exact branch & bound", graph, search.bestSlots, optimal, search.timedOut,
                      optimal ? search.bestSlots : search.lower, search.best, search.bestOrder, started, search.nodes);
    }

    public static Comparison compare(Graph graph, long budgetMs) {
        Result first = greedy(graph), second = exact(graph, budgetMs);
        // A completed exact search may also certify the greedy result.
        if (second.optimal && first.slots == second.slots && !first.optimal)
            first = new Result(first.algorithm, first.slots, true, false, second.slots, first.assignment,
                               first.events, first.timeMs, first.searchNodes, first.csv);
        return new Comparison(graph, first, second);
    }

    public static String csv(Graph g, int[] colors, int slots) {
        StringBuilder csv = new StringBuilder("Slot");
        for (int hall = 1; hall <= g.halls; hall++) csv.append(",Hall ").append(hall);
        csv.append('\n');
        for (int slot = 1; slot <= slots; slot++) {
            csv.append("Slot ").append(slot); int count = 0;
            for (int course = 0; course < g.n; course++) if (colors[course] == slot) {
                csv.append(',').append(course + 1); count++;
            }
            while (count++ < g.halls) csv.append(',');
            csv.append('\n');
        }
        return csv.toString();
    }

    static Map<String, Object> resultMap(Result r) {
        List<Map<String, Object>> events = new ArrayList<>();
        for (Event event : r.events) events.add(Map.of("course", event.course, "slot", event.slot));
        return Map.ofEntries(Map.entry("algorithm", r.algorithm), Map.entry("slots", r.slots),
            Map.entry("optimal", r.optimal), Map.entry("timedOut", r.timedOut), Map.entry("lowerBound", r.lowerBound),
            Map.entry("assignment", r.assignment), Map.entry("events", events), Map.entry("timeMs", r.timeMs),
            Map.entry("searchNodes", r.searchNodes), Map.entry("csv", r.csv));
    }
    static Map<String, Object> graphMap(Graph g) { return Map.of("n", g.n, "halls", g.halls, "edges", g.edges); }
    static Map<String, Object> comparisonMap(Comparison c) {
        return Map.of("graph", graphMap(c.graph), "greedy", resultMap(c.greedy), "exact", resultMap(c.exact));
    }

    /** Small JSON writer; requests use URL-encoded forms, so no JSON parser is needed. */
    public static String json(Object value) {
        if (value == null) return "null";
        if (value instanceof String text) {
            StringBuilder result = new StringBuilder("\"");
            for (char ch : text.toCharArray()) switch (ch) {
                case '"' -> result.append("\\\""); case '\\' -> result.append("\\\\");
                case '\n' -> result.append("\\n"); case '\r' -> result.append("\\r"); case '\t' -> result.append("\\t");
                default -> { if (ch < 32) result.append(String.format("\\u%04x", (int) ch)); else result.append(ch); }
            }
            return result.append('"').toString();
        }
        if (value instanceof Number || value instanceof Boolean) return value.toString();
        if (value instanceof Map<?, ?> map) {
            StringJoiner join = new StringJoiner(",", "{", "}");
            map.forEach((k, v) -> join.add(json(k.toString()) + ":" + json(v))); return join.toString();
        }
        if (value instanceof Iterable<?> list) {
            StringJoiner join = new StringJoiner(",", "[", "]");
            for (Object item : list) join.add(json(item)); return join.toString();
        }
        if (value.getClass().isArray()) {
            StringJoiner join = new StringJoiner(",", "[", "]");
            for (int i = 0; i < java.lang.reflect.Array.getLength(value); i++) join.add(json(java.lang.reflect.Array.get(value, i)));
            return join.toString();
        }
        throw new IllegalArgumentException("Unsupported JSON value.");
    }

    static int intField(Map<String, String> data, String key, int fallback) { return Integer.parseInt(data.getOrDefault(key, Integer.toString(fallback))); }
    static long longField(Map<String, String> data, String key, long fallback) { return Long.parseLong(data.getOrDefault(key, Long.toString(fallback))); }
    static Graph formGraph(Map<String, String> data) {
        int n = intField(data, "n", 10), halls = intField(data, "halls", 3);
        require(n <= 60 && halls <= 20, "The visualizer supports at most 60 courses and 20 halls.");
        String edges = data.getOrDefault("edges", "").trim();
        String[] lines = edges.isEmpty() ? new String[0] : edges.split("\\R");
        List<int[]> pairs = new ArrayList<>();
        for (String line : lines) {
            if (line.isBlank()) continue;
            String[] tokens = line.trim().split("[\\s,]+");
            require(tokens.length == 2, "Each row needs two course IDs: u,v.");
            pairs.add(new int[]{Integer.parseInt(tokens[0]), Integer.parseInt(tokens[1])});
        }
        return graph(n, halls, pairs);
    }

    public static Object api(String path, Map<String, String> data) {
        return switch (path) {
            case "/api/solve" -> comparisonMap(compare(formGraph(data), longField(data, "budget", 2000)));
            case "/api/generate" -> {
                int n = intField(data, "n", 10), halls = intField(data, "halls", 3);
                require(n <= 60 && halls <= 20, "The visualizer supports at most 60 courses and 20 halls.");
                yield graphMap(randomGraph(n, halls, Double.parseDouble(data.getOrDefault("density", ".3")), longField(data, "seed", 42)));
            }
            case "/api/benchmark" -> {
                int n = intField(data, "n", 10), halls = intField(data, "halls", 3);
                require(n >= 1 && n <= 60 && halls <= 20, "Benchmark supports 1–60 courses and up to 20 halls.");
                Graph graph = randomGraph(n, halls, Double.parseDouble(data.getOrDefault("density", ".3")), longField(data, "seed", 42));
                Comparison c = compare(graph, longField(data, "budget", 1000));
                yield Map.of("n", n, "edges", graph.edges.length, "greedy", resultMap(c.greedy), "exact", resultMap(c.exact));
            }
            default -> throw new IllegalArgumentException("Unknown API endpoint.");
        };
    }

    static void send(HttpExchange exchange, int status, String type, byte[] content) throws IOException {
        exchange.getResponseHeaders().set("Content-Type", type);
        exchange.getResponseHeaders().set("Cache-Control", "no-store");
        exchange.getResponseHeaders().set("X-Content-Type-Options", "nosniff");
        exchange.sendResponseHeaders(status, content.length);
        try (OutputStream out = exchange.getResponseBody()) { out.write(content); }
    }
    static void sendJson(HttpExchange exchange, int status, Object value) throws IOException {
        send(exchange, status, "application/json; charset=utf-8", json(value).getBytes(StandardCharsets.UTF_8));
    }
    static void serve(Path root, int port) throws IOException {
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", port), 0);
        server.createContext("/", exchange -> {
            try {
                String path = exchange.getRequestURI().getPath();
                if (path.startsWith("/api/")) {
                    if (!exchange.getRequestMethod().equals("POST")) { sendJson(exchange, 405, Map.of("error", "Use POST.")); return; }
                    byte[] bytes = exchange.getRequestBody().readNBytes(100001);
                    require(bytes.length <= 100000, "Request must be smaller than 100 KB.");
                    Map<String, String> fields = new HashMap<>();
                    for (String part : new String(bytes, StandardCharsets.UTF_8).split("&")) if (!part.isEmpty()) {
                        String[] pair = part.split("=", 2);
                        fields.put(URLDecoder.decode(pair[0], StandardCharsets.UTF_8), URLDecoder.decode(pair.length > 1 ? pair[1] : "", StandardCharsets.UTF_8));
                    }
                    sendJson(exchange, 200, api(path, fields));
                } else {
                    if (!exchange.getRequestMethod().equals("GET")) { sendJson(exchange, 405, Map.of("error", "Use GET.")); return; }
                    Path file = root.resolve(path.equals("/") ? "index.html" : path.substring(1)).normalize();
                    if (!file.startsWith(root) || !Files.isRegularFile(file)) { sendJson(exchange, 404, Map.of("error", "Not found.")); return; }
                    String type = path.endsWith(".js") ? "text/javascript" : path.endsWith(".css") ? "text/css" : "text/html";
                    send(exchange, 200, type + "; charset=utf-8", Files.readAllBytes(file));
                }
            } catch (IllegalArgumentException error) { sendJson(exchange, 400, Map.of("error", error.getMessage() == null ? "Invalid input." : error.getMessage())); }
        });
        server.setExecutor(Executors.newFixedThreadPool(4));
        server.start();
        System.out.println("ExamSlot: http://127.0.0.1:" + port);
    }

    static Map<String, String> options(String[] args) {
        Map<String, String> result = new HashMap<>();
        for (int i = 1; i < args.length; i += 2) {
            require(args[i].startsWith("--") && i + 1 < args.length, "Options require --name value pairs.");
            String key = args[i].substring(2);
            require(Set.of("port", "static", "budget", "out", "density", "seed", "sizes", "halls").contains(key), "Unknown option: " + key);
            result.put(key, args[i + 1]);
        }
        return result;
    }
    static void printResult(Result result) {
        System.out.printf(Locale.ROOT, "%s: %d slots; proven optimal: %s; time: %.6f ms%s%n",
            result.algorithm, result.slots, result.optimal ? "yes" : "no", result.timeMs,
            result.timedOut ? "; time limit reached (best found)" : "");
        for (int slot = 1; slot <= result.slots; slot++) {
            StringJoiner courses = new StringJoiner(", ");
            for (int i = 0; i < result.assignment.length; i++) if (result.assignment[i] == slot) courses.add(Integer.toString(i + 1));
            System.out.println("Slot " + slot + ": " + courses);
        }
    }
    public static void main(String[] args) {
        try {
            String command = args.length == 0 ? "serve" : args[0];
            Map<String, String> opts = options(args);
            if (command.equals("serve")) {
                Path classes = Path.of(ExamScheduler.class.getProtectionDomain().getCodeSource().getLocation().toURI());
                Path root = Path.of(opts.getOrDefault("static", classes.resolveSibling("static").toString())).toAbsolutePath().normalize();
                require(Files.isDirectory(root), "Static directory not found; run with the supplied run.sh script.");
                serve(root, intField(opts, "port", 8003));
            } else if (command.equals("solve") || command.equals("random")) {
                String input = new String(System.in.readAllBytes(), StandardCharsets.UTF_8);
                Graph graph;
                if (command.equals("solve")) graph = parse(input);
                else {
                    String[] values = input.trim().split("\\s+");
                    require(values.length == 2, "Random input must contain exactly N R.");
                    graph = randomGraph(Integer.parseInt(values[0]), Integer.parseInt(values[1]),
                        Double.parseDouble(opts.getOrDefault("density", ".3")), longField(opts, "seed", 42));
                }
                Comparison comparison = compare(graph, longField(opts, "budget", 5000));
                printResult(comparison.greedy); printResult(comparison.exact);
                Path out = Path.of(opts.getOrDefault("out", ".")); Files.createDirectories(out);
                Files.writeString(out.resolve("greedy_timetable.csv"), comparison.greedy.csv);
                Files.writeString(out.resolve("exact_timetable.csv"), comparison.exact.csv);
                Files.writeString(out.resolve("comparison.json"), json(comparisonMap(comparison)));
            } else if (command.equals("benchmark")) {
                BenchmarkReport.run(opts);
            } else throw new IllegalArgumentException("Use serve, solve, random, or benchmark. See README.md for options.");
        } catch (Exception error) {
            System.err.println("Error: " + error.getMessage()); System.exit(2);
        }
    }
}
