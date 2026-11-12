import re
from datetime import date as calendar_date
from .security import Problem

def text(value, label, maximum=120, required=True):
    if not isinstance(value, str) or len(value.strip()) > maximum or required and not value.strip():
        raise Problem(f'{label} wajib diisi dengan benar, maksimal {maximum} karakter.')
    return value.strip()

def integer(value, label, minimum=0, maximum=1000000000000):
    if isinstance(value, bool) or not re.fullmatch(r'-?\d+', str(value)) or not minimum <= int(value) <= maximum:
        raise Problem(f'{label} harus bilangan bulat antara {minimum} dan {maximum}.')
    return int(value)

def choice(value, options, label):
    if value not in options:
        raise Problem(f'{label} tidak valid.')
    return value

def date(value):
    try:
        if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            raise ValueError()
        calendar_date.fromisoformat(value)
        return value
    except ValueError:
        raise Problem('Tanggal tidak valid.')

def require_row(db, table, id, allowed):
    if table not in allowed:
        raise Problem('Jenis data tidak valid.')
    row = db.execute(f'SELECT * FROM {table} WHERE id=?', (id,)).fetchone()
    if not row:
        raise Problem('Data tidak ditemukan.', 404)
    return dict(row)
