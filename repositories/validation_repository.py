"""
Modul Repository Validation untuk Sistem Validasi RPS-BAP.

Modul ini mengimplementasikan class ValidationRepository yang bertanggung jawab
untuk melakukan operasi penyimpanan dan pembacaan hasil validasi kesesuaian ke database MySQL.
"""

from typing import List, Optional, Dict, Any, Tuple
from models.validation_result import ValidationResult
from database.connection import DatabaseConnection
from utils.logger import setup_logger

# Inisialisasi logger untuk repository validation
logger = setup_logger(__name__)


class ValidationRepository:
    """
    Repository class untuk entitas ValidationResult.

    Menangani interaksi langsung dengan tabel `validation_results` di database.
    Menerapkan pembersihan batch dan penyimpanan baru dalam satu transaksi.
    """

    def __init__(self, db: DatabaseConnection) -> None:
        """
        Inisialisasi ValidationRepository dengan dependency injection.

        Args:
            db: Instance koneksi database.
        """
        self._db: DatabaseConnection = db

    def save(self, result: ValidationResult) -> int:
        """
        Menyimpan data hasil validasi ke database.

        Args:
            result: Objek ValidationResult yang akan disimpan.

        Returns:
            int: ID record baru (validation_id).
        """
        query = """
        -- Menyimpan data hasil validasi baru
        INSERT INTO validation_results (rps_id, bap_id, meeting_number, similarity_score, status, notes)
        VALUES (%s, %s, %s, %s, %s, %s);
        """
        params = (
            result.rps_id,
            result.bap_id,
            result.meeting_number,
            result.similarity_score,
            result.status,
            result.notes
        )
        logger.info(f"Menyimpan hasil validasi pertemuan ke-{result.meeting_number} status={result.status}")
        last_id = self._db.execute_non_query(query, params)
        result.validation_id = last_id
        return last_id

    def save_batch(self, results: List[ValidationResult]) -> bool:
        """
        Menyimpan sekumpulan data hasil validasi di dalam satu transaksi database.

        Menghapus semua data validasi yang lama terlebih dahulu untuk mencegah duplikasi.

        Args:
            results: List dari objek ValidationResult.

        Returns:
            bool: True jika transaksi sukses dieksekusi.
        """
        queries_with_params: List[Tuple[str, Optional[Tuple[Any, ...]]]] = []
        
        # 1. Hapus data validasi yang lama
        delete_query = """
        -- Menghapus hasil validasi lama sebelum menyimpan yang baru
        DELETE FROM validation_results;
        """
        queries_with_params.append((delete_query, ()))
        
        # 2. Masukkan data validasi baru
        for result in results:
            insert_query = """
            -- Menyimpan data hasil validasi baru (Batch)
            INSERT INTO validation_results (rps_id, bap_id, meeting_number, similarity_score, status, notes)
            VALUES (%s, %s, %s, %s, %s, %s);
            """
            params = (
                result.rps_id,
                result.bap_id,
                result.meeting_number,
                result.similarity_score,
                result.status,
                result.notes
            )
            queries_with_params.append((insert_query, params))
            
        logger.info(f"Menjalankan batch transaksi validasi sebanyak {len(results)} item.")
        return self._db.execute_transaction(queries_with_params)

    def get_all(self) -> List[ValidationResult]:
        """
        Mengambil hasil validasi terurut berdasarkan nomor pertemuan.

        Returns:
            List[ValidationResult]: Daftar objek hasil validasi terurut.
        """
        query = """
        -- Mengambil seluruh hasil validasi terurut meeting_number
        SELECT validation_id, rps_id, bap_id, meeting_number, similarity_score, status, notes, validated_at
        FROM validation_results
        ORDER BY meeting_number ASC;
        """
        logger.debug("Mengambil seluruh data hasil validasi")
        results = self._db.execute_query(query)
        return [ValidationResult.from_dict(row) for row in results]

    def get_by_id(self, validation_id: int) -> Optional[ValidationResult]:
        """
        Mengambil satu data hasil validasi berdasarkan ID.

        Args:
            validation_id: ID hasil validasi.

        Returns:
            Optional[ValidationResult]: Objek ValidationResult jika ditemukan, None jika tidak.
        """
        query = """
        -- Mengambil data hasil validasi berdasarkan validation_id
        SELECT validation_id, rps_id, bap_id, meeting_number, similarity_score, status, notes, validated_at
        FROM validation_results
        WHERE validation_id = %s;
        """
        logger.debug(f"Mengambil hasil validasi ID: {validation_id}")
        results = self._db.execute_query(query, (validation_id,))
        if not results:
            return None
        return ValidationResult.from_dict(results[0])

    def delete_all(self) -> bool:
        """
        Menghapus seluruh hasil validasi.

        Returns:
            bool: True jika berhasil.
        """
        query = """
        -- Menghapus seluruh data hasil validasi
        DELETE FROM validation_results;
        """
        logger.info("Menghapus seluruh hasil validasi")
        self._db.execute_non_query(query)
        return True

    def get_compliance_stats(self) -> Dict[str, Any]:
        """
        Mendapatkan statistik kesesuaian pembelajaran.

        Returns:
            Dict[str, Any]: Dictionary dengan key:
                "total": total pertemuan.
                "sesuai_count": jumlah pertemuan berstatus SESUAI.
                "percentage": persentase kesesuaian (float).
        """
        query_total = """
        -- Menghitung total data hasil validasi
        SELECT COUNT(*) as total
        FROM validation_results;
        """
        query_sesuai = """
        -- Menghitung jumlah pertemuan berstatus SESUAI
        SELECT COUNT(*) as sesuai_count
        FROM validation_results
        WHERE status = 'SESUAI';
        """
        
        res_total = self._db.execute_query(query_total)
        res_sesuai = self._db.execute_query(query_sesuai)
        
        total = res_total[0]["total"] if res_total else 0
        sesuai_count = res_sesuai[0]["sesuai_count"] if res_sesuai else 0
        
        percentage = 0.0
        if total > 0:
            percentage = (sesuai_count / total) * 100
            
        return {
            "total": total,
            "sesuai_count": sesuai_count,
            "percentage": round(percentage, 2)
        }
