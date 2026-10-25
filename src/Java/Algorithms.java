import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.PriorityQueue;
import java.util.Set;

public final class Algorithms {
    static class DSU {
        final int[] parent;
        final int[] size;
        int components;
        int largest;

        DSU(int n) {
            parent = new int[n];
            size = new int[n];
            components = n;
            largest = n == 0 ? 0 : 1;
            for (int i = 0; i < n; i++) {
                parent[i] = i;
                size[i] = 1;
            }
        }

        int find(int vertex) {
            int root = vertex;
            while (root != parent[root]) root = parent[root];
            while (vertex != root) {
                int next = parent[vertex];
                parent[vertex] = root;
                vertex = next;
            }
            return root;
        }

        boolean union(int u, int v) {
            int a = find(u);
            int b = find(v);
            if (a == b) return false;
            if (size[a] < size[b]) {
                int temp = a;
                a = b;
                b = temp;
            }
            parent[b] = a;
            size[a] += size[b];
            components--;
            largest = Math.max(largest, size[a]);
            return true;
        }
    }

    static Map<String, Object> dsu(Map<String, Object> input) {
        int n = Input.vertexCount(input);
        int[][] operations = Input.operations(input);
        DSU sets = new DSU(n);
        int[][] states = new int[operations.length][2];
        for (int i = 0; i < operations.length; i++) {
            sets.union(operations[i][0], operations[i][1]);
            states[i][0] = sets.components;
            states[i][1] = sets.largest;
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("states", states);
        return result;
    }

    static Map<String, Object> kruskal(Map<String, Object> input) {
        int n = Input.vertexCount(input);
        int[][] edges = Input.edges(input);
        Integer[] order = new Integer[edges.length];
        for (int i = 0; i < edges.length; i++) order[i] = i;
        // Sort IDs, so each edge keeps its original input position.
        Arrays.sort(order, Comparator.comparingInt((Integer id) -> edges[id][2])
                .thenComparingInt(id -> id));

        DSU sets = new DSU(n);
        List<Integer> selected = new ArrayList<>();
        long cost = 0;
        for (int id : order) {
            int[] edge = edges[id];
            if (sets.union(edge[0], edge[1])) {
                selected.add(id);
                cost += edge[2];
            }
        }
        return forestResult(cost, selected, sets.components);
    }

    static Map<String, Object> prim(Map<String, Object> input) {
        int n = Input.vertexCount(input);
        int[][] edges = Input.edges(input);
        List<List<Integer>> graph = adjacency(n, edges, true);
        boolean[] visited = new boolean[n];
        PriorityQueue<Integer> queue = new PriorityQueue<>(
                Comparator.comparingInt((Integer id) -> edges[id][2]).thenComparingInt(id -> id));
        List<Integer> selected = new ArrayList<>();
        long cost = 0;
        int components = 0;

        for (int start = 0; start < n; start++) {
            if (visited[start]) continue;
            components++;
            visited[start] = true;
            queue.addAll(graph.get(start));
            while (!queue.isEmpty()) {
                int id = queue.remove();
                int u = edges[id][0];
                int v = edges[id][1];
                if (visited[u] && visited[v]) continue;
                int next = visited[u] ? v : u;
                visited[next] = true;
                selected.add(id);
                cost += edges[id][2];
                for (int other : graph.get(next)) {
                    int a = edges[other][0];
                    int b = edges[other][1];
                    if (!visited[a] || !visited[b]) queue.add(other);
                }
            }
        }
        return forestResult(cost, selected, components);
    }

    private static Map<String, Object> forestResult(long cost, List<Integer> ids, int components) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("cost", cost);
        result.put("edge_ids", ids);
        result.put("components", components);
        return result;
    }

    // Adjacency lists store edge IDs. Directed lists contain outgoing edges only.
    private static List<List<Integer>> adjacency(int n, int[][] edges, boolean undirected) {
        List<List<Integer>> graph = new ArrayList<>(n);
        for (int i = 0; i < n; i++) graph.add(new ArrayList<>());
        for (int id = 0; id < edges.length; id++) {
            int u = edges[id][0];
            int v = edges[id][1];
            graph.get(u).add(id);
            if (undirected && u != v) graph.get(v).add(id);
        }
        return graph;
    }

