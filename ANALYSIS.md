# Assignment 3: Graph Algorithms

Student: Irtay Aldiyar  
Student ID: 250542  
Language: Java 17

The implementation is in `src/Java/Algorithms.java`. The input adapters and the entry point are kept from the template. The code uses arrays, lists, a hash set and a priority queue. There are no external Java libraries.

## Build and run

Install JDK 17+ and Python 3.12+. Run these commands from the project folder:

```text
python tools/run.py --setup
python tools/run.py --check
python tools/run.py --input tests/own_inputs.jsonl
python tests/check_solution.py
python tests/run_java_checks.py
python tests/stress.py
python tests/run_java_checks.py --benchmark
python -m unittest discover -s tools -p "test_*.py"
```

On Windows, `py -3` can replace `python`. Python launches the checks; the solution itself is Java. The custom scripts compile Java with `--release 17` and run it with `-Xmx384m`. They save their results under `tests/`.

For a manual build in PowerShell:

```powershell
New-Item -ItemType Directory -Force .build/Java | Out-Null
javac --release 17 -encoding UTF-8 -d .build/Java src/Java/*.java
Get-Content tests/own_inputs.jsonl | java -Xmx384m -cp .build/Java Main
```

Each input line is a separate JSON request. Each output line is one JSON result. There are no interactive prompts. `ping` is still handled by the supplied `Main`.

## Shared choices

Here, n is the number of vertices, m the number of edges and q the number of union operations. Memory bounds include the returned result.

Every call creates its own arrays and collections. There is no mutable static algorithm state, so a previous request cannot affect the next one. The tests send mixed requests through the same JVM, including repeated batches.

An adjacency list stores original edge IDs. Kruskal sorts IDs instead of moving the input rows. This keeps `edge_ids` and `parent_edge` consistent with the request.

Costs and distances use `long`. A forest or a path in a DAG has at most n-1 edges, so its absolute total is at most 99,999,000,000,000 under the given limits. This fits in `long` but not in `int`. `Long[]` allows unreachable distances to stay `null`; -1 can be a real distance.

DFS is iterative. `stack` contains the active vertices and `nextEdge[u]` records the next outgoing edge to examine. Returning to a vertex does not restart its adjacency scan. Vertices are marked before pushing them, so a vertex is not pushed twice. The arrays have length n, which also handles a chain of 100,000 vertices without recursive calls.

## DSU

Initially, each vertex is its own root and has size 1. `find` first walks to the root, then walks back through the same parent chain and points its vertices directly to that root. `union` joins the smaller root tree to the larger one.

The invariant is that each parent tree describes exactly one connected component, and the root's size equals the number of its vertices. Joining two different roots merges exactly two components. Therefore the component count decreases by one, the new size is the sum of the two old sizes, and `largest` can be updated from that size. If the roots are equal, nothing changes. The saved state is added after every operation, even when it changes nothing.

Repeated connections and self-unions are harmless. With n=0 there are no operations and the answer is an empty array. With n>0 and no operations, the answer is also empty: the initial state is not requested.

Time: O(n + q alpha(n)) amortised, using path compression and union by size. Memory: O(n+q), including the states.

## Kruskal

The edge IDs are sorted by weight, then by ID to make ties repeatable. An edge is selected only if its endpoints have different DSU roots. The weight is added to a `long` total.

The selected edges always form a forest. DSU tracks its connected components. At each selection, a cheapest available edge connects two different components. By the cut property, it can be included in a minimum spanning forest. Repeating this process connects every pair that can be connected without introducing a cycle. The final DSU count is the number of input components, including isolated vertices.

Loops never connect different roots, so they are skipped even when their weights are negative. Parallel edges are considered separately. Tied edges can give more than one optimal forest, and the tests accept that. Empty input gives cost 0, no IDs and zero components.

Time: O(n + m log(m+1)). Sorting dominates the DSU work. Memory: O(n+m) for input conversion, edge IDs, sorting, DSU and the result.

## Prim

Prim builds an undirected adjacency list and uses a min-priority queue of edge IDs. It starts from an unvisited vertex and adds its incident edges. Each selected edge reaches one new vertex. Edges whose endpoints are both visited are discarded. When the queue is empty, the outer loop starts the next component.

The invariant is that the selected edges form a tree on the visited vertices of the current component. Every edge crossing from that tree to an unvisited vertex is available in the queue. After skipping old entries, its minimum is a lightest crossing edge. The cut property makes that choice safe. Restarting applies the same argument to each component.

An isolated vertex still increases the component count. Negative weights and parallel edges work with the same comparison. A loop is discarded because its endpoint is already visited. Empty input gives an empty forest.

This is lazy Prim: old entries may stay in the heap until removed. Every input edge is inserted at most once, and the queue can contain O(m) entries. Time: O(n + m log(m+1)). Memory: O(n+m), including both directions in adjacency and the selected IDs.

