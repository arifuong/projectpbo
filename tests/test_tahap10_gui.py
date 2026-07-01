"""
Unit Test untuk Tahap 10 - GUI Page Instantiation & Controllers.

Modul ini menguji keberhasilan instansiasi halaman GUI Tkinter
dan controller utama. Menggunakan mock penuh untuk Tkinter agar pengujian
dapat berjalan di lingkungan tanpa Tcl/Tk (headless/CI environment).

Menjalankan test:
    pytest tests/test_tahap10_gui.py -v
"""

import os
import sys
import tkinter as tk
import pytest
from unittest.mock import MagicMock, patch

# Memastikan direktori project ada di sys.path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from config.settings import AppSettings
from config.config import DatabaseConfig

from gui.app import AppController
from gui.dashboard_page import DashboardPage
from gui.upload_page import UploadPage
from gui.rps_page import RPSPage
from gui.bap_page import BAPPage
from gui.validation_page import ValidationPage
from gui.report_page import ReportPage

from services.course_service import CourseService
from services.rps_manager import RPSManager
from services.bap_manager import BAPManager
from services.keyword_matcher import KeywordMatcher
from services.validator import Validator
from services.report_generator import ReportGenerator
from services.dashboard_service import DashboardService
from services.file_upload_handler import FileUploadHandler
from services.pdf_extraction_service import PDFExtractionService


