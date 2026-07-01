"""
Modul Entity BAP untuk Sistem Validasi RPS-BAP.

Modul ini mendefinisikan class BAP yang merepresentasikan
data Berita Acara Perkuliahan (BAP) per pertemuan dalam sistem.
"""

from datetime import date, datetime
from typing import Optional, Dict, Any, Union


class BAP:
    """
    Class yang merepresentasikan entitas Berita Acara Perkuliahan (BAP).

    Setiap instansi merepresentasikan catatan pelaksanaan perkuliahan untuk satu pertemuan.

    Attributes:
        course_id (int): ID mata kuliah yang berasosiasi dengan BAP ini.
        meeting_number (int): Nomor pertemuan (ke-).
        meeting_date (date): Tanggal pelaksanaan perkuliahan.
        material_taught (str): Materi yang benar-benar diajarkan.
        cleaned_material (Optional[str]): Materi yang telah dibersihkan.
        bap_id (Optional[int]): ID unik BAP (Primary Key di database).
        created_at (Optional[datetime]): Waktu data dibuat.
        updated_at (Optional[datetime]): Waktu data diperbarui.
    """

    def __init__(
        self,
        course_id: int,
        meeting_number: int,
        meeting_date: Union[date, str],
        material_taught: str,
        cleaned_material: Optional[str] = None,
        bap_id: Optional[int] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ) -> None:
        """
        Inisialisasi objek BAP.

        Args:
            course_id: ID mata kuliah terkait.
            meeting_number: Nomor pertemuan.
            meeting_date: Tanggal pertemuan. Bisa bertipe date atau string (YYYY-MM-DD).
            material_taught: Materi yang diajarkan.
            cleaned_material: Materi yang sudah dibersihkan/dinormalisasi.
            bap_id: ID unik BAP.
            created_at: Waktu data dibuat.
            updated_at: Waktu data diperbarui.
        """
        self.bap_id: Optional[int] = bap_id
        self.course_id: int = course_id
        self.meeting_number: int = meeting_number
        
        # Konversi string tanggal jika inputnya adalah string
        if isinstance(meeting_date, str):
            self.meeting_date: date = datetime.strptime(meeting_date, "%Y-%m-%d").date()
        else:
            self.meeting_date = meeting_date

        self.material_taught: str = material_taught
        self.cleaned_material: Optional[str] = cleaned_material
        self.created_at: Optional[datetime] = created_at
        self.updated_at: Optional[datetime] = updated_at

    def to_dict(self) -> Dict[str, Any]:
        """
        Mengonversi objek BAP menjadi dictionary.

        Returns:
            Dict[str, Any]: Representasi dictionary dari BAP.
        """
        return {
            "bap_id": self.bap_id,
            "course_id": self.course_id,
            "meeting_number": self.meeting_number,
            "meeting_date": self.meeting_date.strftime("%Y-%m-%d") if self.meeting_date else None,
            "material_taught": self.material_taught,
            "cleaned_material": self.cleaned_material,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BAP":
        """
        Membuat objek BAP dari dictionary.

        Args:
            data: Dictionary berisi data BAP.

        Returns:
            BAP: Objek BAP yang baru dibuat.
        """
        meeting_date_raw = data.get("meeting_date")
        meeting_date_val: Union[date, str]
        if isinstance(meeting_date_raw, str):
            meeting_date_val = meeting_date_raw
        elif isinstance(meeting_date_raw, date):
            meeting_date_val = meeting_date_raw
        else:
            meeting_date_val = date.today()

        return cls(
            bap_id=data.get("bap_id"),
            course_id=data.get("course_id", 0),
            meeting_number=data.get("meeting_number", 0),
            meeting_date=meeting_date_val,
            material_taught=data.get("material_taught", ""),
            cleaned_material=data.get("cleaned_material"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )

    def __repr__(self) -> str:
        """
        Representasi string dari objek BAP.

        Returns:
            str: Representasi string.
        """
        return (
            f"BAP(bap_id={self.bap_id}, course_id={self.course_id}, "
            f"meeting_number={self.meeting_number}, meeting_date='{self.meeting_date}')"
        )
