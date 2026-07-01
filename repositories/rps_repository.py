"""
Modul Repository RPS untuk Sistem Validasi RPS-BAP.

Modul ini mengimplementasikan class RPSRepository yang bertanggung jawab
untuk melakukan operasi CRUD data RPS (Rencana Pembelajaran Semester) ke database MySQL.
"""

from typing import List, Optional, Dict, Any, Tuple
from models.rps import RPS
from database.connection import DatabaseConnection
from utils.logger import setup_logger
from utils.exceptions import DatabaseQueryError, DatabaseTransactionError

# Inisialisasi logger untuk repository rps
logger = setup_logger(__name__)


class RPSRepository:
    """
    Repository class untuk entitas RPS.

    Menangani interaksi langsung dengan tabel `rps` di database.
    Menyediakan method penyimpanan batch menggunakan transaksi SQL.
    """

    def __init__(self, db: DatabaseConnection) -> None:
        """
        Inisialisasi RPSRepository dengan dependency injection.

        Args:
            db: Instance koneksi database.
        """
        self._db: DatabaseConnection = db

    def create(self, rps: RPS) -> int:
        """
        Menyimpan data RPS baru.

        Args:
            rps: Objek RPS yang akan disimpan.

        Returns:
            int: ID record baru (rps_id).
        """
        query = """
        -- Menyimpan data RPS pertemuan baru
        INSERT INTO rps (course_id, meeting_number, topic, sub_topic, cleaned_topic, source_file)
        VALUES (%s, %s, %s, %s, %s, %s);
        """
        params = (
            rps.course_id,
            rps.meeting_number,
            rps.topic,
            rps.sub_topic,
            rps.cleaned_topic,
            rps.source_file
        )
        logger.info(f"Menyimpan RPS pertemuan ke-{rps.meeting_number} untuk course_id={rps.course_id}")
        last_id = self._db.execute_non_query(query, params)
        rps.rps_id = last_id
        return last_id

    def save_batch(self, rps_list: List[RPS]) -> bool:
        """
        Menyimpan daftar RPS secara massal (batch) di dalam satu transaksi database.

        Args:
            rps_list: List dari objek RPS.

        Returns:
            bool: True jika transaksi sukses dieksekusi.
        """
        if not rps_list:
            return True
            
        queries_with_params: List[Tuple[str, Optional[Tuple[Any, ...]]]] = []
        for rps in rps_list:
            query = """
            -- Menyimpan data RPS pertemuan baru (Batch)
            INSERT INTO rps (course_id, meeting_number, topic, sub_topic, cleaned_topic, source_file)
            VALUES (%s, %s, %s, %s, %s, %s);
            """
            params = (
                rps.course_id,
                rps.meeting_number,
                rps.topic,
                rps.sub_topic,
                rps.cleaned_topic,
                rps.source_file
            )
            queries_with_params.append((query, params))
            
        logger.info(f"Menjalankan batch transaksi untuk {len(rps_list)} rps record.")
        return self._db.execute_transaction(queries_with_params)

    def get_by_id(self, rps_id: int) -> Optional[RPS]:
        """
        Mengambil satu data RPS berdasarkan ID.

        Args:
            rps_id: ID data RPS.

        Returns:
            Optional[RPS]: Objek RPS jika ditemukan, None jika tidak.
        """
        query = """
        -- Mengambil data RPS berdasarkan rps_id
        SELECT rps_id, course_id, meeting_number, topic, sub_topic, cleaned_topic, source_file, created_at, updated_at
        FROM rps
        WHERE rps_id = %s;
        """
        logger.debug(f"Mengambil RPS dengan ID: {rps_id}")
        results = self._db.execute_query(query, (rps_id,))
        if not results:
            return None
        return RPS.from_dict(results[0])

    def get_by_course(self, course_id: int) -> List[RPS]:
        """
        Mengambil semua data RPS untuk satu mata kuliah, terurut berdasarkan nomor pertemuan.

        Args:
            course_id: ID mata kuliah.

        Returns:
            List[RPS]: Daftar objek RPS terurut.
        """
        query = """
        -- Mengambil seluruh data RPS berdasarkan course_id terurut meeting_number
        SELECT rps_id, course_id, meeting_number, topic, sub_topic, cleaned_topic, source_file, created_at, updated_at
        FROM rps
        WHERE course_id = %s
        ORDER BY meeting_number ASC;
        """
        logger.debug(f"Mengambil data RPS untuk course: {course_id}")
        results = self._db.execute_query(query, (course_id,))
        return [RPS.from_dict(row) for row in results]

    def get_by_course_and_meeting(self, course_id: int, meeting_number: int) -> Optional[RPS]:
        """
        Mengambil data RPS berdasarkan mata kuliah dan nomor pertemuan.

        Args:
            course_id: ID mata kuliah.
            meeting_number: Nomor pertemuan.

        Returns:
            Optional[RPS]: Objek RPS jika ditemukan, None jika tidak.
        """
        query = """
        -- Mengambil data RPS berdasarkan course_id dan meeting_number
        SELECT rps_id, course_id, meeting_number, topic, sub_topic, cleaned_topic, source_file, created_at, updated_at
        FROM rps
        WHERE course_id = %s AND meeting_number = %s;
        """
        logger.debug(f"Mengambil RPS untuk course: {course_id}, pertemuan: {meeting_number}")
        results = self._db.execute_query(query, (course_id, meeting_number))
        if not results:
            return None
        return RPS.from_dict(results[0])

    def update(self, rps: RPS) -> bool:
        """
        Memperbarui data RPS.

        Args:
            rps: Objek RPS berisi data baru.

        Returns:
            bool: True jika berhasil diperbarui.
        """
        if not rps.rps_id:
            logger.error("Gagal memperbarui rps: rps_id kosong.")
            return False
            
        query = """
        -- Memperbarui data RPS berdasarkan rps_id
        UPDATE rps
        SET meeting_number = %s, topic = %s, sub_topic = %s, cleaned_topic = %s, source_file = %s
        WHERE rps_id = %s;
        """
        params = (
            rps.meeting_number,
            rps.topic,
            rps.sub_topic,
            rps.cleaned_topic,
            rps.source_file,
            rps.rps_id
        )
        logger.info(f"Memperbarui rps ID: {rps.rps_id}")
        affected_rows = self._db.execute_non_query(query, params)
        return affected_rows > 0

    def delete(self, rps_id: int) -> bool:
        """
        Menghapus data RPS berdasarkan ID.

        Args:
            rps_id: ID RPS.

        Returns:
            bool: True jika berhasil dihapus.
        """
        query = """
        -- Menghapus data RPS berdasarkan rps_id
        DELETE FROM rps
        WHERE rps_id = %s;
        """
        logger.info(f"Menghapus rps dengan ID: {rps_id}")
        affected_rows = self._db.execute_non_query(query, (rps_id,))
        return affected_rows > 0

    def delete_by_course(self, course_id: int) -> bool:
        """
        Menghapus seluruh data RPS yang terkait dengan mata kuliah tertentu.

        Sering digunakan ketika user mengunggah ulang dokumen RPS.

        Args:
            course_id: ID mata kuliah.

        Returns:
            bool: True jika ada record yang terhapus atau query berjalan sukses.
        """
        query = """
        -- Menghapus seluruh data RPS berdasarkan course_id
        DELETE FROM rps
        WHERE course_id = %s;
        """
        logger.info(f"Menghapus seluruh rps untuk course_id: {course_id}")
        self._db.execute_non_query(query, (course_id,))
        return True

    def count_by_course(self, course_id: int) -> int:
        """
        Mendapatkan total jumlah pertemuan RPS yang terdaftar pada mata kuliah tertentu.

        Args:
            course_id: ID mata kuliah.

        Returns:
            int: Jumlah pertemuan.
        """
        query = """
        -- Menghitung total pertemuan RPS untuk course_id tertentu
        SELECT COUNT(*) as total
        FROM rps
        WHERE course_id = %s;
        """
        results = self._db.execute_query(query, (course_id,))
        if not results:
            return 0
        return results[0]["total"]

    def exists(self, course_id: int, meeting_number: int) -> bool:
        """
        Memeriksa apakah data RPS untuk pertemuan tertentu sudah ada di database.

        Args:
            course_id: ID mata kuliah.
            meeting_number: Nomor pertemuan.

        Returns:
            bool: True jika data ada.
        """
        query = """
        -- Memeriksa keberadaan rps berdasarkan course_id dan meeting_number
        SELECT 1
        FROM rps
        WHERE course_id = %s AND meeting_number = %s;
        """
        results = self._db.execute_query(query, (course_id, meeting_number))
        return len(results) > 0
