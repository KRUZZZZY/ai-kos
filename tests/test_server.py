"""Tests for ai_kos.server — Flask dashboard routes."""
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai_kos.server import app


@pytest.fixture
def client(monkeypatch):
    """Test client with temp knowledge directory to isolate from real data."""
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setenv("AI_KOS_KNOWLEDGE_DIR", tmpdir)
    # Also patch the server's imports
    import ai_kos.config
    ai_kos.config._config = None  # force reload

    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

    # Cleanup
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


class TestDashboard:
    def test_dashboard_loads(self, client):
        resp = client.get('/')
        assert resp.status_code == 200
        assert b'Dashboard' in resp.data


class TestArticles:
    def test_articles_list_loads(self, client):
        resp = client.get('/articles')
        assert resp.status_code == 200

    def test_article_view_missing(self, client):
        resp = client.get('/articles/nonexistent-slug-xyz')
        assert resp.status_code == 404


class TestTasks:
    def test_tasks_page_loads(self, client):
        resp = client.get('/tasks')
        assert resp.status_code == 200

    def test_tasks_create_and_list(self, client):
        resp = client.post('/tasks', data={
            'action': 'create',
            'title': 'Test task',
            'description': 'Testing',
            'priority': '0',
            'urgency': 'yellow',
            'tags': 'unit-test, demo',
            'article_slugs': 'test-article-1, test-article-2',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Test task' in resp.data
        assert b'test-article-1' in resp.data

    def test_tasks_create_empty_title(self, client):
        resp = client.post('/tasks', data={
            'action': 'create',
            'title': '   ',
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_tasks_advance_and_block(self, client):
        # Create a task and advance it through the workflow
        from ai_kos.tasks import TaskManager
        tm = TaskManager()
        task = tm.create('Advance test task', article_slugs=['test-article'])
        task_id = task.id
        resp = client.post('/tasks', data={
            'action': 'advance',
            'task_id': str(task_id),
        }, follow_redirects=True)
        assert resp.status_code == 200
        # Block it
        resp = client.post('/tasks', data={
            'action': 'block',
            'task_id': str(task_id),
        }, follow_redirects=True)
        assert resp.status_code == 200
        # Clean up
        tm.delete(task_id)

    def test_tasks_delete(self, client):
        from ai_kos.tasks import TaskManager
        tm = TaskManager()
        task = tm.create('Delete me test', article_slugs=['test-article'])
        task_id = task.id
        resp = client.post('/tasks', data={
            'action': 'delete',
            'task_id': str(task_id),
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert tm.get(task_id) is None


class TestGraph:
    def test_graph_page_loads(self, client):
        resp = client.get('/graph')
        assert resp.status_code == 200

    def test_graph_api(self, client):
        resp = client.get('/api/graph-data')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'nodes' in data
        assert 'edges' in data
        assert 'stats' in data


class TestFiles:
    def test_files_loads(self, client):
        resp = client.get('/files')
        assert resp.status_code == 200
        assert b'Files' in resp.data

    def test_files_inbox_tab(self, client):
        resp = client.get('/files?tab=inbox')
        assert resp.status_code == 200

    def test_inbox_redirect_still_works(self, client):
        resp = client.get('/inbox')
        assert resp.status_code == 200
