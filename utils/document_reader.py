"""
Modul DocumentReader untuk Sistem Validasi RPS-BAP.

Modul ini mendefinisikan Abstract Base Class (ABC) DocumentReader yang bertindak
sebagai kelas induk untuk semua pembaca dokumen dalam sistem (seperti PDFReader).
"""

from abc import ABC, abstractmethod
from typing import List, Any


class DocumentReader(ABC):
    """
    Abstract Base Class untuk pembaca dokumen.

    Menerapkan konsep Abstraction dan Inheritance (PRD 12.3 & 12.4).
    Setiap pembaca dokumen konkret harus mewarisi kelas ini dan mengimplementasikan
    method abstraknya.

    Attributes:
        file_path (str): Path file dokumen yang akan dibaca.
    """

    def __init__(self, file_path: str) -> None:
        """
        Inisialisasi DocumentReader.

        Args:
            file_path: Path absolut atau relatif ke file dokumen.
        """
        self.file_path: str = file_path

    @abstractmethod
    def read(self) -> str:
        """
        Membaca teks dari dokumen secara keseluruhan.

        Returns:
            str: Teks lengkap hasil pembacaan dokumen.
        """
        pass

    @abstractmethod
    def extract_tables(self) -> List[List[List[str]]]:
        """
        Mengekstrak data tabel dari dokumen.

        Returns:
            List[List[List[str]]]: representasi tabel 3D: list of tables,
                                   di mana setiap tabel adalah list of rows,
                                   dan setiap row adalah list of cells (str).
        """
        pass

    @abstractmethod
    def extract_raw_text(self) -> str:
        """
        Mengekstrak teks mentah (raw text) dari dokumen.

        Returns:
            str: Teks mentah tanpa pemrosesan terstruktur.
        """
        pass
