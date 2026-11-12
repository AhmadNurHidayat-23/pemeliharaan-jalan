import csv
import io
import secrets
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from app import create_app
from app.models import today
from core.db import connect
from core.security import add_user, digest

def day(offset=0):
    return (date.fromisoformat(today()) + timedelta(days=offset)).isoformat()

@pytest.fixture
def env(tmp_path):
    app = create_app({'INSTANCE_DIR': str(tmp_path)})
    db = connect(tmp_path)
    password = secrets.token_urlsafe(20)
    for username, role in [('admin', 'Admin'), ('petugas', 'Petugas')]:
        add_user(db, username, username + ' pengujian', role, password)
    db.close()
    clients = {}
    for username in ('admin', 'petugas'):
        client = TestClient(app)
        response = client.post('/api/login', json={'username': username, 'password': password})
        assert response.status_code == 200
        clients[username] = (client, {'X-CSRF-Token': response.json()['csrf']})
    admin, headers = clients['admin']
    admin.post('/api/regions', json={'name': 'Wilayah Uji'}, headers=headers)
    admin.post('/api/roads', json=road(), headers=headers)
    yield app, clients, tmp_path
    for client, _ in clients.values():
        client.close()

def road(**extra):
    return {'code': 'JL-UJI-01', 'name': 'Ruas Pengujian', 'region_id': 1, 'length_m': 1500, 'traffic': 5, **extra}

def job(**extra):
    return {'road_id': 1, 'name': 'Pemeliharaan Pengujian', 'starts_on': day(-3), 'target_on': day(-1), **extra}

def test_crud_roads_regions_archive_restore(env):
    _, c, _ = env
    a, h = c['admin']
    assert a.put('/api/roads/1', json=road(name='Ruas Diubah', length_m=2000), headers=h).status_code == 200
    assert a.get('/api/state').json()['roads'][0]['length_m'] == 2000
    assert a.post('/api/regions', json={'name': 'Kosong'}, headers=h).status_code == 200
    assert a.put('/api/regions/2', json={'name': 'Diubah'}, headers=h).status_code == 200
    assert a.request('DELETE', '/api/regions/2', json={}, headers=h).status_code == 200
    assert a.request('DELETE', '/api/regions/1', json={}, headers=h).status_code == 409
    assert a.request('DELETE', '/api/roads/1', json={}, headers=h).status_code == 200
    assert a.get('/api/state').json()['roads'] == []
    assert len(a.get('/api/state?archived=1').json()['roads']) == 1
    assert a.post('/api/roads/1/restore', json={}, headers=h).status_code == 200

def test_inspection_priority_backdating_and_filters(env):
    _, c, _ = env
    s, h = c['petugas']
    assert s.get('/api/state').json()['roads'][0]['priority'] is None
    assert s.post('/api/roads/1/inspections', json={'inspected_on': day(), 'condition': 'Rusak', 'note': 'Data inspeksi uji'}, headers=h).status_code == 200
    assert s.post('/api/roads/1/inspections', json={'inspected_on': day(-1), 'condition': 'Baik', 'note': 'Catatan lebih lama'}, headers=h).status_code == 200
    value = s.get('/api/state?q=pengujian&region_id=1&condition=Rusak&priority_label=Tinggi').json()
    assert len(value['roads']) == 1 and value['roads'][0]['priority'] == 100
    assert value['roads'][0]['condition'] == 'Rusak' and value['summary']['high'] == 1
    assert s.get('/api/state?condition=Baik').json()['roads'] == []
    history = s.get('/api/roads/1/inspections').json()
    assert len(history) == 2 and history[0]['inspected_on'] == day()
    assert s.post('/api/roads/1/inspections', json={'inspected_on': day(1), 'condition': 'Baik', 'note': 'Belum terjadi'}, headers=h).status_code == 400

def test_schedule_progress_late_and_condition_remains_inspected(env):
    _, c, _ = env
    a, ah = c['admin']
    s, sh = c['petugas']
    a.post('/api/roads/1/inspections', json={'inspected_on': day(), 'condition': 'Rusak', 'note': 'Inspeksi uji'}, headers=ah)
    assert a.post('/api/jobs', json=job(), headers=ah).status_code == 200
    assert a.put('/api/jobs/1', json=job(name='Pekerjaan Diubah'), headers=ah).status_code == 200
    assert a.get('/api/state').json()['summary']['late'] == 1
    assert a.get('/api/state').json()['jobs'][0]['last_report'] is None
    for percent in [50, 100]:
        assert s.post('/api/jobs/1/progress', json={'recorded_on': day(), 'percent': percent, 'note': 'Laporan progres uji'}, headers=sh).status_code == 200
    assert s.post('/api/jobs/1/progress', json={'recorded_on': day(-1), 'percent': 30, 'note': 'Laporan lama'}, headers=sh).status_code == 200
    state = a.get('/api/state').json()
    assert state['jobs'][0]['percent'] == 100 and state['jobs'][0]['status'] == 'Selesai'
    assert state['jobs'][0]['last_report'] == day()
    assert state['summary']['late'] == 0 and state['roads'][0]['condition'] == 'Rusak'
    assert len(a.get('/api/jobs/1/progress').json()) == 3
    assert a.put('/api/jobs/1', json=job(starts_on=day(1), target_on=day(2)), headers=ah).status_code == 400

