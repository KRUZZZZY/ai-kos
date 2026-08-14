"""AI-KOS datasets module — SQL table CRUD for structured/tabular data.

Each dataset is a SQLite table in a database file under datasets/.
Articles reference datasets via DatasetRef (db + table + column list).

This module is separate from db.py (which stores article body text).
Here we handle structured rows — bird species, chemical compounds, financial records.
"""

import sqlite3
import csv
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

logger = logging.getLogger("ai-kos.datasets")


def _connect(db_path: str) -> sqlite3.Connection:
    """Open a SQLite connection with WAL mode and 5s timeout."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


def create_table(db_path: str, table_name: str, columns: List[Dict[str, str]]) -> None:
    """CREATE TABLE IF NOT EXISTS with given column definitions.

    columns: [{"name": "scientific_name", "type": "TEXT"}, ...]
    """
    col_defs = []
    for col in columns:
        name = col["name"]
        col_type = col.get("type", "TEXT")
        col_defs.append(f'"{name}" {col_type}')

    sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join(col_defs)})'
    conn = _connect(db_path)
    try:
        conn.execute(sql)
        conn.commit()
        logger.info(f"Created table {table_name} in {db_path} ({len(columns)} columns)")
    finally:
        conn.close()


def drop_table(db_path: str, table_name: str) -> bool:
    """DROP TABLE IF EXISTS. Returns True if a table was dropped."""
    conn = _connect(db_path)
    try:
        # Check if table exists first
        exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
        ).fetchone()
        if exists:
            conn.execute(f'DROP TABLE "{table_name}"')
            conn.commit()
            logger.info(f"Dropped table {table_name} from {db_path}")
            return True
        return False
    finally:
        conn.close()


def insert_rows(db_path: str, table_name: str, rows: List[Dict[str, Any]]) -> int:
    """Insert multiple rows into a table. Returns number of rows inserted."""
    if not rows:
        return 0

    columns = list(rows[0].keys())
    placeholders = ", ".join(["?"] * len(columns))
    col_names = ", ".join(f'"{c}"' for c in columns)

    sql = f'INSERT INTO "{table_name}" ({col_names}) VALUES ({placeholders})'

    conn = _connect(db_path)
    try:
        count = 0
        for row in rows:
            values = [row.get(c) for c in columns]
            conn.execute(sql, values)
            count += 1
        conn.commit()
        return count
    finally:
        conn.close()


def query_table(db_path: str, sql: str, params: Optional[tuple] = None,
                limit: int = 500) -> List[Dict[str, Any]]:
    """Run a SELECT query and return rows as list of dicts.

    Capped at `limit` rows for safety. Returns column names + row data.
    """
    conn = _connect(db_path)
    try:
        cursor = conn.execute(sql, params or ())
        rows = cursor.fetchmany(limit)
        return [dict(r) for r in rows]
    finally:
        conn.close()


def table_stats(db_path: str, table_name: str) -> Optional[dict]:
    """Get row count and column info for a table. Returns None if table doesn't exist."""
    conn = _connect(db_path)
    try:
        exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
        ).fetchone()
        if not exists:
            return None

        row_count = conn.execute(f'SELECT COUNT(*) as n FROM "{table_name}"').fetchone()["n"]
        col_info = conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
        columns = [{"name": r["name"], "type": r["type"]} for r in col_info]

        return {"table": table_name, "db": db_path, "row_count": row_count, "columns": columns}
    finally:
        conn.close()


def list_tables(db_path: str) -> List[str]:
    """List all user tables in a database (excludes sqlite_ internal tables)."""
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        return [r["name"] for r in rows]
    finally:
        conn.close()


