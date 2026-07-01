"""
Main Entry Point - Sistem Validasi Kesesuaian RPS dan BAP.

Modul ini merupakan titik masuk utama (entry point) aplikasi.
Sesuai PRD Section 6 - Status & Lifecycle:
Aplikasi langsung menampilkan Dashboard tanpa proses login.

Tahap 1: Verifikasi konfigurasi dan koneksi database.
Tahap selanjutnya: Inisialisasi GUI Tkinter.
"""

import sys
import os

# Menambahkan direktori project ke sys.path agar semua modul dapat diimpor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.config import DatabaseConfig
from config.settings import AppSettings
from config.constants import APP_TITLE
from utils.logger import setup_logger

# Inisialisasi logger untuk modul main
logger = setup_logger(__name__)


def initialize_application() -> AppSettings:
    """
    Menginisialisasi seluruh konfigurasi aplikasi.

    Fungsi ini mempersiapkan konfigurasi database, pengaturan
    aplikasi, dan memastikan direktori yang diperlukan tersedia.

    Returns:
        AppSettings: Objek pengaturan aplikasi yang telah
                    diinisialisasi dan siap digunakan.

    Raises:
        SystemExit: Jika inisialisasi gagal, aplikasi dihentikan.
    """
    try:
        # Membuat konfigurasi database
        logger.info("Menginisialisasi konfigurasi database...")
        db_config = DatabaseConfig()
        logger.info(f"Konfigurasi database: {db_config}")

        # Membuat pengaturan aplikasi dengan Dependency Injection
        logger.info("Menginisialisasi pengaturan aplikasi...")
        settings = AppSettings(db_config=db_config)
        logger.info(f"Direktori upload: {settings.upload_dir}")
        logger.info(f"Direktori ekspor: {settings.export_dir}")
        logger.info(f"Direktori laporan: {settings.report_dir}")
        logger.info(
            f"Threshold kemiripan: {settings.similarity_threshold}"
        )

        logger.info("Inisialisasi aplikasi berhasil.")
        return settings

    except Exception as e:
        logger.exception(f"Gagal menginisialisasi aplikasi: {e}")
        sys.exit(1)


def main() -> None:
    """
    Fungsi utama untuk menjalankan aplikasi.

    Sesuai PRD Section 6 - Status & Lifecycle:
    [1] Buka Aplikasi -> langsung menuju Dashboard, tanpa login.
    """
    # Menampilkan header aplikasi
    logger.info("=" * 60)
    logger.info(f"  {APP_TITLE}")
    logger.info("=" * 60)

    # Menginisialisasi konfigurasi aplikasi
    settings = initialize_application()

    # Menampilkan ringkasan konfigurasi
    logger.info("Konfigurasi aktif:")
    logger.info(f"  - Database Host : {settings.db_config.host}")
    logger.info(f"  - Database Port : {settings.db_config.port}")
    logger.info(f"  - Database User : {settings.db_config.user}")
    logger.info(f"  - Database Name : {settings.db_config.database}")
    logger.info(f"  - Threshold     : {settings.similarity_threshold}")
    logger.info(f"  - Max Upload    : {settings.max_upload_size_mb} MB")

    logger.info("Meluncurkan Antarmuka GUI Desktop...")
    
    try:
        from gui.app import AppController
        app = AppController(settings)
        app.mainloop()
        logger.info("Aplikasi dihentikan dengan sukses.")
    except Exception as e:
        logger.critical(f"Kesalahan fatal peluncuran antarmuka GUI: {e}")
        print(f"\n[ERROR] Gagal meluncurkan aplikasi GUI:\n{e}\n")


# Entry point aplikasi
if __name__ == "__main__":
    main()
