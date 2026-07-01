"""
Modul BAP Manager untuk Sistem Validasi RPS-BAP.

Modul ini mengimplementasikan Service Layer untuk mengelola
data Berita Acara Perkuliahan (BAP), termasuk operasi
CRUD dan validasi bisnis.

Sesuai PRD - Modul BAP Management.
"""

from typing import List, Optional, Dict, Any
from models.bap import BAP
from repositories.bap_repository import BAPRepository
from repositories.rps_repository import RPSRepository
from utils.text_cleaner import TextCleaner
from utils.logger import setup_logger
from utils.exceptions import (
    DuplicateMeetingError,
    MeetingNumberExceededError,
    ValidationError,
)
from config.constants import (
    MSG_DUPLICATE_MEETING,
    MSG_MEETING_EXCEEDED,
)

# Inisialisasi logger untuk modul ini
logger = setup_logger(__name__)


class BAPManager:
    """
    Service class untuk mengelola data BAP.

    Class ini mengimplementasikan logika bisnis untuk operasi
    CRUD pada data BAP, termasuk validasi nomor pertemuan
    dan pembersihan teks sebelum penyimpanan.

    Business Rules:
        - BR-02: Nomor pertemuan BAP unik dan tidak melebihi total pertemuan RPS
        - BR-03: Text cleaning wajib sebelum penyimpanan
    """

    def __init__(
        self,
        bap_repo: BAPRepository,
        rps_repo: RPSRepository,
        text_cleaner: TextCleaner
    ):
        """
        Inisialisasi BAPManager dengan dependency injection.

        Args:
            bap_repo: Repository untuk operasi data BAP.
            rps_repo: Repository untuk validasi total pertemuan.
            text_cleaner: Utilitas pembersihan teks.
        """
        self._bap_repo: BAPRepository = bap_repo
        self._rps_repo: RPSRepository = rps_repo
        self._text_cleaner: TextCleaner = text_cleaner
        logger.info("BAPManager berhasil diinisialisasi")

    def add_bap(self, bap: BAP) -> int:
        """
        Menambahkan satu data BAP baru.

        Args:
            bap: Objek BAP yang akan ditambahkan.

        Returns:
            int: ID BAP yang baru dibuat.

        Raises:
            DuplicateMeetingError: Jika nomor pertemuan sudah ada.
            MeetingNumberExceededError: Jika melebihi total RPS.
        """
        # Validasi nomor pertemuan sesuai BR-02
        self._validate_meeting_number(bap.meeting_number)

        # Membersihkan teks materi sebelum penyimpanan (BR-03)
        if bap.material_taught:
            bap.cleaned_material = self._text_cleaner.clean(
                bap.material_taught
            )
        else:
            bap.cleaned_material = ""

        logger.info(f"Menambahkan BAP pertemuan ke-{bap.meeting_number}")
        return self._bap_repo.create(bap)

    def get_all_bap(self) -> List[BAP]:
        """
        Mengambil seluruh data BAP terurut berdasarkan nomor pertemuan.

        Returns:
            List[BAP]: Daftar objek BAP terurut.
        """
        logger.info("Mengambil seluruh data BAP aktif")
        return self._bap_repo.get_all()

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

        Args:
            bap_id: ID data BAP yang akan diperbarui.
            updated_data: Dictionary berisi field yang akan diubah.

        Returns:
            bool: True jika pembaruan berhasil.

        Raises:
            ValidationError: Jika data BAP tidak ditemukan.
            DuplicateMeetingError: Jika nomor pertemuan baru sudah ada.
            MeetingNumberExceededError: Jika melebihi total RPS.
        """
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
                self._validate_meeting_number(new_meeting)
            existing_bap.meeting_number = new_meeting

        if "meeting_date" in updated_data:
            existing_bap.meeting_date = updated_data["meeting_date"]

        if "material_taught" in updated_data:
            existing_bap.material_taught = updated_data["material_taught"]
            existing_bap.cleaned_material = self._text_cleaner.clean(
                updated_data["material_taught"]
            )

        logger.info(f"Memperbarui data BAP id={bap_id}")
        result = self._bap_repo.update(existing_bap)
        logger.info("Data BAP berhasil diperbarui")
        return result

    def get_total_rps_meetings(self) -> int:
        """
        Mengambil total pertemuan RPS aktif untuk kebutuhan progress BAP.

        Returns:
            int: Total pertemuan RPS aktif.
        """
        return self._rps_repo.count_all()

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
        existing_bap = self._bap_repo.get_by_id(bap_id)
        if existing_bap is None:
            logger.error(f"Data BAP dengan ID {bap_id} tidak ditemukan")
            raise ValidationError(
                "Data BAP tidak ditemukan",
                details={"bap_id": bap_id}
            )

        logger.info(f"Menghapus data BAP id={bap_id}")
        return self._bap_repo.delete(bap_id)

    def _validate_meeting_number(self, meeting_number: int) -> None:
        """
        Memvalidasi nomor pertemuan BAP sesuai Business Rules.

        Raises:
            DuplicateMeetingError: Jika nomor pertemuan sudah ada.
            MeetingNumberExceededError: Jika melebihi total RPS.
        """
        if self._bap_repo.exists(meeting_number):
            logger.warning(
                f"Nomor pertemuan {meeting_number} sudah ada di database"
            )
            raise DuplicateMeetingError(
                MSG_DUPLICATE_MEETING,
                details={
                    "meeting_number": meeting_number,
                }
            )

        total_rps_meetings = self._rps_repo.count_all()
        if total_rps_meetings > 0 and meeting_number > total_rps_meetings:
            logger.warning(
                f"Nomor pertemuan {meeting_number} melebihi total RPS ({total_rps_meetings})"
            )
            raise MeetingNumberExceededError(
                MSG_MEETING_EXCEEDED,
                details={
                    "meeting_number": meeting_number,
                    "total_rps_meetings": total_rps_meetings,
                }
            )

    def validate_meeting_number(self, meeting_number: int) -> bool:
        """
        Memvalidasi nomor pertemuan BAP (versi return boolean).

        Args:
            meeting_number: Nomor pertemuan yang akan divalidasi.

        Returns:
            bool: True jika nomor pertemuan valid.
        """
        try:
            self._validate_meeting_number(meeting_number)
            return True
        except (DuplicateMeetingError, MeetingNumberExceededError):
            return False

    def get_bap_count(self) -> int:
        """
        Mengambil jumlah data BAP yang aktif.

        Returns:
            int: Jumlah data BAP.
        """
        return self._bap_repo.count_all()
