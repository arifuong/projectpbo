"""
Modul DashboardRepository untuk Sistem Validasi RPS-BAP.

Modul ini menangani kueri SQL agregasi data statistik lintasan tabel
untuk kebutuhan data visualisasi halaman Dashboard (Single Active Mode).
"""

from typing import List, Dict, Any, Optional
from database.connection import DatabaseConnection
from utils.logger import setup_logger

# Inisialisasi logger untuk repository
logger = setup_logger(__name__)


class DashboardRepository:
    """
    Repository class untuk data Dashboard.

    Menangani interaksi kueri agregasi SQL untuk menyediakan data statistik ringkasan,
    diagram status, dan daftar pertemuan bermasalah.
    """

    def __init__(self, db: DatabaseConnection) -> None:
        """
        Inisialisasi DashboardRepository dengan database connection.

        Args:
            db: Koneksi database aktif.
        """
        self._db: DatabaseConnection = db

    def get_aggregate_stats(self) -> Dict[str, Any]:
        """
        Mengambil statistik ringkasan agregat dari database untuk single-course.

        Returns:
            Dict[str, Any]: Statistik jumlah RPS, BAP, upload, dan rata-rata kesesuaian.
        """
        query_rps = "SELECT COUNT(*) as total FROM rps;"
        query_bap = "SELECT COUNT(*) as total FROM bap;"
        query_upload = "SELECT COUNT(*) as total FROM upload_history;"
        
        # Hitung persentase kesesuaian aktif
        query_compliance = """
        SELECT (SUM(CASE WHEN status = 'SESUAI' THEN 1 ELSE 0 END) / COUNT(*)) * 100 as pct
        FROM validation_results;
        """

        try:
            rps_res = self._db.execute_query(query_rps)
            bap_res = self._db.execute_query(query_bap)
            upload_res = self._db.execute_query(query_upload)
            comp_res = self._db.execute_query(query_compliance)

            total_rps = rps_res[0]["total"] if rps_res else 0
            total_bap = bap_res[0]["total"] if bap_res else 0
            total_upload = upload_res[0]["total"] if upload_res else 0
            
            avg_compliance = 0.0
            if comp_res and comp_res[0]["pct"] is not None:
                avg_compliance = float(comp_res[0]["pct"])

            return {
                "total_rps": total_rps,
                "total_bap": total_bap,
                "total_upload": total_upload,
                "avg_compliance": round(avg_compliance, 2)
            }
        except Exception as e:
            logger.error(f"Gagal mengambil data statistik dashboard: {e}")
            return {
                "total_rps": 0,
                "total_bap": 0,
                "total_upload": 0,
                "avg_compliance": 0.0
            }

    def get_top_mismatched(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Mengambil daftar pertemuan dengan status ketidaksesuaian aktif.

        Args:
            limit: Jumlah record maksimal.

        Returns:
            List[Dict[str, Any]]: List dict berisi detail pertemuan bermasalah.
        """
        query = """
        -- Mengambil daftar pertemuan dengan status TIDAK_SESUAI atau TIDAK_DITEMUKAN
        SELECT vr.meeting_number, vr.similarity_score, vr.status, vr.notes, r.topic as rps_topic
        FROM validation_results vr
        LEFT JOIN rps r ON vr.meeting_number = r.meeting_number
        WHERE vr.status IN ('TIDAK_SESUAI', 'TIDAK_DITEMUKAN')
        ORDER BY vr.meeting_number ASC
        LIMIT %s;
        """
        try:
            return self._db.execute_query(query, (limit,))
        except Exception as e:
            logger.error(f"Gagal mengambil top mismatched meetings: {e}")
            return []

    def get_compliance_chart(self) -> List[Dict[str, Any]]:
        """
        Mengambil data persentase distribusi status validasi untuk diagram Chart.js.

        Returns:
            List[Dict[str, Any]]: Jumlah per status.
        """
        query = """
        SELECT status, COUNT(*) as count
        FROM validation_results
        GROUP BY status;
        """
        try:
            results = self._db.execute_query(query)
            return results
        except Exception as e:
            logger.error(f"Gagal mengambil compliance chart data: {e}")
            return []
