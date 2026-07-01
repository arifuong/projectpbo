"""
Modul TextCleaner untuk Sistem Validasi RPS-BAP.

Modul ini mendefinisikan class TextCleaner yang bertugas melakukan
pembersihan dan normalisasi teks (RPS/BAP) menggunakan string processing
dan Regular Expressions (Regex).

Sesuai PRD Section 4.4 - Modul Text Cleaning.
"""

import re
from typing import Set

# Coba impor STOPWORDS dari constants, jika gagal gunakan set default
try:
    from config.constants import STOPWORDS
except ImportError:
    STOPWORDS = frozenset({"dan", "yang", "untuk", "dengan", "atau"})

from utils.logger import setup_logger
from utils.exceptions import TextCleaningError

# Inisialisasi logger untuk TextCleaner
logger = setup_logger(__name__)


class TextCleaner:
    """
    Class untuk melakukan pembersihan teks dan normalisasi.

    Menyediakan method pembersihan bertahap (lowercase, trim whitespace, 
    hapus karakter khusus, normalisasi regex, dan penghapusan stopwords).
    """

    def __init__(self, stopwords: Set[str] = None) -> None:
        """
        Inisialisasi TextCleaner dengan stopwords.

        Args:
            stopwords: Set stopwords kustom. Jika None, gunakan STOPWORDS default.
        """
        self.stopwords: Set[str] = set(stopwords) if stopwords is not None else set(STOPWORDS)
        logger.debug(f"TextCleaner diinisialisasi dengan {len(self.stopwords)} stopwords.")

    def to_lowercase(self, text: str) -> str:
        """
        Mengonversi teks menjadi huruf kecil.

        Args:
            text: Teks input.

        Returns:
            str: Teks huruf kecil.
        """
        if text is None:
            return ""
        return text.lower()

    def strip_whitespace(self, text: str) -> str:
        """
        Menghilangkan spasi berlebih di awal, akhir, dan menggabungkan spasi ganda di tengah.

        Args:
            text: Teks input.

        Returns:
            str: Teks bersih dari spasi berlebih.
        """
        if not text:
            return ""
        # Trim spasi di awal/akhir, lalu collapse multiple spaces
        cleaned = text.strip()
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned

    def remove_special_characters(self, text: str) -> str:
        """
        Menghapus karakter khusus dan tanda baca, hanya menyisakan huruf, angka, dan spasi.

        Args:
            text: Teks input.

        Returns:
            str: Teks tanpa karakter khusus.
        """
        if not text:
            return ""
        # Hapus semua karakter yang bukan alfanumerik atau spasi
        return re.sub(r'[^a-zA-Z0-9\s]', ' ', text)

    def apply_regex_normalization(self, text: str) -> str:
        """
        Melakukan normalisasi penulisan urutan pertemuan atau istilah penting menggunakan regex.

        Contoh: "Pertemuan ke-1" -> "1", "Minggu Ke - I" -> "1", dsb.

        Args:
            text: Teks input.

        Returns:
            str: Teks yang ternormalisasi.
        """
        if not text:
            return ""
            
        # Sederhanakan angka romawi terlebih dahulu agar menjadi angka desimal
        # (I, II, III, IV, V, VI, VII, VIII, IX, X, ..., XVI)
        roman_map = [
            (r'\bxvi\b', '16'), (r'\bxv\b', '15'), (r'\bxiv\b', '14'), (r'\bxiii\b', '13'),
            (r'\bxii\b', '12'), (r'\bxi\b', '11'), (r'\bx\b', '10'), (r'\bix\b', '9'),
            (r'\bviii\b', '8'), (r'\bvii\b', '7'), (r'\bvi\b', '6'), (r'\bv\b', '5'),
            (r'\biv\b', '4'), (r'\biii\b', '3'), (r'\bii\b', '2'), (r'\bi\b', '1')
        ]
        
        normalized = text
        for roman, arabic in roman_map:
            normalized = re.sub(roman, arabic, normalized, flags=re.IGNORECASE)
            
        # Normalisasi: "pertemuan ke-XX" atau "minggu ke-XX" menjadi hanya angka XX
        # Menggunakan regex case-insensitive (flags=re.IGNORECASE)
        normalized = re.sub(
            r'\b(?:pertemuan|minggu|p-\s*|m-\s*)\s*(?:ke)?[-:\s]*(\d+)\b', 
            r'\1', 
            normalized, 
            flags=re.IGNORECASE
        )
        
        return normalized

    def remove_stopwords(self, text: str) -> str:
        """
        Menghapus stopwords dari teks.

        Args:
            text: Teks input.

        Returns:
            str: Teks tanpa stopwords.
        """
        if not text:
            return ""
            
        words = text.split()
        filtered_words = [w for w in words if w.lower() not in self.stopwords]
        return " ".join(filtered_words)

    def clean(self, text: str) -> str:
        """
        Pipeline utama pembersihan teks.

        Menerapkan seluruh transformasi teks secara berurutan:
        1. lowercase
        2. normalisasi regex
        3. hapus karakter khusus
        4. hapus stopwords
        5. bersihkan whitespace ganda

        Args:
            text: Teks mentah.

        Returns:
            str: Teks hasil pembersihan (cleaned text).

        Raises:
            TextCleaningError: Jika terjadi kesalahan pemrosesan string.
        """
        if text is None:
            return ""
            
        try:
            logger.debug(f"Pembersihan teks dimulai untuk text length: {len(text)}")
            
            # 1. Lowercase
            step1 = self.to_lowercase(text)
            # 2. Regex Normalization
            step2 = self.apply_regex_normalization(step1)
            # 3. Remove Special Characters
            step3 = self.remove_special_characters(step2)
            # 4. Remove Stopwords
            step4 = self.remove_stopwords(step3)
            # 5. Clean Whitespaces
            step5 = self.strip_whitespace(step4)
            
            logger.debug(f"Pembersihan teks selesai.")
            return step5
        except Exception as e:
            logger.exception(f"Gagal melakukan text cleaning: {e}")
            raise TextCleaningError(f"Kesalahan internal pembersihan teks: {e}")
