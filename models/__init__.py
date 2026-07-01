"""
Paket model (entity) untuk Sistem Validasi RPS-BAP.

Paket ini mengekspor semua class model entitas agar mudah diimpor
oleh modul lain seperti repository dan service.
"""

from models.course import Course
from models.rps import RPS
from models.bap import BAP
from models.validation_result import ValidationResult
from models.report import Report

__all__ = [
    "Course",
    "RPS",
    "BAP",
    "ValidationResult",
    "Report"
]
