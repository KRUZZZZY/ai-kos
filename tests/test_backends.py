"""Tests for time-series and graph backends."""
import tempfile, os, pytest
from datetime import datetime, timedelta


@pytest.fixture
def ts_db():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)


class TestTimeSeries:
    def test_query_time_range(self, ts_db):
        from ai_kos.datasets import create_table, insert_rows, query_time_range
        create_table(ts_db, "metrics", [
            {"name": "ts", "type": "TEXT"}, {"name": "value", "type": "REAL"},
        ])
        base = datetime(2024, 1, 1, 12, 0, 0)
        rows = [{"ts": (base + timedelta(minutes=i)).isoformat(), "value": float(i * 10)} for i in range(10)]
        insert_rows(ts_db, "metrics", rows)

        results = query_time_range(ts_db, "metrics", "ts",
                                   from_ts="2024-01-01T12:03:00", to_ts="2024-01-01T12:06:00")
        assert len(results) == 4

    def test_timeseries_stats(self, ts_db):
        from ai_kos.datasets import create_table, insert_rows, timeseries_stats
        create_table(ts_db, "temps", [
            {"name": "time", "type": "TEXT"}, {"name": "celsius", "type": "REAL"},
        ])
        base = datetime(2024, 1, 1, 0, 0, 0)
        rows = [
            {"time": base.isoformat(), "celsius": 20.0},
            {"time": (base + timedelta(hours=1)).isoformat(), "celsius": 22.0},
        ]
        insert_rows(ts_db, "temps", rows)
        stats = timeseries_stats(ts_db, "temps", "time")
        assert stats["total_rows"] == 2
        assert stats["numeric_columns"] == ["celsius"]

    def test_detect_gaps(self, ts_db):
        from ai_kos.datasets import create_table, insert_rows, detect_gaps
        create_table(ts_db, "readings", [
            {"name": "t", "type": "TEXT"}, {"name": "val", "type": "INTEGER"},
        ])
        base = datetime(2024, 1, 1, 12, 0, 0)
        rows = [{"t": (base + timedelta(minutes=m)).isoformat(), "val": m} for m in [0, 1, 2, 5, 6]]
        insert_rows(ts_db, "readings", rows)
        gaps = detect_gaps(ts_db, "readings", "t", expected_interval_seconds=60)
        assert gaps["gap_count"] == 1
        assert gaps["gaps"][0]["missing_points"] >= 2

    def test_empty_timeseries(self, ts_db):
        from ai_kos.datasets import create_table, timeseries_stats
        create_table(ts_db, "empty", [{"name": "t", "type": "TEXT"}, {"name": "v", "type": "REAL"}])
        stats = timeseries_stats(ts_db, "empty", "t")
        assert stats["total_rows"] == 0


@pytest.fixture
def graph_db():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)


class TestGraphCRUD:
    def test_create_and_insert(self, graph_db):
        from ai_kos.graphs import create_graph, insert_nodes, insert_edges, graph_stats
        create_graph(graph_db, "test_graph")
        n = insert_nodes(graph_db, "test_graph", [
            {"node_id": "A"}, {"node_id": "B"}, {"node_id": "C"},
        ])
        assert n == 3
        e = insert_edges(graph_db, "test_graph", [
            {"source": "A", "target": "B"}, {"source": "B", "target": "C"},
        ])
        assert e == 2
        stats = graph_stats(graph_db, "test_graph")
        assert stats["node_count"] == 3
        assert stats["edge_count"] == 2

    def test_neighbors(self, graph_db):
        from ai_kos.graphs import create_graph, insert_nodes, insert_edges, get_neighbors
        create_graph(graph_db, "nbr_test")
        insert_nodes(graph_db, "nbr_test", [{"node_id": "X"}, {"node_id": "Y"}, {"node_id": "Z"}])
        insert_edges(graph_db, "nbr_test", [{"source": "X", "target": "Y"}, {"source": "X", "target": "Z"}])
        neighbors = get_neighbors(graph_db, "nbr_test", "X", "out")
        assert len(neighbors) == 2
        nids = {n["node_id"] for n in neighbors}
        assert nids == {"Y", "Z"}

    def test_shortest_path(self, graph_db):
        from ai_kos.graphs import create_graph, insert_nodes, insert_edges, shortest_path
        create_graph(graph_db, "path_test")
        insert_nodes(graph_db, "path_test", [{"node_id": str(i)} for i in range(5)])
        insert_edges(graph_db, "path_test", [{"source": str(i), "target": str(i+1)} for i in range(4)])
        path = shortest_path(graph_db, "path_test", "0", "4")
        assert path is not None
        assert path["length"] == 4

    def test_no_path(self, graph_db):
        from ai_kos.graphs import create_graph, insert_nodes, shortest_path
        create_graph(graph_db, "disconnected")
        insert_nodes(graph_db, "disconnected", [{"node_id": "A"}, {"node_id": "B"}])
        path = shortest_path(graph_db, "disconnected", "A", "B")
        assert path is None

    def test_export_vis(self, graph_db):
        from ai_kos.graphs import create_graph, insert_nodes, insert_edges, export_vis_network
        create_graph(graph_db, "vis_test")
        insert_nodes(graph_db, "vis_test", [{"node_id": "1"}, {"node_id": "2"}])
        insert_edges(graph_db, "vis_test", [{"source": "1", "target": "2"}])
        exported = export_vis_network(graph_db, "vis_test")
        assert len(exported["nodes"]) == 2
        assert len(exported["edges"]) == 1

    def test_drop_graph(self, graph_db):
        from ai_kos.graphs import create_graph, drop_graph
        create_graph(graph_db, "to_drop")
        drop_graph(graph_db, "to_drop")


class TestJSONFunctions:
    def test_store_and_retrieve(self, ts_db):
        from ai_kos.datasets import store_json_doc, get_json_doc
        data = {"name": "Test", "values": [1, 2, 3], "nested": {"key": "val"}}
        store_json_doc(ts_db, "json_docs", "test-doc", data)
        result = get_json_doc(ts_db, "json_docs", "test-doc")
        assert result["name"] == "Test"
        assert len(result["values"]) == 3
        assert result["nested"]["key"] == "val"

    def test_json_query_array(self, ts_db):
        from ai_kos.datasets import store_json_doc, json_query
        data = {"repos": [{"name": "ai-kos", "stars": 5}, {"name": "hermes", "stars": 100}]}
        store_json_doc(ts_db, "json_docs", "repos", data)
        results = json_query(ts_db, "json_docs", "repos", "$.repos[*].name")
        names = [r["value"] for r in results]
        assert "ai-kos" in names
        assert "hermes" in names

    def test_json_query_root(self, ts_db):
        from ai_kos.datasets import store_json_doc, json_query
        data = {"hello": "world"}
        store_json_doc(ts_db, "json_docs", "simple", data)
        results = json_query(ts_db, "json_docs", "simple", "$")
        assert results[0]["value"] == data

    def test_json_stats(self, ts_db):
        from ai_kos.datasets import store_json_doc, json_stats
        data = {"users": [{"name": "Alice"}, {"name": "Bob"}], "count": 2}
        store_json_doc(ts_db, "json_docs", "stats-test", data)
        stats = json_stats(ts_db, "json_docs", "stats-test")
        assert "users" in stats["top_level_keys"]
        assert stats["array_users_length"] == 2

    def test_flatten_for_index(self):
        from ai_kos.search import _flatten_json_for_index
        data = {"birds": [{"name": "Raven", "family": "Corvidae"}]}
        text = _flatten_json_for_index(data)
        assert "birds" in text
        assert "Raven" in text
