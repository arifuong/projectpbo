"""
Modul Halaman Data RPS untuk GUI Sistem Validasi RPS-BAP.

Modul ini mengimplementasikan kelas RPSPage yang menyediakan antarmuka CRUD
untuk memanipulasi data RPS secara manual pasca ekstraksi PDF.

Sesuai PRD Section 10.3 - Halaman Data RPS.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional

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
    COLOR_DANGER,
    FONT_FAMILY,
    FONT_SIZE_TITLE,
    FONT_SIZE_NORMAL,
    FONT_SIZE_MEDIUM
)


class RPSPage(tk.Frame):
    """
    Kelas untuk halaman manajemen Data RPS (CRUD).

    Attributes:
        _rps_manager (RPSManager): Service pengelola data RPS.
        _course_service (CourseService): Service pengelola mata kuliah.
    """

    def __init__(
        self,
        parent: tk.Widget,
        rps_manager: RPSManager,
        course_service: CourseService
    ) -> None:
        """
        Inisialisasi RPSPage.

        Args:
            parent: Widget parent.
            rps_manager: Service RPS manager.
            course_service: Service mata kuliah.
        """
        super().__init__(parent, bg=COLOR_BACKGROUND)
        self._rps_manager: RPSManager = rps_manager
        self._course_service: CourseService = course_service

        self.courses_list: list = []
        self.current_course_id: Optional[int] = None

        self._init_ui()

    def _init_ui(self) -> None:
        """
        Membangun komponen antarmuka halaman Data RPS.
        """
        # Header Halaman
        header_frame = tk.Frame(self, bg=COLOR_BACKGROUND)
        header_frame.pack(fill=tk.X, padx=20, pady=15)
        
        lbl_title = tk.Label(
            header_frame,
            text="Manajemen Rencana Pembelajaran (RPS)",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"),
            fg=COLOR_TEXT_DARK,
            bg=COLOR_BACKGROUND
        )
        lbl_title.pack(side=tk.LEFT)

        # Control Panel (Pilih Mata Kuliah & Tombol Aksi CRUD)
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

        # Tombol CRUD RPS
        self.btn_add = tk.Button(
            self.control_frame,
            text="Tambah Pertemuan",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            bg=COLOR_PRIMARY,
            fg=COLOR_WHITE,
            bd=0,
            cursor="hand2",
            padx=10,
            pady=5,
            command=self._open_add_dialog
        )
        self.btn_add.pack(side=tk.RIGHT, padx=5)

        self.btn_edit = tk.Button(
            self.control_frame,
            text="Edit Topik",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            bg=COLOR_BACKGROUND,
            fg=COLOR_TEXT_DARK,
            bd=1,
            relief=tk.SOLID,
            cursor="hand2",
            padx=10,
            pady=4,
            command=self._open_edit_dialog
        )
        self.btn_edit.pack(side=tk.RIGHT, padx=5)

        self.btn_delete = tk.Button(
            self.control_frame,
            text="Hapus",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            bg=COLOR_DANGER,
            fg=COLOR_WHITE,
            bd=0,
            cursor="hand2",
            padx=10,
            pady=5,
            command=self._delete_selected_rps
        )
        self.btn_delete.pack(side=tk.RIGHT, padx=5)

        # Container Tabel
        self.table_frame = tk.Frame(self, bg=COLOR_WHITE, bd=1, relief=tk.SOLID)
        self.table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        # Treeview untuk data RPS
        columns = ("rps_id", "meeting", "topic", "sub_topic", "file")
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings")
        self.tree.heading("rps_id", text="RPS ID")
        self.tree.heading("meeting", text="Pertemuan Ke-")
        self.tree.heading("topic", text="Pokok Bahasan (Topik Utama)")
        self.tree.heading("sub_topic", text="Sub-Pokok Bahasan")
        self.tree.heading("file", text="Sumber Dokumen")

        self.tree.column("rps_id", width=0, stretch=tk.NO)  # Kolom ID disembunyikan
        self.tree.column("meeting", width=120, anchor=tk.CENTER)
        self.tree.column("topic", width=300, anchor=tk.W)
        self.tree.column("sub_topic", width=300, anchor=tk.W)
        self.tree.column("file", width=150, anchor=tk.CENTER)

        # Scrollbar
        scrollbar = ttk.Scrollbar(self.table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def load_courses(self) -> None:
        """
        Memuat ulang daftar mata kuliah ke combobox.
        """
        try:
            self.courses_list = self._course_service.get_all_courses()
            combo_values = [
                f"{c.course_code} - {c.course_name} ({c.semester} {c.academic_year})" 
                for c in self.courses_list
            ]
            self.course_combo["values"] = combo_values
            
            # Reset pilihan jika ada
            if self.courses_list:
                # Pilih item pertama secara default jika belum ada course_id aktif
                if self.current_course_id is None:
                    self.course_combo.current(0)
                    self._on_course_selected(None)
                else:
                    # Cari indeks course saat ini
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
        Handler event combobox saat mata kuliah dipilih.
        """
        idx = self.course_combo.current()
        if idx != -1:
            course = self.courses_list[idx]
            self.current_course_id = course.course_id
            self._load_rps_table()

    def _clear_table(self) -> None:
        """
        Membersihkan baris tabel treeview.
        """
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _load_rps_table(self) -> None:
        """
        Mengambil data RPS dari database berdasarkan course_id aktif dan menampilkannya di tabel.
        """
        self._clear_table()
        if self.current_course_id is None:
            return

        try:
            rps_list = self._rps_manager.get_rps_by_course(self.current_course_id)
            for r in rps_list:
                self.tree.insert(
                    "",
                    tk.END,
                    values=(
                        r.rps_id,
                        f"Pertemuan {r.meeting_number}",
                        r.topic,
                        r.sub_topic or "",
                        r.source_file or "Input Manual"
                    )
                )
        except Exception as e:
            messagebox.showerror("Error Database", f"Gagal memuat data RPS dari database:\n{e}")

    def _open_add_dialog(self) -> None:
        """
        Membuka jendela popup dialog modal kustom untuk tambah pertemuan RPS.
        """
        if self.current_course_id is None:
            messagebox.showwarning("Peringatan", "Silakan pilih mata kuliah terlebih dahulu.")
            return

        self._create_form_dialog("Tambah Pertemuan RPS", None)

    def _open_edit_dialog(self) -> None:
        """
        Membuka jendela popup dialog modal kustom untuk mengedit baris RPS terpilih.
        """
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Peringatan", "Silakan pilih baris tabel yang ingin diedit.")
            return

        # Ambil data dari baris terpilih
        values = self.tree.item(selected[0], "values")
        rps_id = int(values[0])
        
        # Ambil objek RPS dari database
        try:
            rps = self._rps_manager.get_rps_by_id(rps_id)
            if rps:
                self._create_form_dialog("Edit Pertemuan RPS", rps)
        except Exception as e:
            messagebox.showerror("Error Database", f"Gagal memuat detail RPS:\n{e}")

    def _create_form_dialog(self, title: str, rps: Optional[RPS] = None) -> None:
        """
        Membangun dialog modal Form kustom.

        Args:
            title: Judul window.
            rps: Objek RPS jika mengedit, None jika tambah baru.
        """
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.geometry("400x320")
        dialog.transient(self)  # Selalu di atas window utama
        dialog.grab_set()  # Blok interaksi window utama
        dialog.resizable(False, False)

        # Frame Form
        frame = tk.Frame(dialog, bg=COLOR_WHITE, padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # 1. Input Nomor Pertemuan
        tk.Label(
            frame, text="Pertemuan Ke- (Angka):", font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            bg=COLOR_WHITE, fg=COLOR_TEXT_DARK
        ).pack(anchor=tk.W, pady=(0, 2))

        entry_meeting = tk.Entry(frame, font=(FONT_FAMILY, FONT_SIZE_NORMAL))
        entry_meeting.pack(fill=tk.X, pady=(0, 15))
        if rps:
            entry_meeting.insert(0, str(rps.meeting_number))

        # 2. Input Pokok Bahasan / Topik
        tk.Label(
            frame, text="Pokok Bahasan (Topik Utama):", font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            bg=COLOR_WHITE, fg=COLOR_TEXT_DARK
        ).pack(anchor=tk.W, pady=(0, 2))

        entry_topic = tk.Entry(frame, font=(FONT_FAMILY, FONT_SIZE_NORMAL))
        entry_topic.pack(fill=tk.X, pady=(0, 15))
        if rps:
            entry_topic.insert(0, rps.topic)

        # 3. Input Sub Pokok Bahasan
        tk.Label(
            frame, text="Sub-Pokok Bahasan (Opsional):", font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            bg=COLOR_WHITE, fg=COLOR_TEXT_DARK
        ).pack(anchor=tk.W, pady=(0, 2))

        entry_sub = tk.Entry(frame, font=(FONT_FAMILY, FONT_SIZE_NORMAL))
        entry_sub.pack(fill=tk.X, pady=(0, 20))
        if rps and rps.sub_topic:
            entry_sub.insert(0, rps.sub_topic)

        # Frame Tombol Aksi Simpan / Batal
        btn_frame = tk.Frame(frame, bg=COLOR_WHITE)
        btn_frame.pack(fill=tk.X)

        btn_cancel = tk.Button(
            btn_frame, text="Batal", font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            bg=COLOR_BACKGROUND, fg=COLOR_TEXT_DARK, bd=1, relief=tk.SOLID, padx=15, pady=5,
            command=dialog.destroy
        )
        btn_cancel.pack(side=tk.LEFT)

        def _save() -> None:
            """Handler ketika tombol simpan diklik."""
            # Ambil data input
            meeting_str = entry_meeting.get().strip()
            topic = entry_topic.get().strip()
            sub_topic = entry_sub.get().strip()

            if not meeting_str or not topic:
                messagebox.showwarning("Peringatan", "Nomor pertemuan dan topik wajib diisi.", parent=dialog)
                return

            try:
                meeting_num = int(meeting_str)
            except ValueError:
                messagebox.showwarning("Peringatan", "Nomor pertemuan harus berupa angka.", parent=dialog)
                return

            if rps is None:
                # Mode Tambah
                new_rps = RPS(
                    course_id=self.current_course_id,  # type: ignore
                    meeting_number=meeting_num,
                    topic=topic,
                    sub_topic=sub_topic,
                    source_file="Input Manual"
                )
                try:
                    self._rps_manager.add_single_rps(new_rps)
                    messagebox.showinfo("Sukses", "Data RPS berhasil ditambahkan.", parent=dialog)
                    dialog.destroy()
                    self._load_rps_table()
                except DuplicateMeetingError:
                    messagebox.showerror("Error", "Nomor pertemuan sudah terdaftar untuk mata kuliah ini.", parent=dialog)
                except Exception as e:
                    messagebox.showerror("Error Database", f"Gagal menambahkan data:\n{e}", parent=dialog)
            else:
                # Mode Edit
                updated_data = {
                    "meeting_number": meeting_num,
                    "topic": topic,
                    "sub_topic": sub_topic
                }
                try:
                    self._rps_manager.update_rps(rps.rps_id, updated_data)  # type: ignore
                    messagebox.showinfo("Sukses", "Data RPS berhasil diperbarui.", parent=dialog)
                    dialog.destroy()
                    self._load_rps_table()
                except DuplicateMeetingError:
                    messagebox.showerror("Error", "Nomor pertemuan sudah terdaftar untuk mata kuliah ini.", parent=dialog)
                except Exception as e:
                    messagebox.showerror("Error Database", f"Gagal memperbarui data:\n{e}", parent=dialog)

        btn_save = tk.Button(
            btn_frame, text="Simpan", font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            bg=COLOR_SUCCESS, fg=COLOR_WHITE, bd=0, padx=15, pady=6,
            command=_save
        )
        btn_save.pack(side=tk.RIGHT)

    def _delete_selected_rps(self) -> None:
        """
        Menghapus data RPS yang dipilih di tabel.
        """
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Peringatan", "Silakan pilih baris tabel yang ingin dihapus.")
            return

        values = self.tree.item(selected[0], "values")
        rps_id = int(values[0])
        meeting_name = values[1]

        confirm = messagebox.askyesno(
            "Konfirmasi Hapus",
            f"Apakah Anda yakin ingin menghapus rencana pembelajaran {meeting_name}?"
        )
        if confirm:
            try:
                success = self._rps_manager.delete_rps(rps_id)
                if success:
                    messagebox.showinfo("Sukses", "Data RPS berhasil dihapus.")
                    self._load_rps_table()
                else:
                    messagebox.showerror("Error", "Gagal menghapus data dari database.")
            except Exception as e:
                messagebox.showerror("Error Database", f"Kesalahan saat menghapus data:\n{e}")
