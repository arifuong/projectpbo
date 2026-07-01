# Task

## Selesai

- Analisis struktur project lanjutan.
- Verifikasi dokumen konteks awal yang diminta belum ada di root project.
- Verifikasi test baseline: `119 passed`.
- Menghapus akses repository private dari controller web.
- Mengembalikan update BAP melalui `BAPManager.update_bap` agar `cleaned_material` tetap diperbarui.
- Mengganti sisa referensi dashboard lama dari data berbasis course ke data pertemuan/status.
- Membersihkan sisa exception dan pesan terkait course yang sudah tidak dipakai.
- Memperbarui test agar sesuai mode satu data akademik aktif.
- Menambahkan `README.md`, `PROJECT_CONTEXT.md`, `task.md`, `walkthrough.md`, dan `CHANGELOG.md`.
- Refactor parser topik utama RPS melalui `TopicExtractor`.
- Menambahkan unit test ekstraksi topik utama dari PDF RPS contoh.
- Memastikan pertemuan 4 tidak lagi tersimpan sebagai detail referensi, tetapi menjadi `Praktikum Enkapsulasi`.

## TODO

- Tidak ada TODO kode yang belum selesai dari analisis saat ini.
- Review manual UI di browser masih bisa dilakukan bila dibutuhkan.

## Bug Ditemukan dan Diperbaiki

- `BAPController.update_bap_meeting` sebelumnya bypass service layer dan tidak menjalankan text cleaning.
- `ValidationController` dan `ReportController` sebelumnya membaca repository lewat atribut private service.
- Dashboard template sebelumnya membaca field lama `course_name` dan `course_code`.
- Test lama masih mengizinkan string `courses` di schema meskipun tabel tersebut sudah dihapus.
- Parser sebelumnya mengambil seluruh isi/detail kolom `Materi Pembelajaran`, sehingga aktivitas seperti `Mencoba program pada buku referensi 2.` tersimpan sebagai pokok bahasan.

## Verifikasi

```text
pytest -q
123 passed
```
