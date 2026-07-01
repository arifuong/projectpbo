"""
Modul Routing Upload untuk Aplikasi Web.

Modul ini mendefinisikan rute HTTP untuk halaman unggah, API unggah PDF,
dan aksi penyimpanan hasil ekstraksi RPS.
"""

from flask import Blueprint
from app.controllers.upload_controller import UploadController

upload_bp = Blueprint("upload", __name__)
controller = UploadController()


@upload_bp.route("/upload", methods=["GET"])
def index():
    """Halaman Unggah PDF RPS."""
    return controller.index()


@upload_bp.route("/upload", methods=["POST"])
def upload_file():
    """API endpoint untuk unggah file PDF dan ekstraksi data."""
    return controller.upload_file()


@upload_bp.route("/api/upload/save", methods=["POST"])
def save_extracted_rps():
    """API endpoint untuk menyimpan data ekstraksi RPS yang disetujui."""
    return controller.save_extracted_rps()
