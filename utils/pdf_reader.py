"""
Modul PDFReader untuk Sistem Validasi RPS-BAP.

Modul ini mengimplementasikan class PDFReader yang merupakan kelas tiruan dari DocumentReader.
Bertanggung jawab untuk membaca konten file PDF (RPS) menggunakan pdfplumber
dan pypdf sebagai fallback, serta Tesseract OCR sebagai fallback terakhir.
"""

import os
from typing import List, Any, Dict, Optional
import pdfplumber
from pypdf import PdfReader as PyPdfReader

from utils.document_reader import DocumentReader
from utils.rps_parser import RPSParser
from utils.logger import setup_logger
from utils.exceptions import PDFExtractionError, PDFTableNotFoundError

# Inisialisasi logger untuk PDFReader
logger = setup_logger(__name__)


class PDFReader(DocumentReader):
    """
    Class untuk membaca file PDF.

    Mewarisi DocumentReader (Inheritance).
    Menggunakan library `pdfplumber` untuk mengekstrak tabel secara akurat,
    dan `pypdf` sebagai fallback untuk mengekstrak teks mentah jika pdfplumber gagal,
    serta Tesseract OCR sebagai fallback akhir.
    """

    def __init__(self, file_path: str) -> None:
        super().__init__(file_path)
        self._rps_parser = RPSParser()

    def read(self) -> str:
        """
        Membaca teks dari dokumen PDF secara keseluruhan menggunakan pypdf/pdfplumber.

        Returns:
            str: Teks lengkap dari file PDF.

        Raises:
            PDFExtractionError: Jika file tidak ditemukan atau gagal dibaca.
        """
        logger.info(f"Membaca file PDF secara keseluruhan: {self.file_path}")
        if not os.path.exists(self.file_path):
            raise PDFExtractionError(f"File PDF tidak ditemukan: {self.file_path}")

        try:
            return self.extract_raw_text()
        except Exception as e:
            logger.error(f"Gagal membaca teks dari PDF: {e}")
            raise PDFExtractionError(f"Gagal mengekstrak teks PDF: {e}")

    def extract_tables(self) -> List[List[List[str]]]:
        """
        Mengekstrak data tabel dari dokumen PDF menggunakan pdfplumber.

        Menyaring tabel berdasarkan header RPS dan mencatat halaman temuan.

        Returns:
            List[List[List[str]]]: List berisi tabel-tabel yang ditemukan.
                                   Setiap tabel direpresentasikan sebagai list of list of string.

        Raises:
            PDFTableNotFoundError: Jika tidak ada tabel yang ditemukan dalam PDF.
            PDFExtractionError: Jika terjadi kesalahan teknis pembacaan PDF.
        """
        logger.info(f"Mengekstrak tabel dari PDF: {self.file_path}")
        if not os.path.exists(self.file_path):
            raise PDFExtractionError(f"File PDF tidak ditemukan: {self.file_path}")

        extracted_tables: List[List[List[str]]] = []
        total_tables_found = 0
        try:
            with pdfplumber.open(self.file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    logger.info(f"Halaman {page_num}: membaca tabel PDF")
                    tables = page.extract_tables()
                    if tables:
                        for t in tables:
                            total_tables_found += 1
                            # Bersihkan sel bernilai None menjadi string kosong
                            cleaned_table = [
                                [str(cell) if cell is not None else "" for cell in row]
                                for row in t
                            ]
                            
                            if self._is_rps_table(cleaned_table):
                                logger.info(f"Halaman {page_num}: tabel RPS ditemukan")
                                extracted_tables.append(cleaned_table)
            
            logger.info(f"Total tabel ditemukan: {total_tables_found}")
            
            if not extracted_tables:
                logger.warning(f"Tidak ada tabel terdeteksi di file PDF: {self.file_path}")
                raise PDFTableNotFoundError("Tabel Pokok Bahasan tidak ditemukan di dokumen PDF.")
                
            return extracted_tables
        except PDFTableNotFoundError:
            raise
        except Exception as e:
            logger.exception(f"Gagal mengekstrak tabel dari PDF: {e}")
            raise PDFExtractionError(f"Gagal mengekstrak tabel PDF: {e}")

    def _is_rps_table(self, table: List[List[str]]) -> bool:
        """
        Memeriksa apakah tabel mentah adalah tabel RPS berdasarkan kecocokan keyword header.

        Args:
            table: Baris-baris tabel.

        Returns:
            bool: True jika terdeteksi tabel RPS, False jika tidak.
        """
        if len(table) < 2:
            return False
            
        return self._rps_parser.is_rps_table(table)

    def extract_words_by_page(self) -> List[Dict[str, Any]]:
        """
        Mengekstrak kata beserta koordinat per halaman menggunakan pdfplumber.

        Dipakai sebagai fallback saat PDF tidak memiliki garis tabel yang
        dapat dibaca `extract_tables`.
        """
        logger.info(f"Mengekstrak words dari PDF menggunakan pdfplumber: {self.file_path}")
        if not os.path.exists(self.file_path):
            raise PDFExtractionError(f"File PDF tidak ditemukan: {self.file_path}")

        pages_words: List[Dict[str, Any]] = []
        try:
            with pdfplumber.open(self.file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    words = page.extract_words(
                        keep_blank_chars=False,
                        use_text_flow=True,
                    )
                    logger.info(f"Halaman {page_num}: words terbaca {len(words)}")
                    pages_words.append({
                        "page_number": page_num,
                        "width": float(page.width),
                        "height": float(page.height),
                        "words": words,
                    })
            return pages_words
        except Exception as e:
            logger.exception(f"Gagal mengekstrak words dari PDF: {e}")
            raise PDFExtractionError(f"Gagal mengekstrak words PDF: {e}")

    def extract_raw_text(self) -> str:
        """
        Mengekstrak teks mentah dari file PDF menggunakan pypdf sebagai fallback utama.

        Returns:
            str: Teks mentah gabungan seluruh halaman PDF.

        Raises:
            PDFExtractionError: Jika terjadi kesalahan pembacaan PDF.
        """
        logger.info(f"Mengekstrak teks mentah dari PDF menggunakan pypdf: {self.file_path}")
        if not os.path.exists(self.file_path):
            raise PDFExtractionError(f"File PDF tidak ditemukan: {self.file_path}")

        text_content = []
        try:
            reader = PyPdfReader(self.file_path)
            for page_num, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text()
                if page_text:
                    text_content.append(page_text)
            
            raw_text = "\n".join(text_content)
            
            # Jika pypdf mengembalikan string kosong, coba gunakan pdfplumber
            if not raw_text.strip():
                logger.warning("Ekstraksi pypdf kosong, mencoba pdfplumber sebagai cadangan teks...")
                with pdfplumber.open(self.file_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_content.append(page_text)
                raw_text = "\n".join(text_content)
                
            return raw_text
        except Exception as e:
            logger.exception(f"Gagal mengekstrak teks mentah dari PDF: {e}")
            raise PDFExtractionError(f"Gagal mengekstrak teks mentah PDF: {e}")

    def _find_tesseract_path(self) -> Optional[str]:
        """
        Mencari path executable tesseract di Windows secara otomatis.
        """
        import shutil
        path = shutil.which("tesseract")
        if path:
            return path
            
        possible_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            possible_paths.append(os.path.join(local_appdata, "Tesseract-OCR", "tesseract.exe"))
            
        for p in possible_paths:
            if os.path.exists(p):
                return p
                
        return None

    def extract_text_via_ocr(self) -> str:
        """
        Mengekstrak teks mentah menggunakan Tesseract OCR sebagai fallback terakhir.
        Berguna untuk PDF hasil scan / berupa gambar.
        """
        logger.info(f"Mengekstrak teks via OCR dari PDF: {self.file_path}")
        
        try:
            import pytesseract
            import pdf2image
        except ImportError:
            logger.error("Library pytesseract atau pdf2image tidak terpasang. OCR diabaikan.")
            return ""

        tesseract_path = self._find_tesseract_path()
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            logger.info(f"Tesseract ditemukan di: {tesseract_path}")
        else:
            logger.warning("Executable tesseract tidak ditemukan. OCR diabaikan.")
            return ""

        try:
            # Convert PDF pages to PIL images
            images = pdf2image.convert_from_path(self.file_path, dpi=150)
            logger.info(f"Berhasil merender {len(images)} halaman untuk OCR.")
            text_pages = []
            
            for page_num, img in enumerate(images, start=1):
                logger.info(f"OCR Halaman {page_num}...")
                page_text = pytesseract.image_to_string(img, lang='ind+eng')
                if page_text:
                    text_pages.append(page_text)
                    
            return "\n".join(text_pages)
        except Exception as e:
            logger.warning(f"Gagal mengekstrak teks via OCR: {e}")
            return ""
