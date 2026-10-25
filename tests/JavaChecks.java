import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Random;

public class JavaChecks {
    static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    static Map<String, Object> request(int n, int[][] edges, int source) {
        List<List<Integer>> rows = new ArrayList<>();
        for (int[] edge : edges) rows.add(List.of(edge[0], edge[1], edge[2]));
        return Map.of("n", n, "edges", rows, "source", source);
    }

    static void route(String name, int source, int target, int[][] edges,
                      Map<String, Object> result, List<Integer> expected) {
        int[] parents = (int[]) result.get("parent_edge");
        Long[] distances = (Long[]) result.get("distance");
        List<Integer> path = Algorithms.reconstructRoute(source, target, edges, parents);
        require(path.equals(expected), name + " route");
        List<Integer> ids = new ArrayList<>();
        long cost = 0;
        for (int i = 1; i < path.size(); i++) {
            int id = parents[path.get(i)];
            require(edges[id][0] == path.get(i - 1) && edges[id][1] == path.get(i), name + " direction");
            ids.add(id);
            cost += edges[id][2];
        }
        if (!path.isEmpty()) require(cost == distances[target], name + " cost");
        else require(distances[target] == null, name + " unreachable");
        System.out.println(name + ": reconstructRoute(" + source + ", " + target
                + ", edges, parentEdge) = " + path + "; edge_ids=" + ids
                + "; cost=" + (path.isEmpty() ? "null" : cost));
    }

    static void routes() {
        int[][] edges = {{0,1,3}, {0,2,8}, {1,2,-7}, {2,3,4}};
        Map<String, Object> result = Algorithms.dag(request(5, edges, 0));
        System.out.println("Example parent_edge=" + Arrays.toString((int[]) result.get("parent_edge")));
        route("reachable", 0, 3, edges, result, List.of(0,1,2,3));
        route("source", 0, 0, edges, result, List.of(0));
        route("unreachable", 0, 4, edges, result, List.of());

        int[][] tied = {{0,1,2}, {0,1,2}, {0,2,2}, {1,3,3}, {2,3,3}};
        result = Algorithms.dag(request(5, tied, 0));
        System.out.println("Tied parent_edge=" + Arrays.toString((int[]) result.get("parent_edge")));
        // DFS visits 1 before 2, so reverse finish order processes 2 before 1.
        route("parallel", 0, 1, tied, result, List.of(0,1));
        route("tied", 0, 3, tied, result, List.of(0,2,3));

        int n = 100000;
        int[][] chain = new int[n - 1][3];
        for (int i = 0; i < n - 1; i++) chain[i] = new int[]{i, i + 1, -1000000000};
        result = Algorithms.dag(request(n, chain, 0));
        List<Integer> longRoute = Algorithms.reconstructRoute(0, n - 1, chain, (int[]) result.get("parent_edge"));
        require(longRoute.size() == n, "deep route length");
        for (int i = 0; i < n; i++) require(longRoute.get(i) == i, "deep route vertex");
        require(((Long[]) result.get("distance"))[n - 1] == -99999000000000L, "deep route cost");
        System.out.println("PASS deep route: 100000 vertices; cost=-99999000000000");
    }

    static int[][] graph(int n, int m, long seed) {
        Random random = new Random(seed);
        int[][] edges = new int[m][3];
        // This chain is the unique cheapest tree: all other edges are heavier.
        for (int i = 0; i < n - 1; i++) edges[i] = new int[]{i, i + 1, -1000000000};
        for (int i = n - 1; i < m; i++) {
            edges[i] = new int[]{random.nextInt(n), random.nextInt(n), random.nextInt(2000000000) - 999999999};
        }
        for (int i = m - 1; i > 0; i--) {
            int j = random.nextInt(i + 1);
            int[] temp = edges[i];
            edges[i] = edges[j];
            edges[j] = temp;
        }
        return edges;
    }

    static void checkForest(int n, int[][] edges, Map<String, Object> result) {
        List<?> ids = (List<?>) result.get("edge_ids");
        require(((Number) result.get("components")).intValue() == 1, "connected graph");
        require(ids.size() == n - 1, "tree edge count");
        boolean[] used = new boolean[edges.length];
        List<List<Integer>> graph = new ArrayList<>();
        for (int i = 0; i < n; i++) graph.add(new ArrayList<>());
        long cost = 0;
        for (Object value : ids) {
            int id = ((Number) value).intValue();
            require(id >= 0 && id < edges.length && !used[id], "unique valid edge IDs");
            used[id] = true;
            int u = edges[id][0];
            int v = edges[id][1];
            require(u != v, "no self loops");
            graph.get(u).add(v);
            graph.get(v).add(u);
            cost += edges[id][2];
        }
        // Connectivity plus n-1 distinct edges proves that the witness is a tree.
        boolean[] visited = new boolean[n];
        int[] queue = new int[n];
        int end = 1;
        visited[0] = true;
        for (int i = 0; i < end; i++) {
            for (int v : graph.get(queue[i])) {
                if (!visited[v]) {
                    visited[v] = true;
                    queue[end++] = v;
                }
            }
        }
        require(end == n, "tree spans every vertex");
        require(cost == -(n - 1L) * 1000000000L, "independently known optimum");
        require(((Number) result.get("cost")).longValue() == cost, "reported cost");
    }

    static Map<String, Object> solve(int method, Map<String, Object> input) {
        return method == 0 ? Algorithms.kruskal(input) : Algorithms.prim(input);
    }

    static void benchmark() {
        System.out.println("java=" + System.getProperty("java.version") + "; vm=" + System.getProperty("java.vm.name"));
        System.out.println("os=" + System.getProperty("os.name") + " " + System.getProperty("os.version")
                + "; arch=" + System.getProperty("os.arch") + "; logical_cpus=" + Runtime.getRuntime().availableProcessors());
        System.out.println("timer=System.nanoTime; warmup=5 per method per size; measured=5; heap=-Xmx384m");
        System.out.println("Includes Input.edges conversion, algorithm data structures and result allocation; excludes generation, JSON parsing, serialization, validation and compilation.");
        for (int n : new int[]{1000, 10000, 100000}) {
            int m = n * 5 / 2;
            long seed = 250542L + n;
            int[][] edges = graph(n, m, seed);
            Map<String, Object> input = request(n, edges, 0);
            for (int method = 0; method < 2; method++) checkForest(n, edges, solve(method, input));
            for (int i = 0; i < 5; i++) {
                for (int method = 0; method < 2; method++) checkForest(n, edges, solve(method, input));
            }
            double[][] times = new double[2][5];
            for (int round = 0; round < 5; round++) {
                // Alternate first method to reduce a fixed execution-order advantage.
                for (int offset = 0; offset < 2; offset++) {
                    int method = (round + offset) % 2;
                    long start = System.nanoTime();
                    Map<String, Object> result = solve(method, input);
                    times[method][round] = (System.nanoTime() - start) / 1000000.0;
                    checkForest(n, edges, result);
                }
            }
            for (int method = 0; method < 2; method++) {
                double[] sorted = times[method].clone();
                Arrays.sort(sorted);
                System.out.printf(Locale.ROOT, "n=%d m=%d seed=%d method=%s ms=%s median_ms=%.6f cost=%d verified=true%n",
                        n, m, seed, method == 0 ? "kruskal" : "prim", Arrays.toString(times[method]), sorted[2], -(n - 1L) * 1000000000L);
            }
        }
    }

    public static void main(String[] args) {
        if (args.length > 0 && args[0].equals("benchmark")) benchmark();
        else routes();
    }
}
