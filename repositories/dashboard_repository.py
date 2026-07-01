"""
Modul DashboardRepository untuk Sistem Validasi RPS-BAP.

Modul ini menangani kueri SQL agregasi data statistik lintasan tabel
untuk kebutuhan data visualisasi halaman Dashboard.
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
    diagram kesesuaian, dan mata kuliah dengan tingkat ketidaksesuaian tertinggi.
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
        Mengambil statistik ringkasan agregat dari database.

        Returns:
            Dict[str, Any]: Statistik jumlah course, rps, bap, dan rata-rata kesesuaian.
        """
        query_courses = "SELECT COUNT(*) as total FROM courses;"
        query_rps = "SELECT COUNT(DISTINCT course_id) as total FROM rps;"
        query_bap = "SELECT COUNT(DISTINCT course_id) as total FROM bap;"
        
        # Hitung rata-rata persentase kesesuaian untuk semua course yang memiliki hasil validasi
        # Persentase per course = (jumlah berstatus SESUAI / total pertemuan) * 100
        query_compliance = """
        -- Menghitung rata-rata kesesuaian global di sistem
        SELECT AVG(course_avg.pct) as avg_pct
        FROM (
            SELECT course_id, 
                   (SUM(CASE WHEN status = 'SESUAI' THEN 1 ELSE 0 END) / COUNT(*)) * 100 as pct
            FROM validation_results
            GROUP BY course_id
        ) as course_avg;
        """

        try:
            courses_res = self._db.execute_query(query_courses)
            rps_res = self._db.execute_query(query_rps)
            bap_res = self._db.execute_query(query_bap)
            comp_res = self._db.execute_query(query_compliance)

            total_courses = courses_res[0]["total"] if courses_res else 0
            total_rps = rps_res[0]["total"] if rps_res else 0
            total_bap = bap_res[0]["total"] if bap_res else 0
            
            avg_compliance = 0.0
            if comp_res and comp_res[0]["avg_pct"] is not None:
                avg_compliance = float(comp_res[0]["avg_pct"])

            return {
                "total_courses": total_courses,
                "total_rps": total_rps,
                "total_bap": total_bap,
                "avg_compliance": round(avg_compliance, 2)
            }
        except Exception as e:
            logger.error(f"Gagal mengambil data statistik dashboard: {e}")
            return {
                "total_courses": 0,
                "total_rps": 0,
                "total_bap": 0,
                "avg_compliance": 0.0
            }

    def get_top_mismatched(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Mengambil daftar mata kuliah dengan tingkat ketidaksesuaian tertinggi.

        Tingkat ketidaksesuaian = jumlah pertemuan berstatus TIDAK_SESUAI atau TIDAK_DITEMUKAN.

        Args:
            limit: Jumlah record maksimal.

        Returns:
            List[Dict[str, Any]]: List dict berisi detail course dan jumlah mismatches.
        """
        query = """
        -- Mengambil daftar mata kuliah dengan tingkat ketidaksesuaian tertinggi
        SELECT c.course_id, c.course_code, c.course_name, c.semester, c.academic_year,
               SUM(CASE WHEN vr.status IN ('TIDAK_SESUAI', 'TIDAK_DITEMUKAN') THEN 1 ELSE 0 END) as mismatch_count
        FROM validation_results vr
        JOIN courses c ON vr.course_id = c.course_id
        GROUP BY c.course_id
        HAVING mismatch_count > 0
        ORDER BY mismatch_count DESC, c.course_code ASC
        LIMIT %s;
        """
        try:
            return self._db.execute_query(query, (limit,))
        except Exception as e:
            logger.error(f"Gagal mengambil top mismatched courses: {e}")
            return []

    def get_compliance_chart(self, semester: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Mengambil data persentase kesesuaian per mata kuliah untuk diagram.

        Args:
            semester: Filter berdasarkan semester (opsional).

        Returns:
            List[Dict[str, Any]]: List mata kuliah dan persentase kesesuaiannya.
        """
        params = []
        filter_clause = ""
        if semester:
            filter_clause = "WHERE c.semester = %s"
            params.append(semester)

        query = f"""
        -- Mengambil data kesesuaian per mata kuliah untuk diagram dashboard
        SELECT c.course_code, c.course_name,
               (SUM(CASE WHEN vr.status = 'SESUAI' THEN 1 ELSE 0 END) / COUNT(*)) * 100 as compliance_percentage
        FROM validation_results vr
        JOIN courses c ON vr.course_id = c.course_id
        {filter_clause}
        GROUP BY c.course_id
        ORDER BY c.course_code ASC;
        """
        try:
            results = self._db.execute_query(query, tuple(params))
            # Konversi nilai decimal ke float untuk serialization
            for r in results:
                if r["compliance_percentage"] is not None:
                    r["compliance_percentage"] = round(float(r["compliance_percentage"]), 2)
                else:
                    r["compliance_percentage"] = 0.0
            return results
        except Exception as e:
            logger.error(f"Gagal mengambil compliance chart data: {e}")
            return []
