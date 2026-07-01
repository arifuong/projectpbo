"""
Modul Halaman Dashboard untuk GUI Sistem Validasi RPS-BAP.

Modul ini mengimplementasikan kelas DashboardPage yang menampilkan ringkasan
statistik sistem, daftar mata kuliah dengan tingkat ketidaksesuaian tertinggi,
dan diagram persentase kesesuaian sederhana menggunakan Canvas Tkinter.

Sesuai PRD Section 10.1 - Halaman Dashboard.
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, List

from services.dashboard_service import DashboardService
from services.course_service import CourseService
from config.constants import (
    COLOR_PRIMARY,
    COLOR_BACKGROUND,
    COLOR_WHITE,
    COLOR_TEXT_DARK,
    COLOR_BORDER,
    FONT_FAMILY,
    FONT_SIZE_TITLE,
    FONT_SIZE_LARGE,
    FONT_SIZE_NORMAL,
    COLOR_SUCCESS,
    COLOR_DANGER
)


class DashboardPage(tk.Frame):
    """
    Kelas untuk halaman Dashboard utama.

    Attributes:
        _dashboard_service (DashboardService): Service untuk data dashboard.
        _course_service (CourseService): Service untuk data mata kuliah.
    """

    def __init__(
        self,
        parent: tk.Widget,
        dashboard_service: DashboardService,
        course_service: CourseService
    ) -> None:
        """
        Inisialisasi DashboardPage.

        Args:
            parent: Widget parent.
            dashboard_service: Service dashboard.
            course_service: Service mata kuliah.
        """
        super().__init__(parent, bg=COLOR_BACKGROUND)
        self._dashboard_service: DashboardService = dashboard_service
        self._course_service: CourseService = course_service

        self._init_ui()

    def _init_ui(self) -> None:
        """
        Membangun komponen antarmuka Halaman Dashboard.
        """
        # Header Halaman
        header_frame = tk.Frame(self, bg=COLOR_BACKGROUND)
        header_frame.pack(fill=tk.X, padx=20, pady=15)
        
        lbl_title = tk.Label(
            header_frame,
            text="Dashboard Ringkasan",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"),
            fg=COLOR_TEXT_DARK,
            bg=COLOR_BACKGROUND
        )
        lbl_title.pack(side=tk.LEFT)

        # Container Utama (Grid / Scrollable)
        self.main_container = tk.Frame(self, bg=COLOR_BACKGROUND)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Row 1: Summary Cards
        self.cards_frame = tk.Frame(self.main_container, bg=COLOR_BACKGROUND)
        self.cards_frame.pack(fill=tk.X, pady=10)

        self.card_courses = self._create_card(self.cards_frame, "MATA KULIAH", "0", COLOR_PRIMARY)
        self.card_rps = self._create_card(self.cards_frame, "RPS DIUNGGAH", "0", COLOR_SUCCESS)
        self.card_bap = self._create_card(self.cards_frame, "BAP DIINPUT", "0", COLOR_PRIMARY)
        self.card_compliance = self._create_card(self.cards_frame, "RATA-RATA KESESUAIAN", "0.0%", COLOR_DANGER)

        # Row 2: Layout 2 Kolom (Kiri: Diagram, Kanan: Top Mismatches)
        self.content_frame = tk.Frame(self.main_container, bg=COLOR_BACKGROUND)
        self.content_frame.pack(fill=tk.BOTH, expand=True, pady=15)

        # Kolom Kiri - Diagram Persentase
        self.chart_frame = tk.LabelFrame(
            self.content_frame,
            text=" Grafis Kesesuaian per Mata Kuliah ",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            bg=COLOR_WHITE,
            fg=COLOR_TEXT_DARK,
            bd=1,
            relief=tk.SOLID
        )
        self.chart_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # Canvas untuk diagram batang
        self.canvas = tk.Canvas(self.chart_frame, bg=COLOR_WHITE, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Kolom Kanan - Top Mismatches
        self.table_frame = tk.LabelFrame(
            self.content_frame,
            text=" Ketidaksesuaian Tertinggi (Mismatches) ",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            bg=COLOR_WHITE,
            fg=COLOR_TEXT_DARK,
            bd=1,
            relief=tk.SOLID
        )
        self.table_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

        # Treeview untuk Top Mismatches
        columns = ("code", "name", "semester", "mismatches")
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings", height=8)
        self.tree.heading("code", text="Kode")
        self.tree.heading("name", text="Nama Mata Kuliah")
        self.tree.heading("semester", text="Semester")
        self.tree.heading("mismatches", text="Jumlah Tidak Sesuai")

        self.tree.column("code", width=80, anchor=tk.CENTER)
        self.tree.column("name", width=180, anchor=tk.W)
        self.tree.column("semester", width=100, anchor=tk.CENTER)
        self.tree.column("mismatches", width=120, anchor=tk.CENTER)

        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def _create_card(self, parent: tk.Widget, title: str, value: str, color: str) -> Dict[str, Any]:
        """
        Membuat komponen summary card (widget persegi).

        Args:
            parent: Frame induk.
            title: Label teks kecil atas.
            value: Angka/nilai utama.
            color: Warna garis dekorasi kiri.

        Returns:
            Dict[str, Any]: Widget referensi yang dapat diupdate nilainya.
        """
        card = tk.Frame(parent, bg=COLOR_WHITE, bd=1, relief=tk.SOLID, height=100)
        card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        card.pack_propagate(False)

        # Garis hiasan warna di sisi kiri
        accent = tk.Frame(card, bg=color, width=5)
        accent.pack(side=tk.LEFT, fill=tk.Y)

        inner = tk.Frame(card, bg=COLOR_WHITE, padx=10, pady=10)
        inner.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        lbl_title = tk.Label(
            inner,
            text=title,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg=COLOR_BORDER,
            bg=COLOR_WHITE
        )
        lbl_title.pack(anchor=tk.W)

        lbl_value = tk.Label(
            inner,
            text=value,
            font=(FONT_FAMILY, FONT_SIZE_LARGE, "bold"),
            fg=COLOR_TEXT_DARK,
            bg=COLOR_WHITE
        )
        lbl_value.pack(anchor=tk.W, pady=(5, 0))

        return {"card": card, "value_label": lbl_value}

    def refresh_data(self) -> None:
        """
        Mengambil data terbaru dari Service dan memperbarui visualisasi halaman.
        """
        # 1. Update Cards
        stats = self._dashboard_service.get_summary_statistics()
        self.card_courses["value_label"].config(text=str(stats.get("total_courses", 0)))
        self.card_rps["value_label"].config(text=str(stats.get("total_rps", 0)))
        self.card_bap["value_label"].config(text=str(stats.get("total_bap", 0)))
        self.card_compliance["value_label"].config(text=f"{stats.get('avg_compliance', 0.0):.1f}%")

        # 2. Update Treeview Top Mismatches
        # Bersihkan treeview
        for item in self.tree.get_children():
            self.tree.delete(item)

        mismatches = self._dashboard_service.get_top_mismatched_courses(8)
        for m in mismatches:
            self.tree.insert(
                "",
                tk.END,
                values=(
                    m.get("course_code"),
                    m.get("course_name"),
                    f"{m.get('semester')} {m.get('academic_year')}",
                    m.get("mismatch_count")
                )
            )

        # 3. Draw Chart (Canvas)
        self._draw_chart()

    def _draw_chart(self) -> None:
        """
        Menggambar diagram batang persentase kesesuaian pada Canvas Tkinter.
        """
        self.canvas.delete("all")
        
        # Ambil data diagram
        chart_data = self._dashboard_service.get_compliance_chart_data()
        if not chart_data:
            self.canvas.create_text(
                150, 100,
                text="Belum ada data validasi kesesuaian.",
                font=(FONT_FAMILY, FONT_SIZE_NORMAL),
                fill=COLOR_BORDER
            )
            return

        # Ambil dimensi canvas saat ini
        canvas_width = max(self.canvas.winfo_width(), 400)
        canvas_height = max(self.canvas.winfo_height(), 220)

        # Parameter gambar
        padding_left = 50
        padding_bottom = 30
        padding_top = 20
        padding_right = 20

        graph_width = canvas_width - padding_left - padding_right
        graph_height = canvas_height - padding_top - padding_bottom

        # Gambar sumbu Y & X
        self.canvas.create_line(
            padding_left, padding_top,
            padding_left, canvas_height - padding_bottom,
            fill=COLOR_BORDER, width=1
        )
        self.canvas.create_line(
            padding_left, canvas_height - padding_bottom,
            canvas_width - padding_right, canvas_height - padding_bottom,
            fill=COLOR_BORDER, width=1
        )

        # Gambar grid garis bantu Y (0%, 25%, 50%, 75%, 100%)
        for pct in [0, 25, 50, 75, 100]:
            y_pos = canvas_height - padding_bottom - (pct / 100 * graph_height)
            self.canvas.create_text(
                padding_left - 10, y_pos,
                text=f"{pct}%",
                font=(FONT_FAMILY, FONT_SIZE_NORMAL - 2),
                anchor=tk.E,
                fill=COLOR_BORDER
            )
            if pct > 0:
                self.canvas.create_line(
                    padding_left, y_pos,
                    canvas_width - padding_right, y_pos,
                    fill=COLOR_BACKGROUND, dash=(2, 2)
                )

        # Menggambar batang data
        num_items = len(chart_data)
        bar_gap = 10
        total_gaps_width = bar_gap * (num_items + 1)
        bar_width = (graph_width - total_gaps_width) / num_items if num_items > 0 else 30
        
        # Batasi lebar batang agar tidak terlalu gemuk
        if bar_width > 50:
            bar_width = 50

        for idx, item in enumerate(chart_data):
            code = item.get("course_code", "")
            pct = item.get("compliance_percentage", 0.0)

            # Hitung posisi kotak batang
            x_start = padding_left + bar_gap + idx * (bar_width + bar_gap)
            x_end = x_start + bar_width
            y_end = canvas_height - padding_bottom
            y_start = y_end - (pct / 100 * graph_height)

            # Gambar batang
            color = COLOR_SUCCESS if pct >= 70.0 else COLOR_DANGER
            self.canvas.create_rectangle(
                x_start, y_start, x_end, y_end,
                fill=color, outline=""
            )

            # Tulis nilai di atas batang
            self.canvas.create_text(
                x_start + (bar_width / 2), y_start - 8,
                text=f"{pct:.0f}%",
                font=(FONT_FAMILY, FONT_SIZE_NORMAL - 2, "bold"),
                anchor=tk.S,
                fill=COLOR_TEXT_DARK
            )

            # Tulis label kode di sumbu X
            self.canvas.create_text(
                x_start + (bar_width / 2), y_end + 10,
                text=code,
                font=(FONT_FAMILY, FONT_SIZE_NORMAL - 2),
                anchor=tk.N,
                fill=COLOR_TEXT_DARK
            )
