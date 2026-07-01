"""
Modul RPS Manager untuk Sistem Validasi RPS-BAP.

Modul ini mengimplementasikan Service Layer untuk mengelola
data Rencana Pembelajaran Semester (RPS), termasuk operasi
CRUD dan validasi bisnis.

Sesuai PRD - Modul RPS Management.
"""

from typing import List, Optional, Dict, Any
from models.rps import RPS
from repositories.rps_repository import RPSRepository
from utils.text_cleaner import TextCleaner
from utils.logger import setup_logger
from utils.exceptions import DuplicateMeetingError, ValidationError
from config.constants import MSG_DUPLICATE_MEETING

# Inisialisasi logger untuk modul ini
logger = setup_logger(__name__)


class RPSManager:
    """
    Service class untuk mengelola data RPS.

    Class ini mengimplementasikan logika bisnis untuk operasi
    CRUD pada data RPS, termasuk validasi nomor pertemuan unik
    dan pembersihan teks sebelum penyimpanan.

    Business Rules:
        - BR-01: Nomor pertemuan RPS harus unik secara global
        - BR-03: Text cleaning wajib dilakukan sebelum penyimpanan
    """

    def __init__(
        self,
        rps_repo: RPSRepository,
        text_cleaner: TextCleaner
    ):
        """
        Inisialisasi RPSManager dengan dependency injection.

        Args:
            rps_repo: Repository untuk operasi data RPS.
            text_cleaner: Utilitas pembersihan teks.
        """
        self._rps_repo: RPSRepository = rps_repo
        self._text_cleaner: TextCleaner = text_cleaner
        logger.info("RPSManager berhasil diinisialisasi")

    def save_rps(self, rps_list: List[RPS], filename: str, filepath: str, filesize_kb: int) -> bool:
        """
        Menyimpan daftar data RPS hasil ekstraksi PDF ke database.

        Mengganti seluruh data akademik aktif secara transaksional,
        tetapi menyisipkan log audit baru ke riwayat unggah.

        Args:
            rps_list: Daftar objek RPS yang akan disimpan.
            filename: Nama file baru.
            filepath: Path file baru.
            filesize_kb: Ukuran file baru.

        Returns:
            bool: True jika penyimpanan berhasil.
        """
        # Membersihkan teks topik sebelum penyimpanan (BR-03)
        for rps in rps_list:
            if rps.topic:
                rps.cleaned_topic = self._text_cleaner.clean(rps.topic)
            else:
                rps.cleaned_topic = ""

        logger.info(
            f"Menyimpan {len(rps_list)} data RPS secara transaksional REPLACE ALL."
        )
        result = self._rps_repo.replace_all_rps(rps_list, filename, filepath, filesize_kb)
        logger.info("Data RPS berhasil disimpan")
        return result

    def get_all_rps(self) -> List[RPS]:
        """
        Mengambil seluruh data RPS terurut berdasarkan nomor pertemuan.

        Returns:
            List[RPS]: Daftar objek RPS terurut.
        """
        logger.info("Mengambil seluruh data RPS aktif")
        return self._rps_repo.get_all()

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

        Args:
            rps_id: ID data RPS yang akan diperbarui.
            updated_data: Dictionary berisi field yang akan diubah.

        Returns:
            bool: True jika pembaruan berhasil.

        Raises:
            ValidationError: Jika data RPS tidak ditemukan.
            DuplicateMeetingError: Jika nomor pertemuan baru sudah ada.
        """
        existing_rps = self._rps_repo.get_by_id(rps_id)
        if existing_rps is None:
            logger.error(f"Data RPS dengan ID {rps_id} tidak ditemukan")
            raise ValidationError(
                "Data RPS tidak ditemukan",
                details={"rps_id": rps_id}
            )

        if "meeting_number" in updated_data:
            new_meeting = updated_data["meeting_number"]
            if new_meeting != existing_rps.meeting_number:
                if not self.validate_unique_meeting_number(new_meeting):
                    raise DuplicateMeetingError(
                        MSG_DUPLICATE_MEETING,
                        details={
                            "meeting_number": new_meeting,
                        }
                    )
            existing_rps.meeting_number = new_meeting

        if "topic" in updated_data:
            existing_rps.topic = updated_data["topic"]
            existing_rps.cleaned_topic = self._text_cleaner.clean(
                updated_data["topic"]
            )

        if "sub_topic" in updated_data:
            existing_rps.sub_topic = updated_data["sub_topic"]

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
        existing_rps = self._rps_repo.get_by_id(rps_id)
        if existing_rps is None:
            logger.error(f"Data RPS dengan ID {rps_id} tidak ditemukan")
            raise ValidationError(
                "Data RPS tidak ditemukan",
                details={"rps_id": rps_id}
            )

        logger.info(f"Menghapus data RPS id={rps_id}")
        return self._rps_repo.delete(rps_id)

    def validate_unique_meeting_number(self, meeting_number: int) -> bool:
        """
        Memvalidasi bahwa nomor pertemuan unik.

        Args:
            meeting_number: Nomor pertemuan yang akan divalidasi.

        Returns:
            bool: True jika nomor pertemuan belum ada.
        """
        is_existing = self._rps_repo.exists(meeting_number)
        if is_existing:
            logger.warning(
                f"Nomor pertemuan {meeting_number} sudah ada di database"
            )
        return not is_existing

    def get_total_meetings(self) -> int:
        """
        Mengambil total jumlah pertemuan RPS yang aktif.

        Returns:
            int: Total jumlah pertemuan RPS.
        """
        return self._rps_repo.count_all()

    def add_single_rps(self, rps: RPS) -> int:
        """
        Menambahkan satu data RPS secara manual.

        Args:
            rps: Objek RPS yang akan ditambahkan.

        Returns:
            int: ID RPS yang baru dibuat.

        Raises:
            DuplicateMeetingError: Jika nomor pertemuan sudah ada.
        """
        if not self.validate_unique_meeting_number(rps.meeting_number):
            raise DuplicateMeetingError(
                MSG_DUPLICATE_MEETING,
                details={
                    "meeting_number": rps.meeting_number,
                }
            )

        if rps.topic:
            rps.cleaned_topic = self._text_cleaner.clean(rps.topic)

        logger.info(
            f"Menambahkan RPS pertemuan ke-{rps.meeting_number} secara manual."
        )
        return self._rps_repo.create(rps)
