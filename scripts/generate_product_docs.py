from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Iterable

from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    Image,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "pdf"
LOGO = ROOT / "logo.png"
INSTALLER_URL = "https://drive.google.com/file/d/1dIgIS8ApF7IH9nSl8DUZt730VKpUgBVk/view?usp=sharing"
DOC_DATE = date(2026, 8, 23)

NAVY = colors.HexColor("#0B1218")
INK = colors.HexColor("#15232D")
MUTED = colors.HexColor("#5C6B74")
CYAN = colors.HexColor("#00B9FF")
BLUE = colors.HexColor("#0077A8")
PALE = colors.HexColor("#EAF7FC")
LINE = colors.HexColor("#D8E3E8")
GREEN = colors.HexColor("#17815D")
AMBER = colors.HexColor("#C77B00")
RED = colors.HexColor("#B43C3C")


def esc(value: object) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


class ProductDocTemplate(BaseDocTemplate):
    def __init__(self, filename: Path, title: str, document_code: str):
        self.product_title = title
        self.document_code = document_code
        super().__init__(
            str(filename),
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=20 * mm,
            bottomMargin=18 * mm,
            title=title,
            author="ERGoSIGHT",
            subject="ERGoSIGHT product documentation",
        )
        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="body",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )
        self.addPageTemplates(PageTemplate(id="content", frames=frame, onPage=self._draw_page))

    def _draw_page(self, canvas, doc):
        if doc.page == 1:
            canvas.setFillColor(NAVY)
            canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
            canvas.setFillColor(CYAN)
            canvas.rect(0, 0, 9 * mm, A4[1], fill=1, stroke=0)
            return
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.line(18 * mm, A4[1] - 13 * mm, A4[0] - 18 * mm, A4[1] - 13 * mm)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(INK)
        canvas.drawString(18 * mm, A4[1] - 10 * mm, "ERGoSIGHT")
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawRightString(A4[0] - 18 * mm, A4[1] - 10 * mm, self.document_code)
        canvas.line(18 * mm, 12 * mm, A4[0] - 18 * mm, 12 * mm)
        canvas.drawString(18 * mm, 8 * mm, self.product_title)
        canvas.drawRightString(A4[0] - 18 * mm, 8 * mm, f"Halaman {doc.page}")
        canvas.restoreState()


class ProcessFlow(Flowable):
    def __init__(self, labels: list[str], width: float = 174 * mm, columns: int = 4):
        super().__init__()
        self.labels = labels
        self.width = width
        self.columns = min(columns, len(labels))
        self.row_height = 25 * mm
        self.rows = (len(labels) + self.columns - 1) // self.columns
        self.height = self.rows * self.row_height

    def draw(self):
        gap = 7 * mm
        box_width = (self.width - gap * (self.columns - 1)) / self.columns
        box_height = 15 * mm
        for index, label in enumerate(self.labels):
            row, col = divmod(index, self.columns)
            visual_col = col if row % 2 == 0 else self.columns - 1 - col
            x = visual_col * (box_width + gap)
            y = self.height - (row + 1) * self.row_height + 5 * mm
            self.canv.setFillColor(PALE if index % 2 == 0 else colors.white)
            self.canv.setStrokeColor(BLUE)
            self.canv.roundRect(x, y, box_width, box_height, 2 * mm, fill=1, stroke=1)
            paragraph = Paragraph(
                f"<b>{index + 1}</b><br/>{esc(label)}",
                ParagraphStyle(
                    "FlowLabel",
                    fontName="Helvetica",
                    fontSize=7.5,
                    leading=9,
                    alignment=TA_CENTER,
                    textColor=INK,
                ),
            )
            _, h = paragraph.wrap(box_width - 4 * mm, box_height - 2 * mm)
            paragraph.drawOn(self.canv, x + 2 * mm, y + (box_height - h) / 2)
            if index + 1 < len(self.labels):
                next_row, next_col = divmod(index + 1, self.columns)
                if next_row == row:
                    direction = 1 if row % 2 == 0 else -1
                    start_x = x + box_width if direction == 1 else x
                    end_x = start_x + direction * gap
                    mid_y = y + box_height / 2
                    self._arrow(start_x, mid_y, end_x, mid_y)
                else:
                    start_x = x + box_width / 2
                    self._arrow(start_x, y, start_x, y - 5 * mm)

    def _arrow(self, x1: float, y1: float, x2: float, y2: float):
        self.canv.setStrokeColor(BLUE)
        self.canv.setFillColor(BLUE)
        self.canv.line(x1, y1, x2, y2)
        if x1 == x2:
            self.canv.line(x2, y2, x2 - 1.5 * mm, y2 + 2 * mm)
            self.canv.line(x2, y2, x2 + 1.5 * mm, y2 + 2 * mm)
        elif x2 > x1:
            self.canv.line(x2, y2, x2 - 2 * mm, y2 + 1.5 * mm)
            self.canv.line(x2, y2, x2 - 2 * mm, y2 - 1.5 * mm)
        else:
            self.canv.line(x2, y2, x2 + 2 * mm, y2 + 1.5 * mm)
            self.canv.line(x2, y2, x2 + 2 * mm, y2 - 1.5 * mm)


def styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=sample["Title"],
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=32,
            textColor=colors.white,
            alignment=TA_LEFT,
            spaceAfter=7 * mm,
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=13,
            leading=18,
            textColor=colors.HexColor("#C9D8DF"),
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=sample["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=19,
            leading=23,
            textColor=INK,
            spaceBefore=4 * mm,
            spaceAfter=4 * mm,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=sample["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=BLUE,
            spaceBefore=5 * mm,
            spaceAfter=2.5 * mm,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "H3",
            parent=sample["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=INK,
            spaceBefore=3 * mm,
            spaceAfter=1.5 * mm,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=13.2,
            textColor=INK,
            alignment=TA_LEFT,
            spaceAfter=2.4 * mm,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=7.7,
            leading=10.2,
            textColor=MUTED,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12.5,
            leftIndent=5 * mm,
            firstLineIndent=-3.5 * mm,
            bulletIndent=1 * mm,
            textColor=INK,
            spaceAfter=1.3 * mm,
        ),
        "code": ParagraphStyle(
            "Code",
            parent=sample["Code"],
            fontName="Courier",
            fontSize=7.5,
            leading=10,
            leftIndent=4 * mm,
            rightIndent=4 * mm,
            borderColor=LINE,
            borderWidth=0.5,
            borderPadding=3 * mm,
            backColor=colors.HexColor("#F5F8F9"),
            textColor=INK,
            spaceBefore=2 * mm,
            spaceAfter=3 * mm,
        ),
    }


S = styles()


def cover(title: str, subtitle: str, code: str) -> list[Flowable]:
    logo = Image(str(LOGO), width=90 * mm, height=53 * mm, kind="proportional")
    meta = Table(
        [
            ["Dokumen", code],
            ["Versi produk", "MVP 0.1.0"],
            ["Tanggal", DOC_DATE.strftime("%d %B %Y")],
            ["Klasifikasi", "Dokumentasi produk"],
        ],
        colWidths=[32 * mm, 80 * mm],
    )
    meta.setStyle(
        TableStyle(
            [
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#3A505C")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return [
        Spacer(1, 16 * mm),
        logo,
        Spacer(1, 17 * mm),
        Paragraph(title, S["cover_title"]),
        Paragraph(subtitle, S["cover_subtitle"]),
        Spacer(1, 25 * mm),
        meta,
        PageBreak(),
    ]


def h1(text: str) -> Paragraph:
    return Paragraph(esc(text), S["h1"])


def h2(text: str) -> Paragraph:
    return Paragraph(esc(text), S["h2"])


def h3(text: str) -> Paragraph:
    return Paragraph(esc(text), S["h3"])


def p(text: str) -> Paragraph:
    return Paragraph(text, S["body"])


def bullets(items: Iterable[str]) -> list[Paragraph]:
    return [Paragraph(f"- {item}", S["bullet"]) for item in items]


def numbered(items: Iterable[str], start: int = 1) -> list[Paragraph]:
    return [Paragraph(f"<b>{index}.</b> {item}", S["bullet"]) for index, item in enumerate(items, start)]


def note(title: str, text: str, color=BLUE) -> Table:
    table = Table(
        [[Paragraph(f"<b>{esc(title)}</b><br/>{text}", S["body"])]],
        colWidths=[174 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F2F8FA")),
                ("BOX", (0, 0), (-1, -1), 0.6, color),
                ("LINEBEFORE", (0, 0), (0, -1), 3, color),
                ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5 * mm),
            ]
        )
    )
    return table


def data_table(headers: list[str], rows: list[list[object]], widths: list[float] | None = None) -> Table:
    data = [[Paragraph(f"<b>{esc(cell)}</b>", S["small"]) for cell in headers]]
    data.extend([[Paragraph(esc(cell), S["small"]) for cell in row] for row in rows])
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, LINE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F8F9")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2.5 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2.5 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 2.2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2 * mm),
            ]
        )
    )
    return table


