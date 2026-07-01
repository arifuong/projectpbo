"""
Modul Routing Validasi untuk Aplikasi Web.

Modul ini mendefinisikan rute HTTP untuk halaman validasi, API pemicuan validator,
dan penarikan hasil validasi terkini.
"""

from flask import Blueprint
from app.controllers.validation_controller import ValidationController

validation_bp = Blueprint("validation", __name__)
controller = ValidationController()


@validation_bp.route("/validation", methods=["GET"])
def index():
    """Halaman Hasil Pemeriksaan Validasi."""
    return controller.index()


@validation_bp.route("/validation/run", methods=["POST"])
def run_validation():
    """API endpoint untuk memicu proses validasi."""
    return controller.run_validation()


@validation_bp.route("/api/validation/data", methods=["GET"])
def get_validation_data():
    """API endpoint untuk mengambil data hasil pemeriksaan validasi."""
    return controller.get_validation_data()
