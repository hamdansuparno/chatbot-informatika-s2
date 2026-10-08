#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APLIKASI LAPORAN KEUANGAN (satu file)
=====================================
Fitur:
  - CRUD transaksi (tambah, ubah, hapus) pemasukan & pengeluaran
  - Penyimpanan otomatis ke database SQLite (laporan.db)
  - Filter berdasarkan tanggal, jenis, dan kata kunci
  - Ringkasan total pemasukan / pengeluaran / saldo
  - Ringkasan per kategori + grafik batang per bulan
  - Ekspor ke CSV dan laporan HTML (bisa dicetak / disimpan jadi PDF dari browser)
  - Data contoh untuk mencoba aplikasi

Cara menjalankan:
    python aplikasi_laporan.py

Hanya memakai library bawaan Python (tkinter, sqlite3, csv), jadi tidak perlu instalasi tambahan.
"""

import csv
import html
import os
import sqlite3
import tempfile
import webbrowser
from datetime import date, datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

APP_TITLE = "Aplikasi Laporan Keuangan"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "laporan.db")

KATEGORI = {
    "Pemasukan": ["Gaji", "Penjualan", "Bonus", "Investasi", "Lainnya"],
    "Pengeluaran": ["Makan & Minum", "Transportasi", "Tagihan", "Pendidikan",
                    "Belanja", "Kesehatan", "Hiburan", "Lainnya"],
}
JENIS_LIST = ["Pemasukan", "Pengeluaran"]


# ----------------------------------------------------------------------
# Fungsi bantu
# ----------------------------------------------------------------------
def rupiah(angka):
    """Format angka ke 'Rp 1.234.567'."""
    angka = angka or 0
    teks = f"{abs(angka):,.0f}".replace(",", ".")
    return ("-Rp " if angka < 0 else "Rp ") + teks


def parse_angka(teks):
    """Ubah teks seperti 'Rp 1.500.000' atau '1500000,50' menjadi float."""
    bersih = teks.strip().lower().replace("rp", "").replace(" ", "")
    bersih = bersih.replace(".", "").replace(",", ".")
    return float(bersih)


def valid_tanggal(teks):
    """Validasi format YYYY-MM-DD. Mengembalikan string tanggal atau melempar ValueError."""
    return datetime.strptime(teks.strip(), "%Y-%m-%d").strftime("%Y-%m-%d")


# ----------------------------------------------------------------------
# Lapisan database
# ----------------------------------------------------------------------
class Database:
    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS transaksi (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   tanggal TEXT NOT NULL,
                   jenis TEXT NOT NULL CHECK (jenis IN ('Pemasukan','Pengeluaran')),
                   kategori TEXT NOT NULL,
                   keterangan TEXT,
                   jumlah REAL NOT NULL CHECK (jumlah >= 0)
               )"""
        )
        self.conn.commit()

    @staticmethod
    def _where(f):
        klausa, params = [], []
        if f.get("dari"):
            klausa.append("tanggal >= ?")
            params.append(f["dari"])
        if f.get("sampai"):
            klausa.append("tanggal <= ?")
            params.append(f["sampai"])
        if f.get("jenis") and f["jenis"] != "Semua":
            klausa.append("jenis = ?")
            params.append(f["jenis"])
        if f.get("cari"):
            klausa.append("(keterangan LIKE ? OR kategori LIKE ?)")
            kata = f"%{f['cari']}%"
            params += [kata, kata]
        sql = (" WHERE " + " AND ".join(klausa)) if klausa else ""
        return sql, params

    def tambah(self, tanggal, jenis, kategori, keterangan, jumlah):
        self.conn.execute(
            "INSERT INTO transaksi (tanggal, jenis, kategori, keterangan, jumlah) VALUES (?,?,?,?,?)",
            (tanggal, jenis, kategori, keterangan, jumlah),
        )
        self.conn.commit()

    def ubah(self, id_, tanggal, jenis, kategori, keterangan, jumlah):
        self.conn.execute(
            "UPDATE transaksi SET tanggal=?, jenis=?, kategori=?, keterangan=?, jumlah=? WHERE id=?",
            (tanggal, jenis, kategori, keterangan, jumlah, id_),
        )
        self.conn.commit()

    def hapus(self, id_):
        self.conn.execute("DELETE FROM transaksi WHERE id=?", (id_,))
        self.conn.commit()

    def hapus_semua(self):
        self.conn.execute("DELETE FROM transaksi")
        self.conn.commit()

    def ambil(self, f):
        where, params = self._where(f)
        cur = self.conn.execute(
            f"SELECT * FROM transaksi{where} ORDER BY tanggal DESC, id DESC", params
        )
        return cur.fetchall()

    def ringkasan_kategori(self, f):
        where, params = self._where(f)
        cur = self.conn.execute(
            f"""SELECT jenis, kategori, SUM(jumlah) AS total, COUNT(*) AS n
                FROM transaksi{where}
                GROUP BY jenis, kategori
                ORDER BY jenis, total DESC""",
            params,
        )
        return cur.fetchall()

    def ringkasan_bulanan(self, f):
        where, params = self._where(f)
        cur = self.conn.execute(
            f"""SELECT substr(tanggal,1,7) AS bulan,
                       SUM(CASE WHEN jenis='Pemasukan'  THEN jumlah ELSE 0 END) AS masuk,
                       SUM(CASE WHEN jenis='Pengeluaran' THEN jumlah ELSE 0 END) AS keluar
                FROM transaksi{where}
                GROUP BY bulan ORDER BY bulan""",
            params,
        )
        return cur.fetchall()

    def isi_contoh(self):
        import random
        random.seed(7)
        hari_ini = date.today()
        data = []
        for i in range(90):
            tgl = (hari_ini - timedelta(days=i)).strftime("%Y-%m-%d")
            if i % 30 == 0:
                data.append((tgl, "Pemasukan", "Gaji", "Gaji bulanan", 6_000_000))
            if i % 11 == 0:
                data.append((tgl, "Pemasukan", "Penjualan", "Penjualan barang",
                             random.randint(3, 15) * 100_000))
            kat = random.choice(KATEGORI["Pengeluaran"])
            data.append((tgl, "Pengeluaran", kat, f"Pembayaran {kat.lower()}",
                         random.randint(2, 40) * 10_000))
        self.conn.executemany(
            "INSERT INTO transaksi (tanggal, jenis, kategori, keterangan, jumlah) VALUES (?,?,?,?,?)",
            data,
        )
        self.conn.commit()
        return len(data)


