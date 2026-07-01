"""
Modul BAP Manager untuk Sistem Validasi RPS-BAP.

Modul ini mengimplementasikan Service Layer untuk mengelola
data Berita Acara Perkuliahan (BAP), termasuk operasi
CRUD dan validasi bisnis.

Sesuai PRD Section 4.6 - Modul BAP Management.

Design Pattern:
    - Service Layer: Logika bisnis terpisah dari akses data
    - Repository Pattern: Akses data melalui BAPRepository
    - Dependency Injection: Semua dependency diinjeksi via constructor
    - Composition: BAPManager has-a BAPRepository, RPSRepository, TextCleaner
"""

from typing import List, Optional, Dict, Any
from datetime import date

from models.bap import BAP
from repositories.bap_repository import BAPRepository
from repositories.rps_repository import RPSRepository
from repositories.course_repository import CourseRepository
from utils.text_cleaner import TextCleaner
from utils.logger import setup_logger
from utils.exceptions import (
    DuplicateMeetingError,
    MeetingNumberExceededError,
    CourseNotFoundError,
    ValidationError,
)
from config.constants import (
    MSG_DUPLICATE_MEETING,
    MSG_MEETING_EXCEEDED,
    MSG_COURSE_NOT_FOUND,
)

# Inisialisasi logger untuk modul ini
logger = setup_logger(__name__)


