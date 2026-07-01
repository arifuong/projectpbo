"""
Modul BAPController untuk Mengelola CRUD Realisasi BAP melalui Web.

Modul ini mendefinisikan class BAPController yang menangani render halaman kelola BAP,
serta API RESTful untuk menambah, mengedit, dan menghapus realisasi BAP.
Menjamin aturan validasi BR-02 dievaluasi.

Sesuai PRD Single User & Single Course.
"""

from datetime import datetime
from flask import render_template, request, Response
from app.controllers.base_controller import BaseController
from services.bap_manager import BAPManager
from models.bap import BAP
from utils.exceptions import DuplicateMeetingError, MeetingNumberExceededError
from utils.logger import setup_logger

# Inisialisasi logger untuk controller
logger = setup_logger(__name__)


class BAPController(BaseController):
    """
    Controller untuk halaman pengelolaan Data BAP.
    """

    def index(self) -> str:
        """
        Menampilkan halaman utama pengelolaan data realisasi BAP.

        Returns:
            str: HTML template hasil render.
        """
        return render_template("bap.html", active_page="bap")

    def get_bap_data(self) -> Response:
        """
        Mengambil daftar seluruh pertemuan realisasi BAP terdaftar dalam format JSON.

        Returns:
            Response: JSON API response.
        """
        bap_manager: BAPManager = self.get_service("bap_manager")
        
        try:
            bap_list = bap_manager.get_all_bap()
            data = [item.to_dict() for item in bap_list]
            
            # Hitung progress pengisian BAP terhadap rencana RPS
            total_rps_count = bap_manager.get_total_rps_meetings()
            
            return self.json_response({
                "items": data,
                "total_rps": total_rps_count,
                "total_bap": len(data)
            })
        except Exception as e:
            logger.exception("Gagal mengambil data BAP.")
            return self.json_error(str(e))

    def add_bap_meeting(self) -> Response:
        """
        Menambahkan baris realisasi tatap muka kuliah BAP baru secara manual.
        """
        payload = request.get_json()
        if not payload:
            return self.json_error("Payload data kosong.")

        try:
            meeting_number = int(payload.get("meeting_number"))
            meeting_date_str = payload.get("meeting_date", "").strip()
            material_taught = payload.get("material_taught", "").strip()

            if not meeting_date_str:
                return self.json_error("Tanggal tatap muka wajib diisi.")
            if not material_taught:
                return self.json_error("Materi tatap muka wajib diisi.")

            try:
                meeting_date = datetime.strptime(meeting_date_str, "%Y-%m-%d").date()
            except ValueError:
                return self.json_error("Format tanggal salah. Gunakan YYYY-MM-DD.")

            bap_manager: BAPManager = self.get_service("bap_manager")

            new_bap = BAP(
                meeting_number=meeting_number,
                meeting_date=meeting_date,
                material_taught=material_taught
            )

            # Panggil BAPManager untuk menyimpan dan mengevaluasi validasi BR-02
            success = bap_manager.add_bap(new_bap)
            if success:
                logger.info(f"Berhasil menambahkan BAP pertemuan ke-{meeting_number}.")
                return self.json_response({"message": f"Realisasi Pertemuan {meeting_number} berhasil disimpan."})
            else:
                return self.json_error("Gagal menyimpan data BAP ke database.")

        except (DuplicateMeetingError, MeetingNumberExceededError) as ve:
            logger.warning(f"Validasi BAP gagal: {ve.message}")
            return self.json_error(ve.message)
        except Exception as e:
            logger.exception("Gagal menambahkan realisasi BAP.")
            return self.json_error(f"Gagal menambahkan data: {e}")

    def update_bap_meeting(self) -> Response:
        """
        Mengubah data realisasi BAP secara manual.
        """
        payload = request.get_json()
        if not payload:
            return self.json_error("Payload data kosong.")

        try:
            bap_id = int(payload.get("bap_id"))
            meeting_date_str = payload.get("meeting_date", "").strip()
            material_taught = payload.get("material_taught", "").strip()

            if not meeting_date_str or not material_taught:
                return self.json_error("Seluruh field wajib diisi.")

            try:
                meeting_date = datetime.strptime(meeting_date_str, "%Y-%m-%d").date()
            except ValueError:
                return self.json_error("Format tanggal salah. Gunakan YYYY-MM-DD.")

            bap_manager: BAPManager = self.get_service("bap_manager")
            
            success = bap_manager.update_bap(
                bap_id,
                {
                    "meeting_date": meeting_date,
                    "material_taught": material_taught,
                }
            )
            if success:
                logger.info(f"Berhasil merapikan BAP ID {bap_id}.")
                return self.json_response({"message": "Pertemuan BAP diperbarui."})
            else:
                return self.json_error("Gagal memperbarui data di database.")
        except Exception as e:
            logger.exception("Gagal mengubah data BAP.")
            return self.json_error(str(e))

    def delete_bap_meeting(self, bap_id: int) -> Response:
        """
        Menghapus data realisasi BAP secara permanen.
        """
        bap_manager: BAPManager = self.get_service("bap_manager")
        
        try:
            success = bap_manager.delete_bap(bap_id)
            if success:
                logger.info(f"Berhasil menghapus record BAP ID {bap_id}.")
                return self.json_response({"message": "Realisasi BAP berhasil dihapus."})
            else:
                return self.json_error("Gagal menghapus data BAP di database.")
        except Exception as e:
            logger.exception("Gagal menghapus data BAP.")
            return self.json_error(str(e))
