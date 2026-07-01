"""
Modul Entity ValidationResult untuk Sistem Validasi RPS-BAP.

Modul ini mendefinisikan class ValidationResult yang merepresentasikan
data hasil validasi kesesuaian antara RPS dan BAP per pertemuan.
"""

from datetime import datetime
from typing import Optional, Dict, Any


class ValidationResult:
    """
    Class yang merepresentasikan entitas Hasil Validasi (ValidationResult).

    Attributes:
        meeting_number (int): Nomor pertemuan ke-.
        similarity_score (float): Skor kemiripan antara RPS dan BAP (0.0 - 100.0).
        status (str): Status hasil validasi ('SESUAI', 'TIDAK_SESUAI', 'TIDAK_DITEMUKAN', 'PENDING').
        rps_id (Optional[int]): ID entitas RPS yang dicocokkan.
        bap_id (Optional[int]): ID entitas BAP yang dicocokkan.
        notes (Optional[str]): Catatan hasil validasi.
        validation_id (Optional[int]): ID unik hasil validasi (Primary Key).
        validated_at (Optional[datetime]): Waktu proses validasi dijalankan.
    """

    def __init__(
        self,
        meeting_number: int,
        similarity_score: float,
        status: str,
        rps_id: Optional[int] = None,
        bap_id: Optional[int] = None,
        notes: Optional[str] = None,
        validation_id: Optional[int] = None,
        validated_at: Optional[datetime] = None
    ) -> None:
        """
        Inisialisasi objek ValidationResult.

        Args:
            meeting_number: Nomor pertemuan.
            similarity_score: Skor kemiripan (0.0 - 100.0).
            status: Status hasil validasi.
            rps_id: ID rps.
            bap_id: ID bap.
            notes: Catatan validasi.
            validation_id: ID unik hasil validasi.
            validated_at: Tanggal validasi.
        """
        self.validation_id: Optional[int] = validation_id
        self.rps_id: Optional[int] = rps_id
        self.bap_id: Optional[int] = bap_id
        self.meeting_number: int = meeting_number
        self.similarity_score: float = float(similarity_score)
        self.status: str = status
        self.notes: Optional[str] = notes
        self.validated_at: Optional[datetime] = validated_at

    def to_dict(self) -> Dict[str, Any]:
        """
        Mengonversi objek ValidationResult menjadi dictionary.

        Returns:
            Dict[str, Any]: Representasi dictionary.
        """
        return {
            "validation_id": self.validation_id,
            "rps_id": self.rps_id,
            "bap_id": self.bap_id,
            "meeting_number": self.meeting_number,
            "similarity_score": self.similarity_score,
            "status": self.status,
            "notes": self.notes,
            "validated_at": self.validated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationResult":
        """
        Membuat objek ValidationResult dari dictionary.

        Args:
            data: Dictionary berisi data hasil validasi.

        Returns:
            ValidationResult: Objek ValidationResult yang baru dibuat.
        """
        return cls(
            validation_id=data.get("validation_id"),
            rps_id=data.get("rps_id"),
            bap_id=data.get("bap_id"),
            meeting_number=data.get("meeting_number", 0),
            similarity_score=data.get("similarity_score", 0.0),
            status=data.get("status", "PENDING"),
            notes=data.get("notes"),
            validated_at=data.get("validated_at")
        )

    def __repr__(self) -> str:
        """
        Representasi string dari objek ValidationResult.

        Returns:
            str: Representasi string.
        """
        return (
            f"ValidationResult(validation_id={self.validation_id}, "
            f"meeting_number={self.meeting_number}, status='{self.status}', "
            f"similarity_score={self.similarity_score})"
        )