# ----------------------------------------------------------------------
# Pembuat laporan (CSV & HTML)
# ----------------------------------------------------------------------
def hitung_total(rows):
    masuk = sum(r["jumlah"] for r in rows if r["jenis"] == "Pemasukan")
    keluar = sum(r["jumlah"] for r in rows if r["jenis"] == "Pengeluaran")
    return masuk, keluar, masuk - keluar


def ekspor_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["ID", "Tanggal", "Jenis", "Kategori", "Keterangan", "Jumlah"])
        for r in rows:
            w.writerow([r["id"], r["tanggal"], r["jenis"], r["kategori"],
                        r["keterangan"] or "", int(r["jumlah"])])
        masuk, keluar, saldo = hitung_total(rows)
        w.writerow([])
        w.writerow(["", "", "", "", "Total Pemasukan", int(masuk)])
        w.writerow(["", "", "", "", "Total Pengeluaran", int(keluar)])
        w.writerow(["", "", "", "", "Saldo", int(saldo)])


def buat_html(rows, ringkasan_kat, periode):
    masuk, keluar, saldo = hitung_total(rows)
    e = html.escape
    baris = "".join(
        f"<tr><td>{i}</td><td>{e(r['tanggal'])}</td>"
        f"<td class='{r['jenis'].lower()}'>{e(r['jenis'])}</td>"
        f"<td>{e(r['kategori'])}</td><td>{e(r['keterangan'] or '')}</td>"
        f"<td class='num'>{rupiah(r['jumlah'])}</td></tr>"
        for i, r in enumerate(rows, 1)
    )
    baris_kat = "".join(
        f"<tr><td>{e(r['jenis'])}</td><td>{e(r['kategori'])}</td>"
        f"<td class='num'>{r['n']}</td><td class='num'>{rupiah(r['total'])}</td></tr>"
        for r in ringkasan_kat
    )
    return f"""<!DOCTYPE html>
<html lang="id"><head><meta charset="utf-8"><title>Laporan Keuangan</title>
<style>
 body{{font-family:Segoe UI,Arial,sans-serif;margin:32px;color:#222}}
 h1{{margin:0}} .sub{{color:#666;margin-bottom:20px}}
 table{{border-collapse:collapse;width:100%;margin:12px 0 28px}}
 th,td{{border:1px solid #ccc;padding:6px 10px;font-size:13px;text-align:left}}
 th{{background:#f0f3f7}} .num{{text-align:right}}
 .pemasukan{{color:#1a7f37}} .pengeluaran{{color:#c0392b}}
 .kartu{{display:flex;gap:16px;margin:16px 0}}
 .kartu div{{flex:1;border:1px solid #ddd;border-radius:8px;padding:12px}}
 .kartu b{{display:block;font-size:20px;margin-top:4px}}
 @media print{{body{{margin:12px}}}}
</style></head><body>
<h1>Laporan Keuangan</h1>
<div class="sub">Periode: {e(periode)} &middot; Dicetak: {datetime.now():%d-%m-%Y %H:%M}</div>
<div class="kartu">
  <div>Total Pemasukan<b class="pemasukan">{rupiah(masuk)}</b></div>
  <div>Total Pengeluaran<b class="pengeluaran">{rupiah(keluar)}</b></div>
  <div>Saldo<b>{rupiah(saldo)}</b></div>
</div>
<h2>Ringkasan per Kategori</h2>
<table><tr><th>Jenis</th><th>Kategori</th><th>Jumlah Transaksi</th><th>Total</th></tr>{baris_kat}</table>
<h2>Rincian Transaksi ({len(rows)} data)</h2>
<table><tr><th>No</th><th>Tanggal</th><th>Jenis</th><th>Kategori</th><th>Keterangan</th><th>Jumlah</th></tr>{baris}</table>
</body></html>"""


