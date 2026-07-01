"""
Modul Routing Laporan untuk Aplikasi Web.

Modul ini mendefinisikan rute HTTP untuk halaman laporan evaluasi,
unduhan PDF, unduhan Excel, dan API log riwayat unggahan.
"""

from flask import Blueprint
from app.controllers.report_controller import ReportController

report_bp = Blueprint("report", __name__)
controller = ReportController()


@report_bp.route("/report", methods=["GET"])
def index():
    """Halaman Laporan Evaluasi Pembelajaran."""
    return controller.index()


@report_bp.route("/api/report/data", methods=["GET"])
def get_report_data():
    """API endpoint untuk mengambil ringkasan data laporan."""
    return controller.get_report_data()


@report_bp.route("/report/export/pdf", methods=["GET"])
def export_pdf():
    """Endpoint untuk unduh Laporan PDF."""
    return controller.export_pdf()


@report_bp.route("/report/export/excel", methods=["GET"])
def export_excel():
    """Endpoint untuk unduh Laporan Excel."""
    return controller.export_excel()


@report_bp.route("/api/report/upload-history", methods=["GET"])
def get_upload_history():
    """API endpoint untuk mengambil riwayat log audit unggah RPS."""
    return controller.get_upload_history()
