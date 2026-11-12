import hashlib
import hmac
import re
import secrets
import time

class Problem(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def password_hash(password):
    if not isinstance(password, str) or not 12 <= len(password) <= 200:
        raise Problem('Kata sandi harus 12–200 karakter.')
    salt = secrets.token_hex(16)
    value = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 600000).hex()
    return 'pbkdf2_sha256$600000$' + salt + '$' + value

def verify_password(password, encoded):
    try:
        algorithm, rounds, salt, expected = encoded.split('$')
        if algorithm != 'pbkdf2_sha256' or not isinstance(password, str) or len(password) > 200:
            return False
        value = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(rounds)).hex()
        return hmac.compare_digest(value, expected)
    except (ValueError, TypeError, AttributeError):
        return False

DUMMY_HASH = password_hash(secrets.token_urlsafe(24))

def add_user(db, username, name, role, password):
    if not isinstance(username, str) or not re.fullmatch(r'[a-zA-Z0-9._-]{1,80}', username) or not name.strip() or len(name) > 80 or role not in ('Admin', 'Petugas'):
        raise Problem('Nama pengguna, nama tampilan atau peran tidak valid.')
    with db:
        db.execute('INSERT INTO users(username,name,role,password) VALUES(?,?,?,?)', (username.lower(), name.strip(), role, password_hash(password)))

def get_session(db, token):
    if not token or not re.fullmatch(r'[a-f0-9]{64}', token):
        return None
    row = db.execute('''SELECT s.*,u.id,u.username,u.name,u.role FROM sessions s JOIN users u ON u.id=s.user_id
        WHERE token=? AND expires>?''', (digest(token), int(time.time()))).fetchone()
    return dict(row) if row else None

def authenticate(db, username, password):
    username, now = str(username).strip().lower()[:80], int(time.time())
    key = digest(username)
    attempt = db.execute('SELECT * FROM attempts WHERE key=?', (key,)).fetchone()
    if attempt and attempt['until'] > now and attempt['count'] >= 6:
        raise Problem('Terlalu banyak percobaan. Coba lagi dalam 15 menit.', 429)
    user = db.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
    valid = verify_password(password, user['password'] if user else DUMMY_HASH)
    if not user or not valid:
        with db:
            db.execute('''INSERT INTO attempts(key,count,until) VALUES(?,1,?) ON CONFLICT(key) DO UPDATE SET
                count=CASE WHEN until<=? THEN 1 ELSE count+1 END,until=CASE WHEN until<=? THEN ? ELSE until END''',
                       (key, now + 900, now, now, now + 900))
        raise Problem('Nama pengguna atau kata sandi tidak cocok.', 401)
    return user['id'], key

def new_session(db, user_id, old=None, attempt_key=None):
    token, csrf, now = secrets.token_hex(32), secrets.token_hex(32), int(time.time())
    with db:
        db.execute('DELETE FROM sessions WHERE expires<=?', (now,))
        if old:
            db.execute('DELETE FROM sessions WHERE token=?', (old['token'],))
        if attempt_key:
            db.execute('DELETE FROM attempts WHERE key=?', (attempt_key,))
        db.execute('INSERT INTO sessions(token,user_id,csrf,expires) VALUES(?,?,?,?)', (digest(token), user_id, csrf, now + 28800))
    return token, csrf
