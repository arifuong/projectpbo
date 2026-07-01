"""
Modul Halaman Validasi Kesesuaian untuk GUI Sistem Validasi RPS-BAP.

Modul ini mengimplementasikan kelas ValidationPage yang mengorkestrasi pemicuan
proses validasi kesesuaian dan menampilkan tabel status hasil validasi
berwarna (Hijau, Kuning, Merah).

Sesuai PRD Section 10.5 - Halaman Validation.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from typing import List, Optional

from services.validator import Validator
from services.course_service import CourseService
from models.validation_result import ValidationResult
from config.constants import (
    COLOR_BACKGROUND,
    COLOR_WHITE,
    COLOR_TEXT_DARK,
    COLOR_BORDER,
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_DANGER,
    COLOR_WARNING,
    COLOR_PENDING,
    FONT_FAMILY,
    FONT_SIZE_TITLE,
    FONT_SIZE_NORMAL,
    STATUS_SESUAI,
    STATUS_TIDAK_SESUAI,
    STATUS_TIDAK_DITEMUKAN,
    STATUS_PENDING
)


class ValidationPage(tk.Frame):
    """
    Kelas untuk halaman Proses Validasi.

    Attributes:
        _validator (Validator): Service Validation Engine.
        _course_service (CourseService): Service pengelola mata kuliah.
    """

    def __init__(
        self,
        parent: tk.Widget,
        validator: Validator,
        course_service: CourseService
    ) -> None:
        """
        Inisialisasi ValidationPage.

        Args:
            parent: Widget parent.
            validator: Service Validator.
            course_service: Service mata kuliah.
        """
        super().__init__(parent, bg=COLOR_BACKGROUND)
        self._validator: Validator = validator
        self._course_service: CourseService = course_service

        self.courses_list: list = []
        self.current_course_id: Optional[int] = None

        self._init_ui()

    def _init_ui(self) -> None:
        """
        Membangun komponen antarmuka halaman Validation.
        """
        # Header Halaman
        header_frame = tk.Frame(self, bg=COLOR_BACKGROUND)
        header_frame.pack(fill=tk.X, padx=20, pady=15)
        
        lbl_title = tk.Label(
            header_frame,
            text="Pemeriksaan Kesesuaian RPS & BAP",
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

        # Tombol Jalankan Validasi
        self.btn_validate = tk.Button(
            self.control_frame,
            text="Jalankan Validasi",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            bg=COLOR_PRIMARY,
            fg=COLOR_WHITE,
            bd=0,
            cursor="hand2",
            padx=15,
            pady=6,
            command=self._start_validation_thread
        )
        self.btn_validate.pack(side=tk.RIGHT, padx=5)

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self,
            variable=self.progress_var,
            maximum=100,
            mode="determinate"
        )
        self.progress_bar.pack(fill=tk.X, padx=20, pady=(0, 10))

        # Container Tabel
        self.table_frame = tk.Frame(self, bg=COLOR_WHITE, bd=1, relief=tk.SOLID)
        self.table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        # Treeview untuk hasil validasi
        columns = ("meeting", "similarity", "status", "notes")
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings")
        self.tree.heading("meeting", text="Pertemuan Ke-")
        self.tree.heading("similarity", text="Skor Kemiripan (%)")
        self.tree.heading("status", text="Status Hasil")
        self.tree.heading("notes", text="Keterangan / Notes")

        self.tree.column("meeting", width=120, anchor=tk.CENTER)
        self.tree.column("similarity", width=150, anchor=tk.CENTER)
        self.tree.column("status", width=150, anchor=tk.CENTER)
        self.tree.column("notes", width=450, anchor=tk.W)

        # Menerapkan style warna status baris
        # Gunakan tag konfigurasi warna latar belakang
        self.tree.tag_configure("status_sesuai", background="#d4edda", foreground="#155724")
        self.tree.tag_configure("status_tidak_sesuai", background="#fff3cd", foreground="#856404")
        self.tree.tag_configure("status_tidak_ditemukan", background="#f8d7da", foreground="#721c24")
        self.tree.tag_configure("status_pending", background="#e2e3e5", foreground="#383d41")

        # Scrollbar
        scrollbar = ttk.Scrollbar(self.table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def load_courses(self) -> None:
        """
        Memuat daftar mata kuliah ke combobox.
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
                self._clear_table()
        except Exception as e:
            messagebox.showerror("Error", f"Gagal memuat mata kuliah: {e}")

    def refresh_data(self) -> None:
        """
        Menyegarkan data halaman (memanggil load_courses).
        """
        self.load_courses()

    def _on_course_selected(self, event: Optional[tk.Event]) -> None:
        """
        Handler ketika combobox mata kuliah berubah.
        """
        idx = self.course_combo.current()
        if idx != -1:
            course = self.courses_list[idx]
            self.current_course_id = course.course_id
            self._load_validation_results()

    def _clear_table(self) -> None:
        """
        Membersihkan isi treeview.
        """
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _load_validation_results(self) -> None:
        """
        Membaca riwayat hasil validasi dari database dan menampilkannya di tabel dengan warna status.
        """
        self._clear_table()
        if self.current_course_id is None:
            return

        try:
            results = self._validator.get_validation_results(self.current_course_id)
            for r in results:
                # Tentukan tag warna berdasarkan status
                tag = "status_pending"
                if r.status == STATUS_SESUAI:
                    tag = "status_sesuai"
                elif r.status == STATUS_TIDAK_SESUAI:
                    tag = "status_tidak_sesuai"
                elif r.status == STATUS_TIDAK_DITEMUKAN:
                    tag = "status_tidak_ditemukan"

                self.tree.insert(
                    "",
                    tk.END,
                    values=(
                        f"Pertemuan {r.meeting_number}",
                        f"{r.similarity_score:.1f}%",
                        r.status,
                        r.notes or ""
                    ),
                    tags=(tag,)
                )
        except Exception as e:
            messagebox.showerror("Error Database", f"Gagal memuat riwayat validasi:\n{e}")

    def _start_validation_thread(self) -> None:
        """
        Memulai proses validasi di thread terpisah.
        """
        if self.current_course_id is None:
            messagebox.showwarning("Peringatan", "Silakan pilih mata kuliah terlebih dahulu.")
            return

        self.btn_validate.config(state=tk.DISABLED)
        self.course_combo.config(state=tk.DISABLED)
        self.progress_var.set(0)

        t = threading.Thread(target=self._run_validation)
        t.daemon = True
        t.start()

    def _run_validation(self) -> None:
        """
        Eksekusi logika Validation Engine di background thread.
        """
        try:
            # Simulasi progress loading
            for i in range(1, 6):
                self.progress_var.set(i * 15)
                self.update_idletasks()
                time.sleep(0.1)

            # Jalankan logika validasi
            self._validator.run_validation(self.current_course_id)  # type: ignore

            self.progress_var.set(100)
            self.update_idletasks()

            # Selesai
            self.after(0, self._on_validation_success)
        except Exception as e:
            logger.exception("Gagal menjalankan validasi.")
            self.after(0, lambda: self._on_validation_failed(str(e)))

    def _on_validation_success(self) -> None:
        """
        Pemberitahuan sukses validasi.
        """
        self.btn_validate.config(state=tk.NORMAL)
        self.course_combo.config(state="readonly")
        messagebox.showinfo("Sukses", "Proses validasi selesai dijalankan.")
        self._load_validation_results()

    def _on_validation_failed(self, error_msg: str) -> None:
        """
        Pemberitahuan gagal validasi.
        """
        self.btn_validate.config(state=tk.NORMAL)
        self.course_combo.config(state="readonly")
        self.progress_var.set(0)
        messagebox.showerror(
            "Gagal Validasi",
            f"Proses validasi tidak dapat diselesaikan:\n{error_msg}"
        )
