"""
Modul KeywordMatcher untuk Sistem Validasi RPS-BAP.

Modul ini mengimplementasikan pencocokan kata kunci dan perhitungan
skor kemiripan (similarity score) antara materi BAP dan Pokok Bahasan RPS.
Menggunakan kombinasi metode Token Overlap dan difflib SequenceMatcher.

Sesuai PRD Section 4.7 - Modul Keyword Matching.
"""

import difflib
from typing import Set, Dict, Any, List
from config.constants import DEFAULT_SIMILARITY_THRESHOLD
from utils.logger import setup_logger

# Inisialisasi logger untuk KeywordMatcher
logger = setup_logger(__name__)


class KeywordMatcher:
    """
    Class untuk mencocokkan kata kunci dan menghitung kemiripan teks.

    Menerapkan pembandingan string case-insensitive, tokenisasi kata,
    token overlap, dan pencocokan urutan karakter (difflib).

    Attributes:
        threshold (float): Ambang batas kemiripan untuk dinyatakan "Sesuai".
    """

    def __init__(self, threshold: float = DEFAULT_SIMILARITY_THRESHOLD) -> None:
        """
        Inisialisasi KeywordMatcher.

        Args:
            threshold: Ambang batas skor kemiripan (0.0 - 1.0).
        """
        self.threshold: float = threshold
        logger.debug(f"KeywordMatcher diinisialisasi dengan threshold: {self.threshold}")

    def extract_keywords(self, text: str) -> Set[str]:
        """
        Mengekstrak kata kunci unik (tokens) dari teks yang telah dibersihkan.

        Args:
            text: Teks yang sudah bersih dari stopwords dan karakter khusus.

        Returns:
            Set[str]: Set kata kunci unik.
        """
        if not text:
            return set()
        
        # Pisahkan kata berdasarkan spasi
        words = text.split()
        
        # Filter kata kosong atau sangat pendek
        keywords = {word.strip() for word in words if len(word.strip()) > 1}
        return keywords

    def calculate_similarity(self, text_bap: str, text_rps: str) -> float:
        """
        Menghitung nilai kemiripan (similarity score) gabungan antara BAP dan RPS.

        Kombinasi 2 metode:
        1. Token Overlap (Jaccard-like): rasio kata yang sama terhadap total kata.
        2. Sequence Similarity (difflib): kemiripan susunan karakter.
        Gabungan dihitung dengan bobot: 60% Token Overlap dan 40% Sequence Similarity.

        Args:
            text_bap: Teks BAP yang bersih.
            text_rps: Teks RPS yang bersih.

        Returns:
            float: Nilai kemiripan antara 0.0 sampai 1.0.
        """
        if not text_bap or not text_rps:
            return 0.0

        # 1. Hitung Token Overlap
        tokens_bap = self.extract_keywords(text_bap)
        tokens_rps = self.extract_keywords(text_rps)

        if not tokens_bap or not tokens_rps:
            return 0.0

        intersection = tokens_bap.intersection(tokens_rps)
        # Formula Jaccard: |A n B| / |A u B|
        union = tokens_bap.union(tokens_rps)
        token_overlap_score = len(intersection) / len(union) if union else 0.0

        # 2. Hitung Sequence Similarity (difflib)
        seq_matcher = difflib.SequenceMatcher(None, text_bap, text_rps)
        seq_score = seq_matcher.ratio()

        # 3. Gabungan dengan bobot
        combined_score = (0.6 * token_overlap_score) + (0.4 * seq_score)
        
        logger.debug(
            f"Kalkulasi kemiripan - overlap: {token_overlap_score:.4f}, "
            f"sequence: {seq_score:.4f}, combined: {combined_score:.4f}"
        )
        return combined_score

    def is_match(self, similarity_score: float) -> bool:
        """
        Memeriksa apakah skor kemiripan memenuhi threshold.

        Args:
            similarity_score: Skor kemiripan (0.0 - 1.0).

        Returns:
            bool: True jika skor >= threshold, False jika tidak.
        """
        return similarity_score >= self.threshold

    def match(self, text_bap: str, text_rps: str) -> Dict[str, Any]:
        """
        Menghasilkan detail pencocokan kata kunci lengkap.

        Args:
            text_bap: Teks BAP.
            text_rps: Teks RPS.

        Returns:
            Dict[str, Any]: Detail hasil pencocokan. Keys:
                "similarity_score" (float): 0.0 - 1.0.
                "is_match" (bool): True/False.
                "matched_keywords" (List[str]): Kata-kata yang cocok.
                "unmatched_keywords" (List[str]): Kata-kata BAP yang tidak ada di RPS.
        """
        similarity_score = self.calculate_similarity(text_bap, text_rps)
        is_match_val = self.is_match(similarity_score)

        tokens_bap = self.extract_keywords(text_bap)
        tokens_rps = self.extract_keywords(text_rps)

        matched_keywords = sorted(list(tokens_bap.intersection(tokens_rps)))
        unmatched_keywords = sorted(list(tokens_bap.difference(tokens_rps)))

        return {
            "similarity_score": similarity_score,
            "is_match": is_match_val,
            "matched_keywords": matched_keywords,
            "unmatched_keywords": unmatched_keywords
        }
