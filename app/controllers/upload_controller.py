"""
Modul UploadController untuk Mengelola Proses Unggah dan Ekstraksi RPS.

Modul ini mendefinisikan class UploadController yang menangani upload dokumen PDF,
ekstraksi pokok bahasan, pratinjau data, dan penyimpanan permanen data RPS.

Sesuai PRD Single User & Single Course.
"""

import os
from flask import render_template, request, Response
from werkzeug.utils import secure_filename

from app.controllers.base_controller import BaseController
from services.file_upload_handler import FileUploadHandler
from services.pdf_extraction_service import PDFExtractionService
from services.rps_manager import RPSManager
from models.rps import RPS
from utils.logger import setup_logger

# Inisialisasi logger untuk controller
logger = setup_logger(__name__)


class UploadController(BaseController):
    """
    Controller untuk modul Unggah PDF RPS.
    """

    def index(self) -> str:
        """
        Menampilkan halaman form upload PDF RPS.

        Returns:
            str: HTML template hasil render.
        """
        return render_template("upload.html", active_page="upload")

    def upload_file(self) -> Response:
        """
        Menerima file PDF dari client, memproses penyimpanan, dan mengekstrak materi.

        Returns:
            Response: JSON API response berisi data pokok bahasan terekstrak.
        """
        logger.info("Menerima request upload file RPS PDF...")
        
        if "file" not in request.files:
            return self.json_error("Tidak ada file yang diunggah.")
            
        file = request.files["file"]
        if file.filename == "":
            return self.json_error("Nama file kosong.")

        upload_handler: FileUploadHandler = self.get_service("upload_handler")
        temp_dir = os.path.join(upload_handler.storage_path, "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        filename = secure_filename(file.filename)
        temp_file_path = os.path.join(temp_dir, filename)
        
        try:
            file.save(temp_file_path)
            
            # Simpan secara fisik dan catat log awal (SUCCESS)
            saved_path = upload_handler.save_file(temp_file_path)
            
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

            # Ekstrak data materi
            extraction_service: PDFExtractionService = self.get_service("extraction_service")
            extracted_data = extraction_service.extract_pokok_bahasan(saved_path)
            
            logger.info(f"Ekstraksi RPS PDF sukses. Berhasil mengekstrak {len(extracted_data)} pertemuan.")
            
            return self.json_response({
                "source_file": os.path.basename(saved_path),
                "items": extracted_data
            })
            
        except Exception as e:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            logger.exception("Gagal memproses unggah & ekstraksi file PDF.")
            return self.json_error(str(e))

    def save_extracted_rps(self) -> Response:
        """
        Menyimpan data hasil ekstraksi yang disetujui pengguna ke database secara permanen.
        """
        logger.info("Menerima request penyimpanan permanen hasil ekstraksi RPS...")
        payload = request.get_json()
        if not payload:
            return self.json_error("Payload data kosong.")

        source_file = payload.get("source_file", "Upload Web")
        items = payload.get("items", [])

        if not items:
            return self.json_error("Tidak ada item data pertemuan untuk disimpan.")

        upload_handler: FileUploadHandler = self.get_service("upload_handler")
        filepath = os.path.join(upload_handler.storage_path, source_file)
        filesize_kb = int(os.path.getsize(filepath) / 1024) if os.path.exists(filepath) else 0

        # Konversi data ke objek model RPS
        rps_list = []
        for i in items:
            rps_list.append(
                RPS(
                    meeting_number=int(i["meeting_number"]),
                    topic=i["topic"],
                    sub_topic=i.get("sub_topic", ""),
                    source_file=source_file
                )
            )

        try:
            # Simpan massal transaksional terpadu (mengganti data lama)
            rps_manager: RPSManager = self.get_service("rps_manager")
            success = rps_manager.save_rps(rps_list, source_file, filepath, filesize_kb)
            if success:
                logger.info(f"Berhasil menyimpan {len(rps_list)} rps record ke basis data.")
                return self.json_response({"message": f"Berhasil menyimpan {len(rps_list)} pertemuan RPS."})
            else:
                return self.json_error("Gagal menulis data ke database.")
        except Exception as e:
            logger.exception("Gagal menyimpan data RPS.")
            return self.json_error(f"Kesalahan penyimpanan database: {e}")
