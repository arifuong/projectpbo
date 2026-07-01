"""
Unit Test untuk Tahap 1 - Konfigurasi dan Struktur Project.

Modul ini menguji:
1. Class DatabaseConfig (config/config.py)
2. Konstanta aplikasi (config/constants.py)
3. Class AppSettings (config/settings.py)
4. Fungsi setup_logger (utils/logger.py)
5. Custom exceptions (utils/exceptions.py)
6. Keberadaan SQL schema (sql/schema.sql)
7. Struktur folder project

Menjalankan test:
    pytest tests/test_tahap1_config.py -v
"""

import os
import sys
import logging
import pytest

# Memastikan direktori project ada di sys.path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from config.config import DatabaseConfig
from config.settings import AppSettings
from config.constants import (
    MAX_UPLOAD_SIZE_MB,
    MAX_UPLOAD_SIZE_BYTES,
    ALLOWED_FILE_EXTENSIONS,
    DEFAULT_SIMILARITY_THRESHOLD,
    STATUS_SESUAI,
    STATUS_TIDAK_SESUAI,
    STATUS_TIDAK_DITEMUKAN,
    STATUS_PENDING,
    STATUS_PROCESSING,
    VALID_STATUSES,
    UPLOAD_SUCCESS,
    UPLOAD_FAILED,
    STOPWORDS,
    APP_TITLE,
    COLOR_SESUAI,
    COLOR_TIDAK_SESUAI,
    COLOR_TIDAK_DITEMUKAN,
    LOG_FORMAT,
    LOG_FILE,
    MSG_DB_CONNECTION_FAILED,
    MSG_FILE_NOT_PDF,
    MSG_FILE_TOO_LARGE,
    MSG_DUPLICATE_MEETING,
)
from utils.logger import setup_logger
from utils.exceptions import (
    AppBaseException,
    DatabaseConnectionError,
    DatabaseQueryError,
    DatabaseTransactionError,
    PDFExtractionError,
    PDFTableNotFoundError,
    TextCleaningError,
    ValidationError,
    ReportGenerationError,
    FileUploadError,
    FileValidationError,
    DuplicateMeetingError,
    MeetingNumberExceededError,
)


# ============================================================
# Test Class: DatabaseConfig
# Menguji konfigurasi database dan encapsulation password
# ============================================================

class TestDatabaseConfig:
    """Test suite untuk class DatabaseConfig."""

    def test_default_initialization(self):
        """Memastikan nilai default digunakan jika parameter tidak diberikan."""
        config = DatabaseConfig()

        assert config.host == "localhost"
        assert config.port == 3306
        assert config.user == "root"
        assert config.database == "validasi_rps_bap"

    def test_custom_initialization(self):
        """Memastikan parameter kustom diterapkan dengan benar."""
        config = DatabaseConfig(
            host="192.168.1.100",
            port=3307,
            user="admin",
            password="secret123",
            database="test_db"
        )

        assert config.host == "192.168.1.100"
        assert config.port == 3307
        assert config.user == "admin"
        assert config.database == "test_db"

    def test_password_encapsulation(self):
        """
        Memastikan password tidak dapat diakses langsung.
        
        Sesuai PRD Section 12.2 - Encapsulation:
        Password disembunyikan menggunakan name mangling.
        """
        config = DatabaseConfig(password="rahasia")

        # Password harus diakses melalui method accessor
        assert config.get_password() == "rahasia"

        # Akses langsung ke __password harus gagal (name mangling)
        with pytest.raises(AttributeError):
            _ = config.__password

    def test_get_connection_params(self):
        """Memastikan dictionary parameter koneksi lengkap dan benar."""
        config = DatabaseConfig(
            host="localhost",
            port=3306,
            user="root",
            password="pass123",
            database="mydb"
        )

        params = config.get_connection_params()

        assert isinstance(params, dict)
        assert params["host"] == "localhost"
        assert params["port"] == 3306
        assert params["user"] == "root"
        assert params["password"] == "pass123"
        assert params["database"] == "mydb"

    def test_repr_hides_password(self):
        """Memastikan representasi string tidak menampilkan password."""
        config = DatabaseConfig(password="sensitif")
        repr_str = repr(config)

        # Password tidak boleh muncul dalam representasi string
        assert "sensitif" not in repr_str
        assert "DatabaseConfig" in repr_str


# ============================================================
# Test Class: AppSettings
# Menguji pengaturan aplikasi dan composition
# ============================================================

