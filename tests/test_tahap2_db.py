"""
Unit Test untuk Tahap 2 - Database Connection, Entities, dan Repositories (Refactored Single Course).

Modul ini menguji:
1. Class Entity: RPS, BAP, ValidationResult, Report
2. Class DatabaseConnection (menggunakan mocking)
3. Kelas-kelas Repository (RPSRepository, BAPRepository, ValidationRepository, UploadRepository) menggunakan mocking

Menjalankan test:
    pytest tests/test_tahap2_db.py -v
"""

import os
import sys
from datetime import datetime, date
import pytest
from unittest.mock import MagicMock, patch
import mysql.connector

# Memastikan direktori project ada di sys.path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from models.rps import RPS
from models.bap import BAP
from models.validation_result import ValidationResult
from models.report import Report

from database.connection import DatabaseConnection
from config.config import DatabaseConfig

from repositories.rps_repository import RPSRepository
from repositories.bap_repository import BAPRepository
from repositories.validation_repository import ValidationRepository
from repositories.upload_repository import UploadRepository

from utils.exceptions import (
    DatabaseConnectionError,
    DatabaseQueryError,
    DatabaseTransactionError
)


# ============================================================
# Test Class: Entities / Models
# ============================================================

class TestEntities:
    """Test suite untuk kelas-kelas Entity/Model."""

    def test_rps_entity(self):
        """Menguji entitas RPS."""
        created_time = datetime.now()
        rps = RPS(
            meeting_number=1,
            topic="Pengenalan OOP",
            sub_topic="Class dan Object",
            cleaned_topic="pengenalan oop",
            source_file="rps_pbo.pdf",
            rps_id=10,
            created_at=created_time,
            updated_at=created_time
        )

        assert rps.rps_id == 10
        assert rps.meeting_number == 1
        assert rps.topic == "Pengenalan OOP"
        assert rps.sub_topic == "Class dan Object"
        assert rps.cleaned_topic == "pengenalan oop"
        assert rps.source_file == "rps_pbo.pdf"

        # Test dict conversion
        d = rps.to_dict()
        assert d["rps_id"] == 10
        assert d["topic"] == "Pengenalan OOP"

        rps_clone = RPS.from_dict(d)
        assert rps_clone.rps_id == 10
        assert rps_clone.topic == "Pengenalan OOP"
        assert repr(rps) == "RPS(rps_id=10, meeting_number=1, topic='Pengenalan OOP')"

    def test_bap_entity(self):
        """Menguji entitas BAP."""
        meeting_date = date(2024, 9, 10)
        bap = BAP(
            meeting_number=1,
            meeting_date=meeting_date,
            material_taught="Pendahuluan OOP dasar kelas dan objek",
            cleaned_material="pendahuluan oop dasar kelas objek",
            bap_id=20
        )

        assert bap.bap_id == 20
        assert bap.meeting_number == 1
        assert bap.meeting_date == meeting_date
        assert bap.material_taught == "Pendahuluan OOP dasar kelas dan objek"
        assert bap.cleaned_material == "pendahuluan oop dasar kelas objek"

        # Test string date initialization
        bap_str_date = BAP(
            meeting_number=1,
            meeting_date="2024-09-10",
            material_taught="Materi"
        )
        assert bap_str_date.meeting_date == meeting_date

        # Test dict conversion
        d = bap.to_dict()
        assert d["bap_id"] == 20
        assert d["meeting_date"] == "2024-09-10"

        bap_clone = BAP.from_dict(d)
        assert bap_clone.bap_id == 20
        assert bap_clone.meeting_date == meeting_date
        assert repr(bap) == "BAP(bap_id=20, meeting_number=1, meeting_date='2024-09-10')"

    def test_validation_result_entity(self):
        """Menguji entitas ValidationResult."""
        created_time = datetime.now()
        vr = ValidationResult(
            meeting_number=1,
            similarity_score=85.5,
            status="SESUAI",
            rps_id=10,
            bap_id=20,
            notes="Materi cocok secara signifikan",
            validation_id=30,
            validated_at=created_time
        )

        assert vr.validation_id == 30
        assert vr.meeting_number == 1
        assert vr.similarity_score == 85.5
        assert vr.status == "SESUAI"
        assert vr.rps_id == 10
        assert vr.bap_id == 20
        assert vr.notes == "Materi cocok secara signifikan"

        d = vr.to_dict()
        assert d["validation_id"] == 30
        assert d["similarity_score"] == 85.5

        vr_clone = ValidationResult.from_dict(d)
        assert vr_clone.validation_id == 30
        assert vr_clone.similarity_score == 85.5
        assert repr(vr) == "ValidationResult(validation_id=30, meeting_number=1, status='SESUAI', similarity_score=85.5)"

    def test_report_entity(self):
        """Menguji entitas Report."""
        created_time = datetime.now()
        report = Report(
            compliance_percentage=92.3,
            total_meetings=16,
            matched_count=14,
            mismatched_list=[{"meeting_number": 5, "notes": "diacak"}],
            missing_list=[{"meeting_number": 16, "topic": "UAS"}],
            results=[{"meeting_number": 1, "status": "SESUAI"}],
            generated_at=created_time
        )

        assert report.compliance_percentage == 92.3
        assert report.total_meetings == 16
        assert report.matched_count == 14
        assert len(report.mismatched_list) == 1
        assert len(report.missing_list) == 1
        assert len(report.results) == 1

        d = report.to_dict()
        assert d["compliance_percentage"] == 92.3
        
        summary = report.get_summary()
        assert "Laporan Hasil Evaluasi Pembelajaran Aktif" in summary
        assert "92.30%" in summary
        assert repr(report) == "Report(compliance_percentage=92.30%)"


