"""
Modul pengaturan aplikasi untuk Sistem Validasi RPS-BAP.

Modul ini menyediakan class AppSettings yang menggabungkan
seluruh konfigurasi aplikasi termasuk konfigurasi database,
path folder, dan parameter operasional lainnya.

Menerapkan pola Composition: AppSettings memiliki (has-a)
DatabaseConfig sebagai bagian dari konfigurasinya.
"""

import os
from config.config import DatabaseConfig
from config.constants import (
    UPLOAD_FOLDER,
    EXPORT_FOLDER,
    REPORT_FOLDER,
    DEFAULT_SIMILARITY_THRESHOLD,
    MAX_UPLOAD_SIZE_MB,
)


class AppSettings:
    """
    Class untuk mengelola seluruh pengaturan aplikasi secara terpusat.

    Class ini berfungsi sebagai single point of access untuk
    seluruh konfigurasi yang dibutuhkan oleh berbagai modul
    dalam sistem. Menerapkan prinsip Single Responsibility:
    hanya bertanggung jawab mengelola pengaturan.

    Composition:
        AppSettings memiliki (has-a) DatabaseConfig.
        Jika AppSettings dihancurkan, referensi ke DatabaseConfig
        juga tidak lagi diperlukan.

    Attributes:
        db_config (DatabaseConfig): Objek konfigurasi koneksi database.
        base_dir (str): Direktori dasar (root) aplikasi.
        upload_dir (str): Path absolut direktori penyimpanan file upload.
        export_dir (str): Path absolut direktori penyimpanan file ekspor.
        report_dir (str): Path absolut direktori penyimpanan file laporan.
        similarity_threshold (float): Ambang batas skor kemiripan (default 0.7).
        max_upload_size_mb (int): Ukuran maksimum file upload dalam MB.

    Contoh penggunaan:
        >>> settings = AppSettings()
        >>> print(settings.upload_dir)
        '/path/to/project/uploads'
        >>> print(settings.db_config.host)
        'localhost'
    """

    def __init__(self, db_config: DatabaseConfig = None):
        """
        Inisialisasi pengaturan aplikasi.

        Menerima objek DatabaseConfig melalui Dependency Injection.
        Jika tidak diberikan, akan membuat instance default.

        Args:
            db_config: Konfigurasi database yang akan digunakan.
                      Jika None, menggunakan konfigurasi default.
        """
        # Composition: AppSettings memiliki DatabaseConfig
        # Dependency Injection: konfigurasi database diterima dari luar
        self.db_config: DatabaseConfig = db_config or DatabaseConfig()

        # Menentukan direktori dasar aplikasi
        # Menggunakan path relatif dari posisi file settings.py
        self.base_dir: str = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )

        # Menyusun path absolut untuk setiap direktori kerja
        self.upload_dir: str = os.path.join(self.base_dir, UPLOAD_FOLDER)
        self.export_dir: str = os.path.join(self.base_dir, EXPORT_FOLDER)
        self.report_dir: str = os.path.join(self.base_dir, REPORT_FOLDER)

        # Parameter operasional yang dapat dikonfigurasi
        # Sesuai PRD BR-05: threshold kemiripan default 70%
        self.similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD
        # Sesuai PRD BR-11: ukuran file maksimum 10 MB
        self.max_upload_size_mb: int = MAX_UPLOAD_SIZE_MB

        # Memastikan seluruh direktori kerja tersedia
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """
        Membuat direktori yang dibutuhkan jika belum ada.

        Method ini bersifat privat (diawali underscore) karena
        hanya dipanggil secara internal saat inisialisasi.
        Menggunakan os.makedirs dengan exist_ok=True agar
        tidak error jika direktori sudah ada.
        """
        # Daftar semua direktori yang harus tersedia
        directories: list = [
            self.upload_dir,
            self.export_dir,
            self.report_dir,
        ]

        # Membuat setiap direktori beserta parent directory-nya
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

    def get_upload_path(self, filename: str) -> str:
        """
        Menghasilkan path absolut untuk file yang akan diupload.

        Args:
            filename: Nama file yang akan disimpan.

        Returns:
            str: Path absolut lengkap ke lokasi penyimpanan file.
        """
        return os.path.join(self.upload_dir, filename)

    def get_export_path(self, filename: str) -> str:
        """
        Menghasilkan path absolut untuk file yang akan diekspor.

        Args:
            filename: Nama file ekspor yang akan disimpan.

        Returns:
            str: Path absolut lengkap ke lokasi ekspor file.
        """
        return os.path.join(self.export_dir, filename)

    def get_report_path(self, filename: str) -> str:
        """
        Menghasilkan path absolut untuk file laporan.

        Args:
            filename: Nama file laporan yang akan disimpan.

        Returns:
            str: Path absolut lengkap ke lokasi penyimpanan laporan.
        """
        return os.path.join(self.report_dir, filename)

    def __repr__(self) -> str:
        """
        Representasi string dari pengaturan aplikasi.

        Returns:
            str: Informasi pengaturan dalam format yang mudah dibaca.
        """
        return (
            f"AppSettings(db={self.db_config}, "
            f"threshold={self.similarity_threshold}, "
            f"max_upload={self.max_upload_size_mb}MB)"
        )
