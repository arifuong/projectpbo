"""
Modul Routing BAP untuk Aplikasi Web.

Modul ini mendefinisikan rute HTTP untuk halaman realisasi BAP,
RESTful API CRUD untuk data pertemuan BAP.
"""

from flask import Blueprint
from app.controllers.bap_controller import BAPController

bap_bp = Blueprint("bap", __name__)
controller = BAPController()


@bap_bp.route("/bap", methods=["GET"])
def index():
    """Halaman Pengelolaan Realisasi BAP."""
    return controller.index()


@bap_bp.route("/api/bap/data", methods=["GET"])
def get_bap_data():
    """API endpoint untuk mengambil seluruh data BAP."""
    return controller.get_bap_data()


@bap_bp.route("/api/bap/add", methods=["POST"])
def add_bap_meeting():
    """API endpoint untuk menambah BAP baru manual."""
    return controller.add_bap_meeting()


@bap_bp.route("/api/bap/update", methods=["PUT"])
def update_bap_meeting():
    """API endpoint untuk mengubah data BAP."""
    return controller.update_bap_meeting()


@bap_bp.route("/api/bap/delete/<int:bap_id>", methods=["DELETE"])
def delete_bap_meeting(bap_id):
    """API endpoint untuk menghapus data BAP."""
    return controller.delete_bap_meeting(bap_id)