def ingest_csv(csv_path: str, db_path: str, table_name: str,
               delimiter: str = ",", has_header: bool = True) -> dict:
    """Ingest a CSV file into a SQLite table.

    Auto-detects column names from header row and infers types from first data row.
    Returns {table, row_count, columns}.
    """
    with open(csv_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=delimiter)
        if has_header:
            headers = next(reader)
        else:
            # Try to read first row to infer header
            first_row = next(reader)
            headers = [f"col_{i}" for i in range(len(first_row))]
            # Re-create reader to get all rows
            f.seek(0)
            reader = csv.reader(f, delimiter=delimiter)

        # Read all rows
        all_rows = list(reader)
        if has_header and all_rows:
            # Headers already consumed
            pass
        elif not has_header:
            # Skip the auto-generated header row in data
            all_rows = all_rows[1:] if all_rows else []

        if not all_rows:
            return {"error": "CSV has no data rows"}

    # Infer column types from first data row
    columns = _infer_types(headers, all_rows[0])

    # Create table
    create_table(db_path, table_name, columns)

    # Insert rows
    dict_rows = []
    for row in all_rows:
        if len(row) < len(headers):
            row = row + [None] * (len(headers) - len(row))
        elif len(row) > len(headers):
            row = row[:len(headers)]
        dict_rows.append(dict(zip(headers, row)))

    count = insert_rows(db_path, table_name, dict_rows)

    logger.info(f"Ingested {count} rows into {table_name} from {csv_path}")
    return {"table": table_name, "db": db_path, "row_count": count, "columns": columns}


def _infer_types(headers: List[str], sample_row: List[str]) -> List[Dict[str, str]]:
    """Infer SQLite column types from header names + first data row values."""
    columns = []
    for i, header in enumerate(headers):
        value = sample_row[i] if i < len(sample_row) else ""
        col_type = _guess_type(value, header)
        columns.append({"name": header.strip(), "type": col_type})
    return columns


def _guess_type(value: str, header: str) -> str:
    """Guess SQLite type from a string value and column name."""
    # Heuristic: column name hints
    header_lower = header.lower()
    if any(hint in header_lower for hint in ['id', '_id', 'count', 'population', 'year', 'age', 'size']):
        try:
            int(value)
            return "INTEGER"
        except (ValueError, TypeError):
            pass

    if any(hint in header_lower for hint in ['price', 'rate', 'ratio', 'weight', 'height', 'score',
                                              'latitude', 'longitude', 'lat', 'lon', 'lng']):
        try:
            float(value)
            return "REAL"
        except (ValueError, TypeError):
            pass

    # Try value-based inference
    try:
        int(value)
        return "INTEGER"
    except (ValueError, TypeError):
        pass

    try:
        float(value)
        return "REAL"
    except (ValueError, TypeError):
        pass

    return "TEXT"


# ── Time-Series Functions ───────────────────────────────────────

def query_time_range(db_path: str, table_name: str, time_column: str,
                     from_ts: Optional[str] = None, to_ts: Optional[str] = None,
                     limit: int = 500) -> List[Dict[str, Any]]:
    """Query a time-series table with optional time range filter."""
    conn = _connect(db_path)
    try:
        conditions = []
        params = []
        if from_ts:
            conditions.append(f'"{time_column}" >= ?')
            params.append(from_ts)
        if to_ts:
            conditions.append(f'"{time_column}" <= ?')
            params.append(to_ts)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f'SELECT * FROM "{table_name}" {where} ORDER BY "{time_column}" LIMIT ?'
        params.append(limit)

        cursor = conn.execute(sql, params)
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def timeseries_stats(db_path: str, table_name: str, time_column: str,
                     interval: str = "1h") -> dict:
    """Compute min/max/avg/count per time bucket for numeric columns."""
    conn = _connect(db_path)
    try:
        total = conn.execute(f'SELECT COUNT(*) as n FROM "{table_name}"').fetchone()["n"]
        if total == 0:
            return {"buckets": [], "total_rows": 0, "time_span": None}

        time_range = conn.execute(
            f'SELECT MIN("{time_column}") as tmin, MAX("{time_column}") as tmax FROM "{table_name}"'
        ).fetchone()

        col_info = conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
        numeric_cols = [r["name"] for r in col_info
                        if r["name"] != time_column and r["type"] in ("INTEGER", "REAL")]

        agg_parts = ["COUNT(*) as bucket_count"]
        for col in numeric_cols:
            agg_parts.append(f'MIN("{col}") as min_{col}')
            agg_parts.append(f'MAX("{col}") as max_{col}')
            agg_parts.append(f'AVG("{col}") as avg_{col}')

        sql = f"""
            SELECT strftime('%Y-%m-%dT%H:%M:%S', "{time_column}") as time_start,
                   {', '.join(agg_parts)}
            FROM "{table_name}"
            GROUP BY strftime('%Y-%m-%dT%H:00:00', "{time_column}")
            ORDER BY time_start
            LIMIT 200
        """
        buckets = [dict(r) for r in conn.execute(sql).fetchall()]

        return {
            "buckets": buckets,
            "total_rows": total,
            "time_span": {"from": time_range["tmin"], "to": time_range["tmax"]},
            "numeric_columns": numeric_cols,
            "interval_used": "1h",
        }
    finally:
        conn.close()


