"""
Flask Application Factory untuk Sistem Validasi RPS-BAP Web.

Modul ini menginisialisasi aplikasi Flask, memuat konfigurasi,
mengelola koneksi database, dan mendaftarkan seluruh blueprint routing.

Sesuai PRD mode satu pengguna dan satu data akademik aktif.
"""

import os
from flask import Flask, render_template

from config.settings import AppSettings
from config.config import DatabaseConfig
from database.connection import DatabaseConnection

# Import Repositories
from repositories.rps_repository import RPSRepository
from repositories.bap_repository import BAPRepository
from repositories.validation_repository import ValidationRepository
from repositories.upload_repository import UploadRepository
from repositories.dashboard_repository import DashboardRepository

# Import Services
from services.rps_manager import RPSManager
from services.bap_manager import BAPManager
from services.keyword_matcher import KeywordMatcher
from services.validator import Validator
from services.report_generator import ReportGenerator
from services.dashboard_service import DashboardService
from services.file_upload_handler import FileUploadHandler
from services.pdf_extraction_service import PDFExtractionService

from utils.text_cleaner import TextCleaner
from utils.logger import setup_logger

# Inisialisasi logger utama
logger = setup_logger("app_factory")


def create_app(settings: AppSettings = None) -> Flask:
    """
    Application Factory untuk membuat dan mengonfigurasi instansi Flask.

    Args:
        settings: Objek AppSettings (opsional). Jika None, dibuat secara internal.

    Returns:
        Flask: Instansi aplikasi Flask yang siap dijalankan.
    """
    app = Flask(__name__, template_folder="templates", static_folder="static")
    
    # 1. Load Configurations
    if settings is None:
        db_config = DatabaseConfig()
        settings = AppSettings(db_config=db_config)
    
    app.config["APP_SETTINGS"] = settings
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "rps-bap-secret-key-12345")

    logger.info("Menginisialisasi koneksi database MySQL...")
    db_conn = DatabaseConnection(settings.db_config)
    db_conn.ensure_connection()

    # 2. Inisialisasi Repositories (DI)
    rps_repo = RPSRepository(db_conn)
    bap_repo = BAPRepository(db_conn)
    val_repo = ValidationRepository(db_conn)
    upload_repo = UploadRepository(db_conn)
    dashboard_repo = DashboardRepository(db_conn)

    # 3. Inisialisasi Services (DI)
    text_cleaner = TextCleaner()
    
    app.config["SERVICES"] = {
        "rps_manager": RPSManager(rps_repo, text_cleaner),
        "bap_manager": BAPManager(bap_repo, rps_repo, text_cleaner),
        "keyword_matcher": KeywordMatcher(settings.similarity_threshold),
        "validator": Validator(KeywordMatcher(settings.similarity_threshold), rps_repo, bap_repo, val_repo),
        "report_generator": ReportGenerator(rps_repo, bap_repo, val_repo),
        "dashboard_service": DashboardService(dashboard_repo),
        "upload_handler": FileUploadHandler(upload_repo, settings.upload_dir, settings.max_upload_size_mb),
        "extraction_service": PDFExtractionService()
    }

    # 4. Registrasi Blueprints / Routes
    from app.routes.dashboard_routes import dashboard_bp
    from app.routes.upload_routes import upload_bp
    from app.routes.rps_routes import rps_bp
    from app.routes.bap_routes import bap_bp
    from app.routes.validation_routes import validation_bp
    from app.routes.report_routes import report_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(rps_bp)
    app.register_blueprint(bap_bp)
    app.register_blueprint(validation_bp)
    app.register_blueprint(report_bp)

    # 5. Registrasi Global Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        logger.error(f"Internal Server Error: {e}")
        return render_template("500.html"), 500

    logger.info("Aplikasi Flask berhasil dibentuk melalui Factory Pattern.")
    return app
