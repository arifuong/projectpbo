"""
Modul konstanta untuk Sistem Validasi RPS-BAP.

Modul ini menyimpan seluruh nilai konstanta yang digunakan
di seluruh aplikasi. Setiap magic number atau hardcoded value
WAJIB didefinisikan di sini agar mudah dipelihara dan diubah.

Konstanta dikelompokkan berdasarkan domain fungsional
sesuai dengan modul-modul pada PRD.
"""

# ============================================================
# Konstanta Upload File
# Sesuai PRD BR-11: Hanya menerima .pdf, maksimum 10 MB
# ============================================================
MAX_UPLOAD_SIZE_MB: int = 10
MAX_UPLOAD_SIZE_BYTES: int = MAX_UPLOAD_SIZE_MB * 1024 * 1024
ALLOWED_FILE_EXTENSIONS: tuple = (".pdf",)

# ============================================================
# Konstanta Keyword Matching
# Sesuai PRD BR-05: Threshold kemiripan minimal 70%
# Nilai ini dapat dikonfigurasi melalui AppSettings
# ============================================================
DEFAULT_SIMILARITY_THRESHOLD: float = 0.7

# ============================================================
# Konstanta Status Validasi
# Sesuai PRD Section 6 - Status Lifecycle per Pertemuan
# ============================================================
STATUS_PENDING: str = "PENDING"
STATUS_PROCESSING: str = "PROCESSING"
STATUS_SESUAI: str = "SESUAI"
STATUS_TIDAK_SESUAI: str = "TIDAK_SESUAI"
STATUS_TIDAK_DITEMUKAN: str = "TIDAK_DITEMUKAN"

# Kumpulan seluruh status yang valid untuk keperluan validasi input
VALID_STATUSES: tuple = (
    STATUS_PENDING,
    STATUS_PROCESSING,
    STATUS_SESUAI,
    STATUS_TIDAK_SESUAI,
    STATUS_TIDAK_DITEMUKAN,
)

# ============================================================
# Konstanta Status Upload
# Sesuai PRD Section 7.6 - Tabel upload_history
# ============================================================
UPLOAD_SUCCESS: str = "SUCCESS"
UPLOAD_FAILED: str = "FAILED"

# ============================================================
# Konstanta Stopwords Bahasa Indonesia
# Sesuai PRD Section 4.4 - Modul Text Cleaning
# Kata-kata umum yang dihapus saat proses pembersihan teks
# ============================================================
STOPWORDS: frozenset = frozenset({
    "dan", "yang", "untuk", "dengan", "atau",
    "di", "ke", "dari", "pada", "oleh",
    "ini", "itu", "adalah", "serta", "juga",
})

# ============================================================
# Konstanta Nama Folder
# Path relatif terhadap direktori dasar aplikasi
# ============================================================
UPLOAD_FOLDER: str = "uploads"
EXPORT_FOLDER: str = "exports"
REPORT_FOLDER: str = "reports"

# ============================================================
# Konstanta Format Tanggal dan Waktu
# ============================================================
DATE_FORMAT: str = "%Y-%m-%d"
DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"

# ============================================================
# Konstanta GUI - Ukuran dan Judul Aplikasi
# Sesuai PRD Section 10 - UI/UX Requirements
# ============================================================
APP_TITLE: str = "Sistem Validasi Kesesuaian RPS dan BAP"
APP_WIDTH: int = 1200
APP_HEIGHT: int = 700
APP_MIN_WIDTH: int = 1024
APP_MIN_HEIGHT: int = 600

# ============================================================
# Konstanta GUI - Warna Status Validasi
# Sesuai PRD Section 10.5: Warna berbeda untuk tiap status
# Hijau = Sesuai, Kuning = Tidak Sesuai, Merah = Tidak Ditemukan
# ============================================================
COLOR_SESUAI: str = "#28a745"
COLOR_TIDAK_SESUAI: str = "#ffc107"
COLOR_TIDAK_DITEMUKAN: str = "#dc3545"
COLOR_PENDING: str = "#6c757d"

# ============================================================
# Konstanta GUI - Warna Umum Aplikasi
# ============================================================
COLOR_PRIMARY: str = "#0d6efd"
COLOR_SECONDARY: str = "#6c757d"
COLOR_SUCCESS: str = "#28a745"
COLOR_DANGER: str = "#dc3545"
COLOR_WARNING: str = "#ffc107"
COLOR_INFO: str = "#17a2b8"
COLOR_BACKGROUND: str = "#f8f9fa"
COLOR_SIDEBAR: str = "#2c3e50"
COLOR_SIDEBAR_ACTIVE: str = "#34495e"
COLOR_WHITE: str = "#ffffff"
COLOR_TEXT_DARK: str = "#212529"
COLOR_TEXT_LIGHT: str = "#f8f9fa"
COLOR_BORDER: str = "#dee2e6"

# ============================================================
# Konstanta GUI - Font
# ============================================================
FONT_FAMILY: str = "Segoe UI"
FONT_SIZE_SMALL: int = 9
FONT_SIZE_NORMAL: int = 10
FONT_SIZE_MEDIUM: int = 12
FONT_SIZE_LARGE: int = 14
FONT_SIZE_TITLE: int = 18
FONT_SIZE_HEADER: int = 24

# ============================================================
# Konstanta Pertemuan
# Jumlah pertemuan standar dalam satu semester perkuliahan
# ============================================================
DEFAULT_MAX_MEETINGS: int = 16
DEFAULT_MIN_MEETINGS: int = 14

# ============================================================
# Konstanta Dashboard
# Sesuai PRD Section 4.1 - Modul Dashboard
# ============================================================
DEFAULT_TOP_MISMATCHED_LIMIT: int = 5

# ============================================================
# Konstanta Logging
# Konfigurasi untuk file log aplikasi
# ============================================================
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
LOG_FILE: str = "app.log"
LOG_MAX_BYTES: int = 5 * 1024 * 1024  # Ukuran maksimum 5 MB
LOG_BACKUP_COUNT: int = 3  # Jumlah file backup log

# ============================================================
# Konstanta Pesan Error
# Pesan error standar yang digunakan di seluruh aplikasi
# ============================================================
MSG_DB_CONNECTION_FAILED: str = "Gagal terhubung ke database"
MSG_DB_QUERY_FAILED: str = "Gagal mengeksekusi query database"
MSG_FILE_NOT_PDF: str = "File harus berformat PDF (.pdf)"
MSG_FILE_TOO_LARGE: str = f"Ukuran file melebihi batas maksimum ({MAX_UPLOAD_SIZE_MB} MB)"
MSG_FILE_NOT_FOUND: str = "File tidak ditemukan"
MSG_EXTRACTION_FAILED: str = "Gagal mengekstrak data dari file PDF"
MSG_COURSE_NOT_FOUND: str = "Mata kuliah tidak ditemukan"
MSG_DUPLICATE_MEETING: str = "Nomor pertemuan sudah ada untuk mata kuliah ini"
MSG_MEETING_EXCEEDED: str = "Nomor pertemuan melebihi total pertemuan pada RPS"
MSG_VALIDATION_NO_DATA: str = "Data RPS atau BAP belum tersedia untuk validasi"
MSG_REPORT_FAILED: str = "Gagal membuat laporan"