# ============================================================
# Test Class: DatabaseConnection (dengan Mocking)
# ============================================================

class TestDatabaseConnection:
    """Test suite untuk class DatabaseConnection menggunakan mock koneksi MySQL."""

    @patch("mysql.connector.pooling.MySQLConnectionPool")
    def test_connection_pool_initialization(self, mock_pool_class):
        """Memastikan connection pool diinisialisasi saat class dibuat."""
        config = DatabaseConfig(host="localhost", user="root", password="", database="test_db")
        db_conn = DatabaseConnection(config)

        mock_pool_class.assert_called_once()
        assert db_conn._pool is not None

    @patch("mysql.connector.pooling.MySQLConnectionPool")
    def test_get_connection_success(self, mock_pool_class):
        """Memastikan get_connection berhasil meminjam koneksi dari pool."""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_conn.is_connected.return_value = True
        mock_pool.get_connection.return_value = mock_conn
        mock_pool_class.return_value = mock_pool

        config = DatabaseConfig()
        db_conn = DatabaseConnection(config)
        
        conn = db_conn.get_connection()
        assert conn is mock_conn
        mock_pool.get_connection.assert_called_once()

    @patch("mysql.connector.pooling.MySQLConnectionPool")
    def test_execute_query_select(self, mock_pool_class):
        """Memastikan execute_query berhasil mengembalikan list of dict."""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        
        mock_cursor.description = [("col1", None, None, None, None, None, None)]
        mock_cursor.fetchall.return_value = [{"meeting_number": 1, "topic": "IF101"}]
        
        mock_conn.cursor.return_value = mock_cursor
        mock_pool.get_connection.return_value = mock_conn
        mock_pool_class.return_value = mock_pool

        config = DatabaseConfig()
        db_conn = DatabaseConnection(config)
        
        results = db_conn.execute_query("SELECT * FROM rps WHERE meeting_number = %s", (1,))
        
        assert len(results) == 1
        assert results[0]["topic"] == "IF101"
        mock_cursor.execute.assert_called_once_with("SELECT * FROM rps WHERE meeting_number = %s", (1,))
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch("mysql.connector.pooling.MySQLConnectionPool")
    def test_execute_non_query_insert(self, mock_pool_class):
        """Memastikan execute_non_query berhasil mengembalikan lastrowid."""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 12
        
        mock_conn.cursor.return_value = mock_cursor
        mock_pool.get_connection.return_value = mock_conn
        mock_pool_class.return_value = mock_pool

        config = DatabaseConfig()
        db_conn = DatabaseConnection(config)
        
        last_id = db_conn.execute_non_query("INSERT INTO rps ...", ("params",))
        assert last_id == 12
        mock_conn.commit.assert_called_once()

    @patch("mysql.connector.pooling.MySQLConnectionPool")
    def test_execute_transaction_success(self, mock_pool_class):
        """Memastikan transaksi berhasil dicommit secara utuh."""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        
        mock_conn.cursor.return_value = mock_cursor
        mock_pool.get_connection.return_value = mock_conn
        mock_pool_class.return_value = mock_pool

        config = DatabaseConfig()
        db_conn = DatabaseConnection(config)
        
        queries = [
            ("INSERT INTO rps ...", (1, "Topik 1")),
            ("INSERT INTO rps ...", (2, "Topik 2"))
        ]
        
        success = db_conn.execute_transaction(queries)
        
        assert success is True
        assert mock_cursor.execute.call_count == 2
        mock_conn.commit.assert_called_once()
        mock_conn.rollback.assert_not_called()

    @patch("mysql.connector.pooling.MySQLConnectionPool")
    def test_execute_transaction_rollback(self, mock_pool_class):
        """Memastikan transaksi dibatalkan (rollback) jika terjadi error."""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        
        mock_cursor.execute.side_effect = [None, mysql.connector.Error("SQL Syntax Error")]
        
        mock_conn.cursor.return_value = mock_cursor
        mock_pool.get_connection.return_value = mock_conn
        mock_pool_class.return_value = mock_pool

        config = DatabaseConfig()
        db_conn = DatabaseConnection(config)
        
        queries = [
            ("INSERT INTO rps ...", (1, "Topik 1")),
            ("INSERT INTO rps INVALID...", (2, "Topik 2"))
        ]
        
        with pytest.raises(DatabaseTransactionError):
            db_conn.execute_transaction(queries)
            
        mock_conn.rollback.assert_called_once()
        mock_conn.commit.assert_not_called()


