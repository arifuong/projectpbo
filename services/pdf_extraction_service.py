"""
Modul PDFExtractionService untuk Sistem Validasi RPS-BAP.

Modul ini mendefinisikan class PDFExtractionService yang bertugas mengekstraksi
tabel Pokok Bahasan dari PDF RPS dan menghasilkan data terstruktur.

Sesuai PRD Section 4.3 - Modul PDF Extraction.
"""

import re
from typing import List, Dict, Any, Optional, Tuple

from utils.pdf_reader import PDFReader
from utils.rps_parser import RPSParser
from utils.logger import setup_logger
from utils.exceptions import PDFExtractionError, PDFTableNotFoundError

# Inisialisasi logger untuk service
logger = setup_logger(__name__)


class PDFExtractionService:
    """
    Service class untuk melakukan ekstraksi pokok bahasan dari file PDF RPS.

    Menerapkan design pattern Composition dengan memiliki (has-a) objek PDFReader.
    Mendukung fallback otomatis dari pemrosesan tabel (pdfplumber) ke analisis teks mentah (pypdf).

    Attributes:
        _reader (Optional[PDFReader]): Instansi PDFReader yang diinjeksi atau dibuat secara internal.
    """

    def __init__(self, reader: Optional[PDFReader] = None) -> None:
        """
        Inisialisasi PDFExtractionService.

        Args:
            reader: Instansi PDFReader (Dependency Injection).
        """
        # Composition: has-a PDFReader
        self._reader: Optional[PDFReader] = reader
        self._rps_parser = RPSParser()
        logger.info("PDFExtractionService diinisialisasi.")

    def extract_pokok_bahasan(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Metode utama mengekstrak Pokok Bahasan RPS dari file PDF.

        Sesuai PRD & AC-04:
        Mengekstrak kolom: Pertemuan ke-, Pokok Bahasan, Sub Pokok Bahasan.
        Menggunakan ekstraksi tabel sebagai metode utama, dan fallback ke teks mentah jika gagal.

        Args:
            file_path: Path absolut file PDF.

        Returns:
            List[Dict[str, Any]]: List dictionary berisi data:
                                 "meeting_number": int,
                                 "topic": str,
                                 "sub_topic": str

        Raises:
            PDFExtractionError: Jika gagal mengekstrak data baik melalui tabel maupun teks.
        """
        logger.info(f"Memulai proses ekstraksi Pokok Bahasan dari: {file_path}")
        
        # Buat reader baru jika tidak diinjeksi di constructor
        reader = self._reader or PDFReader(file_path)
        reader.file_path = file_path

        # 1. Coba ekstraksi menggunakan metode tabel (pdfplumber)
        try:
            tables = reader.extract_tables()
            if tables:
                parsed_data = self._parse_table_data(tables)
                if parsed_data:
                    self._log_extraction_summary(parsed_data)
                    return parsed_data
        except (PDFTableNotFoundError, PDFExtractionError) as e:
            logger.warning(f"Ekstraksi tabel gagal atau tidak ditemukan. Alasan: {e}. Mengaktifkan fallback ke teks mentah...")
            self.handle_extraction_failure({"file_path": file_path, "reason": str(e)})
        except Exception as e:
            logger.error(f"Gagal saat mencoba ekstraksi tabel: {e}. Mengaktifkan fallback ke teks mentah...")
            self.handle_extraction_failure({"file_path": file_path, "reason": str(e)})

        # 2. Fallback: words + regex untuk PDF tanpa garis tabel.
        try:
            pages_words = reader.extract_words_by_page()
            parsed_data = self._parse_words_data(pages_words)
            if parsed_data:
                self._log_extraction_summary(parsed_data)
                return parsed_data
        except Exception as e:
            logger.warning(f"Fallback extract_words gagal. Alasan: {e}. Mengaktifkan fallback pypdf...")

        # 3. Fallback akhir: Ekstraksi teks biasa dan parsing regex (pypdf/pdfplumber text)
        try:
            raw_text = reader.extract_raw_text()
            if raw_text:
                parsed_data = self._parse_text_data(raw_text)
                if parsed_data:
                    self._log_extraction_summary(parsed_data)
                    return parsed_data
            
            # Jika semua metode gagal mengembalikan data
            raise PDFExtractionError(
                "Gagal mengekstrak data terstruktur Pokok Bahasan dari PDF baik melalui tabel maupun teks."
            )
        except Exception as e:
            logger.exception(f"Fallback ekstraksi teks mentah gagal: {e}")
            raise PDFExtractionError(f"Gagal melakukan ekstraksi PDF: {e}")

    def _parse_table_data(self, tables: List[List[List[str]]]) -> List[Dict[str, Any]]:
        """
        Memparse list data tabel mentah 3D menjadi baris data pertemuan terstruktur.

        Args:
            tables: Representasi tabel dari pdfplumber.

        Returns:
            List[Dict[str, Any]]: Hasil parsing baris data terstruktur.
        """
        results: List[Dict[str, Any]] = []
        
        for table_idx, table in enumerate(tables):
            if len(table) < 2:
                continue
                
            col_mapping = self._detect_columns(table)
            meeting_col, topic_col, sub_topic_col = col_mapping
            
            logger.debug(
                f"Tabel {table_idx} - Deteksi kolom mapping: "
                f"meeting={meeting_col}, topic={topic_col}, sub_topic={sub_topic_col}"
            )
            
            if meeting_col == -1 or topic_col == -1:
                continue

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
                continue

            existing = unique_results[m_num]
            if item.get("sub_topic"):
                existing["sub_topic"] = self._rps_parser.append_sub_topic(
                    existing.get("sub_topic", ""),
                    item["sub_topic"],
                )
                
        final_list = []
        for item in sorted(unique_results.values(), key=lambda x: x["meeting_number"]):
            item["topic"] = self._rps_parser.normalize_cell(item.get("topic", ""), keep_newline=False)
            item["sub_topic"] = self._rps_parser.normalize_multiline(item.get("sub_topic", ""))
            final_list.append(item)
            
        return final_list

    def _detect_columns(self, table: List[List[str]]) -> Tuple[int, int, int]:
        """
        Mendeteksi indeks kolom untuk Pertemuan, Topik, dan Sub Topik secara dinamis.

        Args:
            table: Baris-baris tabel.

        Returns:
            Tuple[int, int, int]: Indeks kolom (meeting_col, topic_col, sub_topic_col).
        """
        return self._rps_parser.detect_columns(table)

    def _extract_meeting_number(self, val: str) -> Optional[int]:
        """
        Mengekstrak integer nomor pertemuan dari string input secara aman.

        Args:
            val: String mentah (contoh: "Pertemuan 1", "Minggu Ke - 2", "3").

        Returns:
            Optional[int]: Nilai integer jika ditemukan, None jika tidak.
        """
        return self._rps_parser.extract_meeting_number(val)

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

        Args:
            raw_text: Teks mentah dokumen.

        Returns:
            List[Dict[str, Any]]: Daftar record hasil parsing teks.
        """
        results: List[Dict[str, Any]] = []
        lines = raw_text.split("\n")
        
        pattern = re.compile(
            r'\b(?:pertemuan|minggu|ke|sesi)\s*[-:]?\s*(\d+)\s*[-:]?\s*(.*)', 
            re.IGNORECASE
        )
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
                
            match = pattern.search(line_stripped)
            if match:
                meeting_num = int(match.group(1))
                content = match.group(2).strip()
                
                topic, sub_topic = self._rps_parser.split_topic_subtopic(content)
                if topic:
                    results.append({
                        "meeting_number": meeting_num,
                        "topic": topic,
                        "sub_topic": sub_topic
                    })
                    
        # Hilangkan duplikasi
        unique_results = {}
        for item in results:
            m_num = item["meeting_number"]
            if m_num not in unique_results or len(item["topic"]) > len(unique_results[m_num]["topic"]):
                unique_results[m_num] = item
                
        final_list = []
        for item in sorted(unique_results.values(), key=lambda x: x["meeting_number"]):
            item["topic"] = self._rps_parser.normalize_cell(item.get("topic", ""), keep_newline=False)
            item["sub_topic"] = self._rps_parser.normalize_multiline(item.get("sub_topic", ""))
            final_list.append(item)
            
        return final_list

    def handle_extraction_failure(self, error_info: Dict[str, Any]) -> None:
        """
        Mencatat informasi kegagalan ekstraksi PDF.

        Args:
            error_info: Info kesalahan.
        """
        logger.warning(
            f"KEGAGALAN EKSTRAKSI DOKUMEN: file={error_info.get('file_path')}, "
            f"Alasan={error_info.get('reason')}"
        )

    def _log_extraction_summary(self, parsed_data: List[Dict[str, Any]]) -> None:
        """
        Logging ringkasan hasil parsing RPS.
        """
        if len(parsed_data) < 10:
            logger.warning(
                f"WARNING: Hasil ekstraksi hanya menemukan {len(parsed_data)} pertemuan."
            )
        logger.info(f"Pertemuan berhasil dibaca: {len(parsed_data)}")
        topic_count = sum(1 for item in parsed_data if item.get("topic"))
        logger.info(f"Topik berhasil diekstrak: {topic_count}")
