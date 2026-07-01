"""
Modul konfigurasi database untuk Sistem Validasi RPS-BAP.

Modul ini menyediakan class DatabaseConfig yang menyimpan
parameter koneksi ke database MySQL secara terpusat.
Menerapkan prinsip Encapsulation untuk melindungi credential
database (password) dari akses langsung.

Sesuai PRD Section 4.10 - Modul Database Management:
Mengelola parameter koneksi basis data secara terpusat.
"""

import os


class DatabaseConfig:
    """
    Class untuk menyimpan konfigurasi koneksi database MySQL.

    Menerapkan encapsulation dengan menyembunyikan atribut
    password menggunakan name mangling (double underscore).
    Nilai konfigurasi dapat diambil dari environment variable
    atau menggunakan nilai default untuk pengembangan lokal.

    Attributes:
        host (str): Alamat host database server.
        port (int): Nomor port database server.
        user (str): Username untuk koneksi database.
        database (str): Nama database yang digunakan.

    Encapsulation:
        __password (str): Password database, hanya dapat diakses
                         melalui method get_password().

    Contoh penggunaan:
        >>> config = DatabaseConfig()
        >>> params = config.get_connection_params()
        >>> print(config)
        DatabaseConfig(host='localhost', port=3306, ...)
    """

    def __init__(
        self,
        host: str = None,
        port: int = None,
        user: str = None,
        password: str = None,
        database: str = None
    ):
        """
        Inisialisasi konfigurasi database.

        Jika parameter tidak diberikan, nilai diambil dari
        environment variable atau menggunakan nilai default
        untuk keperluan pengembangan lokal (Laragon).

        Args:
            host: Alamat host database (default: localhost).
            port: Nomor port database (default: 3306).
            user: Username database (default: root).
            password: Password database (default: string kosong).
            database: Nama database (default: validasi_rps_bap).
        """
        # Mengambil konfigurasi dari parameter atau environment variable
        self.host: str = host or os.getenv("DB_HOST", "localhost")
        self.port: int = port or int(os.getenv("DB_PORT", "3306"))
        self.user: str = user or os.getenv("DB_USER", "root")
        self.database: str = database or os.getenv(
            "DB_NAME", "validasi_rps_bap"
        )

        # Encapsulation: password disimpan sebagai atribut privat
        # sesuai PRD Section 12.2 tentang Encapsulation
        self.__password: str = password or os.getenv("DB_PASSWORD", "")

    def get_password(self) -> str:
        """
        Mengambil password database melalui method accessor.

        Menerapkan encapsulation agar password tidak dapat
        diakses langsung melalui atribut publik. Ini sesuai
        dengan PRD Section 12.2 yang mengharuskan atribut
        sensitif disembunyikan.

        Returns:
            str: Password database yang tersimpan.
        """
        return self.__password

    def get_connection_params(self) -> dict:
        """
        Mengambil seluruh parameter koneksi dalam bentuk dictionary.

        Dictionary yang dihasilkan dapat langsung digunakan sebagai
        keyword arguments untuk mysql.connector.connect().

        Returns:
            dict: Parameter koneksi database dengan key:
                  host, port, user, password, database.
        """
        return {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.__password,
            "database": self.database,
        }

    def __repr__(self) -> str:
        """
        Representasi string dari konfigurasi database.

        Password tidak ditampilkan untuk keamanan.

        Returns:
            str: Representasi string tanpa password.
        """
        return (
            f"DatabaseConfig(host='{self.host}', port={self.port}, "
            f"user='{self.user}', database='{self.database}')"
        )