# ----------------------------------------------------------------------
# Antarmuka (GUI)
# ----------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1100x680")
        self.minsize(900, 560)
        self.db = Database(DB_PATH)
        self.selected_id = None
        self.rows = []

        self._style()
        self._menu()
        self._build()
        self.refresh()

    # ---------- tampilan dasar ----------
    def _style(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure("Treeview", rowheight=24)
        s.configure("Judul.TLabel", font=("Segoe UI", 11, "bold"))
        s.configure("Angka.TLabel", font=("Segoe UI", 13, "bold"))

    def _menu(self):
        bar = tk.Menu(self)
        m_file = tk.Menu(bar, tearoff=0)
        m_file.add_command(label="Ekspor CSV...", command=self.aksi_csv)
        m_file.add_command(label="Ekspor / Buka Laporan HTML", command=self.aksi_html)
        m_file.add_separator()
        m_file.add_command(label="Keluar", command=self.destroy)
        bar.add_cascade(label="File", menu=m_file)

        m_data = tk.Menu(bar, tearoff=0)
        m_data.add_command(label="Isi data contoh", command=self.aksi_contoh)
        m_data.add_command(label="Hapus semua data", command=self.aksi_hapus_semua)
        bar.add_cascade(label="Data", menu=m_data)

        m_help = tk.Menu(bar, tearoff=0)
        m_help.add_command(label="Tentang", command=lambda: messagebox.showinfo(
            "Tentang", f"{APP_TITLE}\nPython + Tkinter + SQLite\nDatabase: {DB_PATH}"))
        bar.add_cascade(label="Bantuan", menu=m_help)
        self.config(menu=bar)

    def _build(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)
        self.tab_data = ttk.Frame(nb)
        self.tab_ring = ttk.Frame(nb)
        nb.add(self.tab_data, text="  Data Transaksi  ")
        nb.add(self.tab_ring, text="  Ringkasan & Grafik  ")
        self._build_data()
        self._build_ringkasan()
        nb.bind("<<NotebookTabChanged>>", lambda e: self._gambar_grafik())

    # ---------- tab data ----------
    def _build_data(self):
        kiri = ttk.LabelFrame(self.tab_data, text="Form Transaksi", padding=10)
        kiri.pack(side="left", fill="y", padx=(0, 8), pady=4)

        self.v_tgl = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        self.v_jenis = tk.StringVar(value="Pemasukan")
        self.v_kat = tk.StringVar()
        self.v_ket = tk.StringVar()
        self.v_jml = tk.StringVar()

        def baris(r, teks, widget):
            ttk.Label(kiri, text=teks).grid(row=r, column=0, sticky="w", pady=4)
            widget.grid(row=r, column=1, sticky="ew", pady=4, padx=(8, 0))

        baris(0, "Tanggal (YYYY-MM-DD)", ttk.Entry(kiri, textvariable=self.v_tgl, width=24))
        cb_jenis = ttk.Combobox(kiri, textvariable=self.v_jenis, values=JENIS_LIST,
                                state="readonly", width=22)
        cb_jenis.bind("<<ComboboxSelected>>", lambda e: self._set_kategori())
        baris(1, "Jenis", cb_jenis)
        self.cb_kat = ttk.Combobox(kiri, textvariable=self.v_kat, width=22)
        baris(2, "Kategori", self.cb_kat)
        baris(3, "Keterangan", ttk.Entry(kiri, textvariable=self.v_ket, width=24))
        baris(4, "Jumlah (Rp)", ttk.Entry(kiri, textvariable=self.v_jml, width=24))
        self._set_kategori()

        tombol = ttk.Frame(kiri)
        tombol.grid(row=5, column=0, columnspan=2, pady=(14, 0), sticky="ew")
        for i, (t, c) in enumerate([("Tambah", self.aksi_tambah), ("Ubah", self.aksi_ubah),
                                    ("Hapus", self.aksi_hapus), ("Bersihkan", self.bersihkan)]):
            ttk.Button(tombol, text=t, command=c).grid(row=i // 2, column=i % 2,
                                                       padx=3, pady=3, sticky="ew")
            tombol.columnconfigure(i % 2, weight=1)

        kanan = ttk.Frame(self.tab_data)
        kanan.pack(side="left", fill="both", expand=True, pady=4)

        # filter
        fr = ttk.LabelFrame(kanan, text="Filter", padding=8)
        fr.pack(fill="x")
        self.f_dari = tk.StringVar()
        self.f_sampai = tk.StringVar()
        self.f_jenis = tk.StringVar(value="Semua")
        self.f_cari = tk.StringVar()
        ttk.Label(fr, text="Dari").grid(row=0, column=0)
        ttk.Entry(fr, textvariable=self.f_dari, width=12).grid(row=0, column=1, padx=4)
        ttk.Label(fr, text="Sampai").grid(row=0, column=2)
        ttk.Entry(fr, textvariable=self.f_sampai, width=12).grid(row=0, column=3, padx=4)
        ttk.Label(fr, text="Jenis").grid(row=0, column=4)
        ttk.Combobox(fr, textvariable=self.f_jenis, values=["Semua"] + JENIS_LIST,
                     state="readonly", width=12).grid(row=0, column=5, padx=4)
        ttk.Label(fr, text="Cari").grid(row=0, column=6)
        ent = ttk.Entry(fr, textvariable=self.f_cari, width=16)
        ent.grid(row=0, column=7, padx=4)
        ent.bind("<Return>", lambda e: self.refresh())
        ttk.Button(fr, text="Terapkan", command=self.refresh).grid(row=0, column=8, padx=4)
        ttk.Button(fr, text="Reset", command=self.reset_filter).grid(row=0, column=9)
        ttk.Label(fr, text="Format tanggal: YYYY-MM-DD (kosongkan jika tidak dipakai)",
                  foreground="#777").grid(row=1, column=0, columnspan=10, sticky="w", pady=(4, 0))

        # tabel
        wrap = ttk.Frame(kanan)
        wrap.pack(fill="both", expand=True, pady=6)
        kolom = ("id", "tanggal", "jenis", "kategori", "keterangan", "jumlah")
        self.tree = ttk.Treeview(wrap, columns=kolom, show="headings", selectmode="browse")
        lebar = {"id": 40, "tanggal": 90, "jenis": 90, "kategori": 120, "keterangan": 220, "jumlah": 110}
        for k in kolom:
            self.tree.heading(k, text=k.capitalize())
            self.tree.column(k, width=lebar[k], anchor="e" if k == "jumlah" else "w")
        self.tree.tag_configure("Pemasukan", foreground="#1a7f37")
        self.tree.tag_configure("Pengeluaran", foreground="#c0392b")
        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.saat_pilih)

        # total
        tot = ttk.Frame(kanan)
        tot.pack(fill="x")
        self.l_masuk = ttk.Label(tot, style="Angka.TLabel", foreground="#1a7f37")
        self.l_keluar = ttk.Label(tot, style="Angka.TLabel", foreground="#c0392b")
        self.l_saldo = ttk.Label(tot, style="Angka.TLabel")
        for i, (judul, lbl) in enumerate([("Pemasukan", self.l_masuk),
                                          ("Pengeluaran", self.l_keluar), ("Saldo", self.l_saldo)]):
            box = ttk.Frame(tot)
            box.grid(row=0, column=i, padx=14)
            ttk.Label(box, text=judul, style="Judul.TLabel").pack(anchor="w")
            lbl.master = box
            lbl.pack(in_=box, anchor="w")
        self.l_jumlah = ttk.Label(tot, text="")
        self.l_jumlah.grid(row=0, column=3, padx=14, sticky="e")

    # ---------- tab ringkasan ----------
    def _build_ringkasan(self):
        atas = ttk.Frame(self.tab_ring)
        atas.pack(fill="both", expand=True, pady=4)

        kiri = ttk.LabelFrame(atas, text="Total per Kategori (mengikuti filter)", padding=6)
        kiri.pack(side="left", fill="both", expand=True, padx=(0, 6))
        kol = ("jenis", "kategori", "n", "total")
        self.tree_kat = ttk.Treeview(kiri, columns=kol, show="headings")
        for k, t, w, a in [("jenis", "Jenis", 90, "w"), ("kategori", "Kategori", 130, "w"),
                           ("n", "Transaksi", 70, "e"), ("total", "Total", 120, "e")]:
            self.tree_kat.heading(k, text=t)
            self.tree_kat.column(k, width=w, anchor=a)
        self.tree_kat.tag_configure("Pemasukan", foreground="#1a7f37")
        self.tree_kat.tag_configure("Pengeluaran", foreground="#c0392b")
        self.tree_kat.pack(fill="both", expand=True)

        kanan = ttk.LabelFrame(atas, text="Pemasukan vs Pengeluaran per Bulan", padding=6)
        kanan.pack(side="left", fill="both", expand=True)
        self.canvas = tk.Canvas(kanan, bg="white", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self._gambar_grafik())

    def _gambar_grafik(self):
        c = self.canvas
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if w < 50 or h < 50:
            return
        data = self.db.ringkasan_bulanan(self._filter())
        if not data:
            c.create_text(w / 2, h / 2, text="Belum ada data", fill="#888")
            return
        data = data[-12:]  # maksimal 12 bulan terakhir
        kiri, bawah, atas, kanan = 70, 40, 20, 15
        area_w, area_h = w - kiri - kanan, h - bawah - atas
        maks = max(max(d["masuk"], d["keluar"]) for d in data) or 1
        # garis bantu
        for i in range(5):
            y = atas + area_h * i / 4
            c.create_line(kiri, y, w - kanan, y, fill="#e6e6e6")
            c.create_text(kiri - 6, y, anchor="e", fill="#666", font=("Segoe UI", 8),
                          text=f"{maks * (4 - i) / 4 / 1000:,.0f}k".replace(",", "."))
        grup = area_w / len(data)
        lebar_bar = min(28, grup / 3)
        for i, d in enumerate(data):
            x0 = kiri + grup * i + grup / 2
            for geser, nilai, warna in [(-lebar_bar, d["masuk"], "#2ea44f"),
                                        (0, d["keluar"], "#d9534f")]:
                tinggi = area_h * nilai / maks
                c.create_rectangle(x0 + geser, atas + area_h - tinggi,
                                   x0 + geser + lebar_bar, atas + area_h, fill=warna, outline="")
            c.create_text(x0, h - bawah + 14, text=d["bulan"], fill="#444", font=("Segoe UI", 8))
        c.create_rectangle(kiri, 4, kiri + 10, 14, fill="#2ea44f", outline="")
        c.create_text(kiri + 14, 9, anchor="w", text="Pemasukan", font=("Segoe UI", 8))
        c.create_rectangle(kiri + 90, 4, kiri + 100, 14, fill="#d9534f", outline="")
        c.create_text(kiri + 104, 9, anchor="w", text="Pengeluaran", font=("Segoe UI", 8))

    # ---------- logika ----------
    def _set_kategori(self):
        daftar = KATEGORI[self.v_jenis.get()]
        self.cb_kat["values"] = daftar
        if self.v_kat.get() not in daftar:
            self.v_kat.set(daftar[0])

    def _filter(self):
        return {"dari": self.f_dari.get().strip(), "sampai": self.f_sampai.get().strip(),
                "jenis": self.f_jenis.get(), "cari": self.f_cari.get().strip()}

    def _periode_teks(self):
        f = self._filter()
        return f"{f['dari'] or 'awal'} s/d {f['sampai'] or 'sekarang'}"

    def refresh(self):
        f = self._filter()
        for k in ("dari", "sampai"):
            if f[k]:
                try:
                    valid_tanggal(f[k])
                except ValueError:
                    messagebox.showwarning("Filter", "Format tanggal filter harus YYYY-MM-DD.")
                    return
        self.rows = self.db.ambil(f)
        self.tree.delete(*self.tree.get_children())
        for r in self.rows:
            self.tree.insert("", "end", iid=str(r["id"]), tags=(r["jenis"],),
                             values=(r["id"], r["tanggal"], r["jenis"], r["kategori"],
                                     r["keterangan"] or "", rupiah(r["jumlah"])))
        masuk, keluar, saldo = hitung_total(self.rows)
        self.l_masuk.config(text=rupiah(masuk))
        self.l_keluar.config(text=rupiah(keluar))
        self.l_saldo.config(text=rupiah(saldo), foreground="#1a7f37" if saldo >= 0 else "#c0392b")
        self.l_jumlah.config(text=f"{len(self.rows)} transaksi")

        self.tree_kat.delete(*self.tree_kat.get_children())
        for r in self.db.ringkasan_kategori(f):
            self.tree_kat.insert("", "end", tags=(r["jenis"],),
                                 values=(r["jenis"], r["kategori"], r["n"], rupiah(r["total"])))
        self._gambar_grafik()
        self.selected_id = None

    def reset_filter(self):
        self.f_dari.set("")
        self.f_sampai.set("")
        self.f_jenis.set("Semua")
        self.f_cari.set("")
        self.refresh()

    def bersihkan(self):
        self.v_tgl.set(date.today().strftime("%Y-%m-%d"))
        self.v_jenis.set("Pemasukan")
        self._set_kategori()
        self.v_ket.set("")
        self.v_jml.set("")
        self.selected_id = None
        self.tree.selection_remove(self.tree.selection())

    def saat_pilih(self, _=None):
        sel = self.tree.selection()
        if not sel:
            return
        id_ = int(sel[0])
        r = next((x for x in self.rows if x["id"] == id_), None)
        if r:
            self.selected_id = id_
            self.v_tgl.set(r["tanggal"])
            self.v_jenis.set(r["jenis"])
            self._set_kategori()
            self.v_kat.set(r["kategori"])
            self.v_ket.set(r["keterangan"] or "")
            self.v_jml.set(f"{r['jumlah']:.0f}")

    def _baca_form(self):
        try:
            tgl = valid_tanggal(self.v_tgl.get())
        except ValueError:
            messagebox.showwarning("Validasi", "Tanggal tidak valid. Gunakan format YYYY-MM-DD.")
            return None
        kat = self.v_kat.get().strip()
        if not kat:
            messagebox.showwarning("Validasi", "Kategori wajib diisi.")
            return None
        try:
            jml = parse_angka(self.v_jml.get())
            if jml <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Validasi", "Jumlah harus berupa angka lebih dari 0.")
            return None
        return tgl, self.v_jenis.get(), kat, self.v_ket.get().strip(), jml

    # ---------- aksi tombol ----------
    def aksi_tambah(self):
        data = self._baca_form()
        if data:
            self.db.tambah(*data)
            self.refresh()
            self.v_ket.set("")
            self.v_jml.set("")

    def aksi_ubah(self):
        if self.selected_id is None:
            messagebox.showinfo("Ubah", "Pilih dulu baris yang ingin diubah.")
            return
        data = self._baca_form()
        if data:
            id_ = self.selected_id
            self.db.ubah(id_, *data)
            self.refresh()

    def aksi_hapus(self):
        if self.selected_id is None:
            messagebox.showinfo("Hapus", "Pilih dulu baris yang ingin dihapus.")
            return
        if messagebox.askyesno("Konfirmasi", "Hapus transaksi yang dipilih?"):
            self.db.hapus(self.selected_id)
            self.refresh()
            self.bersihkan()

    def aksi_hapus_semua(self):
        if messagebox.askyesno("Konfirmasi", "Hapus SEMUA data transaksi? Tindakan ini tidak bisa dibatalkan."):
            self.db.hapus_semua()
            self.refresh()
            self.bersihkan()

    def aksi_contoh(self):
        n = self.db.isi_contoh()
        self.refresh()
        messagebox.showinfo("Data contoh", f"{n} transaksi contoh ditambahkan.")

    def aksi_csv(self):
        if not self.rows:
            messagebox.showinfo("Ekspor", "Tidak ada data untuk diekspor.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")],
            initialfile=f"laporan_{date.today():%Y%m%d}.csv")
        if path:
            ekspor_csv(path, self.rows)
            messagebox.showinfo("Ekspor", f"Berhasil disimpan:\n{path}")

    def aksi_html(self):
        if not self.rows:
            messagebox.showinfo("Laporan", "Tidak ada data untuk dilaporkan.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".html", filetypes=[("HTML", "*.html")],
            initialfile=f"laporan_{date.today():%Y%m%d}.html")
        if not path:
            path = os.path.join(tempfile.gettempdir(), "laporan_keuangan.html")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(buat_html(self.rows, self.db.ringkasan_kategori(self._filter()),
                               self._periode_teks()))
        webbrowser.open("file://" + os.path.abspath(path))
        messagebox.showinfo("Laporan", "Laporan dibuka di browser.\n"
                                       "Gunakan Ctrl+P untuk mencetak atau menyimpan sebagai PDF.")


if __name__ == "__main__":
    App().mainloop()
