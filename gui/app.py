"""
Modul Aplikasi Utama GUI (App Controller) untuk Sistem Validasi RPS-BAP.

Modul ini menginisialisasi seluruh dependency injection dari DatabaseConnection,
Repositories, Services, dan membangun layout navigasi sidebar halaman Tkinter.

Sesuai PRD Section 10.7 - Navigasi Menu Sidebar & Arsitektur MVC.
"""

import tkinter as tk
from tkinter import messagebox
from typing import Dict

from config.settings import AppSettings
from database.connection import DatabaseConnection

# Import Repositories
from repositories.course_repository import CourseRepository
from repositories.rps_repository import RPSRepository
from repositories.bap_repository import BAPRepository
from repositories.validation_repository import ValidationRepository
from repositories.upload_repository import UploadRepository
from repositories.dashboard_repository import DashboardRepository

# Import Services
from services.course_service import CourseService
from services.rps_manager import RPSManager
from services.bap_manager import BAPManager
from services.keyword_matcher import KeywordMatcher
from services.validator import Validator
from services.report_generator import ReportGenerator
from services.dashboard_service import DashboardService
from services.file_upload_handler import FileUploadHandler

# Import GUI Pages
from gui.dashboard_page import DashboardPage
from gui.upload_page import UploadPage
from gui.rps_page import RPSPage
from gui.bap_page import BAPPage
from gui.validation_page import ValidationPage
from gui.report_page import ReportPage

# Import Constants
from config.constants import (
    APP_TITLE,
    COLOR_PRIMARY,
    COLOR_BACKGROUND,
    COLOR_WHITE,
    COLOR_TEXT_DARK,
    COLOR_BORDER,
    FONT_FAMILY,
    FONT_SIZE_TITLE,
    FONT_SIZE_NORMAL,
    FONT_SIZE_LARGE
)


