"""
Modul Halaman Upload PDF RPS untuk GUI Sistem Validasi RPS-BAP.

Modul ini mengimplementasikan kelas UploadPage untuk mengunggah file PDF RPS,
memproses ekstraksi tabel pokok bahasan, menampilkan pratinjau,
dan menyimpan hasilnya ke database.

Sesuai PRD Section 10.2 - Halaman Upload PDF RPS.
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
from typing import List, Dict, Any, Optional

from services.file_upload_handler import FileUploadHandler
from services.pdf_extraction_service import PDFExtractionService
from services.rps_manager import RPSManager
from services.course_service import CourseService
from models.rps import RPS
from config.constants import (
    COLOR_BACKGROUND,
    COLOR_WHITE,
    COLOR_TEXT_DARK,
    COLOR_BORDER,
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    FONT_FAMILY,
    FONT_SIZE_TITLE,
    FONT_SIZE_NORMAL,
    FONT_SIZE_MEDIUM
)


class UploadPage(tk.Frame):
    """
    Kelas untuk halaman Unggah PDF RPS.

    Attributes:
        _upload_handler (FileUploadHandler): Service penangan unggah file.
        _extraction_service (PDFExtractionService): Service ekstraksi dokumen PDF.
        _rps_manager (RPSManager): Service pengelola data RPS.
        _course_service (CourseService): Service pengelola mata kuliah.
    """

    def __init__(
        self,
        parent: tk.Widget,
        upload_handler: FileUploadHandler,
        extraction_service: PDFExtractionService,
        rps_manager: RPSManager,
        course_service: CourseService
    ) -> None:
        """
        Inisialisasi UploadPage.

        Args:
            parent: Widget parent.
            upload_handler: Service upload file.
            extraction_service: Service ekstraksi PDF.
            rps_manager: Service RPS manager.
            course_service: Service mata kuliah.
        """
        super().__init__(parent, bg=COLOR_BACKGROUND)
        self._upload_handler: FileUploadHandler = upload_handler
        self._extraction_service: PDFExtractionService = extraction_service
        self._rps_manager: RPSManager = rps_manager
        self._course_service: CourseService = course_service

        # State data sementara
        self.selected_file_path: str = ""
        self.extracted_items: List[Dict[str, Any]] = []
        self.courses_list: list = []

        self._init_ui()

    def _init_ui(self) -> None:
        """
        Membangun komponen antarmuka halaman Unggah PDF.
        """
        # Header Halaman
        header_frame = tk.Frame(self, bg=COLOR_BACKGROUND)
        header_frame.pack(fill=tk.X, padx=20, pady=15)
        
        lbl_title = tk.Label(
            header_frame,
            text="Unggah Dokumen RPS",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"),
            fg=COLOR_TEXT_DARK,
            bg=COLOR_BACKGROUND
        )
        lbl_title.pack(side=tk.LEFT)

        # Container Utama (2 bagian: Kiri Form Upload, Kanan Preview Tabel)
        self.main_frame = tk.Frame(self, bg=COLOR_BACKGROUND)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Bagian Form Input & Upload
        self.form_frame = tk.LabelFrame(
            self.main_frame,
            text=" Form Upload Dokumen RPS ",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            bg=COLOR_WHITE,
            fg=COLOR_TEXT_DARK,
            bd=1,
            relief=tk.SOLID,
            width=320,
            padx=15,
            pady=15
        )
        self.form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        self.form_frame.pack_propagate(False)

        # 1. Dropdown Pilih Mata Kuliah
        lbl_course = tk.Label(
            self.form_frame,
            text="Pilih Mata Kuliah:",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            bg=COLOR_WHITE,
            fg=COLOR_TEXT_DARK
        )
        lbl_course.pack(anchor=tk.W, pady=(5, 5))

        self.course_combo = ttk.Combobox(self.form_frame, state="readonly", font=(FONT_FAMILY, FONT_SIZE_NORMAL))
        self.course_combo.pack(fill=tk.X, pady=(0, 15))

        # 2. Tombol Pilih File
        lbl_file = tk.Label(
            self.form_frame,
            text="Pilih File PDF RPS:",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            bg=COLOR_WHITE,
            fg=COLOR_TEXT_DARK
        )
        lbl_file.pack(anchor=tk.W, pady=(5, 5))

        self.btn_select_file = tk.Button(
            self.form_frame,
            text="Pilih File PDF...",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            bg=COLOR_BACKGROUND,
            fg=COLOR_TEXT_DARK,
            bd=1,
            relief=tk.SOLID,
            command=self._select_file_dialog
        )
        self.btn_select_file.pack(fill=tk.X, pady=(0, 5))

        self.lbl_selected_file = tk.Label(
            self.form_frame,
            text="Tidak ada file yang dipilih",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL - 2),
            fg=COLOR_BORDER,
            bg=COLOR_WHITE,
            wraplength=280,
            justify=tk.LEFT
        )
        self.lbl_selected_file.pack(anchor=tk.W, pady=(0, 20))

        # 3. Tombol Proses Ekstraksi
        self.btn_process = tk.Button(
            self.form_frame,
            text="Mulai Ekstraksi PDF",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            bg=COLOR_PRIMARY,
            fg=COLOR_WHITE,
            bd=0,
            cursor="hand2",
            command=self._start_extraction_thread
        )
        self.btn_process.pack(fill=tk.X, pady=(0, 15))

        # Progress Bar & Loading Status
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.form_frame,
            variable=self.progress_var,
            maximum=100,
            mode="determinate"
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))

        self.lbl_status = tk.Label(
            self.form_frame,
            text="Status: Siap",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL - 2),
            fg=COLOR_TEXT_DARK,
            bg=COLOR_WHITE
        )
        self.lbl_status.pack(anchor=tk.W)

        # Bagian Kanan: Preview Panel
        self.preview_frame = tk.LabelFrame(
            self.main_frame,
            text=" Pratinjau (Preview) Hasil Ekstraksi ",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            bg=COLOR_WHITE,
            fg=COLOR_TEXT_DARK,
            bd=1,
            relief=tk.SOLID,
            padx=15,
            pady=15
        )
        self.preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

        # Treeview Preview Data
        columns = ("meeting", "topic", "sub_topic")
        self.tree = ttk.Treeview(self.preview_frame, columns=columns, show="headings")
        self.tree.heading("meeting", text="Pertemuan Ke-")
        self.tree.heading("topic", text="Pokok Bahasan (Topik Utama)")
        self.tree.heading("sub_topic", text="Sub-Pokok Bahasan")

        self.tree.column("meeting", width=100, anchor=tk.CENTER)
        self.tree.column("topic", width=250, anchor=tk.W)
        self.tree.column("sub_topic", width=250, anchor=tk.W)

        # Scrollbar untuk Treeview
        scrollbar = ttk.Scrollbar(self.preview_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Frame Tombol Aksi di Bawah Preview
        self.actions_frame = tk.Frame(self, bg=COLOR_BACKGROUND)
        self.actions_frame.pack(fill=tk.X, padx=20, pady=(0, 20))

        self.btn_save = tk.Button(
            self.actions_frame,
            text="Simpan ke Database",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            bg=COLOR_SUCCESS,
            fg=COLOR_WHITE,
            bd=0,
            cursor="hand2",
            padx=15,
            pady=8,
            state=tk.DISABLED,
            command=self._save_to_database
        )
        self.btn_save.pack(side=tk.RIGHT, padx=5)

        self.btn_cancel = tk.Button(
            self.actions_frame,
            text="Batalkan",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            bg=COLOR_BACKGROUND,
            fg=COLOR_TEXT_DARK,
            bd=1,
            relief=tk.SOLID,
            padx=15,
            pady=8,
            state=tk.DISABLED,
            command=self._cancel_preview
        )
        self.btn_cancel.pack(side=tk.RIGHT, padx=5)

    def load_courses(self) -> None:
        """
        Memuat ulang daftar mata kuliah terdaftar ke dalam dropdown combo.
        """
        try:
            self.courses_list = self._course_service.get_all_courses()
            combo_values = [
                f"{c.course_code} - {c.course_name} ({c.semester} {c.academic_year})" 
                for c in self.courses_list
            ]
            self.course_combo["values"] = combo_values
            if combo_values:
                self.course_combo.current(0)
            else:
                self.course_combo.set("")
        except Exception as e:
            logger.error(f"Gagal memuat mata kuliah di UploadPage: {e}")

    def refresh_data(self) -> None:
        """
        Menyegarkan data halaman (memanggil load_courses).
        """
        self.load_courses()

    def _select_file_dialog(self) -> None:
        """
        Membuka file dialog untuk memilih dokumen PDF.
        """
        file_path = filedialog.askopenfilename(
            title="Pilih Dokumen PDF RPS",
            filetypes=[("PDF Files", "*.pdf")]
        )
        if file_path:
            self.selected_file_path = file_path
            self.lbl_selected_file.config(
                text=os.path.basename(file_path),
                fg=COLOR_TEXT_DARK
            )

    def _start_extraction_thread(self) -> None:
        """
        Memulai proses ekstraksi pada thread terpisah (background thread) agar GUI tidak freeze.
        """
        if not self.selected_file_path:
            messagebox.showwarning("Peringatan", "Silakan pilih file PDF terlebih dahulu.")
            return

        idx = self.course_combo.current()
        if idx == -1:
            messagebox.showwarning("Peringatan", "Silakan pilih mata kuliah terlebih dahulu.")
            return

        # Matikan tombol agar tidak double click
        self.btn_process.config(state=tk.DISABLED)
        self.btn_select_file.config(state=tk.DISABLED)
        
        # Jalankan thread
        t = threading.Thread(target=self._run_extraction)
        t.daemon = True
        t.start()

    def _run_extraction(self) -> None:
        """
        Eksekusi ekstraksi PDF di background thread.
        """
        try:
            self.lbl_status.config(text="Status: Memvalidasi file...")
            self.progress_var.set(10)
            self.update_idletasks()
            
            # Simulasi load progress bar
            time.sleep(0.5)
            self.lbl_status.config(text="Status: Menyalin dokumen...")
            self.progress_var.set(30)
            self.update_idletasks()

            # 1. Simpan file PDF ke uploads/
            idx = self.course_combo.current()
            course = self.courses_list[idx]
            saved_path = self._upload_handler.save_file(self.selected_file_path, course.course_id)
            
            time.sleep(0.5)
            self.lbl_status.config(text="Status: Mengekstrak pokok bahasan...")
            self.progress_var.set(60)
            self.update_idletasks()

            # 2. Ekstrak data dari PDF
            self.extracted_items = self._extraction_service.extract_pokok_bahasan(saved_path)
            
            self.progress_var.set(90)
            self.lbl_status.config(text="Status: Menampilkan hasil...")
            self.update_idletasks()
            
            # Tampilkan hasil di Treeview (harus di-update di GUI thread via method safely)
            self.after(0, self._populate_preview_data)
            
        except Exception as e:
            logger.exception("Gagal memproses ekstraksi file.")
            self.after(0, lambda: self._show_error_dialog(str(e)))

    def _populate_preview_data(self) -> None:
        """
        Menampilkan data hasil ekstraksi di Treeview dan mengaktifkan tombol aksi.
        """
        # Bersihkan Treeview
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Masukkan baris baru
        for item in self.extracted_items:
            self.tree.insert(
                "",
                tk.END,
                values=(
                    f"Pertemuan {item.get('meeting_number')}",
                    item.get("topic"),
                    item.get("sub_topic", "")
                )
            )

        self.progress_var.set(100)
        self.lbl_status.config(text="Status: Selesai mengekstrak.")
        
        # Aktifkan tombol
        self.btn_save.config(state=tk.NORMAL)
        self.btn_cancel.config(state=tk.NORMAL)
        self.btn_process.config(state=tk.NORMAL)
        self.btn_select_file.config(state=tk.NORMAL)

    def _show_error_dialog(self, error_msg: str) -> None:
        """
        Menampilkan pesan error jika proses ekstraksi gagal.
        """
        self.progress_var.set(0)
        self.lbl_status.config(text="Status: Gagal.")
        self.btn_process.config(state=tk.NORMAL)
        self.btn_select_file.config(state=tk.NORMAL)
        messagebox.showerror("Error Ekstraksi", f"Gagal mengekstrak PDF RPS:\n{error_msg}")

    def _save_to_database(self) -> None:
        """
        Menyimpan data pratinjau yang terekstrak ke database melalui RPSManager.
        """
        idx = self.course_combo.current()
        if idx == -1:
            return
        course = self.courses_list[idx]

        # Konversi dict items ke list objek RPS
        rps_models: List[RPS] = []
        for item in self.extracted_items:
            rps_models.append(
                RPS(
                    course_id=course.course_id,
                    meeting_number=item["meeting_number"],
                    topic=item["topic"],
                    sub_topic=item.get("sub_topic", ""),
                    source_file=os.path.basename(self.selected_file_path)
                )
            )

        try:
            success = self._rps_manager.save_rps(rps_models, course.course_id)
            if success:
                messagebox.showinfo(
                    "Sukses", 
                    f"Berhasil menyimpan {len(rps_models)} pertemuan RPS untuk mata kuliah {course.course_name}."
                )
                self._cancel_preview()
            else:
                messagebox.showerror("Error", "Gagal menyimpan data RPS ke database.")
        except Exception as e:
            logger.exception("Gagal menyimpan RPS ke database.")
            messagebox.showerror("Error Database", f"Kesalahan saat menyimpan RPS ke database:\n{e}")

    def _cancel_preview(self) -> None:
        """
        Membatalkan pratinjau hasil ekstraksi dan membersihkan widget.
        """
        # Reset state
        self.extracted_items = []
        self.selected_file_path = ""
        self.lbl_selected_file.config(text="Tidak ada file yang dipilih", fg=COLOR_BORDER)
        self.progress_var.set(0)
        self.lbl_status.config(text="Status: Siap")

        # Bersihkan treeview
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Matikan tombol aksi
        self.btn_save.config(state=tk.DISABLED)
        self.btn_cancel.config(state=tk.DISABLED)
