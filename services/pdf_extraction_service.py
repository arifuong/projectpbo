"""
Modul PDFExtractionService untuk Sistem Validasi RPS-BAP.

Modul ini mendefinisikan class PDFExtractionService yang bertugas mengekstraksi
tabel Pokok Bahasan dari PDF RPS dan menghasilkan data terstruktur.

Sesuai PRD Section 4.3 - Modul PDF Extraction.
"""

import re
from typing import List, Dict, Any, Optional, Tuple

from utils.pdf_reader import PDFReader
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
                    logger.info(f"Ekstraksi tabel sukses. Berhasil mengekstrak {len(parsed_data)} pertemuan.")
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
                
            # Deteksi kolom header
            col_mapping = self._detect_columns(table)
            meeting_col, topic_col, sub_topic_col = col_mapping
            
            logger.debug(
                f"Tabel {table_idx} - Deteksi kolom mapping: "
                f"meeting={meeting_col}, topic={topic_col}, sub_topic={sub_topic_col}"
            )
            
            # Jika kolom minimal (meeting & topic) tidak terdeteksi, lewati atau gunakan fallback default
            if meeting_col == -1 or topic_col == -1:
                # Fallback default kolom jika tabel minimal lebar 2
                if len(table[0]) >= 2:
                    meeting_col = 0
                    topic_col = 1
                    sub_topic_col = 2 if len(table[0]) >= 3 else -1
                else:
                    continue

            # Iterasi baris tabel (mulai dari baris setelah header)
            # Menghindari baris yang merupakan header itu sendiri
            start_row = 1
            for row in table[start_row:]:
                if len(row) <= max(meeting_col, topic_col):
                    continue
                    
                meeting_val = row[meeting_col].strip()
                topic_val = row[topic_col].strip()
                
                # sub_topic bersifat opsional
                sub_topic_val = ""
                if sub_topic_col != -1 and len(row) > sub_topic_col:
                    sub_topic_val = row[sub_topic_col].strip()
                
                # Ekstrak nomor pertemuan angka dari string (misal: "Pertemuan 1" -> 1)
                meeting_num = self._extract_meeting_number(meeting_val)
                if meeting_num is None:
                    continue  # Lewati baris yang bukan record pertemuan
                    
                # Pastikan topik tidak kosong
                if not topic_val:
                    continue
                    
                # Masukkan hasil
                results.append({
                    "meeting_number": meeting_num,
                    "topic": topic_val,
                    "sub_topic": sub_topic_val
                })
                
        # Urutkan berdasarkan nomor pertemuan dan hilangkan duplikasi jika ada
        unique_results = {}
        for item in results:
            m_num = item["meeting_number"]
            # Simpan atau update rincian terpanjang jika ada duplikat nomor pertemuan
            if m_num not in unique_results or len(item["topic"]) > len(unique_results[m_num]["topic"]):
                unique_results[m_num] = item
                
        return sorted(unique_results.values(), key=lambda x: x["meeting_number"])

    def _detect_columns(self, table: List[List[str]]) -> Tuple[int, int, int]:
        """
        Mendeteksi indeks kolom untuk Pertemuan, Topik/Pokok Bahasan, dan Sub Topik.

        Args:
            table: Baris-baris tabel.

        Returns:
            Tuple[int, int, int]: Indeks kolom (meeting_col, topic_col, sub_topic_col).
                                  Kembalian -1 jika kolom tidak terdeteksi.
        """
        meeting_col = -1
        topic_col = -1
        sub_topic_col = -1
        
        # Cari header di 2 baris pertama
        for row_idx in range(min(2, len(table))):
            row = [cell.lower() for cell in table[row_idx]]
            
            for col_idx, cell in enumerate(row):
                # Deteksi nomor pertemuan
                if any(k in cell for k in ["minggu", "pertemuan", "ke-", "ke ", "mng", "pert", "no"]):
                    if meeting_col == -1:
                        meeting_col = col_idx
                # Deteksi sub pokok bahasan (harus diletakkan sebelum pokok bahasan)
                elif any(k in cell for k in ["sub pokok", "sub bahasan", "sub-topik", "sub topik", "rincian materi"]):
                    if sub_topic_col == -1:
                        sub_topic_col = col_idx
                # Deteksi pokok bahasan / topik
                elif any(k in cell for k in ["pokok bahasan", "materi", "topik", "bahan kajian", "kemampuan akhir"]):
                    if topic_col == -1:
                        topic_col = col_idx
                        
            # Jika sudah menemukan setidaknya meeting dan topic, sudahi pencarian header
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
        
        # 1. Cari angka langsung
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

        Mencari pola baris seperti "Pertemuan 1: Pengenalan OOP", dsb.

        Args:
            raw_text: Teks mentah dokumen.

        Returns:
            List[Dict[str, Any]]: Daftar record hasil parsing teks.
        """
        results: List[Dict[str, Any]] = []
        lines = raw_text.split("\n")
        
        # Pola regex pencarian pertemuan dan materi
        # Mencari string seperti "Pertemuan 1: Pengenalan Class" atau "Minggu 2 - Objek"
        pattern = re.compile(
            r'\b(?:pertemuan|minggu|ke)\s*[-:]?\s*(\d+)\s*[-:]?\s*(.*)', 
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
                
                # Jika konten memuat sub pokok bahasan ditandai titik koma atau kurung
                topic = content
                sub_topic = ""
                
                # Pemecahan sederhana sub_topic dari topik (misal: "Topik utama (sub topik detail)")
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
                
        return sorted(unique_results.values(), key=lambda x: x["meeting_number"])

    def handle_extraction_failure(self, error_info: Dict[str, Any]) -> None:
        """
        Mencatat dan menangani informasi kegagalan ekstraksi PDF.

        Sesuai PRD:
        Logging kegagalan ekstraksi untuk ditinjau ulang secara manual.

        Args:
            error_info: Info kesalahan berupa dictionary (keys: file_path, reason).
        """
        logger.warning(
            f"KEGAGALAN EKSTRAKSI DOKUMEN: file={error_info.get('file_path')}, "
            f"Alasan={error_info.get('reason')}"
        )
