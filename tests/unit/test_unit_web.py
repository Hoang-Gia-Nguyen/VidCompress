import pytest
import sqlite3
import sys
import os
from unittest.mock import patch, MagicMock
from pathlib import Path

@pytest.fixture
def clean_web_module():
    """Ensure app.web is re-imported for each test to apply environment changes."""
    if 'app.web' in sys.modules:
        del sys.modules['app.web']
    yield
    if 'app.web' in sys.modules:
        del sys.modules['app.web']

@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test_job_repo.db"
    # Create the table so the app doesn't try to create it
    conn = sqlite3.connect(str(db_path))
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE,
            size INTEGER,
            mtime REAL,
            status TEXT NOT NULL,
            error TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    conn.close()
    return db_path

@pytest.fixture
def client(test_db, clean_web_module, monkeypatch):
    monkeypatch.setenv("JOB_REPO_DB", str(test_db))
    monkeypatch.setenv("FLASK_ENV", "testing")
    from app.web import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_empty(client):
    with patch("app.web.render_template_string") as mock_render:
        mock_render.return_value = "OK"
        response = client.get('/')
        assert response.status_code == 200
        args, kwargs = mock_render.call_args
        assert len(kwargs['jobs']) == 0

def test_index_with_jobs(client, test_db):
    conn = sqlite3.connect(str(test_db))
    conn.execute('INSERT INTO jobs (path, status) VALUES (?, ?)', ("test.mp4", "pending"))
    conn.commit()
    conn.close()
    
    with patch("app.web.render_template_string") as mock_render:
        mock_render.return_value = "OK"
        response = client.get('/')
        assert response.status_code == 200
        args, kwargs = mock_render.call_args
        assert len(kwargs['jobs']) == 1
        assert kwargs['jobs'][0]['path'] == "test.mp4"

@patch("app.web.Path.touch")
def test_trigger_all(mock_touch, client):
    response = client.post('/trigger/all')
    assert response.status_code == 302
    assert response.headers['Location'] == '/'
    mock_touch.assert_called()

@patch("app.web.Path.touch")
def test_trigger_one(mock_touch, client):
    response = client.post('/trigger/one', data={'path': '/mnt/media/movie.mkv'})
    assert response.status_code == 302
    assert response.headers['Location'] == '/'
    mock_touch.assert_called()