def detect_gaps(db_path: str, table_name: str, time_column: str,
                expected_interval_seconds: int = 60) -> dict:
    """Detect gaps (missing periods) in time-series data using LAG window function."""
    conn = _connect(db_path)
    try:
        sql = f"""
            SELECT "{time_column}",
                   LAG("{time_column}") OVER (ORDER BY "{time_column}") as prev_ts
            FROM "{table_name}"
            ORDER BY "{time_column}"
        """
        rows = conn.execute(sql).fetchall()

        gaps = []
        for row in rows:
            if row["prev_ts"] is None:
                continue
            try:
                curr = datetime.fromisoformat(str(row[time_column]).replace('Z', '+00:00'))
                prev = datetime.fromisoformat(str(row["prev_ts"]).replace('Z', '+00:00'))
                diff = (curr - prev).total_seconds()
                if diff > expected_interval_seconds * 1.5:
                    missing = int(diff / expected_interval_seconds) - 1
                    gaps.append({
                        "from": str(row["prev_ts"]),
                        "to": str(row[time_column]),
                        "gap_seconds": diff,
                        "missing_points": missing,
                    })
            except Exception:
                continue

        return {"gap_count": len(gaps), "gaps": gaps[:50]}
    finally:
        conn.close()


# ── JSON Document Functions ─────────────────────────────────────

