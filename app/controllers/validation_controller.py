"""
Modul ValidationController untuk Mengelola Proses Audit Evaluasi Kepatuhan.

Modul ini mendefinisikan class ValidationController yang memicu mesin validasi (Validator)
dan mengembalikan rincian data hasil validasi ber-warna.

Sesuai PRD Single User & Single Course.
"""

from flask import render_template, Response
from app.controllers.base_controller import BaseController
from services.validator import Validator
from utils.logger import setup_logger

# Inisialisasi logger
logger = setup_logger(__name__)


class ValidationController(BaseController):
    """
    Controller untuk halaman pemeriksaan Validasi.
    """

    def index(self) -> str:
        """
        Menampilkan halaman pemeriksaan validasi kesesuaian.

        Returns:
            str: HTML template hasil render.
        """
        return render_template("validation.html", active_page="validation")

    def run_validation(self) -> Response:
        """
        Menjalankan audit kesesuaian RPS-BAP secara asinkron (AJAX).

        Returns:
            Response: JSON API response berisi status dan ringkasan kepatuhan.
        """
        logger.info("Menjalankan validasi kesesuaian RPS-BAP...")
        validator: Validator = self.get_service("validator")
        
        try:
            # Jalankan validator engine
            results = validator.run_validation()
            
            # Hitung ringkasan statistik
            stats = validator.get_compliance_stats()
            logger.info(f"Validasi selesai. Persentase kepatuhan: {stats.get('percentage', 0)}%.")
            
            return self.json_response({
                "message": "Validasi kesesuaian RPS-BAP berhasil diselesaikan.",
                "stats": stats
            })
        except Exception as e:
            logger.exception("Gagal menjalankan mesin validasi.")
            return self.json_error(f"Gagal memvalidasi: {e}")

    def get_validation_data(self) -> Response:
        """
        Mengambil riwayat data hasil pemeriksaan validasi aktif dari database.

        Returns:
            Response: JSON API response.
        """
        validator: Validator = self.get_service("validator")
        
        try:
            results = validator.get_validation_results()
            
            # Gabungkan dengan deskripsi topik dan materi diajarkan untuk keperluan view
            data = []
            for r in results:
                rps_item = validator.get_rps_by_meeting(r.meeting_number)
                bap_item = validator.get_bap_by_meeting(r.meeting_number)
                
                data.append({
                    "validation_id": r.validation_id,
                    "meeting_number": r.meeting_number,
                    "similarity_score": round(r.similarity_score, 1) if r.similarity_score else 0.0,
                    "status": r.status,
                    "notes": r.notes or "-",
                    "topic": rps_item.topic if rps_item else "(Tidak ada rencana)",
                    "material_taught": bap_item.material_taught if bap_item else "(Belum diajarkan)"
                })
                
            return self.json_response(data)
        except Exception as e:
            logger.exception("Gagal mengambil data validasi.")
            return self.json_error(str(e))
