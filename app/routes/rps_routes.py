"""
Modul Routing RPS untuk Aplikasi Web.

Modul ini mendefinisikan rute HTTP untuk halaman rencana silabus,
RESTful API CRUD untuk data pertemuan RPS.
"""

from flask import Blueprint
from app.controllers.rps_controller import RPSController

rps_bp = Blueprint("rps", __name__)
controller = RPSController()


@rps_bp.route("/rps", methods=["GET"])
def index():
    """Halaman Pengelolaan Rencana RPS."""
    return controller.index()


@rps_bp.route("/api/rps/data", methods=["GET"])
def get_rps_data():
    """API endpoint untuk mengambil seluruh data RPS."""
    return controller.get_rps_data()


@rps_bp.route("/api/rps/add", methods=["POST"])
def add_rps_meeting():
    """API endpoint untuk menambah pertemuan RPS baru secara manual."""
    return controller.add_rps_meeting()


@rps_bp.route("/api/rps/update", methods=["PUT"])
def update_rps_meeting():
    """API endpoint untuk mengubah data topik/sub-topik RPS."""
    return controller.update_rps_meeting()


@rps_bp.route("/api/rps/delete/<int:rps_id>", methods=["DELETE"])
def delete_rps_meeting(rps_id):
    """API endpoint untuk menghapus pertemuan RPS."""
    return controller.delete_rps_meeting(rps_id)
