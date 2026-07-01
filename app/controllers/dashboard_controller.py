"""
Modul DashboardController untuk Mengelola Presentasi Dashboard Web.

Modul ini mendefinisikan class DashboardController yang menangani request data dashboard
serta format output JSON untuk Chart.js.

Sesuai PRD Single User & Single Course.
"""

from flask import render_template, Response
from app.controllers.base_controller import BaseController
from services.dashboard_service import DashboardService


class DashboardController(BaseController):
    """
    Controller untuk halaman Dashboard.
    """

    def index(self) -> str:
        """
        Menampilkan halaman Dashboard utama.

        Returns:
            str: HTML template hasil render.
        """
        dashboard_service: DashboardService = self.get_service("dashboard_service")
        stats = dashboard_service.get_summary_statistics()
        top_mismatched = dashboard_service.get_top_mismatched_meetings(5)

        return render_template(
            "dashboard.html",
            stats=stats,
            top_mismatched=top_mismatched,
            active_page="dashboard"
        )

    def get_stats(self) -> Response:
        """
        Mengambil statistik ringkasan dalam format JSON.

        Returns:
            Response: JSON API response.
        """
        dashboard_service: DashboardService = self.get_service("dashboard_service")
        stats = dashboard_service.get_summary_statistics()
        return self.json_response(stats)

    def get_chart_data(self) -> Response:
        """
        Mengambil data grafik status validasi untuk Chart.js.

        Returns:
            Response: JSON API response.
        """
        dashboard_service: DashboardService = self.get_service("dashboard_service")
        chart_data = dashboard_service.get_compliance_chart_data()
        return self.json_response(chart_data)