class TestAppSettings:
    """Test suite untuk class AppSettings."""

    def test_default_initialization(self):
        """Memastikan pengaturan default diterapkan dengan benar."""
        settings = AppSettings()

        assert settings.similarity_threshold == 0.7
        assert settings.max_upload_size_mb == 10
        assert settings.db_config is not None

    def test_composition_with_db_config(self):
        """
        Memastikan Composition diterapkan: AppSettings has-a DatabaseConfig.
        
        Sesuai PRD Section 12.6 - Composition.
        """
        db_config = DatabaseConfig(
            host="custom_host",
            database="custom_db"
        )
        settings = AppSettings(db_config=db_config)

        # Memastikan objek DatabaseConfig yang diberikan digunakan
        assert settings.db_config is db_config
        assert settings.db_config.host == "custom_host"
        assert settings.db_config.database == "custom_db"

    def test_directory_creation(self):
        """Memastikan direktori upload, export, dan report dibuat otomatis."""
        settings = AppSettings()

        assert os.path.isdir(settings.upload_dir)
        assert os.path.isdir(settings.export_dir)
        assert os.path.isdir(settings.report_dir)

    def test_get_upload_path(self):
        """Memastikan path upload file terbentuk dengan benar."""
        settings = AppSettings()
        path = settings.get_upload_path("rps_test.pdf")

        assert path.endswith("rps_test.pdf")
        assert "uploads" in path

    def test_get_export_path(self):
        """Memastikan path export file terbentuk dengan benar."""
        settings = AppSettings()
        path = settings.get_export_path("laporan.xlsx")

        assert path.endswith("laporan.xlsx")
        assert "exports" in path

    def test_get_report_path(self):
        """Memastikan path report file terbentuk dengan benar."""
        settings = AppSettings()
        path = settings.get_report_path("report.pdf")

        assert path.endswith("report.pdf")
        assert "reports" in path

    def test_base_dir_is_project_root(self):
        """Memastikan base_dir mengarah ke root project."""
        settings = AppSettings()

        # base_dir harus berisi app.py (root project)
        assert os.path.isdir(settings.base_dir)

    def test_repr_output(self):
        """Memastikan representasi string berisi informasi penting."""
        settings = AppSettings()
        repr_str = repr(settings)

        assert "AppSettings" in repr_str
        assert "threshold" in repr_str
        assert "max_upload" in repr_str


# ============================================================
# Test Class: Constants
# Menguji seluruh konstanta yang didefinisikan
# ============================================================

class TestConstants:
    """Test suite untuk modul constants."""

    def test_upload_size_constants(self):
        """Memastikan konstanta upload sesuai PRD BR-11."""
        assert MAX_UPLOAD_SIZE_MB == 10
        assert MAX_UPLOAD_SIZE_BYTES == 10 * 1024 * 1024
        assert ALLOWED_FILE_EXTENSIONS == (".pdf",)

    def test_similarity_threshold(self):
        """Memastikan threshold default sesuai PRD BR-05."""
        assert DEFAULT_SIMILARITY_THRESHOLD == 0.7

    def test_validation_statuses(self):
        """Memastikan semua status validasi tersedia sesuai PRD Section 6."""
        assert STATUS_SESUAI == "SESUAI"
        assert STATUS_TIDAK_SESUAI == "TIDAK_SESUAI"
        assert STATUS_TIDAK_DITEMUKAN == "TIDAK_DITEMUKAN"
        assert STATUS_PENDING == "PENDING"
        assert STATUS_PROCESSING == "PROCESSING"

        # Semua status harus terdaftar dalam VALID_STATUSES
        assert STATUS_SESUAI in VALID_STATUSES
        assert STATUS_TIDAK_SESUAI in VALID_STATUSES
        assert STATUS_TIDAK_DITEMUKAN in VALID_STATUSES
        assert STATUS_PENDING in VALID_STATUSES
        assert STATUS_PROCESSING in VALID_STATUSES

    def test_upload_statuses(self):
        """Memastikan status upload tersedia."""
        assert UPLOAD_SUCCESS == "SUCCESS"
        assert UPLOAD_FAILED == "FAILED"

    def test_stopwords(self):
        """Memastikan stopwords Bahasa Indonesia tersedia sesuai PRD 4.4."""
        assert "dan" in STOPWORDS
        assert "yang" in STOPWORDS
        assert "untuk" in STOPWORDS
        assert "dengan" in STOPWORDS
        assert "atau" in STOPWORDS
        # Stopwords harus berupa frozenset (immutable)
        assert isinstance(STOPWORDS, frozenset)

    def test_app_title(self):
        """Memastikan judul aplikasi sesuai PRD."""
        assert APP_TITLE == "Sistem Validasi Kesesuaian RPS dan BAP"

    def test_color_constants(self):
        """Memastikan warna status validasi tersedia sesuai PRD 10.5."""
        # Warna harus berformat hex color code
        assert COLOR_SESUAI.startswith("#")
        assert COLOR_TIDAK_SESUAI.startswith("#")
        assert COLOR_TIDAK_DITEMUKAN.startswith("#")

    def test_error_messages(self):
        """Memastikan pesan error tersedia dan bermakna."""
        assert len(MSG_DB_CONNECTION_FAILED) > 0
        assert len(MSG_FILE_NOT_PDF) > 0
        assert len(MSG_FILE_TOO_LARGE) > 0
        assert len(MSG_DUPLICATE_MEETING) > 0

    def test_log_constants(self):
        """Memastikan konstanta logging tersedia."""
        assert len(LOG_FORMAT) > 0
        assert len(LOG_FILE) > 0