# ============================================================
# Test Class: Repositories (dengan Mocking)
# ============================================================

class TestRepositories:
    """Test suite untuk menguji semua Repository menggunakan mock DatabaseConnection."""

    def test_rps_repository(self):
        """Menguji CRUD di RPSRepository."""
        db_mock = MagicMock(spec=DatabaseConnection)
        repo = RPSRepository(db_mock)

        # Test Save Batch
        rps_list = [
            RPS(1, "OOP Intro"),
            RPS(2, "Inheritance")
        ]
        db_mock.execute_transaction.return_value = True
        success = repo.save_batch(rps_list)
        assert success is True
        
        # Test Get all
        db_mock.execute_query.return_value = [
            {"rps_id": 1, "meeting_number": 1, "topic": "OOP Intro", "sub_topic": "", "cleaned_topic": "", "source_file": "", "created_at": None, "updated_at": None},
            {"rps_id": 2, "meeting_number": 2, "topic": "Inheritance", "sub_topic": "", "cleaned_topic": "", "source_file": "", "created_at": None, "updated_at": None}
        ]
        list_rps = repo.get_all()
        assert len(list_rps) == 2
        assert list_rps[0].topic == "OOP Intro"

    def test_bap_repository(self):
        """Menguji CRUD di BAPRepository."""
        db_mock = MagicMock(spec=DatabaseConnection)
        repo = BAPRepository(db_mock)

        bap = BAP(1, "2024-09-10", "Belajar OOP Intro")
        
        # Test Create
        db_mock.execute_non_query.return_value = 100
        bap_id = repo.create(bap)
        assert bap_id == 100
        assert bap.bap_id == 100

        # Test count all
        db_mock.execute_query.return_value = [{"total": 14}]
        count = repo.count_all()
        assert count == 14

    def test_validation_repository(self):
        """Menguji CRUD di ValidationRepository."""
        db_mock = MagicMock(spec=DatabaseConnection)
        repo = ValidationRepository(db_mock)

        vr = ValidationResult(1, 90.0, "SESUAI", rps_id=1, bap_id=1)
        
        # Test save
        db_mock.execute_non_query.return_value = 1
        vid = repo.save(vr)
        assert vid == 1
        
        # Test save_batch
        results = [vr]
        db_mock.execute_transaction.return_value = True
        success = repo.save_batch(results)
        assert success is True
        db_mock.execute_transaction.assert_called_once()

    def test_upload_repository(self):
        """Menguji CRUD di UploadRepository."""
        db_mock = MagicMock(spec=DatabaseConnection)
        repo = UploadRepository(db_mock)

        # Test create history
        db_mock.execute_non_query.return_value = 7
        upload_id = repo.create("file.pdf", "/path/file.pdf", 250, "SUCCESS")
        assert upload_id == 7
        
        # Test get_all
        db_mock.execute_query.return_value = [
            {"upload_id": 7, "file_name": "file.pdf", "file_path": "/path/file.pdf", "file_size_kb": 250, "upload_status": "SUCCESS", "error_message": None, "uploaded_at": None}
        ]
        history = repo.get_all()
        assert len(history) == 1
        assert history[0]["file_name"] == "file.pdf"
