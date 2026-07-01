"""
Modul PDFExtractionService untuk Sistem Validasi RPS-BAP.

Modul ini mendefinisikan class PDFExtractionService yang bertugas mengekstraksi
tabel Pokok Bahasan dari PDF RPS dan menghasilkan data terstruktur.

Sesuai PRD Section 4.3 - Modul PDF Extraction.
"""

import re
from typing import List, Dict, Any, Optional, Tuple

from utils.pdf_reader import PDFReader
from utils.topic_extractor import TopicExtractor
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
        self._topic_extractor = TopicExtractor()
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
                    # Validasi jumlah pertemuan hasil ekstraksi (Target 10)
                    if len(parsed_data) < 10:
                        logger.warning(
                            f"WARNING: Hasil ekstraksi tabel hanya menemukan {len(parsed_data)} pertemuan (kurang dari 10)! "
                            "Harap periksa format dokumen PDF secara manual."
                        )
                    
                    logger.info(f"Pertemuan berhasil diekstrak: {len(parsed_data)}")
                    return parsed_data
        except (PDFTableNotFoundError, PDFExtractionError) as e:
            logger.warning(f"Ekstraksi tabel gagal atau tidak ditemukan. Alasan: {e}. Mengaktifkan fallback ke teks mentah...")
            self.handle_extraction_failure({"file_path": file_path, "reason": str(e)})
        except Exception as e:
            logger.error(f"Gagal saat mencoba ekstraksi tabel: {e}. Mengaktifkan fallback ke teks mentah...")
            self.handle_extraction_failure({"file_path": file_path, "reason": str(e)})

        # 2. Fallback: Ekstraksi teks biasa dan parsing regex (pypdf/pdfplumber text)
        try:
            raw_text = reader.extract_raw_text()
            if raw_text:
                parsed_data = self._parse_text_data(raw_text)
                if parsed_data:
                    if len(parsed_data) < 10:
                        logger.warning(f"WARNING: Hasil ekstraksi fallback hanya menemukan {len(parsed_data)} pertemuan (kurang dari 10)!")
                        
                    logger.info(f"Ekstraksi teks mentah sukses. Berhasil mengekstrak {len(parsed_data)} pertemuan.")
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
                
            # Deteksi kolom header secara dinamis (Target 7)
            col_mapping = self._detect_columns(table)
            meeting_col, topic_col, sub_topic_col = col_mapping
            
            logger.debug(
                f"Tabel {table_idx} - Deteksi kolom mapping: "
                f"meeting={meeting_col}, topic={topic_col}, sub_topic={sub_topic_col}"
            )
            
            # Jika kolom minimal (meeting & topic) tidak terdeteksi, gunakan fallback default
            if meeting_col == -1 or topic_col == -1:
                if len(table[0]) >= 2:
                    meeting_col = 0
                    topic_col = 1
                    sub_topic_col = 2 if len(table[0]) >= 3 else -1
                else:
                    continue

            # Iterasi baris tabel
            for row in table:
                if len(row) <= max(meeting_col, topic_col):
                    continue
                    
                meeting_val = row[meeting_col].strip()
                topic_val = row[topic_col].strip()
                
                # sub_topic bersifat opsional
                sub_topic_val = ""
                if sub_topic_col != -1 and len(row) > sub_topic_col:
                    sub_topic_val = row[sub_topic_col].strip()
                
                # Normalisasi nomor pertemuan, tetapi pertahankan newline topik
                # karena newline dipakai TopicExtractor untuk mendeteksi heading.
                meeting_val = re.sub(r'\s+', ' ', meeting_val).strip()
                sub_topic_val = self._topic_extractor.normalize_whitespace(sub_topic_val)

                if not meeting_val or not topic_val:
                    continue

                # Ekstrak nomor pertemuan angka dari string
                meeting_num = self._extract_meeting_number(meeting_val)
                if meeting_num is None:
                    continue  # Lewati baris header/identitas yang bukan record pertemuan
                    
                context_values = [
                    cell for idx, cell in enumerate(row)
                    if idx != topic_col and isinstance(cell, str) and cell.strip()
                ]

                results.append({
                    "meeting_number": meeting_num,
                    "topic": self._topic_extractor.clean_topic(topic_val, context=context_values),
                    "sub_topic": sub_topic_val
                })
                
        # Urutkan berdasarkan nomor pertemuan dan hilangkan duplikasi jika ada
        unique_results = {}
        for item in results:
            m_num = item["meeting_number"]
            # Simpan atau update rincian terpanjang jika ada duplikat nomor pertemuan
            if m_num not in unique_results or len(item["topic"]) > len(unique_results[m_num]["topic"]):
                unique_results[m_num] = item
                
        final_list = []
        for item in sorted(unique_results.values(), key=lambda x: x["meeting_number"]):
            item["topic"] = self._topic_extractor.clean_topic(item["topic"])
            if item.get("sub_topic"):
                item["sub_topic"] = self._topic_extractor.normalize_whitespace(item["sub_topic"])
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
        meeting_col = -1
        topic_col = -1
        sub_topic_col = -1
        
        # Cari header di 3 baris pertama
        for row_idx in range(min(3, len(table))):
            row = [cell.lower() for cell in table[row_idx]]
            
            for col_idx, cell in enumerate(row):
                # 1. Deteksi nomor pertemuan / sesi
                if any(k in cell for k in ["minggu", "pertemuan", "ke-", "ke ", "mng", "pert", "no", "sesi"]):
                    if meeting_col == -1:
                        meeting_col = col_idx
                # 2. Deteksi sub pokok bahasan (harus diletakkan sebelum pokok bahasan utama)
                elif any(k in cell for k in ["sub pokok", "sub bahasan", "sub-topik", "sub topik", "sub-cp-mk", "sub cpmk", "rincian materi"]):
                    if sub_topic_col == -1:
                        sub_topic_col = col_idx
                # 3. Deteksi pokok bahasan / topik utama
                elif any(k in cell for k in ["pokok bahasan", "materi", "topik", "bahan kajian", "kemampuan akhir"]):
                    if topic_col == -1:
                        topic_col = col_idx
                        
            # Jika sudah menemukan setidaknya meeting dan topic, stop pencarian
            if meeting_col != -1 and topic_col != -1:
                break
                
        return meeting_col, topic_col, sub_topic_col

    def _extract_meeting_number(self, val: str) -> Optional[int]:
        """
        Mengekstrak integer nomor pertemuan dari string input secara aman.

        Args:
            val: String mentah (contoh: "Pertemuan 1", "Minggu Ke - 2", "3").

        Returns:
            Optional[int]: Nilai integer jika ditemukan, None jika tidak.
        """
        if not val:
            return None
            
        # Bersihkan spasi
        val_clean = val.strip().lower()
        
        # 1. Cari angka desimal langsung
        match = re.search(r'\b(\d+)\b', val_clean)
        if match:
            return int(match.group(1))
            
        # 2. Cari angka romawi jika tidak ada angka biasa (I, II, III, IV, dsb)
        roman_patterns = [
            (r'\bxvi\b', 16), (r'\bxv\b', 15), (r'\bxiv\b', 14), (r'\bxiii\b', 13),
            (r'\bxii\b', 12), (r'\bxi\b', 11), (r'\bx\b', 10), (r'\bix\b', 9),
            (r'\bviii\b', 8), (r'\bvii\b', 7), (r'\bvi\b', 6), (r'\bv\b', 5),
            (r'\biv\b', 4), (r'\biii\b', 3), (r'\bii\b', 2), (r'\bi\b', 1)
        ]
        for pattern, num in roman_patterns:
            if re.search(pattern, val_clean):
                return num
                
        return None

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
                
                topic = content
                sub_topic = ""
                
                sub_match = re.search(r'\((.*?)\)', content)
                if sub_match:
                    sub_topic = sub_match.group(1)
                    topic = content.replace(f"({sub_topic})", "").strip()
                
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
            item["topic"] = self._topic_extractor.clean_topic(item["topic"])
            if item.get("sub_topic"):
                item["sub_topic"] = self._topic_extractor.normalize_whitespace(item["sub_topic"])
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