class AppController(tk.Tk):
    """
    Controller utama aplikasi desktop berbasis Tkinter.

    Mewarisi tk.Tk. Bertanggung jawab atas inisialisasi koneksi MySQL,
    repository, business service, and menyusun layout frame dengan model raise frame.
    """

    def __init__(self, settings: AppSettings) -> None:
        """
        Inisialisasi Controller Utama GUI.

        Args:
            settings: Instance konfigurasi AppSettings.
        """
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1100x680")
        self.minsize(1000, 600)
        self.configure(bg=COLOR_BACKGROUND)

        self._settings: AppSettings = settings
        
        # 1. Inisialisasi Database Connection & Verify
        self._db_conn = DatabaseConnection(self._settings.db_config)
        try:
            # Periksa status server database
            self._db_conn.ensure_connection()
        except Exception as e:
            messagebox.showerror(
                "Koneksi Database Gagal",
                f"Aplikasi gagal terhubung ke server database MySQL.\n"
                f"Pastikan MySQL aktif dan database '{self._settings.db_config.database}' tersedia.\n\n"
                f"Error: {e}"
            )
            # Jangan matikan aplikasi agar user bisa setup schema
            # kita coba inisialisasi tapi catat statusnya
            
        # 2. Inisialisasi Repositories (DI)
        self.course_repo = CourseRepository(self._db_conn)
        self.rps_repo = RPSRepository(self._db_conn)
        self.bap_repo = BAPRepository(self._db_conn)
        self.val_repo = ValidationRepository(self._db_conn)
        self.upload_repo = UploadRepository(self._db_conn)
        self.dashboard_repo = DashboardRepository(self._db_conn)

        # 3. Inisialisasi Services (DI)
        self.course_service = CourseService(self.course_repo)
        
        # Inisialisasi TextCleaner bawaan
        from utils.text_cleaner import TextCleaner
        self.text_cleaner = TextCleaner()

        self.rps_manager = RPSManager(self.rps_repo, self.course_repo, self.text_cleaner)
        self.bap_manager = BAPManager(self.bap_repo, self.rps_repo, self.course_repo, self.text_cleaner)
        
        self.keyword_matcher = KeywordMatcher(self._settings.similarity_threshold)
        self.validator = Validator(self.keyword_matcher, self.rps_repo, self.bap_repo, self.val_repo)
        self.report_generator = ReportGenerator(self.rps_repo, self.bap_repo, self.val_repo, self.course_repo)
        
        self.dashboard_service = DashboardService(self.dashboard_repo)
        self.upload_handler = FileUploadHandler(self.upload_repo, self._settings.upload_dir, self._settings.max_upload_size_mb)
        
        from services.pdf_extraction_service import PDFExtractionService
        self.extraction_service = PDFExtractionService()

        # 4. Inisialisasi Menu UI
        self._init_layout()

    def _init_layout(self) -> None:
        """
        Membangun layout utama 2 bagian: Sidebar kiri untuk menu navigasi,
        dan area konten kanan untuk menampung Frame halaman aktif.
        """
        # Sidebar Panel Kiri
        self.sidebar = tk.Frame(self, bg=COLOR_PRIMARY, width=220)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        # Judul App di Sidebar
        lbl_brand = tk.Label(
            self.sidebar,
            text="VALIDATOR\nRPS & BAP",
            font=(FONT_FAMILY, FONT_SIZE_LARGE, "bold"),
            fg=COLOR_WHITE,
            bg=COLOR_PRIMARY,
            pady=20
        )
        lbl_brand.pack(fill=tk.X)

        # Pembatas Garis
        separator = tk.Frame(self.sidebar, bg=COLOR_WHITE, height=1)
        separator.pack(fill=tk.X, padx=15, pady=(0, 20))

        # Panel Halaman Utama Kanan
        self.content_area = tk.Frame(self, bg=COLOR_BACKGROUND)
        self.content_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Dictionary Penampung Halaman
        self.pages: Dict[str, tk.Frame] = {}

        # Registrasi Halaman ke dalam Container
        self.pages["dashboard"] = DashboardPage(self.content_area, self.dashboard_service, self.course_service)
        self.pages["upload"] = UploadPage(self.content_area, self.upload_handler, self.extraction_service, self.rps_manager, self.course_service)
        self.pages["rps"] = RPSPage(self.content_area, self.rps_manager, self.course_service)
        self.pages["bap"] = BAPPage(self.content_area, self.bap_manager, self.course_service)
        self.pages["validation"] = ValidationPage(self.content_area, self.validator, self.course_service)
        self.pages["report"] = ReportPage(self.content_area, self.report_generator, self.course_service)

        # Letakkan semua Frame halaman pada posisi yang sama agar bisa ditumpuk raise
        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")

        # Pastikan grid container responsif meluas mengikuti window
        self.content_area.rowconfigure(0, weight=1)
        self.content_area.columnconfigure(0, weight=1)

        # Tambah Tombol Navigasi Menu ke Sidebar
        self.nav_buttons: Dict[str, tk.Button] = {}
        
        self._create_nav_button("dashboard", "Dashboard Overview")
        self._create_nav_button("upload", "Unggah PDF RPS")
        self._create_nav_button("rps", "Data Pokok RPS")
        self._create_nav_button("bap", "Realisasi BAP")
        self._create_nav_button("validation", "Pemeriksaan Validasi")
        self._create_nav_button("report", "Ekspor Laporan")

        # Tombol Keluar di Sidebar Bawah
        btn_exit = tk.Button(
            self.sidebar,
            text="Keluar Aplikasi",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            bg="#dc3545",  # Merah
            fg=COLOR_WHITE,
            bd=0,
            cursor="hand2",
            pady=10,
            command=self.quit
        )
        btn_exit.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=20)

        # Tampilkan halaman default (Dashboard)
        self.show_page("dashboard")

    def _create_nav_button(self, page_name: str, text: str) -> None:
        """
        Helper untuk membuat tombol navigasi sidebar dengan hover-effect.

        Args:
            page_name: Kode string nama halaman.
            text: Label teks pada tombol.
        """
        btn = tk.Button(
            self.sidebar,
            text=text,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            bg=COLOR_PRIMARY,
            fg=COLOR_WHITE,
            bd=0,
            anchor=tk.W,
            padx=20,
            pady=12,
            cursor="hand2",
            command=lambda: self.show_page(page_name)
        )
        btn.pack(fill=tk.X)
        self.nav_buttons[page_name] = btn

    def show_page(self, page_name: str) -> None:
        """
        Mengangkat frame halaman aktif ke tumpukan teratas (raise frame)
        dan memperbarui data visualisasi pada halaman tersebut secara dinamis.

        Args:
            page_name: Kode string nama halaman yang ingin ditampilkan.
        """
        if page_name in self.pages:
            # 1. Update status visual tombol navigasi sidebar aktif
            for name, btn in self.nav_buttons.items():
                if name == page_name:
                    btn.config(bg=COLOR_WHITE, fg=COLOR_PRIMARY)
                else:
                    btn.config(bg=COLOR_PRIMARY, fg=COLOR_WHITE)

            # 2. Segarkan data terbaru pada halaman tujuan
            page = self.pages[page_name]
            if hasattr(page, "refresh_data"):
                # Panggil method refresh_data milik halaman
                page.refresh_data() # type: ignore

            # 3. Tampilkan frame ke atas
            page.tkraise()
