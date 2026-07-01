"""
Modul Repository BAP untuk Sistem Validasi RPS-BAP.

Modul ini mengimplementasikan class BAPRepository yang bertanggung jawab
untuk melakukan operasi CRUD data BAP (Berita Acara Perkuliahan) ke database MySQL.
"""

from typing import List, Optional, Dict, Any
from models.bap import BAP
from database.connection import DatabaseConnection
from utils.logger import setup_logger
from utils.exceptions import DatabaseQueryError

# Inisialisasi logger untuk repository bap
logger = setup_logger(__name__)


class BAPRepository:
    """
    Repository class untuk entitas BAP.

    Menangani interaksi langsung dengan tabel `bap` di database.
    Mendukung input manual data realisasi pembelajaran per pertemuan.
    """

    def __init__(self, db: DatabaseConnection) -> None:
        """
        Inisialisasi BAPRepository dengan dependency injection.

        Args:
            db: Instance koneksi database.
        """
        self._db: DatabaseConnection = db

    def create(self, bap: BAP) -> int:
        """
        Menyimpan data BAP baru.

        Args:
            bap: Objek BAP yang akan disimpan.

        Returns:
            int: ID record baru (bap_id).
        """
        query = """
        -- Menyimpan data BAP baru
        INSERT INTO bap (course_id, meeting_number, meeting_date, material_taught, cleaned_material)
        VALUES (%s, %s, %s, %s, %s);
        """
        params = (
            bap.course_id,
            bap.meeting_number,
            bap.meeting_date,
            bap.material_taught,
            bap.cleaned_material
        )
        logger.info(f"Menyimpan BAP pertemuan ke-{bap.meeting_number} untuk course_id={bap.course_id}")
        last_id = self._db.execute_non_query(query, params)
        bap.bap_id = last_id
        return last_id

    def get_by_id(self, bap_id: int) -> Optional[BAP]:
        """
        Mengambil data BAP berdasarkan ID.

        Args:
            bap_id: ID data BAP.

        Returns:
            Optional[BAP]: Objek BAP jika ditemukan, None jika tidak.
        """
        query = """
        -- Mengambil data BAP berdasarkan bap_id
        SELECT bap_id, course_id, meeting_number, meeting_date, material_taught, cleaned_material, created_at, updated_at
        FROM bap
        WHERE bap_id = %s;
        """
        logger.debug(f"Mengambil BAP dengan ID: {bap_id}")
        results = self._db.execute_query(query, (bap_id,))
        if not results:
            return None
        return BAP.from_dict(results[0])

    def get_by_course(self, course_id: int) -> List[BAP]:
        """
        Mengambil semua data BAP untuk satu mata kuliah, terurut berdasarkan nomor pertemuan.

        Args:
            course_id: ID mata kuliah.

        Returns:
            List[BAP]: Daftar objek BAP terurut.
        """
        query = """
        -- Mengambil seluruh data BAP berdasarkan course_id terurut meeting_number
        SELECT bap_id, course_id, meeting_number, meeting_date, material_taught, cleaned_material, created_at, updated_at
        FROM bap
        WHERE course_id = %s
        ORDER BY meeting_number ASC;
        """
        logger.debug(f"Mengambil data BAP untuk course: {course_id}")
        results = self._db.execute_query(query, (course_id,))
        return [BAP.from_dict(row) for row in results]

    def get_by_course_and_meeting(self, course_id: int, meeting_number: int) -> Optional[BAP]:
        """
        Mengambil data BAP berdasarkan mata kuliah dan nomor pertemuan.

        Args:
            course_id: ID mata kuliah.
            meeting_number: Nomor pertemuan.

        Returns:
            Optional[BAP]: Objek BAP jika ditemukan, None jika tidak.
        """
        query = """
        -- Mengambil data BAP berdasarkan course_id dan meeting_number
        SELECT bap_id, course_id, meeting_number, meeting_date, material_taught, cleaned_material, created_at, updated_at
        FROM bap
        WHERE course_id = %s AND meeting_number = %s;
        """
        logger.debug(f"Mengambil BAP untuk course: {course_id}, pertemuan: {meeting_number}")
        results = self._db.execute_query(query, (course_id, meeting_number))
        if not results:
            return None
        return BAP.from_dict(results[0])

    def update(self, bap: BAP) -> bool:
        """
        Memperbarui data BAP.

        Args:
            bap: Objek BAP berisi data baru.

        Returns:
            bool: True jika berhasil diperbarui.
        """
        if not bap.bap_id:
            logger.error("Gagal memperbarui bap: bap_id kosong.")
            return False
            
        query = """
        -- Memperbarui data BAP berdasarkan bap_id
        UPDATE bap
        SET meeting_number = %s, meeting_date = %s, material_taught = %s, cleaned_material = %s
        WHERE bap_id = %s;
        """
        params = (
            bap.meeting_number,
            bap.meeting_date,
            bap.material_taught,
            bap.cleaned_material,
            bap.bap_id
        )
        logger.info(f"Memperbarui BAP ID: {bap.bap_id}")
        affected_rows = self._db.execute_non_query(query, params)
        return affected_rows > 0

    def delete(self, bap_id: int) -> bool:
        """
        Menghapus data BAP berdasarkan ID.

        Args:
            bap_id: ID BAP.

        Returns:
            bool: True jika berhasil dihapus.
        """
        query = """
        -- Menghapus data BAP berdasarkan bap_id
        DELETE FROM bap
        WHERE bap_id = %s;
        """
        logger.info(f"Menghapus bap dengan ID: {bap_id}")
        affected_rows = self._db.execute_non_query(query, (bap_id,))
        return affected_rows > 0

    def count_by_course(self, course_id: int) -> int:
        """
        Mendapatkan total jumlah pertemuan BAP yang terdaftar pada mata kuliah tertentu.

        Args:
            course_id: ID mata kuliah.

        Returns:
            int: Jumlah pertemuan BAP.
        """
        query = """
        -- Menghitung total pertemuan BAP untuk course_id tertentu
        SELECT COUNT(*) as total
        FROM bap
        WHERE course_id = %s;
        """
        results = self._db.execute_query(query, (course_id,))
        if not results:
            return 0
        return results[0]["total"]

    def exists(self, course_id: int, meeting_number: int) -> bool:
        """
        Memeriksa apakah data BAP untuk pertemuan tertentu sudah ada di database.

        Args:
            course_id: ID mata kuliah.
            meeting_number: Nomor pertemuan.

        Returns:
            bool: True jika data ada.
        """
        query = """
        -- Memeriksa keberadaan bap berdasarkan course_id dan meeting_number
        SELECT 1
        FROM bap
        WHERE course_id = %s AND meeting_number = %s;
        """
        results = self._db.execute_query(query, (course_id, meeting_number))
        return len(results) > 0
