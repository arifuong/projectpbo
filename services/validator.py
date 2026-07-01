"""
Modul Validator untuk Sistem Validasi RPS-BAP.

Modul ini merupakan inti logika bisnis sistem yang menggabungkan
hasil Keyword Matching dengan pengecekan urutan pertemuan,
kemudian menetapkan status akhir tiap pertemuan.

Sesuai PRD Section 4.8 - Modul Validation Engine.

Business Rules yang diimplementasikan:
    - BR-06: Status SESUAI (skor >= threshold DAN urutan cocok)
    - BR-07: Status TIDAK_SESUAI (skor >= threshold, urutan beda)
    - BR-08: Status TIDAK_DITEMUKAN (skor < threshold di semua RPS)
    - BR-09: Persentase = (Sesuai / Total RPS) x 100%
    - BR-10: Materi belum diajarkan = RPS tanpa padanan BAP
    - BR-13: Validasi hanya jika RPS dan minimal 1 BAP tersedia

Design Pattern:
    - Composition: Validator has-a KeywordMatcher
    - Dependency Injection: Semua dependency diinjeksi
    - Strategy Pattern: KeywordMatcher sebagai strategi matching
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

    Class ini mengorkestrasi seluruh proses validasi mulai dari
    pengambilan data, pencocokan kata kunci, validasi urutan,
    hingga penentuan status akhir setiap pertemuan.

    Composition:
        Validator has-a KeywordMatcher (strategi pencocokan)
        Validator has-a RPSRepository (data RPS)
        Validator has-a BAPRepository (data BAP)
        Validator has-a ValidationRepository (hasil validasi)

    Attributes:
        _matcher (KeywordMatcher): Objek untuk pencocokan kata kunci.
        _rps_repo (RPSRepository): Repository data RPS.
        _bap_repo (BAPRepository): Repository data BAP.
        _validation_repo (ValidationRepository): Repository hasil validasi.
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
        # Composition: Validator memiliki KeywordMatcher
        self._matcher: KeywordMatcher = matcher
        self._rps_repo: RPSRepository = rps_repo
        self._bap_repo: BAPRepository = bap_repo
        self._validation_repo: ValidationRepository = validation_repo
        logger.info("Validator berhasil diinisialisasi")

    def run_validation(self, course_id: int) -> List[ValidationResult]:
        """
        Menjalankan pipeline utama proses validasi untuk satu mata kuliah.

        Alur validasi:
        1. Mengambil data RPS dan BAP dari database
        2. Memvalidasi ketersediaan data (BR-13)
        3. Melakukan keyword matching per pertemuan
        4. Menentukan status validasi per pertemuan
        5. Mendeteksi materi yang diacak (shuffled)
        6. Mendeteksi materi yang belum diajarkan
        7. Menyimpan hasil validasi ke database

        Args:
            course_id: ID mata kuliah yang akan divalidasi.

        Returns:
            List[ValidationResult]: Daftar hasil validasi per pertemuan.

        Raises:
            ValidationError: Jika data RPS atau BAP belum tersedia (BR-13).
        """
        logger.info(f"Memulai proses validasi untuk course_id={course_id}")

        # Mengambil data RPS dan BAP dari database
        rps_list = self._rps_repo.get_by_course(course_id)
        bap_list = self._bap_repo.get_by_course(course_id)

        # Memvalidasi ketersediaan data (BR-13)
        if not rps_list:
            logger.error(f"Data RPS belum tersedia untuk course_id={course_id}")
            raise ValidationError(
                MSG_VALIDATION_NO_DATA,
                details={"course_id": course_id, "reason": "RPS kosong"}
            )

        if not bap_list:
            logger.error(f"Data BAP belum tersedia untuk course_id={course_id}")
            raise ValidationError(
                MSG_VALIDATION_NO_DATA,
                details={"course_id": course_id, "reason": "BAP kosong"}
            )

        # Membangun mapping data untuk akses cepat
        rps_map = {rps.meeting_number: rps for rps in rps_list}
        bap_map = {bap.meeting_number: bap for bap in bap_list}

        # Menjalankan proses validasi per pertemuan
        results = []

        for rps in rps_list:
            meeting_num = rps.meeting_number
            bap = bap_map.get(meeting_num)

            if bap is None:
                # Materi belum diajarkan (BR-10)
                result = ValidationResult(
                    course_id=course_id,
                    rps_id=rps.rps_id,
                    bap_id=None,
                    meeting_number=meeting_num,
                    similarity_score=0.0,
                    status=STATUS_PENDING,
                    notes="Materi belum diajarkan (BAP belum diinput)"
                )
                results.append(result)
                logger.info(
                    f"Pertemuan ke-{meeting_num}: PENDING (BAP belum ada)"
                )
                continue

            # Melakukan keyword matching antara BAP dan RPS
            rps_text = rps.cleaned_topic or ""
            bap_text = bap.cleaned_material or ""

            # Mencocokkan materi BAP dengan RPS pertemuan yang sama
            match_result = self._matcher.match(bap_text, rps_text)
            similarity_score = match_result["similarity_score"]
            is_matched = match_result["is_match"]

            if is_matched:
                # Skor >= threshold DAN pertemuan sama => SESUAI (BR-06)
                result = ValidationResult(
                    course_id=course_id,
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
                logger.info(
                    f"Pertemuan ke-{meeting_num}: SESUAI "
                    f"(skor={similarity_score * 100:.2f}%)"
                )
            else:
                # Skor < threshold, cek apakah cocok dengan pertemuan lain
                shuffled_result = self._find_matching_rps(
                    bap_text, rps_list, meeting_num
                )

                if shuffled_result is not None:
                    # Cocok dengan pertemuan lain => TIDAK_SESUAI (BR-07)
                    matched_meeting, matched_score = shuffled_result
                    result = ValidationResult(
                        course_id=course_id,
                        rps_id=rps.rps_id,
                        bap_id=bap.bap_id,
                        meeting_number=meeting_num,
                        similarity_score=round(matched_score * 100, 2),
                        status=STATUS_TIDAK_SESUAI,
                        notes=(
                            f"Materi diacak. Cocok dengan "
                            f"pertemuan ke-{matched_meeting} "
                            f"(skor={matched_score * 100:.2f}%)"
                        )
                    )
                    results.append(result)
                    logger.info(
                        f"Pertemuan ke-{meeting_num}: TIDAK_SESUAI "
                        f"(cocok dengan pertemuan ke-{matched_meeting})"
                    )
                else:
                    # Tidak cocok dengan RPS manapun => TIDAK_DITEMUKAN (BR-08)
                    result = ValidationResult(
                        course_id=course_id,
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
                    logger.info(
                        f"Pertemuan ke-{meeting_num}: TIDAK_DITEMUKAN "
                        f"(skor tertinggi={similarity_score * 100:.2f}%)"
                    )

        # Menyimpan hasil validasi ke database (menggantikan hasil lama)
        logger.info(
            f"Menyimpan {len(results)} hasil validasi "
            f"untuk course_id={course_id}"
        )
        self._validation_repo.save_batch(results, course_id)

        # Menghitung dan mencatat persentase kesesuaian
        percentage = self.calculate_compliance_percentage(results)
        logger.info(
            f"Validasi selesai. Persentase kesesuaian: {percentage:.2f}%"
        )

        return results

    def _find_matching_rps(
        self,
        bap_text: str,
        rps_list: List[RPS],
        exclude_meeting: int
    ) -> Optional[Tuple[int, float]]:
        """
        Mencari padanan materi BAP di pertemuan RPS lain.

        Digunakan untuk mendeteksi materi yang diacak/tertukar urutan.
        Sesuai PRD BR-07: Status TIDAK_SESUAI jika materi cocok
        dengan pertemuan lain.

        Args:
            bap_text: Teks materi BAP yang sudah dibersihkan.
            rps_list: Daftar seluruh data RPS mata kuliah.
            exclude_meeting: Nomor pertemuan yang dikecualikan
                            (pertemuan yang sedang divalidasi).

        Returns:
            Optional[Tuple[int, float]]: Tuple (meeting_number, score)
            jika ditemukan padanan, None jika tidak.
        """
        best_match: Optional[Tuple[int, float]] = None
        best_score: float = 0.0

        for rps in rps_list:
            # Melewati pertemuan yang sedang divalidasi
            if rps.meeting_number == exclude_meeting:
                continue

            rps_text = rps.cleaned_topic or ""
            if not rps_text:
                continue

            # Menghitung skor kemiripan
            match_result = self._matcher.match(bap_text, rps_text)

            if match_result["is_match"] and match_result["similarity_score"] > best_score:
                best_score = match_result["similarity_score"]
                best_match = (rps.meeting_number, best_score)

        return best_match

    def validate_sequence(
        self, rps_list: List[RPS], bap_list: List[BAP]
    ) -> List[Dict]:
        """
        Memvalidasi urutan materi antara RPS dan BAP.

        Membandingkan urutan pertemuan BAP dengan urutan yang
        direncanakan pada RPS untuk mendeteksi pengacakan.

        Args:
            rps_list: Daftar data RPS terurut.
            bap_list: Daftar data BAP terurut.

        Returns:
            List[Dict]: Daftar hasil validasi urutan per pertemuan.
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

            rps_text = rps.cleaned_topic or ""
            bap_text = bap.cleaned_material or ""

            match_result = self._matcher.match(bap_text, rps_text)
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

        Sesuai PRD Section 4.8: Deteksi materi yang diajarkan
        namun tertukar urutan.

        Args:
            rps_list: Daftar data RPS.
            bap_list: Daftar data BAP.

        Returns:
            List[Dict]: Daftar materi yang terdeteksi diacak,
                       berisi meeting_number BAP dan nomor
                       pertemuan RPS yang cocok.
        """
        shuffled = []

        for bap in bap_list:
            bap_text = bap.cleaned_material or ""
            if not bap_text:
                continue

            # Cek apakah cocok dengan pertemuan yang sama
            same_meeting_rps = None
            for rps in rps_list:
                if rps.meeting_number == bap.meeting_number:
                    same_meeting_rps = rps
                    break

            if same_meeting_rps:
                same_match = self._matcher.match(
                    bap_text, same_meeting_rps.cleaned_topic or ""
                )
                if same_match["is_match"]:
                    # Sudah sesuai, bukan shuffled
                    continue

            # Cari padanan di pertemuan lain
            result = self._find_matching_rps(
                bap_text, rps_list, bap.meeting_number
            )
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

        Sesuai PRD BR-10: Materi RPS yang tidak memiliki
        padanan BAP dikategorikan sebagai materi belum diajarkan.

        Args:
            rps_list: Daftar data RPS.
            bap_list: Daftar data BAP.

        Returns:
            List[Dict]: Daftar materi RPS yang belum memiliki BAP.
        """
        # Mengumpulkan nomor pertemuan yang sudah ada di BAP
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
        Menghitung persentase kesesuaian mata kuliah.

        Sesuai PRD BR-09:
        Persentase = (Jumlah Pertemuan Berstatus Sesuai / Total Pertemuan RPS) x 100%

        Args:
            results: Daftar hasil validasi per pertemuan.

        Returns:
            float: Persentase kesesuaian (0.00 - 100.00).
        """
        if not results:
            return 0.0

        # Menghitung jumlah pertemuan berstatus SESUAI
        sesuai_count = sum(
            1 for r in results if r.status == STATUS_SESUAI
        )
        total = len(results)

        # Menghitung persentase sesuai rumus BR-09
        percentage = (sesuai_count / total) * 100
        return round(percentage, 2)

    def get_validation_results(
        self, course_id: int
    ) -> List[ValidationResult]:
        """
        Mengambil hasil validasi yang tersimpan di database.

        Args:
            course_id: ID mata kuliah.

        Returns:
            List[ValidationResult]: Daftar hasil validasi.
        """
        return self._validation_repo.get_by_course(course_id)
