"""
Unit Test untuk Tahap 3 - Document Readers, Text Cleaning, dan PDF Extraction Service.

Modul ini menguji:
1. Class PDFReader (menggunakan mocking)
2. Class FallbackTextReader
3. Class TextCleaner
4. Class PDFExtractionService (menggunakan mocking pada PDFReader)

Menjalankan test:
    pytest tests/test_tahap3_extraction.py -v
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Memastikan direktori project ada di sys.path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from utils.document_reader import DocumentReader
from utils.pdf_reader import PDFReader
from utils.fallback_text_reader import FallbackTextReader
from utils.text_cleaner import TextCleaner
from utils.topic_extractor import TopicExtractor
from services.pdf_extraction_service import PDFExtractionService
from utils.exceptions import PDFExtractionError, PDFTableNotFoundError, TextCleaningError


# ============================================================
# Test Class: TextCleaner
# ============================================================

class TestTextCleaner:
    """Test suite untuk class TextCleaner."""

    def test_to_lowercase(self):
        """Memastikan konversi huruf kecil berjalan benar."""
        cleaner = TextCleaner()
        assert cleaner.to_lowercase("PEMROGRAMAN Objek") == "pemrograman objek"
        assert cleaner.to_lowercase("") == ""
        assert cleaner.to_lowercase(None) == ""

    def test_strip_whitespace(self):
        """Memastikan penghilangan spasi ganda dan trim berjalan benar."""
        cleaner = TextCleaner()
        assert cleaner.strip_whitespace("  halo   dunia  ") == "halo dunia"
        assert cleaner.strip_whitespace("") == ""

    def test_remove_special_characters(self):
        """Memastikan karakter khusus digantikan dengan spasi."""
        cleaner = TextCleaner()
        assert cleaner.remove_special_characters("pbo @2026! #java") == "pbo  2026   java"
        assert cleaner.remove_special_characters("") == ""

    def test_apply_regex_normalization(self):
        """Memastikan normalisasi regex 'pertemuan ke-X' dan romawi berjalan benar."""
        cleaner = TextCleaner()
        
        # Test normalisasi kata Pertemuan/Minggu
        assert cleaner.apply_regex_normalization("pertemuan ke-1") == "1"
        assert cleaner.apply_regex_normalization("Minggu Ke - 5") == "5"
        assert cleaner.apply_regex_normalization("p- 10") == "10"
        
        # Test angka Romawi
        assert cleaner.apply_regex_normalization("Pertemuan ke-I") == "1"
        assert cleaner.apply_regex_normalization("Minggu ke-IV") == "4"
        assert cleaner.apply_regex_normalization("pertemuan ke-xvi") == "16"
        assert cleaner.apply_regex_normalization("materi umum") == "materi umum"

    def test_remove_stopwords(self):
        """Memastikan kata hubung disaring keluar."""
        cleaner = TextCleaner()
        # Default stopwords: dan, yang, untuk, dengan, atau
        assert cleaner.remove_stopwords("kelas dan objek dengan pewarisan") == "kelas objek pewarisan"
        assert cleaner.remove_stopwords("") == ""

    def test_clean_pipeline(self):
        """Memastikan pipeline utama pembersihan berjalan utuh."""
        cleaner = TextCleaner()
        raw_text = "  Pertemuan Ke-1: Pengenalan OOP & Class (dengan Java) dan C++  "
        # 1. Lower: "  pertemuan ke-1: pengenalan oop & class (dengan java) dan c++  "
        # 2. Regex normal: "  1: pengenalan oop & class (dengan java) dan c++  "
        # 3. Special char: "  1  pengenalan oop   class  dengan java  dan c    "
        # 4. Stopwords (dengan, dan): "1 pengenalan oop class java c"
        # 5. Spasi: "1 pengenalan oop class java c"
        cleaned = cleaner.clean(raw_text)
        assert cleaned == "1 pengenalan oop class java c"

    def test_clean_error(self):
        """Memastikan exception di-handle jika input tidak valid."""
        cleaner = TextCleaner()
        # Mengirim tipe data non-string untuk memicu Exception
        with pytest.raises(TextCleaningError):
            cleaner.clean(123)  # type: ignore


# ============================================================
# Test Class: FallbackTextReader
# ============================================================

class TestFallbackTextReader:
    """Test suite untuk class FallbackTextReader."""

    def test_read_success(self, tmp_path):
        """Menguji pembacaan file txt biasa."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("Baris 1\nBaris 2\nBaris 3", encoding="utf-8")
        
        reader = FallbackTextReader(str(file_path))
        assert reader.read() == "Baris 1\nBaris 2\nBaris 3"
        assert reader.extract_raw_text() == "Baris 1\nBaris 2\nBaris 3"
        
        # Test extract_lines
        lines = reader.extract_lines()
        assert len(lines) == 3
        assert lines[0] == "Baris 1"

    def test_extract_tables_empty(self, tmp_path):
        """Memastikan extract_tables mengembalikan list kosong."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("Konten")
        
        reader = FallbackTextReader(str(file_path))
        assert reader.extract_tables() == []


# ============================================================
# Test Class: PDFReader (dengan Mocking)
# ============================================================

class TestPDFReader:
    """Test suite untuk class PDFReader menggunakan mocking pdfplumber & pypdf."""

    @patch("os.path.exists")
    @patch("pdfplumber.open")
    def test_extract_tables_success(self, mock_pdfplumber_open, mock_exists):
        """Memastikan ekstraksi tabel PDF mengembalikan array 3D yang dibersihkan."""
        mock_exists.return_value = True
        
        # Set up mock pdfplumber
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        # Mocking table row data dengan cell None untuk ditest pembersihannya
        mock_page.extract_tables.return_value = [
            [["Minggu ke", "Pokok Bahasan", None], ["1", "OOP Dasar", "Sub 1"]]
        ]
        mock_pdf.pages = [mock_page]
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        reader = PDFReader("dummy.pdf")
        tables = reader.extract_tables()
        
        assert len(tables) == 1
        assert tables[0][0][0] == "Minggu ke"
        # None dibersihkan menjadi ""
        assert tables[0][0][2] == ""
        assert tables[0][1][1] == "OOP Dasar"

    @patch("os.path.exists")
    @patch("pdfplumber.open")
    def test_extract_tables_not_found(self, mock_pdfplumber_open, mock_exists):
        """Memastikan error PDFTableNotFoundError dilempar jika tidak ada tabel terdeteksi."""
        mock_exists.return_value = True
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_tables.return_value = []
        mock_pdf.pages = [mock_page]
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        reader = PDFReader("dummy.pdf")
        with pytest.raises(PDFTableNotFoundError):
            reader.extract_tables()

    @patch("os.path.exists")
    @patch("utils.pdf_reader.PyPdfReader")
    def test_extract_raw_text_success(self, mock_pypdf_reader, mock_exists):
        """Memastikan ekstraksi teks mentah menggunakan pypdf sukses."""
        mock_exists.return_value = True
        
        mock_reader_instance = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Teks Halaman 1"
        mock_reader_instance.pages = [mock_page]
        mock_pypdf_reader.return_value = mock_reader_instance

        reader = PDFReader("dummy.pdf")
        text = reader.extract_raw_text()
        
        assert text == "Teks Halaman 1"
        assert reader.read() == "Teks Halaman 1"


# ============================================================
# Test Class: PDFExtractionService
# ============================================================

class TestPDFExtractionService:
    """Test suite untuk class PDFExtractionService."""

    def test_extract_pokok_bahasan_via_tables(self):
        """Menguji pemrosesan data tabel menjadi list of dict terstruktur."""
        mock_reader = MagicMock(spec=PDFReader)
        # Mock table 3D
        mock_reader.extract_tables.return_value = [
            [
                ["Pertemuan Ke", "Pokok Bahasan/Materi", "Sub Pokok Bahasan"],
                ["Pertemuan 1", "Konsep Class & Object", "Atribut dan Method"],
                ["Minggu Ke - II", "Pewarisan (Inheritance)", "Override method"]
            ]
        ]
        
        service = PDFExtractionService(mock_reader)
        data = service.extract_pokok_bahasan("dummy.pdf")
        
        assert len(data) == 2
        # Pertemuan 1
        assert data[0]["meeting_number"] == 1
        assert data[0]["topic"] == "Konsep Class & Object"
        assert data[0]["sub_topic"] == "Atribut dan Method"
        # Pertemuan 2 (Romawi II -> 2)
        assert data[1]["meeting_number"] == 2
        assert data[1]["topic"] == "Pewarisan"

    def test_extract_pokok_bahasan_only_main_topic_from_materi_cell(self):
        """Memastikan kolom Materi Pembelajaran disingkat menjadi pokok bahasan utama."""
        mock_reader = MagicMock(spec=PDFReader)
        mock_reader.extract_tables.return_value = [
            [
                [
                    "Sesi",
                    "Sub-CP-MK",
                    "Indikator",
                    "Metode",
                    "Materi Pembelajaran (Pustaka)",
                    "Bobot",
                ],
                [
                    "4",
                    "Mahasiswa mampu menjalankan contoh program secara mandiri",
                    "Mampu menjalankan program",
                    "Kuliah, Diskusi, Presentasi",
                    "1. Mencoba\nprogram pada\nbuku referensi\n2.",
                    "5,00%",
                ],
                [
                    "5",
                    "Mahasiswa mampu mengimplementasikan enkapsulasi",
                    "Mampu mengimplementasikan enkapsulasi",
                    "Kuliah, Diskusi, Presentasi",
                    "1. Mendesain\nprogram yang\nmemanfaatkan\nenkapsulasi\nuntuk\npermasalahan\nsederhana",
                    "5,00%",
                ],
            ]
        ]

        service = PDFExtractionService(mock_reader)
        data = service.extract_pokok_bahasan("dummy.pdf")

        assert data[0]["meeting_number"] == 4
        assert data[0]["topic"] == "Praktikum Enkapsulasi"
        assert data[1]["meeting_number"] == 5
        assert data[1]["topic"] == "Praktikum Enkapsulasi"

    def test_extract_pokok_bahasan_via_text_fallback(self):
        """Menguji fallback sukses ke parsing teks biasa jika tabel kosong/error."""
        mock_reader = MagicMock(spec=PDFReader)
        # Bikin extract_tables melempar error agar masuk ke fallback
        mock_reader.extract_tables.side_effect = PDFTableNotFoundError("No table")
        
        # Sediakan teks mentah yang terstruktur
        mock_reader.extract_raw_text.return_value = (
            "Silabus Perkuliahan PBO\n"
            "Pertemuan 1 - Pengenalan OOP dasar (Class Java)\n"
            "Minggu Ke-2: Abstraksi & Polimorfisme\n"
        )
        
        service = PDFExtractionService(mock_reader)
        data = service.extract_pokok_bahasan("dummy.pdf")
        
        assert len(data) == 2
        assert data[0]["meeting_number"] == 1
        assert data[0]["topic"] == "Pengenalan OOP dasar"
        assert data[0]["sub_topic"] == "Class Java"  # sub_topic diekstrak dari kurung
        
        assert data[1]["meeting_number"] == 2
        assert data[1]["topic"] == "Abstraksi & Polimorfisme"
        assert data[1]["sub_topic"] == ""

    def test_extract_pokok_bahasan_failure(self):
        """Menguji pelemparan PDFExtractionError jika semua metode gagal."""
        mock_reader = MagicMock(spec=PDFReader)
        mock_reader.extract_tables.side_effect = Exception("System Error Table")
        mock_reader.extract_raw_text.side_effect = Exception("System Error Text")
        
        service = PDFExtractionService(mock_reader)
        with pytest.raises(PDFExtractionError):
            service.extract_pokok_bahasan("dummy.pdf")

    @patch("os.path.exists")
    @patch("pdfplumber.open")
    def test_extract_multi_page_and_minimum_14_meetings(self, mock_pdfplumber_open, mock_exists):
        """Menguji ekstraksi multi-halaman (11 halaman) yang menghasilkan minimal 14 pertemuan dan menyaring tabel identitas."""
        mock_exists.return_value = True
        mock_pdf = MagicMock()
        
        # Buat 11 halaman tiruan
        mock_pages = []
        
        # Halaman 1-3: Berisi tabel identitas/pustaka (tanpa keyword RPS)
        for i in range(3):
            page = MagicMock()
            page.extract_tables.return_value = [
                [["No", "Buku Referensi"], ["1", "OOP Java 8 - Deitel"]]
            ]
            mock_pages.append(page)
            
        # Halaman 4-11: Berisi tabel silabus RPS pertemuan 1 s/d 14
        meeting_counter = 1
        for i in range(8):
            page = MagicMock()
            # Masing-masing halaman rps berisi 2 pertemuan (total 16, tapi kita batasi sampai 14)
            table_data = [
                ["Pertemuan", "Pokok Bahasan (Topik)", "Sub Pokok Bahasan"]
            ]
            if meeting_counter <= 14:
                table_data.append([f"Sesi {meeting_counter}", f"Topik Ke {meeting_counter}", f"Subtopik {meeting_counter}"])
                meeting_counter += 1
            if meeting_counter <= 14:
                table_data.append([f"Sesi {meeting_counter}", f"Topik Ke {meeting_counter}", f"Subtopik {meeting_counter}"])
                meeting_counter += 1
                
            page.extract_tables.return_value = [table_data]
            mock_pages.append(page)
            
        mock_pdf.pages = mock_pages
        mock_pdfplumber_open.return_value.__enter__.return_value = mock_pdf

        service = PDFExtractionService()
        data = service.extract_pokok_bahasan("dummy.pdf")
        
        # Penegasan (Assertions)
        assert len(data) == 14  # Harus mengekstrak 14 pertemuan (Target 11)
        assert data[0]["meeting_number"] == 1
        assert data[0]["topic"] == "Topik Ke 1"
        assert data[13]["meeting_number"] == 14
        assert data[13]["topic"] == "Topik Ke 14"
        # Memastikan tidak ada data "OOP Java 8 - Deitel" yang menyusup (berhasil difilter)
        for item in data:
            assert "Deitel" not in item["topic"]


class TestTopicExtractor:
    """Menguji modul TopicExtractor (Pembersihan Topik Utama)."""

    def test_clean_topic_with_subtopics_numbering(self):
        """Memastikan TopicExtractor berhasil membersihkan submateri terperinci dengan penomoran."""
        from utils.topic_extractor import TopicExtractor
        extractor = TopicExtractor()

        raw_text = (
            "Classes and Object\n"
            "1. Difference between class and object\n"
            "2. Giving examples of objects\n"
            "3. Making first object in Java"
        )
        cleaned = extractor.clean_topic(raw_text)
        assert cleaned == "Classes and Object"

    def test_clean_topic_with_focus_notes_and_parentheses(self):
        """Memastikan TopicExtractor berhasil menghapus (Fokus ...) dan merapikan kurung."""
        from utils.topic_extractor import TopicExtractor
        extractor = TopicExtractor()

        raw_text_1 = "Konsep Enkapsulasi (Fokus: Setter Getter dan Access Modifier)"
        cleaned_1 = extractor.clean_topic(raw_text_1)
        assert cleaned_1 == "Konsep Enkapsulasi"

        raw_text_2 = "Latihan Program (Latihan: Membuat kelas Mahasiswa)"
        cleaned_2 = extractor.clean_topic(raw_text_2)
        assert cleaned_2 == "Latihan Program"

    def test_clean_topic_with_bullets_and_whitespace(self):
        """Memastikan TopicExtractor berhasil membuang bullet dan menormalkan spasi."""
        from utils.topic_extractor import TopicExtractor
        extractor = TopicExtractor()

        raw_text = "  •  Konsep Inheritance  \n  - Submateri: Extends keyword"
        cleaned = extractor.clean_topic(raw_text)
        assert cleaned == "Konsep Inheritance"

    def test_clean_topic_with_duplicate_words(self):
        """Memastikan TopicExtractor menghilangkan kata duplikat berurutan."""
        from utils.topic_extractor import TopicExtractor
        extractor = TopicExtractor()

        raw_text = "Polimorfisme Polimorfisme (OOP)"
        cleaned = extractor.clean_topic(raw_text)
        assert cleaned == "Polimorfisme"

    def test_extract_main_topic_with_domain_fallback(self):
        """Memastikan regex heading menangani cell yang berisi aktivitas/detail saja."""
        extractor = TopicExtractor()

        raw_text = "1. Mencoba\nprogram pada\nbuku referensi\n2."
        assert extractor.extract_main_topic(raw_text) == "Praktikum Enkapsulasi"

        raw_text_2 = "Making connection\nwith database\n1. JDBC\n2. Oracle/mysql"
        assert extractor.clean_topic(raw_text_2) == "Making Connection with Database"

    def test_remove_helpers(self):
        """Memastikan helper wajib tersedia dan bekerja pada kasus umum."""
        extractor = TopicExtractor()

        assert extractor.remove_numbering("1. Konsep Enkapsulasi") == "Konsep Enkapsulasi"
        assert extractor.remove_bullet("• Konsep Pewarisan") == "Konsep Pewarisan"
        assert extractor.remove_focus_note("Konsep Enkapsulasi (Fokus: setter getter)") == "Konsep Enkapsulasi"
        assert extractor.remove_parentheses("Polimorfisme (OOP)") == "Polimorfisme"
        assert extractor.normalize_whitespace("GUI\n&\tSWING") == "GUI & SWING"

    def test_extract_sample_pdf_rps_main_topics(self):
        """Membandingkan hasil ekstraksi dengan PDF RPS contoh lokal."""
        pdf_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "uploads",
            "rps_active_1782904682.pdf",
        )
        if not os.path.exists(pdf_path):
            pytest.skip("PDF RPS contoh tidak tersedia di workspace.")

        data = PDFExtractionService().extract_pokok_bahasan(pdf_path)
        topics = {item["meeting_number"]: item["topic"] for item in data}

        assert len(data) == 14
        assert topics[1] == "Kontrak Kuliah"
        assert topics[2] == "Classes and Object"
        assert topics[3] == "Konsep Enkapsulasi"
        assert topics[4] == "Praktikum Enkapsulasi"
        assert topics[5] == "Praktikum Enkapsulasi"
        assert topics[6] == "Konsep Pewarisan"
        assert topics[7] == "Konsep Pewarisan"
        assert topics[8] == "Exception Handling"
        assert topics[9] == "Object Persistence"
        assert topics[10] == "Multithreading"
        assert topics[11] == "Using Java Library"
        assert topics[12] == "Collections"
        assert topics[13] == "Making Connection with Database"
        assert topics[14] == "GUI & SWING"

        banned_fragments = ("buku referensi", "fokus", "latihan", "contoh", "\n")
        for topic in topics.values():
            assert all(fragment not in topic.lower() for fragment in banned_fragments)
