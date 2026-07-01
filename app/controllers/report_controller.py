"""
Modul ReportController untuk Mengelola Ekspor Laporan via Web.

Modul ini mendefinisikan class ReportController yang melayani visualisasi ringkasan kepatuhan,
audit log upload_history, serta trigger unduhan laporan PDF dan Excel.

Sesuai PRD Single User & Single Course.
"""

import os
from flask import render_template, send_file, Response, current_app
from app.controllers.base_controller import BaseController
from services.report_generator import ReportGenerator
from services.file_upload_handler import FileUploadHandler
from utils.logger import setup_logger

# Inisialisasi logger
logger = setup_logger(__name__)


class ReportController(BaseController):
    """
    Controller untuk halaman laporan dan ekspor.
    """

    def index(self) -> str:
        """
        Menampilkan halaman laporan evaluasi pembelajaran dan riwayat audit.

        Returns:
            str: HTML template hasil render.
        """
        return render_template("report.html", active_page="report")

    def get_report_data(self) -> Response:
        """
        Mengambil ringkasan kepatuhan serta daftar detail penyimpangan (mismatches).

        Returns:
            Response: JSON API response.
        """
        report_gen: ReportGenerator = self.get_service("report_generator")
        
        try:
            report = report_gen.generate_report()
            return self.json_response(report.to_dict())
        except Exception as e:
            logger.exception("Gagal menyusun data ringkasan laporan.")
            return self.json_error(str(e))

    def export_pdf(self) -> Response:
        """
        Menyusun dan mengunduh berkas laporan PDF formal.

        Returns:
            Response: File download stream.
        """
        logger.info("Menerima request unduhan Laporan PDF...")
        report_gen: ReportGenerator = self.get_service("report_generator")
        
        try:
            app_settings = current_app.config["APP_SETTINGS"]
            pdf_path = os.path.join(app_settings.export_dir, "Laporan_Kesesuaian_RPS_BAP.pdf")
            
            report = report_gen.generate_report()
            file_path = report_gen.export_to_pdf(report, pdf_path)
            
            if not os.path.exists(file_path):
                return "File laporan gagal disusun.", 500
                
            logger.info(f"Ekspor PDF sukses. Mengirim berkas: {file_path}")
            return send_file(
                file_path,
                as_attachment=True,
                download_name="Laporan_Kesesuaian_RPS_BAP.pdf",
                mimetype="application/pdf"
            )
        except Exception as e:
            logger.exception("Gagal melakukan ekspor PDF.")
            return f"Gagal mengekspor PDF: {e}", 500

    def export_excel(self) -> Response:
        """
        Menyusun dan mengunduh berkas spreadsheet Excel multi-sheet.

        Returns:
            Response: File download stream.
        """
        logger.info("Menerima request unduhan Laporan Excel...")
        report_gen: ReportGenerator = self.get_service("report_generator")
        
        try:
            app_settings = current_app.config["APP_SETTINGS"]
            excel_path = os.path.join(app_settings.export_dir, "Laporan_Kesesuaian_RPS_BAP.xlsx")
            
            report = report_gen.generate_report()
            file_path = report_gen.export_to_excel(report, excel_path)
            
            if not os.path.exists(file_path):
                return "File spreadsheet gagal disusun.", 500

            logger.info(f"Ekspor Excel sukses. Mengirim berkas: {file_path}")
            return send_file(
                file_path,
                as_attachment=True,
                download_name="Laporan_Kesesuaian_RPS_BAP.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            logger.exception("Gagal melakukan ekspor Excel.")
            return f"Gagal mengekspor Excel: {e}", 500

    def get_upload_history(self) -> Response:
        """
        Mengambil riwayat log audit pengunggahan file PDF RPS (upload_history).

        Returns:
            Response: JSON API response.
        """
        upload_handler: FileUploadHandler = self.get_service("upload_handler")
        
        try:
            history = upload_handler.get_upload_history()
            return self.json_response(history)
        except Exception as e:
            logger.exception("Gagal mengambil log riwayat unggahan.")
            return self.json_error(str(e))