class TestGUIComponents:
    """Test suite untuk memverifikasi instansiasi komponen GUI."""

    @pytest.fixture
    def mock_parent(self):
        """Fixture untuk menyediakan objek parent mock murni."""
        parent = MagicMock()
        parent.winfo_width.return_value = 400
        parent.winfo_height.return_value = 300
        return parent

    @patch("tkinter.Canvas", return_value=MagicMock())
    @patch("tkinter.Label", return_value=MagicMock())
    @patch("tkinter.Frame", return_value=MagicMock())
    @patch("tkinter.LabelFrame", return_value=MagicMock())
    @patch("tkinter.Button", return_value=MagicMock())
    @patch("tkinter.Entry", return_value=MagicMock())
    @patch("tkinter.ttk.Treeview", return_value=MagicMock())
    @patch("tkinter.ttk.Scrollbar", return_value=MagicMock())
    @patch("tkinter.ttk.Combobox", return_value=MagicMock())
    @patch("tkinter.ttk.Progressbar", return_value=MagicMock())
    def test_dashboard_page_creation(self, mock_parent, *mocks):
        """Memastikan DashboardPage dapat dibuat dan memuat data."""
        mock_dash_service = MagicMock(spec=DashboardService)
        mock_course_service = MagicMock(spec=CourseService)
        
        mock_dash_service.get_summary_statistics.return_value = {
            "total_courses": 5, "total_rps": 4, "total_bap": 3, "avg_compliance": 85.5
        }
        mock_dash_service.get_top_mismatched_courses.return_value = []
        mock_dash_service.get_compliance_chart_data.return_value = []

        page = DashboardPage(mock_parent, mock_dash_service, mock_course_service)
        assert page is not None
        page.refresh_data()
        mock_dash_service.get_summary_statistics.assert_called_once()

    @patch("tkinter.DoubleVar", return_value=MagicMock())
    @patch("tkinter.Canvas", return_value=MagicMock())
    @patch("tkinter.Label", return_value=MagicMock())
    @patch("tkinter.Frame", return_value=MagicMock())
    @patch("tkinter.LabelFrame", return_value=MagicMock())
    @patch("tkinter.Button", return_value=MagicMock())
    @patch("tkinter.Entry", return_value=MagicMock())
    @patch("tkinter.ttk.Treeview", return_value=MagicMock())
    @patch("tkinter.ttk.Scrollbar", return_value=MagicMock())
    @patch("tkinter.ttk.Combobox", return_value=MagicMock())
    @patch("tkinter.ttk.Progressbar", return_value=MagicMock())
    def test_upload_page_creation(self, mock_parent, *mocks):
        """Memastikan UploadPage dapat dibuat."""
        mock_upload_handler = MagicMock(spec=FileUploadHandler)
        mock_extraction = MagicMock(spec=PDFExtractionService)
        mock_rps_manager = MagicMock(spec=RPSManager)
        mock_course_service = MagicMock(spec=CourseService)

        mock_course_service.get_all_courses.return_value = []

        page = UploadPage(mock_parent, mock_upload_handler, mock_extraction, mock_rps_manager, mock_course_service)
        assert page is not None
        page.load_courses()
        mock_course_service.get_all_courses.assert_called_once()

    @patch("tkinter.Canvas", return_value=MagicMock())
    @patch("tkinter.Label", return_value=MagicMock())
    @patch("tkinter.Frame", return_value=MagicMock())
    @patch("tkinter.LabelFrame", return_value=MagicMock())
    @patch("tkinter.Button", return_value=MagicMock())
    @patch("tkinter.Entry", return_value=MagicMock())
    @patch("tkinter.ttk.Treeview", return_value=MagicMock())
    @patch("tkinter.ttk.Scrollbar", return_value=MagicMock())
    @patch("tkinter.ttk.Combobox", return_value=MagicMock())
    @patch("tkinter.ttk.Progressbar", return_value=MagicMock())
    def test_rps_page_creation(self, mock_parent, *mocks):
        """Memastikan RPSPage dapat dibuat."""
        mock_rps_manager = MagicMock(spec=RPSManager)
        mock_course_service = MagicMock(spec=CourseService)

        mock_course_service.get_all_courses.return_value = []

        page = RPSPage(mock_parent, mock_rps_manager, mock_course_service)
        assert page is not None
        page.load_courses()
        mock_course_service.get_all_courses.assert_called_once()

    @patch("tkinter.Canvas", return_value=MagicMock())
    @patch("tkinter.Label", return_value=MagicMock())
    @patch("tkinter.Frame", return_value=MagicMock())
    @patch("tkinter.LabelFrame", return_value=MagicMock())
    @patch("tkinter.Button", return_value=MagicMock())
    @patch("tkinter.Entry", return_value=MagicMock())
    @patch("tkinter.ttk.Treeview", return_value=MagicMock())
    @patch("tkinter.ttk.Scrollbar", return_value=MagicMock())
    @patch("tkinter.ttk.Combobox", return_value=MagicMock())
    @patch("tkinter.ttk.Progressbar", return_value=MagicMock())
    def test_bap_page_creation(self, mock_parent, *mocks):
        """Memastikan BAPPage dapat dibuat."""
        mock_bap_manager = MagicMock(spec=BAPManager)
        mock_course_service = MagicMock(spec=CourseService)

        mock_course_service.get_all_courses.return_value = []

        page = BAPPage(mock_parent, mock_bap_manager, mock_course_service)
        assert page is not None
        page.load_courses()
        mock_course_service.get_all_courses.assert_called_once()

    @patch("tkinter.DoubleVar", return_value=MagicMock())
    @patch("tkinter.Canvas", return_value=MagicMock())
    @patch("tkinter.Label", return_value=MagicMock())
    @patch("tkinter.Frame", return_value=MagicMock())
    @patch("tkinter.LabelFrame", return_value=MagicMock())
    @patch("tkinter.Button", return_value=MagicMock())
    @patch("tkinter.Entry", return_value=MagicMock())
    @patch("tkinter.ttk.Treeview", return_value=MagicMock())
    @patch("tkinter.ttk.Scrollbar", return_value=MagicMock())
    @patch("tkinter.ttk.Combobox", return_value=MagicMock())
    @patch("tkinter.ttk.Progressbar", return_value=MagicMock())
    def test_validation_page_creation(self, mock_parent, *mocks):
        """Memastikan ValidationPage dapat dibuat."""
        mock_validator = MagicMock(spec=Validator)
        mock_course_service = MagicMock(spec=CourseService)

        mock_course_service.get_all_courses.return_value = []

        page = ValidationPage(mock_parent, mock_validator, mock_course_service)
        assert page is not None
        page.load_courses()
        mock_course_service.get_all_courses.assert_called_once()

    @patch("tkinter.Canvas", return_value=MagicMock())
    @patch("tkinter.Label", return_value=MagicMock())
    @patch("tkinter.Frame", return_value=MagicMock())
    @patch("tkinter.LabelFrame", return_value=MagicMock())
    @patch("tkinter.Button", return_value=MagicMock())
    @patch("tkinter.Entry", return_value=MagicMock())
    @patch("tkinter.ttk.Treeview", return_value=MagicMock())
    @patch("tkinter.ttk.Scrollbar", return_value=MagicMock())
    @patch("tkinter.ttk.Combobox", return_value=MagicMock())
    @patch("tkinter.ttk.Progressbar", return_value=MagicMock())
    def test_report_page_creation(self, mock_parent, *mocks):
        """Memastikan ReportPage dapat dibuat."""
        mock_report_gen = MagicMock(spec=ReportGenerator)
        mock_course_service = MagicMock(spec=CourseService)

        mock_course_service.get_all_courses.return_value = []

        page = ReportPage(mock_parent, mock_report_gen, mock_course_service)
        assert page is not None
        page.load_courses()
        mock_course_service.get_all_courses.assert_called_once()


class TestAppController:
    """Test suite untuk AppController utama."""

    def test_app_controller_mocked(self):
        """Menguji struktur komponen AppController menggunakan mockup penuh untuk memintas TclError."""
        # Buat tiruan kelas tk.Tk secara terisolasi
        mock_tk = MagicMock()
        mock_tk.tk = MagicMock()
        
        with patch("tkinter.Tk", return_value=mock_tk), \
             patch("gui.app.DatabaseConnection") as mock_db_conn_class:
             
            mock_db_conn = MagicMock()
            mock_db_conn_class.return_value = mock_db_conn
            
            # Setup configuration
            config = DatabaseConfig()
            settings = AppSettings(db_config=config)
            
            with patch.object(AppController, "_init_layout", return_value=None):
                app = AppController(settings)
                
                assert app is not None
                assert app._db_conn is mock_db_conn
                mock_db_conn.ensure_connection.assert_called_once()
