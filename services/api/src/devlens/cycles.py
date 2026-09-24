"""Iterative Kosaraju SCCs with a deterministic, real-edge cycle witness per SCC."""

from collections import defaultdict

from devlens.architecture_models import DependencyCycle


def dependency_cycles(links: list[tuple[str, str, str]], kind: str) -> list[DependencyCycle]:
    adjacency: dict[str, list[str]] = defaultdict(list)
    reverse: dict[str, list[str]] = defaultdict(list)
    evidence: dict[tuple[str, str], str] = {}
    for source, target, edge_id in sorted(links):
        adjacency[source].append(target)
        reverse[target].append(source)
        evidence.setdefault((source, target), edge_id)
    vertices = sorted(set(adjacency) | set(reverse))
    for vertex in vertices:
        adjacency[vertex] = sorted(set(adjacency[vertex]))
        reverse[vertex] = sorted(set(reverse[vertex]))
    seen: set[str] = set()
    order: list[str] = []
    for root in vertices:
        if root in seen:
            continue
        stack = [(root, False)]
        while stack:
            node, finished = stack.pop()
            if finished:
                order.append(node)
            elif node not in seen:
                seen.add(node)
                stack.append((node, True))
                stack.extend(
                    (target, False) for target in reversed(adjacency[node]) if target not in seen
                )
    seen.clear()
    components: list[list[str]] = []
    for root in reversed(order):
        if root in seen:
            continue
        pending = [root]
        component: list[str] = []
        seen.add(root)
        while pending:
            node = pending.pop()
            component.append(node)
            for target in reverse[node]:
                if target not in seen:
                    seen.add(target)
                    pending.append(target)
        if len(component) > 1 or root in adjacency[root]:
            components.append(sorted(component))
    result: list[DependencyCycle] = []
    for index, component in enumerate(sorted(components)):
        members = set(component)
        # Find a back edge in the SCC; the stack slice is a closed witness.
        active: dict[str, int] = {}
        visited: set[str] = set()
        path: list[str] = []
        walk = [(component[0], iter(adjacency[component[0]]))]
        active[component[0]] = 0
        path.append(component[0])
        visited.add(component[0])
        witness: list[str] = []
        while walk and not witness:
            node, children = walk[-1]
            next_target = next(children, None)
            if next_target is None:
                walk.pop()
                active.pop(node)
                path.pop()
            elif next_target in members:
                target = next_target
                if target in active:
                    witness = path[active[target] :] + [target]
                elif target not in visited:
                    visited.add(target)
                    active[target] = len(path)
                    path.append(target)
                    walk.append((target, iter(adjacency[target])))
        result.append(
            DependencyCycle(
                id=f"{kind}-cycle-{index + 1}",
                kind="file" if kind == "file" else "directory",
                members=component,
                path=witness,
                edge_ids=[evidence[(a, b)] for a, b in zip(witness, witness[1:], strict=False)],
            )
        )
    return result
