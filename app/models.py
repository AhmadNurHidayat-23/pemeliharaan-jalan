from datetime import datetime, timezone, timedelta
from core.validate import require_row

def today():
    return datetime.now(timezone(timedelta(hours=7))).date().isoformat()

def find(db, kind, id):
    return require_row(db, kind, id, ('regions', 'roads', 'inspections', 'jobs', 'progress'))

def roads(db, filters):
    rows = [dict(r) for r in db.execute('''SELECT r.*,g.name region,i.condition,i.inspected_on FROM roads r
        JOIN regions g ON g.id=r.region_id LEFT JOIN inspections i ON i.id=(SELECT id FROM inspections
        WHERE road_id=r.id ORDER BY inspected_on DESC,id DESC LIMIT 1) WHERE r.archived=? ORDER BY r.name''',
        (1 if filters.get('archived') == '1' else 0,))]
    output = []
    for r in rows:
        score = {'Baik': 0, 'Sedang': 40, 'Rusak': 80}.get(r['condition'])
        r['priority'] = score + r['traffic'] * 4 if score is not None else None
        r['priority_label'] = 'Belum dinilai' if score is None else 'Tinggi' if r['priority'] >= 80 else 'Sedang' if r['priority'] >= 40 else 'Rendah'
        q = str(filters.get('q', '')).lower().strip()[:120]
        if q and q not in r['name'].lower() and q not in r['code'].lower():
            continue
        if any(filters.get(key) and str(r[key]) != str(filters[key]) for key in ('region_id', 'condition', 'priority_label')):
            continue
        output.append(r)
    return sorted(output, key=lambda r: (-(r['priority'] or -1), r['code']))

def jobs(db, road_ids):
    rows = db.execute('''SELECT j.*,r.name road,r.code,
        coalesce((SELECT percent FROM progress WHERE job_id=j.id ORDER BY recorded_on DESC,id DESC LIMIT 1),0) percent,
        (SELECT recorded_on FROM progress WHERE job_id=j.id ORDER BY recorded_on DESC,id DESC LIMIT 1) last_report
        FROM jobs j JOIN roads r ON r.id=j.road_id ORDER BY j.target_on,j.id''').fetchall()
    output = []
    for row in rows:
        if row['road_id'] not in road_ids:
            continue
        j = dict(row)
        j['status'] = 'Dibatalkan' if j['canceled'] else 'Selesai' if j['percent'] == 100 else 'Berjalan' if j['percent'] else 'Terjadwal'
        j['late'] = not j['canceled'] and j['percent'] < 100 and j['target_on'] < today()
        output.append(j)
    return output

def history(db, id):
    find(db, 'roads', id)
    return [dict(r) for r in db.execute('''SELECT i.*,u.name actor FROM inspections i JOIN users u ON u.id=i.actor_id
        WHERE road_id=? ORDER BY inspected_on DESC,i.id DESC''', (id,))]

def progress_history(db, id):
    find(db, 'jobs', id)
    return [dict(r) for r in db.execute('''SELECT p.*,u.name actor FROM progress p JOIN users u ON u.id=p.actor_id
        WHERE job_id=? ORDER BY recorded_on DESC,p.id DESC''', (id,))]

def state(db, filters):
    rows = roads(db, filters)
    work = jobs(db, {r['id'] for r in rows})
    return {'roads': rows, 'jobs': work, 'regions': [dict(r) for r in db.execute('SELECT * FROM regions ORDER BY name')],
            'allRoads': [dict(r) for r in db.execute('SELECT id,name,code FROM roads WHERE archived=0 ORDER BY name')],
            'summary': {'total': len(rows), 'damaged': sum(r['condition'] == 'Rusak' for r in rows),
                        'high': sum(r['priority_label'] == 'Tinggi' for r in rows), 'late': sum(j['late'] for j in work)}}