def contents(rows: list[tuple[str, str]]) -> Table:
    return data_table(
        ["Bagian", "Isi"],
        [[number, title] for number, title in rows],
        [22 * mm, 152 * mm],
    )


def qr_drawing(value: str, size: float = 32 * mm) -> Drawing:
    widget = QrCodeWidget(value)
    x1, y1, x2, y2 = widget.getBounds()
    scale = size / max(x2 - x1, y2 - y1)
    drawing = Drawing(size, size, transform=[scale, 0, 0, scale, 0, 0])
    drawing.add(widget)
    return drawing


def page() -> PageBreak:
    return PageBreak()


def build_user_guide() -> Path:
    output = OUTPUT_DIR / "ERGoSIGHT-Panduan-Pengguna-MVP.pdf"
    doc = ProductDocTemplate(output, "Panduan Pengguna MVP", "ERG-UG-001")
    story: list[Flowable] = []
    story.extend(
        cover(
            "Panduan Pengguna",
            "Instalasi, pairing Raspberry Pi, registrasi worker, live assessment, session review, dan laporan PDF.",
            "ERG-UG-001",
        )
    )
    story += [h1("Daftar Isi")]
    story.append(
        contents(
            [
                ("1", "Ringkasan dan persiapan"),
                ("2", "Mengunduh dan memasang aplikasi"),
                ("3", "Akun dan login"),
                ("4", "Menyambungkan edge device"),
                ("5", "Discovery dan pairing"),
                ("6", "Worker registry dan foto enrollment"),
                ("7", "Menjalankan live assessment"),
                ("8", "Session review dan final scoring"),
                ("9", "History, dashboard, dan reports"),
                ("10", "Penghapusan data dan logout"),
                ("11", "Troubleshooting"),
                ("12", "Checklist operasional"),
            ]
        )
    )
    story += [Spacer(1, 5 * mm), h2("Alur Utama")]
    story.append(
        ProcessFlow(
            [
                "Install aplikasi",
                "Login atau Sign Up",
                "Hubungkan Raspberry Pi",
                "Scan dan Pair",
                "Add Worker",
                "Start Session",
                "Review bukti",
                "Download Report",
            ]
        )
    )
    story.append(
        note(
            "Posisi sistem",
            "ERGoSIGHT adalah alat screening ergonomi berbasis kamera. Keputusan akhir tetap memerlukan penilaian profesional, verifikasi kondisi kerja, dan konfirmasi input yang tidak dapat diamati kamera.",
            AMBER,
        )
    )

    story += [page(), h1("1. Ringkasan dan Persiapan")]
    story += [h2("1.1 Isi perangkat")]
    story += bullets(
        [
            "Laptop Windows 10/11 64-bit dengan hak administrator untuk instalasi.",
            "Raspberry Pi 5 edge device, AI HAT Hailo-8, kamera USB, media penyimpanan, adaptor daya, dan kabel LAN.",
            "Label perangkat yang memuat nama hotspot <b>ERGoSIGHT-CAM01</b> dan password WPA2.",
            "Installer <b>ERGoSIGHT-Setup-0.1.0.exe</b> dari tautan resmi.",
        ]
    )
    story += [h2("1.2 Kondisi area assessment")]
    story += bullets(
        [
            "Pasang kamera pada posisi stabil; seluruh tubuh worker terlihat dari kepala sampai kaki.",
            "Hindari backlight kuat, refleksi, dan objek yang menutup sendi utama.",
            "Gunakan jarak yang membuat worker memenuhi sebagian besar frame tanpa terpotong.",
            "Untuk multi-worker, pastikan ada jarak visual yang cukup dan minim saling menutupi.",
            "Foto enrollment sebaiknya menggunakan pakaian dan APD yang sama dengan kondisi kerja normal.",
        ]
    )
    story.append(note("Sebelum mulai", "Nyalakan Raspberry Pi dan tunggu sekitar 60-90 detik sampai edge agent serta jaringan siap."))

    story += [page(), h1("2. Mengunduh dan Memasang Aplikasi")]
    story += [h2("2.1 Unduh installer")]
    link = f'<link href="{INSTALLER_URL}" color="#0077A8"><u>Buka ERGoSIGHT installer di Google Drive</u></link>'
    download_table = Table(
        [[qr_drawing(INSTALLER_URL), Paragraph(f"<b>Installer resmi</b><br/>{link}<br/><br/>Nama file: ERGoSIGHT-Setup-0.1.0.exe", S["body"])]],
        colWidths=[42 * mm, 124 * mm],
    )
    download_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BOX", (0, 0), (-1, -1), 0.5, LINE), ("PADDING", (0, 0), (-1, -1), 4 * mm)]))
    story.append(download_table)
    story += [h2("2.2 Proses instalasi")]
    story += numbered(
        [
            "Unduh file lalu pastikan nama file berakhir dengan <b>.exe</b>.",
            "Klik dua kali installer. Pilih <b>Yes</b> pada dialog User Account Control.",
            "Jika Windows SmartScreen muncul, pilih <b>More info</b> lalu <b>Run anyway</b>. MVP ini belum ditandatangani dengan sertifikat code-signing komersial.",
            "Pilih folder instalasi atau gunakan lokasi default, lalu pilih <b>Install</b>.",
            "Setelah selesai, jalankan ERGoSIGHT dari Desktop atau Start Menu.",
        ]
    )
    story.append(
        note(
            "Tidak perlu memasang komponen tambahan",
            "Installer sudah membawa Electron, backend FastAPI, database SQLite, migrasi database, dan firewall rule private-network. Python, Node.js, dan PostgreSQL tidak diperlukan pada laptop user.",
            GREEN,
        )
    )
    story += [h2("2.3 Lokasi data")]
    story.append(p("Data produksi disimpan di <b>%APPDATA%\\ERGoSIGHT</b>. Upgrade atau uninstall tidak otomatis menghapus folder ini agar histori dan bukti assessment tidak hilang."))

    story += [page(), h1("3. Akun dan Login")]
    story += [h2("3.1 Membuat akun pertama")]
    story += numbered(
        [
            "Pada layar login pilih <b>Sign Up</b>.",
            "Isi <b>Email</b>, <b>Username</b>, <b>Full name</b>, <b>Password</b>, dan <b>Confirm password</b>.",
            "Pastikan indikator password menunjukkan kedua isian cocok.",
            "Pilih tombol pembuatan akun, lalu kembali ke halaman login.",
        ]
    )
    story += [h2("3.2 Login")]
    story += numbered(
        [
            "Masukkan username atau email dan password.",
            "Gunakan ikon mata untuk memeriksa karakter password bila perlu.",
            "Centang <b>Keep me logged in</b> hanya pada laptop yang dikendalikan oleh user bersangkutan.",
            "Pilih <b>Login</b>. Dashboard akan terbuka setelah backend lokal siap.",
        ]
    )
    story.append(note("Kepemilikan data", "Worker, device, session, review, analytics, dan report dibatasi berdasarkan akun yang sedang login."))

    story += [page(), h1("4. Menyambungkan Edge Device")]
    story += [h2("4.1 Opsi A - Kabel LAN langsung (direkomendasikan)")]
    story += numbered(
        [
            "Nyalakan Raspberry Pi dan sambungkan kabel Ethernet langsung ke laptop.",
            "Biarkan pengaturan IPv4 adapter Ethernet laptop pada <b>Obtain an IP address automatically</b>.",
            "Tidak perlu mengaktifkan Windows Internet Connection Sharing.",
            "Tunggu sampai laptop menerima alamat lokal. Edge device menggunakan <b>10.55.0.1</b>.",
            "Buka ERGoSIGHT, login, lalu buka menu <b>Devices</b>.",
        ]
    )
    story += [h2("4.2 Opsi B - Onboarding Wi-Fi")]
    story += numbered(
        [
            "Jika Raspberry Pi belum mengenal Wi-Fi lokasi, tunggu hotspot fallback aktif.",
            "Sambungkan laptop ke <b>ERGoSIGHT-CAM01</b> menggunakan password pada label perangkat.",
            "Buka menu <b>Devices</b>, lakukan scan, dan pair device.",
            "Pilih <b>Set up Wi-Fi</b>, pilih SSID tujuan, isi password, lalu pilih <b>Connect</b>.",
            "Sambungkan kembali laptop ke Wi-Fi tujuan yang sama.",
            "Jalankan <b>Scan LAN</b> agar aplikasi menemukan alamat baru Raspberry Pi.",
        ]
    )
    story.append(
        data_table(
            ["Mode", "Alamat edge", "Kapan digunakan", "Internet laptop"],
            [
                ["LAN langsung", "10.55.0.1:8765", "Operasi lapangan paling sederhana", "Tetap melalui Wi-Fi laptop"],
                ["Setup hotspot", "10.42.0.1:8765", "Memasukkan kredensial Wi-Fi baru", "Biasanya sementara terputus"],
                ["Wi-Fi bersama", "DHCP jaringan", "Operasi tanpa kabel setelah onboarding", "Mengikuti jaringan Wi-Fi"],
            ],
            [28 * mm, 36 * mm, 65 * mm, 45 * mm],
        )
    )

    story += [page(), h1("5. Discovery dan Pairing")]
    story += [h2("5.1 Pairing pertama")]
    story += numbered(
        [
            "Buka <b>Devices</b> dan pilih <b>Scan LAN</b>.",
            "Jika scan tidak menemukan device pada LAN langsung, isi <b>Manual edge IP</b> dengan <b>10.55.0.1</b> lalu pilih <b>Probe IP</b>.",
            "Pastikan device tampil pada bagian <b>Discovered Devices</b>.",
            "Pilih <b>Create pairing code</b>. Kode sementara akan muncul.",
            "Pada baris device yang ditemukan, pilih <b>Pair</b>.",
            "Tunggu pesan sukses dan pastikan device muncul pada <b>Camera Nodes</b>.",
            "Gunakan <b>Rename</b> untuk memberi nama operasional, misalnya Kamera Packing Line 2.",
        ]
    )
    story += [h2("5.2 Arti pairing code")]
    story.append(p("Pairing code adalah token sekali pakai dan berumur pendek untuk mengikat satu Raspberry Pi ke akun/backend lokal yang benar. Kode ini bukan password user dan bukan kredensial Wi-Fi. Setelah pairing selesai, edge menyimpan kredensial node sehingga proses ini tidak perlu diulang setiap sesi."))
    story.append(note("Keamanan", "Jangan membagikan pairing code di luar proses instalasi. Jika device dipindahkan ke akun lain, pilih Remove pada Camera Nodes lalu lakukan pairing ulang."))

    story += [page(), h1("6. Worker Registry dan Foto Enrollment")]
    story += [h2("6.1 Menambahkan worker")]
    story += numbered(
        [
            "Buka menu <b>Workers</b>.",
            "Pada <b>Add Worker</b>, isi Name. Employee number, Department, dan Position bersifat opsional tetapi direkomendasikan.",
            "Pilih <b>Add Worker</b> dan pastikan worker tampil pada registry.",
        ]
    )
    story += [h2("6.2 Foto full-body")]
    story += bullets(
        [
            "Upload tiga sudut: <b>Front</b>, <b>Left Side</b>, dan <b>Right Side</b>.",
            "Gunakan JPEG/PNG, seluruh tubuh terlihat, fokus baik, pencahayaan cukup, dan latar tidak ramai.",
            "Worker memakai pakaian kerja serta APD normal.",
            "Periksa label <b>Good</b> atau <b>Review</b>. Ganti foto jika kualitas dinilai rendah.",
        ]
    )
    story.append(note("Batas identitas", "Foto enrollment membantu referensi visual dan pengembangan candidate matching. Soft Re-ID pada MVP bukan identifikasi biometrik final; operator tetap mengonfirmasi identitas saat review.", AMBER))
    story += [h2("6.3 Status worker")]
    story += bullets(
        [
            "<b>Deactivate</b>: menyembunyikan worker dari pilihan aktif tanpa menghapus histori.",
            "<b>Activate</b>: mengaktifkan kembali worker.",
            "<b>Delete</b>: hanya untuk data yang belum memiliki histori session; gunakan Deactivate bila worker sudah pernah dinilai.",
        ]
    )

    story += [page(), h1("7. Menjalankan Live Assessment")]
    story += [h2("7.1 Memulai sesi")]
    story += numbered(
        [
            "Pastikan Camera Nodes menunjukkan device paired/online dan kamera terpasang.",
            "Buka <b>Live Assessment</b>.",
            "Pilih camera node dan isi catatan/nama sesi yang mudah dikenali.",
            "Pilih <b>Start Session</b>. Pipeline Hailo yang berat baru dijalankan pada tahap ini.",
            "Tunggu status camera running dan gambar live tampil.",
        ]
    )
    story += [h2("7.2 Kontrol live stream")]
    story.append(
        data_table(
            ["Kontrol", "Fungsi", "Rekomendasi"],
            [
                ["Camera", "Menyalakan/mematikan preview MJPEG", "Matikan jika bandwidth terbatas; deteksi tetap dapat berjalan"],
                ["Overlay", "Bounding box, skeleton, worker ID", "Aktifkan untuk verifikasi alignment"],
                ["FPS 4/8/12", "Kecepatan preview", "Gunakan 8 FPS sebagai default; turunkan ke 4 saat jaringan lambat"],
                ["Worker cards", "RULA/REBA provisional, confidence, sudut", "Pantau semua worker yang aktif dalam frame"],
            ],
            [28 * mm, 70 * mm, 76 * mm],
        )
    )
    story += [h2("7.3 Mengakhiri sesi")]
    story += numbered(
        [
            "Pastikan aktivitas yang dibutuhkan sudah terekam.",
            "Pilih <b>Stop Session</b>.",
            "Edge menghentikan inference dan kembali idle untuk menghemat resource.",
            "Session berpindah ke status <b>review_pending</b> dan tersedia di Session Review.",
        ]
    )
    story.append(note("Provisional score", "Angka live berasal dari pose yang terlihat kamera dan dapat berubah antar-frame. Jangan gunakan sebagai final sebelum bukti, identitas, load/force, activity, coupling, dan wrist twist dikonfirmasi."))

    story += [page(), h1("8. Session Review dan Final Scoring")]
    story += [h2("8.1 Memilih bukti")]
    story += numbered(
        [
            "Buka <b>Session Review</b> dan pilih session berstatus review_pending.",
            "Gunakan filter Worker, Event, Severity, Review, serta Sort untuk mencari kejadian penting.",
            "Klik event pada Event Timeline untuk membuka <b>Review Evidence</b>.",
            "Periksa snapshot, pose measurements, pose quality, durasi, dan score provisional.",
            "Jika snapshot belum tersedia, pilih <b>Capture Snapshot</b>; gunakan Recapture untuk mengganti bukti.",
        ]
    )
    story += [h2("8.2 Konfirmasi identitas")]
    story += numbered(
        [
            "Pilih worker pada <b>Worker Identity</b>.",
            "Bandingkan snapshot dengan foto enrollment bila diperlukan.",
            "Pilih <b>Confirm Identity</b>. Koreksi dapat dilakukan jika soft Re-ID salah.",
        ]
    )
    story += [h2("8.3 Review REBA")]
    story.append(
        data_table(
            ["Input", "Pilihan skor", "Dasar verifikasi"],
            [
                ["Load / Force", "0 sampai 3", "Berat beban, shock, atau rapid force"],
                ["Coupling", "0 sampai 3", "Kualitas pegangan: good sampai unacceptable"],
                ["Activity", "0 sampai 2", "Statis, berulang, rapid change, atau kombinasi"],
            ],
            [38 * mm, 42 * mm, 94 * mm],
        )
    )
    story += [h2("8.4 Review RULA")]
    story.append(
        data_table(
            ["Input", "Pilihan skor", "Dasar verifikasi"],
            [
                ["Force / Load", "0 sampai 3", "Beban intermiten, statis, berulang, atau shock"],
                ["Wrist Twist", "1 atau 2", "Mid-range atau near end-range"],
                ["Muscle Use", "0 atau 1", "Postur statis atau gerakan berulang"],
            ],
            [38 * mm, 42 * mm, 94 * mm],
        )
    )
    story += numbered(
        [
            "Pilih tab REBA atau RULA.",
            "Isi semua parameter manual berdasarkan observasi dan bukti.",
            "Tambahkan Review Notes untuk kondisi yang memengaruhi interpretasi.",
            "Pilih <b>Save REBA Review</b> dan/atau <b>Save RULA Review</b>.",
            "Periksa <b>Reviewed Final</b> dan Score Breakdown.",
            "Setelah event penting selesai, pilih <b>Complete Review</b>.",
        ]
    )

    story += [page(), h1("9. History, Dashboard, dan Reports")]
    story += [h2("9.1 Dashboard")]
    story += bullets(
        [
            "Menampilkan jumlah device paired, sesi berjalan, worker, exposure, dan ringkasan risiko.",
            "Gunakan rentang analytics untuk melihat tren periode yang relevan.",
            "Klik Devices jika perangkat belum tersambung atau perlu diperiksa.",
        ]
    )
    story += [h2("9.2 History")]
    story += bullets(
        [
            "Menampilkan sesi yang tersimpan beserta statusnya.",
            "Session running tidak dapat dihapus.",
            "Hapus hanya rekaman uji atau assessment yang dipastikan tidak diperlukan.",
        ]
    )
    story += [h2("9.3 Membuat dan mengunduh report")]
    story += numbered(
        [
            "Buka menu <b>Reports</b>.",
            "Pilih session yang sudah berhenti atau selesai direview.",
            "Pilih <b>Generate PDF</b>.",
            "Tunggu pesan <b>Report PDF generated</b>.",
            "Pada Generated Reports, periksa jumlah worker, event, dan reviewed assessment.",
            "Pilih <b>Download</b> dan tentukan lokasi penyimpanan file.",
        ]
    )
    story.append(note("Isi report", "Report memuat ringkasan session, worker, reviewed RULA/REBA, parameter manual, event risiko, dan snapshot yang tersedia."))

    story += [page(), h1("10. Penghapusan Data dan Logout")]
    story.append(
        data_table(
            ["Objek", "Aksi", "Dampak"],
            [
                ["Session", "Delete Session / Delete di History", "Menghapus detection, review, snapshot, dan relasi session terkait"],
                ["Worker", "Delete", "Ditolak bila masih memiliki histori; gunakan Deactivate"],
                ["Device", "Remove", "Mencabut device dari akun; pairing ulang diperlukan"],
                ["Enrollment photo", "Remove", "Menghapus satu foto view worker"],
                ["Login session", "Logout", "Mengakhiri akses aplikasi pada akun aktif"],
            ],
            [32 * mm, 50 * mm, 92 * mm],
        )
    )
    story.append(note("Peringatan", "Penghapusan session bersifat permanen. Pastikan report atau bukti yang diperlukan sudah diunduh sebelum konfirmasi Delete.", RED))

    story += [page(), h1("11. Troubleshooting")]
    story.append(
        data_table(
            ["Gejala", "Pemeriksaan", "Tindakan"],
            [
                ["Aplikasi tidak terbuka", "Shortcut dan proses ERGoSIGHT", "Restart aplikasi; bila perlu jalankan sebagai administrator sekali"],
                ["Cannot reach backend", "%APPDATA%\\ERGoSIGHT\\logs\\backend.log", "Tutup semua instance, buka ulang; pastikan port 8000 tidak dipakai aplikasi lain"],
                ["Device tidak ditemukan", "Daya Pi, LED, kabel, adapter DHCP", "Scan ulang; Probe IP 10.55.0.1; nonaktifkan Internet Connection Sharing"],
                ["Hotspot tidak muncul", "Waktu boot dan saved Wi-Fi", "Tunggu lebih dari 60 detik; hotspot hanya fallback saat Wi-Fi tersimpan gagal"],
                ["Pairing gagal", "Pairing code dan backend URL", "Buat code baru; pastikan laptop dan Pi masih saling terhubung"],
                ["Kamera fallback demo", "Kabel USB dan device camera", "Pasang ulang kamera sebelum start session; restart Pi jika device terkunci"],
                ["Stream lag", "FPS, kualitas Wi-Fi, jumlah worker", "Turunkan preview ke 4 FPS atau gunakan LAN langsung"],
                ["Overlay waiting", "Pipeline detection dan session status", "Pastikan session running; tunggu inference; perbaiki framing/pencahayaan"],
                ["ID worker berubah", "Occlusion dan durasi keluar frame", "Konfirmasi identitas saat review; kurangi occlusion; soft Re-ID TTL sekitar 10 detik"],
                ["Report kosong", "Status review dan event", "Simpan review event serta Complete Review sebelum generate ulang"],
            ],
            [43 * mm, 52 * mm, 79 * mm],
        )
    )

    story += [page(), h1("12. Checklist Operasional")]
    story += [h2("Sebelum assessment")]
    story += bullets(
        [
            "[ ] Raspberry Pi, Hailo, kamera, dan adaptor daya terpasang.",
            "[ ] Laptop dan edge terhubung melalui LAN langsung atau Wi-Fi yang sama.",
            "[ ] Device berstatus paired/online.",
            "[ ] Worker dan foto enrollment sudah diperiksa.",
            "[ ] Kamera stabil, full-body terlihat, pencahayaan cukup.",
        ]
    )
    story += [h2("Saat assessment")]
    story += bullets(
        [
            "[ ] Session name/notes menjelaskan lokasi dan aktivitas.",
            "[ ] Overlay sejajar dengan tubuh dan worker ID terlihat.",
            "[ ] Stream stabil; FPS diturunkan bila jaringan terbatas.",
            "[ ] Seluruh aktivitas representatif sudah terekam.",
        ]
    )
    story += [h2("Setelah assessment")]
    story += bullets(
        [
            "[ ] Session dihentikan dan edge kembali idle.",
            "[ ] Identitas worker dikonfirmasi.",
            "[ ] Snapshot dan pose quality diperiksa.",
            "[ ] Input manual RULA/REBA disimpan.",
            "[ ] Review diselesaikan dan report diunduh.",
        ]
    )
    story.append(Spacer(1, 8 * mm))
    story.append(p(f"<b>Dukungan teknis:</b> sertakan versi aplikasi, session code, waktu kejadian, foto layar, dan file log dari %APPDATA%\\ERGoSIGHT\\logs. Installer: {link}"))

    doc.build(story)
    return output


