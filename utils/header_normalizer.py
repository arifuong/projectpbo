"""
Header Normalizer untuk parser PDF RPS.

Modul ini bertanggung jawab menormalisasi header tabel PDF
sehingga parser dapat mengenali ARTI header, bukan teks persisnya.

Semua proses pencarian header harus melalui normalize_header().
"""

import re
import logging
from typing import Optional

logger = logging.getLogger("utils.header_normalizer")

# ============================================================
# HEADER MAPPING
# ============================================================
# Setiap key adalah nama semantik kolom.
# Setiap value adalah list pattern yang sudah dinormalisasi.
# Pattern dicocokkan secara substring terhadap header yang sudah dinormalisasi.
# Pattern yang lebih panjang (spesifik) harus diletakkan PERTAMA
# agar matching prioritas berjalan benar.
# ============================================================

HEADER_MAPPING = {
    "meeting": [
        "minggu ke",
        "mg ke",
        "minggu",
        "pertemuan ke",
        "pertemuan",
        "pert ke",
        "pert",
        "sesi",
        "meeting",
        "session",
        "week",
    ],
    "topic": [
        "materi pembelajaran pustaka",
        "materi pembelajaran pokok bahasan",
        "materi pembelajaran",
        "materi kuliah",
        "pokok bahasan",
        "topik pembelajaran",
        "bahan kajian",
        "learning material",
        "materi",
        "topik",
        "topic",
    ],
    "sub_cpmk": [
        "kemampuan akhir tiap tahapan belajar",
        "kemampuan akhir yang diharapkan",
        "sub cp mk",
        "sub cpmk",
        "learning outcome",
    ],
    "sub_topic": [
        "sub pokok bahasan",
        "sub topik",
        "rincian materi",
        "detail materi",
    ],
    "indicator": [
        "indikator",
        "indicator",
    ],
    "assessment": [
        "kriteria penilaian",
        "kriteria bentuk penilaian",
        "bentuk penilaian",
        "penilaian",
        "assessment",
    ],
    "method": [
        "metode pembelajaran",
        "bentuk pembelajaran",
        "pengalaman belajar",
        "media pembelajaran",
        "estimasi waktu",
    ],
    "weight": [
        "bobot penilaian",
        "bobot",
    ],
    "reference": [
        "daftar pustaka",
        "pustaka",
        "referensi",
        "reference",
    ],
    "identity": [
        "capaian pembelajaran lulusan",
        "capaian pembelajaran",
        "deskripsi mata kuliah",
        "deskripsi singkat mk",
        "deskripsi",
        "dosen pengampu",
        "dosen pengembang rps",
        "dosen koordinator",
        "tim pengembang",
        "mata kuliah",
        "program studi",
        "identitas",
        "tgl penyusunan",
        "kode mk",
        "semester",
        "bobot sks",
        "cpl prodi",
        "cpmk",
        "cpl",
    ],
}

# Semantic groups yang VALID untuk dipilih sebagai kolom Topic
VALID_TOPIC_ROLES = {"topic"}

# Semantic groups yang VALID untuk dipilih sebagai kolom Meeting
VALID_MEETING_ROLES = {"meeting"}

# Semantic groups yang VALID untuk dipilih sebagai kolom Sub Topic
VALID_SUB_TOPIC_ROLES = {"sub_topic", "sub_cpmk"}

# Semantic groups yang HARUS DIBLOKIR — tidak boleh dipilih sebagai meeting/topic/sub_topic
BANNED_ROLES = {"identity", "reference", "assessment", "method", "weight", "indicator"}


