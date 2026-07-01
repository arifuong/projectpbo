"""
Modul custom exception untuk Sistem Validasi RPS-BAP.

Modul ini mendefinisikan seluruh exception khusus yang digunakan
di seluruh aplikasi. Setiap exception merepresentasikan jenis
kesalahan spesifik pada domain bisnis tertentu.

Penerapan OOP - Inheritance:
    Semua custom exception merupakan turunan dari AppBaseException,
    yang mewarisi class Exception bawaan Python.
    Hierarki: Exception -> AppBaseException -> [Domain Exceptions]

Penerapan SOLID - Single Responsibility:
    Setiap exception class bertanggung jawab atas satu jenis
    kesalahan domain tertentu.
"""


class AppBaseException(Exception):
    """
    Base exception untuk seluruh custom exception aplikasi.

    Semua exception khusus dalam sistem ini WAJIB mewarisi
    class ini agar dapat ditangkap secara seragam melalui
    satu blok except jika diperlukan.

    Inheritance:
        AppBaseException -> Exception (bawaan Python)

    Attributes:
        message (str): Pesan kesalahan yang menjelaskan error.
        details (dict): Detail tambahan terkait error (opsional).
    """

    def __init__(self, message: str, details: dict = None):
        """
        Inisialisasi base exception.

        Args:
            message: Pesan kesalahan utama yang menjelaskan
                    apa yang terjadi.
            details: Informasi tambahan dalam bentuk dictionary,
                    berguna untuk debugging dan logging.
        """
        super().__init__(message)
        self.message: str = message
        self.details: dict = details or {}

    def __str__(self) -> str:
        """
        Format string exception dengan detail jika tersedia.

        Returns:
            str: Pesan error lengkap dengan detail.
        """
        if self.details:
            return f"{self.message} | Detail: {self.details}"
        return self.message


# ============================================================
# Exception Domain: Database
# Digunakan oleh modul database/connection.py dan repositories
# ============================================================

class DatabaseConnectionError(AppBaseException):
    """
    Exception untuk kesalahan koneksi database.

    Dilemparkan ketika:
    - Koneksi ke database MySQL gagal dibuat
    - Koneksi timeout
    - Koneksi terputus secara tidak terduga

    Sesuai PRD Section 4.10 - Modul Database Management.
    """
    pass


class DatabaseQueryError(AppBaseException):
    """
    Exception untuk kesalahan eksekusi query database.

    Dilemparkan ketika:
    - Query SQL gagal dieksekusi (syntax error)
    - Constraint violation (unique, foreign key)
    - Deadlock atau lock timeout
    """
    pass


class DatabaseTransactionError(AppBaseException):
    """
    Exception untuk kesalahan transaksi database.

    Dilemparkan ketika:
    - Proses commit gagal
    - Proses rollback gagal
    - Transaksi tidak dapat diselesaikan
    """
    pass


# ============================================================
# Exception Domain: PDF Extraction
# Digunakan oleh modul utils/pdf_reader.py dan
# services/pdf_extraction_service.py
# ============================================================

class PDFExtractionError(AppBaseException):
    """
    Exception untuk kesalahan ekstraksi PDF.

    Dilemparkan ketika:
    - File PDF tidak dapat dibaca
    - Struktur tabel tidak ditemukan dalam PDF
    - pdfplumber atau pypdf gagal memproses file

    Sesuai PRD Section 4.3 - Modul PDF Extraction.
    """
    pass


class PDFTableNotFoundError(PDFExtractionError):
    """
    Exception ketika tabel tidak ditemukan dalam PDF.

    Turunan dari PDFExtractionError, dilemparkan ketika
    file PDF tidak mengandung tabel yang dapat diekstrak.
    """
    pass


# ============================================================
# Exception Domain: Text Cleaning
# Digunakan oleh modul utils/text_cleaner.py
# ============================================================

class TextCleaningError(AppBaseException):
    """
    Exception untuk kesalahan pembersihan teks.

    Dilemparkan ketika:
    - Input teks bernilai None atau tipe data tidak valid
    - Proses regex normalisasi gagal
    - Pipeline pembersihan teks mengalami kegagalan

    Sesuai PRD Section 4.4 - Modul Text Cleaning.
    """
    pass


# ============================================================
# Exception Domain: Validasi Bisnis
# Digunakan oleh modul services/validator.py
# ============================================================

class ValidationError(AppBaseException):
    """
    Exception untuk kesalahan proses validasi.

    Dilemparkan ketika:
    - Data RPS atau BAP tidak tersedia untuk divalidasi
    - Proses keyword matching gagal
    - Proses validasi urutan materi gagal

    Sesuai PRD Section 4.8 - Modul Validation Engine.
    """
    pass


# ============================================================
# Exception Domain: Report
# Digunakan oleh modul services/report_generator.py
# ============================================================

class ReportGenerationError(AppBaseException):
    """
    Exception untuk kesalahan pembuatan laporan.

    Dilemparkan ketika:
    - Data validasi tidak tersedia untuk membuat laporan
    - Proses ekspor ke PDF gagal
    - Proses ekspor ke Excel gagal

    Sesuai PRD Section 4.9 - Modul Report Generator.
    """
    pass


# ============================================================
# Exception Domain: File Upload
# Digunakan oleh modul services/file_upload_handler.py
# ============================================================

class FileUploadError(AppBaseException):
    """
    Exception untuk kesalahan upload file.

    Dilemparkan ketika:
    - Proses penyimpanan file gagal
    - Path penyimpanan tidak valid
    - Pencatatan riwayat upload gagal

    Sesuai PRD Section 4.2 - Modul Upload PDF RPS.
    """
    pass


class FileValidationError(FileUploadError):
    """
    Exception untuk kesalahan validasi file yang diunggah.

    Turunan dari FileUploadError, dilemparkan ketika file
    tidak memenuhi kriteria validasi:
    - Format file bukan .pdf (PRD BR-11)
    - Ukuran file melebihi 10 MB (PRD BR-11)

    Inheritance:
        FileValidationError -> FileUploadError -> AppBaseException
    """
    pass


# ============================================================
# Exception Domain: Data Mata Kuliah
# Digunakan oleh modul repositories dan services
# ============================================================

class CourseNotFoundError(AppBaseException):
    """
    Exception ketika mata kuliah tidak ditemukan di database.

    Dilemparkan ketika operasi memerlukan data mata kuliah
    yang tidak ada dalam tabel courses.
    """
    pass


# ============================================================
# Exception Domain: Nomor Pertemuan
# Digunakan oleh modul services/rps_manager.py dan
# services/bap_manager.py
# ============================================================

class DuplicateMeetingError(AppBaseException):
    """
    Exception untuk nomor pertemuan yang duplikat.

    Dilemparkan ketika user mencoba menyimpan data RPS atau BAP
    dengan nomor pertemuan yang sudah ada pada mata kuliah
    yang sama.

    Sesuai PRD BR-01 (RPS) dan BR-02 (BAP).
    """
    pass


class MeetingNumberExceededError(AppBaseException):
    """
    Exception ketika nomor pertemuan BAP melebihi batas RPS.

    Dilemparkan ketika nomor pertemuan pada data BAP melebihi
    total pertemuan yang tercantum pada RPS untuk mata kuliah
    yang bersangkutan.

    Sesuai PRD BR-02.
    """
    pass
