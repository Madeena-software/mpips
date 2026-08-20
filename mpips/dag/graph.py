from typing import Any, Dict, List


def topological_sort(
    nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    # Build graph
    adj: Dict[str, List[str]] = {n["id"]: [] for n in nodes}
    in_degree = {n["id"]: 0 for n in nodes}
    node_map = {n["id"]: n for n in nodes}

    for edge in edges:
        src = edge["source"]
        tgt = edge["target"]
        if src not in node_map or tgt not in node_map:
            raise ValueError(f"Edge references non-existent node: {src} -> {tgt}")
        adj[src].append(tgt)
        in_degree[tgt] += 1

    queue = [nid for nid, deg in in_degree.items() if deg == 0]
    sorted_nodes = []

    while queue:
        u = queue.pop(0)
        sorted_nodes.append(node_map[u])
        for v in adj[u]:
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)

    if len(sorted_nodes) < len(nodes):
        raise ValueError("Cycle detected in graph")

    return sorted_nodes
