"""
Service untuk melakukan ekstraksi Pokok Bahasan dari file PDF RPS.

Service ini bertanggung jawab mengoordinasikan proses membaca PDF,
memparse tabel/teks, menangani fallback ke OCR, dan memvalidasi hasil parsing.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from utils.exceptions import PDFExtractionError
from utils.topic_extractor import TopicExtractor
from utils.pdf_reader import PDFReader
from utils.rps_parser import RPSParser

logger = logging.getLogger("services.pdf_extraction_service")


class PDFExtractionService:
    """
    Service koordinasi ekstraksi PDF dengan pipeline fallback 5-stage dan validation.
    """

    def __init__(self, reader: Optional[PDFReader] = None, rps_parser: Optional[RPSParser] = None):
        """
        Inisialisasi PDFExtractionService.

        Args:
            reader: Instansi PDFReader opsional untuk dependecy injection.
            rps_parser: Instansi RPSParser opsional untuk dependency injection.
        """
        self._reader = reader
        self._rps_parser = rps_parser or RPSParser()
        self._topic_extractor = TopicExtractor()
        logger.info("PDFExtractionService diinisialisasi.")

    def extract_pokok_bahasan(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Metode utama mengekstrak Pokok Bahasan RPS dari file PDF menggunakan multi-stage fallback pipeline.
        """
        logger.info(f"Memulai proses ekstraksi Pokok Bahasan dari: {file_path}")
        
        reader = self._reader or PDFReader(file_path)
        reader.file_path = file_path

        stats = {
            "method_used": "None",
            "tables_found": 0,
            "tables_processed": 0,
            "records_extracted": 0,
            "records_failed": 0,
            "fallbacks_used": [],
            "ocr_used": False,
            "failure_reasons": {}
        }

        # Stage 1: Coordinate-Based Extraction (Primary)
        try:
            pages_words = reader.extract_words_by_page()
            if pages_words and isinstance(pages_words, list) and len(pages_words) > 0 and pages_words[0].get("words"):
                parsed_data = self._parse_coordinate_data(pages_words)
                if parsed_data:
                    stats["method_used"] = "Coordinate-Based"
                    stats["records_extracted"] = len(parsed_data)
                    self._log_and_validate_warnings(parsed_data, stats)
                    return parsed_data
                else:
                    logger.info("Stage 1 (Coordinate-Based) tidak berhasil mengekstrak record.")
        except Exception as e:
            reason = str(e)
            logger.warning(f"Stage 1 (Coordinate-Based) gagal: {reason}.")
            stats["failure_reasons"]["Coordinate-Based"] = reason
            stats["fallbacks_used"].append("Coordinate-Based")

        # Fallback Stage 2: Header-Based Table Extraction
        try:
            tables = reader.extract_tables()
            stats["tables_found"] = len(tables)
            if tables:
                parsed_data = self._parse_table_data(tables, stats, use_heuristic=False)
                if parsed_data:
                    stats["method_used"] = "Header-Based Table"
                    stats["records_extracted"] = len(parsed_data)
                    self._log_and_validate_warnings(parsed_data, stats)
                    return parsed_data
                else:
                    logger.info("Stage 2 (Header-Based Table) tidak berhasil mengekstrak record.")
        except Exception as e:
            reason = str(e)
            logger.warning(f"Stage 2 (Header-Based Table) gagal: {reason}.")
            stats["failure_reasons"]["Header-Based Table"] = reason
            stats["fallbacks_used"].append("Header-Based Table")

        # Fallback Stage 3: Semantic Column Detection
        try:
            tables = tables if 'tables' in locals() else reader.extract_tables()
            stats["tables_found"] = len(tables)
            if tables:
                parsed_data = self._parse_table_data(tables, stats, use_heuristic=True)
                if parsed_data:
                    stats["method_used"] = "Semantic Table"
                    stats["records_extracted"] = len(parsed_data)
                    self._log_and_validate_warnings(parsed_data, stats)
                    return parsed_data
                else:
                    logger.info("Stage 3 (Semantic Table) tidak berhasil mengekstrak record.")
        except Exception as e:
            reason = str(e)
            logger.warning(f"Stage 3 (Semantic Table) gagal: {reason}.")
            stats["failure_reasons"]["Semantic Table"] = reason
            stats["fallbacks_used"].append("Semantic Table")

        # Fallback Stage 4: Word Position Extraction
        try:
            pages_words = pages_words if 'pages_words' in locals() else reader.extract_words_by_page()
            if pages_words:
                parsed_data = self._parse_words_data(pages_words)
                if parsed_data:
                    stats["method_used"] = "Word Position"
                    stats["records_extracted"] = len(parsed_data)
                    self._log_and_validate_warnings(parsed_data, stats)
                    return parsed_data
                else:
                    logger.info("Stage 4 (Word Position) tidak berhasil mengekstrak record.")
        except Exception as e:
            reason = str(e)
            logger.warning(f"Stage 4 (Word Position) gagal: {reason}.")
            stats["failure_reasons"]["Word Position"] = reason
            stats["fallbacks_used"].append("Word Position")

        # Fallback Stage 5: Raw Text Parsing
        try:
            raw_text = reader.extract_raw_text()
            if raw_text:
                parsed_data = self._parse_text_data(raw_text)
                if parsed_data:
                    stats["method_used"] = "Raw Text"
                    stats["records_extracted"] = len(parsed_data)
                    self._log_and_validate_warnings(parsed_data, stats)
                    return parsed_data
                else:
                    logger.info("Stage 5 (Raw Text) tidak berhasil mengekstrak record.")
        except Exception as e:
            reason = str(e)
            logger.warning(f"Stage 5 (Raw Text) gagal: {reason}.")
            stats["failure_reasons"]["Raw Text"] = reason
            stats["fallbacks_used"].append("Raw Text")

        # Fallback Stage 6: OCR
        try:
            logger.info("Mengaktifkan Stage 6: OCR...")
            stats["ocr_used"] = True
            ocr_text = reader.extract_text_via_ocr()
            if ocr_text:
                parsed_data = self._parse_text_data(ocr_text)
                if parsed_data:
                    stats["method_used"] = "OCR"
                    stats["records_extracted"] = len(parsed_data)
                    self._log_and_validate_warnings(parsed_data, stats)
                    return parsed_data
                else:
                    logger.info("Stage 6 (OCR) tidak berhasil mengekstrak record.")
        except Exception as e:
            reason = str(e)
            logger.error(f"Stage 6 (OCR) gagal: {reason}")
            stats["failure_reasons"]["OCR"] = reason
            stats["fallbacks_used"].append("OCR")

        raise PDFExtractionError(
            "Gagal mengekstrak data terstruktur Pokok Bahasan dari PDF melalui semua stage fallback."
        )

    def _parse_coordinate_data(self, pages_words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Memparse data koordinat kata menggunakan rps_parser.parse_by_coordinates().
        """
        results = self._rps_parser.parse_by_coordinates(pages_words)
        
        unique_results = {}
        for item in results:
            m_num = item["meeting_number"]
            if m_num not in unique_results:
                unique_results[m_num] = item
            else:
                existing = unique_results[m_num]
                if len(item.get("topic", "")) > len(existing.get("topic", "")):
                    if existing.get("sub_topic"):
                        item["sub_topic"] = self._rps_parser.append_sub_topic(
                            existing["sub_topic"],
                            item.get("sub_topic", "")
                        )
                    unique_results[m_num] = item
                else:
                    if item.get("sub_topic"):
                        existing["sub_topic"] = self._rps_parser.append_sub_topic(
                            existing.get("sub_topic", ""),
                            item["sub_topic"]
                        )
                        
        final_list = []
        for item in sorted(unique_results.values(), key=lambda x: x["meeting_number"]):
            item["topic"] = self._topic_extractor.clean_topic(item.get("topic", ""))
            item["sub_topic"] = self._rps_parser.normalize_multiline(item.get("sub_topic", ""))
            final_list.append(item)
            
        return final_list

    def _parse_table_data(self, tables: List[List[List[str]]], stats: Optional[Dict[str, Any]] = None, use_heuristic: bool = True) -> List[Dict[str, Any]]:
        """
        Memparse list data tabel mentah 3D menjadi baris data pertemuan terstruktur.
        """
        if stats is None:
            stats = {"tables_processed": 0, "records_failed": 0}

        results: List[Dict[str, Any]] = []
        
        for table_idx, table in enumerate(tables):
            if len(table) < 2:
                continue
                
            col_mapping = self._rps_parser.detect_columns(table, use_heuristic=use_heuristic)
            meeting_col, topic_col, sub_topic_col = col_mapping
            
            # Log detected headers
            detected_headers = []
            for col_idx in (meeting_col, topic_col, sub_topic_col):
                if col_idx != -1 and col_idx < len(table[0]):
                    detected_headers.append(f"col_{col_idx}: '{table[0][col_idx]}'")
                    
            logger.info(
                f"Tabel {table_idx} - Deteksi kolom mapping: "
                f"meeting_col={meeting_col}, topic_col={topic_col}, sub_topic_col={sub_topic_col}. "
                f"Headers: {', '.join(detected_headers)}"
            )
            
            if meeting_col == -1 or topic_col == -1:
                stats["records_failed"] += len(table)
                continue

            stats["tables_processed"] += 1
            table_records = self._rps_parser.rows_to_records(
                table,
                meeting_col=meeting_col,
                topic_col=topic_col,
                sub_topic_col=sub_topic_col,
            )
            results.extend(table_records)
                
        # Urutkan berdasarkan nomor pertemuan dan hilangkan duplikasi jika ada
        unique_results = {}
        for item in results:
            m_num = item["meeting_number"]
            if m_num not in unique_results:
                unique_results[m_num] = item
            else:
                existing = unique_results[m_num]
                if len(item.get("topic", "")) > len(existing.get("topic", "")):
                    if existing.get("sub_topic"):
                        item["sub_topic"] = self._rps_parser.append_sub_topic(
                            existing["sub_topic"],
                            item.get("sub_topic", "")
                        )
                    unique_results[m_num] = item
                else:
                    if item.get("sub_topic"):
                        existing["sub_topic"] = self._rps_parser.append_sub_topic(
                            existing.get("sub_topic", ""),
                            item["sub_topic"]
                        )
                
        final_list = []
        for item in sorted(unique_results.values(), key=lambda x: x["meeting_number"]):
            item["topic"] = self._topic_extractor.clean_topic(item.get("topic", ""))
            item["sub_topic"] = self._rps_parser.normalize_multiline(item.get("sub_topic", ""))
            final_list.append(item)
            
        return final_list

    def _parse_words_data(self, pages_words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Fallback untuk PDF tanpa garis tabel: susun teks dari words lalu parse regex.
        """
        page_texts = []
        for page in pages_words:
            words = page.get("words", [])
            if not words:
                continue
            words_sorted = sorted(words, key=lambda w: (round(float(w.get("top", 0)) / 4), float(w.get("x0", 0))))
            lines: Dict[int, List[str]] = {}
            for word in words_sorted:
                key = round(float(word.get("top", 0)) / 4)
                lines.setdefault(key, []).append(str(word.get("text", "")))
            for key in sorted(lines):
                line = self._rps_parser.normalize_cell(" ".join(lines[key]), keep_newline=False)
                if line:
                    page_texts.append(line)
        return self._parse_text_data("\n".join(page_texts))

    def _parse_text_data(self, raw_text: str) -> List[Dict[str, Any]]:
        """
        Memparse teks mentah (raw text) jika ekstraksi tabel gagal.
        """
        results: List[Dict[str, Any]] = []
        lines = raw_text.split("\n")
        
        # Pattern 1: Mengandung kata kunci (pertemuan, minggu, ke, sesi)
        pattern_keyword = re.compile(
            r'\b(?:pertemuan|minggu|ke|sesi|week|session)\s*[-:]?\s*([0-9\s,&\-danivxlc]+)\s*[-:]\s*(.*)', 
            re.IGNORECASE
        )
        
        # Pattern 2: Angka di awal baris langsung diikuti pemisah
        pattern_digit = re.compile(
            r'^\s*([0-9\s,&\-danivxlc]+)\s*[-:\.]\s*(.*)',
            re.IGNORECASE
        )
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
                
            meeting_group = ""
            content = ""
            
            match = pattern_keyword.search(line_stripped)
            if match:
                meeting_group = match.group(1).strip()
                content = match.group(2).strip()
            else:
                match = pattern_digit.match(line_stripped)
                if match:
                    meeting_group = match.group(1).strip()
                    content = match.group(2).strip()
            
            if meeting_group and content:
                meeting_numbers = self._rps_parser.extract_meeting_numbers(meeting_group)
                if meeting_numbers:
                    topic, sub_topic = self._rps_parser.split_topic_subtopic(content)
                    if topic:
                        for num in meeting_numbers:
                            results.append({
                                "meeting_number": num,
                                "topic": topic,
                                "sub_topic": sub_topic
                            })
                            
        # Hilangkan duplikasi dan urutkan
        unique_results = {}
        for item in results:
            m_num = item["meeting_number"]
            if m_num not in unique_results or len(item["topic"]) > len(unique_results[m_num]["topic"]):
                unique_results[m_num] = item
                
        final_list = []
        for item in sorted(unique_results.values(), key=lambda x: x["meeting_number"]):
            item["topic"] = self._topic_extractor.clean_topic(item.get("topic", ""))
            item["sub_topic"] = self._rps_parser.normalize_multiline(item.get("sub_topic", ""))
            final_list.append(item)
            
        return final_list

    def _log_and_validate_warnings(self, parsed_data: List[Dict[str, Any]], stats: Dict[str, Any]) -> None:
        """
        Log warnings untuk meeting yang hilang atau kosong, hitung confidence score, dan print summary.
        """
        # Ekstrak nomor pertemuan yang berhasil dibaca
        found_meetings = {item["meeting_number"] for item in parsed_data}
        empty_topic_meetings = {item["meeting_number"] for item in parsed_data if not item.get("topic", "").strip()}
        
        max_meeting = max(found_meetings) if found_meetings else 16
        expected_range = range(1, max(17, max_meeting + 1))
        
        missing_meetings = []
        for m in expected_range:
            if m not in found_meetings:
                missing_meetings.append(m)
                logger.warning(f"Warning: Meeting {m} tidak ditemukan.")
            elif m in empty_topic_meetings:
                logger.warning(f"Warning: Meeting {m} tidak memiliki Materi Pembelajaran.")

        # Hitung Confidence Score
        method_weights = {
            "Coordinate-Based": 1.0,
            "Header-Based Table": 1.0,
            "Semantic Table": 0.85,
            "Word Position": 0.70,
            "Raw Text": 0.55,
            "OCR": 0.40
        }
        weight = method_weights.get(stats["method_used"], 0.5)
        found_count = len(found_meetings)
        meetings_ratio = min(1.0, found_count / 16.0)
        confidence_score = round(weight * meetings_ratio * 100, 2)
        stats["confidence_score"] = confidence_score
        stats["missing_meetings"] = missing_meetings

        # Print statistics to logs
        logger.info("================ EXTRACTION SUMMARY ================")
        logger.info(f"Extraction Method : {stats['method_used']}")
        logger.info(f"Confidence Score  : {confidence_score}%")
        logger.info(f"Tables Found      : {stats.get('tables_found', 0)}")
        logger.info(f"Tables Parsed     : {stats.get('tables_processed', 0)}")
        logger.info(f"Rows Parsed       : {found_count}")
        logger.info(f"Missing Meetings  : {missing_meetings}")
        logger.info(f"OCR Used          : {stats.get('ocr_used', False)}")
        if stats.get('fallbacks_used'):
            logger.info(f"Fallbacks Used    : {', '.join(stats['fallbacks_used'])}")
        logger.info("====================================================")
