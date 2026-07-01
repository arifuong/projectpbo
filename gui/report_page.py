"""
Modul Halaman Laporan untuk GUI Sistem Validasi RPS-BAP.

Modul ini mengimplementasikan kelas ReportPage yang menampilkan ringkasan
laporan kesesuaian dan tombol untuk mengekspor hasil ke format PDF atau Excel.

Sesuai PRD Section 10.6 - Halaman Report.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List, Optional

from services.report_generator import ReportGenerator
from services.course_service import CourseService
from models.report import Report
from config.constants import (
    COLOR_BACKGROUND,
    COLOR_WHITE,
    COLOR_TEXT_DARK,
    COLOR_BORDER,
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_DANGER,
    FONT_FAMILY,
    FONT_SIZE_TITLE,
    FONT_SIZE_NORMAL,
    FONT_SIZE_MEDIUM,
    COLOR_INFO
)


class ReportPage(tk.Frame):
    """
    Kelas untuk halaman Pembuatan dan Ekspor Laporan.

    Attributes:
        _report_generator (ReportGenerator): Service pembuat laporan.
        _course_service (CourseService): Service pengelola mata kuliah.
    """

    def __init__(
        self,
        parent: tk.Widget,
        report_generator: ReportGenerator,
        course_service: CourseService
    ) -> None:
        """
        Inisialisasi ReportPage.

        Args:
            parent: Widget parent.
            report_generator: Service ReportGenerator.
            course_service: Service mata kuliah.
        """
        super().__init__(parent, bg=COLOR_BACKGROUND)
        self._report_generator: ReportGenerator = report_generator
        self._course_service: CourseService = course_service

        self.courses_list: list = []
        self.current_course_id: Optional[int] = None
        self.current_report: Optional[Report] = None

        self._init_ui()

    def _init_ui(self) -> None:
        """
        Membangun komponen antarmuka halaman Report.
        """
        # Header Halaman
        header_frame = tk.Frame(self, bg=COLOR_BACKGROUND)
        header_frame.pack(fill=tk.X, padx=20, pady=15)
        
        lbl_title = tk.Label(
            header_frame,
            text="Laporan Evaluasi Pembelajaran",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"),
            fg=COLOR_TEXT_DARK,
            bg=COLOR_BACKGROUND
        )
        lbl_title.pack(side=tk.LEFT)

        # Control Panel
        self.control_frame = tk.Frame(self, bg=COLOR_BACKGROUND)
        self.control_frame.pack(fill=tk.X, padx=20, pady=(0, 10))

        lbl_course = tk.Label(
            self.control_frame,
            text="Pilih Mata Kuliah: ",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            bg=COLOR_BACKGROUND,
            fg=COLOR_TEXT_DARK
        )
        lbl_course.pack(side=tk.LEFT, pady=5)

        self.course_combo = ttk.Combobox(self.control_frame, state="readonly", font=(FONT_FAMILY, FONT_SIZE_NORMAL), width=40)
        self.course_combo.pack(side=tk.LEFT, padx=5, pady=5)
        self.course_combo.bind("<<ComboboxSelected>>", self._on_course_selected)

        # Tombol Aksi Ekspor
        self.btn_export_pdf = tk.Button(
            self.control_frame,
            text="Ekspor PDF",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            bg=COLOR_DANGER,
            fg=COLOR_WHITE,
            bd=0,
            cursor="hand2",
            padx=12,
            pady=5,
            state=tk.DISABLED,
            command=self._export_pdf
        )
        self.btn_export_pdf.pack(side=tk.RIGHT, padx=5)

        self.btn_export_excel = tk.Button(
            self.control_frame,
            text="Ekspor Excel",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            bg=COLOR_SUCCESS,
            fg=COLOR_WHITE,
            bd=0,
            cursor="hand2",
            padx=12,
            pady=5,
            state=tk.DISABLED,
            command=self._export_excel
        )
        self.btn_export_excel.pack(side=tk.RIGHT, padx=5)

        # Container Utama Laporan
        self.report_container = tk.Frame(self, bg=COLOR_BACKGROUND)
        self.report_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        # 1. Ringkasan Kuantitatif
        self.summary_box = tk.LabelFrame(
            self.report_container,
            text=" Ringkasan Kuantitatif Kesesuaian ",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            bg=COLOR_WHITE,
            fg=COLOR_TEXT_DARK,
            bd=1,
            relief=tk.SOLID,
            padx=15,
            pady=15
        )
        self.summary_box.pack(fill=tk.X, pady=(0, 15))

        self.lbl_percentage = tk.Label(
            self.summary_box,
            text="Kesesuaian: 0.0%",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"),
            fg=COLOR_PRIMARY,
            bg=COLOR_WHITE
        )
        self.lbl_percentage.pack(side=tk.LEFT, padx=10)

        # Progress bar
        self.compliance_progress = ttk.Progressbar(
            self.summary_box,
            orient=tk.HORIZONTAL,
            length=300,
            mode='determinate'
        )
        self.compliance_progress.pack(side=tk.LEFT, padx=30)

        self.lbl_details = tk.Label(
            self.summary_box,
            text="0 dari 0 pertemuan sesuai | 0 tidak sesuai | 0 belum diajarkan",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            fg=COLOR_TEXT_DARK,
            bg=COLOR_WHITE
        )
        self.lbl_details.pack(side=tk.LEFT, padx=10)

        # 2. Dua Tabel Hasil Analisis Laporan (Mismatches & Missing)
        self.paned_window = ttk.Panedwindow(self.report_container, orient=tk.VERTICAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        # Tabel 1: Materi Tidak Sesuai
        self.mismatch_frame = tk.LabelFrame(
            self.paned_window,
            text=" Daftar Materi Tidak Sesuai / Diacak ",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            bg=COLOR_WHITE,
            fg=COLOR_TEXT_DARK,
            bd=1,
            relief=tk.SOLID
        )
        self.paned_window.add(self.mismatch_frame, weight=1)

        columns_mm = ("meeting", "status", "score", "notes")
        self.tree_mismatch = ttk.Treeview(self.mismatch_frame, columns=columns_mm, show="headings")
        self.tree_mismatch.heading("meeting", text="Pertemuan")
        self.tree_mismatch.heading("status", text="Status")
        self.tree_mismatch.heading("score", text="Skor Kemiripan")
        self.tree_mismatch.heading("notes", text="Analisis Perbandingan")

        self.tree_mismatch.column("meeting", width=100, anchor=tk.CENTER)
        self.tree_mismatch.column("status", width=120, anchor=tk.CENTER)
        self.tree_mismatch.column("score", width=120, anchor=tk.CENTER)
        self.tree_mismatch.column("notes", width=400, anchor=tk.W)

        scroll_mm = ttk.Scrollbar(self.mismatch_frame, orient=tk.VERTICAL, command=self.tree_mismatch.yview)
        self.tree_mismatch.configure(yscrollcommand=scroll_mm.set)
        self.tree_mismatch.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scroll_mm.pack(side=tk.RIGHT, fill=tk.Y)

        # Tabel 2: Materi Belum Diajarkan
        self.missing_frame = tk.LabelFrame(
            self.paned_window,
            text=" Daftar Materi RPS yang Belum Diajarkan ",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            bg=COLOR_WHITE,
            fg=COLOR_TEXT_DARK,
            bd=1,
            relief=tk.SOLID
        )
        self.paned_window.add(self.missing_frame, weight=1)

        columns_ms = ("meeting", "topic", "sub_topic")
        self.tree_missing = ttk.Treeview(self.missing_frame, columns=columns_ms, show="headings")
        self.tree_missing.heading("meeting", text="Pertemuan Rencana")
        self.tree_missing.heading("topic", text="Topik Pokok Bahasan")
        self.tree_missing.heading("sub_topic", text="Sub-Pokok Bahasan")

        self.tree_missing.column("meeting", width=120, anchor=tk.CENTER)
        self.tree_missing.column("topic", width=350, anchor=tk.W)
        self.tree_missing.column("sub_topic", width=350, anchor=tk.W)

        scroll_ms = ttk.Scrollbar(self.missing_frame, orient=tk.VERTICAL, command=self.tree_missing.yview)
        self.tree_missing.configure(yscrollcommand=scroll_ms.set)
        self.tree_missing.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scroll_ms.pack(side=tk.RIGHT, fill=tk.Y)

    def load_courses(self) -> None:
        """
        Memuat daftar mata kuliah.
        """
        try:
            self.courses_list = self._course_service.get_all_courses()
            combo_values = [
                f"{c.course_code} - {c.course_name} ({c.semester} {c.academic_year})" 
                for c in self.courses_list
            ]
            self.course_combo["values"] = combo_values
            
            if self.courses_list:
                if self.current_course_id is None:
                    self.course_combo.current(0)
                    self._on_course_selected(None)
                else:
                    found = False
                    for idx, c in enumerate(self.courses_list):
                        if c.course_id == self.current_course_id:
                            self.course_combo.current(idx)
                            found = True
                            break
                    if not found:
                        self.course_combo.current(0)
                        self._on_course_selected(None)
            else:
                self.course_combo.set("")
                self._clear_report_data()
        except Exception as e:
            messagebox.showerror("Error", f"Gagal memuat mata kuliah: {e}")

    def refresh_data(self) -> None:
        """
        Menyegarkan data halaman (memanggil load_courses).
        """
        self.load_courses()

    def _on_course_selected(self, event: Optional[tk.Event]) -> None:
        """
        Handler ketika dropdown berubah.
        """
        idx = self.course_combo.current()
        if idx != -1:
            course = self.courses_list[idx]
            self.current_course_id = course.course_id
            self._load_report()

    def _clear_report_data(self) -> None:
        """
        Reset data visualisasi laporan ke nol.
        """
        self.lbl_percentage.config(text="Kesesuaian: 0.0%", fg=COLOR_PRIMARY)
        self.compliance_progress["value"] = 0
        self.lbl_details.config(text="0 dari 0 pertemuan sesuai | 0 tidak sesuai | 0 belum diajarkan")
        
        for item in self.tree_mismatch.get_children():
            self.tree_mismatch.delete(item)
            
        for item in self.tree_missing.get_children():
            self.tree_missing.delete(item)

        self.btn_export_pdf.config(state=tk.DISABLED)
        self.btn_export_excel.config(state=tk.DISABLED)
        self.current_report = None

    def _load_report(self) -> None:
        """
        Menginisialisasi pembuatan Report dari ReportGenerator dan merender hasilnya ke GUI.
        """
        self._clear_report_data()
        if self.current_course_id is None:
            return

        try:
            # Generate Report
            report = self._report_generator.generate_report(self.current_course_id)
            self.current_report = report

            # 1. Tampilkan skor
            pct = report.compliance_percentage
            color = COLOR_SUCCESS if pct >= 70.0 else COLOR_DANGER
            self.lbl_percentage.config(text=f"Kesesuaian: {pct:.1f}%", fg=color)
            self.compliance_progress["value"] = pct

            # 2. Tampilkan metrik detail
            mismatch_count = len(report.mismatched_list)
            missing_count = len(report.missing_list)
            self.lbl_details.config(
                text=f"{report.matched_count} dari {report.total_meetings} pertemuan sesuai | "
                     f"{mismatch_count} tidak sesuai | "
                     f"{missing_count} belum diajarkan"
            )

            # 3. Tampilkan list mismatch
            for item in report.mismatched_list:
                self.tree_mismatch.insert(
                    "",
                    tk.END,
                    values=(
                        f"Pertemuan {item.get('meeting_number')}",
                        item.get("status"),
                        f"{item.get('similarity_score', 0):.1f}%",
                        item.get("notes")
                    )
                )

            # 4. Tampilkan list missing
            for item in report.missing_list:
                self.tree_missing.insert(
                    "",
                    tk.END,
                    values=(
                        f"Pertemuan {item.get('meeting_number')}",
                        item.get("topic"),
                        item.get("sub_topic", "")
                    )
                )

            # Aktifkan tombol ekspor
            self.btn_export_pdf.config(state=tk.NORMAL)
            self.btn_export_excel.config(state=tk.NORMAL)

        except Exception as e:
            # Error jika hasil validasi belum ada
            logger.warning(f"Laporan gagal disusun: {e}")
            self.lbl_details.config(
                text="Hasil validasi tidak ditemukan. Harap jalankan pemeriksaan validasi terlebih dahulu!"
            )

    def _export_pdf(self) -> None:
        """
        Mengekspor laporan ke format PDF lokal menggunakan dialog penyimpanan file.
        """
        if not self.current_report:
            return

        file_path = filedialog.asksaveasfilename(
            title="Ekspor Laporan PDF",
            defaultextension=".pdf",
            filetypes=[("PDF Documents", "*.pdf")],
            initialfile=f"laporan_kesesuaian_{self.current_report.course_name.lower().replace(' ', '_')}.pdf"
        )
        if file_path:
            try:
                self._report_generator.export_to_pdf(self.current_report, file_path)
                messagebox.showinfo("Sukses Ekspor", f"Laporan PDF berhasil disimpan ke:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Gagal Ekspor", f"Gagal mengekspor file PDF:\n{e}")

    def _export_excel(self) -> None:
        """
        Mengekspor laporan ke format Excel lokal menggunakan dialog penyimpanan file.
        """
        if not self.current_report:
            return

        file_path = filedialog.asksaveasfilename(
            title="Ekspor Laporan Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel Workbooks", "*.xlsx")],
            initialfile=f"laporan_kesesuaian_{self.current_report.course_name.lower().replace(' ', '_')}.xlsx"
        )
        if file_path:
            try:
                self._report_generator.export_to_excel(self.current_report, file_path)
                messagebox.showinfo("Sukses Ekspor", f"Laporan Excel berhasil disimpan ke:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Gagal Ekspor", f"Gagal mengekspor file Excel:\n{e}")
