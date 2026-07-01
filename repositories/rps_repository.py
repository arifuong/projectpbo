"""
Modul Repository RPS untuk Sistem Validasi RPS-BAP.

Modul ini mengimplementasikan class RPSRepository yang bertanggung jawab
untuk melakukan operasi CRUD data RPS (Rencana Pembelajaran Semester) ke database MySQL.
"""

from typing import List, Optional, Tuple, Any
from models.rps import RPS
from database.connection import DatabaseConnection
from utils.logger import setup_logger

# Inisialisasi logger untuk repository rps
logger = setup_logger(__name__)


class RPSRepository:
    """
    Repository class untuk entitas RPS.

    Menangani interaksi langsung dengan tabel `rps` di database.
    Menyediakan method penyimpanan batch menggunakan transaksi SQL.
    """

    def __init__(self, db: DatabaseConnection) -> None:
        """
        Inisialisasi RPSRepository dengan dependency injection.

        Args:
            db: Instance koneksi database.
        """
        self._db: DatabaseConnection = db

    def create(self, rps: RPS) -> int:
        """
        Menyimpan data RPS baru.

        Args:
            rps: Objek RPS yang akan disimpan.

        Returns:
            int: ID record baru (rps_id).
        """
        query = """
        -- Menyimpan data RPS pertemuan baru
        INSERT INTO rps (meeting_number, topic, sub_topic, cleaned_topic, source_file)
        VALUES (%s, %s, %s, %s, %s);
        """
        params = (
            rps.meeting_number,
            rps.topic,
            rps.sub_topic,
            rps.cleaned_topic,
            rps.source_file
        )
        logger.info(f"Menyimpan RPS pertemuan ke-{rps.meeting_number}")
        last_id = self._db.execute_non_query(query, params)
        rps.rps_id = last_id
        return last_id

    def save_batch(self, rps_list: List[RPS]) -> bool:
        """
        Menyimpan daftar RPS secara massal (batch) di dalam satu transaksi database.

        Args:
            rps_list: List dari objek RPS.

        Returns:
            bool: True jika transaksi sukses dieksekusi.
        """
        if not rps_list:
            return True
            
        queries_with_params = []
        for rps in rps_list:
            query = """
            -- Menyimpan data RPS pertemuan baru (Batch)
            INSERT INTO rps (meeting_number, topic, sub_topic, cleaned_topic, source_file)
            VALUES (%s, %s, %s, %s, %s);
            """
            params = (
                rps.meeting_number,
                rps.topic,
                rps.sub_topic,
                rps.cleaned_topic,
                rps.source_file
            )
            queries_with_params.append((query, params))
            
        logger.info(f"Menjalankan batch transaksi untuk {len(rps_list)} rps record.")
        return self._db.execute_transaction(queries_with_params)

    def replace_all_rps(self, rps_list: List[RPS], filename: str, filepath: str, filesize_kb: int) -> bool:
        """
        Mengganti seluruh data RPS lama, BAP lama, dan hasil validasi lama dengan RPS baru,
        serta menyimpan riwayat unggah (audit trail) baru dalam satu transaksi database tunggal (ACID).

        Args:
            rps_list: List objek RPS baru.
            filename: Nama file baru.
            filepath: Path file baru.
            filesize_kb: Ukuran file baru.

        Returns:
            bool: True jika transaksi sukses dicommit.
        """
        queries_with_params = []

        # 1. Bersihkan seluruh data akademik aktif
        queries_with_params.append(("DELETE FROM validation_results;", ()))
        queries_with_params.append(("DELETE FROM bap;", ()))
        queries_with_params.append(("DELETE FROM rps;", ()))

        # 2. Sisipkan seluruh data RPS baru
        for rps in rps_list:
            insert_rps_query = """
            INSERT INTO rps (meeting_number, topic, sub_topic, cleaned_topic, source_file)
            VALUES (%s, %s, %s, %s, %s);
            """
            params_rps = (
                rps.meeting_number,
                rps.topic,
                rps.sub_topic,
                rps.cleaned_topic,
                rps.source_file
            )
            queries_with_params.append((insert_rps_query, params_rps))

        # 3. Catat riwayat audit upload baru dengan status = 'REPLACED'
        insert_history_query = """
        INSERT INTO upload_history (file_name, file_path, file_size_kb, upload_status)
        VALUES (%s, %s, %s, %s);
        """
        params_history = (
            filename,
            filepath,
            filesize_kb,
            "REPLACED"
        )
        queries_with_params.append((insert_history_query, params_history))

        logger.info(f"Menjalankan transaksi REPLACE ALL dengan {len(queries_with_params)} query.")
        return self._db.execute_transaction(queries_with_params)

    def get_by_id(self, rps_id: int) -> Optional[RPS]:
        """
        Mengambil satu data RPS berdasarkan ID.

        Args:
            rps_id: ID data RPS.

        Returns:
            Optional[RPS]: Objek RPS jika ditemukan, None jika tidak.
        """
        query = """
        -- Mengambil data RPS berdasarkan rps_id
        SELECT rps_id, meeting_number, topic, sub_topic, cleaned_topic, source_file, created_at, updated_at
        FROM rps
        WHERE rps_id = %s;
        """
        logger.debug(f"Mengambil RPS dengan ID: {rps_id}")
        results = self._db.execute_query(query, (rps_id,))
        if not results:
            return None
        return RPS.from_dict(results[0])

    def get_all(self) -> List[RPS]:
        """
        Mengambil seluruh data RPS, terurut berdasarkan nomor pertemuan.

        Returns:
            List[RPS]: Daftar objek RPS terurut.
        """
        query = """
        -- Mengambil seluruh data RPS terurut meeting_number
        SELECT rps_id, meeting_number, topic, sub_topic, cleaned_topic, source_file, created_at, updated_at
        FROM rps
        ORDER BY meeting_number ASC;
        """
        logger.debug("Mengambil seluruh data RPS")
        results = self._db.execute_query(query)
        return [RPS.from_dict(row) for row in results]

    def get_by_meeting(self, meeting_number: int) -> Optional[RPS]:
        """
        Mengambil data RPS berdasarkan nomor pertemuan.

        Args:
            meeting_number: Nomor pertemuan.

        Returns:
            Optional[RPS]: Objek RPS jika ditemukan, None jika tidak.
        """
        query = """
        -- Mengambil data RPS berdasarkan meeting_number
        SELECT rps_id, meeting_number, topic, sub_topic, cleaned_topic, source_file, created_at, updated_at
        FROM rps
        WHERE meeting_number = %s;
        """
        logger.debug(f"Mengambil RPS untuk pertemuan: {meeting_number}")
        results = self._db.execute_query(query, (meeting_number,))
        if not results:
            return None
        return RPS.from_dict(results[0])

    def update(self, rps: RPS) -> bool:
        """
        Memperbarui data RPS.

        Args:
            rps: Objek RPS berisi data baru.

        Returns:
            bool: True jika berhasil diperbarui.
        """
        if not rps.rps_id:
            logger.error("Gagal memperbarui rps: rps_id kosong.")
            return False
            
        query = """
        -- Memperbarui data RPS berdasarkan rps_id
        UPDATE rps
        SET meeting_number = %s, topic = %s, sub_topic = %s, cleaned_topic = %s, source_file = %s
        WHERE rps_id = %s;
        """
        params = (
            rps.meeting_number,
            rps.topic,
            rps.sub_topic,
            rps.cleaned_topic,
            rps.source_file,
            rps.rps_id
        )
        logger.info(f"Memperbarui rps ID: {rps.rps_id}")
        affected_rows = self._db.execute_non_query(query, params)
        return affected_rows > 0

    def delete(self, rps_id: int) -> bool:
        """
        Menghapus data RPS berdasarkan ID.

        Args:
            rps_id: ID RPS.

        Returns:
            bool: True jika berhasil dihapus.
        """
        query = """
        -- Menghapus data RPS berdasarkan rps_id
        DELETE FROM rps
        WHERE rps_id = %s;
        """
        logger.info(f"Menghapus rps dengan ID: {rps_id}")
        affected_rows = self._db.execute_non_query(query, (rps_id,))
        return affected_rows > 0

    def delete_all(self) -> bool:
        """
        Menghapus seluruh data RPS yang aktif.

        Returns:
            bool: True jika query berjalan sukses.
        """
        query = """
        -- Menghapus seluruh data RPS
        DELETE FROM rps;
        """
        logger.info("Menghapus seluruh data rps")
        self._db.execute_non_query(query)
        return True

    def count_all(self) -> int:
        """
        Mendapatkan total jumlah pertemuan RPS yang terdaftar.

        Returns:
            int: Jumlah pertemuan.
        """
        query = """
        -- Menghitung total pertemuan RPS
        SELECT COUNT(*) as total
        FROM rps;
        """
        results = self._db.execute_query(query)
        if not results:
            return 0
        return results[0]["total"]

    def exists(self, meeting_number: int) -> bool:
        """
        Memeriksa apakah data RPS untuk pertemuan tertentu sudah ada di database.

        Args:
            meeting_number: Nomor pertemuan.

        Returns:
            bool: True jika data ada.
        """
        query = """
        -- Memeriksa keberadaan rps berdasarkan meeting_number
        SELECT 1
        FROM rps
        WHERE meeting_number = %s;
        """
        results = self._db.execute_query(query, (meeting_number,))
        return len(results) > 0
