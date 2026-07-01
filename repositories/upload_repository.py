"""
Modul Repository Upload untuk Sistem Validasi RPS-BAP.

Modul ini mengimplementasikan class UploadRepository yang bertanggung jawab
untuk mencatat riwayat unggahan dokumen PDF RPS ke database MySQL.
"""

from typing import List, Optional, Dict, Any
from database.connection import DatabaseConnection
from utils.logger import setup_logger
from utils.exceptions import DatabaseQueryError

# Inisialisasi logger untuk repository upload
logger = setup_logger(__name__)


class UploadRepository:
    """
    Repository class untuk entitas UploadHistory.

    Menangani interaksi langsung dengan tabel `upload_history` di database.
    Mendukung audit log riwayat upload dokumen RPS sesuai PRD BR-15.
    """

    def __init__(self, db: DatabaseConnection) -> None:
        """
        Inisialisasi UploadRepository dengan dependency injection.

        Args:
            db: Instance koneksi database.
        """
        self._db: DatabaseConnection = db

    def create(
        self,
        course_id: int,
        file_name: str,
        file_path: str,
        file_size_kb: int,
        upload_status: str,
        error_message: Optional[str] = None
    ) -> int:
        """
        Menyimpan data riwayat unggahan file ke database.

        Args:
            course_id: ID mata kuliah terkait.
            file_name: Nama asli file.
            file_path: Lokasi penyimpanan file di server/lokal.
            file_size_kb: Ukuran file dalam kilobyte.
            upload_status: Status upload ('SUCCESS' atau 'FAILED').
            error_message: Keterangan error jika status 'FAILED' (opsional).

        Returns:
            int: ID record baru (upload_id).
        """
        query = """
        -- Menyimpan data riwayat unggahan baru
        INSERT INTO upload_history (course_id, file_name, file_path, file_size_kb, upload_status, error_message)
        VALUES (%s, %s, %s, %s, %s, %s);
        """
        params = (
            course_id,
            file_name,
            file_path,
            file_size_kb,
            upload_status,
            error_message
        )
        logger.info(f"Mencatat riwayat upload file '{file_name}' status={upload_status} untuk course_id={course_id}")
        last_id = self._db.execute_non_query(query, params)
        return last_id

    def get_by_course(self, course_id: int) -> List[Dict[str, Any]]:
        """
        Mengambil riwayat unggahan berdasarkan ID mata kuliah.

        Args:
            course_id: ID mata kuliah.

        Returns:
            List[Dict[str, Any]]: Daftar riwayat unggahan dalam bentuk list of dictionary.
        """
        query = """
        -- Mengambil riwayat unggahan berdasarkan course_id terurut tanggal terbaru
        SELECT upload_id, course_id, file_name, file_path, file_size_kb, upload_status, error_message, uploaded_at
        FROM upload_history
        WHERE course_id = %s
        ORDER BY uploaded_at DESC;
        """
        logger.debug(f"Mengambil riwayat upload untuk course: {course_id}")
        return self._db.execute_query(query, (course_id,))

    def get_all(self) -> List[Dict[str, Any]]:
        """
        Mengambil seluruh riwayat unggahan dari database.

        Returns:
            List[Dict[str, Any]]: Daftar seluruh riwayat unggahan.
        """
        query = """
        -- Mengambil seluruh data riwayat unggahan terurut tanggal terbaru
        SELECT upload_id, course_id, file_name, file_path, file_size_kb, upload_status, error_message, uploaded_at
        FROM upload_history
        ORDER BY uploaded_at DESC;
        """
        logger.debug("Mengambil seluruh riwayat upload")
        return self._db.execute_query(query)
