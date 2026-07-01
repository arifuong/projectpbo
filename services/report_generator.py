"""
Modul Report Generator untuk Sistem Validasi RPS-BAP.

Modul ini menyusun dan mengekspor laporan hasil validasi
kesesuaian RPS-BAP dalam format PDF and Excel.

Sesuai PRD - Modul Report Generator.
"""

import os
from typing import List, Optional, Dict, Any
from datetime import datetime

from models.report import Report
from models.validation_result import ValidationResult
from repositories.rps_repository import RPSRepository
from repositories.bap_repository import BAPRepository
from repositories.validation_repository import ValidationRepository
from utils.logger import setup_logger
from utils.exceptions import ReportGenerationError
from config.constants import (
    STATUS_SESUAI,
    STATUS_TIDAK_SESUAI,
    STATUS_TIDAK_DITEMUKAN,
    DATETIME_FORMAT,
    MSG_REPORT_FAILED,
)

# Inisialisasi logger untuk modul ini
logger = setup_logger(__name__)


class ReportGenerator:
    """
    Class untuk membuat dan mengekspor laporan validasi.
    """

    def __init__(
        self,
        rps_repo: RPSRepository,
        bap_repo: BAPRepository,
        validation_repo: ValidationRepository
    ):
        """
        Inisialisasi ReportGenerator dengan dependency injection.

        Args:
            rps_repo: Repository untuk akses data RPS.
            bap_repo: Repository untuk akses data BAP.
            validation_repo: Repository untuk akses hasil validasi.
        """
        self._rps_repo: RPSRepository = rps_repo
        self._bap_repo: BAPRepository = bap_repo
        self._validation_repo: ValidationRepository = validation_repo
        logger.info("ReportGenerator berhasil diinisialisasi")

    def generate_report(self) -> Report:
        """
        Membuat laporan kesesuaian pembelajaran aktif.

        Returns:
            Report: Objek laporan yang berisi seluruh hasil analisis.

        Raises:
            ReportGenerationError: Jika data validasi belum tersedia.
        """
        logger.info("Membuat laporan kesesuaian pembelajaran")

        # Mengambil hasil validasi dari database
        validation_results = self._validation_repo.get_all()
        if not validation_results:
            logger.warning("Belum ada hasil validasi aktif")
            raise ReportGenerationError(
                MSG_REPORT_FAILED,
                details={
                    "reason": "Hasil validasi belum tersedia. "
                              "Jalankan validasi terlebih dahulu."
                }
            )

        # Mengambil data RPS dan BAP untuk konteks laporan
        rps_list = self._rps_repo.get_all()
        bap_list = self._bap_repo.get_all()

        # Menghitung statistik kesesuaian (BR-09)
        total_meetings = len(rps_list)
        sesuai_count = sum(
            1 for r in validation_results if r.status == STATUS_SESUAI
        )
        compliance_percentage = (
            (sesuai_count / total_meetings) * 100
            if total_meetings > 0 else 0.0
        )

        # Menyusun daftar materi tidak sesuai (AC-14)
        mismatched_list = self._build_mismatched_list(
            validation_results, rps_list, bap_list
        )

        # Menyusun daftar materi belum diajarkan (AC-15)
        bap_meetings = {bap.meeting_number for bap in bap_list}
        missing_list = [
            {
                "meeting_number": rps.meeting_number,
                "topic": rps.topic,
                "sub_topic": rps.sub_topic or "",
            }
            for rps in rps_list
            if rps.meeting_number not in bap_meetings
        ]

        # Menyusun objek Report
        report = Report(
            compliance_percentage=round(compliance_percentage, 2),
            total_meetings=total_meetings,
            matched_count=sesuai_count,
            mismatched_list=mismatched_list,
            missing_list=missing_list,
            results=[r.to_dict() for r in validation_results],
            generated_at=datetime.now()
        )

        logger.info(
            f"Laporan berhasil dibuat. Kesesuaian: {compliance_percentage:.2f}%"
        )
        return report

    def _build_mismatched_list(
        self,
        validation_results: List[ValidationResult],
        rps_list: list,
        bap_list: list
    ) -> List[Dict[str, Any]]:
        """
        Menyusun daftar materi yang tidak sesuai atau tidak ditemukan.
        """
        rps_map = {rps.meeting_number: rps for rps in rps_list}
        bap_map = {bap.meeting_number: bap for bap in bap_list}

        mismatched = []
        for result in validation_results:
            if result.status in (STATUS_TIDAK_SESUAI, STATUS_TIDAK_DITEMUKAN):
                rps = rps_map.get(result.meeting_number)
                bap = bap_map.get(result.meeting_number)

                mismatched.append({
                    "meeting_number": result.meeting_number,
                    "status": result.status,
                    "similarity_score": result.similarity_score,
                    "rps_topic": rps.topic if rps else "-",
                    "bap_material": bap.material_taught if bap else "-",
                    "notes": result.notes or "",
                })

        return mismatched

    def export_to_pdf(self, report: Report, output_path: str) -> str:
        """
        Mengekspor laporan ke format PDF menggunakan reportlab.
        """
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.units import cm
            from reportlab.platypus import (
                SimpleDocTemplate, Table, TableStyle,
                Paragraph, Spacer
            )
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

            logger.info(f"Mengekspor laporan ke PDF: {output_path}")

            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=2 * cm,
                leftMargin=2 * cm,
                topMargin=2 * cm,
                bottomMargin=2 * cm
            )

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=12,
                alignment=1
            )
            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Heading2'],
                fontSize=12,
                spaceAfter=8
            )
            normal_style = styles['Normal']

            elements = []

            elements.append(
                Paragraph("Laporan Kesesuaian RPS dan BAP (Single Active Mode)", title_style)
            )
            elements.append(Spacer(1, 12))

            elements.append(
                Paragraph(
                    f"Tanggal Generate: "
                    f"{report.generated_at.strftime(DATETIME_FORMAT)}",
                    normal_style
                )
            )
            elements.append(Spacer(1, 12))

            elements.append(
                Paragraph("Ringkasan Kesesuaian", subtitle_style)
            )
            summary_data = [
                ["Metrik", "Nilai"],
                ["Total Pertemuan", str(report.total_meetings)],
                ["Pertemuan Sesuai", str(report.matched_count)],
                [
                    "Persentase Kesesuaian",
                    f"{report.compliance_percentage:.2f}%"
                ],
                [
                    "Materi Tidak Sesuai",
                    str(len(report.mismatched_list))
                ],
                [
                    "Materi Belum Diajarkan",
                    str(len(report.missing_list))
                ],
            ]
            summary_table = Table(summary_data, colWidths=[8 * cm, 8 * cm])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1),
                 [colors.white, colors.HexColor('#f8f9fa')]),
            ]))
            elements.append(summary_table)
            elements.append(Spacer(1, 20))

            # Tabel detail hasil validasi
            elements.append(
                Paragraph("Detail Hasil Validasi", subtitle_style)
            )
            detail_header = [
                "Pertemuan", "Status", "Skor (%)", "Keterangan"
            ]
            detail_data = [detail_header]
            for r in report.results:
                detail_data.append([
                    str(r.get("meeting_number", "-")),
                    r.get("status", "-"),
                    f"{r.get('similarity_score', 0):.2f}",
                    str(r.get("notes", "-"))[:60],
                ])

            detail_table = Table(
                detail_data,
                colWidths=[2.5 * cm, 3.5 * cm, 2.5 * cm, 8 * cm]
            )
            detail_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1),
                 [colors.white, colors.HexColor('#f8f9fa')]),
            ]))
            elements.append(detail_table)
            elements.append(Spacer(1, 20))

            if report.mismatched_list:
                elements.append(
                    Paragraph("Daftar Materi Tidak Sesuai", subtitle_style)
                )
                mm_header = ["Pertemuan", "Status", "Topik RPS", "Materi BAP"]
                mm_data = [mm_header]
                for item in report.mismatched_list:
                    mm_data.append([
                        str(item.get("meeting_number", "-")),
                        item.get("status", "-"),
                        str(item.get("rps_topic", "-"))[:40],
                        str(item.get("bap_material", "-"))[:40],
                    ])
                mm_table = Table(
                    mm_data,
                    colWidths=[2.5 * cm, 3.5 * cm, 5 * cm, 5.5 * cm]
                )
                mm_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ffc107')),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                elements.append(mm_table)
                elements.append(Spacer(1, 20))

            if report.missing_list:
                elements.append(
                    Paragraph("Daftar Materi Belum Diajarkan", subtitle_style)
                )
                ms_header = ["Pertemuan", "Topik", "Sub Topik"]
                ms_data = [ms_header]
                for item in report.missing_list:
                    ms_data.append([
                        str(item.get("meeting_number", "-")),
                        str(item.get("topic", "-"))[:50],
                        str(item.get("sub_topic", "-"))[:50],
                    ])
                ms_table = Table(
                    ms_data,
                    colWidths=[2.5 * cm, 7 * cm, 7 * cm]
                )
                ms_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc3545')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                elements.append(ms_table)

            doc.build(elements)
            logger.info(f"Laporan PDF berhasil diekspor ke {output_path}")
            return os.path.abspath(output_path)

        except ImportError as e:
            logger.error(f"Library reportlab tidak tersedia: {e}")
            raise ReportGenerationError(
                "Library reportlab tidak terinstall",
                details={"error": str(e)}
            )
        except Exception as e:
            logger.exception(f"Gagal mengekspor laporan ke PDF: {e}")
            raise ReportGenerationError(
                MSG_REPORT_FAILED,
                details={"format": "PDF", "error": str(e)}
            )

    def export_to_excel(self, report: Report, output_path: str) -> str:
        """
        Mengekspor laporan ke format Excel menggunakan pandas dan openpyxl.
        """
        try:
            import pandas as pd

            logger.info(f"Mengekspor laporan ke Excel: {output_path}")

            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Sheet 1: Ringkasan
                summary_data = {
                    "Metrik": [
                        "Total Pertemuan",
                        "Pertemuan Sesuai", "Persentase Kesesuaian (%)",
                        "Materi Tidak Sesuai", "Materi Belum Diajarkan",
                        "Tanggal Generate"
                    ],
                    "Nilai": [
                        report.total_meetings,
                        report.matched_count,
                        f"{report.compliance_percentage:.2f}",
                        len(report.mismatched_list),
                        len(report.missing_list),
                        report.generated_at.strftime(DATETIME_FORMAT)
                    ]
                }
                df_summary = pd.DataFrame(summary_data)
                df_summary.to_excel(
                    writer, sheet_name='Ringkasan', index=False
                )

                # Sheet 2: Detail Hasil Validasi
                if report.results:
                    detail_data = []
                    for r in report.results:
                        detail_data.append({
                            "Pertemuan": r.get("meeting_number", "-"),
                            "Status": r.get("status", "-"),
                            "Skor Kemiripan (%)": r.get(
                                "similarity_score", 0
                            ),
                            "Keterangan": r.get("notes", "-"),
                        })
                    df_detail = pd.DataFrame(detail_data)
                    df_detail.to_excel(
                        writer, sheet_name='Detail Validasi', index=False
                    )

                # Sheet 3: Materi Tidak Sesuai
                if report.mismatched_list:
                    mm_data = []
                    for item in report.mismatched_list:
                        mm_data.append({
                            "Pertemuan": item.get("meeting_number", "-"),
                            "Status": item.get("status", "-"),
                            "Skor (%)": item.get("similarity_score", 0),
                            "Topik RPS": item.get("rps_topic", "-"),
                            "Materi BAP": item.get("bap_material", "-"),
                            "Keterangan": item.get("notes", "-"),
                        })
                    df_mm = pd.DataFrame(mm_data)
                    df_mm.to_excel(
                        writer, sheet_name='Materi Tidak Sesuai', index=False
                    )

                # Sheet 4: Materi Belum Diajarkan
                if report.missing_list:
                    ms_data = []
                    for item in report.missing_list:
                        ms_data.append({
                            "Pertemuan": item.get("meeting_number", "-"),
                            "Topik": item.get("topic", "-"),
                            "Sub Topik": item.get("sub_topic", "-"),
                        })
                    df_ms = pd.DataFrame(ms_data)
                    df_ms.to_excel(
                        writer, sheet_name='Belum Diajarkan', index=False
                    )

            logger.info(f"Laporan Excel berhasil diekspor ke {output_path}")
            return os.path.abspath(output_path)

        except ImportError as e:
            logger.error(f"Library pandas/openpyxl tidak tersedia: {e}")
            raise ReportGenerationError(
                "Library pandas/openpyxl tidak terinstall",
                details={"error": str(e)}
            )
        except Exception as e:
            logger.exception(f"Gagal mengekspor laporan ke Excel: {e}")
            raise ReportGenerationError(
                MSG_REPORT_FAILED,
                details={"format": "Excel", "error": str(e)}
            )
