"""Tests for AI-KOS datasets module — SQL table CRUD and CSV ingest."""
import tempfile
import os
import csv
import pytest


@pytest.fixture
def temp_db():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)


class TestTableCRUD:
    def test_create_and_drop(self, temp_db):
        from ai_kos.datasets import create_table, drop_table, table_stats
        columns = [{"name": "id", "type": "INTEGER"}, {"name": "name", "type": "TEXT"}]
        create_table(temp_db, "test_table", columns)
        stats = table_stats(temp_db, "test_table")
        assert stats is not None
        assert stats["row_count"] == 0
        assert len(stats["columns"]) == 2
        assert drop_table(temp_db, "test_table") is True
        assert table_stats(temp_db, "test_table") is None

    def test_drop_nonexistent(self, temp_db):
        from ai_kos.datasets import drop_table
        assert drop_table(temp_db, "no_such_table") is False

    def test_insert_and_query(self, temp_db):
        from ai_kos.datasets import create_table, insert_rows, query_table
        columns = [{"name": "species", "type": "TEXT"}, {"name": "count", "type": "INTEGER"}]
        create_table(temp_db, "birds", columns)
        rows = [
            {"species": "Corvus corax", "count": 100},
            {"species": "Pica pica", "count": 200},
        ]
        n = insert_rows(temp_db, "birds", rows)
        assert n == 2
        results = query_table(temp_db, "SELECT * FROM birds WHERE count > ?", (150,))
        assert len(results) == 1
        assert results[0]["species"] == "Pica pica"

    def test_table_stats(self, temp_db):
        from ai_kos.datasets import create_table, insert_rows, table_stats
        columns = [{"name": "x", "type": "REAL"}, {"name": "y", "type": "INTEGER"}]
        create_table(temp_db, "points", columns)
        insert_rows(temp_db, "points", [{"x": 1.5, "y": 10}, {"x": 2.5, "y": 20}])
        stats = table_stats(temp_db, "points")
        assert stats["row_count"] == 2
        assert stats["columns"][0]["name"] == "x"
        assert stats["columns"][0]["type"] == "REAL"

    def test_list_tables(self, temp_db):
        from ai_kos.datasets import create_table, list_tables
        create_table(temp_db, "alpha", [{"name": "a", "type": "TEXT"}])
        create_table(temp_db, "beta", [{"name": "b", "type": "TEXT"}])
        tables = list_tables(temp_db)
        assert "alpha" in tables
        assert "beta" in tables

    def test_query_limit(self, temp_db):
        from ai_kos.datasets import create_table, insert_rows, query_table
        create_table(temp_db, "big", [{"name": "n", "type": "INTEGER"}])
        insert_rows(temp_db, "big", [{"n": i} for i in range(1000)])
        results = query_table(temp_db, "SELECT * FROM big", limit=50)
        assert len(results) == 50
        assert results[0]["n"] == 0


class TestCSVIngest:
    def test_ingest_basic(self, temp_db):
        import csv
        from ai_kos.datasets import ingest_csv, table_stats, query_table

        csv_path = temp_db + ".csv"
        with open(csv_path, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(["scientific_name", "common_name", "family", "population"])
            w.writerow(["Corvus corax", "Common Raven", "Corvidae", "16000000"])
            w.writerow(["Pica pica", "Eurasian Magpie", "Corvidae", "75000000"])

        result = ingest_csv(csv_path, temp_db, "bird_species")
        assert result["row_count"] == 2
        assert result["table"] == "bird_species"
        assert result["columns"][0]["type"] == "TEXT"
        assert result["columns"][3]["type"] == "INTEGER"  # population

        stats = table_stats(temp_db, "bird_species")
        assert stats["row_count"] == 2

        ravens = query_table(temp_db,
                             "SELECT * FROM bird_species WHERE family = ?", ("Corvidae",))
        assert len(ravens) == 2
        assert ravens[0]["common_name"] == "Common Raven"

        os.unlink(csv_path)

    def test_type_inference(self, temp_db):
        import csv
        from ai_kos.datasets import ingest_csv
        from ai_kos.datasets import _guess_type

        assert _guess_type("42", "count") == "INTEGER"
        assert _guess_type("3.14", "ratio") == "REAL"
        assert _guess_type("hello", "name") == "TEXT"
        assert _guess_type("2024", "year") == "INTEGER"
        assert _guess_type("1.234", "latitude") == "REAL"


class TestSQLArticleCreate:
    def test_create_and_read_sql_article(self, tmp_path, monkeypatch):
        """Integration test: create a SQL-backed article, insert rows, read it back."""
        import uuid
        from datetime import date
        from ai_kos.schemas import DatasetColumn, DatasetRef
        from ai_kos.config import get

        # Use temp knowledge dir
        kd = str(tmp_path / "knowledge")
        monkeypatch.setattr("ai_kos.config._config", None)
        monkeypatch.setattr("ai_kos.articles.KNOWLEDGE_DIR", kd)
        monkeypatch.setattr("ai_kos.linker.KNOWLEDGE_DIR", kd, raising=False)

        from ai_kos.articles import create_article, read_article, delete_article, _refresh_index
        _refresh_index()

        today = date.today()
        columns = [DatasetColumn(name="name", type="TEXT"), DatasetColumn(name="value", type="INTEGER")]
        ds_ref = DatasetRef(db=str(tmp_path / "test.db"), table="test_data", columns=columns)

        data = {
            "id": str(uuid.uuid4()), "title": "Test Dataset", "slug": "test-dataset",
            "type": "base", "created_at": today, "updated_at": today, "reviewed_at": today,
            "next_review_at": date(2027, 1, 1), "keywords": ["test", "data", "sql"],
            "summary": "A test SQL dataset.", "backend": "sql", "dataset": ds_ref,
            "provenance": [{"source": "ingest", "origin_ref": "test.csv"}],
            "confidence": 0.9,
        }

        result = create_article("base", data)
        assert result["status"] == "created"
        assert result["backend"] == "sql"
        assert result["table"] == "test_data"

        # Insert some rows
        from ai_kos.datasets import insert_rows
        insert_rows(str(tmp_path / "test.db"), "test_data", [
            {"name": "alpha", "value": 10},
            {"name": "beta", "value": 20},
        ])

        # Read it back
        article = read_article("test-dataset")
        assert article["backend"] == "sql"
        assert article["row_count"] == 2
        assert len(article["preview"]) == 2
        assert article["preview"][0]["name"] == "alpha"

        # Cleanup
        delete_article("test-dataset")
