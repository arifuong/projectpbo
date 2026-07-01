"""
Unit Test untuk Tahap 4 s/d 9 - Service Layer & Logika Bisnis (Refactored Single Course).

Modul ini menguji:
1. RPSManager
2. BAPManager
3. KeywordMatcher
4. Validator
5. ReportGenerator
6. DashboardService
7. FileUploadHandler

Menjalankan test:
    pytest tests/test_tahap4_to_9_services.py -v
"""

import os
import sys
from datetime import datetime, date
import pytest
from unittest.mock import MagicMock, patch

# Memastikan direktori project ada di sys.path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from models.rps import RPS
from models.bap import BAP
from models.validation_result import ValidationResult
from models.report import Report

from repositories.rps_repository import RPSRepository
from repositories.bap_repository import BAPRepository
from repositories.validation_repository import ValidationRepository
from repositories.upload_repository import UploadRepository
from repositories.dashboard_repository import DashboardRepository

from services.rps_manager import RPSManager
from services.bap_manager import BAPManager
from services.keyword_matcher import KeywordMatcher
from services.validator import Validator
from services.report_generator import ReportGenerator
from services.dashboard_service import DashboardService
from services.file_upload_handler import FileUploadHandler

from utils.text_cleaner import TextCleaner
from utils.exceptions import (
    DuplicateMeetingError,
    MeetingNumberExceededError,
    ValidationError,
    FileValidationError,
    FileUploadError
)


# ============================================================
# Test Class: RPSManager (Tahap 4)
# ============================================================

class TestRPSManager:
    """Test suite untuk class RPSManager."""

    def test_save_rps_success(self):
        """Memastikan data RPS berhasil disimpan massal setelah dibersihkan."""
        rps_repo = MagicMock(spec=RPSRepository)
        cleaner = TextCleaner()

        rps_repo.replace_all_rps.return_value = True

        manager = RPSManager(rps_repo, cleaner)
        
        rps_list = [RPS(1, "Topik 1 dan 2")]
        success = manager.save_rps(rps_list, "source.pdf", "/path/source.pdf", 120)

        assert success is True
        # Topik harus dibersihkan (stopwords dihapus)
        assert rps_list[0].cleaned_topic == "topik 1 2"
        rps_repo.replace_all_rps.assert_called_once_with(rps_list, "source.pdf", "/path/source.pdf", 120)

    def test_validate_unique_meeting_number(self):
        """Menguji validasi nomor pertemuan unik."""
        rps_repo = MagicMock(spec=RPSRepository)
        cleaner = TextCleaner()

        # Mock pertemuan 1 sudah ada, pertemuan 2 belum
        rps_repo.exists.side_effect = lambda m: m == 1

        manager = RPSManager(rps_repo, cleaner)
        assert manager.validate_unique_meeting_number(1) is False
        assert manager.validate_unique_meeting_number(2) is True


# ============================================================
# Test Class: BAPManager (Tahap 5)
# ============================================================

class TestBAPManager:
    """Test suite untuk class BAPManager."""

    def test_add_bap_success(self):
        """Memastikan data BAP berhasil ditambahkan."""
        bap_repo = MagicMock(spec=BAPRepository)
        rps_repo = MagicMock(spec=RPSRepository)
        cleaner = TextCleaner()

        bap_repo.exists.return_value = False
        rps_repo.count_all.return_value = 16
        bap_repo.create.return_value = 10

        manager = BAPManager(bap_repo, rps_repo, cleaner)
        bap = BAP(1, "2024-09-15", "Topik 1 dan Pewarisan")
        
        bap_id = manager.add_bap(bap)
        
        assert bap_id == 10
        assert bap.cleaned_material == "topik 1 pewarisan"

    def test_add_bap_duplicate_meeting(self):
        """Memastikan error jika nomor pertemuan BAP duplikat (BR-02)."""
        bap_repo = MagicMock(spec=BAPRepository)
        rps_repo = MagicMock(spec=RPSRepository)
        cleaner = TextCleaner()

        bap_repo.exists.return_value = True  # Pertemuan duplikat

        manager = BAPManager(bap_repo, rps_repo, cleaner)
        bap = BAP(1, "2024-09-15", "Materi")
        
        with pytest.raises(DuplicateMeetingError):
            manager.add_bap(bap)

    def test_add_bap_meeting_exceeded(self):
        """Memastikan error jika nomor pertemuan BAP melebihi total RPS (BR-02)."""
        bap_repo = MagicMock(spec=BAPRepository)
        rps_repo = MagicMock(spec=RPSRepository)
        cleaner = TextCleaner()

        bap_repo.exists.return_value = False
        rps_repo.count_all.return_value = 14  # Max 14 pertemuan

        manager = BAPManager(bap_repo, rps_repo, cleaner)
        bap = BAP(15, "2024-09-15", "Materi")  # Pertemuan 15 (melebihi)
        
        with pytest.raises(MeetingNumberExceededError):
            manager.add_bap(bap)


