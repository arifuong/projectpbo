"""
Modul Halaman Data BAP untuk GUI Sistem Validasi RPS-BAP.

Modul ini mengimplementasikan kelas BAPPage yang menyediakan antarmuka CRUD
untuk memanipulasi data Berita Acara Perkuliahan (BAP) secara manual.

Sesuai PRD Section 10.4 - Halaman Data BAP.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional
from datetime import date

from services.bap_manager import BAPManager
from services.course_service import CourseService
from models.bap import BAP
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


class BAPPage(tk.Frame):
    """
    Kelas untuk halaman manajemen Data BAP (CRUD).

    Attributes:
        _bap_manager (BAPManager): Service pengelola data BAP.
        _course_service (CourseService): Service pengelola mata kuliah.
    """

    def __init__(
        self,
        parent: tk.Widget,
        bap_manager: BAPManager,
        course_service: CourseService
    ) -> None:
        """
        Inisialisasi BAPPage.

        Args:
            parent: Widget parent.
            bap_manager: Service BAP manager.
            course_service: Service mata kuliah.
        """
        super().__init__(parent, bg=COLOR_BACKGROUND)
        self._bap_manager: BAPManager = bap_manager
        self._course_service: CourseService = course_service

        self.courses_list: list = []
        self.current_course_id: Optional[int] = None

        self._init_ui()

    def _init_ui(self) -> None:
        """
        Membangun komponen antarmuka halaman Data BAP.
        """
        # Header Halaman
        header_frame = tk.Frame(self, bg=COLOR_BACKGROUND)
        header_frame.pack(fill=tk.X, padx=20, pady=15)
        
        lbl_title = tk.Label(
            header_frame,
            text="Manajemen Berita Acara Perkuliahan (BAP)",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"),
            fg=COLOR_TEXT_DARK,
            bg=COLOR_BACKGROUND
        )
        lbl_title.pack(side=tk.LEFT)

        # Control Panel (Pilih Mata Kuliah & Tombol Aksi CRUD)
        self.control_frame = tk.Frame(self, bg=COLOR_BACKGROUND)
        self.control_frame.pack(fill=tk.X, padx=20, pady=(0, 5))

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

        # Tombol CRUD BAP
        self.btn_add = tk.Button(
            self.control_frame,
            text="Tambah Realisasi (BAP)",
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
            text="Edit Realisasi",
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
            command=self._delete_selected_bap
        )
        self.btn_delete.pack(side=tk.RIGHT, padx=5)

        # Indikator Realisasi Pertemuan (Informasi di bawah Combo)
        self.lbl_indicator = tk.Label(
            self,
            text="BAP Terisi: 0 dari 0 pertemuan rencana (0%)",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg=COLOR_PRIMARY,
            bg=COLOR_BACKGROUND
        )
        self.lbl_indicator.pack(anchor=tk.W, padx=20, pady=(0, 10))

        # Container Tabel
        self.table_frame = tk.Frame(self, bg=COLOR_WHITE, bd=1, relief=tk.SOLID)
        self.table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        # Treeview untuk data BAP
        columns = ("bap_id", "meeting", "date", "material")
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings")
        self.tree.heading("bap_id", text="BAP ID")
        self.tree.heading("meeting", text="Pertemuan Ke-")
        self.tree.heading("date", text="Tanggal Kuliah")
        self.tree.heading("material", text="Materi yang Diajarkan (BAP)")

        self.tree.column("bap_id", width=0, stretch=tk.NO)
        self.tree.column("meeting", width=120, anchor=tk.CENTER)
        self.tree.column("date", width=150, anchor=tk.CENTER)
        self.tree.column("material", width=500, anchor=tk.W)

        # Scrollbar
        scrollbar = ttk.Scrollbar(self.table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def load_courses(self) -> None:
        """
        Memuat daftar mata kuliah ke combobox dropdown.
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
                self.lbl_indicator.config(text="BAP Terisi: 0 dari 0 pertemuan rencana (0%)")
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
            self._load_bap_table()

    def _clear_table(self) -> None:
        """
        Membersihkan isi treeview.
        """
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _load_bap_table(self) -> None:
        """
        Membaca data BAP dari database dan menampilkan ke tabel, serta memperbarui label indikator.
        """
        self._clear_table()
        if self.current_course_id is None:
            return

        try:
            # 1. Load data tabel BAP
            bap_list = self._bap_manager.get_bap_by_course(self.current_course_id)
            for b in bap_list:
                self.tree.insert(
                    "",
                    tk.END,
                    values=(
                        b.bap_id,
                        f"Pertemuan {b.meeting_number}",
                        b.meeting_date.strftime("%Y-%m-%d") if b.meeting_date else "-",
                        b.material_taught
                    )
                )

            # 2. Update Indikator (BR-02)
            # Ambil total rencana pertemuan pada RPS
            total_rps = self._bap_manager._rps_repo.count_by_course(self.current_course_id)
            bap_count = len(bap_list)
            
            percentage = 0.0
            if total_rps > 0:
                percentage = (bap_count / total_rps) * 100
                
            self.lbl_indicator.config(
                text=f"BAP Terisi: {bap_count} dari {total_rps} pertemuan rencana ({percentage:.1f}%)"
            )
        except Exception as e:
            messagebox.showerror("Error Database", f"Gagal memuat data BAP:\n{e}")

    def _open_add_dialog(self) -> None:
        """
        Membuka dialog form tambah BAP.
        """
        if self.current_course_id is None:
            messagebox.showwarning("Peringatan", "Silakan pilih mata kuliah terlebih dahulu.")
            return

        # Ambil total RPS
        total_rps = self._bap_manager._rps_repo.count_by_course(self.current_course_id)
        if total_rps == 0:
            messagebox.showwarning(
                "Peringatan",
                "Mata kuliah ini belum memiliki data rencana RPS. Unggah RPS terlebih dahulu!"
            )
            return

        self._create_form_dialog("Tambah Realisasi BAP", None)

    def _open_edit_dialog(self) -> None:
        """
        Membuka dialog form edit BAP.
        """
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Peringatan", "Silakan pilih baris tabel yang ingin diedit.")
            return

        values = self.tree.item(selected[0], "values")
        bap_id = int(values[0])

        try:
            bap = self._bap_manager.get_bap_by_id(bap_id)
            if bap:
                self._create_form_dialog("Edit Realisasi BAP", bap)
        except Exception as e:
            messagebox.showerror("Error Database", f"Gagal memuat detail BAP:\n{e}")

    def _create_form_dialog(self, title: str, bap: Optional[BAP] = None) -> None:
        """
        Membuat popup dialog form entri BAP.
        """
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.geometry("400x340")
        dialog.transient(self)
        dialog.grab_set()
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
        if bap:
            entry_meeting.insert(0, str(bap.meeting_number))

        # 2. Input Tanggal Pertemuan
        tk.Label(
            frame, text="Tanggal Perkuliahan (YYYY-MM-DD):", font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            bg=COLOR_WHITE, fg=COLOR_TEXT_DARK
        ).pack(anchor=tk.W, pady=(0, 2))

        entry_date = tk.Entry(frame, font=(FONT_FAMILY, FONT_SIZE_NORMAL))
        entry_date.pack(fill=tk.X, pady=(0, 15))
        if bap:
            entry_date.insert(0, bap.meeting_date.strftime("%Y-%m-%d"))
        else:
            entry_date.insert(0, date.today().strftime("%Y-%m-%d"))

        # 3. Input Materi yang Diajarkan
        tk.Label(
            frame, text="Materi yang Diajarkan:", font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            bg=COLOR_WHITE, fg=COLOR_TEXT_DARK
        ).pack(anchor=tk.W, pady=(0, 2))

        entry_material = tk.Entry(frame, font=(FONT_FAMILY, FONT_SIZE_NORMAL))
        entry_material.pack(fill=tk.X, pady=(0, 20))
        if bap:
            entry_material.insert(0, bap.material_taught)

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
            meeting_str = entry_meeting.get().strip()
            date_str = entry_date.get().strip()
            material = entry_material.get().strip()

            if not meeting_str or not date_str or not material:
                messagebox.showwarning("Peringatan", "Semua kolom wajib diisi.", parent=dialog)
                return

            try:
                meeting_num = int(meeting_str)
            except ValueError:
                messagebox.showwarning("Peringatan", "Nomor pertemuan harus berupa angka.", parent=dialog)
                return

            try:
                # Validasi format tanggal YYYY-MM-DD
                bap_date = date.fromisoformat(date_str)
            except ValueError:
                messagebox.showwarning(
                    "Peringatan", 
                    "Format tanggal salah. Gunakan format YYYY-MM-DD (contoh: 2024-09-10).",
                    parent=dialog
                )
                return

            # Jalankan logika simpan/update
            if bap is None:
                # Mode Tambah
                new_bap = BAP(
                    course_id=self.current_course_id,  # type: ignore
                    meeting_number=meeting_num,
                    meeting_date=bap_date,
                    material_taught=material
                )
                try:
                    # Validasi nomor pertemuan sesuai BR-02
                    self._bap_manager.add_bap(new_bap)
                    messagebox.showinfo("Sukses", "Data realisasi BAP berhasil ditambahkan.", parent=dialog)
                    dialog.destroy()
                    self._load_bap_table()
                except DuplicateMeetingError:
                    messagebox.showerror(
                        "Error", 
                        "Nomor pertemuan sudah diinput untuk BAP mata kuliah ini.", 
                        parent=dialog
                    )
                except MeetingNumberExceededError as e:
                    total_rps = e.details.get("total_rps_meetings", 0)
                    messagebox.showerror(
                        "Error Validasi", 
                        f"Nomor pertemuan ({meeting_num}) melebihi total rencana pertemuan di RPS ({total_rps} pertemuan).",
                        parent=dialog
                    )
                except Exception as e:
                    messagebox.showerror("Error Database", f"Gagal menambahkan data:\n{e}", parent=dialog)
            else:
                # Mode Edit
                updated_data = {
                    "meeting_number": meeting_num,
                    "meeting_date": bap_date,
                    "material_taught": material
                }
                try:
                    self._bap_manager.update_bap(bap.bap_id, updated_data)  # type: ignore
                    messagebox.showinfo("Sukses", "Data realisasi BAP berhasil diperbarui.", parent=dialog)
                    dialog.destroy()
                    self._load_bap_table()
                except DuplicateMeetingError:
                    messagebox.showerror(
                        "Error", 
                        "Nomor pertemuan sudah terdaftar untuk BAP mata kuliah ini.", 
                        parent=dialog
                    )
                except MeetingNumberExceededError as e:
                    total_rps = e.details.get("total_rps_meetings", 0)
                    messagebox.showerror(
                        "Error Validasi", 
                        f"Nomor pertemuan ({meeting_num}) melebihi total rencana pertemuan di RPS ({total_rps} pertemuan).",
                        parent=dialog
                    )
                except Exception as e:
                    messagebox.showerror("Error Database", f"Gagal memperbarui data:\n{e}", parent=dialog)

        btn_save = tk.Button(
            btn_frame, text="Simpan", font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            bg=COLOR_SUCCESS, fg=COLOR_WHITE, bd=0, padx=15, pady=6,
            command=_save
        )
        btn_save.pack(side=tk.RIGHT)

    def _delete_selected_bap(self) -> None:
        """
        Menghapus data BAP yang dipilih di tabel.
        """
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Peringatan", "Silakan pilih baris tabel yang ingin dihapus.")
            return

        values = self.tree.item(selected[0], "values")
        bap_id = int(values[0])
        meeting_name = values[1]

        confirm = messagebox.askyesno(
            "Konfirmasi Hapus",
            f"Apakah Anda yakin ingin menghapus catatan realisasi perkuliahan {meeting_name}?"
        )
        if confirm:
            try:
                success = self._bap_manager.delete_bap(bap_id)
                if success:
                    messagebox.showinfo("Sukses", "Data realisasi BAP berhasil dihapus.")
                    self._load_bap_table()
                else:
                    messagebox.showerror("Error", "Gagal menghapus data dari database.")
            except Exception as e:
                messagebox.showerror("Error Database", f"Kesalahan saat menghapus data:\n{e}")
