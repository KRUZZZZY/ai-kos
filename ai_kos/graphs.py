"""AI-KOS graph backend — store and query network/graph data.

Graphs are stored as node + edge tables in SQLite.
Traversal uses recursive SQL CTEs (no external deps).
"""

import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any

logger = logging.getLogger("ai-kos.graphs")


def _connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def create_graph(db_path: str, name: str, directed: bool = True,
                 node_attrs: Optional[List[str]] = None,
                 edge_attrs: Optional[List[str]] = None) -> None:
    """Create nodes and edges tables for a graph."""
    conn = _connect(db_path)
    try:
        node_cols = ['"node_id" TEXT PRIMARY KEY']
        for attr in (node_attrs or []):
            node_cols.append(f'"{attr}" TEXT')
        conn.execute(f'CREATE TABLE IF NOT EXISTS "{name}_nodes" ({", ".join(node_cols)})')

        edge_cols = ['"source" TEXT', '"target" TEXT']
        for attr in (edge_attrs or []):
            edge_cols.append(f'"{attr}" TEXT')
        conn.execute(f'CREATE TABLE IF NOT EXISTS "{name}_edges" ({", ".join(edge_cols)})')

        if directed:
            conn.execute(f'CREATE INDEX IF NOT EXISTS idx_{name}_edges_src ON "{name}_edges"(source)')
        conn.execute(f'CREATE INDEX IF NOT EXISTS idx_{name}_edges_tgt ON "{name}_edges"(target)')
        conn.commit()
        logger.info(f"Created graph {name} in {db_path}")
    finally:
        conn.close()


def drop_graph(db_path: str, name: str) -> None:
    """Drop both nodes and edges tables."""
    conn = _connect(db_path)
    try:
        conn.execute(f'DROP TABLE IF EXISTS "{name}_nodes"')
        conn.execute(f'DROP TABLE IF EXISTS "{name}_edges"')
        conn.commit()
    finally:
        conn.close()


def insert_nodes(db_path: str, name: str, nodes: List[Dict[str, Any]]) -> int:
    """Insert nodes. Each dict must have 'node_id'. Other keys become attributes."""
    if not nodes:
        return 0
    conn = _connect(db_path)
    try:
        cols = list(nodes[0].keys())
        placeholders = ", ".join(["?"] * len(cols))
        col_names = ", ".join(f'"{c}"' for c in cols)
        sql = f'INSERT OR REPLACE INTO "{name}_nodes" ({col_names}) VALUES ({placeholders})'
        count = 0
        for node in nodes:
            conn.execute(sql, [node.get(c) for c in cols])
            count += 1
        conn.commit()
        return count
    finally:
        conn.close()


def insert_edges(db_path: str, name: str, edges: List[Dict[str, Any]]) -> int:
    """Insert edges. Each dict must have 'source' and 'target'."""
    if not edges:
        return 0
    conn = _connect(db_path)
    try:
        cols = list(edges[0].keys())
        placeholders = ", ".join(["?"] * len(cols))
        col_names = ", ".join(f'"{c}"' for c in cols)
        sql = f'INSERT OR REPLACE INTO "{name}_edges" ({col_names}) VALUES ({placeholders})'
        count = 0
        for edge in edges:
            conn.execute(sql, [edge.get(c) for c in cols])
            count += 1
        conn.commit()
        return count
    finally:
        conn.close()


def graph_stats(db_path: str, name: str) -> dict:
    """Get node count, edge count, and sample nodes."""
    conn = _connect(db_path)
    try:
        nodes_n = conn.execute(f'SELECT COUNT(*) as n FROM "{name}_nodes"').fetchone()["n"]
        edges_n = conn.execute(f'SELECT COUNT(*) as n FROM "{name}_edges"').fetchone()["n"]
        sample = conn.execute(f'SELECT * FROM "{name}_nodes" LIMIT 5').fetchall()
        node_cols = [d[0] for d in conn.execute(f'PRAGMA table_info("{name}_nodes")').fetchall()]
        return {
            "name": name,
            "node_count": nodes_n,
            "edge_count": edges_n,
            "node_columns": node_cols,
            "sample_nodes": [dict(r) for r in sample],
        }
    finally:
        conn.close()


def get_neighbors(db_path: str, name: str, node_id: str,
                  direction: str = "out", limit: int = 100) -> List[dict]:
    """Get neighbors of a node. direction: 'out', 'in', or 'both'."""
    conn = _connect(db_path)
    try:
        if direction == "out":
            sql = f"""
                SELECT e.target as node_id, n.*
                FROM "{name}_edges" e
                LEFT JOIN "{name}_nodes" n ON e.target = n.node_id
                WHERE e.source = ? LIMIT ?
            """
            rows = conn.execute(sql, (node_id, limit)).fetchall()
        elif direction == "in":
            sql = f"""
                SELECT e.source as node_id, n.*
                FROM "{name}_edges" e
                LEFT JOIN "{name}_nodes" n ON e.source = n.node_id
                WHERE e.target = ? LIMIT ?
            """
            rows = conn.execute(sql, (node_id, limit)).fetchall()
        else:  # both
            sql = f"""
                SELECT DISTINCT related.node_id, n.* FROM (
                    SELECT target as node_id FROM "{name}_edges" WHERE source = ?
                    UNION
                    SELECT source as node_id FROM "{name}_edges" WHERE target = ?
                ) related
                LEFT JOIN "{name}_nodes" n ON related.node_id = n.node_id
                LIMIT ?
            """
            rows = conn.execute(sql, (node_id, node_id, limit)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def shortest_path(db_path: str, name: str, source: str, target: str,
                  max_depth: int = 6) -> Optional[dict]:
    """Find shortest path between two nodes using BFS via recursive SQL CTE."""
    conn = _connect(db_path)
    try:
        sql = f"""
            WITH RECURSIVE bfs(depth, node_id, path) AS (
                SELECT 0, ?, ?
                UNION ALL
                SELECT bfs.depth + 1, e.target, bfs.path || ',' || e.target
                FROM bfs
                JOIN "{name}_edges" e ON e.source = bfs.node_id
                WHERE bfs.depth < ?
                  AND instr(bfs.path, e.target) = 0
            )
            SELECT path, depth FROM bfs
            WHERE node_id = ?
            ORDER BY depth LIMIT 1
        """
        row = conn.execute(sql, (source, source, max_depth, target)).fetchone()
        if row:
            return {"path": row["path"].split(","), "length": row["depth"]}
        return None
    finally:
        conn.close()


def export_vis_network(db_path: str, name: str, max_nodes: int = 500) -> dict:
    """Export graph as vis-network JSON (nodes + edges) for dashboard."""
    conn = _connect(db_path)
    try:
        nodes = conn.execute(f'SELECT * FROM "{name}_nodes" LIMIT ?', (max_nodes,)).fetchall()
        node_ids = {r["node_id"] for r in nodes}

        if node_ids:
            id_list = list(node_ids)
            placeholders = ",".join("?" * len(id_list))
            edges = conn.execute(
                f'SELECT * FROM "{name}_edges" WHERE source IN ({placeholders}) AND target IN ({placeholders}) LIMIT 5000',
                id_list + id_list
            ).fetchall()
        else:
            edges = []

        return {
            "nodes": [{"id": r["node_id"], "label": r["node_id"],
                       "title": str({k: r[k] for k in r.keys() if k != "node_id"})}
                      for r in nodes],
            "edges": [{"from": r["source"], "to": r["target"]} for r in edges],
        }
    finally:
        conn.close()
