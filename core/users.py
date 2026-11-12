import argparse
import getpass
import os
import sqlite3
from .db import initialize, connect
from .security import add_user, Problem

def main():
    parser = argparse.ArgumentParser(description='Membuat akun lokal pengelola prototipe.')
    parser.add_argument('--role', choices=['Admin', 'Petugas'], required=True)
    args = parser.parse_args()
    folder = os.getenv('APP_INSTANCE', './instance')
    initialize(folder)
    username, name = input('Nama pengguna: ').strip(), input('Nama tampilan: ').strip()
    password = getpass.getpass('Kata sandi (12–200 karakter): ')
    if password != getpass.getpass('Ulangi kata sandi: '):
        raise SystemExit('Kata sandi tidak sama.')
    db = connect(folder)
    try:
        add_user(db, username, name, args.role, password)
    except (sqlite3.IntegrityError, Problem) as error:
        raise SystemExit('Akun gagal dibuat; nama sudah digunakan atau data tidak valid.') from error
    finally:
        db.close()
    print('Akun berhasil dibuat.')

if __name__ == '__main__':
    main()
