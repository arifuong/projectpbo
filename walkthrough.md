# Walkthrough

## Alur Aplikasi

1. User membuka dashboard untuk melihat ringkasan RPS, BAP, upload, dan persentase kesesuaian.
2. User mengunggah PDF RPS melalui halaman Upload.
3. Sistem menyimpan file sementara, memvalidasi file PDF, lalu menyalin file ke folder `uploads/`.
4. `PDFExtractionService` mengekstrak data pokok bahasan dan sub pokok bahasan.
5. `TopicExtractor` memilih satu judul/pokok bahasan utama dari cell `Materi Pembelajaran`, membuang numbering, bullet, catatan fokus/latihan/contoh, referensi, submateri, dan newline.
6. User meninjau hasil ekstraksi dan menyimpan RPS.
7. `RPSManager.save_rps` membersihkan topik dan memanggil `RPSRepository.replace_all_rps`.
8. Repository menjalankan transaksi:
   - hapus `validation_results`
   - hapus `bap`
   - hapus `rps`
   - insert RPS baru
   - insert `upload_history`
9. User mengisi atau mengelola BAP.
10. User menjalankan validasi.
11. `Validator` membandingkan RPS dan BAP menggunakan `KeywordMatcher`.
12. Hasil validasi disimpan ulang secara batch.
13. User melihat laporan dan dapat mengekspor PDF atau Excel.

## Struktur Utama

- `app/controllers`: controller Flask MVC.
- `app/routes`: blueprint route.
- `app/templates`: tampilan Jinja2.
- `models`: entity/model domain.
- `repositories`: akses database.
- `services`: business logic.
- `utils`: helper PDF, text cleaning, logging, exception.
- `sql/schema.sql`: schema MySQL.
- `tests`: unit test dan web route test.

## Catatan Implementasi Terakhir

Controller web sekarang menggunakan method publik service untuk kebutuhan data tambahan:

- `BAPManager.get_total_rps_meetings`
- `Validator.get_compliance_stats`
- `Validator.get_rps_by_meeting`
- `Validator.get_bap_by_meeting`
- `FileUploadHandler.get_upload_history`

Update BAP kembali melewati `BAPManager.update_bap`, sehingga `cleaned_material` ikut diperbarui.

Parser RPS sekarang mempertahankan newline cell PDF saat ekstraksi, lalu `TopicExtractor`:

- memecah cell menjadi kandidat baris judul,
- membuang baris detail seperti contoh, latihan, referensi, dan submateri,
- memberi prioritas pada regex heading domain,
- memakai fallback regex untuk cell yang hanya berisi aktivitas/detail,
- mengembalikan satu topik utama per pertemuan.

Contoh hasil:

- Sebelum: `Mencoba program pada buku referensi 2.`
- Sesudah: `Praktikum Enkapsulasi`
