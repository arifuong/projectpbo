"""
Modul Entity RPS untuk Sistem Validasi RPS-BAP.

Modul ini mendefinisikan class RPS yang merepresentasikan
data Rencana Pembelajaran Semester (RPS) per pertemuan dalam sistem.
"""

from datetime import datetime
from typing import Optional, Dict, Any


class RPS:
    """
    Class yang merepresentasikan entitas Rencana Pembelajaran Semester (RPS).

    Setiap instansi merepresentasikan rencana pembelajaran untuk satu pertemuan tertentu.

    Attributes:
        meeting_number (int): Nomor pertemuan (ke-).
        topic (str): Pokok bahasan/topik utama pembelajaran.
        sub_topic (Optional[str]): Sub pokok bahasan/topik detail.
        cleaned_topic (Optional[str]): Topik yang telah dibersihkan.
        source_file (Optional[str]): Nama file PDF asal data RPS ini.
        rps_id (Optional[int]): ID unik RPS (Primary Key di database).
        created_at (Optional[datetime]): Waktu data dibuat.
        updated_at (Optional[datetime]): Waktu data diperbarui.
    """

    def __init__(
        self,
        meeting_number: int,
        topic: str,
        sub_topic: Optional[str] = None,
        cleaned_topic: Optional[str] = None,
        source_file: Optional[str] = None,
        rps_id: Optional[int] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ) -> None:
        """
        Inisialisasi objek RPS.

        Args:
            meeting_number: Nomor pertemuan.
            topic: Topik/pokok bahasan.
            sub_topic: Sub topik/sub pokok bahasan.
            cleaned_topic: Topik yang sudah dibersihkan/dinormalisasi.
            source_file: Nama file PDF sumber.
            rps_id: ID unik rps.
            created_at: Waktu data dibuat.
            updated_at: Waktu data diperbarui.
        """
        self.rps_id: Optional[int] = rps_id
        self.meeting_number: int = meeting_number
        self.topic: str = topic
        self.sub_topic: Optional[str] = sub_topic
        self.cleaned_topic: Optional[str] = cleaned_topic
        self.source_file: Optional[str] = source_file
        self.created_at: Optional[datetime] = created_at
        self.updated_at: Optional[datetime] = updated_at

    def to_dict(self) -> Dict[str, Any]:
        """
        Mengonversi objek RPS menjadi dictionary.

        Returns:
            Dict[str, Any]: Representasi dictionary dari RPS.
        """
        return {
            "rps_id": self.rps_id,
            "meeting_number": self.meeting_number,
            "topic": self.topic,
            "sub_topic": self.sub_topic,
            "cleaned_topic": self.cleaned_topic,
            "source_file": self.source_file,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RPS":
        """
        Membuat objek RPS dari dictionary.

        Args:
            data: Dictionary berisi data RPS.

        Returns:
            RPS: Objek RPS yang baru dibuat.
        """
        return cls(
            rps_id=data.get("rps_id"),
            meeting_number=data.get("meeting_number", 0),
            topic=data.get("topic", ""),
            sub_topic=data.get("sub_topic"),
            cleaned_topic=data.get("cleaned_topic"),
            source_file=data.get("source_file"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )

    def __repr__(self) -> str:
        """
        Representasi string dari objek RPS.

        Returns:
            str: Representasi string.
        """
        return (
            f"RPS(rps_id={self.rps_id}, "
            f"meeting_number={self.meeting_number}, topic='{self.topic}')"
        )
