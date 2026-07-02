"""
Modul Validator untuk Sistem Validasi RPS-BAP.

Modul ini merupakan inti logika bisnis sistem yang menggabungkan
hasil Keyword Matching dengan pengecekan urutan pertemuan,
kemudian menetapkan status akhir tiap pertemuan.

Sesuai PRD - Modul Validation Engine.
"""

from typing import List, Dict, Optional, Tuple

from models.rps import RPS
from models.bap import BAP
from models.validation_result import ValidationResult
from repositories.rps_repository import RPSRepository
from repositories.bap_repository import BAPRepository
from repositories.validation_repository import ValidationRepository
from services.keyword_matcher import KeywordMatcher
from utils.logger import setup_logger
from utils.exceptions import ValidationError
from config.constants import (
    STATUS_SESUAI,
    STATUS_TIDAK_SESUAI,
    STATUS_TIDAK_DITEMUKAN,
    STATUS_PENDING,
    MSG_VALIDATION_NO_DATA,
)

# Inisialisasi logger untuk modul ini
logger = setup_logger(__name__)


class Validator:
    """
    Class inti untuk melakukan validasi kesesuaian RPS dan BAP.
    """

    def __init__(
        self,
        matcher: KeywordMatcher,
        rps_repo: RPSRepository,
        bap_repo: BAPRepository,
        validation_repo: ValidationRepository
    ):
        """
        Inisialisasi Validator dengan dependency injection.

        Args:
            matcher: Objek KeywordMatcher untuk pencocokan kata kunci.
            rps_repo: Repository untuk akses data RPS.
            bap_repo: Repository untuk akses data BAP.
            validation_repo: Repository untuk menyimpan hasil validasi.
        """
        self._matcher: KeywordMatcher = matcher
        self._rps_repo: RPSRepository = rps_repo
        self._bap_repo: BAPRepository = bap_repo
        self._val_repo: ValidationRepository = validation_repo
        logger.info("Validator berhasil diinisialisasi")

    def run_validation(self) -> List[ValidationResult]:
        """
        Menjalankan pipeline utama proses validasi kesesuaian perkuliahan.

        Alur validasi:
        1. Mengambil data RPS dan BAP dari database
        2. Memvalidasi ketersediaan data (BR-13)
        3. Melakukan keyword matching per pertemuan
        4. Menentukan status validasi per pertemuan
        5. Mendeteksi materi yang diacak (shuffled)
        6. Mendeteksi materi yang belum diajarkan
        7. Menyimpan hasil validasi ke database

        Returns:
            List[ValidationResult]: Daftar hasil validasi per pertemuan.

        Raises:
            ValidationError: Jika data RPS atau BAP belum tersedia.
        """
        logger.info("Memulai proses validasi aktif")

        # Mengambil data RPS dan BAP aktif dari database
        rps_list = self._rps_repo.get_all()
        bap_list = self._bap_repo.get_all()

        # Memvalidasi ketersediaan data (BR-13)
        if not rps_list:
            logger.error("Data RPS belum tersedia")
            raise ValidationError(
                MSG_VALIDATION_NO_DATA,
                details={"reason": "RPS kosong"}
            )

        if not bap_list:
            logger.error("Data BAP belum tersedia")
            raise ValidationError(
                MSG_VALIDATION_NO_DATA,
                details={"reason": "BAP kosong"}
            )

        bap_map = {bap.meeting_number: bap for bap in bap_list}
        results = []

        for rps in rps_list:
            meeting_num = rps.meeting_number
            bap = bap_map.get(meeting_num)

            if bap is None:
                # Materi belum diajarkan (BR-10)
                result = ValidationResult(
                    rps_id=rps.rps_id,
                    bap_id=None,
                    meeting_number=meeting_num,
                    similarity_score=0.0,
                    status=STATUS_PENDING,
                    notes="Materi belum diajarkan (BAP belum diinput)"
                )
                results.append(result)
                logger.info(f"Pertemuan ke-{meeting_num}: PENDING (BAP belum ada)")
                continue

            # Melakukan keyword matching antara BAP dan RPS
            rps_topic = rps.topic or ""
            rps_sub_topic = rps.sub_topic or ""
            bap_text = bap.cleaned_material or bap.material_taught or ""

            match_result = self._matcher.match(bap_text, rps_topic, rps_sub_topic)
            similarity_score = match_result["similarity_score"]
            is_matched = match_result["is_match"]

            if is_matched:
                # Skor >= threshold DAN pertemuan sama => SESUAI (BR-06)
                result = ValidationResult(
                    rps_id=rps.rps_id,
                    bap_id=bap.bap_id,
                    meeting_number=meeting_num,
                    similarity_score=round(similarity_score * 100, 2),
                    status=STATUS_SESUAI,
                    notes=(
                        f"Materi sesuai dengan skor {similarity_score * 100:.2f}%. "
                        f"Kata kunci cocok: {match_result.get('matched_keywords', set())}"
                    )
                )
                results.append(result)
                logger.info(f"Pertemuan ke-{meeting_num}: SESUAI (skor={similarity_score * 100:.2f}%)")
            else:
                # Cek apakah cocok dengan pertemuan lain (diacak)
                shuffled_result = self._find_matching_rps(bap_text, rps_list, meeting_num)

                if shuffled_result is not None:
                    # Cocok dengan pertemuan lain => TIDAK_SESUAI (BR-07)
                    matched_meeting, matched_score = shuffled_result
                    result = ValidationResult(
                        rps_id=rps.rps_id,
                        bap_id=bap.bap_id,
                        meeting_number=meeting_num,
                        similarity_score=round(matched_score * 100, 2),
                        status=STATUS_TIDAK_SESUAI,
                        notes=(
                            f"Materi diacak. Cocok dengan pertemuan ke-{matched_meeting} "
                            f"(skor={matched_score * 100:.2f}%)"
                        )
                    )
                    results.append(result)
                    logger.info(f"Pertemuan ke-{meeting_num}: TIDAK_SESUAI (cocok dengan pertemuan ke-{matched_meeting})")
                else:
                    # Tidak cocok dengan RPS manapun => TIDAK_DITEMUKAN (BR-08)
                    result = ValidationResult(
                        rps_id=rps.rps_id,
                        bap_id=bap.bap_id,
                        meeting_number=meeting_num,
                        similarity_score=round(similarity_score * 100, 2),
                        status=STATUS_TIDAK_DITEMUKAN,
                        notes=(
                            f"Tidak ditemukan padanan materi di RPS manapun. "
                            f"Skor tertinggi: {similarity_score * 100:.2f}%"
                        )
                    )
                    results.append(result)
                    logger.info(f"Pertemuan ke-{meeting_num}: TIDAK_DITEMUKAN (skor tertinggi={similarity_score * 100:.2f}%)")

        # Menyimpan hasil validasi ke database (menggantikan hasil lama)
        logger.info(f"Menyimpan {len(results)} hasil validasi ke database.")
        self._val_repo.save_batch(results)

        # Menghitung dan mencatat persentase kesesuaian
        percentage = self.calculate_compliance_percentage(results)
        logger.info(f"Validasi selesai. Persentase kesesuaian: {percentage:.2f}%")

        return results

    def _find_matching_rps(
        self,
        bap_text: str,
        rps_list: List[RPS],
        exclude_meeting: int
    ) -> Optional[Tuple[int, float]]:
        """
        Mencari padanan materi BAP di pertemuan RPS lain (deteksi pengacakan).
        """
        best_match: Optional[Tuple[int, float]] = None
        best_score: float = 0.0

        for rps in rps_list:
            if rps.meeting_number == exclude_meeting:
                continue

            rps_topic = rps.topic or ""
            rps_sub_topic = rps.sub_topic or ""
            match_result = self._matcher.match(bap_text, rps_topic, rps_sub_topic)

            if match_result["is_match"] and match_result["similarity_score"] > best_score:
                best_score = match_result["similarity_score"]
                best_match = (rps.meeting_number, best_score)

        return best_match

    def validate_sequence(
        self, rps_list: List[RPS], bap_list: List[BAP]
    ) -> List[Dict]:
        """
        Memvalidasi urutan materi antara RPS dan BAP.
        """
        results = []
        rps_map = {rps.meeting_number: rps for rps in rps_list}

        for bap in bap_list:
            rps = rps_map.get(bap.meeting_number)
            if rps is None:
                results.append({
                    "meeting_number": bap.meeting_number,
                    "status": STATUS_TIDAK_DITEMUKAN,
                    "notes": "Tidak ada data RPS untuk pertemuan ini"
                })
                continue

            rps_topic = rps.topic or ""
            rps_sub_topic = rps.sub_topic or ""
            bap_text = bap.cleaned_material or bap.material_taught or ""

            match_result = self._matcher.match(bap_text, rps_topic, rps_sub_topic)
            status = STATUS_SESUAI if match_result["is_match"] else STATUS_TIDAK_SESUAI

            results.append({
                "meeting_number": bap.meeting_number,
                "status": status,
                "similarity_score": match_result["similarity_score"],
                "notes": f"Skor: {match_result['similarity_score'] * 100:.2f}%"
            })

        return results

    def detect_shuffled_material(
        self, rps_list: List[RPS], bap_list: List[BAP]
    ) -> List[Dict]:
        """
        Mendeteksi materi BAP yang tertukar urutan dengan RPS.
        """
        shuffled = []

        for bap in bap_list:
            bap_text = bap.cleaned_material or ""
            if not bap_text:
                continue

            same_meeting_rps = None
            for rps in rps_list:
                if rps.meeting_number == bap.meeting_number:
                    same_meeting_rps = rps
                    break

            if same_meeting_rps:
                same_match = self._matcher.match(
                    bap_text, same_meeting_rps.topic or "", same_meeting_rps.sub_topic or ""
                )
                if same_match["is_match"]:
                    continue

            result = self._find_matching_rps(bap_text, rps_list, bap.meeting_number)
            if result:
                matched_meeting, matched_score = result
                shuffled.append({
                    "bap_meeting": bap.meeting_number,
                    "matched_rps_meeting": matched_meeting,
                    "similarity_score": matched_score,
                    "material": bap.material_taught,
                })

        return shuffled

    def detect_missing_material(
        self, rps_list: List[RPS], bap_list: List[BAP]
    ) -> List[Dict]:
        """
        Mendeteksi materi RPS yang belum diajarkan.
        """
        bap_meetings = {bap.meeting_number for bap in bap_list}
        missing = []

        for rps in rps_list:
            if rps.meeting_number not in bap_meetings:
                missing.append({
                    "meeting_number": rps.meeting_number,
                    "topic": rps.topic,
                    "sub_topic": rps.sub_topic or "",
                })

        return missing

    def calculate_compliance_percentage(
        self, results: List[ValidationResult]
    ) -> float:
        """
        Menghitung persentase kesesuaian perkuliahan.
        """
        if not results:
            return 0.0

        sesuai_count = sum(1 for r in results if r.status == STATUS_SESUAI)
        total = len(results)
        return round((sesuai_count / total) * 100, 2)

    def get_validation_results(self) -> List[ValidationResult]:
        """
        Mengambil hasil validasi aktif yang tersimpan di database.
        """
        return self._val_repo.get_all()

    def get_compliance_stats(self) -> Dict:
        """
        Mengambil statistik kesesuaian dari hasil validasi aktif.
        """
        return self._val_repo.get_compliance_stats()

    def get_rps_by_meeting(self, meeting_number: int) -> Optional[RPS]:
        """
        Mengambil data RPS aktif berdasarkan nomor pertemuan.
        """
        return self._rps_repo.get_by_meeting(meeting_number)

    def get_bap_by_meeting(self, meeting_number: int) -> Optional[BAP]:
        """
        Mengambil data BAP aktif berdasarkan nomor pertemuan.
        """
        return self._bap_repo.get_by_meeting(meeting_number)
