"""
Modul BaseController untuk Arsitektur MVC Flask.

Modul ini mendefinisikan class BaseController yang menyediakan helper utilitas
seperti akses service, parsing request data, dan standardisasi JSON response.
"""

from flask import current_app, jsonify, Response
from typing import Any, Dict


class BaseController:
    """
    Kelas dasar (Base Class) untuk seluruh Web Controller.

    Menerapkan prinsip Inheritance untuk berbagi utilitas context, logger,
    dan parsing request dari Flask.
    """

    def get_service(self, name: str) -> Any:
        """
        Mengambil instansi service dari configuration context Flask.

        Args:
            name: Nama service yang ingin diambil (contoh: "rps_manager").

        Returns:
            Any: Objek service terkait.
        """
        services = current_app.config.get("SERVICES", {})
        service = services.get(name)
        if not service:
            raise KeyError(f"Service '{name}' tidak terdaftar pada aplikasi.")
        return service

    def json_response(self, data: Any, status_code: int = 200) -> Response:
        """
        Membentuk respon JSON terstandar untuk API.

        Args:
            data: Data payload (dict, list, string, atau boolean).
            status_code: HTTP Status Code.

        Returns:
            Response: Respon Flask JSON.
        """
        # Bungkus data ke bentuk standar jika data adalah list, atau dict tanpa key success
        if isinstance(data, list) or (isinstance(data, dict) and "success" not in data):
            response_data = {
                "success": status_code < 400,
                "data": data
            }
        else:
            response_data = data

        return jsonify(response_data), status_code

    def json_error(self, message: str, status_code: int = 400, details: Dict[str, Any] = None) -> Response:
        """
        Membentuk respon JSON error terstandar.

        Args:
            message: Keterangan kesalahan.
            status_code: HTTP Status Code (>= 400).
            details: Informasi detail kesalahan tambahan (opsional).

        Returns:
            Response: Respon Flask JSON.
        """
        response_data = {
            "success": False,
            "message": message,
            "details": details or {}
        }
        return jsonify(response_data), status_code
