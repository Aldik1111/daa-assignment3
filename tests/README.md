# Tests

Run all commands from the project root. JDK 17+ and Python 3.12+ are required. No extra packages are needed.

| Command | What it checks | Saved evidence |
| --- | --- | --- |
| `python tools/run.py --setup` | Supplied ping interface | `public_results.txt` |
| `python tools/run.py --check` | 36 public cases and two mixed batches | `public_results.txt` |
| `python tests/check_solution.py` | Independent small cases and witness checks | `own_*` files |
| `python tests/run_java_checks.py` | Direct Java route helper calls | `routes_results.txt` |
| `python tests/stress.py` | Full published limits | `stress_*` files |
| `python tests/run_java_checks.py --benchmark` | Verified Kruskal/Prim measurements | `benchmark_results.txt` |
| `python -m unittest discover -s tools -p "test_*.py"` | Supplied checker/transport tests | `tool_results.txt` |

The custom scripts save their evidence automatically. The two public commands and the tools command print their output; their saved logs were captured during verification.

## Small cases

`own_inputs.jsonl` has 726 requests. `own_expected.jsonl` has one independently calculated expected result or set of properties per request. `own_actual.jsonl` has 1,452 results because the complete input batch is sent twice in one process. The first and second halves correspond to the same input file. Replay without comparison using `python tools/run.py --input tests/own_inputs.jsonl`.

Expected files intentionally do not fix a forest's edge IDs or a DAG's parent IDs. The checker verifies these witnesses against the input. SCC labels and topological orders may also differ from the stored example as long as they are valid.

The first 26 cases are explicit boundary examples. Some useful ones:

- DSU on five vertices with operations `[0,0],[0,1],[1,0],[2,3],[3,4],[1,4]` must produce `[[5,1],[4,2],[4,2],[3,2],[2,3],[1,5]]`. The first and third unions change nothing; the last joins groups of size 2 and 3.
- The weighted graph `[[0,0,-100],[0,1,-4],[0,1,-4],[1,2,2],[0,2,9],[3,3,-8]]` with n=5 has optimum -2 and three components. One -4 edge and the weight-2 edge connect vertices 0,1,2. Vertices 3 and 4 remain separate. Loops cannot enter a forest.
- Four weight-1000000000 chain edges total 4000000000. Four negative versions total -4000000000. Both check 64-bit totals in both MST methods.
- SCC input `[[0,1],[1,0],[1,2],[0,2],[2,2],[2,3],[2,3]]` has groups `{0,1}`, `{2}`, `{3}`, `{4}`. Only the first group -> second and second -> third belong in condensation. Repeated edges and the loop add no new pair.
- Topo edges `0->1,0->2,1->3,2->3,0->3` form a DAG. An edge to a finished DFS vertex must not be mistaken for a back edge. A separate `2->3->2` component makes the whole graph cyclic.
- A DAG request from source 0 with `0->1` and a separate `2->3->2` cycle must be rejected, although that cycle is unreachable.
- Source 2 with edges `2->0(-1),2->0(-1),0->1(-1000000000)` has distances `[-1,-1000000001,0,null]`. This checks a nonzero source, a valid distance of -1, parallel choices and an unreachable vertex.
- Positive and negative chains check long DAG distances. A singleton without edges is valid; a singleton self-loop is cyclic.

The remaining 700 requests come from 100 seeded rounds. Each round tests DSU, both forest methods, SCC, topo, an arbitrary weighted directed graph and a generated DAG with shuffled vertex numbering. Small graphs have at most seven vertices and ten edges.

Independent reference methods:

- DSU: merge explicit vertex sets.
- Forest: enumerate every subset with n-c edges, retain spanning forests and minimise the weight.
- SCC: compute all-pairs reachability; two vertices belong together exactly when both directions are reachable.
- Cycles: Kahn's algorithm, separate from the solution's DFS.
- Distances: Bellman-Ford on graphs already established as acyclic.

`checker_examples()` tests the checker itself. It accepts two different optimal forests and rejects a repeated edge ID; accepts renamed SCC labels and rejects missing condensation; accepts two topological orders and rejects reversed precedence; accepts either tied parallel parent and rejects parent edges with the wrong direction. Both forest methods use this same semantic checker.

## Full-limit cases

`stress.py` writes the full requests to `stress_inputs.jsonl.gz` and actual output to `stress_actual.jsonl.gz`. These are ordinary UTF-8 JSON Lines compressed with gzip. Their uncompressed SHA-256 values are recorded in `stress_results.txt`.

There are 18 requests in one JVM, with a 20-second timeout and `-Xmx384m`:

- DSU: n=100000, q=250000. The first 99999 operations build a chain. After k successful joins, the answer is `[100000-k,k+1]`. Later self/repeated joins leave `[1,100000]` unchanged.
- Both forests: n=100000, m=250000. A chain uses weight -1000000000; extra skip edges have weight 1000000000. The unique optimum uses all chain edges, so the exact ID set and cost -99999000000000 are known without another greedy solver.
- SCC and topo: the same forward chain and skip edges. Every SCC is a singleton. Condensation must contain exactly the distinct original pairs under the returned labels. The chain forces the increasing topological order.
- DAG: every chain edge is negative and every shortcut is positive, so distance[v] is `-v*1000000000`, with parent ID v-1 for v>0.
- Replacing the last extra edge by `99999->0` creates one large SCC and makes both topo and DAG cyclic.
- Another full-size DAG request has isolated source 0 and a cycle on vertices 1 through 99999. It must also return the cycle result.
- Five edgeless graphs with 100000 vertices test all-isolate behaviour. The DAG source is 99999; every other vertex is unreachable.
- A wide star with duplicate outgoing edges checks DFS progress across a large adjacency list.
- A ping and a small DSU request after the large cases check state reset.

Large expected answers are represented by these formulas and executable assertions in `stress.py`, rather than a second copy of large arrays. Small expected answers are stored explicitly.

## Routes and benchmark

`JavaChecks.java` calls the helper directly for reachable, source, unreachable, parallel-edge and tied-route cases, checks edge direction and weight, and reconstructs a 100000-vertex route. See `routes_results.txt` and the route tables in `ANALYSIS.md`.

The benchmark uses three sizes, five warm-ups and five measured calls for each method at each size. It verifies the tree and the independently known optimum before measuring and after every call. Generator, seeds, timing boundary, environment and limitations are documented in `ANALYSIS.md`.
