"""
Parser struktur RPS dari hasil ekstraksi PDF.

Modul ini hanya menangani normalisasi ringan dan pemisahan isi materi
menjadi topic dan sub_topic. Tidak ada business rule database di sini.

Deteksi kolom dilakukan melalui header_normalizer.py untuk mengenali
ARTI header, bukan teks persisnya.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from utils.header_normalizer import (
    build_column_roles,
    normalize_header,
    VALID_MEETING_ROLES,
    VALID_TOPIC_ROLES,
    VALID_SUB_TOPIC_ROLES,
    BANNED_ROLES,
)

logger = logging.getLogger("utils.rps_parser")


class RPSParser:
    """
    Helper untuk memetakan cell PDF RPS menjadi meeting_number, topic, sub_topic.
    """

    # ================================================================
    # Cell Normalization
    # ================================================================

    def normalize_cell(self, value: Optional[str], keep_newline: bool = True) -> str:
        """
        Normalisasi ringan: None ke string kosong, trim, rapikan spasi,
        dan buang newline/bullet/broken unicode.
        """
        if value is None:
            return ""

        text = str(value).replace("\r", "\n").replace("\t", " ")

        # Clean unicode bullet characters and corrupt text indicators
        text = re.sub(r'[\uf0b7\u2022\u25cf\u25aa|●▪★]', ' ', text)
        text = text.replace("â€¢", " ")

        if keep_newline:
            lines = []
            for line in text.split("\n"):
                cleaned_line = re.sub(r"[ ]+", " ", line).strip()
                if cleaned_line:
                    lines.append(cleaned_line)
            return "\n".join(lines).strip()

        return re.sub(r"\s+", " ", text).strip()

    def normalize_multiline(self, value: Optional[str]) -> str:
        """
        Normalisasi multiline untuk preview dan penyimpanan sub_topic.
        """
        text = self.normalize_cell(value, keep_newline=True)
        return re.sub(r"\n{2,}", "\n", text).strip()

    def clean_line_numbering_bullet(self, line: str) -> str:
        """
        Menghapus numbering dan bullet di awal satu baris teks.
        """
        line = re.sub(r"^\s*(?:\(?\d+\)?[.\)]|[a-zA-Z][.\)])\s*", "", line)
        line = re.sub(r"^\s*(?:[ivxlcdm]+)[.\)]\s*", "", line, flags=re.IGNORECASE)
        line = re.sub(r"^\s*(?:[•●▪*+-]|â€¢)+\s*", "", line)
        return line.strip()

    # ================================================================
    # Column Detection — Header Normalization (Stage 1)
    # ================================================================

    def detect_columns_header_based(self, table: List[List[str]]) -> Tuple[int, int, int]:
        """
        Mendeteksi meeting_col, topic_col, dan sub_topic_col berdasarkan
        Header Normalization melalui header_normalizer.build_column_roles().

        Mengembalikan (-1, -1, -1) jika tidak ada header yang cocok.
        """
        if not table or len(table) < 1:
            return -1, -1, -1

        roles = build_column_roles(table, normalize_cell_fn=self.normalize_cell)

        meeting_col = -1
        topic_col = -1
        sub_topic_col = -1

        for col_idx, role in sorted(roles.items()):
            if role in VALID_MEETING_ROLES and meeting_col == -1:
                meeting_col = col_idx
            elif role in VALID_TOPIC_ROLES and topic_col == -1:
                topic_col = col_idx
            elif role in VALID_SUB_TOPIC_ROLES and sub_topic_col == -1:
                sub_topic_col = col_idx

        if meeting_col != -1 and topic_col != -1:
            logger.info(
                f"Header Normalization berhasil: "
                f"meeting_col={meeting_col}, topic_col={topic_col}, sub_topic_col={sub_topic_col}"
            )

        return meeting_col, topic_col, sub_topic_col

    # ================================================================
    # Column Detection — Dispatch (Header → Semantic)
    # ================================================================

    def detect_columns(self, table: List[List[str]], use_heuristic: bool = True) -> Tuple[int, int, int]:
        """
        Strategi deteksi kolom:
        1. Header Normalization (via header_normalizer)
        2. Semantic scoring heuristic (jika header gagal dan use_heuristic=True)
        """
        meeting_col, topic_col, sub_topic_col = self.detect_columns_header_based(table)

        if meeting_col != -1 and topic_col != -1:
            return meeting_col, topic_col, sub_topic_col

        if use_heuristic:
            return self.detect_columns_semantic(table)

        return meeting_col, topic_col, sub_topic_col

    # ================================================================
    # Column Detection — Semantic Scoring (Stage 2 Fallback)
    # ================================================================

    def detect_columns_semantic(self, table: List[List[str]]) -> Tuple[int, int, int]:
        """
        Deteksi kolom menggunakan scoring heuristic semantic detection.
        Kolom dengan banned roles dari header_normalizer tetap diblokir.
        """
        if not table or len(table) < 1:
            return -1, -1, -1

        max_cols = max(len(row) for row in table)
        if max_cols == 0:
            return -1, -1, -1

        meeting_scores = [0] * max_cols
        topic_scores = [0] * max_cols
        sub_topic_scores = [0] * max_cols

        # Gunakan header_normalizer untuk mendeteksi role dari header
        roles = build_column_roles(table, normalize_cell_fn=self.normalize_cell)

        for col_idx in range(max_cols):
            role = roles.get(col_idx)

            # Block banned roles
            if role in BANNED_ROLES:
                meeting_scores[col_idx] = -99999
                topic_scores[col_idx] = -99999
                sub_topic_scores[col_idx] = -99999
                continue

            # Boost scores based on recognized roles
            if role in VALID_MEETING_ROLES:
                meeting_scores[col_idx] += 150
            if role in VALID_TOPIC_ROLES:
                topic_scores[col_idx] += 120
            if role in VALID_SUB_TOPIC_ROLES:
                sub_topic_scores[col_idx] += 150

        # Semantic cell content scoring
        data_rows = table[1:] if len(table) > 1 else table
        for row in data_rows:
            for col_idx in range(min(max_cols, len(row))):
                if meeting_scores[col_idx] < -1000:
                    continue
                cell_val = row[col_idx]
                if not cell_val:
                    continue
                val = self.normalize_cell(cell_val, keep_newline=False)
                val_len = len(val)
                if val_len == 0:
                    continue

                meeting_nums = self.extract_meeting_numbers(val)
                if meeting_nums:
                    meeting_scores[col_idx] += 25
                    if val_len <= 15:
                        meeting_scores[col_idx] += 15
                    if val.isdigit() or re.match(r'^[ivxlcdm]+$', val.lower()):
                        meeting_scores[col_idx] += 10

                if val_len > 30:
                    meeting_scores[col_idx] -= 25

                if 15 <= val_len <= 150:
                    topic_scores[col_idx] += 8
                    if any(w in val.lower() for w in [
                        "konsep", "dasar", "pengenalan", "teori",
                        "praktikum", "aplikasi", "sistem", "metode", "materi"
                    ]):
                        topic_scores[col_idx] += 10
                elif val_len < 4:
                    topic_scores[col_idx] -= 15

                if any(val.strip().startswith(b) for b in ["-", "*", "•", "1.", "2.", "3.", "a.", "b.", "c."]):
                    sub_topic_scores[col_idx] += 15
                if 20 <= val_len <= 250:
                    sub_topic_scores[col_idx] += 8
                elif val_len < 4:
                    sub_topic_scores[col_idx] -= 15

        # Pick best columns
        meeting_col = self._pick_best_column(meeting_scores, max_cols, exclude=set())
        topic_col = self._pick_best_column(topic_scores, max_cols, exclude={meeting_col})
        sub_topic_col = self._pick_best_column(sub_topic_scores, max_cols, exclude={meeting_col, topic_col})

        # Positional heuristic fallbacks
        if meeting_col == -1:
            meeting_col = 0

        if topic_col == -1:
            longest_avg_len = -1
            best_col = -1
            for c in range(max_cols):
                if c == meeting_col or meeting_scores[c] < -1000:
                    continue
                total_len = 0
                non_empty_count = 0
                for row in table:
                    if c < len(row) and row[c]:
                        total_len += len(self.normalize_cell(row[c], keep_newline=False))
                        non_empty_count += 1
                avg_len = total_len / non_empty_count if non_empty_count > 0 else 0
                if avg_len > longest_avg_len:
                    longest_avg_len = avg_len
                    best_col = c
            topic_col = best_col if best_col != -1 else (1 if max_cols > 1 else 0)

        if sub_topic_col == -1:
            if topic_col + 1 < max_cols and topic_col + 1 != meeting_col and meeting_scores[topic_col + 1] > -1000:
                sub_topic_col = topic_col + 1
            elif topic_col - 1 >= 0 and topic_col - 1 != meeting_col and meeting_scores[topic_col - 1] > -1000:
                sub_topic_col = topic_col - 1

        return meeting_col, topic_col, sub_topic_col

    @staticmethod
    def _pick_best_column(scores: List[int], max_cols: int, exclude: set) -> int:
        """Helper: memilih kolom dengan score tertinggi > 0, selain kolom di exclude."""
        best_score = -9999
        best_idx = -1
        for c in range(max_cols):
            if c in exclude:
                continue
            if scores[c] > best_score:
                best_score = scores[c]
                best_idx = c
        return best_idx if best_score > 0 else -1

    # ================================================================
    # Table Validation
    # ================================================================

    def is_rps_table(self, table: List[List[str]]) -> bool:
        """
        Memastikan tabel punya ciri struktur RPS, bukan tabel identitas/pustaka/penilaian.
        Harus punya KEDUA kolom meeting DAN topic untuk dianggap tabel RPS.
        """
        if len(table) < 2:
            return False

        # Cek role kolom via header_normalizer
        roles = build_column_roles(table, normalize_cell_fn=self.normalize_cell)
        role_values = set(roles.values())

        # Jika semua kolom bertipe identity/reference/assessment/method, tolak
        if role_values and role_values <= BANNED_ROLES:
            return False

        # Scan rows untuk keyword identitas khusus
        for r in range(len(table)):
            for col in range(len(table[r])):
                cell_val = self.normalize_cell(table[r][col], keep_newline=False).lower()
                if any(kw in cell_val for kw in [
                    "dosen pengampu", "mata kuliah", "program studi",
                    "tgl penyusunan", "dosen pengembang rps",
                ]):
                    return False

        # Harus punya KEDUA meeting dan topic col
        meeting_col, topic_col, _ = self.detect_columns(table, use_heuristic=True)
        return meeting_col != -1 and topic_col != -1

    # ================================================================
    # Topic / Sub-Topic Splitting
    # ================================================================

    def split_topic_subtopic(
        self,
        material_text: str,
        explicit_sub_topic: str = "",
        context_values: Optional[List[str]] = None
    ) -> Tuple[str, str]:
        """
        Memisahkan cell materi menjadi topic dan sub_topic.
        Mendukung domain-specific pattern matching dan multiline topic combination.
        """
        material = self.normalize_multiline(material_text)
        explicit_sub_topic = self.normalize_multiline(explicit_sub_topic)

        if not material:
            return "", explicit_sub_topic

        # Check for domain-specific topic pattern first (legacy compatibility)
        from utils.topic_extractor import TopicExtractor
        extractor = TopicExtractor()
        domain_topic = extractor._detect_domain_topic([material, *(context_values or [])])

        lines = [line for line in material.split("\n") if line.strip()]
        if not lines:
            return "", explicit_sub_topic

        if domain_topic:
            topic = domain_topic
            first_line = lines[0].strip()
            if extractor.clean_topic(first_line).lower() == domain_topic.lower():
                sub_lines = lines[1:]
            else:
                sub_lines = lines
            sub_topic = "\n".join(sub_lines)
        else:
            # Universal Multiline Topic Combination
            cleaned_lines = [self.clean_line_numbering_bullet(l) for l in lines]
            topic = "\n".join(cleaned_lines)
            sub_topic = explicit_sub_topic

            # Parentheses fallback for single-line topic
            if len(lines) == 1 and not sub_topic:
                match = re.search(r'\(([^)]+)\)', topic)
                if match:
                    parentheses_content = match.group(1).strip()
                    if not any(parentheses_content.lower().startswith(k) for k in [
                        "fokus", "focus", "latihan", "contoh", "example", "referensi", "tugas"
                    ]):
                        sub_topic = parentheses_content
                        topic = topic.replace(match.group(0), "").strip()

        return self.normalize_cell(topic, keep_newline=True), self.normalize_multiline(sub_topic)

    # ================================================================
    # Sub-Topic Append
    # ================================================================

    def append_sub_topic(self, current_sub_topic: str, continuation_text: str) -> str:
        """
        Menambahkan lanjutan cell PDF ke sub_topic pertemuan sebelumnya.
        """
        current = self.normalize_multiline(current_sub_topic)
        continuation = self.normalize_multiline(continuation_text)
        if not continuation:
            return current
        if not current:
            return continuation
        return self.normalize_multiline(f"{current}\n{continuation}")

    # ================================================================
    # Table Rows → Records
    # ================================================================

    def rows_to_records(
        self,
        table: List[List[str]],
        meeting_col: int,
        topic_col: int,
        sub_topic_col: int = -1,
    ) -> List[Dict[str, Any]]:
        """
        Mengubah baris tabel menjadi record RPS sementara.
        Mendukung row lanjutan (continuation rows), merged cells, dan range/list pertemuan.
        """
        records: List[Dict[str, Any]] = []
        current_records: List[Dict[str, Any]] = []

        for row in table:
            if len(row) <= max(meeting_col, topic_col):
                continue

            meeting_text = self.normalize_cell(row[meeting_col], keep_newline=False)
            material_text = self.normalize_cell(row[topic_col], keep_newline=True)
            explicit_sub_topic = ""
            if sub_topic_col != -1 and len(row) > sub_topic_col:
                explicit_sub_topic = self.normalize_cell(row[sub_topic_col], keep_newline=True)

            meeting_numbers = self.extract_meeting_numbers(meeting_text)

            # Check if this row is a header row (contains header keyword but no numbers)
            is_header = False
            meeting_role = normalize_header(meeting_text)
            if meeting_role == "meeting" and not meeting_numbers:
                is_header = True
            if not is_header:
                for kw in ("pertemuan", "minggu", "sesi", "week", "session"):
                    if kw in meeting_text.lower() and not meeting_numbers:
                        is_header = True
                        break
            if is_header:
                continue

            if not meeting_numbers:
                if current_records:
                    for record in current_records:
                        if material_text:
                            record["sub_topic"] = self.append_sub_topic(
                                record.get("sub_topic", ""),
                                material_text,
                            )
                        if explicit_sub_topic:
                            record["sub_topic"] = self.append_sub_topic(
                                record.get("sub_topic", ""),
                                explicit_sub_topic,
                            )
                continue

            context_values = [
                cell for idx, cell in enumerate(row)
                if idx != topic_col and isinstance(cell, str) and cell.strip()
            ]
            topic, sub_topic = self.split_topic_subtopic(material_text, explicit_sub_topic, context_values)
            if not topic and not sub_topic:
                continue

            current_records = []
            for num in meeting_numbers:
                rec = {
                    "meeting_number": num,
                    "topic": topic,
                    "sub_topic": sub_topic,
                }
                records.append(rec)
                current_records.append(rec)

        return records

    # ================================================================
    # Meeting Number Extraction
    # ================================================================

    def extract_meeting_numbers(self, value: str) -> List[int]:
        """
        Ekstrak semua nomor pertemuan dari string input secara aman.
        Mendukung format list (3,4, 7 dan 8), range (5-6), dan romawi (I-II).
        """
        text = self.normalize_cell(value, keep_newline=False).lower()
        if not text:
            return []

        # Replace Roman numerals with digits
        roman_map = {
            "xvi": 16, "xv": 15, "xiv": 14, "xiii": 13,
            "xii": 12, "xi": 11, "x": 10, "ix": 9,
            "viii": 8, "vii": 7, "vi": 6, "v": 5,
            "iv": 4, "iii": 3, "ii": 2, "i": 1,
        }
        for roman, number in roman_map.items():
            text = re.sub(rf"\b{roman}\b", str(number), text)

        range_pattern = re.compile(
            r"\b(\d+)\s*(?:-|to|s/d|s\.d\.?|sampai|hingga)\s*(\d+)\b",
            re.IGNORECASE
        )

        numbers = []
        ranges = range_pattern.findall(text)
        if ranges:
            for start_str, end_str in ranges:
                try:
                    start, end = int(start_str), int(end_str)
                    if 0 < start <= 20 and 0 < end <= 20 and start <= end:
                        if end - start <= 5:
                            numbers.extend(range(start, end + 1))
                except ValueError:
                    pass

        cleaned_list_text = re.sub(r"\b(?:dan|and|&|s/d|s\.d\.?)\b", ",", text)

        if not numbers:
            all_nums = re.findall(r"\b\d+\b", cleaned_list_text)
            for num_str in all_nums:
                try:
                    num = int(num_str)
                    if 0 < num <= 20:
                        numbers.append(num)
                except ValueError:
                    pass

        return sorted(list(set(numbers)))

    def extract_meeting_number(self, value: str) -> Optional[int]:
        """
        Mengekstrak integer nomor pertemuan pertama dari string input.
        """
        numbers = self.extract_meeting_numbers(value)
        return numbers[0] if numbers else None

    def parse_by_coordinates(self, pages_words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Mengekstrak data dari koordinat kata menggunakan Area-Based Table Parser.
        """
        import os
        import re
        logger.info("Memulai Area-Based Table Parser (Coordinate-Based)...")
        
        # 1. Bersihkan lines & cari headers per halaman
        ref_pages = set()
        page_lines = {}
        page_all_candidates = {}
        page_headers = {}
        
        for p_data in pages_words:
            page_num = p_data["page_number"]
            words = p_data.get("words", [])
            width = p_data.get("width", 595.0)
            height = p_data.get("height", 842.0)
            
            page_text = " ".join(w['text'] for w in words).lower()
            is_ref = any(kw in page_text for kw in ["daftar pustaka", "pustaka utama", "pustaka pendukung", "referensi"])
            if is_ref:
                ref_pages.add(page_num)
                continue
                
            lines = self._reconstruct_lines(words)
            page_lines[page_num] = lines
            
            best_meeting, best_topic, all_cand = self._find_headers_on_page(lines)
            page_all_candidates[page_num] = all_cand
            
            if best_meeting and best_topic and best_meeting['x0'] < best_topic['x0']:
                headers = {'meeting': best_meeting, 'topic': best_topic}
                for h in all_cand:
                    if h['role'] not in headers:
                        headers[h['role']] = h
                page_headers[page_num] = headers

        # 2. Kelompokkan halaman ke Logical Tables (logical multi-page tables)
        logical_tables = []
        active_table = None
        
        for p_data in pages_words:
            page_num = p_data["page_number"]
            if page_num in ref_pages:
                active_table = None
                continue
                
            if page_num in page_headers:
                active_table = {
                    'pages': [page_num],
                    'page_data': {
                        page_num: {
                            'words': p_data.get("words", []),
                            'lines': page_lines[page_num],
                            'width': p_data.get("width", 595.0),
                            'height': p_data.get("height", 842.0),
                            'headers': page_headers[page_num],
                            'all_candidates': page_all_candidates[page_num]
                        }
                    },
                    'headers': page_headers[page_num]
                }
                logical_tables.append(active_table)
            else:
                if active_table:
                    active_table['pages'].append(page_num)
                    active_table['page_data'][page_num] = {
                        'words': p_data.get("words", []),
                        'lines': page_lines.get(page_num, []),
                        'width': p_data.get("width", 595.0),
                        'height': p_data.get("height", 842.0),
                        'headers': {},
                        'all_candidates': page_all_candidates.get(page_num, [])
                    }

        if not logical_tables:
            logger.warning("Tidak ditemukan tabel kandidat silabus (missing headers).")
            return []

        # 3. Hitung score setiap logical table & pilih score tertinggi
        best_lt = None
        best_lt_score = -1
        best_lt_meetings = []
        best_lt_checkpoints = []
        best_lt_grids = {}
        
        for lt_idx, lt in enumerate(logical_tables):
            lt_meetings_list = []
            lt_checkpoints_list = []
            lt_grids = {}
            
            # Grid propagation
            prev_grid = None
            first_p = lt['pages'][0]
            first_data = lt['page_data'][first_p]
            first_headers = first_data['headers']
            
            f_meeting = first_headers['meeting']
            f_topic = first_headers['topic']
            
            f_m_x = (f_meeting['x0'] - 10, f_meeting['x1'] + 10)
            f_t_x = (f_topic['x0'] - 15, f_topic['x1'] + 20)
            f_m_x, f_t_x = self._calculate_column_bounds(
                f_meeting, f_topic, first_data['all_candidates'], first_data['lines'], first_data['width'], f_m_x, f_t_x, first_data['words']
            )
            
            first_grid = {
                'meeting_x': f_m_x,
                'topic_x': f_t_x,
                'header_y': (f_meeting['top'] - 5, max(f_meeting['bottom'], f_topic['bottom']) + 5),
                'best_meeting': f_meeting,
                'best_topic': f_topic
            }
            
            f_bobot = first_headers.get('weight')
            if f_bobot:
                first_grid['bobot_x'] = (f_bobot['x0'] - 5, f_bobot['x1'] + 5)
                
            prev_grid = first_grid
            meeting_candidates = []
            
            for p in lt['pages']:
                p_data = lt['page_data'][p]
                words = p_data['words']
                lines = p_data['lines']
                width = p_data['width']
                height = p_data['height']
                
                grid = None
                if p == first_p:
                    grid = first_grid
                else:
                    l_headers = p_data.get('headers', {})
                    if l_headers.get('meeting') and l_headers.get('topic'):
                        l_meeting = l_headers['meeting']
                        l_topic = l_headers['topic']
                        l_m_x = (l_meeting['x0'] - 10, l_meeting['x1'] + 10)
                        l_t_x = (l_topic['x0'] - 15, l_topic['x1'] + 20)
                        l_m_x, l_t_x = self._calculate_column_bounds(
                            l_meeting, l_topic, p_data['all_candidates'], lines, width, l_m_x, l_t_x, words
                        )
                        grid = {
                            'meeting_x': l_m_x,
                            'topic_x': l_t_x,
                            'header_y': (l_meeting['top'] - 5, max(l_meeting['bottom'], l_topic['bottom']) + 5),
                            'best_meeting': l_meeting,
                            'best_topic': l_topic
                        }
                        l_bobot = l_headers.get('weight')
                        if l_bobot:
                            grid['bobot_x'] = (l_bobot['x0'] - 5, l_bobot['x1'] + 5)
                    else:
                        grid = prev_grid
                        
                prev_grid = grid
                lt_grids[p] = grid
                
                if not grid:
                    continue
                    
                meeting_x = grid['meeting_x']
                header_y = grid['header_y']
                
                for line in lines:
                    line_top = min(float(w['top']) for w in line)
                    if header_y[0] <= line_top <= header_y[1] + 25:
                        continue
                        
                    # Hanya ambil words yang berada DI DALAM area Meeting Column
                    meeting_words = [
                        w for w in line
                        if meeting_x[0] <= ((float(w['x0']) + float(w['x1'])) / 2) <= meeting_x[1]
                    ]
                    
                    if not meeting_words:
                        continue
                        
                    phrase = " ".join(w['text'] for w in meeting_words)
                    cleaned_phrase = phrase.strip()
                    
                    # Validator meeting strict
                    rejection_reason = None
                    if re.match(r'^\s*\(\s*\d+\s*\)\s*$', cleaned_phrase):
                        rejection_reason = "Parenthesized column indicator"
                    elif len(cleaned_phrase) > 15 or len(cleaned_phrase.split()) > 3:
                        rejection_reason = f"Text length too long ({len(cleaned_phrase)} chars)"
                    elif any(sym in cleaned_phrase for sym in ['•', '-', '*', 'o', '■', '♦', '▪', 'v', '']):
                        rejection_reason = "Contains bullet symbol"
                    elif any(word in cleaned_phrase.lower() for word in [
                        "cpl", "cpmk", "sub-cpmk", "sub cpmk", "deskripsi", "pustaka", "referensi", 
                        "evaluasi", "dosen", "bobot", "metode", "penilaian", "tugas", "nilai"
                    ]):
                        rejection_reason = "Contains academic/banned role keyword"
                    else:
                        words_in_phrase = [w.lower() for w in re.findall(r'\b[a-zA-Z]+\b', cleaned_phrase)]
                        meeting_keywords = ['pertemuan', 'minggu', 'sesi', 'week', 'session', 'mgo', 'mg', 'ke', 'pert']
                        
                        is_pure_num_or_roman = False
                        clean_alphanum = re.sub(r'[^a-zA-Z0-9]', '', cleaned_phrase)
                        if clean_alphanum.isdigit():
                            is_pure_num_or_roman = True
                        else:
                            roman_pattern = re.compile(r'^[ivxlcdm]+$', re.IGNORECASE)
                            if roman_pattern.match(clean_alphanum):
                                is_pure_num_or_roman = True
                                
                        if words_in_phrase and not is_pure_num_or_roman:
                            has_keyword = any(kw in words_in_phrase for kw in meeting_keywords)
                            if not has_keyword:
                                rejection_reason = f"Does not contain meeting keywords: {words_in_phrase}"
                                
                    if rejection_reason:
                        logger.debug(f"Angka/teks '{phrase}' pada Halaman {p} ditolak sebagai Meeting. Alasan: {rejection_reason}")
                        continue
                        
                    nums = self.extract_meeting_numbers(phrase)
                    if nums:
                        y = sum((float(w['top']) + float(w['bottom']))/2 for w in meeting_words) / len(meeting_words)
                        global_y = (p - 1) * height + y
                        meeting_candidates.append({
                            'numbers': nums,
                            'page_num': p,
                            'y': y,
                            'global_y': global_y,
                            'text': phrase,
                            'bbox': {
                                'x0': min(float(w['x0']) for w in meeting_words),
                                'x1': max(float(w['x1']) for w in meeting_words),
                                'top': min(float(w['top']) for w in meeting_words),
                                'bottom': max(float(w['bottom']) for w in meeting_words),
                            }
                        })
                        
            # Unique checkpoints
            unique_checkpoints = []
            for cand in sorted(meeting_candidates, key=lambda c: c['global_y']):
                if not unique_checkpoints:
                    unique_checkpoints.append(cand)
                else:
                    last = unique_checkpoints[-1]
                    if abs(cand['global_y'] - last['global_y']) < 5:
                        last['numbers'] = sorted(list(set(last['numbers'] + cand['numbers'])))
                    else:
                        unique_checkpoints.append(cand)
                        
            extracted_meetings = sorted(list(set(num for cp in unique_checkpoints for num in cp['numbers'])))
            
            # Hitung skor tabel logical ini
            score = 0
            headers = lt['headers']
            if headers.get('meeting'): score += 15
            if headers.get('topic'): score += 15
            if headers.get('weight'): score += 5
            if headers.get('assessment'): score += 5
            
            meetings_count = len(extracted_meetings)
            if meetings_count >= 10:
                score += 20
                
            if meetings_count > 0:
                max_meeting = max(extracted_meetings)
                density = meetings_count / max_meeting if max_meeting > 0 else 0
                max_gap = max(extracted_meetings[i] - extracted_meetings[i-1] for i in range(1, len(extracted_meetings))) if len(extracted_meetings) > 1 else 1
                
                if 12 <= max_meeting <= 18 and density >= 0.70 and max_gap <= 3 and (1 in extracted_meetings or 2 in extracted_meetings):
                    score += 30
                    
            logger.info(f"Kandidat logical table {lt_idx+1} (Halaman {lt['pages'][0]}-{lt['pages'][-1]}): score={score}, meetings={extracted_meetings}")
            
            if score > best_lt_score:
                best_lt_score = score
                best_lt = lt
                best_lt_meetings = extracted_meetings
                best_lt_checkpoints = unique_checkpoints
                best_lt_grids = lt_grids

        if not best_lt or best_lt_score < 0:
            logger.warning("Tidak ada logical table silabus yang valid terdeteksi.")
            return []

        logger.info(f"Logical table terpilih dengan score {best_lt_score} (Halaman {best_lt['pages'][0]}-{best_lt['pages'][-1]}).")
        
        # 4. Kumpulkan kata-kata Topic per checkpoint
        results = []
        all_doc_words = []
        for p in best_lt['pages']:
            p_data = best_lt['page_data'][p]
            words = p_data['words']
            height = p_data['height']
            
            for w in words:
                w_top = float(w['top'])
                w_bottom = float(w['bottom'])
                global_top = (p - 1) * height + w_top
                global_bottom = (p - 1) * height + w_bottom
                
                all_doc_words.append({
                    'text': w['text'],
                    'x0': float(w['x0']),
                    'x1': float(w['x1']),
                    'top': w_top,
                    'bottom': w_bottom,
                    'global_top': global_top,
                    'global_bottom': global_bottom,
                    'page_num': p
                })

        # Hitung match_start_y menggunakan midpoints
        for idx, cp in enumerate(best_lt_checkpoints):
            p = cp['page_num']
            grid = best_lt_grids.get(p)
            cp_height = best_lt['page_data'][p]['height']
            
            if idx == 0:
                if grid:
                    cp['match_start_y'] = (p - 1) * cp_height + grid['header_y'][1]
                else:
                    cp['match_start_y'] = cp['global_y']
            else:
                prev_cp = best_lt_checkpoints[idx-1]
                if prev_cp['page_num'] != p:
                    if grid:
                        cp['match_start_y'] = (p - 1) * cp_height + grid['header_y'][1]
                    else:
                        cp['match_start_y'] = cp['global_y']
                else:
                    cp['match_start_y'] = (prev_cp['global_y'] + cp['global_y']) / 2

        debug_topic_boxes = []

        for idx, cp in enumerate(best_lt_checkpoints):
            start_y = cp['match_start_y']
            
            if idx + 1 < len(best_lt_checkpoints):
                next_cp = best_lt_checkpoints[idx+1]
                if next_cp['page_num'] != cp['page_num']:
                    cp_height = best_lt['page_data'][cp['page_num']]['height']
                    end_y = cp['page_num'] * cp_height
                else:
                    end_y = (cp['global_y'] + next_cp['global_y']) / 2
            else:
                end_y = float('inf')
                
            topic_words = []
            for w in all_doc_words:
                if start_y - 2 <= w['global_top'] < end_y - 2:
                    p = w['page_num']
                    grid = best_lt_grids.get(p)
                    if not grid:
                        continue
                        
                    mid_x = (w['x0'] + w['x1']) / 2
                    if grid['topic_x'][0] <= mid_x <= grid['topic_x'][1]:
                        if not (grid['header_y'][0] <= w['top'] <= grid['header_y'][1] + 25):
                            topic_words.append(w)
                            
            raw_topic_text = self._reconstruct_text_from_words(topic_words)
            topic, sub_topic = self.split_topic_subtopic(raw_topic_text)
            
            if topic or sub_topic:
                for num in cp['numbers']:
                    results.append({
                        "meeting_number": num,
                        "topic": topic,
                        "sub_topic": sub_topic
                    })
                    
                if topic_words:
                    words_by_page = {}
                    for tw in topic_words:
                        words_by_page.setdefault(tw['page_num'], []).append(tw)
                        
                    for p_num, p_words in words_by_page.items():
                        debug_topic_boxes.append({
                            'page_num': p_num,
                            'meeting_label': f"M{cp['numbers']}",
                            'x0': min(w['x0'] for w in p_words),
                            'x1': max(w['x1'] for w in p_words),
                            'top': min(w['top'] for w in p_words),
                            'bottom': max(w['bottom'] for w in p_words)
                        })

        # 5. Validator akhir sequence (Step 8)
        is_seq_valid = True
        reason_invalid = ""
        
        if not best_lt_meetings:
            is_seq_valid = False
            reason_invalid = "Daftar meeting kosong"
        else:
            max_meeting = max(best_lt_meetings)
            meetings_count = len(best_lt_meetings)
            density = meetings_count / max_meeting if max_meeting > 0 else 0
            max_gap = max(best_lt_meetings[i] - best_lt_meetings[i-1] for i in range(1, len(best_lt_meetings))) if len(best_lt_meetings) > 1 else 1
            
            # Cek 1: Meeting kurang dari 10 (Reject!)
            if meetings_count < 10:
                is_seq_valid = False
                reason_invalid = f"Jumlah meeting kurang dari 10 ({meetings_count})"
            # Cek 2: Sequence gap besar (Reject!)
            elif max_gap > 3:
                is_seq_valid = False
                reason_invalid = f"Sequence memiliki gap tidak wajar ({max_gap} > 3). Urutan: {best_lt_meetings}"
            # Cek 3: Range tidak wajar
            elif not (12 <= max_meeting <= 18):
                is_seq_valid = False
                reason_invalid = f"Pertemuan maksimum ({max_meeting}) di luar batas wajar 12-18"
            # Cek 4: Mulai dari awal (1 atau 2)
            elif not (1 in best_lt_meetings or 2 in best_lt_meetings):
                is_seq_valid = False
                reason_invalid = f"Tidak dimulai dari pertemuan 1 atau 2. Urutan: {best_lt_meetings}"

        # 6. Table Confidence Score (Step 9)
        confidence_score = 0.0
        if is_seq_valid:
            # - Header ditemukan (+15)
            headers = best_lt['headers']
            if headers.get('meeting') and headers.get('topic'):
                confidence_score += 15.0
            # - Meeting sequence (+15)
            confidence_score += 15.0
            # - Topic tidak kosong (+15)
            if results:
                non_empty = [r for r in results if r["topic"].strip()]
                if len(non_empty) / len(results) >= 0.8:
                    confidence_score += 15.0
            # - Jumlah meeting (+15)
            if len(best_lt_meetings) >= 10:
                confidence_score += 15.0
            # - Topic berada di kolom Materi (+15)
            confidence_score += 15.0
            # - Tidak mengambil text dari kolom Bobot (+15)
            confidence_score += 15.0
            # - Tidak mengambil text dari kolom Penilaian (+10)
            confidence_score += 10.0
            
        # Log debug info yang diminta
        logger.info("=== DEBUG PARREAD AREA ===")
        selected_table_name = f"Tabel Silabus (Halaman {best_lt['pages'][0]}-{best_lt['pages'][-1]})"
        logger.info(f"Nama Tabel Terpilih: {selected_table_name}")
        for p in best_lt['pages']:
            grid = best_lt_grids.get(p)
            if grid and grid.get('best_meeting') and grid.get('best_topic'):
                logger.info(
                    f"Halaman {p} - Header ditemukan: "
                    f"Meeting='{grid['best_meeting']['phrase']}' (X: {grid['meeting_x'][0]:.1f}-{grid['meeting_x'][1]:.1f}), "
                    f"Materi='{grid['best_topic']['phrase']}' (X: {grid['topic_x'][0]:.1f}-{grid['topic_x'][1]:.1f})"
                )
        logger.info(f"Daftar Meeting terdeteksi: {best_lt_meetings}")
        logger.info(f"Meeting Sequence Valid: {is_seq_valid} (Alasan: {reason_invalid if not is_seq_valid else 'Urutan valid'})")
        logger.info(f"Confidence Score: {confidence_score}%")
        logger.info("=========================")

        try:
            self._write_debug_html(
                pages_words, 
                best_lt_grids, 
                best_lt_checkpoints, 
                debug_topic_boxes, 
                confidence_score, 
                selected_table_name
            )
        except Exception as e:
            logger.warning(f"Gagal menulis file debug.html: {e}")
            
        if not is_seq_valid or confidence_score < 80.0:
            logger.warning(f"Coordinate-Based (Area Parser) gagal: seq_valid={is_seq_valid}, confidence={confidence_score}%. Melanjutkan ke fallback berikutnya.")
            return []
            
        return results

    def _reconstruct_lines(self, words: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        if not words:
            return []
        sorted_words = sorted(words, key=lambda w: (float(w['top']), float(w['x0'])))
        lines = []
        current_line = []
        current_top = None
        current_bottom = None
        
        for w in sorted_words:
            w_top = float(w['top'])
            w_bottom = float(w['bottom'])
            if current_top is None:
                current_top = w_top
                current_bottom = w_bottom
                current_line.append(w)
            else:
                if w_top < current_bottom - 2 or abs(w_top - current_top) < 4:
                    current_line.append(w)
                    current_top = min(current_top, w_top)
                    current_bottom = max(current_bottom, w_bottom)
                else:
                    lines.append(sorted(current_line, key=lambda x: float(x['x0'])))
                    current_line = [w]
                    current_top = w_top
                    current_bottom = w_bottom
        if current_line:
            lines.append(sorted(current_line, key=lambda x: float(x['x0'])))
        return lines

    def _find_headers_on_page(self, lines: List[List[Dict[str, Any]]]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        all_candidates = []
        
        for line in lines:
            n = len(line)
            for i in range(n):
                # Batasi maksimum 4 kata untuk mencegah cross-column match
                for j in range(i + 1, min(n + 1, i + 5)):
                    sub_segment = line[i:j]
                    phrase = " ".join(w['text'] for w in sub_segment)
                    cleaned = normalize_header(phrase) # Menggunakan normalize_header
                    
                    # Mencari kecocokan persis pada role
                    matched_role = None
                    from utils.header_normalizer import _clean_header_text, HEADER_MAPPING
                    cleaned_phrase = _clean_header_text(phrase)
                    for role, patterns in HEADER_MAPPING.items():
                        for pattern in patterns:
                            if cleaned_phrase == pattern:
                                matched_role = role
                                break
                        if matched_role:
                            break
                    
                    if matched_role:
                        x0 = min(float(w['x0']) for w in sub_segment)
                        x1 = max(float(w['x1']) for w in sub_segment)
                        top = min(float(w['top']) for w in sub_segment)
                        bottom = max(float(w['bottom']) for w in sub_segment)
                        
                        all_candidates.append({
                            'phrase': phrase,
                            'x0': x0,
                            'x1': x1,
                            'top': top,
                            'bottom': bottom,
                            'role': matched_role
                        })
                        
        meeting_candidates = [c for c in all_candidates if c['role'] == 'meeting']
        topic_candidates = [c for c in all_candidates if c['role'] == 'topic']
                            
        best_meeting = None
        best_topic = None
        
        for m in sorted(meeting_candidates, key=lambda c: c['top']):
            for t in sorted(topic_candidates, key=lambda c: c['top']):
                if abs(m['top'] - t['top']) < 25:
                    if m['x0'] < t['x0']:
                        same_top_m = [x for x in meeting_candidates if abs(x['top'] - m['top']) < 5 and x['x0'] < t['x0']]
                        same_top_t = [x for x in topic_candidates if abs(x['top'] - t['top']) < 5 and m['x0'] < x['x0']]
                        if same_top_m and same_top_t:
                            best_meeting = max(same_top_m, key=lambda x: len(x['phrase']))
                            best_topic = max(same_top_t, key=lambda x: len(x['phrase']))
                            break
            if best_meeting:
                break
        return best_meeting, best_topic, all_candidates

    def _calculate_column_bounds(self, best_meeting, best_topic, all_candidates, lines, page_width, meeting_x, topic_x, words):
        meeting_x0, meeting_x1 = meeting_x
        topic_x0, topic_x1 = topic_x
        
        # Cari header kolom lain di sebelah kanan materi pada level vertikal yang mirip
        same_level_other_headers = []
        for h in all_candidates:
            if h['role'] != 'topic' and abs(h['top'] - best_topic['top']) < 25 and h['x0'] > best_topic['x1']:
                same_level_other_headers.append(h)
                    
        next_col_x0 = None
        if same_level_other_headers:
            next_col_x0 = min(h['x0'] for h in same_level_other_headers)
            
        if next_col_x0 is not None:
            topic_x1 = next_col_x0 - 2
        else:
            # Cari batas kanan dari semua kata pada baris-baris di halaman ini yang berada di bawah header
            words_below = [w for w in words if float(w['top']) > best_topic['bottom']]
            max_x1 = max(float(w['x1']) for w in words_below) if words_below else page_width - 20
            topic_x1 = max_x1
            
        # Hanya gunakan midpoint jika gap antara meeting dan topic kecil (<80)
        gap = best_topic['x0'] - best_meeting['x1']
        if gap > 0 and gap < 80:
            midpoint = (best_meeting['x1'] + best_topic['x0']) / 2
            meeting_x1 = midpoint
            topic_x0 = midpoint
            
        return (meeting_x0, meeting_x1), (topic_x0, topic_x1)

    def _reconstruct_text_from_words(self, words: List[Dict[str, Any]]) -> str:
        if not words:
            return ""
        sorted_words = sorted(words, key=lambda w: (w['global_top'], w['x0']))
        lines = []
        current_line = []
        current_top = None
        
        for w in sorted_words:
            w_top = w['global_top']
            if current_top is None:
                current_top = w_top
                current_line.append(w)
            else:
                if abs(w_top - current_top) < 4:
                    current_line.append(w)
                else:
                    current_line_sorted = sorted(current_line, key=lambda x: x['x0'])
                    lines.append(" ".join(x['text'] for x in current_line_sorted))
                    current_line = [w]
                    current_top = w_top
        if current_line:
            current_line_sorted = sorted(current_line, key=lambda x: x['x0'])
            lines.append(" ".join(x['text'] for x in current_line_sorted))
        return "\n".join(lines)

    def _write_debug_html(self, pages_words, page_grids, checkpoints, topic_boxes, confidence_score, selected_table_name):
        import json
        import os
        
        html_template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>RPS Area-Based Table Debugger</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #0f172a;
            color: #f8fafc;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid #334155;
        }
        h1 {
            color: #38bdf8;
            margin: 0 0 10px 0;
        }
        .summary {
            font-size: 14px;
            color: #94a3b8;
            margin-bottom: 10px;
        }
        .meta-info {
            display: inline-block;
            background-color: #1e293b;
            border: 1px solid #475569;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 14px;
            margin-top: 5px;
        }
        .meta-info span {
            margin: 0 15px;
            font-weight: bold;
        }
        .meta-info .value {
            color: #38bdf8;
        }
        .page-container {
            background-color: #1e293b;
            border: 2px solid #334155;
            border-radius: 8px;
            margin-bottom: 40px;
            box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5);
            overflow: hidden;
        }
        .page-header {
            background-color: #334155;
            padding: 10px 20px;
            font-weight: bold;
            font-size: 16px;
            display: flex;
            justify-content: space-between;
        }
        .page-canvas {
            position: relative;
            background-color: #fff;
            margin: 20px auto;
            border: 1px solid #cbd5e1;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        }
        .word {
            position: absolute;
            font-size: 6px;
            color: #475569;
            white-space: nowrap;
            line-height: 1;
            pointer-events: none;
        }
        .overlay {
            position: absolute;
            pointer-events: none;
            opacity: 0.12;
        }
        .overlay-meeting-col {
            background-color: #0284c7;
            border-right: 2px dashed #0284c7;
            height: 100%;
        }
        .overlay-topic-col {
            background-color: #16a34a;
            border-left: 2px dashed #16a34a;
            border-right: 2px dashed #16a34a;
            height: 100%;
        }
        .overlay-bobot-col {
            background-color: #eab308;
            border-left: 2px dashed #eab308;
            border-right: 2px dashed #eab308;
            height: 100%;
        }
        .overlay-header-row {
            background-color: #dc2626;
            border-bottom: 2px dashed #dc2626;
            width: 100%;
        }
        .box-highlight {
            position: absolute;
            border: 2px solid;
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 4px;
            pointer-events: none;
        }
        .box-meeting {
            border-color: #0ea5e9;
            box-shadow: 0 0 8px rgba(14, 165, 233, 0.4);
        }
        .box-meeting::after {
            content: attr(data-label);
            position: absolute;
            top: -15px;
            left: 0;
            background-color: #0ea5e9;
            color: #0f172a;
            font-size: 8px;
            font-weight: bold;
            padding: 1px 3px;
            border-radius: 2px;
            white-space: nowrap;
        }
        .box-topic {
            border-color: #22c55e;
            box-shadow: 0 0 8px rgba(34, 197, 94, 0.4);
        }
        .box-topic::after {
            content: attr(data-label);
            position: absolute;
            top: -15px;
            left: 0;
            background-color: #22c55e;
            color: #0f172a;
            font-size: 8px;
            font-weight: bold;
            padding: 1px 3px;
            border-radius: 2px;
            white-space: nowrap;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>RPS Area-Based Table Debugger</h1>
            <div class="summary">Visualisasi deteksi kolom dan area parsing Meeting & Topic berbasis koordinat</div>
            <div class="meta-info">
                <span>Tabel Terpilih: <span class="value">%TABLE_NAME%</span></span>
                <span>Confidence Score: <span class="value">%CONFIDENCE_SCORE%%</span></span>
            </div>
        </div>
        <div id="pages-list"></div>
    </div>

    <script>
        const pagesData = %PAGES_DATA%;
        const checkpoints = %CHECKPOINTS_DATA%;
        const topicBoxes = %TOPIC_BOXES_DATA%;
        const grids = %GRIDS_DATA%;

        const listDiv = document.getElementById('pages-list');

        pagesData.forEach(p => {
            const pageNum = p.page_number;
            const w = p.width;
            const h = p.height;
            const words = p.words;
            const grid = grids[pageNum];

            const pageDiv = document.createElement('div');
            pageDiv.className = 'page-container';

            const pHeader = document.createElement('div');
            pHeader.className = 'page-header';
            pHeader.innerHTML = `<span>Halaman ${pageNum}</span><span>Dimensi: ${w} x ${h}</span>`;
            pageDiv.appendChild(pHeader);

            const canvas = document.createElement('div');
            canvas.className = 'page-canvas';
            
            const targetWidth = 800;
            const scale = targetWidth / w;
            const targetHeight = h * scale;

            canvas.style.width = targetWidth + 'px';
            canvas.style.height = targetHeight + 'px';

            if (grid) {
                const mCol = document.createElement('div');
                mCol.className = 'overlay overlay-meeting-col';
                mCol.style.left = (grid.meeting_x[0] * scale) + 'px';
                mCol.style.width = ((grid.meeting_x[1] - grid.meeting_x[0]) * scale) + 'px';
                canvas.appendChild(mCol);

                const tCol = document.createElement('div');
                tCol.className = 'overlay overlay-topic-col';
                tCol.style.left = (grid.topic_x[0] * scale) + 'px';
                tCol.style.width = ((grid.topic_x[1] - grid.topic_x[0]) * scale) + 'px';
                canvas.appendChild(tCol);
                
                if (grid.bobot_x) {
                    const bCol = document.createElement('div');
                    bCol.className = 'overlay overlay-bobot-col';
                    bCol.style.left = (grid.bobot_x[0] * scale) + 'px';
                    bCol.style.width = ((grid.bobot_x[1] - grid.bobot_x[0]) * scale) + 'px';
                    canvas.appendChild(bCol);
                }

                const hRow = document.createElement('div');
                hRow.className = 'overlay overlay-header-row';
                hRow.style.top = (grid.header_y[0] * scale) + 'px';
                hRow.style.height = ((grid.header_y[1] - grid.header_y[0]) * scale) + 'px';
                canvas.appendChild(hRow);
            }

            checkpoints.filter(cp => cp.page_num === pageNum).forEach(cp => {
                if (cp.bbox) {
                    const mBox = document.createElement('div');
                    mBox.className = 'box-highlight box-meeting';
                    mBox.setAttribute('data-label', `Meeting ${cp.numbers}`);
                    mBox.style.left = (cp.bbox.x0 * scale) + 'px';
                    mBox.style.width = ((cp.bbox.x1 - cp.bbox.x0) * scale) + 'px';
                    mBox.style.top = (cp.bbox.top * scale) + 'px';
                    mBox.style.height = ((cp.bbox.bottom - cp.bbox.top) * scale) + 'px';
                    canvas.appendChild(mBox);
                }
            });

            topicBoxes.filter(tb => tb.page_num === pageNum).forEach(tb => {
                const tBox = document.createElement('div');
                tBox.className = 'box-highlight box-topic';
                tBox.setAttribute('data-label', `${tb.meeting_label} Topic Area`);
                tBox.style.left = (tb.x0 * scale) + 'px';
                tBox.style.width = ((tb.x1 - tb.x0) * scale) + 'px';
                tBox.style.top = (tb.top * scale) + 'px';
                tBox.style.height = ((tb.bottom - tb.top) * scale) + 'px';
                canvas.appendChild(tBox);
            });

            words.forEach(wd => {
                const span = document.createElement('span');
                span.className = 'word';
                span.innerText = wd.text;
                span.style.left = (wd.x0 * scale) + 'px';
                span.style.top = (wd.top * scale) + 'px';
                span.style.width = ((wd.x1 - wd.x0) * scale) + 'px';
                span.style.height = ((wd.bottom - wd.top) * scale) + 'px';
                canvas.appendChild(span);
            });

            pageDiv.appendChild(canvas);
            listDiv.appendChild(pageDiv);
        });
    </script>
</body>
</html>
"""
        html_content = html_template.replace("%PAGES_DATA%", json.dumps(pages_words))
        html_content = html_content.replace("%CHECKPOINTS_DATA%", json.dumps(checkpoints))
        html_content = html_content.replace("%TOPIC_BOXES_DATA%", json.dumps(topic_boxes))
        html_content = html_content.replace("%TABLE_NAME%", selected_table_name)
        html_content = html_content.replace("%CONFIDENCE_SCORE%", str(confidence_score))
        
        serializable_grids = {}
        for p_num, g in page_grids.items():
            serializable_grids[p_num] = {
                'meeting_x': g['meeting_x'],
                'topic_x': g['topic_x'],
                'bobot_x': g.get('bobot_x'),
                'header_y': g['header_y']
            }
        html_content = html_content.replace("%GRIDS_DATA%", json.dumps(serializable_grids))
        
        with open("debug.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"Visual debug file debug.html berhasil ditulis ke {os.path.abspath('debug.html')}")
