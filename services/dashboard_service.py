"""
Modul DashboardService untuk Sistem Validasi RPS-BAP.

Modul ini mengimplementasikan Service Layer untuk halaman Dashboard (Single Active Mode).
"""

from typing import List, Dict, Any, Optional
from repositories.dashboard_repository import DashboardRepository
from utils.logger import setup_logger

# Inisialisasi logger untuk DashboardService
logger = setup_logger(__name__)


class DashboardService:
    """
    Service class untuk mengelola data visualisasi Dashboard.
    """

    def __init__(self, dashboard_repo: DashboardRepository) -> None:
        """
        Inisialisasi DashboardService dengan dependency injection.

        Args:
            dashboard_repo: Repository data dashboard.
        """
        self._dashboard_repo: DashboardRepository = dashboard_repo
        logger.info("DashboardService berhasil diinisialisasi.")

    def get_summary_statistics(self) -> Dict[str, Any]:
        """
        Mengambil statistik ringkasan agregat aktif.

        Returns:
            Dict[str, Any]: Statistik jumlah record dan rata-rata persentase kesesuaian.
        """
        logger.info("Mengambil statistik ringkasan dashboard.")
        return self._dashboard_repo.get_aggregate_stats()

    def get_top_mismatched_meetings(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Mengambil daftar pertemuan dengan tingkat ketidaksesuaian aktif.
        """
        logger.info(f"Mengambil top {limit} mismatched meetings.")
        return self._dashboard_repo.get_top_mismatched(limit)

    def get_compliance_chart_data(self) -> List[Dict[str, Any]]:
        """
        Mengambil data persentase kesesuaian/status validasi diagram.
        """
        logger.info("Mengambil compliance chart data.")
        return self._dashboard_repo.get_compliance_chart()
