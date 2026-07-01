"""
Modul Entity Course untuk Sistem Validasi RPS-BAP.

Modul ini mendefinisikan class Course yang merepresentasikan
data mata kuliah dalam sistem.
"""

from datetime import datetime
from typing import Optional, Dict, Any


class Course:
    """
    Class yang merepresentasikan entitas Mata Kuliah (Course).

    Attributes:
        course_code (str): Kode unik mata kuliah.
        course_name (str): Nama mata kuliah.
        semester (str): Semester mata kuliah (Ganjil/Genap).
        academic_year (str): Tahun akademik (misal: 2024/2025).
        course_id (Optional[int]): ID mata kuliah (Primary Key di database).
        created_at (Optional[datetime]): Waktu data dibuat.
    """

    def __init__(
        self,
        course_code: str,
        course_name: str,
        semester: str,
        academic_year: str,
        course_id: Optional[int] = None,
        created_at: Optional[datetime] = None
    ) -> None:
        """
        Inisialisasi objek Course.

        Args:
            course_code: Kode unik mata kuliah.
            course_name: Nama mata kuliah.
            semester: Semester mata kuliah.
            academic_year: Tahun akademik.
            course_id: ID unik mata kuliah.
            created_at: Waktu pembuatan data.
        """
        self.course_id: Optional[int] = course_id
        self.course_code: str = course_code
        self.course_name: str = course_name
        self.semester: str = semester
        self.academic_year: str = academic_year
        self.created_at: Optional[datetime] = created_at

    def to_dict(self) -> Dict[str, Any]:
        """
        Mengonversi objek Course menjadi dictionary.

        Returns:
            Dict[str, Any]: Representasi dictionary dari Course.
        """
        return {
            "course_id": self.course_id,
            "course_code": self.course_code,
            "course_name": self.course_name,
            "semester": self.semester,
            "academic_year": self.academic_year,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Course":
        """
        Membuat objek Course dari dictionary.

        Args:
            data: Dictionary berisi data Course.

        Returns:
            Course: Objek Course yang baru dibuat.
        """
        return cls(
            course_id=data.get("course_id"),
            course_code=data.get("course_code", ""),
            course_name=data.get("course_name", ""),
            semester=data.get("semester", ""),
            academic_year=data.get("academic_year", ""),
            created_at=data.get("created_at")
        )

    def __repr__(self) -> str:
        """
        Representasi string dari objek Course.

        Returns:
            str: Representasi string.
        """
        return (
            f"Course(course_id={self.course_id}, course_code='{self.course_code}', "
            f"course_name='{self.course_name}', semester='{self.semester}', "
            f"academic_year='{self.academic_year}')"
        )
