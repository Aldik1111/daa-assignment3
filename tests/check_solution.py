"""Independent small-graph checks. Run from the repository root."""
import itertools
import json
import pathlib
import random
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from run import build, execute


def groups(n, edges):
    parts = [{v} for v in range(n)]
    for u, v, *_ in edges:
        a = next(p for p in parts if u in p)
        b = next(p for p in parts if v in p)
        if a is not b:
            a.update(b)
            parts.remove(b)
    return parts


def reachable(n, edges):
    reach = [[i == j for j in range(n)] for i in range(n)]
    for u, v, *_ in edges:
        reach[u][v] = True
    for k in range(n):
        for i in range(n):
            for j in range(n):
                reach[i][j] |= reach[i][k] and reach[k][j]
    return reach


def kahn(n, edges):
    degree = [0] * n
    out = [[] for _ in range(n)]
    for u, v, *_ in edges:
        degree[v] += 1
        out[u].append(v)
    queue = [v for v in range(n) if degree[v] == 0]
    for u in queue:
        for v in out[u]:
            degree[v] -= 1
            if degree[v] == 0:
                queue.append(v)
    return queue


def expected(req):
    task = req['task']
    if task == 'ping':
        return {'status': 'ready'}
    n = req['n']
    edges = req.get('edges', [])
    if task == 'dsu':
        states = []
        for end in range(1, len(req['operations']) + 1):
            parts = groups(n, req['operations'][:end])
            states.append([len(parts), max(map(len, parts), default=0)])
        return {'states': states}
    if task in ('kruskal', 'prim'):
        count = len(groups(n, edges))
        best = None
        # Enumerate every candidate with n-c edges. No greedy MST algorithm here.
        for ids in itertools.combinations(range(len(edges)), n - count):
            chosen = [edges[i] for i in ids]
            if len(groups(n, chosen)) == count:
                cost = sum(e[2] for e in chosen)
                best = cost if best is None else min(best, cost)
        return {'cost': best, 'components': count}
    if task == 'scc':
        reach = reachable(n, edges)
        labels = [min(j for j in range(n) if reach[i][j] and reach[j][i]) for i in range(n)]
        pairs = sorted({(labels[u], labels[v]) for u, v in edges if labels[u] != labels[v]})
        return {'component': labels, 'condensation': [list(p) for p in pairs]}
    order = kahn(n, edges)
    acyclic = len(order) == n
    if task == 'topo':
        return {'acyclic': acyclic, 'order': order if acyclic else []}
    if not acyclic:
        return {'acyclic': False, 'distance': [], 'parent_edge': []}
    dist = [None] * n
    dist[req['source']] = 0
    for _ in range(n - 1):
        for u, v, w in edges:
            if dist[u] is not None and (dist[v] is None or dist[u] + w < dist[v]):
                dist[v] = dist[u] + w
    return {'acyclic': True, 'distance': dist}


def validate(req, answer, want):
    assert 'error' not in answer, answer
    task = req['task']
    n = req.get('n', 0)
    edges = req.get('edges', [])
    if task in ('ping', 'dsu'):
        assert answer == want
    elif task in ('kruskal', 'prim'):
        assert answer['cost'] == want['cost']
        assert answer['components'] == want['components']
        ids = answer['edge_ids']
        assert len(ids) == len(set(ids)) == n - want['components']
        assert all(type(i) is int and 0 <= i < len(edges) for i in ids)
        chosen = [edges[i] for i in ids]
        assert all(u != v for u, v, _ in chosen)
        assert len(groups(n, chosen)) == want['components']
        assert sum(e[2] for e in chosen) == want['cost']
    elif task == 'scc':
        labels = answer['component']
        assert len(labels) == n
        assert all(type(v) is int and 0 <= v <= 2**63 - 1 for v in labels)
        for i in range(n):
            for j in range(n):
                assert (labels[i] == labels[j]) == (want['component'][i] == want['component'][j])
        pairs = [tuple(p) for p in answer['condensation']]
        assert len(pairs) == len(set(pairs))
        assert set(pairs) == {(labels[u], labels[v]) for u, v in edges if labels[u] != labels[v]}
    elif task == 'topo':
        assert answer['acyclic'] is want['acyclic']
        if not want['acyclic']:
            assert answer['order'] == []
        else:
            order = answer['order']
            assert sorted(order) == list(range(n))
            position = {v: i for i, v in enumerate(order)}
            assert all(position[u] < position[v] for u, v in edges)
    else:
        assert answer['acyclic'] is want['acyclic']
        assert answer['distance'] == want['distance']
        if not want['acyclic']:
            assert answer['parent_edge'] == []
            return
        parents = answer['parent_edge']
        assert len(parents) == n
        source = req['source']
        for target, distance in enumerate(want['distance']):
            if target == source or distance is None:
                assert parents[target] == -1
                continue
            current, cost, seen = target, 0, set()
            while current != source:
                assert current not in seen
                seen.add(current)
                edge_id = parents[current]
                assert type(edge_id) is int and 0 <= edge_id < len(edges)
                u, v, w = edges[edge_id]
                assert v == current
                current = u
                cost += w
            assert cost == distance


