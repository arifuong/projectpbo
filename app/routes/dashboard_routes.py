"""
Modul Routing Dashboard untuk Aplikasi Web.

Modul ini mendefinisikan rute HTTP untuk halaman Dashboard Utama.
"""

from flask import Blueprint, render_template
from app.controllers.dashboard_controller import DashboardController

dashboard_bp = Blueprint("dashboard", __name__)
controller = DashboardController()


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
def index():
    """Halaman Dashboard Utama."""
    return controller.index()


@dashboard_bp.route("/api/dashboard/stats")
def get_stats():
    """API endpoint untuk mengambil data statistik agregat."""
    return controller.get_stats()


@dashboard_bp.route("/api/dashboard/chart")
def get_chart_data():
    """API endpoint untuk data diagram Chart.js."""
    return controller.get_chart_data()
