from core.security import Problem
from core.validate import text, integer, choice, date
from core.db import transaction
from .models import find, today

def region(db, data, id=None):
    name = text(data.get('name'), 'Nama wilayah', 80)
    if id:
        find(db, 'regions', id)
    with db:
        if id:
            db.execute('UPDATE regions SET name=? WHERE id=?', (name, id))
        else:
            db.execute('INSERT INTO regions(name) VALUES(?)', (name,))

def road(db, data, id=None):
    if id and find(db, 'roads', id)['archived']:
        raise Problem('Pulihkan ruas jalan terlebih dahulu.')
    region_id = integer(data.get('region_id'), 'Wilayah', 1)
    find(db, 'regions', region_id)
    values = (text(data.get('code'), 'Kode ruas', 40).upper(), text(data.get('name'), 'Nama ruas'), region_id,
              integer(data.get('length_m'), 'Panjang (meter)', 1, 1000000), integer(data.get('traffic'), 'Tingkat lalu lintas', 1, 5))
    with db:
        if id:
            db.execute('UPDATE roads SET code=?,name=?,region_id=?,length_m=?,traffic=? WHERE id=?', (*values, id))
        else:
            db.execute('INSERT INTO roads(code,name,region_id,length_m,traffic) VALUES(?,?,?,?,?)', values)

def inspect(db, user, id, data):
    when = date(data.get('inspected_on'))
    if when > today():
        raise Problem('Tanggal inspeksi tidak boleh di masa depan.')
    condition = choice(data.get('condition'), ('Baik', 'Sedang', 'Rusak'), 'Kondisi')
    note = text(data.get('note'), 'Catatan inspeksi', 1000)
    with transaction(db):
        if find(db, 'roads', id)['archived']:
            raise Problem('Ruas jalan dalam arsip.')
        db.execute('INSERT INTO inspections(road_id,inspected_on,condition,note,actor_id) VALUES(?,?,?,?,?)', (id, when, condition, note, user['id']))

def job(db, data, id=None):
    road_id = integer(data.get('road_id'), 'Ruas jalan', 1)
    name, start, target = text(data.get('name'), 'Nama pemeliharaan'), date(data.get('starts_on')), date(data.get('target_on'))
    if target < start:
        raise Problem('Target selesai harus pada atau setelah tanggal mulai.')
    with transaction(db):
        if find(db, 'roads', road_id)['archived']:
            raise Problem('Ruas jalan dalam arsip.')
        if id:
            old = find(db, 'jobs', id)
            earliest = db.execute('SELECT min(recorded_on) FROM progress WHERE job_id=?', (id,)).fetchone()[0]
            if earliest and (old['road_id'] != road_id or start > earliest):
                raise Problem('Jadwal memiliki progres; ruas tidak boleh dipindahkan atau tanggal mulai melewati laporan yang sudah ada.')
            db.execute('UPDATE jobs SET road_id=?,name=?,starts_on=?,target_on=? WHERE id=?', (road_id, name, start, target, id))
        else:
            db.execute('INSERT INTO jobs(road_id,name,starts_on,target_on) VALUES(?,?,?,?)', (road_id, name, start, target))

def progress(db, user, id, data):
    when, percent = date(data.get('recorded_on')), integer(data.get('percent'), 'Progres (%)', 0, 100)
    note = text(data.get('note'), 'Catatan progres', 1000)
    with transaction(db):
        item = find(db, 'jobs', id)
        if item['canceled'] or find(db, 'roads', item['road_id'])['archived']:
            raise Problem('Jadwal dibatalkan atau ruas diarsipkan.')
        if when < item['starts_on'] or when > today():
            raise Problem('Tanggal laporan harus pada/setelah mulai pekerjaan dan tidak di masa depan.')
        db.execute('INSERT INTO progress(job_id,recorded_on,percent,note,actor_id) VALUES(?,?,?,?,?)', (id, when, percent, note, user['id']))

def remove(db, kind, id):
    find(db, kind, id)
    with db:
        if kind == 'roads':
            db.execute('UPDATE roads SET archived=1 WHERE id=?', (id,))
        elif kind == 'regions':
            db.execute('DELETE FROM regions WHERE id=?', (id,))
        else:
            raise Problem('Tindakan tidak tersedia.')
