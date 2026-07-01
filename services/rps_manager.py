"""
Modul RPS Manager untuk Sistem Validasi RPS-BAP.

Modul ini mengimplementasikan Service Layer untuk mengelola
data Rencana Pembelajaran Semester (RPS), termasuk operasi
CRUD dan validasi bisnis.

Sesuai PRD Section 4.5 - Modul RPS Management.

Design Pattern:
    - Service Layer: Memisahkan logika bisnis dari akses data
    - Repository Pattern: Akses data melalui RPSRepository
    - Dependency Injection: Repository dan TextCleaner diinjeksi
    - Composition: RPSManager has-a RPSRepository, TextCleaner
"""

from typing import List, Optional, Dict, Any

from models.rps import RPS
from models.course import Course
from repositories.rps_repository import RPSRepository
from repositories.course_repository import CourseRepository
from utils.text_cleaner import TextCleaner
from utils.logger import setup_logger
from utils.exceptions import (
    DuplicateMeetingError,
    CourseNotFoundError,
    ValidationError,
)
from config.constants import MSG_DUPLICATE_MEETING, MSG_COURSE_NOT_FOUND

# Inisialisasi logger untuk modul ini
logger = setup_logger(__name__)


class RPSManager:
    """
    Service class untuk mengelola data RPS.

    Class ini mengimplementasikan logika bisnis untuk operasi
    CRUD pada data RPS, termasuk validasi nomor pertemuan unik
    dan pembersihan teks sebelum penyimpanan.

    Sesuai PRD Section 4.5 dan Business Rules:
        - BR-01: Nomor pertemuan RPS harus unik per mata kuliah
        - BR-03: Text cleaning wajib dilakukan sebelum penyimpanan
        - BR-12: Satu mata kuliah hanya boleh satu RPS aktif

    Composition:
        RPSManager has-a RPSRepository (akses data)
        RPSManager has-a CourseRepository (validasi mata kuliah)
        RPSManager has-a TextCleaner (pembersihan teks)

    Attributes:
        _rps_repo (RPSRepository): Repository untuk operasi data RPS.
        _course_repo (CourseRepository): Repository untuk data mata kuliah.
        _text_cleaner (TextCleaner): Utilitas pembersihan teks.
    """

    def __init__(
        self,
        rps_repo: RPSRepository,
        course_repo: CourseRepository,
        text_cleaner: TextCleaner
    ):
        """
        Inisialisasi RPSManager dengan dependency injection.

        Args:
            rps_repo: Repository untuk operasi data RPS.
            course_repo: Repository untuk validasi mata kuliah.
            text_cleaner: Utilitas pembersihan teks.
        """
        # Composition: menyimpan referensi ke dependency
        self._rps_repo: RPSRepository = rps_repo
        self._course_repo: CourseRepository = course_repo
        self._text_cleaner: TextCleaner = text_cleaner
        logger.info("RPSManager berhasil diinisialisasi")

    def save_rps(self, rps_list: List[RPS], course_id: int) -> bool:
        """
        Menyimpan daftar data RPS hasil ekstraksi PDF ke database.

        Sesuai PRD BR-12: Unggahan baru menggantikan data sebelumnya.
        Method ini menghapus data RPS lama untuk mata kuliah tersebut
        sebelum menyimpan data baru.

        Sesuai PRD BR-03: Text cleaning dilakukan sebelum penyimpanan.

        Args:
            rps_list: Daftar objek RPS yang akan disimpan.
            course_id: ID mata kuliah terkait.

        Returns:
            bool: True jika penyimpanan berhasil.

        Raises:
            CourseNotFoundError: Jika mata kuliah tidak ditemukan.
            ValidationError: Jika data tidak valid.
        """
        # Memvalidasi keberadaan mata kuliah di database
        course = self._course_repo.get_by_id(course_id)
        if course is None:
            logger.error(f"Mata kuliah dengan ID {course_id} tidak ditemukan")
            raise CourseNotFoundError(
                MSG_COURSE_NOT_FOUND,
                details={"course_id": course_id}
            )

        # Membersihkan teks topik sebelum penyimpanan (BR-03)
        for rps in rps_list:
            rps.course_id = course_id
            if rps.topic:
                rps.cleaned_topic = self._text_cleaner.clean(rps.topic)
            else:
                rps.cleaned_topic = ""

        # Menghapus data RPS lama untuk mata kuliah ini (BR-12)
        logger.info(
            f"Menghapus data RPS lama untuk course_id={course_id}"
        )
        self._rps_repo.delete_by_course(course_id)

        # Menyimpan data RPS baru secara batch
        logger.info(
            f"Menyimpan {len(rps_list)} data RPS untuk course_id={course_id}"
        )
        result = self._rps_repo.save_batch(rps_list)
        logger.info("Data RPS berhasil disimpan")
        return result

    def get_rps_by_course(self, course_id: int) -> List[RPS]:
        """
        Mengambil seluruh data RPS untuk satu mata kuliah.

        Data diurutkan berdasarkan nomor pertemuan secara ascending.

        Args:
            course_id: ID mata kuliah yang datanya akan diambil.

        Returns:
            List[RPS]: Daftar objek RPS terurut berdasarkan meeting_number.
        """
        logger.info(f"Mengambil data RPS untuk course_id={course_id}")
        return self._rps_repo.get_by_course(course_id)

    def get_rps_by_id(self, rps_id: int) -> Optional[RPS]:
        """
        Mengambil satu data RPS berdasarkan ID.

        Args:
            rps_id: ID data RPS yang dicari.

        Returns:
            Optional[RPS]: Objek RPS jika ditemukan, None jika tidak.
        """
        return self._rps_repo.get_by_id(rps_id)

    def update_rps(self, rps_id: int, updated_data: Dict[str, Any]) -> bool:
        """
        Memperbarui data RPS yang sudah ada.

        Jika field 'topic' diperbarui, cleaned_topic juga diperbarui
        secara otomatis melalui text cleaning (BR-03).

        Args:
            rps_id: ID data RPS yang akan diperbarui.
            updated_data: Dictionary berisi field yang akan diubah.
                         Key yang valid: topic, sub_topic, meeting_number.

        Returns:
            bool: True jika pembaruan berhasil.

        Raises:
            ValidationError: Jika data RPS tidak ditemukan.
            DuplicateMeetingError: Jika nomor pertemuan baru sudah ada.
        """
        # Mengambil data RPS yang akan diperbarui
        existing_rps = self._rps_repo.get_by_id(rps_id)
        if existing_rps is None:
            logger.error(f"Data RPS dengan ID {rps_id} tidak ditemukan")
            raise ValidationError(
                "Data RPS tidak ditemukan",
                details={"rps_id": rps_id}
            )

        # Memvalidasi nomor pertemuan jika diubah (BR-01)
        if "meeting_number" in updated_data:
            new_meeting = updated_data["meeting_number"]
            if new_meeting != existing_rps.meeting_number:
                if not self.validate_unique_meeting_number(
                    existing_rps.course_id, new_meeting
                ):
                    raise DuplicateMeetingError(
                        MSG_DUPLICATE_MEETING,
                        details={
                            "course_id": existing_rps.course_id,
                            "meeting_number": new_meeting,
                        }
                    )
            existing_rps.meeting_number = new_meeting

        # Memperbarui topik dan membersihkan teks (BR-03)
        if "topic" in updated_data:
            existing_rps.topic = updated_data["topic"]
            existing_rps.cleaned_topic = self._text_cleaner.clean(
                updated_data["topic"]
            )

        # Memperbarui sub topik jika ada
        if "sub_topic" in updated_data:
            existing_rps.sub_topic = updated_data["sub_topic"]

        # Menyimpan perubahan ke database
        logger.info(f"Memperbarui data RPS id={rps_id}")
        result = self._rps_repo.update(existing_rps)
        logger.info("Data RPS berhasil diperbarui")
        return result

    def delete_rps(self, rps_id: int) -> bool:
        """
        Menghapus satu data RPS berdasarkan ID.

        Args:
            rps_id: ID data RPS yang akan dihapus.

        Returns:
            bool: True jika penghapusan berhasil.

        Raises:
            ValidationError: Jika data RPS tidak ditemukan.
        """
        # Memastikan data RPS ada sebelum dihapus
        existing_rps = self._rps_repo.get_by_id(rps_id)
        if existing_rps is None:
            logger.error(f"Data RPS dengan ID {rps_id} tidak ditemukan")
            raise ValidationError(
                "Data RPS tidak ditemukan",
                details={"rps_id": rps_id}
            )

        logger.info(f"Menghapus data RPS id={rps_id}")
        return self._rps_repo.delete(rps_id)

    def validate_unique_meeting_number(
        self, course_id: int, meeting_number: int
    ) -> bool:
        """
        Memvalidasi bahwa nomor pertemuan unik per mata kuliah.

        Sesuai PRD BR-01: Setiap nomor pertemuan pada RPS
        harus unik dalam satu mata kuliah.

        Args:
            course_id: ID mata kuliah.
            meeting_number: Nomor pertemuan yang akan divalidasi.

        Returns:
            bool: True jika nomor pertemuan belum ada (unik).
        """
        # Mengecek keberadaan nomor pertemuan di database
        is_existing = self._rps_repo.exists(course_id, meeting_number)
        if is_existing:
            logger.warning(
                f"Nomor pertemuan {meeting_number} sudah ada "
                f"untuk course_id={course_id}"
            )
        return not is_existing

    def get_total_meetings(self, course_id: int) -> int:
        """
        Mengambil total jumlah pertemuan RPS untuk satu mata kuliah.

        Digunakan oleh BAPManager untuk validasi BR-02
        (nomor pertemuan BAP tidak boleh melebihi total RPS).

        Args:
            course_id: ID mata kuliah.

        Returns:
            int: Total jumlah pertemuan RPS.
        """
        return self._rps_repo.count_by_course(course_id)

    def add_single_rps(self, rps: RPS) -> int:
        """
        Menambahkan satu data RPS secara manual.

        Digunakan untuk koreksi manual hasil ekstraksi PDF
        sesuai PRD Section 4.5.

        Args:
            rps: Objek RPS yang akan ditambahkan.

        Returns:
            int: ID RPS yang baru dibuat.

        Raises:
            CourseNotFoundError: Jika mata kuliah tidak ditemukan.
            DuplicateMeetingError: Jika nomor pertemuan sudah ada.
        """
        # Validasi keberadaan mata kuliah
        course = self._course_repo.get_by_id(rps.course_id)
        if course is None:
            raise CourseNotFoundError(
                MSG_COURSE_NOT_FOUND,
                details={"course_id": rps.course_id}
            )

        # Validasi nomor pertemuan unik (BR-01)
        if not self.validate_unique_meeting_number(
            rps.course_id, rps.meeting_number
        ):
            raise DuplicateMeetingError(
                MSG_DUPLICATE_MEETING,
                details={
                    "course_id": rps.course_id,
                    "meeting_number": rps.meeting_number,
                }
            )

        # Membersihkan teks topik (BR-03)
        if rps.topic:
            rps.cleaned_topic = self._text_cleaner.clean(rps.topic)

        logger.info(
            f"Menambahkan RPS pertemuan ke-{rps.meeting_number} "
            f"untuk course_id={rps.course_id}"
        )
        return self._rps_repo.create(rps)
