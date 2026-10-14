import java.nio.file.*;
import java.util.*;

/** CLI performance comparison with a portable CSV and standalone SVG. */
public final class BenchmarkReport {
    record Row(int n, int edges, ExamScheduler.Result greedy, ExamScheduler.Result exact) {}

    public static void run(Map<String, String> options) throws Exception {
        int halls = ExamScheduler.intField(options, "halls", 3);
        double density = Double.parseDouble(options.getOrDefault("density", ".35"));
        long seed = ExamScheduler.longField(options, "seed", 42);
        long budget = ExamScheduler.longField(options, "budget", 500);
        String[] parts = options.getOrDefault("sizes", "6,8,10,12,16,20,24").split(",", -1);
        ExamScheduler.require(parts.length >= 1 && parts.length <= 12, "Provide 1–12 benchmark sizes.");
        SortedSet<Integer> sizes = new TreeSet<>();
        for (String part : parts) {
            int n = Integer.parseInt(part.trim());
            ExamScheduler.require(n >= 1 && n <= 200, "Benchmark sizes must be from 1 to 200.");
            sizes.add(n);
        }
        // A small, fixed warm-up reduces first-call class loading effects.
        for (int i = 0; i < 8; i++) ExamScheduler.compare(ExamScheduler.randomGraph(8, halls, density, seed + i), budget);
        List<Row> rows = new ArrayList<>();
        StringBuilder csv = new StringBuilder("N,conflicts,R,density,seed,exact_budget_ms,greedy_slots,exact_slots,greedy_ms,exact_ms,greedy_optimal,exact_optimal,exact_lower_bound,timed_out\n");
        for (int n : sizes) {
            long graphSeed = seed + n * 31L;
            var graph = ExamScheduler.randomGraph(n, halls, density, graphSeed);
            var comparison = ExamScheduler.compare(graph, budget);
            var greedy = comparison.greedy(); var exact = comparison.exact();
            rows.add(new Row(n, graph.edges().length, greedy, exact));
            csv.append(String.format(Locale.ROOT, "%d,%d,%d,%.4f,%d,%d,%d,%d,%.6f,%.6f,%s,%s,%d,%s%n",
                n, graph.edges().length, halls, density, graphSeed, budget, greedy.slots(), exact.slots(),
                greedy.timeMs(), exact.timeMs(), greedy.optimal(), exact.optimal(), exact.lowerBound(), exact.timedOut()));
        }
        Path out = Path.of(options.getOrDefault("out", ".")); Files.createDirectories(out);
        Files.writeString(out.resolve("benchmark.csv"), csv);
        Files.writeString(out.resolve("benchmark.svg"), svg(rows, halls, density, seed, budget));
        System.out.print(csv);
        System.out.println("Saved " + out.resolve("benchmark.csv") + " and " + out.resolve("benchmark.svg"));
    }

    static String svg(List<Row> rows, int halls, double density, long seed, long budget) {
        StringBuilder out = new StringBuilder("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"1100\" height=\"480\" viewBox=\"0 0 1100 480\"><rect width=\"1100\" height=\"480\" fill=\"white\"/><g font-family=\"Arial,sans-serif\" fill=\"#485c7b\">");
        out.append("<text x=\"35\" y=\"32\" font-size=\"21\">Exam timetabling · measured algorithm comparison</text>");
        out.append(String.format(Locale.ROOT, "<text x=\"35\" y=\"56\" font-size=\"11\">R=%d · density=%.0f%% · seed=%d · exact budget=%d ms · one measured run per graph after warm-up</text>", halls, density * 100, seed, budget));
        int maxN = rows.stream().mapToInt(Row::n).max().orElse(1);
        for (int chart = 0; chart < 2; chart++) {
            double x0 = chart == 0 ? 65 : 610, width = 450, top = 115, bottom = 355;
            double maxY = 0;
            for (Row row : rows) maxY = Math.max(maxY, chart == 0 ? Math.max(row.greedy.slots(), row.exact.slots()) : Math.max(row.greedy.timeMs(), row.exact.timeMs()));
            maxY = Math.max(maxY, .001);
            out.append(String.format(Locale.ROOT, "<text x=\"%.1f\" y=\"91\" font-size=\"14\">%s</text>", x0, chart == 0 ? "Slots used" : "Running time (ms)"));
            for (int i = 0; i <= 4; i++) {
                double y = bottom - (bottom-top) * i / 4;
                out.append(String.format(Locale.ROOT, "<path d=\"M%.1f %.1fH%.1f\" stroke=\"#e6ebf4\"/><text x=\"%.1f\" y=\"%.1f\" text-anchor=\"end\" font-size=\"10\">%.2f</text>", x0, y, x0+width, x0-9, y+3, maxY*i/4));
            }
            for (int algorithm = 0; algorithm < 2; algorithm++) {
                String color = algorithm == 0 ? "#dc8c5d" : "#6289ce";
                StringBuilder line = new StringBuilder();
                StringBuilder dots = new StringBuilder();
                for (Row row : rows) {
                    var result = algorithm == 0 ? row.greedy : row.exact;
                    double x = x0 + (double)row.n / maxN * width;
                    double y = bottom - (chart == 0 ? result.slots() : result.timeMs()) / maxY * (bottom - top);
                    line.append(String.format(Locale.ROOT, "%.2f,%.2f ", x,y));
                    dots.append(String.format(Locale.ROOT, "<circle cx=\"%.2f\" cy=\"%.2f\" r=\"%d\" fill=\"%s\" stroke=\"%s\" stroke-width=\"2\"/>", x,y,algorithm == 0 ? 5 : 3, algorithm == 1 && !result.optimal() ? "white" : color,color));
                }
                out.append("<polyline points=\"").append(line).append("\" fill=\"none\" stroke=\"").append(color).append("\" stroke-width=\"").append(algorithm == 0 ? 4 : 2).append("\"");
                if (algorithm == 1) out.append(" stroke-dasharray=\"6 3\"");
                out.append("/>").append(dots);
            }
            for (Row row : rows) out.append(String.format(Locale.ROOT, "<text x=\"%.2f\" y=\"377\" text-anchor=\"middle\" font-size=\"10\">%d</text>", x0 + (double)row.n/maxN*width, row.n));
            out.append(String.format(Locale.ROOT, "<text x=\"%.1f\" y=\"401\" text-anchor=\"middle\" font-size=\"12\">Courses (N)</text>", x0+width/2));
        }
        out.append("<circle cx=\"65\" cy=\"443\" r=\"5\" fill=\"#dc8c5d\"/><text x=\"77\" y=\"447\" font-size=\"12\">DSatur greedy</text><circle cx=\"250\" cy=\"443\" r=\"5\" fill=\"#6289ce\"/><text x=\"262\" y=\"447\" font-size=\"12\">Branch &amp; bound</text><text x=\"470\" y=\"447\" font-size=\"11\">Hollow exact markers: optimality not proved before timeout.</text></g></svg>");
        return out.toString();
    }
}
