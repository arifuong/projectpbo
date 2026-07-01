# Sistem Validasi Kesesuaian RPS dan BAP

Aplikasi web Flask untuk memvalidasi kesesuaian materi RPS dengan realisasi BAP.

## Arsitektur

- Flask MVC
- Repository Pattern
- Service Layer
- OOP
- Dependency Injection
- MySQL
- Bootstrap 5, Jinja2, JavaScript, Fetch API

## Fitur Utama

- Dashboard ringkasan evaluasi
- Upload PDF RPS
- Ekstraksi pokok bahasan RPS
- CRUD RPS
- CRUD BAP
- Validasi kesesuaian RPS dan BAP
- Deteksi materi sesuai, tidak sesuai, tidak ditemukan, dan pending
- Export laporan PDF dan Excel
- Audit log upload history

## Mode Data

Project berjalan dalam mode satu pengguna dan satu data akademik aktif. Upload RPS baru mengganti data akademik aktif, tetapi riwayat upload tetap disimpan sebagai audit log.

## Business Rule Upload RPS Baru

1. Hapus hasil validasi.
2. Hapus BAP.
3. Hapus RPS.
4. Insert RPS baru.
5. Catat audit upload history.
6. Commit transaksi.

## Menjalankan Aplikasi

```powershell
python app.py
```

Default URL:

```text
http://127.0.0.1:5000
```

## Menjalankan Test

```powershell
pytest -q
```