def store_json_doc(db_path: str, table_name: str, slug: str, data: dict | list) -> None:
    """Store a JSON document (dict or list) in a json_docs table. Upserts on slug."""
    now = datetime.now(timezone.utc).isoformat()
    doc_str = json.dumps(data, ensure_ascii=False)

    conn = _connect(db_path)
    try:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS "{table_name}" (
                slug TEXT PRIMARY KEY,
                doc TEXT NOT NULL DEFAULT '{{}}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute(f"""
            INSERT INTO "{table_name}" (slug, doc, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                doc = excluded.doc, updated_at = excluded.updated_at
        """, (slug, doc_str, now, now))
        conn.commit()
        logger.info(f"Stored JSON doc {slug} in {db_path}/{table_name}")
    finally:
        conn.close()


def get_json_doc(db_path: str, table_name: str, slug: str) -> Optional[dict | list]:
    """Retrieve a JSON document by slug."""
    conn = _connect(db_path)
    try:
        row = conn.execute(
            f'SELECT doc FROM "{table_name}" WHERE slug = ?', (slug,)
        ).fetchone()
        return json.loads(row["doc"]) if row else None
    finally:
        conn.close()


def json_query(db_path: str, table_name: str, slug: str,
               json_path: str = "$", limit: int = 500) -> List[dict]:
    """Query a JSON document using JSON path expressions via SQLite JSON1."""
    conn = _connect(db_path)
    try:
        if json_path in ("$", "$.*"):
            row = conn.execute(
                f'SELECT json_extract(doc, ?) as result FROM "{table_name}" WHERE slug = ?',
                (json_path, slug)
            ).fetchone()
            if row and row["result"]:
                try:
                    val = json.loads(row["result"])
                except (json.JSONDecodeError, TypeError):
                    val = row["result"]
                return [{"value": val}] if val is not None else []
            return []

        if "[*]" in json_path:
            array_path = json_path.split("[*]")[0]
            field_path = json_path.split("[*]")[-1].lstrip(".")

            if field_path:
                sql = f"""
                    SELECT json_extract(value, ?) as value
                    FROM "{table_name}", json_each(json_extract(doc, ?))
                    WHERE slug = ? LIMIT ?
                """
                rows = conn.execute(sql, (f"$.{field_path}", array_path, slug, limit)).fetchall()
                return [{"value": r["value"]} for r in rows if r["value"] is not None]
            else:
                sql = f"""
                    SELECT value
                    FROM "{table_name}", json_each(json_extract(doc, ?))
                    WHERE slug = ? LIMIT ?
                """
                rows = conn.execute(sql, (array_path, slug, limit)).fetchall()
                return [{"value": r["value"]} for r in rows]

        row = conn.execute(
            f'SELECT json_extract(doc, ?) as result FROM "{table_name}" WHERE slug = ?',
            (json_path, slug)
        ).fetchone()
        if row and row["result"]:
            try:
                val = json.loads(row["result"])
            except (json.JSONDecodeError, TypeError):
                val = row["result"]
            return [{"value": val}]
        return []
    finally:
        conn.close()


def json_stats(db_path: str, table_name: str, slug: str) -> dict:
    """Get stats about a JSON document: size, top-level keys, array lengths."""
    conn = _connect(db_path)
    try:
        row = conn.execute(
            f'SELECT doc, LENGTH(doc) as size FROM "{table_name}" WHERE slug = ?', (slug,)
        ).fetchone()
        if not row:
            return {"error": "Document not found"}

        doc = json.loads(row["doc"])
        stats = {"size_bytes": row["size"]}

        if isinstance(doc, dict):
            stats["top_level_keys"] = list(doc.keys())
            stats["key_count"] = len(doc)
            for k, v in doc.items():
                if isinstance(v, list):
                    stats[f"array_{k}_length"] = len(v)
        elif isinstance(doc, list):
            stats["array_length"] = len(doc)
            if doc and isinstance(doc[0], dict):
                stats["item_keys"] = list(doc[0].keys())

        return stats
    finally:
        conn.close()


# ── Parquet / ORC Ingest ───────────────────────────────────────

def ingest_parquet(parquet_path: str, db_path: str, table_name: str) -> dict:
    """Ingest a Parquet file into a SQLite table. Requires pyarrow."""
    try:
        import pyarrow.parquet as pq
    except ImportError:
        return {"error": "pyarrow required: pip install pyarrow"}

    table = pq.read_table(parquet_path)
    columns = [{"name": f.name, "type": _pyarrow_to_sqlite(f.type)} for f in table.schema]

    create_table(db_path, table_name, columns)

    # Convert to list of dicts and insert in batches
    rows = table.to_pylist()
    batch_size = 1000
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        total += insert_rows(db_path, table_name, batch)

    logger.info(f"Ingested {total} rows from {parquet_path} into {table_name}")
    return {"table": table_name, "db": db_path, "row_count": total, "columns": columns,
            "source_format": "parquet"}


def ingest_orc(orc_path: str, db_path: str, table_name: str) -> dict:
    """Ingest an ORC file into a SQLite table. Requires pyarrow."""
    try:
        import pyarrow.orc as orc_mod
    except ImportError:
        return {"error": "pyarrow required: pip install pyarrow"}

    table = orc_mod.read_table(orc_path)
    columns = [{"name": f.name, "type": _pyarrow_to_sqlite(f.type)} for f in table.schema]

    create_table(db_path, table_name, columns)
    rows = table.to_pylist()
    total = 0
    for i in range(0, len(rows), 1000):
        total += insert_rows(db_path, table_name, rows[i:i + 1000])

    logger.info(f"Ingested {total} rows from {orc_path} into {table_name}")
    return {"table": table_name, "db": db_path, "row_count": total, "columns": columns,
            "source_format": "orc"}


def _pyarrow_to_sqlite(pa_type) -> str:
    """Map pyarrow types to SQLite types."""
    type_str = str(pa_type).lower()
    if any(t in type_str for t in ('int', 'timestamp', 'date', 'time')):
        return "INTEGER"
    elif any(t in type_str for t in ('float', 'double', 'decimal')):
        return "REAL"
    elif 'bool' in type_str:
        return "INTEGER"
    return "TEXT"


# ── SQLite DB Import ───────────────────────────────────────────

def import_sqlite_db(source_db: str, target_db: str, table_filter: str = None) -> dict:
    """Import tables from a source SQLite database into the target database.

    Copies schema and data for each table. Returns list of imported tables.
    """
    import sqlite3
    src = sqlite3.connect(source_db)
    src.row_factory = sqlite3.Row

    tables = src.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()

    imported = []
    for t in tables:
        tname = t["name"]
        if table_filter and table_filter not in tname:
            continue

        # Get schema
        col_info = src.execute(f'PRAGMA table_info("{tname}")').fetchall()
        columns = [{"name": c["name"], "type": c["type"]} for c in col_info]

        # Create table in target
        create_table(target_db, tname, columns)

        # Copy all rows
        rows = src.execute(f'SELECT * FROM "{tname}"').fetchall()
        if rows:
            dict_rows = [dict(r) for r in rows]
            insert_rows(target_db, tname, dict_rows)

        imported.append({
            "table": tname,
            "row_count": len(rows),
            "columns": [c["name"] for c in col_info],
        })

    src.close()
    logger.info(f"Imported {len(imported)} tables from {source_db}")
    return {"source": source_db, "tables_imported": len(imported), "tables": imported}


def ingest_sql_dump(sql_path: str, db_path: str) -> dict:
    """Execute a SQL dump file against a SQLite database.

    Attempts to normalize PostgreSQL-specific syntax for SQLite compatibility.
    Returns list of created tables with row counts.
    """
    import sqlite3, re

    with open(sql_path) as f:
        sql = f.read()

    # Normalize PostgreSQL → SQLite
    sql = re.sub(r'\bSERIAL\b', 'INTEGER', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bBIGSERIAL\b', 'INTEGER', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bBOOLEAN\b', 'INTEGER', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bGEOGRAPHY\([^)]+\)', 'TEXT', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bGEOMETRY\([^)]+\)', 'TEXT', sql, flags=re.IGNORECASE)
    sql = re.sub(r"ST_GeogFromText\('[^']*'\)", "''", sql)
    sql = re.sub(r"ST_GeomFromText\('[^']*'\)", "''", sql)
    sql = re.sub(r'CREATE EXTENSION[^;]*;', '', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bNOW\(\)', "datetime('now')", sql, flags=re.IGNORECASE)

    conn = _connect(db_path)
    try:
        conn.executescript(sql)
        conn.commit()

        # Get imported tables
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()

        results = []
        for t in tables:
            tname = t["name"]
            cnt = conn.execute(f'SELECT COUNT(*) as n FROM "{tname}"').fetchone()["n"]
            cols = conn.execute(f'PRAGMA table_info("{tname}")').fetchall()
            results.append({
                "table": tname,
                "row_count": cnt,
                "columns": [c["name"] for c in cols],
            })

        logger.info(f"Executed SQL dump: {len(results)} tables imported")
        return {"source": sql_path, "tables_imported": len(results), "tables": results}
    except Exception as e:
        return {"error": f"SQL execution failed: {e}", "source": sql_path}
    finally:
        conn.close()
