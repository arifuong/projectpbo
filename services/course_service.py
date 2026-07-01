"""
Modul CourseService untuk Sistem Validasi RPS-BAP.

Modul ini mengimplementasikan Service Layer untuk pengelolaan mata kuliah (Course).
Bertanggung jawab sebagai penghubung antara GUI dan CourseRepository.
"""

from typing import List, Optional
from models.course import Course
from repositories.course_repository import CourseRepository
from utils.logger import setup_logger

# Inisialisasi logger untuk CourseService
logger = setup_logger(__name__)


class CourseService:
    """
    Service class untuk mengelola entitas Course.

    Attributes:
        _course_repo (CourseRepository): Repository untuk kueri Course.
    """

    def __init__(self, course_repo: CourseRepository) -> None:
        """
        Inisialisasi CourseService.

        Args:
            course_repo: Repository data course.
        """
        self._course_repo: CourseRepository = course_repo
        logger.info("CourseService berhasil diinisialisasi.")

    def get_all_courses(self) -> List[Course]:
        """
        Mengambil seluruh mata kuliah yang terdaftar.

        Returns:
            List[Course]: Daftar mata kuliah.
        """
        return self._course_repo.get_all()

    def get_course_by_id(self, course_id: int) -> Optional[Course]:
        """
        Mengambil detail mata kuliah berdasarkan ID.

        Args:
            course_id: ID mata kuliah.

        Returns:
            Optional[Course]: Detail mata kuliah.
        """
        return self._course_repo.get_by_id(course_id)

    def get_course_by_code(self, course_code: str) -> Optional[Course]:
        """
        Mengambil detail mata kuliah berdasarkan kode.

        Args:
            course_code: Kode mata kuliah.

        Returns:
            Optional[Course]: Detail mata kuliah.
        """
        return self._course_repo.get_by_code(course_code)

    def create_course(self, course_code: str, course_name: str, semester: str, academic_year: str) -> int:
        """
        Membuat mata kuliah baru di sistem.

        Args:
            course_code: Kode unik.
            course_name: Nama lengkap.
            semester: Ganjil / Genap.
            academic_year: Format YYYY/YYYY.

        Returns:
            int: ID record baru.
        """
        course = Course(
            course_code=course_code,
            course_name=course_name,
            semester=semester,
            academic_year=academic_year
        )
        return self._course_repo.create(course)

    def update_course(self, course_id: int, course_code: str, course_name: str, semester: str, academic_year: str) -> bool:
        """
        Memperbarui data mata kuliah.

        Args:
            course_id: ID mata kuliah.
            course_code: Kode baru.
            course_name: Nama baru.
            semester: Semester baru.
            academic_year: Tahun akademik baru.

        Returns:
            bool: True jika berhasil.
        """
        course = Course(
            course_code=course_code,
            course_name=course_name,
            semester=semester,
            academic_year=academic_year,
            course_id=course_id
        )
        return self._course_repo.update(course)

    def delete_course(self, course_id: int) -> bool:
        """
        Menghapus mata kuliah.

        Args:
            course_id: ID mata kuliah.

        Returns:
            bool: True jika berhasil.
        """
        return self._course_repo.delete(course_id)
