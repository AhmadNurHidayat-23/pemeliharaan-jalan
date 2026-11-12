# Pemeliharaan Jalan

Pemantauan kondisi dan perbaikan jalan. Prototipe portofolio independen, bukan aplikasi resmi pemerintah.

## Fitur utama

- CRUD ruas dan wilayah oleh Admin; inspeksi oleh Admin/Petugas dan riwayat berdasarkan tanggal pemeriksaan.
- Skor prioritas: bobot Baik 0, Sedang 40, Rusak 80 ditambah lalu lintas 1–5 × 4. Ruas tanpa inspeksi belum dinilai.
- Jadwal pemeliharaan, pembatalan/pemulihan, laporan progres berkala dan identifikasi lewat target.
- Pencarian, filter, arsip ruas dan laporan CSV. Kondisi jalan tidak otomatis dianggap baik saat progres pekerjaan selesai.

## Teknologi

Python 3.13, FastAPI, Jinja2, SQLite, HTML, CSS, JavaScript.

## Cara instalasi

~~~powershell
cd C:\laragon\www\pemeliharaan-jalan
& 'C:\laragon\bin\python\python-3.13\python.exe' -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m core.users --role Admin
.\.venv\Scripts\python.exe -m core.users --role Petugas
~~~

Gunakan lokasi python.exe terpasang bila Python belum berada di PATH. Kata sandi 12–200 karakter dimasukkan melalui prompt. Tidak ada akun bawaan.

Lokasi Python pada perintah instalasi mengikuti Laragon di komputer ini; sesuaikan bila instalasi Python berada di lokasi lain.

## Cara menjalankan

~~~powershell
.\.venv\Scripts\python.exe run.py
~~~

Buka http://127.0.0.1:5441. SQLite di instance/app.sqlite diinisialisasi otomatis dan aman diulang. APP_INSTANCE dapat mengubah folder data. Seluruh tanggal mengikuti WIB; inspeksi dan laporan progres tidak boleh di masa depan. Catatan lama dapat dimasukkan tanpa mengubah kondisi/progres yang bertanggal lebih baru. Set SECURE_COOKIE=1 saat memakai HTTPS.

Tes: .\.venv\Scripts\python.exe -m pytest.
