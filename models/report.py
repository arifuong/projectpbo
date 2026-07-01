"""
Modul Entity Report untuk Sistem Validasi RPS-BAP.

Modul ini mendefinisikan class Report yang merepresentasikan
data laporan kesesuaian perkuliahan secara agregat/ringkasan.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional


class Report:
    """
    Class yang merepresentasikan entitas Laporan Kesesuaian (Report).

    Attributes:
        compliance_percentage (float): Persentase kesesuaian (0.0 - 100.0).
        total_meetings (int): Jumlah pertemuan RPS yang terdaftar.
        matched_count (int): Jumlah pertemuan yang statusnya 'SESUAI'.
        mismatched_list (List[Dict[str, Any]]): Daftar detail pertemuan yang tidak sesuai.
        missing_list (List[Dict[str, Any]]): Daftar detail pertemuan/topik yang belum diajarkan.
        results (List[Dict[str, Any]]): Daftar hasil validasi per pertemuan.
        generated_at (datetime): Waktu laporan ini dibuat.
    """

    def __init__(
        self,
        compliance_percentage: float,
        total_meetings: int,
        matched_count: int,
        mismatched_list: List[Dict[str, Any]],
        missing_list: List[Dict[str, Any]],
        results: List[Dict[str, Any]],
        generated_at: Optional[datetime] = None
    ) -> None:
        """
        Inisialisasi objek Report.

        Args:
            compliance_percentage: Persentase kesesuaian.
            total_meetings: Total pertemuan.
            matched_count: Jumlah pertemuan sesuai.
            mismatched_list: Daftar pertemuan tidak sesuai.
            missing_list: Daftar materi belum diajarkan.
            results: Daftar seluruh baris hasil validasi.
            generated_at: Waktu pembuatan laporan.
        """
        self.compliance_percentage: float = float(compliance_percentage)
        self.total_meetings: int = total_meetings
        self.matched_count: int = matched_count
        self.mismatched_list: List[Dict[str, Any]] = mismatched_list
        self.missing_list: List[Dict[str, Any]] = missing_list
        self.results: List[Dict[str, Any]] = results
        self.generated_at: datetime = generated_at or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """
        Mengonversi objek Report menjadi dictionary.

        Returns:
            Dict[str, Any]: Representasi dictionary.
        """
        return {
            "compliance_percentage": self.compliance_percentage,
            "total_meetings": self.total_meetings,
            "matched_count": self.matched_count,
            "mismatched_list": self.mismatched_list,
            "missing_list": self.missing_list,
            "results": self.results,
            "generated_at": self.generated_at.strftime("%Y-%m-%d %H:%M:%S") if self.generated_at else None
        }

    def get_summary(self) -> str:
        """
        Mendapatkan ringkasan laporan dalam format teks.

        Returns:
            str: Ringkasan teks laporan.
        """
        return (
            f"Laporan Hasil Evaluasi Pembelajaran Aktif\n"
            f"Tingkat Kesesuaian: {self.compliance_percentage:.2f}%\n"
            f"Total Pertemuan RPS: {self.total_meetings}\n"
            f"Sesuai Rencana BAP: {self.matched_count}\n"
            f"Materi Tidak Sesuai: {len(self.mismatched_list)}\n"
            f"Materi Belum Diajarkan: {len(self.missing_list)}\n"
            f"Dibuat pada: {self.generated_at}"
        )

    def __repr__(self) -> str:
        """
        Representasi string dari objek Report.

        Returns:
            str: Representasi string.
        """
        return (
            f"Report(compliance_percentage={self.compliance_percentage:.2f}%)"
        )