# ============================================================
# Test Class: KeywordMatcher (Tahap 6)
# ============================================================

class TestKeywordMatcher:
    """Test suite untuk class KeywordMatcher."""

    def test_extract_keywords(self):
        """Menguji pemecahan kata kunci."""
        matcher = KeywordMatcher()
        keywords = matcher.extract_keywords("java class inheritance")
        assert len(keywords) == 3
        assert "java" in keywords

    def test_calculate_similarity(self):
        """Menguji perhitungan skor kemiripan."""
        matcher = KeywordMatcher()
        
        score_identical = matcher.calculate_similarity("java class", "java class")
        assert score_identical == 1.0
        
        score_partial = matcher.calculate_similarity("java class", "java class object")
        assert 0.0 < score_partial < 1.0
        
        assert matcher.calculate_similarity("", "java") == 0.0

    def test_match_logic(self):
        """Menguji pemrosesan status is_match berdasarkan threshold."""
        matcher = KeywordMatcher(threshold=0.7)
        
        res = matcher.match("pemrograman berorientasi objek", "pemrograman berorientasi objek")
        assert res["is_match"] is True
        assert res["similarity_score"] == 1.0
        assert "objek" in res["matched_keywords"]


# ============================================================
# Test Class: Validator (Tahap 7)
# ============================================================

class TestValidator:
    """Test suite untuk class Validator (Validation Engine)."""

    def test_run_validation_success_all_match(self):
        """Menguji status kesesuaian validasi berjalan sukses (SESUAI)."""
        matcher = KeywordMatcher(threshold=0.7)
        rps_repo = MagicMock(spec=RPSRepository)
        bap_repo = MagicMock(spec=BAPRepository)
        val_repo = MagicMock(spec=ValidationRepository)

        rps_list = [
            RPS(1, "Pengenalan OOP", cleaned_topic="pengenalan oop", rps_id=10)
        ]
        bap_list = [
            BAP(1, "2024-09-10", "Pengenalan OOP", cleaned_material="pengenalan oop", bap_id=20)
        ]

        rps_repo.get_all.return_value = rps_list
        bap_repo.get_all.return_value = bap_list
        val_repo.save_batch.return_value = True

        validator = Validator(matcher, rps_repo, bap_repo, val_repo)
        results = validator.run_validation()

        assert len(results) == 1
        assert results[0].status == "SESUAI"
        assert results[0].similarity_score == 100.0
        val_repo.save_batch.assert_called_once()

    def test_run_validation_shuffled_material(self):
        """Menguji pendeteksian materi diacak / tertukar urutan (TIDAK_SESUAI)."""
        matcher = KeywordMatcher(threshold=0.7)
        rps_repo = MagicMock(spec=RPSRepository)
        bap_repo = MagicMock(spec=BAPRepository)
        val_repo = MagicMock(spec=ValidationRepository)

        rps_list = [
            RPS(1, "Pengenalan OOP", cleaned_topic="pengenalan oop", rps_id=10),
            RPS(2, "Inheritance Java", cleaned_topic="inheritance java", rps_id=11)
        ]
        bap_list = [
            BAP(1, "2024-09-10", "Inheritance Java", cleaned_material="inheritance java", bap_id=20)
        ]

        rps_repo.get_all.return_value = rps_list
        bap_repo.get_all.return_value = bap_list

        validator = Validator(matcher, rps_repo, bap_repo, val_repo)
        results = validator.run_validation()

        assert len(results) == 2
        assert results[0].status == "TIDAK_SESUAI"
        assert "diacak" in results[0].notes.lower()
        assert results[1].status == "PENDING"

    def test_run_validation_missing_data_error(self):
        """Memastikan ValidationError dilempar jika data kosong."""
        matcher = MagicMock()
        rps_repo = MagicMock(spec=RPSRepository)
        bap_repo = MagicMock(spec=BAPRepository)
        val_repo = MagicMock(spec=ValidationRepository)

        rps_repo.get_all.return_value = []
        bap_repo.get_all.return_value = []

        validator = Validator(matcher, rps_repo, bap_repo, val_repo)
        with pytest.raises(ValidationError):
            validator.run_validation()


