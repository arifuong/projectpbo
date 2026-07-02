"""
Modul KeywordMatcher untuk Sistem Validasi RPS-BAP.

Modul ini mengimplementasikan pencocokan kata kunci dan perhitungan
skor kemiripan (similarity score) antara materi BAP dan Pokok Bahasan RPS.
Menggunakan RapidFuzz token_set_ratio untuk semantic text matching.
"""

import re
from typing import Set, Dict, Any, List, Optional
from config.constants import DEFAULT_SIMILARITY_THRESHOLD
from utils.logger import setup_logger

# Inisialisasi logger untuk KeywordMatcher
logger = setup_logger(__name__)


class KeywordMatcher:
    """
    Class untuk mencocokkan kata kunci dan menghitung kemiripan teks.
    Menggunakan RapidFuzz fuzzy token_set_ratio.
    """

    def __init__(self, threshold: float = 0.8) -> None:
        """
        Inisialisasi KeywordMatcher.

        Args:
            threshold: Ambang batas skor kemiripan (0.0 - 1.0). Default 0.8 (80%).
        """
        self.threshold: float = threshold
        logger.debug(f"KeywordMatcher diinisialisasi dengan threshold: {self.threshold}")

    def _semantic_normalize(self, text: str) -> str:
        """
        Melakukan normalisasi teks secara semantik.
        """
        if not text:
            return ""
        # Gabungkan line break menjadi satu kalimat
        text = text.replace('\n', ' ').replace('\r', ' ')
        # Lowercase
        text = text.lower()
        # Hilangkan numbering
        text = re.sub(r'\b\d+[\.\)\-]\s*', ' ', text)
        # Hilangkan bullets
        text = re.sub(r'[\u2022\-\*\u25aa\u25ab\u25c6\u25cb\u25cf\u25a0\u25c8\u25ae\u27a2\u2714]', ' ', text)
        # Hilangkan tanda baca/karakter khusus, sisakan huruf dan angka
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        # Hilangkan multiple whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _split_subtopics(self, sub_text: str) -> List[str]:
        """
        Memisahkan subtopik menjadi list of string jika berbentuk poin-poin.
        """
        if not sub_text:
            return []
        lines = sub_text.split('\n')
        items = []
        for line in lines:
            cleaned = line.strip()
            if cleaned:
                items.append(cleaned)
        # Dukungan jika numbering di baris tunggal (contoh: 1. A 2. B)
        if len(items) == 1 and re.search(r'\b\d+[\.\)]\s+', items[0]):
            parts = re.split(r'\b\d+[\.\)]\s+', items[0])
            items = [p.strip() for p in parts if p.strip()]
        return items

    def extract_keywords(self, text: str) -> Set[str]:
        """
        Mengekstrak kata kunci unik (tokens) dari teks.
        """
        if not text:
            return set()
        words = text.split()
        keywords = {word.strip() for word in words if len(word.strip()) > 1}
        return keywords

    def calculate_similarity(self, text_bap: str, text_rps: str) -> float:
        """
        Menghitung nilai kemiripan menggunakan fuzzy token_set_ratio.
        """
        if not text_bap or not text_rps:
            return 0.0
        norm_bap = self._semantic_normalize(text_bap)
        norm_rps = self._semantic_normalize(text_rps)
        if not norm_bap or not norm_rps:
            return 0.0
        from rapidfuzz import fuzz
        score = float(fuzz.token_set_ratio(norm_bap, norm_rps))
        return score / 100.0

    def is_match(self, similarity_score: float) -> bool:
        """
        Memeriksa apakah skor kemiripan memenuhi threshold.
        """
        return similarity_score >= self.threshold

    def match(self, text_bap: str, text_topic: str, text_sub_topic: Optional[str] = None) -> Dict[str, Any]:
        """
        Menghasilkan detail pencocokan menggunakan fuzzy matching.
        Membandingkan materi BAP dengan pokok bahasan (topic) dan sub-pokok bahasan (sub_topic).
        """
        from rapidfuzz import fuzz

        norm_bap = self._semantic_normalize(text_bap)
        norm_topic = self._semantic_normalize(text_topic)
        
        sub_items = self._split_subtopics(text_sub_topic)
        norm_subs = [self._semantic_normalize(item) for item in sub_items if item]

        best_score = 0.0
        best_match_text = text_topic

        # Cek main topic
        if norm_topic:
            score = float(fuzz.token_set_ratio(norm_bap, norm_topic))
            if score > best_score:
                best_score = score
                best_match_text = text_topic

        # Cek sub topics
        for idx, norm_sub in enumerate(norm_subs):
            score = float(fuzz.token_set_ratio(norm_bap, norm_sub))
            if score > best_score:
                best_score = score
                best_match_text = sub_items[idx]

        similarity_score = best_score / 100.0
        is_match_val = self.is_match(similarity_score)
        status_str = "MATCH" if is_match_val else "TIDAK_DITEMUKAN"

        # Cetak log sesuai format yang diinginkan user
        logger.info(
            f"\nRPS : {best_match_text}\n"
            f"BAP : {text_bap}\n"
            f"Similarity : {best_score:.0f}%\n"
            f"Status : {status_str}\n"
        )

        tokens_bap = self.extract_keywords(text_bap)
        tokens_rps = self.extract_keywords(text_topic)
        matched_keywords = sorted(list(tokens_bap.intersection(tokens_rps)))
        unmatched_keywords = sorted(list(tokens_bap.difference(tokens_rps)))

        return {
            "similarity_score": similarity_score,
            "is_match": is_match_val,
            "matched_keywords": matched_keywords,
            "unmatched_keywords": unmatched_keywords
        }
