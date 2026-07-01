"""
Modul RPSController untuk Mengelola CRUD Silabus Rencana RPS melalui Web.

Modul ini mendefinisikan class RPSController yang menangani render halaman kelola RPS,
serta RESTful API untuk menambah, mengedit, dan menghapus pertemuan RPS.

Sesuai PRD Single User & Single Course.
"""

from flask import render_template, request, Response
from app.controllers.base_controller import BaseController
from services.rps_manager import RPSManager
from models.rps import RPS
from utils.logger import setup_logger

# Inisialisasi logger untuk controller
logger = setup_logger(__name__)


class RPSController(BaseController):
    """
    Controller untuk halaman pengelolaan Data RPS.
    """

    def index(self) -> str:
        """
        Menampilkan halaman utama pengelolaan data RPS.

        Returns:
            str: HTML template hasil render.
        """
        return render_template("rps.html", active_page="rps")

    def get_rps_data(self) -> Response:
        """
        Mengambil daftar seluruh pertemuan RPS terdaftar dalam format JSON.

        Returns:
            Response: JSON API response.
        """
        rps_manager: RPSManager = self.get_service("rps_manager")
        
        try:
            rps_list = rps_manager.get_all_rps()
            data = [item.to_dict() for item in rps_list]
            return self.json_response(data)
        except Exception as e:
            logger.exception("Gagal mengambil data RPS.")
            return self.json_error(str(e))

    def add_rps_meeting(self) -> Response:
        """
        Menambahkan baris pertemuan rencana pembelajaran baru secara manual.
        """
        payload = request.get_json()
        if not payload:
            return self.json_error("Payload data kosong.")

        try:
            meeting_number = int(payload.get("meeting_number"))
            topic = payload.get("topic", "").strip()
            sub_topic = payload.get("sub_topic", "").strip()
            
            if not topic:
                return self.json_error("Topik Utama wajib diisi.")

            rps_manager: RPSManager = self.get_service("rps_manager")
            
            new_rps = RPS(
                meeting_number=meeting_number,
                topic=topic,
                sub_topic=sub_topic,
                source_file="Input Manual"
            )
            
            # Simpan satu pertemuan manual menggunakan add_single_rps
            last_id = rps_manager.add_single_rps(new_rps)
            if last_id > 0:
                logger.info(f"Berhasil menambahkan pertemuan RPS manual ke-{meeting_number}.")
                return self.json_response({"message": f"Berhasil menambahkan Pertemuan {meeting_number}."})
            else:
                return self.json_error("Gagal menambahkan pertemuan ke database.")
                
        except Exception as e:
            logger.exception("Gagal menambahkan pertemuan RPS.")
            return self.json_error(f"Gagal menambahkan data: {e}")

    def update_rps_meeting(self) -> Response:
        """
        Mengubah data topik / sub-topik pertemuan rencana RPS secara manual.
        """
        payload = request.get_json()
        if not payload:
            return self.json_error("Payload data kosong.")

        try:
            rps_id = int(payload.get("rps_id"))
            topic = payload.get("topic", "").strip()
            sub_topic = payload.get("sub_topic", "").strip()

            if not topic:
                return self.json_error("Topik Utama wajib diisi.")

            rps_manager: RPSManager = self.get_service("rps_manager")
            
            # Update rps
            success = rps_manager.update_rps(rps_id, {"topic": topic, "sub_topic": sub_topic})
            if success:
                logger.info(f"Berhasil merapikan topik RPS ID {rps_id}.")
                return self.json_response({"message": "Pertemuan berhasil diperbarui."})
            else:
                return self.json_error("Gagal memperbarui data di database.")
        except Exception as e:
            logger.exception("Gagal mengubah data RPS.")
            return self.json_error(str(e))

    def delete_rps_meeting(self, rps_id: int) -> Response:
        """
        Menghapus data baris pertemuan RPS secara permanen.
        """
        rps_manager: RPSManager = self.get_service("rps_manager")
        
        try:
            success = rps_manager.delete_rps(rps_id)
            if success:
                logger.info(f"Berhasil menghapus record RPS ID {rps_id}.")
                return self.json_response({"message": "Pertemuan RPS berhasil dihapus."})
            else:
                return self.json_error("Gagal menghapus pertemuan di database.")
        except Exception as e:
            logger.exception("Gagal menghapus data RPS.")
            return self.json_error(str(e))
