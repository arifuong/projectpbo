"""
Modul Koneksi Database untuk Sistem Validasi RPS-BAP.

Modul ini mendefinisikan class DatabaseConnection yang bertindak sebagai
lapisan abstraksi database. Class ini mengelola connection pool,
transaksi (commit/rollback), query terparameterisasi, serta
penanganan exception database secara terpusat.
"""

import os
from typing import Optional, List, Dict, Any, Tuple
import mysql.connector
from mysql.connector import pooling, Error

from config.config import DatabaseConfig
from utils.logger import setup_logger
from utils.exceptions import (
    DatabaseConnectionError,
    DatabaseQueryError,
    DatabaseTransactionError
)

# Inisialisasi logger untuk database
logger = setup_logger(__name__)


class DatabaseConnection:
    """
    Class untuk mengelola koneksi dan transaksi ke database MySQL.

    Menerapkan Connection Pool menggunakan MySQLConnectionPool agar
    efisien dalam pemakaian resource koneksi. Menyediakan method untuk
    mengeksekusi query, menjalankan transaksi dengan commit dan rollback,
    dan menginisialisasi database dari skema SQL.

    Mendukung protokol Context Manager (with statement) untuk mempermudah
    pemakaian koneksi database yang aman.

    Attributes:
        _config (DatabaseConfig): Konfigurasi database yang diinjeksi.
        _pool (Optional[pooling.MySQLConnectionPool]): Pool koneksi MySQL.
        _connection (Optional[mysql.connector.connection.MySQLConnection]): Koneksi aktif saat ini untuk context manager.
    """

    def __init__(self, config: DatabaseConfig) -> None:
        """
        Inisialisasi DatabaseConnection.

        Args:
            config: Objek DatabaseConfig yang berisi kredensial dan detail koneksi.
        """
        self._config: DatabaseConfig = config
        self._pool: Optional[pooling.MySQLConnectionPool] = None
        self._connection: Optional[mysql.connector.connection.MySQLConnection] = None
        
        logger.info("DatabaseConnection diinisialisasi.")
        self._initialize_pool()

    def _initialize_pool(self) -> None:
        """
        Menginisialisasi connection pool MySQL.

        Raises:
            DatabaseConnectionError: Jika inisialisasi pool gagal.
        """
        try:
            logger.info("Membuat MySQL Connection Pool...")
            db_params = self._config.get_connection_params()
            
            # Buat parameter untuk pooling
            pool_params = {
    "pool_name": "rps_bap_pool",
    "pool_size": 5,
    **db_params
}
            
            self._pool = pooling.MySQLConnectionPool(**pool_params)
            logger.info("MySQL Connection Pool berhasil dibuat.")
        except Error as e:
            logger.error(f"Gagal menginisialisasi connection pool: {e}")
            raise DatabaseConnectionError(
                f"Gagal menginisialisasi database pool: {e}",
                details={"error_code": e.errno if hasattr(e, 'errno') else None}
            )

    def get_connection(self) -> mysql.connector.connection.MySQLConnection:
        """
        Mengambil satu koneksi dari pool.

        Returns:
            mysql.connector.connection.MySQLConnection: Koneksi database aktif.

        Raises:
            DatabaseConnectionError: Jika gagal mendapatkan koneksi dari pool.
        """
        try:
            if not self._pool:
                self._initialize_pool()
            
            conn = self._pool.get_connection()
            if not conn.is_connected():
                conn.reconnect(attempts=3, delay=1)
                
            return conn
        except Error as e:
            logger.error(f"Gagal mendapatkan koneksi dari pool: {e}")
            raise DatabaseConnectionError(
                f"Gagal terhubung ke database server: {e}",
                details={"error_code": e.errno if hasattr(e, 'errno') else None}
            )

    def ensure_connection(self) -> None:
        """
        Memastikan koneksi database dapat dibangun.

        Berguna untuk memeriksa status server database sebelum aplikasi dijalankan.
        """
        try:
            conn = self.get_connection()
            conn.close()
            logger.info("Koneksi ke database terverifikasi aktif.")
        except Exception as e:
            logger.exception("Verifikasi koneksi database gagal.")
            raise DatabaseConnectionError(f"Verifikasi koneksi database gagal: {e}")

    def execute_query(self, query: str, params: Optional[Tuple[Any, ...]] = None) -> List[Dict[str, Any]]:
        """
        Mengeksekusi query SQL non-transaksional (SELECT, dsb) secara aman.

        Menerapkan Parameterized Query untuk mencegah SQL Injection.

        Args:
            query: Query SQL yang akan dieksekusi.
            params: Parameter tuple untuk query SQL (opsional).

        Returns:
            List[Dict[str, Any]]: Hasil record set dalam bentuk list of dictionary.
        """
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            # Gunakan dictionary=True agar hasil query berupa dict (sesuai spesifikasi)
            cursor = conn.cursor(dictionary=True)
            
            logger.debug(f"Mengeksekusi query: {query} dengan params: {params}")
            cursor.execute(query, params or ())
            
            # Jika query menghasilkan data (SELECT)
            if cursor.description:
                result = cursor.fetchall()
            else:
                conn.commit()
                result = []
                
            return result
        except Error as e:
            logger.error(f"Kesalahan eksekusi query database: {e}. Query: {query}")
            raise DatabaseQueryError(
                f"Kesalahan query database: {e}",
                details={"query": query, "params": str(params)}
            )
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def execute_non_query(self, query: str, params: Optional[Tuple[Any, ...]] = None) -> int:
        """
        Mengeksekusi query manipulasi data (INSERT, UPDATE, DELETE) dan mengembalikan lastrowid atau rowcount.

        Args:
            query: Query SQL.
            params: Parameter query.

        Returns:
            int: ID baris terakhir yang dimasukkan (lastrowid) jika INSERT, atau jumlah baris terpengaruh.
        """
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            logger.debug(f"Mengeksekusi non-query: {query} dengan params: {params}")
            cursor.execute(query, params or ())
            conn.commit()
            
            if query.strip().upper().startswith("INSERT"):
                return cursor.lastrowid or 0
            return cursor.rowcount
        except Error as e:
            logger.error(f"Kesalahan eksekusi non-query: {e}. Query: {query}")
            raise DatabaseQueryError(
                f"Kesalahan query database: {e}",
                details={"query": query, "params": str(params)}
            )
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def execute_transaction(self, queries: List[Tuple[str, Optional[Tuple[Any, ...]]]]) -> bool:
        """
        Mengeksekusi serangkaian query di dalam satu transaksi (Commit dan Rollback otomatis jika gagal).

        Sesuai dengan PRD & standard coding:
        Menerapkan transaksi database terpadu.

        Args:
            queries: List berisi tuple (Query SQL string, parameter tuple).

        Returns:
            bool: True jika transaksi sukses dieksekusi dan dicommit.

        Raises:
            DatabaseTransactionError: Jika terjadi kegagalan dalam transaksi dan dilakukan rollback.
        """
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            # Matikan autocommit untuk memulai transaksi
            conn.autocommit = False
            cursor = conn.cursor()
            
            logger.info(f"Memulai transaksi database dengan {len(queries)} query.")
            for query, params in queries:
                logger.debug(f"Transaksi - Mengeksekusi: {query} dengan params: {params}")
                cursor.execute(query, params or ())
                
            conn.commit()
            logger.info("Transaksi database berhasil dicommit.")
            return True
        except Error as e:
            if conn:
                try:
                    conn.rollback()
                    logger.warning("Transaksi gagal. Rollback berhasil dilakukan.")
                except Error as rollback_err:
                    logger.error(f"Gagal melakukan rollback: {rollback_err}")
            
            logger.error(f"Kegagalan transaksi database: {e}")
            raise DatabaseTransactionError(
                f"Kegagalan transaksi database: {e}",
                details={"error_info": str(e)}
            )
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def initialize_database(self, schema_file_path: str) -> None:
        """
        Membaca file skema SQL dan menginisialisasi database (membuat tabel-tabel).

        Args:
            schema_file_path: Path absolut file skema SQL.

        Raises:
            DatabaseQueryError: Jika eksekusi skema gagal.
        """
        if not os.path.exists(schema_file_path):
            raise FileNotFoundError(f"File skema SQL tidak ditemukan: {schema_file_path}")
            
        logger.info(f"Menginisialisasi database dengan file skema: {schema_file_path}")
        
        # Baca isi file skema SQL
        with open(schema_file_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
            
        # Pisahkan perintah SQL berdasarkan semicolon ";"
        # Perlu di-parse dengan hati-hati agar tidak memecah isi string atau komentar
        commands = []
        current_command = []
        in_string = False
        string_char = None
        
        lines = schema_sql.split('\n')
        for line in lines:
            # Lewati baris kosong atau baris komentar murni
            stripped = line.strip()
            if not stripped or stripped.startswith('--'):
                continue
                
            # Tambahkan baris ke perintah aktif
            current_command.append(line)
            
            # Jika ada semicolon di akhir, anggap perintah selesai (parsing sederhana)
            if stripped.endswith(';'):
                commands.append('\n'.join(current_command))
                current_command = []
                
        # Jalankan satu per satu
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            for cmd in commands:
                cmd_stripped = cmd.strip()
                if cmd_stripped:
                    logger.debug(f"Menginisialisasi - Eksekusi: {cmd_stripped[:100]}...")
                    cursor.execute(cmd_stripped)
            
            conn.commit()
            logger.info("Database berhasil diinisialisasi dengan tabel skema.")
        except Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Gagal menginisialisasi database: {e}")
            raise DatabaseQueryError(f"Gagal menginisialisasi database dari skema: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    # Context Manager support
    def __enter__(self) -> "DatabaseConnection":
        """
        Memulai blok context manager.

        Returns:
            DatabaseConnection: instance DatabaseConnection aktif.
        """
        self._connection = self.get_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Mengakhiri blok context manager dan menutup koneksi aktif secara aman.
        """
        if self._connection:
            try:
                if exc_type is not None:
                    # Jika ada error dalam blok with, rollback jika dalam mode transaksi
                    self._connection.rollback()
                    logger.warning("Context manager mendeteksi error. Rollback transaksi dilakukan.")
                else:
                    self._connection.commit()
            except Error as e:
                logger.error(f"Error saat menutup context manager koneksi: {e}")
            finally:
                self._connection.close()
                self._connection = None