    static Map<String, Object> scc(Map<String, Object> input) {
        int n = Input.vertexCount(input);
        int[][] edges = Input.edges(input);
        List<List<Integer>> graph = adjacency(n, edges, false);
        List<List<Integer>> reverse = new ArrayList<>(n);
        for (int i = 0; i < n; i++) reverse.add(new ArrayList<>());
        for (int[] edge : edges) reverse.get(edge[1]).add(edge[0]);

        // First pass: finish order in the original graph. Cycles are allowed here.
        int[] order = dfsOrder(graph, edges, false);
        int[] component = new int[n];
        Arrays.fill(component, -1);
        int[] stack = new int[n];
        int label = 0;
        for (int start : order) {
            if (component[start] != -1) continue;
            int top = 0;
            stack[top++] = start;
            component[start] = label;
            while (top > 0) {
                int u = stack[--top];
                for (int v : reverse.get(u)) {
                    if (component[v] == -1) {
                        component[v] = label;
                        stack[top++] = v;
                    }
                }
            }
            label++;
        }

        List<int[]> condensation = new ArrayList<>();
        Set<Long> seen = new HashSet<>();
        for (int[] edge : edges) {
            int from = component[edge[0]];
            int to = component[edge[1]];
            if (from == to) continue;
            long pair = ((long) from << 32) | (to & 0xffffffffL);
            if (seen.add(pair)) condensation.add(new int[]{from, to});
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("component", component);
        result.put("condensation", condensation);
        return result;
    }

    // Each stack entry remembers its next neighbour through nextEdge[u].
    // Returning null means a cycle was found when cycle checking was requested.
    private static int[] dfsOrder(List<List<Integer>> graph, int[][] edges, boolean checkCycle) {
        int n = graph.size();
        int[] state = new int[n]; // 0 = unvisited, 1 = active, 2 = finished
        int[] nextEdge = new int[n];
        int[] stack = new int[n];
        int[] order = new int[n];
        int position = n - 1;
        for (int start = 0; start < n; start++) {
            if (state[start] != 0) continue;
            int top = 0;
            stack[top++] = start;
            state[start] = 1;
            while (top > 0) {
                int u = stack[top - 1];
                if (nextEdge[u] == graph.get(u).size()) {
                    state[u] = 2;
                    order[position--] = u;
                    top--;
                } else {
                    int id = graph.get(u).get(nextEdge[u]++);
                    int v = edges[id][1];
                    if (state[v] == 1 && checkCycle) return null;
                    if (state[v] == 0) {
                        state[v] = 1;
                        stack[top++] = v;
                    }
                }
            }
        }
        return order;
    }

    static Map<String, Object> topo(Map<String, Object> input) {
        int n = Input.vertexCount(input);
        int[][] edges = Input.edges(input);
        int[] order = dfsOrder(adjacency(n, edges, false), edges, true);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("acyclic", order != null);
        result.put("order", order == null ? new int[0] : order);
        return result;
    }

    static Map<String, Object> dag(Map<String, Object> input) {
        int n = Input.vertexCount(input);
        int source = Input.source(input);
        int[][] edges = Input.edges(input);
        List<List<Integer>> graph = adjacency(n, edges, false);
        int[] order = dfsOrder(graph, edges, true);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("acyclic", order != null);
        if (order == null) {
            result.put("distance", new Long[0]);
            result.put("parent_edge", new int[0]);
            return result;
        }

        Long[] distance = new Long[n];
        int[] parentEdge = new int[n];
        Arrays.fill(parentEdge, -1);
        distance[source] = 0L;
        for (int u : order) {
            if (distance[u] == null) continue;
            for (int id : graph.get(u)) {
                int v = edges[id][1];
                long candidate = distance[u] + edges[id][2];
                if (distance[v] == null || candidate < distance[v]) {
                    distance[v] = candidate;
                    parentEdge[v] = id;
                }
            }
        }
        result.put("distance", distance);
        result.put("parent_edge", parentEdge);
        return result;
    }

    // Use parentEdge from a successful dag call. An unreachable target gives [].
    static List<Integer> reconstructRoute(int source, int target, int[][] edges, int[] parentEdge) {
        List<Integer> route = new ArrayList<>();
        if (target != source && parentEdge[target] == -1) return route;
        int current = target;
        while (current != source) {
            route.add(current);
            int id = parentEdge[current];
            current = edges[id][0];
        }
        route.add(source);
        Collections.reverse(route);
        return route;
    }
}