class BAPManager:
    """
    Service class untuk mengelola data BAP.

    Class ini mengimplementasikan logika bisnis untuk operasi
    CRUD pada data BAP, termasuk validasi nomor pertemuan
    dan pembersihan teks sebelum penyimpanan.

    Sesuai PRD Section 4.6 dan Business Rules:
        - BR-02: Nomor pertemuan BAP unik per mata kuliah dan
                 tidak melebihi total pertemuan RPS
        - BR-03: Text cleaning wajib sebelum penyimpanan

    Composition:
        BAPManager has-a BAPRepository (akses data BAP)
        BAPManager has-a RPSRepository (validasi total pertemuan)
        BAPManager has-a CourseRepository (validasi mata kuliah)
        BAPManager has-a TextCleaner (pembersihan teks)

    Attributes:
        _bap_repo (BAPRepository): Repository untuk operasi data BAP.
        _rps_repo (RPSRepository): Repository untuk mengecek total pertemuan RPS.
        _course_repo (CourseRepository): Repository untuk validasi mata kuliah.
        _text_cleaner (TextCleaner): Utilitas pembersihan teks.
    """

    def __init__(
        self,
        bap_repo: BAPRepository,
        rps_repo: RPSRepository,
        course_repo: CourseRepository,
        text_cleaner: TextCleaner
    ):
        """
        Inisialisasi BAPManager dengan dependency injection.

        Args:
            bap_repo: Repository untuk operasi data BAP.
            rps_repo: Repository untuk validasi total pertemuan.
            course_repo: Repository untuk validasi mata kuliah.
            text_cleaner: Utilitas pembersihan teks.
        """
        # Composition: menyimpan referensi ke seluruh dependency
        self._bap_repo: BAPRepository = bap_repo
        self._rps_repo: RPSRepository = rps_repo
        self._course_repo: CourseRepository = course_repo
        self._text_cleaner: TextCleaner = text_cleaner
        logger.info("BAPManager berhasil diinisialisasi")

    def add_bap(self, bap: BAP) -> int:
        """
        Menambahkan satu data BAP baru.

        Melakukan validasi bisnis sebelum penyimpanan:
        1. Validasi keberadaan mata kuliah
        2. Validasi nomor pertemuan unik (BR-02)
        3. Validasi tidak melebihi total pertemuan RPS (BR-02)
        4. Text cleaning pada materi (BR-03)

        Args:
            bap: Objek BAP yang akan ditambahkan.

        Returns:
            int: ID BAP yang baru dibuat.

        Raises:
            CourseNotFoundError: Jika mata kuliah tidak ditemukan.
            DuplicateMeetingError: Jika nomor pertemuan sudah ada.
            MeetingNumberExceededError: Jika melebihi total RPS.
        """
        # Validasi keberadaan mata kuliah
        course = self._course_repo.get_by_id(bap.course_id)
        if course is None:
            logger.error(
                f"Mata kuliah dengan ID {bap.course_id} tidak ditemukan"
            )
            raise CourseNotFoundError(
                MSG_COURSE_NOT_FOUND,
                details={"course_id": bap.course_id}
            )

        # Validasi nomor pertemuan sesuai BR-02
        self._validate_meeting_number(bap.course_id, bap.meeting_number)

        # Membersihkan teks materi sebelum penyimpanan (BR-03)
        if bap.material_taught:
            bap.cleaned_material = self._text_cleaner.clean(
                bap.material_taught
            )
        else:
            bap.cleaned_material = ""

        logger.info(
            f"Menambahkan BAP pertemuan ke-{bap.meeting_number} "
            f"untuk course_id={bap.course_id}"
        )
        return self._bap_repo.create(bap)

    def get_bap_by_course(self, course_id: int) -> List[BAP]:
        """
        Mengambil seluruh data BAP untuk satu mata kuliah.

        Data diurutkan berdasarkan nomor pertemuan secara ascending.

        Args:
            course_id: ID mata kuliah yang datanya akan diambil.

        Returns:
            List[BAP]: Daftar objek BAP terurut berdasarkan meeting_number.
        """
        logger.info(f"Mengambil data BAP untuk course_id={course_id}")
        return self._bap_repo.get_by_course(course_id)

    def get_bap_by_id(self, bap_id: int) -> Optional[BAP]:
        """
        Mengambil satu data BAP berdasarkan ID.

        Args:
            bap_id: ID data BAP yang dicari.

        Returns:
            Optional[BAP]: Objek BAP jika ditemukan, None jika tidak.
        """
        return self._bap_repo.get_by_id(bap_id)

    def update_bap(self, bap_id: int, updated_data: Dict[str, Any]) -> bool:
        """
        Memperbarui data BAP yang sudah ada.

        Jika field 'material_taught' diperbarui, cleaned_material
        juga diperbarui secara otomatis (BR-03).

        Args:
            bap_id: ID data BAP yang akan diperbarui.
            updated_data: Dictionary berisi field yang akan diubah.
                         Key valid: meeting_number, meeting_date,
                         material_taught.

        Returns:
            bool: True jika pembaruan berhasil.

        Raises:
            ValidationError: Jika data BAP tidak ditemukan.
            DuplicateMeetingError: Jika nomor pertemuan baru sudah ada.
            MeetingNumberExceededError: Jika melebihi total RPS.
        """
        # Mengambil data BAP yang akan diperbarui
        existing_bap = self._bap_repo.get_by_id(bap_id)
        if existing_bap is None:
            logger.error(f"Data BAP dengan ID {bap_id} tidak ditemukan")
            raise ValidationError(
                "Data BAP tidak ditemukan",
                details={"bap_id": bap_id}
            )

        # Memvalidasi nomor pertemuan jika diubah (BR-02)
        if "meeting_number" in updated_data:
            new_meeting = updated_data["meeting_number"]
            if new_meeting != existing_bap.meeting_number:
                self._validate_meeting_number(
                    existing_bap.course_id, new_meeting
                )
            existing_bap.meeting_number = new_meeting

        # Memperbarui tanggal pertemuan
        if "meeting_date" in updated_data:
            existing_bap.meeting_date = updated_data["meeting_date"]

        # Memperbarui materi dan membersihkan teks (BR-03)
        if "material_taught" in updated_data:
            existing_bap.material_taught = updated_data["material_taught"]
            existing_bap.cleaned_material = self._text_cleaner.clean(
                updated_data["material_taught"]
            )

        # Menyimpan perubahan ke database
        logger.info(f"Memperbarui data BAP id={bap_id}")
        result = self._bap_repo.update(existing_bap)
        logger.info("Data BAP berhasil diperbarui")
        return result

    def delete_bap(self, bap_id: int) -> bool:
        """
        Menghapus satu data BAP berdasarkan ID.

        Args:
            bap_id: ID data BAP yang akan dihapus.

        Returns:
            bool: True jika penghapusan berhasil.

        Raises:
            ValidationError: Jika data BAP tidak ditemukan.
        """
        # Memastikan data BAP ada sebelum dihapus
        existing_bap = self._bap_repo.get_by_id(bap_id)
        if existing_bap is None:
            logger.error(f"Data BAP dengan ID {bap_id} tidak ditemukan")
            raise ValidationError(
                "Data BAP tidak ditemukan",
                details={"bap_id": bap_id}
            )

        logger.info(f"Menghapus data BAP id={bap_id}")
        return self._bap_repo.delete(bap_id)

    def _validate_meeting_number(
        self, course_id: int, meeting_number: int
    ) -> None:
        """
        Memvalidasi nomor pertemuan BAP sesuai Business Rules.

        Sesuai PRD BR-02:
        1. Nomor pertemuan harus unik per mata kuliah
        2. Tidak boleh melebihi total pertemuan yang ada di RPS

        Args:
            course_id: ID mata kuliah.
            meeting_number: Nomor pertemuan yang akan divalidasi.

        Raises:
            DuplicateMeetingError: Jika nomor pertemuan sudah ada.
            MeetingNumberExceededError: Jika melebihi total RPS.
        """
        # Mengecek duplikasi nomor pertemuan
        if self._bap_repo.exists(course_id, meeting_number):
            logger.warning(
                f"Nomor pertemuan {meeting_number} sudah ada "
                f"untuk course_id={course_id}"
            )
            raise DuplicateMeetingError(
                MSG_DUPLICATE_MEETING,
                details={
                    "course_id": course_id,
                    "meeting_number": meeting_number,
                }
            )

        # Mengecek total pertemuan pada RPS
        total_rps_meetings = self._rps_repo.count_by_course(course_id)
        if total_rps_meetings > 0 and meeting_number > total_rps_meetings:
            logger.warning(
                f"Nomor pertemuan {meeting_number} melebihi "
                f"total RPS ({total_rps_meetings}) "
                f"untuk course_id={course_id}"
            )
            raise MeetingNumberExceededError(
                MSG_MEETING_EXCEEDED,
                details={
                    "course_id": course_id,
                    "meeting_number": meeting_number,
                    "total_rps_meetings": total_rps_meetings,
                }
            )

    def validate_meeting_number(
        self, course_id: int, meeting_number: int
    ) -> bool:
        """
        Memvalidasi nomor pertemuan BAP (versi return boolean).

        Versi publik yang mengembalikan boolean alih-alih
        melempar exception, untuk digunakan oleh GUI.

        Args:
            course_id: ID mata kuliah.
            meeting_number: Nomor pertemuan yang akan divalidasi.

        Returns:
            bool: True jika nomor pertemuan valid (unik dan tidak melebihi).
        """
        try:
            self._validate_meeting_number(course_id, meeting_number)
            return True
        except (DuplicateMeetingError, MeetingNumberExceededError):
            return False

    def get_bap_count(self, course_id: int) -> int:
        """
        Mengambil jumlah data BAP untuk satu mata kuliah.

        Digunakan untuk menampilkan indikator jumlah pertemuan
        yang sudah diinput pada halaman BAP (PRD Section 10.4).

        Args:
            course_id: ID mata kuliah.

        Returns:
            int: Jumlah data BAP.
        """
        return self._bap_repo.count_by_course(course_id)
