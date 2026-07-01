"""
Modul logging untuk Sistem Validasi RPS-BAP.

Modul ini menyediakan fungsi untuk membuat dan mengkonfigurasi
logger yang konsisten di seluruh aplikasi. Setiap modul dapat
memiliki logger sendiri dengan nama unik yang memudahkan
pelacakan sumber pesan log.

Menggunakan RotatingFileHandler untuk mencegah file log
membengkak tanpa batas.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

from config.constants import (
    LOG_FORMAT,
    LOG_DATE_FORMAT,
    LOG_FILE,
    LOG_MAX_BYTES,
    LOG_BACKUP_COUNT,
)


def setup_logger(
    name: str,
    log_file: str = None,
    level: int = logging.INFO
) -> logging.Logger:
    """
    Membuat dan mengkonfigurasi logger untuk modul tertentu.

    Setiap modul memanggil fungsi ini dengan __name__ sebagai
    parameter name, sehingga pesan log dapat dilacak ke modul
    asalnya. Logger menulis ke file dan console secara bersamaan.

    Args:
        name: Nama logger, biasanya menggunakan __name__
             dari modul yang memanggil fungsi ini.
        log_file: Path file log. Jika None, menggunakan
                 default dari konstanta LOG_FILE.
        level: Level logging minimum yang akan dicatat.
              Default: logging.INFO.

    Returns:
        logging.Logger: Objek logger yang telah dikonfigurasi
                       dengan file handler dan console handler.

    Contoh penggunaan:
        >>> from utils.logger import setup_logger
        >>> logger = setup_logger(__name__)
        >>> logger.info("Aplikasi dimulai")
        >>> logger.error("Terjadi kesalahan")
    """
    # Menentukan path file log di direktori dasar aplikasi
    if log_file is None:
        base_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
        log_file = os.path.join(base_dir, LOG_FILE)

    # Membuat logger dengan nama modul yang diberikan
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Menghindari duplikasi handler jika logger sudah pernah dikonfigurasi
    # Hal ini dapat terjadi jika setup_logger dipanggil lebih dari sekali
    if logger.handlers:
        return logger

    # Membuat formatter untuk memformat pesan log secara konsisten
    formatter = logging.Formatter(
        fmt=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT
    )

    # Handler untuk menulis log ke file dengan mekanisme rotasi
    # File akan dirotasi ketika mencapai ukuran LOG_MAX_BYTES
    # Maksimal LOG_BACKUP_COUNT file backup yang disimpan
    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    # Handler untuk menampilkan log ke console (stdout)
    # Berguna saat pengembangan dan debugging
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # Menambahkan kedua handler ke logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