# ============================================================
# Test Class: Logger
# Menguji fungsi setup_logger
# ============================================================

class TestLogger:
    """Test suite untuk fungsi setup_logger."""

    def test_logger_creation(self, tmp_path):
        """Memastikan logger berhasil dibuat."""
        log_file = str(tmp_path / "test.log")
        logger = setup_logger("test_logger", log_file=log_file)

        assert logger is not None
        assert logger.name == "test_logger"
        assert logger.level == logging.INFO

    def test_logger_writes_to_file(self, tmp_path):
        """Memastikan logger menulis pesan ke file log."""
        log_file = str(tmp_path / "test_write.log")
        logger = setup_logger("test_writer", log_file=log_file)

        # Menulis pesan log
        logger.info("Pesan uji coba logging")

        # Memverifikasi file log berisi pesan
        with open(log_file, "r", encoding="utf-8") as f:
            content = f.read()

        assert "Pesan uji coba logging" in content

    def test_logger_has_handlers(self, tmp_path):
        """Memastikan logger memiliki file handler dan console handler."""
        log_file = str(tmp_path / "test_handler.log")
        logger = setup_logger("test_handler_logger", log_file=log_file)

        # Harus memiliki minimal 2 handler (file + console)
        assert len(logger.handlers) >= 2

    def test_logger_no_duplicate_handlers(self, tmp_path):
        """Memastikan setup_logger tidak menambah handler duplikat."""
        log_file = str(tmp_path / "test_dup.log")

        # Memanggil setup_logger dua kali dengan nama yang sama
        logger1 = setup_logger("test_no_dup", log_file=log_file)
        handler_count = len(logger1.handlers)
        logger2 = setup_logger("test_no_dup", log_file=log_file)

        # Jumlah handler tidak boleh bertambah
        assert len(logger2.handlers) == handler_count
        assert logger1 is logger2


# ============================================================
# Test Class: Custom Exceptions
# Menguji hierarki dan perilaku custom exception
# ============================================================

class TestCustomExceptions:
    """Test suite untuk custom exceptions."""

    def test_base_exception(self):
        """Memastikan AppBaseException berfungsi dengan benar."""
        exc = AppBaseException("Test error")

        assert str(exc) == "Test error"
        assert exc.message == "Test error"
        assert exc.details == {}

    def test_base_exception_with_details(self):
        """Memastikan detail error disertakan dalam pesan."""
        exc = AppBaseException(
            "Error terjadi",
            details={"kode": 500, "modul": "database"}
        )

        assert "Error terjadi" in str(exc)
        assert "kode" in str(exc)
        assert exc.details["kode"] == 500

    def test_inheritance_hierarchy(self):
        """
        Memastikan hierarki inheritance exception sesuai desain.
        
        Semua custom exception harus turunan dari AppBaseException.
        """
        # Semua exception harus merupakan turunan AppBaseException
        assert issubclass(DatabaseConnectionError, AppBaseException)
        assert issubclass(DatabaseQueryError, AppBaseException)
        assert issubclass(DatabaseTransactionError, AppBaseException)
        assert issubclass(PDFExtractionError, AppBaseException)
        assert issubclass(TextCleaningError, AppBaseException)
        assert issubclass(ValidationError, AppBaseException)
        assert issubclass(ReportGenerationError, AppBaseException)
        assert issubclass(FileUploadError, AppBaseException)
        assert issubclass(DuplicateMeetingError, AppBaseException)
        assert issubclass(MeetingNumberExceededError, AppBaseException)

    def test_nested_inheritance(self):
        """
        Memastikan inheritance bertingkat berfungsi dengan benar.
        
        FileValidationError -> FileUploadError -> AppBaseException
        PDFTableNotFoundError -> PDFExtractionError -> AppBaseException
        """
        assert issubclass(FileValidationError, FileUploadError)
        assert issubclass(FileValidationError, AppBaseException)
        assert issubclass(PDFTableNotFoundError, PDFExtractionError)
        assert issubclass(PDFTableNotFoundError, AppBaseException)

    def test_catch_by_base_exception(self):
        """Memastikan semua exception dapat ditangkap oleh AppBaseException."""
        exceptions_to_test = [
            DatabaseConnectionError("DB error"),
            PDFExtractionError("PDF error"),
            ValidationError("Validation error"),
            FileUploadError("Upload error"),
        ]

        for exc in exceptions_to_test:
            # Semua exception harus bisa di-catch sebagai AppBaseException
            with pytest.raises(AppBaseException):
                raise exc

    def test_exception_preserves_message(self):
        """Memastikan pesan error dipertahankan pada setiap exception."""
        test_cases = [
            (DatabaseConnectionError, "Koneksi gagal"),
            (PDFExtractionError, "PDF rusak"),
            (ValidationError, "Data tidak valid"),
            (FileValidationError, "Bukan file PDF"),
            (DuplicateMeetingError, "Pertemuan duplikat"),
            (MeetingNumberExceededError, "Melebihi batas"),
        ]

        for exc_class, message in test_cases:
            exc = exc_class(message)
            assert exc.message == message
            assert message in str(exc)