def build_technical_document() -> Path:
    output = OUTPUT_DIR / "ERGoSIGHT-Dokumen-Teknis-MVP.pdf"
    doc = ProductDocTemplate(output, "Dokumen Teknis MVP", "ERG-TS-001")
    story: list[Flowable] = []
    story.extend(
        cover(
            "Dokumen Teknis",
            "Spesifikasi sistem, arsitektur, network topology, data flow, scoring, keamanan, deployment, dan batasan ERGoSIGHT MVP.",
            "ERG-TS-001",
        )
    )
    story += [h1("Daftar Isi")]
    story.append(
        contents(
            [
                ("1", "Tujuan dan ruang lingkup MVP"),
                ("2", "Spesifikasi hardware dan software"),
                ("3", "Arsitektur sistem"),
                ("4", "Network topology, discovery, dan pairing"),
                ("5", "Edge AI pipeline dan streaming"),
                ("6", "Backend, API, dan persistence"),
                ("7", "Electron desktop dan packaging"),
                ("8", "RULA/REBA scoring dan event engine"),
                ("9", "Security dan data ownership"),
                ("10", "Performance, reliability, dan observability"),
                ("11", "Deployment dan maintenance"),
                ("12", "Batasan, risiko, dan roadmap"),
            ]
        )
    )
    story += [Spacer(1, 5 * mm), h2("System Context")]
    story.append(ProcessFlow(["USB Camera", "Pi 5 + Hailo-8", "FastAPI Backend", "Electron UI"], columns=4))
    story.append(note("Design principle", "Edge menangani capture dan inference; backend menjadi system of record serta scoring authority; Electron hanya mengakses data melalui API."))

    story += [page(), h1("1. Tujuan dan Ruang Lingkup MVP")]
    story.append(p("ERGoSIGHT MVP adalah sistem assessment ergonomi lokal untuk satu Raspberry Pi edge node, satu kamera, dan satu laptop operator. Sistem dirancang offline-first pada jaringan lokal dan disiapkan untuk perkembangan multi-camera tanpa memasukkan kompleksitas tersebut ke alur MVP."))
    story += [h2("1.1 Kapabilitas utama")]
    story += bullets(
        [
            "JWT/Bearer authentication dan data ownership per user.",
            "Discovery, pairing, rename, revocation, dan Wi-Fi onboarding edge device.",
            "Hailo YOLO pose, body tracking, soft Re-ID, hand landmarks, dan MJPEG overlay.",
            "Live assessment multi-worker dengan provisional RULA/REBA.",
            "Session review, snapshot evidence, manual scoring, analytics, dan PDF report.",
            "Heavy inference hanya berjalan ketika session terautentikasi aktif.",
        ]
    )
    story += [h2("1.2 Di luar MVP")]
    story += bullets(
        [
            "Multi-camera 3D pose reconstruction dan cross-camera Re-ID.",
            "Biometric identity confirmation tanpa operator.",
            "Cloud synchronization, organization RBAC, fleet OTA, dan centralized monitoring.",
            "Medical diagnosis atau pengganti professional ergonomic assessment.",
        ]
    )

    story += [page(), h1("2. Spesifikasi Hardware dan Software")]
    story += [h2("2.1 Edge node yang divalidasi")]
    story.append(
        data_table(
            ["Komponen", "Spesifikasi"],
            [
                ["Compute", "Raspberry Pi 5, RAM 8 GB"],
                ["AI accelerator", "Hailo-8 PCIe, HailoRT/Firmware 4.23"],
                ["Storage", "NVMe 256 GB"],
                ["OS", "Debian GNU/Linux 13 Trixie, kernel Raspberry Pi 6.12 (2712)"],
                ["Camera", "USB camera, default /dev/video0"],
                ["Inference model", "YOLOv8m pose HEF for Hailo-8"],
                ["Hand model", "MediaPipe hand landmark lite via ai-edge-litert"],
                ["Networking", "Gigabit Ethernet and 2.4/5 GHz Wi-Fi"],
            ],
            [46 * mm, 128 * mm],
        )
    )
    story += [h2("2.2 Desktop target")]
    story.append(
        data_table(
            ["Komponen", "Minimum MVP", "Rekomendasi"],
            [
                ["OS", "Windows 10/11 64-bit", "Windows 11 terbaru"],
                ["CPU", "Dual-core x64", "4 core atau lebih"],
                ["RAM", "4 GB", "8 GB atau lebih"],
                ["Disk", "500 MB aplikasi + data", "Ruang tambahan sesuai snapshot/report"],
                ["Network", "Ethernet atau Wi-Fi", "LAN langsung untuk assessment panjang"],
                ["Privilege", "Administrator saat install", "Standard user saat operasi"],
            ],
            [38 * mm, 58 * mm, 78 * mm],
        )
    )
    story += [h2("2.3 Software stack")]
    story.append(
        data_table(
            ["Layer", "Teknologi", "Peran"],
            [
                ["Desktop", "Electron 43, React 19, TypeScript, Vite, Material UI", "Operator UX dan IPC"],
                ["Backend", "Python 3.12, FastAPI, Uvicorn, Pydantic", "REST, WebSocket, services"],
                ["Persistence", "SQLAlchemy, Alembic, SQLite production-local", "System of record"],
                ["Edge", "Python 3.13, Hailo Apps/GStreamer, OpenCV/Pillow", "Capture, inference, overlay"],
                ["Packaging", "PyInstaller onedir, electron-builder, NSIS", "Single Windows installer"],
                ["Reports", "ReportLab", "Session PDF generation"],
            ],
            [32 * mm, 75 * mm, 67 * mm],
        )
    )

    story += [page(), h1("3. Arsitektur Sistem")]
    architecture = data_table(
        ["Komponen", "Tanggung jawab", "Tidak dilakukan"],
        [
            ["Edge agent", "Discovery, pairing, Wi-Fi, lifecycle detection, stream", "Menyimpan histori authoritative"],
            ["Detection pipeline", "Pose, tracking, soft Re-ID, hand landmarks, payload", "Final manual scoring"],
            ["Backend", "Auth, ownership, sessions, scoring, events, analytics, reports", "Mengakses kamera secara langsung"],
            ["Electron", "Workflow operator, live view, review, download", "Akses database langsung"],
            ["SQLite/media", "Metadata transaksional dan bukti file", "Sinkronisasi cloud"],
        ],
        [34 * mm, 88 * mm, 52 * mm],
    )
    story.append(architecture)
    story += [h2("3.1 Runtime data flow")]
    story.append(ProcessFlow(["Start session API", "Start edge process", "Pose payload WebSocket", "Persist + score", "Live hub update", "Review + report"], columns=3))
    story += [h2("3.2 Session state machine")]
    story.append(ProcessFlow(["created", "running", "review_pending", "completed"], columns=4))
    story += bullets(
        [
            "Start mengaktifkan detection process pada paired camera node.",
            "Stop menyelesaikan event aktif, menghentikan inference, dan membuat session review_pending.",
            "Complete Review menandai hasil telah dikonfirmasi operator.",
            "Session non-running dapat dihapus bersama child data dan media terkait.",
        ]
    )

    story += [page(), h1("4. Network Topology, Discovery, dan Pairing")]
    story += [h2("4.1 Direct LAN")]
    story.append(p("Raspberry Pi menjalankan profile <b>ERGoSIGHT Direct LAN</b> pada 10.55.0.1/24 dan DHCP melalui dnsmasq. DHCP tidak mengiklankan default gateway atau DNS, sehingga internet laptop tetap menggunakan interface Wi-Fi. Edge API tersedia pada TCP 8765; backend desktop pada TCP 8000."))
    story += [h2("4.2 Setup hotspot")]
    story.append(p("Jika tidak ada saved Wi-Fi yang berhasil tersambung sekitar 60 detik setelah boot, service fallback mengaktifkan SSID <b>ERGoSIGHT-CAM01</b> pada 10.42.0.1. Password WPA2 dibuat saat provisioning dan ditempel pada label fisik perangkat."))
    story += [h2("4.3 Discovery")]
    story += bullets(
        [
            "Primary: Electron melakukan LAN subnet probing terhadap <b>/pairing/info</b>.",
            "Known direct-LAN fallback: probe manual <b>http://10.55.0.1:8765</b>.",
            "Service identity internal tetap <b>ergoquipt-edge</b> untuk kompatibilitas protocol.",
            "Edge base URL disimpan pada camera node setelah discovery/pairing.",
        ]
    )
    story += [h2("4.4 Pairing trust flow")]
    story.append(ProcessFlow(["JWT user", "Create short-lived code", "Send code to edge", "Edge completes with backend", "Store node credential", "Authorize session"], columns=3))
    story.append(note("Control plane", "Edge agent ringan selalu tersedia. Detection plane hanya dimulai melalui command session yang berasal dari backend terautentikasi."))

    story += [page(), h1("5. Edge AI Pipeline dan Streaming")]
    story.append(ProcessFlow(["USB frame", "Hailo YOLO pose", "Tracker", "Soft Re-ID", "Hand landmarks", "Angles + scores", "Overlay", "WebSocket"], columns=4))
    story += [h2("5.1 Default runtime tuning")]
    story.append(
        data_table(
            ["Parameter", "Default", "Tujuan"],
            [
                ["Camera", "640 x 360 @ 12 FPS", "Capture dan preview efisien"],
                ["Inference frame", "8 FPS", "Pose update"],
                ["Event publish", "4 FPS", "Membatasi backend traffic"],
                ["Re-ID signature", "2 FPS", "Mengurangi crop/descriptor cost"],
                ["Hand landmark", "3 FPS", "Wrist refinement tanpa full-frame model"],
                ["Soft Re-ID TTL", "10 detik", "Menjaga ID pada kehilangan singkat"],
                ["Track grace", "1.5 detik", "Meredam tracking miss"],
                ["Preview quality", "JPEG 65", "Trade-off bandwidth/visual"],
            ],
            [48 * mm, 38 * mm, 88 * mm],
        )
    )
    story += [h2("5.2 Pose dan hand model")]
    story.append(p("Hailo COCO17 menyediakan body joints sampai wrist. Hand landmark lite dijalankan hanya pada crop sekitar pergelangan untuk memperkirakan arah telapak dan flexion/extension. Wrist twist aksial tetap manual karena ambigu pada single 2D view."))
    story += [h2("5.3 Soft Re-ID")]
    story.append(p("Tracker ID digabung dengan signature warna/appearance torso dan batas temporal-spasial. Output <b>REID_xxxx</b> menjaga kontinuitas jangka pendek, tetapi bukan bukti identitas personal. Registry assignment tetap dikonfirmasi operator."))
    story += [h2("5.4 Stream")]
    story += bullets(
        [
            "MJPEG endpoint: <b>GET /stream/mjpeg</b> dengan width, height, fps, quality, dan overlay.",
            "Overlay memakai detection terbaru yang masih fresh agar koordinat tidak tertinggal jauh.",
            "Preview dapat dimatikan tanpa menghentikan detection process.",
            "Demo stream hanya fallback ketika physical camera tidak dapat dibuka.",
        ]
    )

    story += [page(), h1("6. Backend, API, dan Persistence")]
    story += [h2("6.1 Service modules")]
    story.append(
        data_table(
            ["Service", "Fungsi"],
            [
                ["detection_ingest", "Validasi payload, ownership camera/session, persistence detection"],
                ["live_hub", "Fan-out update live ke desktop subscribers"],
                ["event_engine", "Presence, high-risk, sustained posture, hysteresis"],
                ["scoring", "Pure RULA/REBA lookup dan component breakdown"],
                ["snapshot_capture", "Menyimpan bukti frame dan relasi event"],
                ["exposure_analytics", "Durasi high-risk dan agregasi worker/session"],
                ["report_generation", "Membangun PDF audit session"],
            ],
            [46 * mm, 128 * mm],
        )
    )
    story += [h2("6.2 REST API summary")]
    story.append(
        data_table(
            ["Area", "Endpoint utama"],
            [
                ["Auth", "POST /auth/register, /auth/login, /auth/refresh; GET /auth/me"],
                ["Devices", "GET/PATCH/DELETE /camera-nodes; POST /device-pairings"],
                ["Workers", "GET/POST/PATCH/DELETE /workers; enrollment image endpoints"],
                ["Sessions", "POST/GET/DELETE /sessions; start, stop, complete, events, summary"],
                ["Review", "Event detail, review upsert, snapshot capture/content"],
                ["Analytics", "GET /analytics/overview"],
                ["Reports", "List, generate session PDF, download content"],
                ["Scoring", "POST /scoring/preview"],
            ],
            [34 * mm, 140 * mm],
        )
    )
    story += [h2("6.3 Data model")]
    story.append(
        data_table(
            ["Entity", "Relasi dan isi utama"],
            [
                ["users / refresh_tokens", "Account identity dan refresh token lifecycle"],
                ["camera_nodes / device_pairings", "Ownership, credential, status, edge base URL"],
                ["workers / enrollment_images", "Registry dan foto front/left/right private"],
                ["sessions / session_workers", "Lifecycle assessment dan mapping edge ID ke registry"],
                ["detections", "Pose payload, bbox, confidence, frame/timestamp"],
                ["ergonomic_events", "Presence, risk transition, duration, score statistics"],
                ["assessments / review_items", "Provisional/final score, manual inputs, notes"],
                ["snapshots / reports", "File metadata, evidence, generated PDF"],
            ],
            [48 * mm, 126 * mm],
        )
    )
    story += [page(), h1("7. Electron Desktop dan Packaging")]
    story += [h2("7.1 UI boundaries")]
    story += bullets(
        [
            "React renderer tidak memiliki akses database atau filesystem bebas.",
            "Electron preload mengekspos IPC yang dibatasi untuk discovery, pairing, network setup, dan lifecycle lokal.",
            "REST request menggunakan Bearer token; media private diambil sebagai authenticated blob.",
            "Menu operasional: Dashboard, Live Assessment, Session Review, History, Workers, Reports, Devices.",
        ]
    )
    story += [h2("7.2 Installer composition")]
    story.append(ProcessFlow(["Vite bundle", "PyInstaller backend", "Electron resources", "NSIS setup.exe"], columns=4))
    story.append(
        data_table(
            ["Item", "Implementasi"],
            [
                ["App binary", "Electron packaged as ASAR + runtime"],
                ["Backend binary", "PyInstaller onedir: ergosight-backend.exe"],
                ["Database", "Alembic upgrade head saat backend start"],
                ["User data", "%APPDATA%\\ERGoSIGHT"],
                ["JWT secret", "Random 48-byte secret, persisted pada user data"],
                ["Firewall", "Private-network inbound TCP 8000 untuk edge callback/WebSocket"],
                ["Process lifecycle", "Backend child process start before window dan stop on quit"],
                ["Installer", "NSIS per-machine, shortcut Desktop/Start Menu"],
            ],
            [42 * mm, 132 * mm],
        )
    )
    story.append(note("Distribution gap", "MVP installer belum code-signed. Produksi komersial perlu EV/OV Authenticode certificate dan release pipeline yang menandatangani setup.exe serta application binary.", AMBER))

    story += [page(), h1("8. RULA/REBA Scoring dan Event Engine")]
    story += [h2("8.1 Scoring authority")]
    story.append(p("Edge mengirim angles dan dapat menyertakan provisional score untuk live feedback. Backend menghitung ulang menggunakan lookup tables dan menjadi authority untuk review/final score. Component breakdown disimpan agar hasil dapat diaudit."))
    story += [h2("8.2 REBA")]
    story.append(p("Secara konseptual: <b>A = TableA(trunk, neck, legs) + load</b>; <b>B = TableB(upper arm, lower arm, wrist) + coupling</b>; kemudian <b>REBA = TableC(A, B) + activity</b>."))
    story.append(
        data_table(
            ["REBA", "Risk level", "Interpretasi screening"],
            [
                ["1", "Negligible", "Risiko dapat diabaikan"],
                ["2-3", "Low", "Perubahan mungkin diperlukan"],
                ["4-7", "Medium", "Investigasi dan perubahan"],
                ["8-10", "High", "Investigasi dan perubahan segera"],
                ["11+", "Very High", "Tindakan sangat segera"],
            ],
            [28 * mm, 48 * mm, 98 * mm],
        )
    )
    story += [h2("8.3 RULA")]
    story.append(p("Secara konseptual: <b>A = TableA(upper arm, lower arm, wrist, twist) + muscle + force</b>; <b>B = TableB(neck, trunk, legs) + muscle + force</b>; kemudian <b>RULA = TableC(A, B)</b>."))
    story.append(
        data_table(
            ["RULA", "Risk level", "Interpretasi screening"],
            [
                ["1-2", "Acceptable", "Dapat diterima bila tidak dipertahankan/berulang lama"],
                ["3-4", "Further Investigate", "Perlu investigasi lebih lanjut"],
                ["5-6", "Investigate Soon", "Investigasi dan perubahan dalam waktu dekat"],
                ["7", "Investigate Immediately", "Investigasi dan perubahan segera"],
            ],
            [28 * mm, 56 * mm, 90 * mm],
        )
    )
    story += [h2("8.4 Observable vs manual")]
    story.append(
        data_table(
            ["Kategori", "Dari kamera", "Konfirmasi operator"],
            [
                ["Body posture", "Neck, trunk, arm, elbow, legs dari 2D pose", "Twist/bend yang ambigu atau tertutup"],
                ["Wrist", "Flexion/extension dari hand landmarks bila kualitas cukup", "Axial wrist twist"],
                ["Task context", "Tidak dapat diandalkan", "Load/force, coupling, activity/muscle use"],
                ["Identity", "Soft Re-ID candidate", "Registry identity final"],
            ],
            [35 * mm, 72 * mm, 67 * mm],
        )
    )
    story += [h2("8.5 Event engine")]
    story.append(p("Presence timeout 3 detik menghasilkan worker_entered/worker_left. High-risk dimulai pada REBA &gt;= 8 atau RULA &gt;= 5, memakai release grace 1 detik, dan menjadi sustained setelah 10 detik. Sum, count, peak, dan last score diakumulasi per worker serta assessment type."))

    story += [page(), h1("9. Security dan Data Ownership")]
    story.append(
        data_table(
            ["Kontrol", "Implementasi MVP", "Catatan"],
            [
                ["Authentication", "JWT access + refresh token", "Password di-hash; API protected"],
                ["Authorization", "Owner user filter pada query", "Workers, sessions, devices, reports scoped"],
                ["Pairing", "Short-lived code + node credential", "User password tidak disimpan di edge"],
                ["Media", "Authenticated endpoint", "Enrollment/snapshot bukan public static URL"],
                ["Secret", "Random local JWT key", "Persisted di AppData"],
                ["Network", "Private LAN firewall rule", "MVP belum TLS pada jaringan lokal"],
                ["Persistence", "Local AppData", "Uninstall mempertahankan data"],
            ],
            [37 * mm, 72 * mm, 65 * mm],
        )
    )
    story += [h2("9.1 Threat considerations")]
    story += bullets(
        [
            "Physical access ke laptop atau Raspberry Pi dapat membuka risiko data lokal.",
            "HTTP lokal dapat disadap pada jaringan Wi-Fi tidak terpercaya; gunakan LAN langsung atau jaringan privat.",
            "Enrollment photo dan snapshot merupakan data personal operasional; terapkan retention policy dan akses minimum.",
            "Pairing code harus singkat masa berlaku dan tidak dicatat pada log permanen.",
            "Produksi enterprise memerlukan TLS/mTLS, OS disk encryption, signed installer, RBAC, dan audit log immutable.",
        ]
    )

    story += [page(), h1("10. Performance, Reliability, dan Observability")]
    story += [h2("10.1 Performance controls")]
    story += bullets(
        [
            "Capture, inference, event publishing, Re-ID, dan hand landmarks memiliki rate limit terpisah.",
            "MJPEG preview memakai latest-frame semantics agar frame lama tidak menumpuk.",
            "Frontend mengganti URL object dan state live, bukan menyimpan seluruh frame history.",
            "Heavy pipeline berhenti saat session stop; edge agent tetap ringan.",
            "Preview FPS dapat diturunkan tanpa mengubah event FPS.",
        ]
    )
    story += [h2("10.2 Reliability")]
    story += bullets(
        [
            "Systemd menjalankan edge agent, dnsmasq, dan Wi-Fi fallback saat boot.",
            "Backend menjalankan Alembic migration sebelum menerima request.",
            "Electron menunggu OpenAPI backend kompatibel sebelum membuka main window.",
            "Single-instance lock mencegah dua backend lokal bersaing pada port yang sama.",
            "Event lifecycle diselesaikan saat session stop untuk menjaga durasi konsisten.",
        ]
    )
    story += [h2("10.3 Logs dan health")]
    story.append(
        data_table(
            ["Target", "Lokasi / endpoint"],
            [
                ["Desktop backend log", "%APPDATA%\\ERGoSIGHT\\logs\\backend.log"],
                ["Desktop health", "GET http://127.0.0.1:8000/health"],
                ["OpenAPI compatibility", "GET http://127.0.0.1:8000/openapi.json"],
                ["Edge health", "GET http://EDGE_IP:8765/health"],
                ["Detection status", "GET /detection/status"],
                ["Stream status", "GET /stream/status"],
                ["Network status", "GET /network/status"],
                ["Pi service", "systemctl status ergoquipt-edge-agent"],
            ],
            [55 * mm, 119 * mm],
        )
    )

    story += [page(), h1("11. Deployment dan Maintenance")]
    story += [h2("11.1 Windows build")]
    story.append(Paragraph("cd desktop<br/>npm.cmd run dist:win", S["code"]))
    story += bullets(
        [
            "Script membangun backend PyInstaller, frontend Vite, Electron package, lalu NSIS installer.",
            "Output: <b>desktop\\installer\\ERGoSIGHT-Setup-0.1.0.exe</b>.",
            "Smoke test wajib memverifikasi packaged backend dan packaged Electron lifecycle.",
        ]
    )
    story += [h2("11.2 Edge deployment")]
    story.append(Paragraph("sudo ./systemd/install.sh<br/>sudo ./systemd/install-networking.sh", S["code"]))
    story += bullets(
        [
            "Edge source berada di /home/admin/RULA-REBA_Detection_HailoAI.",
            "Service identity file tetap ergoquipt-* untuk upgrade compatibility; nama produk yang terlihat user adalah ERGoSIGHT.",
            "Perubahan model atau Python package harus diuji terhadap Hailo Apps environment sebelum rollout.",
            "Hotspot password harus disimpan pada inventory/label perangkat dan tidak di-hardcode pada repository.",
        ]
    )
    story += [h2("11.3 Backup dan retention")]
    story += bullets(
        [
            "Backup folder %APPDATA%\\ERGoSIGHT saat aplikasi tertutup.",
            "Sertakan ergosight.sqlite3, media, reports, logs, dan .jwt-secret sebagai satu unit backup terenkripsi.",
            "Tetapkan retention snapshot/report sesuai kebijakan perusahaan dan regulasi privasi lokal.",
            "Uji restore pada workstation terpisah sebelum mengandalkan backup operasional.",
        ]
    )

    story += [page(), h1("12. Batasan, Risiko, dan Roadmap")]
    story.append(
        data_table(
            ["Batasan MVP", "Dampak", "Mitigasi saat ini", "Upgrade trigger"],
            [
                ["Single 2D camera", "Occlusion/depth ambiguity", "Framing, pose quality, manual review", "Need 3D accuracy or occluded task"],
                ["Soft Re-ID", "ID dapat berubah/tertukar", "TTL, appearance, operator confirmation", "Measured false-match unacceptable"],
                ["HTTP local", "LAN interception risk", "Private LAN/hotspot", "Enterprise deployment"],
                ["SQLite local", "Single workstation authority", "Single app instance, backup", "Multi-user/concurrent backend"],
                ["Unsigned installer", "SmartScreen warning", "Documented hash/source", "External customer release"],
                ["Manual task inputs", "Operator variation", "Evidence, notes, standard procedure", "Validated task-sensing method"],
            ],
            [39 * mm, 42 * mm, 52 * mm, 41 * mm],
        )
    )
    story += [h2("12.1 Prioritas lanjutan")]
    story += numbered(
        [
            "Field validation RULA/REBA terhadap assessor manusia dan worksheet resmi.",
            "Long-duration soak test, camera recovery, dan telemetry resource edge.",
            "Body appearance embedding berbasis enrollment dengan confidence gate.",
            "Signed installer, TLS/mTLS, RBAC, audit logging, dan encrypted backup.",
            "PostgreSQL/service mode bila backend berpindah dari satu workstation.",
            "Multi-camera calibration dan 3D fusion setelah single-camera acceptance terpenuhi.",
        ]
    )
    story.append(note("Validation requirement", "Sebelum digunakan sebagai dasar keputusan formal HSE, lakukan study agreement terhadap assessor tersertifikasi, uji variasi kamera/worker/APD, dan dokumentasikan confidence serta limitation per assessment.", RED))

    doc.build(story)
    return output


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in (build_user_guide(), build_technical_document()):
        print(path)


if __name__ == "__main__":
    main()
