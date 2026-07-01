"""
Modul DashboardService untuk Sistem Validasi RPS-BAP.

Modul ini mengimplementasikan Service Layer untuk halaman Dashboard.
Bertanggung jawab untuk menyediakan ringkasan statistik agregat sistem
untuk visualisasi GUI.

Sesuai PRD Section 4.1 - Modul Dashboard.
"""

from typing import List, Dict, Any, Optional
from repositories.dashboard_repository import DashboardRepository
from utils.logger import setup_logger

# Inisialisasi logger untuk DashboardService
logger = setup_logger(__name__)


class DashboardService:
    """
    Service class untuk mengelola data visualisasi Dashboard.

    Menerapkan design pattern Service Layer dan Composition (has-a DashboardRepository).

    Attributes:
        _dashboard_repo (DashboardRepository): Repository untuk kueri dashboard.
    """

    def __init__(self, dashboard_repo: DashboardRepository) -> None:
        """
        Inisialisasi DashboardService dengan dependency injection.

        Args:
            dashboard_repo: Repository data dashboard.
        """
        self._dashboard_repo: DashboardRepository = dashboard_repo
        logger.info("DashboardService berhasil diinisialisasi.")

    def get_summary_statistics(self, filter_params: Optional[dict] = None) -> Dict[str, Any]:
        """
        Mengambil statistik ringkasan agregat sistem.

        Args:
            filter_params: Parameter filter semester/tahun akademik (opsional).

        Returns:
            Dict[str, Any]: Statistik jumlah record dan rata-rata persentase kesesuaian.
        """
        logger.info("Mengambil statistik ringkasan dashboard.")
        # Filter params dapat diperluas jika database mendukung filter dinamis
        return self._dashboard_repo.get_aggregate_stats()

    def get_top_mismatched_courses(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Mengambil daftar mata kuliah dengan tingkat ketidaksesuaian tertinggi.

        Sesuai PRD Section 4.1 & 10.1.

        Args:
            limit: Jumlah record maksimal.

        Returns:
            List[Dict[str, Any]]: List data mata kuliah tidak sesuai.
        """
        logger.info(f"Mengambil top {limit} mismatched courses.")
        return self._dashboard_repo.get_top_mismatched(limit)

    def get_compliance_chart_data(self, semester: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Mengambil data persentase kesesuaian per mata kuliah untuk diagram.

        Args:
            semester: Filter semester (misal: "Ganjil", "Genap").

        Returns:
            List[Dict[str, Any]]: List data koordinat diagram.
        """
        logger.info(f"Mengambil compliance chart data untuk semester: {semester}")
        return self._dashboard_repo.get_compliance_chart(semester)