def test_cancellation_permissions_and_retained_history(env):
    _, c, _ = env
    a, ah = c['admin']
    s, sh = c['petugas']
    a.post('/api/jobs', json=job(), headers=ah)
    assert s.post('/api/jobs', json=job(), headers=sh).status_code == 403
    assert s.post('/api/jobs/1/cancellation', json={'canceled': True}, headers=sh).status_code == 403
    assert a.post('/api/jobs/1/cancellation', json={'canceled': True}, headers=ah).status_code == 200
    assert s.post('/api/jobs/1/progress', json={'recorded_on': day(), 'percent': 20, 'note': 'Uji'}, headers=sh).status_code == 400
    assert a.post('/api/jobs/1/cancellation', json={'canceled': False}, headers=ah).status_code == 200
    assert s.post('/api/jobs/1/progress', json={'recorded_on': day(), 'percent': 20, 'note': 'Uji'}, headers=sh).status_code == 200

def test_validation_and_unique_codes(env):
    _, c, _ = env
    a, h = c['admin']
    for values in [{'length_m': 0}, {'traffic': 6}, {'traffic': True}, {'region_id': 999}, {'name': ''}]:
        assert a.post('/api/roads', json=road(code='BARU', **values), headers=h).status_code in (400, 404)
    assert a.post('/api/roads', json=road(code='jl-uji-01'), headers=h).status_code == 409
    assert a.post('/api/jobs', json=job(target_on=day(-5)), headers=h).status_code == 400
    a.post('/api/jobs', json=job(), headers=h)
    for values in [{'percent': 101}, {'percent': -1}, {'recorded_on': day(-5)}, {'recorded_on': day(1)}]:
        assert a.post('/api/jobs/1/progress', json={'recorded_on': day(), 'percent': 1, 'note': 'Uji', **values}, headers=h).status_code == 400

def test_auth_csrf_origin_rate_limit_and_payload_size(env):
    app, c, _ = env
    anon = TestClient(app)
    a, h = c['admin']
    assert anon.get('/api/state').status_code == 401
    assert a.post('/api/regions', json={'name': 'Tanpa token'}).status_code == 403
    assert a.post('/api/regions', json={'name': 'Asal lain'}, headers={**h, 'Origin': 'https://lain.example'}).status_code == 403
    assert a.post('/api/regions', content=b'x' * 70000, headers={**h, 'Content-Type': 'application/json'}).status_code == 413
    for _ in range(6):
        assert anon.post('/api/login', json={'username': 'tidakada', 'password': secrets.token_hex(10)}).status_code == 401
    assert anon.post('/api/login', json={'username': 'tidakada', 'password': secrets.token_hex(10)}).status_code == 429
    assert a.post('/api/logout', json={}, headers=h).status_code == 200
    assert a.get('/api/state').status_code == 401

def test_export_and_persistence_integrity(env):
    _, c, folder = env
    a, h = c['admin']
    a.post('/api/jobs', json=job(), headers=h)
    response = a.get('/api/export')
    rows = list(csv.reader(io.StringIO(response.content.decode('utf-8-sig'))))
    assert rows[0][0] == 'Kode ruas' and rows[1][0] == 'JL-UJI-01' and rows[1][-1] == 'Terjadwal'
    restarted = TestClient(create_app({'INSTANCE_DIR': str(folder)}))
    restarted.cookies.update(a.cookies)
    assert restarted.get('/api/state').json()['roads'][0]['code'] == 'JL-UJI-01'
    db = connect(folder)
    assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert db.execute('PRAGMA foreign_key_check').fetchall() == []
    token = a.cookies.get('pemeliharaan_jalan_session')
    assert db.execute('SELECT token FROM sessions WHERE token=?', (token,)).fetchone() is None
    assert db.execute('SELECT token FROM sessions WHERE token=?', (digest(token),)).fetchone() is not None
    db.close()
