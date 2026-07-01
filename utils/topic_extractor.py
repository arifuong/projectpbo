"""
Ekstraksi topik utama dari kolom Materi Pembelajaran RPS.

Parser PDF sering mengembalikan satu cell panjang berisi judul, submateri,
aktivitas praktikum, contoh, fokus, dan referensi. Class ini hanya mengambil
pokok bahasan utama yang layak disimpan ke tabel RPS.
"""

import re
from typing import Iterable, List, Optional


class TopicExtractor:
    """
    Mengekstrak judul/pokok bahasan utama dari teks materi RPS.
    """

    DETAIL_KEYWORDS = (
        "buku referensi",
        "reference",
        "referensi",
        "pustaka",
        "contoh",
        "example",
        "latihan",
        "tugas",
        "submateri",
        "sub materi",
        "perbedaan antara",
        "difference between",
        "by giving",
        "some examples",
        "simple example",
        "how to use",
        "membuat program",
        "mencoba program",
        "mendesain program",
        "program yang memanfaatkan",
    )

    HEADING_KEYWORDS = (
        "kontrak kuliah",
        "konsep dasar",
        "classes and object",
        "class and object",
        "enkapsulasi",
        "inheritance",
        "pewarisan",
        "exception handling",
        "object persistence",
        "multithreading",
        "java library",
        "java api",
        "collections",
        "database",
        "gui",
        "swing",
        "polymorphism",
        "polimorfisme",
    )

    DOMAIN_PATTERNS = (
        (r"mencoba\s+program.*buku\s+referensi", "Praktikum Enkapsulasi"),
        (r"program\s+yang\s+memanfaatkan\s+enkapsulasi", "Praktikum Enkapsulasi"),
        (r"mendesain\s+program.*enkapsulasi", "Praktikum Enkapsulasi"),
        (r"classes?\s+and\s+objects?", "Classes and Object"),
        (r"konsep\s+enkapsulasi", "Konsep Enkapsulasi"),
        (r"komponen\s+dalam\s+enkapsulasi", "Konsep Enkapsulasi"),
        (r"konsep\s+pewarisan", "Konsep Pewarisan"),
        (r"exception\s+handling", "Exception Handling"),
        (r"object\s+persistence", "Object Persistence"),
        (r"multithreading", "Multithreading"),
        (r"using\s+java\s+library|java\s+api", "Using Java Library"),
        (r"collections?", "Collections"),
        (r"making\s+connection\s+with\s+database", "Making Connection with Database"),
        (r"gui\s*&\s*swing", "GUI & SWING"),
    )

    def extract_main_topic(self, text: str, context: Optional[Iterable[str]] = None) -> str:
        """
        Mengambil satu judul/pokok bahasan utama dari cell materi.

        Args:
            text: Teks mentah dari cell utama.
            context: Teks pendukung dari kolom lain pada row yang sama.

        Returns:
            str: Topik utama.
        """
        if not text:
            return ""

        domain_topic = self._detect_domain_topic([text, *(context or [])])
        if domain_topic:
            return domain_topic

        lines = self._split_lines(text)
        candidates = self._build_heading_candidates(lines)

        if candidates:
            best_candidate = max(candidates, key=self._score_heading)
            cleaned = self._clean_candidate(best_candidate)
            if self._is_good_heading(cleaned):
                return cleaned

        return self._clean_candidate(lines[0] if lines else text)

    def clean_topic(self, text: str, context: Optional[Iterable[str]] = None) -> str:
        """
        Pipeline lengkap pembersihan topik utama.
        """
        topic = self.extract_main_topic(text, context=context)
        topic = self.remove_focus_note(topic)
        topic = self.remove_parentheses(topic)
        topic = self.remove_numbering(topic)
        topic = self.remove_bullet(topic)
        topic = self.normalize_whitespace(topic)
        topic = self._remove_duplicate_words(topic)
        topic = self._remove_trailing_punctuation(topic)
        return self._title_domain_topic(topic)

    def remove_numbering(self, text: str) -> str:
        """
        Menghapus numbering di awal teks.
        """
        if not text:
            return ""
        text = re.sub(r"^\s*(?:\(?\d+\)?[\.\)]|[a-zA-Z][\.\)])\s*", "", text)
        text = re.sub(r"^\s*(?:[ivxlcdm]+)[\.\)]\s*", "", text, flags=re.IGNORECASE)
        return text.strip()

    def remove_bullet(self, text: str) -> str:
        """
        Menghapus bullet di awal teks.
        """
        if not text:
            return ""
        return re.sub(r"^\s*(?:[•●▪*+-]|â€¢)+\s*", "", text).strip()

    def remove_focus_note(self, text: str) -> str:
        """
        Menghapus catatan fokus/latihan/contoh/submateri/referensi.
        """
        if not text:
            return ""
        return re.sub(
            r"\((?:\s*(?:fokus|focus|latihan|contoh|example|submateri|sub materi|referensi|pustaka|tugas|catatan)\b[^)]*)\)",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()

    def remove_parentheses(self, text: str) -> str:
        """
        Menghapus kurung kosong dan catatan dalam kurung yang tersisa.
        """
        if not text:
            return ""
        text = re.sub(r"\(\s*\)", "", text)
        text = re.sub(r"\s*\((?:[^)]{1,80})\)\s*$", "", text)
        return text.strip()

    def normalize_whitespace(self, text: str) -> str:
        """
        Mengubah newline/tab menjadi spasi tunggal.
        """
        if not text:
            return ""
        text = text.replace("\r", "\n").replace("\t", " ")
        return re.sub(r"\s+", " ", text).strip()

    def _split_lines(self, text: str) -> List[str]:
        text = text.replace("\r", "\n")
        normalized = re.sub(r"\s*/\s*", "\n", text)
        raw_lines = normalized.split("\n")
        lines = []
        for line in raw_lines:
            cleaned = self._clean_candidate(line)
            if cleaned:
                lines.append(cleaned)
        return lines

    def _build_heading_candidates(self, lines: List[str]) -> List[str]:
        candidates = []
        for idx, line in enumerate(lines):
            lowered = line.lower()
            if self._is_detail_line(lowered):
                continue
            if idx == 0 or self._looks_like_heading(line):
                candidates.append(line)
        return candidates

    def _clean_candidate(self, text: str) -> str:
        text = self.normalize_whitespace(text)
        text = self.remove_bullet(text)
        text = self.remove_numbering(text)
        text = self.remove_focus_note(text)
        text = self.remove_parentheses(text)
        text = self.normalize_whitespace(text)
        return self._remove_trailing_punctuation(text)

    def _detect_domain_topic(self, texts: Iterable[str]) -> str:
        combined = " ".join(self.normalize_whitespace(t or "") for t in texts)
        for pattern, topic in self.DOMAIN_PATTERNS:
            if re.search(pattern, combined, flags=re.IGNORECASE):
                return topic
        return ""

    def _looks_like_heading(self, line: str) -> bool:
        lowered = line.lower()
        if any(keyword in lowered for keyword in self.HEADING_KEYWORDS):
            return True
        if len(line.split()) <= 5 and not self._is_detail_line(lowered):
            return True
        return False

    def _is_detail_line(self, lowered_line: str) -> bool:
        return any(keyword in lowered_line for keyword in self.DETAIL_KEYWORDS)

    def _score_heading(self, line: str) -> int:
        lowered = line.lower()
        score = 0
        if any(keyword in lowered for keyword in self.HEADING_KEYWORDS):
            score += 20
        if len(line.split()) <= 5:
            score += 10
        if self._is_detail_line(lowered):
            score -= 30
        if line.endswith(":"):
            score += 2
        return score

    def _is_good_heading(self, text: str) -> bool:
        if not text:
            return False
        lowered = text.lower()
        if self._is_detail_line(lowered):
            return False
        return len(text.split()) <= 8 or any(k in lowered for k in self.HEADING_KEYWORDS)

    def _remove_trailing_punctuation(self, text: str) -> str:
        return re.sub(r"\s*[:;,.\-]+\s*$", "", text or "").strip()

    def _remove_duplicate_words(self, text: str) -> str:
        return re.sub(r"\b(\w+)\s+\1\b", r"\1", text or "", flags=re.IGNORECASE).strip()

    def _title_domain_topic(self, text: str) -> str:
        replacements = {
            "exception handling": "Exception Handling",
            "object persistence": "Object Persistence",
            "multithreading": "Multithreading",
            "collections": "Collections",
            "gui & swing": "GUI & SWING",
            "konsep enkapsulasi": "Konsep Enkapsulasi",
            "konsep pewarisan": "Konsep Pewarisan",
            "praktikum enkapsulasi": "Praktikum Enkapsulasi",
        }
        lowered = text.lower()
        return replacements.get(lowered, text)
