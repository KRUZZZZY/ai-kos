"""AI-KOS graph data export — generates JSON for visualization tools.

v1.7: nodes include lifecycle, doc_type, superseded_by, link_count.
Edges include relation type. Groups colored by type + lifecycle.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Any


def export_graph_data(knowledge_dir: str = "knowledge") -> Dict[str, Any]:
    """Export all articles as a graph data structure for visualization.

    Returns:
        {"nodes": [...], "edges": [...]}
        Each node: {id, title, type, keywords, group, lifecycle, doc_type, superseded_by, linkCount}
        Each edge: {source, target, weight, type}
    """
    nodes: List[Dict] = []
    edges: List[Dict] = []
    slug_to_index: Dict[str, int] = {}

    # v1.7: expanded type colors with lifecycle sub-groups
    type_colors = {
        "base": 0, "process": 1, "plan": 2, "help": 3,
        "research-note": 4, "note": 5, "mission": 6,
    }
    lifecycle_color_offset = {
        "current": 0, "superseded": 7, "historical": 14,
    }

    def _node_group(article_type: str, lifecycle: str) -> int:
        base = type_colors.get(article_type, 0)
        offset = lifecycle_color_offset.get(lifecycle, 0)
        return base + offset

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
                atype = fm.get('type', 'base')
                lc = fm.get('lifecycle', 'current')
                nodes.append({
                    "id": slug,
                    "title": fm.get('title', slug),
                    "type": atype,
                    "keywords": fm.get('keywords', []),
                    "summary": fm.get('summary', ''),
                    "group": _node_group(atype, lc),
                    "lifecycle": lc,
                    "doc_type": fm.get('doc_type'),
                    "superseded_by": fm.get('superseded_by'),
                    "linkCount": fm.get('link_count', len(fm.get('related', []))),
                })
        except Exception:
            continue

    # Second pass: collect typed edges
    for md in Path(knowledge_dir).rglob("*.md"):
        try:
            with open(md, 'r') as f:
                content = f.read()
            if not content.startswith('---'):
                continue
            fm = yaml.safe_load(content.split('---')[1]) or {}
            slug = fm.get('slug', md.stem)
            source_kw = set(fm.get('keywords', []))
            for rel in fm.get('related', []):
                target = rel.get('slug', rel) if isinstance(rel, dict) else rel
                if slug in slug_to_index and target in slug_to_index:
                    target_idx = slug_to_index[target]
                    target_kw = set(nodes[target_idx]["keywords"])
                    weight = len(source_kw & target_kw)
                    edge_type = rel.get('type', 'see-also') if isinstance(rel, dict) else 'see-also'
                    edges.append({
                        "source": slug,
                        "target": target,
                        "weight": max(weight, 1),
                        "type": edge_type,
                    })
        except Exception:
            continue

    # Deduplicate edges
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
