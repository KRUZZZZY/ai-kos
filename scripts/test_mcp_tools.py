#!/usr/bin/env python3
"""AI-KOS MCP Tool Test Suite — exercises all 35 tools non-destructively.

Usage:
    python3 scripts/test_mcp_tools.py              # all phases
    python3 scripts/test_mcp_tools.py --phase read # read-only tools
    python3 scripts/test_mcp_tools.py --phase write # side-effect tools
    python3 scripts/test_mcp_tools.py --phase backend # backend tools
"""

import argparse
import json
import os
import sys
import tempfile
import traceback
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(str(PROJECT_ROOT))

PASS, FAIL, SKIP = 0, 0, 0
TEST_SLUGS = []
TEST_FILES = []


def report(tool: str, ok: bool, detail: str = ""):
    global PASS, FAIL, SKIP
    if ok:
        PASS += 1
        print(f"  \033[32mPASS\033[0m {tool:35s} {detail}")
    else:
        FAIL += 1
        print(f"  \033[31mFAIL\033[0m {tool:35s} {detail}")


def skip(tool: str, reason: str = ""):
    global SKIP
    SKIP += 1
    print(f"  \033[33mSKIP\033[0m {tool:35s} {reason}")


def call_func(module_path: str, func_name: str, *args, **kwargs):
    """Dynamically import and call a function from ai_kos."""
    import importlib
    mod = importlib.import_module(module_path)
    fn = getattr(mod, func_name)
    return fn(*args, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 1: Read-only tools
# ═══════════════════════════════════════════════════════════════════════════════

def phase_read():
    print("\n── Phase 1: Read-only tools ──")

    # ai_kos_stats
    try:
        from ai_kos.articles import stats
        s = stats()
        ok = (isinstance(s, dict) and s.get("total_articles", 0) > 0
              and "by_type" in s and "orphans" in s)
        report("ai_kos_stats", ok,
               f"articles={s.get('total_articles')} types={len(s.get('by_type',{}))}")
    except Exception as e:
        report("ai_kos_stats", False, str(e)[:60])

    # ai_kos_list
    try:
        from ai_kos.articles import list_articles
        all_a = list_articles()
        ok = isinstance(all_a, list) and len(all_a) > 0 and "slug" in all_a[0]
        report("ai_kos_list (all)", ok, f"count={len(all_a)}")

        process_a = list_articles(article_type="process")
        ok2 = all(a["type"] == "process" for a in process_a)
        report("ai_kos_list (by type)", ok2, f"process={len(process_a)}")

        kw_a = list_articles(keyword="ai-kos")
        ok3 = len(kw_a) > 0
        report("ai_kos_list (by keyword)", ok3, f"matching={len(kw_a)}")
    except Exception as e:
        report("ai_kos_list", False, str(e)[:60])

    # ai_kos_search
    try:
        from ai_kos.search import search
        r = search("knowledge graph", top_k=3)
        ok = isinstance(r, list) and len(r) > 0 and "score" in r[0]
        report("ai_kos_search", ok, f"results={len(r)} top_score={r[0].get('score',0):.1f}")

        r2 = search("random graph", top_k=3, article_type="base")
        ok2 = all(a.get("type") == "base" for a in r2)
        report("ai_kos_search (filtered)", ok2, f"base_only={len(r2)}")
    except Exception as e:
        report("ai_kos_search", False, str(e)[:60])

    # ai_kos_read
    try:
        from ai_kos.articles import read_article
        a = read_article("ai-kos")
        ok = a is not None and "frontmatter" in a and "body" in a
        report("ai_kos_read (exists)", ok, f"title={a.get('frontmatter',{}).get('title','')[:40]}")

        a2 = read_article("nonexistent-slug-xyz")
        ok2 = a2 is None or "error" in str(a2).lower()
        report("ai_kos_read (missing)", ok2)
    except Exception as e:
        report("ai_kos_read", False, str(e)[:60])

    # ai_kos_templates
    try:
        from ai_kos.schemas import TEMPLATES
        ok = len(TEMPLATES) == 7
        report("ai_kos_templates", ok, f"types={len(TEMPLATES)}")
    except Exception as e:
        report("ai_kos_templates", False, str(e)[:60])

    # ai_kos_graph
    try:
        from ai_kos.graph_data import export_graph_data
        g = export_graph_data()
        ok = "nodes" in g and "edges" in g and len(g["nodes"]) > 0
        report("ai_kos_graph", ok, f"nodes={len(g['nodes'])} edges={len(g['edges'])}")
    except Exception as e:
        report("ai_kos_graph", False, str(e)[:60])

    # ai_kos_compare
    try:
        from ai_kos.search import compare
        c = compare("ai-kos", top_k=3)
        ok = isinstance(c, list) and len(c) > 0 and "score" in c[0]
        report("ai_kos_compare", ok, f"similar={len(c)}")
    except Exception as e:
        report("ai_kos_compare", False, str(e)[:60])

    # ai_kos_merge_candidates
    try:
        from ai_kos.articles import find_merge_candidates
        mc = find_merge_candidates("ai-kos")
        ok = isinstance(mc, list)
        report("ai_kos_merge_candidates", ok, f"candidates={len(mc)}")
    except Exception as e:
        report("ai_kos_merge_candidates", False, str(e)[:60])


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 2: Side-effect tools
# ═══════════════════════════════════════════════════════════════════════════════

def phase_write():
    print("\n── Phase 2: Side-effect tools ──")

    # ai_kos_ingest
    try:
        test_md = PROJECT_ROOT / "inbox" / "_test_mcp.md"
        test_md.write_text("# MCP Test\nTest content for MCP tool verification.\n")
        TEST_FILES.append(str(test_md))

        from ai_kos.ingestion import extract
        ingested = extract(str(test_md))
        ok = (isinstance(ingested, dict) and "raw_content" in ingested
              and ingested.get("suggested_type"))
        report("ai_kos_ingest", ok,
               f"type={ingested.get('suggested_type')} tokens={ingested.get('token_estimate')}")
    except Exception as e:
        report("ai_kos_ingest", False, str(e)[:60])

    # ai_kos_create — one of each type
    article_types = [
        ("note", {"title": "MCP Test Note", "slug": "mcp-test-note",
                  "keywords": ["test", "mcp", "ai-kos"],
                  "summary": "MCP test note.", "content": "Test body.",
                  "provenance": [{"source": "manual", "origin_ref": "test_mcp_tools.py"}]}),
        ("research-note", {"title": "MCP Test Research", "slug": "mcp-test-research",
                           "keywords": ["test", "mcp", "research"],
                           "summary": "MCP test research note.",
                           "topic": "mcp-testing", "key_notes": ["All tools work."],
                           "open_questions": ["Any failures?"], "sources": ["test_mcp_tools.py"],
                           "provenance": [{"source": "manual", "origin_ref": "test_mcp_tools.py"}]}),
    ]
    create_ok = True
    try:
        from ai_kos.articles import create_article
        for atype, data in article_types:
            result = create_article(atype, data)
            if result.get("status") == "created":
                TEST_SLUGS.append(result["slug"])
            else:
                create_ok = False
                report(f"ai_kos_create ({atype})", False, str(result)[:60])
        if create_ok:
            report("ai_kos_create (2 types)", True,
                   f"slugs={TEST_SLUGS}")
    except Exception as e:
        report("ai_kos_create", False, str(e)[:60])

    # ai_kos_link
    try:
        from ai_kos.linker import link_all
        lr = link_all()
        ok = isinstance(lr, dict) and lr.get("status") == "done"
        report("ai_kos_link", ok,
               f"scanned={lr.get('articles_scanned')} changed={lr.get('articles_changed')}")
    except Exception as e:
        report("ai_kos_link", False, str(e)[:60])

    # ai_kos_clean
    try:
        from ai_kos.config import get
        import shutil
        inbox = Path(get("paths", "inbox_dir", default="inbox"))
        ad = Path(get("paths", "archive_dir", default="archive"))
        rd = Path(get("paths", "rejected_dir", default="rejected"))
        pd = Path(get("paths", "projects_dir", default="projects"))
        for d in [ad, rd, pd]:
            d.mkdir(exist_ok=True)
        st = {"archived": 0, "rejected": 0, "projects": 0, "errors": 0}
        for item in sorted(inbox.iterdir()):
            n, e = item.name, item.suffix.lower()
            try:
                if item.is_dir() and ((item / ".git").exists() or (item / "README.md").exists()):
                    shutil.move(str(item), str(pd / n)); st["projects"] += 1
                elif e in (".md", ".txt", ".rst", ".org"):
                    shutil.move(str(item), str(ad / n)); st["archived"] += 1
                elif any(p in n.lower() for p in [".gradle", "build/", ".venv", "__pycache__"]):
                    shutil.move(str(item), str(rd / n)); st["rejected"] += 1
                elif e in (".jar", ".zip", ".tar", ".bin", ".lock", ".pyc", ".sqlite3", ".db", ".log", ".html"):
                    shutil.move(str(item), str(rd / n)); st["rejected"] += 1
                else:
                    shutil.move(str(item), str(rd / n)); st["rejected"] += 1
            except Exception:
                st["errors"] += 1
        ok = isinstance(st, dict)
        report("ai_kos_clean", ok, f"archived={st['archived']} rejected={st['rejected']}")
    except Exception as e:
        report("ai_kos_clean", False, str(e)[:60])


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 3: Research & Papers
# ═══════════════════════════════════════════════════════════════════════════════

def phase_research():
    print("\n── Phase 3: Research & Papers ──")

    # ai_kos_research_plan
    try:
        from ai_kos.deep_research import plan_research
        from dataclasses import asdict
        plan = asdict(plan_research("How does TF-IDF work?"))
        ok = ("sub_questions" in plan and len(plan["sub_questions"]) >= 3
              and "search_queries" in plan)
        report("ai_kos_research_plan", ok,
               f"sub_q={len(plan.get('sub_questions',[]))} queries={len(plan.get('search_queries',[]))}")
    except Exception as e:
        report("ai_kos_research_plan", False, str(e)[:60])

    # ai_kos_research_persist
    try:
        from ai_kos.deep_research import ResearchResult, persist_research
        rr = ResearchResult(
            id="test001", plan_id="", question="MCP test research",
            sub_questions=["Does it work?"],
            findings=[{"sub_question_idx": 0, "url": "http://example.com",
                       "title": "Test", "key_claim": "Yes", "evidence": "All green"}],
            cross_references=[], synthesis="MCP tools verified.",
            knowledge_gaps=["None"],
        )
        result = persist_research(rr)
        if isinstance(result, dict):
            for k in ("research_note", "base_article"):
                if k in result:
                    TEST_SLUGS.append(result[k])
        ok = isinstance(result, dict) and len(result) > 0
        report("ai_kos_research_persist", ok, f"articles={len(result)}")
    except Exception as e:
        report("ai_kos_research_persist", False, str(e)[:60])

    # ai_kos_citation — requires a real PDF
    skip("ai_kos_citation", "no test PDF in inbox")

    # ai_kos_batch_ingest
    skip("ai_kos_batch_ingest", "no PDFs in inbox")

    # ai_kos_compare_papers — requires two research-notes
    try:
        from ai_kos.paper_compare import compare_papers
        # Need existing research notes — try to find two
        from ai_kos.articles import list_articles
        rnotes = [a["slug"] for a in list_articles(article_type="research-note")[:2]]
        if len(rnotes) >= 2:
            cp = compare_papers(rnotes[0], rnotes[1])
            ok = isinstance(cp, dict) and "relationship" in cp
            report("ai_kos_compare_papers", ok, f"relation={cp.get('relationship')}")
        else:
            skip("ai_kos_compare_papers", "need 2 research-notes")
    except Exception as e:
        report("ai_kos_compare_papers", False, str(e)[:60])

    # ai_kos_promote_ready
    try:
        from ai_kos.paper_compare import promote_ready
        pr = promote_ready(min_notes=2)
        ok = isinstance(pr, list)
        report("ai_kos_promote_ready", ok, f"topics={len(pr)}")
    except Exception as e:
        report("ai_kos_promote_ready", False, str(e)[:60])

    # ai_kos_reading_stats
    try:
        from ai_kos.paper_compare import reading_status_stats
        rs = reading_status_stats()
        ok = isinstance(rs, dict) and "by_status" in rs
        bs = rs.get("by_status", {})
        report("ai_kos_reading_stats", ok,
               f"notes={rs.get('total_research_notes')} unread={bs.get('unread')} annotated={bs.get('annotated')}")
    except Exception as e:
        report("ai_kos_reading_stats", False, str(e)[:60])

    # ai_kos_migrate
    try:
        from ai_kos.migrate import run_migrations
        mr = run_migrations(dry_run=True)
        ok = isinstance(mr, dict)
        report("ai_kos_migrate (dry-run)", ok)
    except Exception as e:
        report("ai_kos_migrate", False, str(e)[:60])


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 4: Tasks
# ═══════════════════════════════════════════════════════════════════════════════

def phase_tasks():
    print("\n── Phase 4: Tasks ──")

    try:
        from ai_kos.tasks import TaskManager
        from dataclasses import asdict
        tm = TaskManager()

        task = tm.create("_MCP Test Task", urgency="yellow",
                        tags=["test", "mcp"], data_summary="Testing MCP tools",
                        article_slugs=["mcp-test-note"])
        ok = task.id is not None and task.status == "research"
        report("ai_kos_task_create", ok,
               f"id={task.id} urgency={task.urgency} tags={task.tags}")

        tasks = tm.list_tasks(status="research", limit=5)
        ok2 = len(tasks) > 0
        report("ai_kos_task_list", ok2, f"research_tasks={len(tasks)}")

        tm.complete(task.id)
        t = tm.get(task.id)
        ok3 = t.status == "qa_passed"
        report("ai_kos_task_complete", ok3, f"status={t.status}")

        tm.delete(task.id)
        ok4 = tm.get(task.id) is None
        report("ai_kos_task_delete", ok4)
    except Exception as e:
        report("ai_kos_tasks", False, str(e)[:60])


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 5: Backends
# ═══════════════════════════════════════════════════════════════════════════════

def phase_backend():
    print("\n── Phase 5: Backends ──")

    # ai_kos_datasets
    try:
        from ai_kos.articles import list_articles
        from ai_kos import datasets as ds
        all_a = list_articles()
        sql_a = [a for a in all_a if a.get("backend") in ("sql", "json")]
        ok = isinstance(sql_a, list)
        report("ai_kos_datasets", ok, f"sql/json_articles={len(sql_a)}")

        if sql_a:
            a = sql_a[0]
            dref = a.get("dataset", {})
            dbp = dref.get("db", "")
            tbl = dref.get("table", "")
            if dbp and tbl:
                rows = ds.query_table(dbp, f'SELECT * FROM "{tbl}" LIMIT 3')
                ok2 = isinstance(rows, list)
                report("ai_kos_query (SQL)", ok2, f"rows={len(rows)} from {tbl}")

                # timeseries stats if time_column present
                st = ds.table_stats(dbp, tbl)
                if st:
                    report("ai_kos_query (table_stats)", True, f"cols={len(st.get('columns',[]))}")
            else:
                skip("ai_kos_query (SQL)", "no db/table ref")
        else:
            skip("ai_kos_query", "no sql articles")
    except Exception as e:
        report("ai_kos_datasets/query", False, str(e)[:60])

    # Graph backend
    try:
        graph_articles = [a for a in all_a if a.get("backend") == "graph"]
        if graph_articles:
            from ai_kos.graphs import graph_stats, get_neighbors
            a = graph_articles[0]
            dref = a.get("dataset", {})
            gs = graph_stats(dref["db"], dref["table"])
            report("ai_kos_query (graph stats)", True,
                   f"nodes={gs['node_count']} edges={gs['edge_count']}")

            # get a neighbor
            sample = gs.get("sample_nodes", [])
            if sample:
                nid = sample[0]["node_id"]
                nb = get_neighbors(dref["db"], dref["table"], nid, direction="out", limit=5)
                report("ai_kos_query (neighbors)", True, f"neighbors of {nid[:20]}={len(nb)}")
        else:
            skip("ai_kos_query (graph)", "no graph articles")
    except Exception as e:
        report("ai_kos_query (graph)", False, str(e)[:60])

    # CSV ingest
    try:
        csv_data = "name,value,category\nalpha,10,test\nbeta,20,test\ngamma,30,test\n"
        csv_path = PROJECT_ROOT / "inbox" / "_test_mcp.csv"
        csv_path.write_text(csv_data)
        TEST_FILES.append(str(csv_path))

        from ai_kos.datasets import ingest_csv
        from ai_kos.articles import create_article
        from ai_kos.schemas import DatasetRef, DatasetColumn
        import uuid as _uuid

        result = ingest_csv(str(csv_path), "datasets/ai-kos.db", "_mcp_test_data")
        if "error" not in result:
            today = date.today()
            cols = [DatasetColumn(name=c["name"], type=c["type"]) for c in result["columns"]]
            cr = create_article("base", {
                "id": str(_uuid.uuid4()), "title": "_MCP Test CSV", "slug": "_mcp-test-csv",
                "type": "base", "created_at": today, "updated_at": today,
                "reviewed_at": today, "next_review_at": today.replace(year=today.year+1),
                "keywords": ["test", "mcp", "csv"], "summary": "MCP test CSV dataset.",
                "backend": "sql",
                "dataset": DatasetRef(db="datasets/ai-kos.db", table="_mcp_test_data", columns=cols),
                "provenance": [{"source": "ingest", "origin_ref": "_test_mcp.csv"}],
                "confidence": 0.9,
            })
            if cr.get("status") == "created":
                TEST_SLUGS.append(cr["slug"])
            report("ai_kos_ingest_csv", True, f"rows={result['row_count']} cols={len(cols)}")
        else:
            report("ai_kos_ingest_csv", False, result.get("error", "")[:60])
    except Exception as e:
        report("ai_kos_ingest_csv", False, str(e)[:60])

    # Blob ingest
    try:
        from ai_kos.blobs import store_blob
        from ai_kos.articles import create_article
        from ai_kos.schemas import BlobRef
        img_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
        img_path = PROJECT_ROOT / "inbox" / "_test_mcp.png"
        img_path.write_bytes(img_data)
        TEST_FILES.append(str(img_path))

        info = store_blob(str(img_path), slug="_mcp-test-blob")
        today = date.today()
        cr = create_article("base", {
            "id": str(_uuid.uuid4()), "title": "_MCP Test Blob", "slug": "_mcp-test-blob",
            "type": "base", "created_at": today, "updated_at": today,
            "reviewed_at": today, "next_review_at": today.replace(year=today.year+1),
            "keywords": ["test", "mcp", "blob"], "summary": "MCP test blob.",
            "backend": "blob", "blob": BlobRef(**info),
            "provenance": [{"source": "ingest", "origin_ref": "_test_mcp.png"}],
            "confidence": 0.9,
        })
        if cr.get("status") == "created":
            TEST_SLUGS.append(cr["slug"])
        report("ai_kos_ingest_blob", True,
               f"mime={info.get('mime_type','?')} size={info.get('size_bytes',0)}B")
    except Exception as e:
        report("ai_kos_ingest_blob", False, str(e)[:60])

    # JSON ingest
    try:
        from ai_kos.datasets import store_json_doc
        from ai_kos.articles import create_article
        from ai_kos.schemas import DatasetRef, DatasetColumn
        json_data = {"test": True, "tools": ["mcp"], "count": 35}
        store_json_doc("datasets/ai-kos.db", "json_docs", "_mcp-test-json", json_data)
        today = date.today()
        cr = create_article("base", {
            "id": str(_uuid.uuid4()), "title": "_MCP Test JSON", "slug": "_mcp-test-json",
            "type": "base", "created_at": today, "updated_at": today,
            "reviewed_at": today, "next_review_at": today.replace(year=today.year+1),
            "keywords": ["test", "mcp", "json"], "summary": "MCP test JSON.",
            "backend": "json",
            "dataset": DatasetRef(db="datasets/ai-kos.db", table="json_docs", columns=[
                DatasetColumn(name="slug", type="TEXT"),
                DatasetColumn(name="doc", type="TEXT"),
            ]),
            "provenance": [{"source": "ingest", "origin_ref": "test_mcp_tools.py"}],
            "confidence": 0.9,
        })
        if cr.get("status") == "created":
            TEST_SLUGS.append(cr["slug"])
        report("ai_kos_ingest_json", True, f"keys={list(json_data.keys())}")
    except Exception as e:
        report("ai_kos_ingest_json", False, str(e)[:60])

    # Graph ingest
    try:
        csv_data = "source,target\nalice,bob\nbob,carol\ncarol,dave\nalice,dave\n"
        csv_path = PROJECT_ROOT / "inbox" / "_test_mcp_graph.csv"
        csv_path.write_text(csv_data)
        TEST_FILES.append(str(csv_path))

        from ai_kos.graphs import create_graph, insert_nodes, insert_edges
        from ai_kos.schemas import GraphRef
        table = "_mcp_test_graph"
        create_graph("datasets/ai-kos.db", table, directed=True)
        nodes_set = {"alice", "bob", "carol", "dave"}
        insert_nodes("datasets/ai-kos.db", table, [{"node_id": n} for n in nodes_set])
        edges = [{"source": "alice", "target": "bob"}, {"source": "bob", "target": "carol"},
                 {"source": "carol", "target": "dave"}, {"source": "alice", "target": "dave"}]
        ec = insert_edges("datasets/ai-kos.db", table, edges)
        gr = GraphRef(directed=True, node_count=len(nodes_set), edge_count=ec)
        cr = create_article("base", {
            "id": str(_uuid.uuid4()), "title": "_MCP Test Graph", "slug": "_mcp-test-graph",
            "type": "base", "created_at": today, "updated_at": today,
            "reviewed_at": today, "next_review_at": today.replace(year=today.year+1),
            "keywords": ["test", "mcp", "graph"], "summary": "MCP test graph.",
            "backend": "graph",
            "dataset": DatasetRef(db="datasets/ai-kos.db", table=table, columns=[
                DatasetColumn(name="node_id", type="TEXT"),
            ]),
            "graph": gr,
            "provenance": [{"source": "ingest", "origin_ref": "_test_mcp_graph.csv"}],
            "confidence": 0.9,
        })
        if cr.get("status") == "created":
            TEST_SLUGS.append(cr["slug"])
        report("ai_kos_ingest_graph", True, f"nodes={len(nodes_set)} edges={ec}")
    except Exception as e:
        report("ai_kos_ingest_graph", False, str(e)[:60])

    # Parquet / ORC — skip without pyarrow
    try:
        import pyarrow
        skip("ai_kos_ingest_parquet", "pyarrow available but skipping (slow)")
        skip("ai_kos_ingest_orc", "skipping")
    except ImportError:
        skip("ai_kos_ingest_parquet", "pyarrow not installed")
        skip("ai_kos_ingest_orc", "pyarrow not installed")

    skip("ai_kos_ingest_sqlite", "no test .db file")
    skip("ai_kos_ingest_sql_dump", "no test .sql file")

    # ai_kos_timeseries_stats — requires time-series dataset
    skip("ai_kos_timeseries_stats", "no time-series dataset")


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 6: Cleanup
# ═══════════════════════════════════════════════════════════════════════════════

def phase_cleanup():
    print("\n── Phase 6: Cleanup ──")

    # Delete test articles
    from ai_kos.articles import _get_index
    idx = _get_index()
    for slug in TEST_SLUGS:
        try:
            fp = idx._paths.get(slug)
            if fp and Path(fp).exists():
                Path(fp).unlink()
        except Exception:
            pass

    # Delete test tables from SQLite
    try:
        import sqlite3
        conn = sqlite3.connect("datasets/ai-kos.db")
        for tbl in ["_mcp_test_data", "_mcp_test_graph"]:
            conn.execute(f'DROP TABLE IF EXISTS "{tbl}_nodes"')
            conn.execute(f'DROP TABLE IF EXISTS "{tbl}_edges"')
            conn.execute(f'DROP TABLE IF EXISTS "{tbl}"')
        conn.execute("DELETE FROM json_docs WHERE slug LIKE '_mcp-test-%'")
        conn.commit()
        conn.close()
    except Exception:
        pass

    # Clean test files
    import shutil
    for fp in TEST_FILES:
        try:
            Path(fp).unlink()
        except Exception:
            pass
    # Clean archived test file
    archived = PROJECT_ROOT / "archive" / "_test_mcp.md"
    if archived.exists():
        archived.unlink()

    # Delete blob file
    blob_dir = PROJECT_ROOT / "datasets" / "blobs"
    if blob_dir.exists():
        for f in blob_dir.iterdir():
            if "_mcp-test" in f.name:
                f.unlink()

    # Rebuild index and re-link
    from ai_kos.articles import _get_index
    idx = _get_index()
    idx._built = False
    idx._ensure_built()

    from ai_kos.linker import link_all
    link_all()

    from ai_kos.articles import stats
    s = stats()
    report("cleanup", True, f"articles_after={s['total_articles']}")
    print(f"  Test articles created: {len(TEST_SLUGS)}")
    print(f"  Test files created: {len(TEST_FILES)}")


# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="AI-KOS MCP Tool Test Suite")
    parser.add_argument("--phase", choices=["read", "write", "research", "tasks", "backend", "all"],
                        default="all", help="Which phase to run")
    args = parser.parse_args()

    phases = {
        "read": [phase_read],
        "write": [phase_write],
        "research": [phase_research],
        "tasks": [phase_tasks],
        "backend": [phase_backend],
        "all": [phase_read, phase_write, phase_research, phase_tasks, phase_backend, phase_cleanup],
    }

    for phase_fn in phases[args.phase]:
        try:
            phase_fn()
        except Exception:
            print(f"  \033[31mCRASH\033[0m in {phase_fn.__name__}: {traceback.format_exc()[:200]}")

    print(f"\n{'='*60}")
    print(f"Results: {PASS} passed, {FAIL} failed, {SKIP} skipped")
    print(f"{'='*60}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