def checker_examples():
    examples = [
        ({'task': 'kruskal', 'n': 3, 'edges': [[0,1,1],[1,2,1],[0,2,1]]},
         [{'cost':2,'components':1,'edge_ids':[0,1]}, {'cost':2,'components':1,'edge_ids':[1,2]}],
         {'cost':2,'components':1,'edge_ids':[0,0]}),
        ({'task':'scc','n':3,'edges':[[0,1],[1,0],[1,2]]},
         [{'component':[0,0,1],'condensation':[[0,1]]}, {'component':[9,9,4],'condensation':[[9,4]]}],
         {'component':[9,9,4],'condensation':[]}),
        ({'task':'topo','n':3,'edges':[[0,2],[1,2]]},
         [{'acyclic':True,'order':[0,1,2]}, {'acyclic':True,'order':[1,0,2]}],
         {'acyclic':True,'order':[2,0,1]}),
        ({'task':'dag','n':3,'source':0,'edges':[[0,1,2],[0,1,2],[1,2,-1]]},
         [{'acyclic':True,'distance':[0,2,1],'parent_edge':[-1,0,2]},
          {'acyclic':True,'distance':[0,2,1],'parent_edge':[-1,1,2]}],
         {'acyclic':True,'distance':[0,2,1],'parent_edge':[-1,2,0]})]
    log = []
    for req, valid, invalid in examples:
        want = expected(req)
        for answer in valid:
            validate(req, answer, want)
        try:
            validate(req, invalid, want)
        except AssertionError:
            log.append(req['task'] + ': accepted two valid answers; rejected invalid witness')
        else:
            raise AssertionError('Checker accepted an invalid witness')
    return log


def cases():
    requests = [{'task':'ping'}, {'task':'dsu','n':0,'operations':[]},
                {'task':'dsu','n':5,'operations':[[0,0],[0,1],[1,0],[2,3],[3,4],[1,4]]}]
    for task in ('kruskal','prim','scc','topo'):
        for n in (0, 4):
            requests.append({'task':task,'n':n,'edges':[]})
    for task in ('kruskal','prim'):
        requests += [
            {'task':task,'n':5,'edges':[[0,0,-100],[0,1,-4],[0,1,-4],[1,2,2],[0,2,9],[3,3,-8]]},
            {'task':task,'n':5,'edges':[[0,1,10**9],[1,2,10**9],[2,3,10**9],[3,4,10**9]]},
            {'task':task,'n':5,'edges':[[0,1,-10**9],[1,2,-10**9],[2,3,-10**9],[3,4,-10**9]]}]
    requests += [
        {'task':'scc','n':5,'edges':[[0,1],[1,0],[1,2],[0,2],[2,2],[2,3],[2,3]]},
        {'task':'topo','n':4,'edges':[[0,1],[0,2],[1,3],[2,3],[0,3]]},
        {'task':'topo','n':4,'edges':[[0,1],[2,3],[3,2]]},
        {'task':'dag','n':4,'source':0,'edges':[[0,1,1],[2,3,1],[3,2,-1]]},
        {'task':'dag','n':4,'source':2,'edges':[[2,0,-1],[2,0,-1],[0,1,-10**9]]},
        {'task':'dag','n':5,'source':0,'edges':[[0,1,-10**9],[1,2,-10**9],[2,3,-10**9]]},
        {'task':'dag','n':5,'source':0,'edges':[[0,1,10**9],[1,2,10**9],[2,3,10**9]]},
        {'task':'dag','n':1,'source':0,'edges':[]},
        {'task':'dag','n':1,'source':0,'edges':[[0,0,-1]]}]
    rng = random.Random(250542)
    for _ in range(100):
        n = rng.randint(1, 7)
        edges = [[rng.randrange(n), rng.randrange(n), rng.randint(-9,9)] for _ in range(rng.randint(0,10))]
        requests.append({'task':'dsu','n':n,'operations':[e[:2] for e in edges]})
        for task in ('kruskal','prim','scc','topo','dag'):
            req = {'task':task,'n':n,'edges':edges if task in ('kruskal','prim','dag') else [e[:2] for e in edges]}
            if task == 'dag':
                req['source'] = rng.randrange(n)
            requests.append(req)
        # Also generate DAGs with arbitrary vertex numbering, not only cycles.
        order = list(range(n))
        rng.shuffle(order)
        forward = [[order[min(u,v)], order[max(u,v)], w] for u,v,w in edges if u != v]
        requests.append({'task':'dag','n':n,'source':rng.randrange(n),'edges':forward})
    return requests


def write_lines(name, items):
    (ROOT / 'tests' / name).write_text(''.join(json.dumps(x, separators=(',', ':')) + '\n' for x in items), encoding='utf-8')


def main():
    checks = checker_examples()
    requests = cases()
    wants = [expected(req) for req in requests]
    write_lines('own_inputs.jsonl', requests)
    write_lines('own_expected.jsonl', wants)
    command = build('Java')
    answers = execute(command, requests + requests)
    for i, (req, answer, want) in enumerate(zip(requests * 2, answers, wants * 2)):
        try:
            validate(req, answer, want)
        except AssertionError as error:
            raise AssertionError(f'case {i}: {req}\nactual={answer}\nexpected={want}') from error
    write_lines('own_actual.jsonl', answers)
    checks.append(f'PASS {len(requests)} own cases, repeated twice in one JVM ({len(answers)} results); seed=250542')
    log = '\n'.join(checks) + '\n'
    (ROOT / 'tests' / 'own_results.txt').write_text(log, encoding='utf-8')
    print(log, end='')


if __name__ == '__main__':
    main()
