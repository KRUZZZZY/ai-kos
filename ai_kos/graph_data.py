"""AI-KOS graph data export — generates JSON for visualization tools."""

import yaml
from pathlib import Path
from typing import Dict, List, Any


def export_graph_data(knowledge_dir: str = "knowledge") -> Dict[str, Any]:
    """Export all articles as a graph data structure for visualization.

    Returns:
        {"nodes": [...], "edges": [...]}
        Each node: {id, title, type, keywords, group (type index)}
        Each edge: {source, target, weight (shared keyword count)}
    """
    nodes: List[Dict] = []
    edges: List[Dict] = []
    slug_to_index: Dict[str, int] = {}
    type_colors = {
        "base": 0, "process": 1, "plan": 2, "help": 3,
        "research-note": 4, "note": 5, "mission": 6
    }

    # First pass: collect all nodes
    for md in Path(knowledge_dir).rglob("*.md"):
        try:
            with open(md, 'r') as f:
                content = f.read()
            if not content.startswith('---'):
                continue
            fm = yaml.safe_load(content.split('---')[1]) or {}
            slug = fm.get('slug', md.stem)
            if slug not in slug_to_index:
                idx = len(nodes)
                slug_to_index[slug] = idx
                nodes.append({
                    "id": slug,
                    "title": fm.get('title', slug),
                    "type": fm.get('type', 'base'),
                    "keywords": fm.get('keywords', []),
                    "summary": fm.get('summary', ''),
                    "group": type_colors.get(fm.get('type', 'base'), 0),
                    "linkCount": len(fm.get('related', [])),
                })
        except Exception:
            continue

    # Second pass: collect edges
    for md in Path(knowledge_dir).rglob("*.md"):
        try:
            with open(md, 'r') as f:
                content = f.read()
            if not content.startswith('---'):
                continue
            fm = yaml.safe_load(content.split('---')[1]) or {}
            slug = fm.get('slug', md.stem)
            source_kw = set(fm.get('keywords', []))
            for target in fm.get('related', []):
                if slug in slug_to_index and target in slug_to_index:
                    # Compute edge weight = shared keyword count
                    # We need target's keywords — look up from nodes
                    target_idx = slug_to_index[target]
                    target_kw = set(nodes[target_idx]["keywords"])
                    weight = len(source_kw & target_kw)
                    edges.append({
                        "source": slug,
                        "target": target,
                        "weight": max(weight, 1),
                    })
        except Exception:
            continue

    # Deduplicate edges (bidirectional links create duplicates)
    seen = set()
    unique_edges = []
    for e in edges:
        key = tuple(sorted([e["source"], e["target"]]))
        if key not in seen:
            seen.add(key)
            unique_edges.append(e)

    return {
        "nodes": nodes,
        "edges": unique_edges,
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(unique_edges),
            "by_type": {t: sum(1 for n in nodes if n["type"] == t) for t in type_colors},
        }
    }
