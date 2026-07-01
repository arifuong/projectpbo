-- ============================================================
-- Schema Database untuk Sistem Validasi Kesesuaian RPS dan BAP
-- Sesuai PRD Section 7 - Database Schema (MySQL)
-- ============================================================
-- Versi    : 2.0 (Single User, tanpa tabel users)
-- Database : MySQL 8.0+
-- ============================================================

-- Membuat database jika belum ada
CREATE DATABASE IF NOT EXISTS validasi_rps_bap
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_general_ci;

-- Menggunakan database yang telah dibuat
USE validasi_rps_bap;

-- ============================================================
-- Tabel: courses (Mata Kuliah)
-- Sesuai PRD Section 7.2
-- Tabel pendukung yang menyimpan data mata kuliah.
-- Setiap mata kuliah diidentifikasi oleh kode unik (course_code).
-- Kolom lecturer_id DIHAPUS sesuai revisi PRD (single user).
-- ============================================================
CREATE TABLE IF NOT EXISTS courses (
    -- Primary key dengan auto increment
    course_id       INT AUTO_INCREMENT PRIMARY KEY,
    -- Kode mata kuliah harus unik (contoh: IF101, TI202)
    course_code     VARCHAR(20)  NOT NULL UNIQUE,
    -- Nama lengkap mata kuliah
    course_name     VARCHAR(150) NOT NULL,
    -- Semester perkuliahan (contoh: Ganjil, Genap)
    semester        VARCHAR(20)  NOT NULL,
    -- Tahun akademik dalam format YYYY/YYYY (contoh: 2024/2025)
    academic_year   VARCHAR(9)   NOT NULL,
    -- Timestamp pencatatan data
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- Tabel: rps (Rencana Pembelajaran Semester)
-- Sesuai PRD Section 7.3
-- Menyimpan data Pokok Bahasan RPS hasil ekstraksi PDF.
-- Setiap baris merepresentasikan satu pertemuan.
-- Constraint UNIQUE memastikan nomor pertemuan tidak duplikat
-- dalam satu mata kuliah (sesuai PRD BR-01).
-- ============================================================
CREATE TABLE IF NOT EXISTS rps (
    -- Primary key dengan auto increment
    rps_id          INT AUTO_INCREMENT PRIMARY KEY,
    -- Foreign key ke tabel courses
    course_id       INT          NOT NULL,
    -- Nomor pertemuan (1, 2, 3, ..., N)
    meeting_number  INT          NOT NULL,
    -- Pokok bahasan/topik utama pertemuan
    topic           VARCHAR(255) NOT NULL,
    -- Sub pokok bahasan (opsional, bisa berisi detail topik)
    sub_topic       TEXT,
    -- Hasil pembersihan teks dari topik (untuk keyword matching)
    cleaned_topic   TEXT,
    -- Nama file PDF sumber data RPS
    source_file     VARCHAR(255),
    -- Timestamp pencatatan dan pembaruan data
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    -- Relasi ke tabel courses
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    -- Memastikan nomor pertemuan unik per mata kuliah (BR-01)
    UNIQUE KEY uq_course_meeting (course_id, meeting_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- Tabel: bap (Berita Acara Perkuliahan)
-- Sesuai PRD Section 7.4
-- Menyimpan data materi yang benar-benar diajarkan
-- pada setiap pertemuan perkuliahan.
-- Kolom lecturer_id DIHAPUS sesuai revisi PRD (single user).
-- Constraint UNIQUE memastikan nomor pertemuan tidak duplikat
-- dalam satu mata kuliah (sesuai PRD BR-02).
-- ============================================================
CREATE TABLE IF NOT EXISTS bap (
    -- Primary key dengan auto increment
    bap_id            INT AUTO_INCREMENT PRIMARY KEY,
    -- Foreign key ke tabel courses
    course_id         INT    NOT NULL,
    -- Nomor pertemuan (harus sesuai dengan yang ada di RPS)
    meeting_number    INT    NOT NULL,
    -- Tanggal pelaksanaan perkuliahan
    meeting_date      DATE   NOT NULL,
    -- Materi yang benar-benar diajarkan pada pertemuan tersebut
    material_taught   TEXT   NOT NULL,
    -- Hasil pembersihan teks dari materi (untuk keyword matching)
    cleaned_material  TEXT,
    -- Timestamp pencatatan dan pembaruan data
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    -- Relasi ke tabel courses
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    -- Memastikan nomor pertemuan unik per mata kuliah (BR-02)
    UNIQUE KEY uq_course_meeting_bap (course_id, meeting_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- Tabel: validation_results (Hasil Validasi)
-- Sesuai PRD Section 7.5
-- Menyimpan hasil proses validasi kesesuaian antara
-- data RPS dan BAP untuk setiap pertemuan.
-- Status menggunakan ENUM sesuai Status Lifecycle PRD Section 6.
-- ============================================================
CREATE TABLE IF NOT EXISTS validation_results (
    -- Primary key dengan auto increment
    validation_id     INT AUTO_INCREMENT PRIMARY KEY,
    -- Foreign key ke tabel courses
    course_id         INT     NOT NULL,
    -- Foreign key ke tabel rps (nullable, untuk status TIDAK_DITEMUKAN)
    rps_id            INT     NULL,
    -- Foreign key ke tabel bap (nullable, untuk status PENDING)
    bap_id            INT     NULL,
    -- Nomor pertemuan yang divalidasi
    meeting_number    INT     NOT NULL,
    -- Skor kemiripan hasil keyword matching (0.00 - 100.00)
    similarity_score  DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    -- Status hasil validasi sesuai PRD Section 6
    status            ENUM('SESUAI', 'TIDAK_SESUAI', 'TIDAK_DITEMUKAN', 'PENDING')
                      NOT NULL DEFAULT 'PENDING',
    -- Catatan tambahan (contoh: "Materi cocok dengan pertemuan ke-5")
    notes             TEXT,
    -- Timestamp proses validasi
    validated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Relasi ke tabel courses, rps, dan bap
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (rps_id) REFERENCES rps(rps_id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    FOREIGN KEY (bap_id) REFERENCES bap(bap_id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- Tabel: upload_history (Riwayat Unggahan)
-- Sesuai PRD Section 7.6
-- Mencatat seluruh aktivitas unggah file RPS (berhasil/gagal).
-- Kolom uploader_id DIHAPUS sesuai revisi PRD (single user).
-- Sesuai PRD BR-15: Semua aktivitas unggah harus tercatat.
-- ============================================================
CREATE TABLE IF NOT EXISTS upload_history (
    -- Primary key dengan auto increment
    upload_id       INT AUTO_INCREMENT PRIMARY KEY,
    -- Foreign key ke tabel courses
    course_id       INT          NOT NULL,
    -- Nama asli file yang diunggah
    file_name       VARCHAR(255) NOT NULL,
    -- Path penyimpanan file di server/lokal
    file_path       VARCHAR(255) NOT NULL,
    -- Ukuran file dalam kilobyte
    file_size_kb    INT,
    -- Status unggahan: SUCCESS atau FAILED
    upload_status   ENUM('SUCCESS', 'FAILED') NOT NULL,
    -- Pesan error jika unggahan gagal
    error_message   TEXT,
    -- Timestamp unggahan
    uploaded_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Relasi ke tabel courses
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- Indeks Tambahan untuk Optimasi Performa Query
-- ============================================================

-- Indeks untuk mempercepat pencarian RPS berdasarkan mata kuliah
CREATE INDEX idx_rps_course_id ON rps(course_id);

-- Indeks untuk mempercepat pencarian BAP berdasarkan mata kuliah
CREATE INDEX idx_bap_course_id ON bap(course_id);

-- Indeks untuk mempercepat pencarian hasil validasi berdasarkan mata kuliah
CREATE INDEX idx_validation_course_id ON validation_results(course_id);

-- Indeks untuk mempercepat pencarian hasil validasi berdasarkan status
CREATE INDEX idx_validation_status ON validation_results(status);

-- Indeks untuk mempercepat pencarian riwayat upload berdasarkan mata kuliah
CREATE INDEX idx_upload_course_id ON upload_history(course_id);

-- Indeks untuk mempercepat filter berdasarkan semester dan tahun akademik
CREATE INDEX idx_courses_semester ON courses(semester, academic_year);