def _clean_header_text(raw: str) -> str:
    """
    Membersihkan teks header dari noise PDF: newline, bracket, bullet, angka numbering, dsb.
    Mengembalikan string lowercase bersih yang siap dicocokkan.
    """
    if not raw:
        return ""

    text = str(raw)

    # Replace newlines, tabs, carriage returns with spaces
    text = text.replace("\r", " ").replace("\n", " ").replace("\t", " ")

    # Remove corrupt unicode / PDF artifacts
    text = text.replace("â€¢", " ")
    text = re.sub(r'[\uf0b7\u2022\u25cf\u25aa●▪★]', ' ', text)

    # Remove brackets and parentheses content markers but keep the text inside
    text = re.sub(r'[(){}\[\]]', ' ', text)

    # Remove separators: colon, dash used as separator, underscores
    text = re.sub(r'[:_]', ' ', text)

    # Remove numbering at the beginning: (1), 1., 1), a., a)
    text = re.sub(r'^\s*(?:\(?\d+\)?[.\)]\s*)', '', text)

    # Lowercase
    text = text.lower()

    # Replace hyphens between words with spaces (e.g. "sub-cpmk" -> "sub cpmk", "sub-cp-mk" -> "sub cp mk")
    text = re.sub(r'-', ' ', text)

    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def normalize_header(raw_header: str) -> Optional[str]:
    """
    Menormalisasi satu header mentah menjadi nama semantik kolom.

    Args:
        raw_header: Teks header mentah dari PDF (bisa multiline, ada bracket, dsb).

    Returns:
        Nama semantik kolom (e.g. "meeting", "topic", "sub_cpmk", "identity", None).
        None jika tidak cocok dengan pattern manapun.

    Contoh:
        normalize_header("Materi Pembelajaran\\n(Pustaka)")  -> "topic"
        normalize_header("Mg Ke")                             -> "meeting"
        normalize_header("Sub-CP-MK")                         -> "sub_cpmk"
        normalize_header("Dosen Pengampu")                     -> "identity"
    """
    cleaned = _clean_header_text(raw_header)
    if not cleaned:
        return None

    # Coba cocokkan dari setiap grup di HEADER_MAPPING
    # Prioritas: pattern yang lebih panjang (lebih spesifik) dicek terlebih dahulu
    best_match: Optional[str] = None
    best_match_len = 0

    for role, patterns in HEADER_MAPPING.items():
        for pattern in patterns:
            if pattern in cleaned:
                if len(pattern) > best_match_len:
                    best_match = role
                    best_match_len = len(pattern)

    return best_match


def build_column_roles(table: list, normalize_cell_fn=None) -> dict:
    """
    Membangun mapping {col_index: semantic_role} dari header tabel.

    Menggabungkan maksimal 4 baris pertama tabel menjadi satu header per kolom,
    lalu menormalisasi setiap kolom menggunakan normalize_header().

    Args:
        table: List of rows (List[List[str]]).
        normalize_cell_fn: Fungsi opsional untuk membersihkan cell (e.g. RPSParser.normalize_cell).

    Returns:
        Dict[int, str]: Mapping {col_index: semantic_role}.
    """
    if not table:
        return {}

    max_cols = max(len(row) for row in table)
    if max_cols == 0:
        return {}

    header_rows_count = min(4, len(table))
    header_rows = table[:header_rows_count]

    roles = {}

    for col_idx in range(max_cols):
        # Gabungkan teks dari baris-baris header untuk kolom ini
        cells = []
        for row in header_rows:
            if col_idx < len(row):
                cell = row[col_idx]
                if normalize_cell_fn:
                    cell = normalize_cell_fn(cell, keep_newline=False)
                elif cell is not None:
                    cell = str(cell)
                else:
                    cell = ""
                if cell.strip():
                    cells.append(cell.strip())

        combined_header = " ".join(cells)
        if not combined_header.strip():
            continue

        role = normalize_header(combined_header)
        if role is not None:
            roles[col_idx] = role

            # Log normalization
            logger.debug(
                f"Header Normalization — col={col_idx}, "
                f"original='{combined_header}', "
                f"normalized='{_clean_header_text(combined_header)}', "
                f"mapped_to='{role}'"
            )

    return roles
