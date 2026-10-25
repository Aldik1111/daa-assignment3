"""Full-limit tests with analytic expected answers; stores compressed evidence."""
import gzip
import hashlib
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from run import build

N = 100000
M = 250000


def cases():
    chain = [[i, i + 1, -10**9] for i in range(N - 1)]
    extra = [[i % (N - 2), i % (N - 2) + 2, 10**9] for i in range(M - len(chain))]
    weighted = chain + extra
    directed = [edge[:2] for edge in weighted]
    operations = [edge[:2] for edge in chain] + [[0,0] if i % 2 else [0,N-1] for i in range(M - N + 1)]
    yield 'dsu-full', {'task':'dsu','n':N,'operations':operations}
    for task in ('kruskal', 'prim', 'scc', 'topo', 'dag'):
        req = {'task':task,'n':N,'edges':weighted if task in ('kruskal','prim','dag') else directed}
        if task == 'dag':
            req['source'] = 0
        yield task + '-chain-full', req
    cyclic = directed[:-1] + [[N - 1, 0]]
    yield 'scc-cycle-full', {'task':'scc','n':N,'edges':cyclic}
    yield 'topo-cycle-full', {'task':'topo','n':N,'edges':cyclic}
    yield 'dag-cycle-full', {'task':'dag','n':N,'source':0,'edges':weighted[:-1] + [[N-1,0,0]]}
    # Vertex 0 is isolated, but the rest contains a directed cycle.
    unreachable_cycle = [[i,i+1,1] for i in range(1,N-1)] + [[N-1,1,1]]
    unreachable_cycle += [[1,2,1]] * (M - len(unreachable_cycle))
    yield 'dag-unreachable-cycle-full', {'task':'dag','n':N,'source':0,'edges':unreachable_cycle}
    for task in ('kruskal','prim','scc','topo','dag'):
        req = {'task':task,'n':N,'edges':[]}
        if task == 'dag':
            req['source'] = N - 1
        yield task + '-isolates', req
    # A wide DFS with many completed-neighbour edges must not rescan adjacency.
    star = [[0,i] for i in range(1,N)]
    star += [[0,1 + i % (N-1)] for i in range(M - len(star))]
    yield 'topo-star-full', {'task':'topo','n':N,'edges':star}
    yield 'ping-reset', {'task':'ping'}
    yield 'dsu-reset', {'task':'dsu','n':3,'operations':[[0,1],[1,1]]}


def validate(name, req, out):
    assert 'error' not in out
    if name == 'ping-reset':
        assert out == {'status':'ready'}
    elif name == 'dsu-reset':
        assert out == {'states':[[2,2],[2,2]]}
    elif name == 'dsu-full':
        assert len(out['states']) == M
        for i, pair in enumerate(out['states']):
            merged = min(i + 1, N - 1)
            assert pair == [N - merged, merged + 1]
    elif 'cycle' in name:
        if req['task'] == 'scc':
            assert len(out['component']) == N and len(set(out['component'])) == 1
            assert out['condensation'] == []
        elif req['task'] == 'topo':
            assert out == {'acyclic':False,'order':[]}
        else:
            assert out == {'acyclic':False,'distance':[],'parent_edge':[]}
    elif req['task'] in ('kruskal','prim'):
        if not req['edges']:
            assert out == {'cost':0,'components':N,'edge_ids':[]}
        else:
            assert out['cost'] == -(N - 1) * 10**9 and out['components'] == 1
            # Only the N-1 chain edges have the lowest possible weight.
            assert len(out['edge_ids']) == N - 1 and set(out['edge_ids']) == set(range(N-1))
    elif req['task'] == 'scc':
        labels = out['component']
        assert len(labels) == N and len(set(labels)) == N
        pairs = [tuple(pair) for pair in out['condensation']]
        assert len(pairs) == len(set(pairs))
        assert set(pairs) == {(labels[u], labels[v]) for u,v in req['edges']}
    elif req['task'] == 'topo':
        assert out['acyclic'] is True and sorted(out['order']) == list(range(N))
        positions = {v:i for i,v in enumerate(out['order'])}
        assert all(positions[u] < positions[v] for u,v in req['edges'])
    elif req['task'] == 'dag':
        assert out['acyclic'] is True
        if req['edges']:
            assert out['distance'] == [-i * 10**9 for i in range(N)]
            assert out['parent_edge'] == [-1] + list(range(N-1))
        else:
            assert out['distance'] == [None] * (N - 1) + [0]
            assert out['parent_edge'] == [-1] * N


def main():
    command = build('Java')
    tests = list(cases())
    data = ''.join(json.dumps(req, separators=(',', ':')) + '\n' for _,req in tests).encode()
    (ROOT / 'tests' / 'stress_inputs.jsonl.gz').write_bytes(gzip.compress(data, mtime=0))
    start = time.perf_counter()
    process = subprocess.run(command, input=data, capture_output=True, timeout=20, check=True)
    elapsed = time.perf_counter() - start
    lines = process.stdout.splitlines()
    assert len(lines) == len(tests)
    report = []
    for (name,req),line in zip(tests, lines):
        validate(name, req, json.loads(line))
        count = len(req.get('edges', req.get('operations', [])))
        report.append(f'PASS {name}: n={req.get("n",0)}, edges/operations={count}')
    (ROOT / 'tests' / 'stress_actual.jsonl.gz').write_bytes(gzip.compress(process.stdout, mtime=0))
    report += [f'PASS {len(tests)} requests in one JVM, -Xmx384m, timeout=20s; elapsed={elapsed:.3f}s',
               'input_sha256=' + hashlib.sha256(data).hexdigest(),
               'output_sha256=' + hashlib.sha256(process.stdout).hexdigest()]
    text = '\n'.join(report) + '\n'
    (ROOT / 'tests' / 'stress_results.txt').write_text(text, encoding='utf-8')
    print(text, end='')


if __name__ == '__main__':
    main()