## Strongly connected components

Kosaraju first runs DFS on the original graph and records decreasing finish order. The second pass traverses the reversed graph in that order. Each new traversal gets a new component label. Cycle detection is disabled for the first pass because SCC input may be cyclic.

After contracting SCCs, the component graph is acyclic. For an edge from one component to another, the first component has a later maximum DFS finish time. Thus the next unassigned component in decreasing finish order has no incoming edge from another unassigned component. In the reversed graph, a traversal cannot leave it for an unassigned component. Within the component, all vertices remain mutually reachable. Each second-pass traversal therefore finds exactly one SCC.

Finally, the code scans the original edges. Internal edges are skipped. A hash set of packed label pairs removes duplicates from the condensation graph. The labels fit in 32 bits here, so combining the two into one `long` is unambiguous.

An isolate gets its own label. Loops do not add condensation edges. Duplicate edges do not duplicate output pairs. Empty input gives two empty arrays.

Time: O(n+m) expected with hash-based deduplication. Memory: O(n+m), including both graphs, DFS arrays, labels, the set and condensation edges.

## Topological order

DFS uses three states: unvisited, active and finished. An edge to an active vertex returns a cycle result. An edge to a finished vertex is safe. The code starts DFS from every unvisited vertex, so disconnected components are checked too.

The active vertices form the current DFS path. An edge back to an active vertex closes a directed cycle. If there is no cycle, every edge u -> v has v finished before u: either DFS visits v from u or v was already finished. Reversing finish order therefore places u before v. Each vertex is included once.

A self-loop is a cycle. Parallel edges are allowed. For an empty graph, the valid order is empty. For any cycle, `acyclic` is false and `order` is empty.

Time and memory: O(n+m). `nextEdge` prevents repeated scans of the same neighbours.

## DAG shortest paths

The method first checks the whole graph with the same three-state DFS. A cycle anywhere gives `acyclic=false` and two empty arrays, even if the cycle cannot be reached from the source.

For an acyclic graph, the source distance is 0 and other distances start as null. Vertices are processed in topological order. Only reachable vertices relax their outgoing edges. A strict improvement replaces both the distance and the incoming edge ID.

Before a vertex is processed, all its predecessors have already been processed. Every path reaching it ends with an edge from one of those predecessors. By induction, taking the minimum of those candidate distances gives its shortest distance. Negative edges do not break this argument because the graph has no cycle. On a tie, keeping the previous parent still gives a shortest path.

Source and unreachable vertices keep parent -1. Other parents are original incoming edge IDs. Parent links lead backwards in topological order and eventually reach the source. Time and memory: O(n+m).

### Route reconstruction

`reconstructRoute(source, target, edges, parentEdge)` follows incoming edges backwards, collects vertices and reverses the list. Its inputs are the original edges and parents from a successful `dag` call. It returns an empty list for an unreachable target and `[source]` for the source. Time and output space are O(L) for a route with L vertices; there is no full-graph allocation in this helper.

The direct calls below were executed by `tests/JavaChecks.java`. Raw output is in `tests/routes_results.txt`.

First graph: `[[0,1,3],[0,2,8],[1,2,-7],[2,3,4]]`, n=5, source=0. Actual parents: `[-1,0,2,3,-1]`.

| Call | Actual vertices | Selected IDs | Total weight |
| --- | --- | --- | --- |
| `reconstructRoute(0,3,edges,parentEdge)` | `[0,1,2,3]` | `[0,2,3]` | 3-7+4 = 0 |
| `reconstructRoute(0,0,edges,parentEdge)` | `[0]` | `[]` | 0 |
| `reconstructRoute(0,4,edges,parentEdge)` | `[]` | `[]` | No route; distance is null |

Second graph: `[[0,1,2],[0,1,2],[0,2,2],[1,3,3],[2,3,3]]`, n=5, source=0. Actual parents: `[-1,0,2,4,-1]`.

| Call | Actual vertices | Selected IDs | Total weight |
| --- | --- | --- | --- |
| `reconstructRoute(0,1,edges,parentEdge)` | `[0,1]` | `[0]` | 2 |
| `reconstructRoute(0,3,edges,parentEdge)` | `[0,2,3]` | `[2,4]` | 2+3 = 5 |

The first two edges are equal parallel choices. Routes 0->1->3 and 0->2->3 also have equal cost. The test verifies the direction of every selected edge and sums its weight. A separate direct call reconstructs all 100,000 vertices of a chain and checks its cost, -99,999,000,000,000.

## Tests and evidence

The 36 public cases and the repeated public batch passed. `tests/check_solution.py` passed 726 own cases twice in one JVM, giving 1,452 checked results. Its random seed is 250542. Inputs, expected properties and actual results are saved as JSON Lines under `tests/`. The supplied tool/transport suite reported 12 tests, OK with four skipped because the optional C++/.NET toolchains were unavailable. Java checks ran successfully.

