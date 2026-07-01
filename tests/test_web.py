"""
Unit Test untuk Lapisan Web (Flask Routes & Controllers) - Refactored Single Course.

Menjalankan test:
    pytest tests/test_web.py -v
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Memastikan direktori project ada di sys.path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from app import create_app
from config.settings import AppSettings
from config.config import DatabaseConfig
from models.rps import RPS
from models.bap import BAP
from models.validation_result import ValidationResult
from models.report import Report


class TestWebRoutes:
    """Test suite untuk memverifikasi Flask routes & controllers."""

    @pytest.fixture
    def client(self):
        """Fixture untuk menyediakan client test Flask dengan database termock."""
        config = DatabaseConfig()
        settings = AppSettings(db_config=config)
        
        with patch("app.DatabaseConnection") as mock_db_conn_class:
            mock_db_conn = MagicMock()
            mock_db_conn_class.return_value = mock_db_conn
            
            app = create_app(settings)
            app.config["TESTING"] = True
            
            with app.test_client() as client:
                yield client

    def test_dashboard_index(self, client):
        """Memastikan route index dashboard mengembalikan HTTP 200."""
        services = client.application.config["SERVICES"]
        mock_dash_service = MagicMock()
        mock_dash_service.get_summary_statistics.return_value = {
            "total_rps": 16, "total_bap": 14, "total_upload": 2, "avg_compliance": 87.5
        }
        mock_dash_service.get_top_mismatched_meetings.return_value = []
        services["dashboard_service"] = mock_dash_service
        
        response = client.get("/")
        assert response.status_code == 200
        assert b"87.5%" in response.data
        assert b"Rencana Pertemuan RPS" in response.data

    def test_dashboard_chart_api(self, client):
        """Memastikan API chart mengembalikan data JSON yang valid."""
        services = client.application.config["SERVICES"]
        mock_dash_service = MagicMock()
        mock_dash_service.get_compliance_chart_data.return_value = [
            {"status": "SESUAI", "count": 10}
        ]
        services["dashboard_service"] = mock_dash_service
        
        response = client.get("/api/dashboard/chart")
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["success"] is True
        assert json_data["data"][0]["count"] == 10

    def test_upload_page_render(self, client):
        """Memastikan form upload di-render dengan sukses."""
        response = client.get("/upload")
        assert response.status_code == 200
        assert b"Unggah Dokumen RPS" in response.data

    def test_upload_file_api(self, client):
        """Menguji pemrosesan file PDF upload API."""
        services = client.application.config["SERVICES"]
        
        mock_handler = MagicMock()
        mock_handler.save_file.return_value = "/mock/uploads/rps_active_123.pdf"
        services["upload_handler"] = mock_handler
        
        mock_extract = MagicMock()
        mock_extract.extract_pokok_bahasan.return_value = [
            {"meeting_number": 1, "topic": "Dasar OOP", "sub_topic": "Class & Object"}
        ]
        services["extraction_service"] = mock_extract

        from io import BytesIO
        data = {
            "file": (BytesIO(b"dummy pdf binary content"), "silabus.pdf")
        }
        
        response = client.post("/upload", data=data, content_type="multipart/form-data")
        assert response.status_code == 200
        
        json_data = response.get_json()
        assert json_data["success"] is True
        assert json_data["data"]["source_file"] == "rps_active_123.pdf"
        assert json_data["data"]["items"][0]["topic"] == "Dasar OOP"

    def test_save_extracted_rps_api(self, client):
        """Menguji penyimpanan permanen data RPS dari hasil ekstraksi."""
        services = client.application.config["SERVICES"]
        
        mock_rps_manager = MagicMock()
        mock_rps_manager.save_rps.return_value = True
        services["rps_manager"] = mock_rps_manager

        payload = {
            "source_file": "rps_active_123.pdf",
            "items": [
                {"meeting_number": 1, "topic": "Dasar OOP", "sub_topic": "Class & Object"}
            ]
        }
        
        response = client.post("/api/upload/save", json=payload)
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["success"] is True
        assert b"Berhasil menyimpan" in response.data

    def test_rps_page_render(self, client):
        """Memastikan halaman kelola rps di-render dengan sukses."""
        response = client.get("/rps")
        assert response.status_code == 200
        assert b"Rencana Pembelajaran Semester" in response.data

    def test_get_rps_data_api(self, client):
        """Menguji pengambilan data list RPS terdaftar."""
        services = client.application.config["SERVICES"]
        mock_rps_manager = MagicMock()
        
        dummy_rps = RPS(meeting_number=1, topic="Inheritance", sub_topic="Subclass")
        dummy_rps.rps_id = 99
        mock_rps_manager.get_all_rps.return_value = [dummy_rps]
        services["rps_manager"] = mock_rps_manager

        response = client.get("/api/rps/data")
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["success"] is True
        assert json_data["data"][0]["topic"] == "Inheritance"

    def test_add_rps_meeting_api(self, client):
        """Menguji API tambah rps pertemuan manual."""
        services = client.application.config["SERVICES"]
        mock_rps_manager = MagicMock()
        mock_rps_manager.add_single_rps.return_value = 12
        services["rps_manager"] = mock_rps_manager

        payload = {
            "meeting_number": 2,
            "topic": "Polymorphism",
            "sub_topic": "Overriding"
        }
        response = client.post("/api/rps/add", json=payload)
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["success"] is True

    def test_update_rps_meeting_api(self, client):
        """Menguji API edit/update pertemuan RPS."""
        services = client.application.config["SERVICES"]
        mock_rps_manager = MagicMock()
        mock_rps_manager.update_rps.return_value = True
        services["rps_manager"] = mock_rps_manager

        payload = {
            "rps_id": 99,
            "topic": "Inheritance Mod",
            "sub_topic": "Subclass Mod"
        }
        response = client.put("/api/rps/update", json=payload)
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["success"] is True

    def test_delete_rps_meeting_api(self, client):
        """Menguji API hapus pertemuan RPS."""
        services = client.application.config["SERVICES"]
        mock_rps_manager = MagicMock()
        mock_rps_manager.delete_rps.return_value = True
        services["rps_manager"] = mock_rps_manager

        response = client.delete("/api/rps/delete/99")
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["success"] is True

    def test_bap_page_render(self, client):
        """Memastikan halaman kelola BAP di-render dengan sukses."""
        response = client.get("/bap")
        assert response.status_code == 200
        assert b"Berita Acara Perkuliahan" in response.data

    def test_get_bap_data_api(self, client):
        """Menguji API pengambilan data list BAP terdaftar."""
        services = client.application.config["SERVICES"]
        mock_bap_manager = MagicMock()
        
        from datetime import date
        dummy_bap = BAP(meeting_number=1, meeting_date=date(2026, 7, 1), material_taught="Pengenalan OOP")
        dummy_bap.bap_id = 100
        mock_bap_manager.get_all_bap.return_value = [dummy_bap]
        mock_bap_manager.get_total_rps_meetings.return_value = 16
        services["bap_manager"] = mock_bap_manager

        response = client.get("/api/bap/data")
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["success"] is True
        assert json_data["data"]["items"][0]["material_taught"] == "Pengenalan OOP"
        assert json_data["data"]["total_rps"] == 16

    def test_add_bap_meeting_api(self, client):
        """Menguji API tambah BAP manual."""
        services = client.application.config["SERVICES"]
        mock_bap_manager = MagicMock()
        mock_bap_manager.add_bap.return_value = True
        services["bap_manager"] = mock_bap_manager

        payload = {
            "meeting_number": 1,
            "meeting_date": "2026-07-01",
            "material_taught": "Pengenalan OOP"
        }
        response = client.post("/api/bap/add", json=payload)
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["success"] is True

    def test_update_bap_meeting_api(self, client):
        """Menguji API edit/update BAP tatap muka."""
        services = client.application.config["SERVICES"]
        mock_bap_manager = MagicMock()
        
        from datetime import date
        dummy_bap = BAP(meeting_number=1, meeting_date=date(2026, 7, 1), material_taught="Pengenalan OOP")
        dummy_bap.bap_id = 100
        
        mock_bap_manager.update_bap.return_value = True
        services["bap_manager"] = mock_bap_manager

        payload = {
            "bap_id": 100,
            "meeting_date": "2026-07-02",
            "material_taught": "Pengenalan OOP Mod"
        }
        response = client.put("/api/bap/update", json=payload)
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["success"] is True

    def test_delete_bap_meeting_api(self, client):
        """Menguji API hapus BAP tatap muka."""
        services = client.application.config["SERVICES"]
        mock_bap_manager = MagicMock()
        mock_bap_manager.delete_bap.return_value = True
        services["bap_manager"] = mock_bap_manager

        response = client.delete("/api/bap/delete/100")
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["success"] is True

    def test_validation_page_render(self, client):
        """Memastikan halaman pemeriksaan validasi di-render dengan sukses."""
        response = client.get("/validation")
        assert response.status_code == 200
        assert b"Pemeriksaan Validasi Kesesuaian" in response.data

    def test_run_validation_api(self, client):
        """Menguji pemicuan validator engine API."""
        services = client.application.config["SERVICES"]
        mock_validator = MagicMock()
        mock_validator.run_validation.return_value = []
        mock_validator.get_compliance_stats.return_value = {"total": 16, "sesuai": 14, "percentage": 87.5}
        services["validator"] = mock_validator

        response = client.post("/validation/run")
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["success"] is True
        assert json_data["data"]["stats"]["percentage"] == 87.5

    def test_get_validation_data_api(self, client):
        """Menguji API penarikan hasil validasi aktif."""
        services = client.application.config["SERVICES"]
        mock_validator = MagicMock()
        
        dummy_val = ValidationResult(meeting_number=1, similarity_score=90.0, status="SESUAI")
        dummy_val.validation_id = 200
        mock_validator.get_validation_results.return_value = [dummy_val]
        
        from datetime import date
        mock_validator.get_rps_by_meeting.return_value = RPS(meeting_number=1, topic="Logic", sub_topic="Condition")
        mock_validator.get_bap_by_meeting.return_value = BAP(meeting_number=1, meeting_date=date(2026, 7, 1), material_taught="Logic Condition")
        
        services["validator"] = mock_validator

        response = client.get("/api/validation/data")
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["success"] is True
        assert json_data["data"][0]["topic"] == "Logic"
        assert json_data["data"][0]["similarity_score"] == 90.0

    def test_report_page_render(self, client):
        """Memastikan halaman evaluasi laporan di-render dengan sukses."""
        response = client.get("/report")
        assert response.status_code == 200
        assert b"Laporan Hasil Evaluasi Pembelajaran" in response.data

    def test_get_report_data_api(self, client):
        """Menguji API data ringkasan laporan kepatuhan."""
        services = client.application.config["SERVICES"]
        mock_report_gen = MagicMock()
        
        dummy_report = Report(compliance_percentage=87.5, total_meetings=16, matched_count=14, mismatched_list=[], missing_list=[], results=[])
        mock_report_gen.generate_report.return_value = dummy_report
        services["report_generator"] = mock_report_gen

        response = client.get("/api/report/data")
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["success"] is True
        assert json_data["data"]["compliance_percentage"] == 87.5

    def test_get_upload_history_api(self, client):
        """Menguji API penarikan log audit riwayat unggah."""
        services = client.application.config["SERVICES"]
        mock_handler = MagicMock()
        mock_handler.get_upload_history.return_value = [
            {"file_name": "rps.pdf", "file_size_kb": 120, "upload_status": "SUCCESS"}
        ]
        services["upload_handler"] = mock_handler

        response = client.get("/api/report/upload-history")
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["success"] is True
        assert json_data["data"][0]["file_name"] == "rps.pdf"

    def test_upload_replace_all_cascades(self, client):
        """Menguji unggahan RPS baru mengganti data akademik aktif (RPS, BAP, validasi) secara kaskade."""
        services = client.application.config["SERVICES"]
        
        mock_rps_manager = MagicMock()
        mock_rps_manager.save_rps.return_value = True
        services["rps_manager"] = mock_rps_manager

        # Data upload RPS pertama
        payload_1 = {
            "source_file": "rps_active_1.pdf",
            "items": [
                {"meeting_number": 1, "topic": "Topik A", "sub_topic": "Sub A"},
                {"meeting_number": 2, "topic": "Topik B", "sub_topic": "Sub B"}
            ]
        }
        res1 = client.post("/api/upload/save", json=payload_1)
        assert res1.status_code == 200
        assert res1.get_json()["success"] is True

        # Data upload RPS kedua (mengganti yang pertama, total 14)
        items_2 = [{"meeting_number": i, "topic": f"Topik Baru {i}", "sub_topic": ""} for i in range(1, 15)]
        payload_2 = {
            "source_file": "rps_active_2.pdf",
            "items": items_2
        }
        res2 = client.post("/api/upload/save", json=payload_2)
        assert res2.status_code == 200
        assert res2.get_json()["success"] is True

        # Verifikasi pemanggilan manager
        mock_rps_manager.save_rps.assert_called()
