"""
Modul FileUploadHandler untuk Sistem Validasi RPS-BAP.

Modul ini menangani validasi file PDF yang diunggah, penyimpanan file fisik
ke folder lokal 'uploads/', dan pencatatan riwayat unggahan ke database.

Sesuai PRD - Modul Upload PDF RPS.
"""

import os
import shutil
import time
from typing import Tuple, Optional, List, Dict, Any
from config.constants import ALLOWED_FILE_EXTENSIONS
from repositories.upload_repository import UploadRepository
from utils.logger import setup_logger
from utils.exceptions import FileValidationError, FileUploadError

# Inisialisasi logger untuk FileUploadHandler
logger = setup_logger(__name__)


class FileUploadHandler:
    """
    Class untuk menangani pengunggahan file dokumen RPS.

    Attributes:
        storage_path (str): Direktori absolut tempat menyimpan file upload.
        max_size_mb (int): Ukuran maksimum file dalam megabyte.
        _upload_repo (UploadRepository): Repository untuk mencatat riwayat ke database.
    """

    def __init__(
        self,
        upload_repo: UploadRepository,
        storage_path: str,
        max_size_mb: int = 10
    ) -> None:
        """
        Inisialisasi FileUploadHandler.

        Args:
            upload_repo: Repository riwayat upload.
            storage_path: Path folder lokal penyimpanan file.
            max_size_mb: Ukuran file maksimal dalam MB (default: 10).
        """
        self._upload_repo: UploadRepository = upload_repo
        self.storage_path: str = storage_path
        self.max_size_mb: int = max_size_mb
        
        # Pastikan folder penyimpanan ada
        os.makedirs(self.storage_path, exist_ok=True)
        logger.info(f"FileUploadHandler diaktifkan. Folder penyimpanan: {self.storage_path}")

    def validate_file(self, file_path: str) -> bool:
        """
        Memvalidasi ekstensi dan ukuran file sebelum diproses.

        Args:
            file_path: Path file yang akan divalidasi.

        Returns:
            bool: True jika valid.

        Raises:
            FileValidationError: Jika tipe atau ukuran file tidak sesuai.
        """
        if not file_path or not os.path.exists(file_path):
            raise FileValidationError("File tidak ditemukan atau path kosong.")

        # 1. Validasi Ekstensi
        _, ext = os.path.splitext(file_path)
        if ext.lower() not in ALLOWED_FILE_EXTENSIONS:
            logger.warning(f"File ditolak. Ekstensi tidak diizinkan: {ext}")
            raise FileValidationError(
                f"Tipe file tidak didukung. Hanya menerima file dengan format: {', '.join(ALLOWED_FILE_EXTENSIONS)}"
            )

        # 2. Validasi Ukuran File
        size_bytes = os.path.getsize(file_path)
        max_bytes = self.max_size_mb * 1024 * 1024
        if size_bytes > max_bytes:
            size_mb = size_bytes / (1024 * 1024)
            logger.warning(f"File ditolak. Ukuran file terlalu besar: {size_mb:.2f} MB")
            raise FileValidationError(
                f"Ukuran file ({size_mb:.2f} MB) melebihi batas maksimum pengunggahan ({self.max_size_mb} MB)."
            )

        return True

    def save_file(self, src_file_path: str) -> str:
        """
        Menyimpan file ke folder penyimpanan lokal dan mencatat riwayat unggahan.

        Args:
            src_file_path: Path file asal di komputer lokal.

        Returns:
            str: Path absolut file yang berhasil disimpan.

        Raises:
            FileUploadError: Jika gagal menyalin file atau gagal menulis database.
        """
        file_name = os.path.basename(src_file_path)
        size_kb = int(os.path.getsize(src_file_path) / 1024) if os.path.exists(src_file_path) else 0
        
        # Validasi terlebih dahulu
        try:
            self.validate_file(src_file_path)
        except FileValidationError as e:
            # Catat riwayat gagal ke database
            self.log_upload_history(file_name, "", size_kb, "FAILED", str(e))
            raise

        # Generate nama file unik agar tidak bertabrakan
        unique_file_name = f"rps_active_{int(time.time())}.pdf"
        dest_file_path = os.path.join(self.storage_path, unique_file_name)

        try:
            # Salin file ke folder uploads/
            logger.info(f"Menyalin file dari '{src_file_path}' ke '{dest_file_path}'")
            shutil.copy2(src_file_path, dest_file_path)
            
            # Catat riwayat sukses ke database (SUCCESS)
            # Catatan: Ini dipanggil untuk log upload awal (sebelum user menekan simpan)
            self.log_upload_history(file_name, dest_file_path, size_kb, "SUCCESS")
            return os.path.abspath(dest_file_path)
        except Exception as e:
            logger.exception(f"Gagal memindahkan file upload: {e}")
            self.log_upload_history(file_name, "", size_kb, "FAILED", str(e))
            raise FileUploadError(f"Gagal mengunggah file dokumen: {e}")

    def log_upload_history(
        self,
        file_name: str,
        file_path: str,
        file_size_kb: int,
        status: str,
        error_message: Optional[str] = None
    ) -> int:
        """
        Pencatat riwayat unggahan langsung ke repository database.
        """
        try:
            return self._upload_repo.create(
                file_name=file_name,
                file_path=file_path,
                file_size_kb=file_size_kb,
                upload_status=status,
                error_message=error_message
            )
        except Exception as e:
            logger.error(f"Gagal mencatat riwayat unggahan di database: {e}")
            return 0

    def get_upload_history(self) -> List[Dict[str, Any]]:
        """
        Mengambil seluruh riwayat unggahan sebagai audit log.
        """
        return self._upload_repo.get_all()