# ============================================================
# Test Class: Struktur Folder
# Menguji keberadaan direktori dan file penting
# ============================================================

class TestProjectStructure:
    """Test suite untuk memverifikasi struktur folder project."""

    def _get_project_root(self) -> str:
        """Mendapatkan path root project."""
        return os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )

    def test_config_directory_exists(self):
        """Memastikan direktori config/ tersedia."""
        root = self._get_project_root()
        assert os.path.isdir(os.path.join(root, "config"))

    def test_database_directory_exists(self):
        """Memastikan direktori database/ tersedia."""
        root = self._get_project_root()
        assert os.path.isdir(os.path.join(root, "database"))

    def test_models_directory_exists(self):
        """Memastikan direktori models/ tersedia."""
        root = self._get_project_root()
        assert os.path.isdir(os.path.join(root, "models"))

    def test_repositories_directory_exists(self):
        """Memastikan direktori repositories/ tersedia."""
        root = self._get_project_root()
        assert os.path.isdir(os.path.join(root, "repositories"))

    def test_services_directory_exists(self):
        """Memastikan direktori services/ tersedia."""
        root = self._get_project_root()
        assert os.path.isdir(os.path.join(root, "services"))

    def test_utils_directory_exists(self):
        """Memastikan direktori utils/ tersedia."""
        root = self._get_project_root()
        assert os.path.isdir(os.path.join(root, "utils"))

    def test_app_directory_exists(self):
        """Memastikan direktori app/ tersedia."""
        root = self._get_project_root()
        assert os.path.isdir(os.path.join(root, "app"))

    def test_sql_directory_exists(self):
        """Memastikan direktori sql/ tersedia."""
        root = self._get_project_root()
        assert os.path.isdir(os.path.join(root, "sql"))

    def test_tests_directory_exists(self):
        """Memastikan direktori tests/ tersedia."""
        root = self._get_project_root()
        assert os.path.isdir(os.path.join(root, "tests"))

    def test_schema_sql_exists(self):
        """Memastikan file sql/schema.sql tersedia."""
        root = self._get_project_root()
        schema_path = os.path.join(root, "sql", "schema.sql")
        assert os.path.isfile(schema_path)

    def test_schema_sql_contains_tables(self):
        """Memastikan schema.sql berisi DDL untuk semua tabel PRD."""
        root = self._get_project_root()
        schema_path = os.path.join(root, "sql", "schema.sql")

        with open(schema_path, "r", encoding="utf-8") as f:
            content = f.read().lower()

        # Memeriksa keberadaan semua tabel sesuai PRD Section 7
        assert "create table" in content
        assert "courses" not in content
        assert "course_id" not in content
        assert "rps" in content
        assert "bap" in content
        assert "validation_results" in content
        assert "upload_history" in content

    def test_app_py_exists(self):
        """Memastikan file app.py tersedia."""
        root = self._get_project_root()
        assert os.path.isfile(os.path.join(root, "app.py"))

    def test_requirements_txt_exists(self):
        """Memastikan file requirements.txt tersedia."""
        root = self._get_project_root()
        req_path = os.path.join(root, "requirements.txt")
        assert os.path.isfile(req_path)

    def test_requirements_contains_dependencies(self):
        """Memastikan requirements.txt berisi dependency sesuai PRD."""
        root = self._get_project_root()
        req_path = os.path.join(root, "requirements.txt")

        with open(req_path, "r", encoding="utf-8") as f:
            content = f.read().lower()

        # Memeriksa dependency sesuai PRD Section 11
        assert "mysql-connector-python" in content
        assert "pdfplumber" in content
        assert "pypdf" in content
        assert "pandas" in content
        assert "openpyxl" in content
        assert "reportlab" in content
        assert "pytest" in content
