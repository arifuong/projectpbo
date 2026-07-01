# Changelog

## 2026-07-01

### Changed

- Refactor `TopicExtractor` agar mengambil hanya pokok bahasan utama dari cell `Materi Pembelajaran`.
- `PDFExtractionService` sekarang mempertahankan newline cell materi sebelum proses ekstraksi topik.
- Menambahkan unit test parser untuk kasus pertemuan 4/5 dan PDF RPS contoh 14 pertemuan.

### Fixed

- Pertemuan 4 tidak lagi diekstrak sebagai `Mencoba program pada buku referensi 2.`, tetapi sebagai `Praktikum Enkapsulasi`.
- Detail seperti numbering, bullet, fokus, latihan, contoh, submateri, referensi, dan newline tidak lagi masuk ke field topik utama.

### Verified

- `pytest tests\test_tahap3_extraction.py -q` menghasilkan `24 passed`.
- `pytest -q` menghasilkan `123 passed`.

## 2026-07-01

### Changed

- Menambahkan dokumentasi project root: `README.md`, `PROJECT_CONTEXT.md`, `task.md`, `walkthrough.md`, dan `CHANGELOG.md`.
- Mengganti akses controller ke atribut private service/repository dengan method publik service.
- Mengubah dashboard controller agar memakai `get_top_mismatched_meetings`.
- Memperbarui dashboard template agar memakai field `meeting_number`, `status`, `rps_topic`, dan distribusi status validasi.
- Memperbarui test agar sesuai mode satu pengguna dan satu data akademik aktif.

### Fixed

- Update BAP kini lewat `BAPManager.update_bap`, sehingga text cleaning tetap berjalan.
- Menghapus sisa exception dan pesan domain course yang sudah tidak digunakan.
- Menegaskan schema test agar `courses` dan `course_id` tidak kembali muncul.

### Verified

- `pytest -q` menghasilkan `119 passed`.