The expected answers do not come from the Java implementation. Small DSU cases use explicit sets. Small forests are checked against exhaustive enumeration. SCC membership uses transitive closure. Cycle checks use Kahn's algorithm, and shortest distances use Bellman-Ford. Forest IDs, condensation edges, topological precedence and parent paths are checked semantically. The checker also accepts two different valid witnesses and rejects an invalid one for forests, SCC, topo and DAG. See `tests/README.md` for concrete cases and reasoning.

The full-limit test sends 18 requests in one process. It covers n=100000, m/q=250000, a 100,000-vertex chain, a large SCC, reachable and unreachable cycles, a wide DFS, isolates and state reset. It passed in 2.824 seconds with a 20-second timeout and a 384 MiB Java heap limit. This is a whole-process stress duration, not an isolated algorithm benchmark. Complete large inputs and actual outputs are stored in compressed JSON Lines files. Expected properties are derived in `tests/stress.py` and explained in the test README.

## Kruskal and Prim measurements

Recorded on 22 October 2026. Environment: Windows 11 10.0, amd64, Intel Core i5-12450H, 12 logical processors, about 15.7 GiB system-visible memory. Runtime: Temurin OpenJDK 17.0.20.1, OpenJDK 64-Bit Server VM, `-Xmx384m`.

Command: `python tests/run_java_checks.py --benchmark`. Timer: `System.nanoTime()`. The runner compiles before starting the JVM; compilation is not timed. Each method has one correctness run, then five warm-up calls and five measured calls per size. The measured rounds alternate which algorithm runs first. No explicit garbage collection is requested.

The generator in `JavaChecks.graph` uses `java.util.Random` with seed `250542+n`. It first makes a chain with weight -1000000000 on every edge. Other edges have random endpoints and weights from -999999999 to 1000000000. It then shuffles the complete edge array. Both methods receive the same graph at each size.

The chain gives an independently known optimum: any tree needs n-1 edges, each weighs at least -1000000000, and the chain attains that lower bound. Before any timings, both results are checked for distinct IDs, no loops, the correct number of edges, connectivity, reported weight and this optimum. Every later result is also checked outside the timed interval. Checking connectivity uses a separate traversal, not the solution's DSU.

The timed region includes conversion from the supplied row lists into `int[][]`, sorting or adjacency construction, the algorithm and result allocation. It excludes random generation, initial input-list construction, JSON parsing, serialization, I/O, validation and compilation. These boundaries are the same for both methods.

All values below are milliseconds. Raw values are in `tests/benchmark_results.txt`; table entries are rounded to three decimals.

| n | m | Seed | Method | Five runs (ms) | Median (ms) |
| --- | --- | --- | --- | --- | --- |
| 1,000 | 2,500 | 251542 | Kruskal | 1.211, 2.364, 1.818, 1.178, 2.139 | 1.818 |
| 1,000 | 2,500 | 251542 | Prim | 1.847, 1.912, 1.470, 1.697, 1.851 | 1.847 |
| 10,000 | 25,000 | 260542 | Kruskal | 9.555, 9.155, 10.579, 13.145, 9.231 | 9.555 |
| 10,000 | 25,000 | 260542 | Prim | 11.418, 11.091, 13.203, 19.302, 13.178 | 13.178 |
| 100,000 | 250,000 | 350542 | Kruskal | 189.179, 201.466, 195.956, 176.328, 192.178 | 192.178 |
| 100,000 | 250,000 | 350542 | Prim | 479.527, 451.060, 415.135, 470.488, 393.921 | 451.060 |

Kruskal had the lower median at all three sizes in this run. The smallest difference was only about 0.03 ms. At the largest size, Prim took about 2.35 times as long. Prim builds adjacency lists and repeatedly updates a heap, while Kruskal sorts once and then scans. Those costs are plausible contributors, but this experiment does not isolate them.

These measurements do not prove a complexity bound or show that Kruskal is always faster. Both implementations have O(n + m log(m+1)) time bounds. Only one sparse graph family and one seed per size were measured. The deliberately cheap chain makes correctness easy to establish but is not a representative sample of all weighted graphs. JIT compilation, allocation, garbage collection, scheduling and CPU power settings can affect the results. Five warm-ups reduce some startup effects without guaranteeing a fully steady JVM. Dense or disconnected graphs may behave differently.

## Sources and AI assistance

The assignment specification, JSON adapters, public checker and workflow come from [RZhaniya/daa-assignment-3-graphs](https://github.com/RZhaniya/daa-assignment-3-graphs), template commit `76c1d91daa90ceadcb225f5408d54d4bfcf397f9`. The earlier local assignments were used as style references.

OpenAI Codex was used for testing, correctness checks, and assistance with implementation and documentation. The saved outputs and benchmark measurements were obtained by executing the included code in the local environment. No additional external algorithm code was copied.
