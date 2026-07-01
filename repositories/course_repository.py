"""
Modul Repository Course untuk Sistem Validasi RPS-BAP.

Modul ini mengimplementasikan class CourseRepository yang bertanggung jawab
untuk melakukan operasi CRUD data Course ke database MySQL.
"""

from typing import List, Optional, Dict, Any
from models.course import Course
from database.connection import DatabaseConnection
from utils.logger import setup_logger
from utils.exceptions import DatabaseQueryError

# Inisialisasi logger untuk repository course
logger = setup_logger(__name__)


class CourseRepository:
    """
    Repository class untuk entitas Course.

    Menangani interaksi langsung dengan tabel `courses` di database.
    Menerapkan design pattern Repository untuk mengisolasi logika data
    dari business service layer.
    """

    def __init__(self, db: DatabaseConnection) -> None:
        """
        Inisialisasi CourseRepository dengan dependency injection.

        Args:
            db: Instance koneksi database.
        """
        self._db: DatabaseConnection = db

    def create(self, course: Course) -> int:
        """
        Menyimpan data Course baru ke database.

        Args:
            course: Objek Course yang akan disimpan.

        Returns:
            int: ID record yang baru saja dimasukkan (course_id).
        """
        query = """
        -- Menyimpan data mata kuliah baru
        INSERT INTO courses (course_code, course_name, semester, academic_year)
        VALUES (%s, %s, %s, %s);
        """
        params = (
            course.course_code,
            course.course_name,
            course.semester,
            course.academic_year
        )
        logger.info(f"Menyimpan course baru: {course.course_code}")
        last_id = self._db.execute_non_query(query, params)
        course.course_id = last_id
        return last_id

    def get_by_id(self, course_id: int) -> Optional[Course]:
        """
        Mengambil data Course berdasarkan ID.

        Args:
            course_id: ID mata kuliah.

        Returns:
            Optional[Course]: Objek Course jika ditemukan, None jika tidak.
        """
        query = """
        -- Mengambil data mata kuliah berdasarkan course_id
        SELECT course_id, course_code, course_name, semester, academic_year, created_at
        FROM courses
        WHERE course_id = %s;
        """
        logger.debug(f"Mengambil course dengan ID: {course_id}")
        results = self._db.execute_query(query, (course_id,))
        if not results:
            return None
        return Course.from_dict(results[0])

    def get_by_code(self, course_code: str) -> Optional[Course]:
        """
        Mengambil data Course berdasarkan kode mata kuliah.

        Args:
            course_code: Kode mata kuliah.

        Returns:
            Optional[Course]: Objek Course jika ditemukan, None jika tidak.
        """
        query = """
        -- Mengambil data mata kuliah berdasarkan course_code
        SELECT course_id, course_code, course_name, semester, academic_year, created_at
        FROM courses
        WHERE course_code = %s;
        """
        logger.debug(f"Mengambil course dengan kode: {course_code}")
        results = self._db.execute_query(query, (course_code,))
        if not results:
            return None
        return Course.from_dict(results[0])

    def get_all(self) -> List[Course]:
        """
        Mengambil seluruh data Course dari database.

        Returns:
            List[Course]: Daftar objek Course.
        """
        query = """
        -- Mengambil seluruh data mata kuliah
        SELECT course_id, course_code, course_name, semester, academic_year, created_at
        FROM courses
        ORDER BY course_code;
        """
        logger.debug("Mengambil seluruh data course")
        results = self._db.execute_query(query)
        return [Course.from_dict(row) for row in results]

    def get_by_semester(self, semester: str, academic_year: str) -> List[Course]:
        """
        Mengambil daftar Course berdasarkan semester dan tahun akademik.

        Args:
            semester: Nama semester (misal: Ganjil/Genap).
            academic_year: Tahun akademik (misal: 2024/2025).

        Returns:
            List[Course]: Daftar objek Course yang sesuai.
        """
        query = """
        -- Mengambil data mata kuliah berdasarkan semester dan tahun akademik
        SELECT course_id, course_code, course_name, semester, academic_year, created_at
        FROM courses
        WHERE semester = %s AND academic_year = %s
        ORDER BY course_code;
        """
        logger.debug(f"Mengambil course untuk semester: {semester}, tahun: {academic_year}")
        results = self._db.execute_query(query, (semester, academic_year))
        return [Course.from_dict(row) for row in results]

    def update(self, course: Course) -> bool:
        """
        Memperbarui data Course yang sudah ada di database.

        Args:
            course: Objek Course yang berisi data baru.

        Returns:
            bool: True jika berhasil diperbarui, False jika gagal.
        """
        if not course.course_id:
            logger.error("Gagal memperbarui course: course_id kosong.")
            return False
            
        query = """
        -- Memperbarui data mata kuliah berdasarkan course_id
        UPDATE courses
        SET course_code = %s, course_name = %s, semester = %s, academic_year = %s
        WHERE course_id = %s;
        """
        params = (
            course.course_code,
            course.course_name,
            course.semester,
            course.academic_year,
            course.course_id
        )
        logger.info(f"Memperbarui course ID: {course.course_id}")
        affected_rows = self._db.execute_non_query(query, params)
        return affected_rows > 0

    def delete(self, course_id: int) -> bool:
        """
        Menghapus data Course dari database berdasarkan ID.

        Args:
            course_id: ID mata kuliah.

        Returns:
            bool: True jika berhasil dihapus, False jika gagal.
        """
        query = """
        -- Menghapus data mata kuliah berdasarkan course_id
        DELETE FROM courses
        WHERE course_id = %s;
        """
        logger.info(f"Menghapus course dengan ID: {course_id}")
        affected_rows = self._db.execute_non_query(query, (course_id,))
        return affected_rows > 0
