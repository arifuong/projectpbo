"""
Modul FallbackTextReader untuk Sistem Validasi RPS-BAP.

Modul ini mendefinisikan class FallbackTextReader yang mewarisi DocumentReader.
Digunakan sebagai fallback reader untuk membaca file teks biasa (.txt) jika diperlukan.
"""

import os
from typing import List
from utils.document_reader import DocumentReader
from utils.logger import setup_logger

# Inisialisasi logger untuk FallbackTextReader
logger = setup_logger(__name__)


class FallbackTextReader(DocumentReader):
    """
    Class untuk membaca file teks biasa (.txt).

    Mewarisi DocumentReader (Inheritance) untuk menunjukkan sifat Polymorphism.
    """

    def read(self) -> str:
        """
        Membaca teks dari file secara keseluruhan.

        Returns:
            str: Teks lengkap dari file.
        """
        logger.info(f"Membaca file teks biasa: {self.file_path}")
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"File tidak ditemukan: {self.file_path}")

        with open(self.file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    def extract_tables(self) -> List[List[List[str]]]:
        """
        Mengekstrak data tabel.

        Karena file teks biasa tidak memiliki struktur tabel asli, method ini mengembalikan
        list kosong sesuai kontrak abstract class.

        Returns:
            List[List[List[str]]]: List kosong.
        """
        logger.warning("FallbackTextReader tidak mendukung ekstraksi tabel terstruktur.")
        return []

    def extract_raw_text(self) -> str:
        """
        Mengekstrak teks mentah dari file.

        Returns:
            str: Teks mentah dari file.
        """
        return self.read()

    def extract_lines(self) -> List[str]:
        """
        Membaca teks dan membaginya menjadi baris-baris.

        Returns:
            List[str]: List baris-baris teks.
        """
        content = self.read()
        return content.splitlines()