# ============================================================
# Test Class: ReportGenerator (Tahap 8)
# ============================================================

class TestReportGenerator:
    """Test suite untuk class ReportGenerator."""

    def test_generate_report_success(self):
        """Memastikan objek Report disusun dengan data ringkasan yang benar."""
        rps_repo = MagicMock(spec=RPSRepository)
        bap_repo = MagicMock(spec=BAPRepository)
        val_repo = MagicMock(spec=ValidationRepository)

        rps_list = [RPS(1, "T1"), RPS(2, "T2")]
        bap_list = [BAP(1, "2024-09-10", "T1")]
        
        val_results = [
            ValidationResult(1, 100.0, "SESUAI", rps_id=1, bap_id=1),
            ValidationResult(2, 0.0, "PENDING", rps_id=2, bap_id=None)
        ]

        rps_repo.get_all.return_value = rps_list
        bap_repo.get_all.return_value = bap_list
        val_repo.get_all.return_value = val_results

        generator = ReportGenerator(rps_repo, bap_repo, val_repo)
        report = generator.generate_report()

        assert report.compliance_percentage == 50.0
        assert report.total_meetings == 2
        assert report.matched_count == 1
        assert len(report.missing_list) == 1
        assert report.missing_list[0]["meeting_number"] == 2


# ============================================================
# Test Class: DashboardService (Tahap 9)
# ============================================================

class TestDashboardService:
    """Test suite untuk class DashboardService."""

    def test_dashboard_service_routing(self):
        """Memastikan pemanggilan data diteruskan ke DashboardRepository."""
        repo = MagicMock(spec=DashboardRepository)
        service = DashboardService(repo)

        repo.get_aggregate_stats.return_value = {"total_rps": 14}
        assert service.get_summary_statistics()["total_rps"] == 14

        repo.get_top_mismatched.return_value = [{"meeting_number": 1}]
        assert len(service.get_top_mismatched_meetings(5)) == 1

        repo.get_compliance_chart.return_value = [{"status": "SESUAI", "count": 10}]
        assert len(service.get_compliance_chart_data()) == 1


# ============================================================
# Test Class: FileUploadHandler
# ============================================================

class TestFileUploadHandler:
    """Test suite untuk class FileUploadHandler."""

    def test_validate_file_ok(self, tmp_path):
        """Menguji validasi file PDF yang sukses."""
        repo = MagicMock(spec=UploadRepository)
        file_path = tmp_path / "valid.pdf"
        file_path.write_bytes(b"%PDF-1.4 dummy content")
        
        handler = FileUploadHandler(repo, str(tmp_path), max_size_mb=10)
        assert handler.validate_file(str(file_path)) is True

    def test_validate_file_invalid_ext(self, tmp_path):
        """Memastikan penolakan ekstensi non-PDF."""
        repo = MagicMock(spec=UploadRepository)
        file_path = tmp_path / "invalid.txt"
        file_path.write_text("dummy")
        
        handler = FileUploadHandler(repo, str(tmp_path))
        with pytest.raises(FileValidationError):
            handler.validate_file(str(file_path))

    def test_validate_file_too_large(self, tmp_path):
        """Memastikan penolakan ukuran file yang melebihi batas."""
        repo = MagicMock(spec=UploadRepository)
        file_path = tmp_path / "large.pdf"
        file_path.write_bytes(b"0" * (2 * 1024 * 1024))
        
        handler = FileUploadHandler(repo, str(tmp_path), max_size_mb=1)
        with pytest.raises(FileValidationError):
            handler.validate_file(str(file_path))

    @patch("shutil.copy2")
    def test_save_file_success(self, mock_copy, tmp_path):
        """Menguji penyimpanan file fisik dan pencatatan riwayat unggah."""
        repo = MagicMock(spec=UploadRepository)
        src_path = tmp_path / "source.pdf"
        src_path.write_bytes(b"%PDF-1.4 content")
        
        handler = FileUploadHandler(repo, str(tmp_path / "uploads"))
        dest_path = handler.save_file(str(src_path))

        assert "rps_active_" in dest_path
        mock_copy.assert_called_once()
        repo.create.assert_called_once()
        args = repo.create.call_args[1]
        assert args["upload_status"] == "SUCCESS"
