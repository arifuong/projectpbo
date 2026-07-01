-- ============================================================
-- Schema Database untuk Sistem Validasi Kesesuaian RPS dan BAP
-- Sesuai PRD mode satu pengguna dan satu data akademik aktif
-- Database : MySQL 8.0+
-- ============================================================

-- Membuat database jika belum ada
CREATE DATABASE IF NOT EXISTS validasi_rps_bap
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_general_ci;

-- Menggunakan database yang telah dibuat
USE validasi_rps_bap;

-- ============================================================
-- Tabel: rps (Rencana Pembelajaran Semester)
-- Menyimpan data Pokok Bahasan RPS hasil ekstraksi PDF.
-- Setiap baris merepresentasikan satu pertemuan.
-- ============================================================
CREATE TABLE IF NOT EXISTS rps (
    -- Primary key dengan auto increment (Target 2)
    rps_id          INT AUTO_INCREMENT PRIMARY KEY,
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
    -- Memastikan nomor pertemuan unik secara global (Target 2)
    UNIQUE KEY uq_meeting (meeting_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- Tabel: bap (Berita Acara Perkuliahan)
-- Menyimpan data materi yang benar-benar diajarkan
-- pada setiap pertemuan perkuliahan.
-- ============================================================
CREATE TABLE IF NOT EXISTS bap (
    -- Primary key dengan auto increment (Target 2)
    bap_id            INT AUTO_INCREMENT PRIMARY KEY,
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
    -- Memastikan nomor pertemuan unik secara global (Target 2)
    UNIQUE KEY uq_meeting (meeting_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- Tabel: validation_results (Hasil Validasi)
-- Menyimpan hasil proses validasi kesesuaian antara
-- data RPS dan BAP untuk setiap pertemuan.
-- Status menggunakan ENUM sesuai Status Lifecycle PRD.
-- ============================================================
CREATE TABLE IF NOT EXISTS validation_results (
    -- Primary key dengan auto increment (Target 2)
    validation_id     INT AUTO_INCREMENT PRIMARY KEY,
    -- Foreign key ke tabel rps (nullable, untuk status TIDAK_DITEMUKAN)
    rps_id            INT     NULL,
    -- Foreign key ke tabel bap (nullable, untuk status PENDING)
    bap_id            INT     NULL,
    -- Nomor pertemuan yang divalidasi
    meeting_number    INT     NOT NULL,
    -- Skor kemiripan hasil keyword matching (0.00 - 100.00)
    similarity_score  DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    -- Status hasil validasi sesuai PRD
    status            ENUM('SESUAI', 'TIDAK_SESUAI', 'TIDAK_DITEMUKAN', 'PENDING')
                      NOT NULL DEFAULT 'PENDING',
    -- Catatan tambahan (contoh: "Materi cocok dengan pertemuan ke-5")
    notes             TEXT,
    -- Timestamp proses validasi
    validated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Relasi ke tabel rps dan bap
    FOREIGN KEY (rps_id) REFERENCES rps(rps_id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    FOREIGN KEY (bap_id) REFERENCES bap(bap_id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    -- Memastikan nomor pertemuan unik secara global (Target 2)
    UNIQUE KEY uq_meeting (meeting_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- Tabel: upload_history (Riwayat Unggahan)
-- Mencatat seluruh aktivitas unggah file RPS (berhasil/gagal).
-- ============================================================
CREATE TABLE IF NOT EXISTS upload_history (
    -- Primary key dengan auto increment
    upload_id       INT AUTO_INCREMENT PRIMARY KEY,
    -- Nama asli file yang diunggah
    file_name       VARCHAR(255) NOT NULL,
    -- Path penyimpanan file di server/lokal
    file_path       VARCHAR(255) NOT NULL,
    -- Ukuran file dalam kilobyte
    file_size_kb    INT,
    -- Status unggahan: SUCCESS atau FAILED atau REPLACED
    upload_status   VARCHAR(20) NOT NULL,
    -- Pesan error jika unggahan gagal
    error_message   TEXT,
    -- Timestamp unggahan
    uploaded_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- Indeks Tambahan untuk Optimasi Performa Query
-- ============================================================

-- Indeks untuk mempercepat pencarian hasil validasi berdasarkan status
CREATE INDEX idx_validation_status ON validation_results(status);
