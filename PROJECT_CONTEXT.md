# Project Context

## Nama Project

Sistem Validasi Kesesuaian RPS dan BAP

## Status Implementasi

Project sudah berada pada tahap penyelesaian akhir. Modul utama sudah tersedia:

- Flask MVC
- Repository Pattern
- Service Layer
- Validator
- PDF Reader
- Text Cleaner
- Keyword Matcher
- Report Generator
- Dashboard
- Upload PDF
- CRUD RPS
- CRUD BAP
- Validation
- Export PDF
- Export Excel
- Unit Test

## Refactor Terbaru

Project sudah direfactor ke mode satu pengguna dan satu data akademik aktif.

Yang sudah dihapus dari source aktif:

- Tabel dan modul `courses`
- Field `course_id`
- `CourseRepository`
- `CourseService`
- `CourseController`
- Model `Course`

## Business Rule Kritis

Upload RPS baru harus mengganti data akademik aktif secara transaksional:

```text
Hapus Validation Result
Hapus BAP
Hapus RPS
Insert RPS baru
Catat Upload History
Commit
```

Upload History tetap disimpan sebagai audit log.

## Batasan Perubahan

Jangan mengubah tanpa alasan jelas:

- Repository Pattern
- Service Layer
- Business Rules
- Validator
- Keyword Matcher
- Database Connection
- Text Cleaner
