#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APLIKASI LAPORAN KEUANGAN v2 (satu file)
========================================
Fitur:
  - LOGIN dengan password ter-hash (PBKDF2-SHA256) + pembatasan percobaan gagal
  - ROLE: Administrator & Pengguna
      Administrator : semua fitur, termasuk Manajemen Pengguna, hapus transaksi,
                      isi data contoh, hapus semua data
      Pengguna      : tambah/ubah transaksi, ringkasan, ekspor laporan
  - MENU PROGRAM (sidebar + menu bar): Dashboard, Data Transaksi,
      Ringkasan & Grafik, Laporan, Manajemen Pengguna (admin), Ubah Password, Logout
  - CRUD transaksi, filter tanggal/jenis/kata kunci, total otomatis
  - Ekspor CSV dan laporan HTML (cetak / simpan PDF lewat browser)
  - Database SQLite (laporan.db) dibuat otomatis

Akun awal (dibuat otomatis saat pertama kali dijalankan):
    username : admin
    password : admin123      (WAJIB diganti saat login pertama)

Jalankan:
    python aplikasi_laporan.py
Hanya memakai library bawaan Python (tkinter, sqlite3, hashlib, csv).
"""

import csv
import hashlib
import hmac
import html
import os
import re
import sqlite3
import tempfile
import time
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
ROLE_LIST = ["admin", "user"]
ROLE_LABEL = {"admin": "Administrator", "user": "Pengguna"}

WARNA_SIDEBAR = "#1f2a44"
WARNA_AKTIF = "#34508a"
WARNA_HOVER = "#2a3a5e"

MAKS_GAGAL = 5
DURASI_KUNCI = 30  # detik
MIN_PASSWORD = 6


# ----------------------------------------------------------------------
# Fungsi bantu
# ----------------------------------------------------------------------
def rupiah(angka):
    angka = angka or 0
    teks = f"{abs(angka):,.0f}".replace(",", ".")
    return ("-Rp " if angka < 0 else "Rp ") + teks


def parse_angka(teks):
    bersih = teks.strip().lower().replace("rp", "").replace(" ", "")
    bersih = bersih.replace(".", "").replace(",", ".")
    return float(bersih)


def valid_tanggal(teks):
    return datetime.strptime(teks.strip(), "%Y-%m-%d").strftime("%Y-%m-%d")


def hash_password(password, salt=None):
    salt = salt or os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 150_000)
    return salt.hex() + "$" + h.hex()


def cek_password(password, tersimpan):
    try:
        salt_hex, h_hex = tersimpan.split("$")
        h = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                                bytes.fromhex(salt_hex), 150_000)
        return hmac.compare_digest(h.hex(), h_hex)
    except (ValueError, AttributeError):
        return False


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
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS users (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                   nama TEXT NOT NULL,
                   password TEXT NOT NULL,
                   role TEXT NOT NULL CHECK (role IN ('admin','user')),
                   wajib_ganti INTEGER NOT NULL DEFAULT 0
               )"""
        )
        self.conn.commit()
        self.admin_baru = False
        if self.conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            self.conn.execute(
                "INSERT INTO users (username, nama, password, role, wajib_ganti) VALUES (?,?,?,?,1)",
                ("admin", "Administrator", hash_password("admin123"), "admin"),
            )
            self.conn.commit()
            self.admin_baru = True

    # ---------- pengguna ----------
    def login(self, username, password):
        row = self.conn.execute("SELECT * FROM users WHERE username=?", (username.strip(),)).fetchone()
        if row and cek_password(password, row["password"]):
            return row
        return None

    def daftar_user(self):
        return self.conn.execute("SELECT * FROM users ORDER BY role, username").fetchall()

    def tambah_user(self, username, nama, password, role):
        self.conn.execute(
            "INSERT INTO users (username, nama, password, role, wajib_ganti) VALUES (?,?,?,?,1)",
            (username.strip(), nama.strip(), hash_password(password), role),
        )
        self.conn.commit()

    def ubah_user(self, id_, nama, role):
        self.conn.execute("UPDATE users SET nama=?, role=? WHERE id=?", (nama.strip(), role, id_))
        self.conn.commit()

    def set_password(self, id_, password, wajib=0):
        self.conn.execute("UPDATE users SET password=?, wajib_ganti=? WHERE id=?",
                          (hash_password(password), wajib, id_))
        self.conn.commit()

    def hapus_user(self, id_):
        self.conn.execute("DELETE FROM users WHERE id=?", (id_,))
        self.conn.commit()

    def jumlah_admin(self):
        return self.conn.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0]

    # ---------- transaksi ----------
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
            (tanggal, jenis, kategori, keterangan, jumlah))
        self.conn.commit()

    def ubah(self, id_, tanggal, jenis, kategori, keterangan, jumlah):
        self.conn.execute(
            "UPDATE transaksi SET tanggal=?, jenis=?, kategori=?, keterangan=?, jumlah=? WHERE id=?",
            (tanggal, jenis, kategori, keterangan, jumlah, id_))
        self.conn.commit()

    def hapus(self, id_):
        self.conn.execute("DELETE FROM transaksi WHERE id=?", (id_,))
        self.conn.commit()

    def hapus_semua(self):
        self.conn.execute("DELETE FROM transaksi")
        self.conn.commit()

    def ambil(self, f):
        where, params = self._where(f)
        return self.conn.execute(
            f"SELECT * FROM transaksi{where} ORDER BY tanggal DESC, id DESC", params).fetchall()

    def ringkasan_kategori(self, f):
        where, params = self._where(f)
        return self.conn.execute(
            f"""SELECT jenis, kategori, SUM(jumlah) AS total, COUNT(*) AS n
                FROM transaksi{where}
                GROUP BY jenis, kategori ORDER BY jenis, total DESC""", params).fetchall()

    def ringkasan_bulanan(self, f):
        where, params = self._where(f)
        return self.conn.execute(
            f"""SELECT substr(tanggal,1,7) AS bulan,
                       SUM(CASE WHEN jenis='Pemasukan'   THEN jumlah ELSE 0 END) AS masuk,
                       SUM(CASE WHEN jenis='Pengeluaran' THEN jumlah ELSE 0 END) AS keluar
                FROM transaksi{where} GROUP BY bulan ORDER BY bulan""", params).fetchall()

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
            "INSERT INTO transaksi (tanggal, jenis, kategori, keterangan, jumlah) VALUES (?,?,?,?,?)", data)
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


def buat_html(rows, ringkasan_kat, periode, pembuat):
    masuk, keluar, saldo = hitung_total(rows)
    e = html.escape
    baris = "".join(
        f"<tr><td>{i}</td><td>{e(r['tanggal'])}</td>"
        f"<td class='{r['jenis'].lower()}'>{e(r['jenis'])}</td>"
        f"<td>{e(r['kategori'])}</td><td>{e(r['keterangan'] or '')}</td>"
        f"<td class='num'>{rupiah(r['jumlah'])}</td></tr>"
        for i, r in enumerate(rows, 1))
    baris_kat = "".join(
        f"<tr><td>{e(r['jenis'])}</td><td>{e(r['kategori'])}</td>"
        f"<td class='num'>{r['n']}</td><td class='num'>{rupiah(r['total'])}</td></tr>"
        for r in ringkasan_kat)
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
<div class="sub">Periode: {e(periode)} &middot; Dicetak oleh: {e(pembuat)} &middot; {datetime.now():%d-%m-%Y %H:%M}</div>
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
# Halaman LOGIN
# ----------------------------------------------------------------------
class LoginFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.pack(fill="both", expand=True)

        card = ttk.LabelFrame(self, padding=28)
        card.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(card, text=APP_TITLE, font=("Segoe UI", 16, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(0, 2))
        ttk.Label(card, text="Silakan login untuk melanjutkan", foreground="#666").grid(
            row=1, column=0, columnspan=2, pady=(0, 16))

        self.v_user = tk.StringVar()
        self.v_pass = tk.StringVar()

        ttk.Label(card, text="Username").grid(row=2, column=0, sticky="w", pady=5)
        e_user = ttk.Entry(card, textvariable=self.v_user, width=28)
        e_user.grid(row=2, column=1, padx=(10, 0), pady=5)
        ttk.Label(card, text="Password").grid(row=3, column=0, sticky="w", pady=5)
        self.e_pass = ttk.Entry(card, textvariable=self.v_pass, width=28, show="*")
        self.e_pass.grid(row=3, column=1, padx=(10, 0), pady=5)

        self.v_lihat = tk.BooleanVar(value=False)
        ttk.Checkbutton(card, text="Tampilkan password", variable=self.v_lihat,
                        command=self._toggle).grid(row=4, column=1, sticky="w", padx=(10, 0))

        self.l_pesan = ttk.Label(card, text="", foreground="#c0392b", wraplength=300)
        self.l_pesan.grid(row=5, column=0, columnspan=2, pady=(8, 0))

        tombol = ttk.Frame(card)
        tombol.grid(row=6, column=0, columnspan=2, pady=(14, 0), sticky="ew")
        tombol.columnconfigure((0, 1), weight=1)
        ttk.Button(tombol, text="Masuk", command=self.masuk).grid(row=0, column=0, padx=3, sticky="ew")
        ttk.Button(tombol, text="Keluar", command=app.destroy).grid(row=0, column=1, padx=3, sticky="ew")

        e_user.bind("<Return>", lambda e: self.e_pass.focus_set())
        self.e_pass.bind("<Return>", lambda e: self.masuk())
        e_user.focus_set()

    def _toggle(self):
        self.e_pass.config(show="" if self.v_lihat.get() else "*")

    def masuk(self):
        app = self.app
        sekarang = time.time()
        if sekarang < app.kunci_sampai:
            sisa = int(app.kunci_sampai - sekarang) + 1
            self.l_pesan.config(text=f"Terlalu banyak percobaan gagal. Coba lagi dalam {sisa} detik.")
            return
        username, password = self.v_user.get().strip(), self.v_pass.get()
        if not username or not password:
            self.l_pesan.config(text="Username dan password wajib diisi.")
            return
        user = app.db.login(username, password)
        if user:
            app.gagal = 0
            app.user = dict(user)
            app.show_main()
            return
        app.gagal += 1
        if app.gagal >= MAKS_GAGAL:
            app.kunci_sampai = time.time() + DURASI_KUNCI
            app.gagal = 0
            self.l_pesan.config(text=f"Login dikunci selama {DURASI_KUNCI} detik karena terlalu banyak percobaan gagal.")
        else:
            self.l_pesan.config(text=f"Username atau password salah. (Sisa percobaan: {MAKS_GAGAL - app.gagal})")
        self.v_pass.set("")


# ----------------------------------------------------------------------
# Halaman UTAMA (menu program)
# ----------------------------------------------------------------------
class MainFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.db = app.db
        self.user = app.user
        self.is_admin = self.user["role"] == "admin"
        self.selected_id = None
        self.selected_user_id = None
        self.rows = []
        self.pages = {}
        self.nav_btns = {}
        self.pack(fill="both", expand=True)

        # variabel filter bersama (dipakai Data, Ringkasan, Laporan)
        self.f_dari = tk.StringVar()
        self.f_sampai = tk.StringVar()
        self.f_jenis = tk.StringVar(value="Semua")
        self.f_cari = tk.StringVar()

        self.nav_items = [("dashboard", "Dashboard"), ("data", "Data Transaksi"),
                          ("ringkasan", "Ringkasan & Grafik"), ("laporan", "Laporan")]
        if self.is_admin:
            self.nav_items.append(("users", "Manajemen Pengguna"))

        self._menu()
        self._sidebar()
        self.content = ttk.Frame(self)
        self.content.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self.content.rowconfigure(0, weight=1)
        self.content.columnconfigure(0, weight=1)

        self._page_dashboard()
        self._page_data()
        self._page_ringkasan()
        self._page_laporan()
        if self.is_admin:
            self._page_users()

        self.refresh()
        self.show("dashboard")
        if self.user.get("wajib_ganti"):
            self.after(300, self._paksa_ganti)

    # ---------- menu bar & sidebar ----------
    def _menu(self):
        bar = tk.Menu(self.app)
        m_prog = tk.Menu(bar, tearoff=0)
        for key, label in self.nav_items:
            m_prog.add_command(label=label, command=lambda k=key: self.show(k))
        m_prog.add_separator()
        m_prog.add_command(label="Keluar dari program", command=self.app.destroy)
        bar.add_cascade(label="Menu Program", menu=m_prog)

        m_lap = tk.Menu(bar, tearoff=0)
        m_lap.add_command(label="Ekspor CSV...", command=self.aksi_csv)
        m_lap.add_command(label="Buat Laporan HTML / Cetak", command=self.aksi_html)
        bar.add_cascade(label="Laporan", menu=m_lap)

        if self.is_admin:
            m_data = tk.Menu(bar, tearoff=0)
            m_data.add_command(label="Isi data contoh", command=self.aksi_contoh)
            m_data.add_command(label="Hapus semua transaksi", command=self.aksi_hapus_semua)
            bar.add_cascade(label="Data", menu=m_data)

        m_akun = tk.Menu(bar, tearoff=0)
        m_akun.add_command(label="Ubah Password", command=lambda: self.dialog_password(False))
        m_akun.add_command(label="Logout", command=self.logout)
        bar.add_cascade(label="Akun", menu=m_akun)

        m_help = tk.Menu(bar, tearoff=0)
        m_help.add_command(label="Tentang", command=lambda: messagebox.showinfo(
            "Tentang", f"{APP_TITLE}\nPython + Tkinter + SQLite\nDatabase: {DB_PATH}"))
        bar.add_cascade(label="Bantuan", menu=m_help)
        self.app.config(menu=bar)

    def _sidebar(self):
        sb = tk.Frame(self, bg=WARNA_SIDEBAR, width=210)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        tk.Label(sb, text="LAPORAN\nKEUANGAN", bg=WARNA_SIDEBAR, fg="white",
                 font=("Segoe UI", 14, "bold"), justify="left").pack(anchor="w", padx=16, pady=(18, 6))
        self.v_nama = tk.StringVar()
        tk.Label(sb, textvariable=self.v_nama, bg=WARNA_SIDEBAR, fg="#c8d3ea",
                 font=("Segoe UI", 9), justify="left", wraplength=180).pack(anchor="w", padx=16, pady=(0, 14))
        self._set_nama()

        def tombol(teks, perintah, key=None):
            b = tk.Button(sb, text=teks, command=perintah, bg=WARNA_SIDEBAR, fg="white",
                          activebackground=WARNA_HOVER, activeforeground="white",
                          relief="flat", bd=0, anchor="w", padx=16, pady=9,
                          font=("Segoe UI", 10), cursor="hand2")
            b.pack(fill="x")
            if key:
                self.nav_btns[key] = b
            return b

        for key, label in self.nav_items:
            tombol(label, lambda k=key: self.show(k), key)

        tk.Frame(sb, bg=WARNA_SIDEBAR).pack(fill="both", expand=True)  # pengisi ruang
        tk.Frame(sb, bg="#3b4a6b", height=1).pack(fill="x", padx=12, pady=4)
        tombol("Ubah Password", lambda: self.dialog_password(False))
        tombol("Logout", self.logout)
        tombol("Keluar", self.app.destroy)
        tk.Frame(sb, bg=WARNA_SIDEBAR, height=10).pack()

    def _set_nama(self):
        self.v_nama.set(f"{self.user['nama']}\n({ROLE_LABEL[self.user['role']]})")

    def show(self, name):
        if name == "users" and not self.is_admin:
            return
        self.pages[name].tkraise()
        for k, b in self.nav_btns.items():
            b.config(bg=WARNA_AKTIF if k == name else WARNA_SIDEBAR)
        if name == "dashboard":
            self._isi_dashboard()
        elif name == "ringkasan":
            self.after(50, self._gambar_grafik)
        elif name == "laporan":
            self._info_laporan()
        elif name == "users":
            self._isi_users()

    def _buat_page(self, name):
        f = ttk.Frame(self.content)
        f.grid(row=0, column=0, sticky="nsew")
        self.pages[name] = f
        return f

    # ---------- halaman: dashboard ----------
    def _page_dashboard(self):
        p = self._buat_page("dashboard")
        self.l_salam = ttk.Label(p, font=("Segoe UI", 16, "bold"))
        self.l_salam.pack(anchor="w")
        ttk.Label(p, text="Ringkasan seluruh transaksi (tanpa filter)", foreground="#666").pack(anchor="w", pady=(0, 10))

        kartu = ttk.Frame(p)
        kartu.pack(fill="x")
        self.d_labels = {}
        for i, (kunci, judul, warna) in enumerate([
                ("masuk", "Total Pemasukan", "#1a7f37"), ("keluar", "Total Pengeluaran", "#c0392b"),
                ("saldo", "Saldo", "#222"), ("n", "Jumlah Transaksi", "#222")]):
            box = ttk.LabelFrame(kartu, text=judul, padding=12)
            box.grid(row=0, column=i, padx=(0 if i == 0 else 8, 0), sticky="ew")
            kartu.columnconfigure(i, weight=1)
            lbl = ttk.Label(box, font=("Segoe UI", 15, "bold"), foreground=warna)
            lbl.pack(anchor="w")
            self.d_labels[kunci] = lbl

        cepat = ttk.Frame(p)
        cepat.pack(fill="x", pady=12)
        ttk.Button(cepat, text="+ Tambah Transaksi", command=lambda: self.show("data")).pack(side="left")
        ttk.Button(cepat, text="Lihat Ringkasan", command=lambda: self.show("ringkasan")).pack(side="left", padx=6)
        ttk.Button(cepat, text="Buat Laporan", command=lambda: self.show("laporan")).pack(side="left")

        ttk.Label(p, text="Transaksi Terbaru", style="Judul.TLabel").pack(anchor="w")
        kol = ("tanggal", "jenis", "kategori", "keterangan", "jumlah")
        self.tree_dash = ttk.Treeview(p, columns=kol, show="headings", height=8)
        for k, w, a in [("tanggal", 90, "w"), ("jenis", 90, "w"), ("kategori", 120, "w"),
                        ("keterangan", 240, "w"), ("jumlah", 110, "e")]:
            self.tree_dash.heading(k, text=k.capitalize())
            self.tree_dash.column(k, width=w, anchor=a)
        self.tree_dash.tag_configure("Pemasukan", foreground="#1a7f37")
        self.tree_dash.tag_configure("Pengeluaran", foreground="#c0392b")
        self.tree_dash.pack(fill="both", expand=True, pady=(4, 0))

    def _isi_dashboard(self):
        semua = self.db.ambil({})
        masuk, keluar, saldo = hitung_total(semua)
        self.l_salam.config(text=f"Selamat datang, {self.user['nama']}")
        self.d_labels["masuk"].config(text=rupiah(masuk))
        self.d_labels["keluar"].config(text=rupiah(keluar))
        self.d_labels["saldo"].config(text=rupiah(saldo),
                                      foreground="#1a7f37" if saldo >= 0 else "#c0392b")
        self.d_labels["n"].config(text=str(len(semua)))
        self.tree_dash.delete(*self.tree_dash.get_children())
        for r in semua[:8]:
            self.tree_dash.insert("", "end", tags=(r["jenis"],),
                                  values=(r["tanggal"], r["jenis"], r["kategori"],
                                          r["keterangan"] or "", rupiah(r["jumlah"])))

    # ---------- halaman: data transaksi ----------
    def _page_data(self):
        p = self._buat_page("data")
        kiri = ttk.LabelFrame(p, text="Form Transaksi", padding=10)
        kiri.pack(side="left", fill="y", padx=(0, 8))

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
        tombol.columnconfigure((0, 1), weight=1)
        ttk.Button(tombol, text="Tambah", command=self.aksi_tambah).grid(row=0, column=0, padx=3, pady=3, sticky="ew")
        ttk.Button(tombol, text="Ubah", command=self.aksi_ubah).grid(row=0, column=1, padx=3, pady=3, sticky="ew")
        self.btn_hapus = ttk.Button(tombol, text="Hapus", command=self.aksi_hapus)
        self.btn_hapus.grid(row=1, column=0, padx=3, pady=3, sticky="ew")
        ttk.Button(tombol, text="Bersihkan", command=self.bersihkan).grid(row=1, column=1, padx=3, pady=3, sticky="ew")
        if not self.is_admin:
            self.btn_hapus.state(["disabled"])
            ttk.Label(kiri, text="Hapus transaksi hanya untuk Administrator.",
                      foreground="#888", wraplength=220).grid(row=6, column=0, columnspan=2, pady=(8, 0))

        kanan = ttk.Frame(p)
        kanan.pack(side="left", fill="both", expand=True)

        fr = ttk.LabelFrame(kanan, text="Filter", padding=8)
        fr.pack(fill="x")
        ttk.Label(fr, text="Dari").grid(row=0, column=0)
        ttk.Entry(fr, textvariable=self.f_dari, width=11).grid(row=0, column=1, padx=4)
        ttk.Label(fr, text="Sampai").grid(row=0, column=2)
        ttk.Entry(fr, textvariable=self.f_sampai, width=11).grid(row=0, column=3, padx=4)
        ttk.Label(fr, text="Jenis").grid(row=0, column=4)
        ttk.Combobox(fr, textvariable=self.f_jenis, values=["Semua"] + JENIS_LIST,
                     state="readonly", width=11).grid(row=0, column=5, padx=4)
        ttk.Label(fr, text="Cari").grid(row=0, column=6)
        ent = ttk.Entry(fr, textvariable=self.f_cari, width=14)
        ent.grid(row=0, column=7, padx=4)
        ent.bind("<Return>", lambda e: self.refresh())
        ttk.Button(fr, text="Terapkan", command=self.refresh).grid(row=0, column=8, padx=4)
        ttk.Button(fr, text="Reset", command=self.reset_filter).grid(row=0, column=9)
        ttk.Label(fr, text="Format tanggal: YYYY-MM-DD (kosongkan jika tidak dipakai)",
                  foreground="#777").grid(row=1, column=0, columnspan=10, sticky="w", pady=(4, 0))

        wrap = ttk.Frame(kanan)
        wrap.pack(fill="both", expand=True, pady=6)
        kolom = ("id", "tanggal", "jenis", "kategori", "keterangan", "jumlah")
        self.tree = ttk.Treeview(wrap, columns=kolom, show="headings", selectmode="browse")
        lebar = {"id": 40, "tanggal": 90, "jenis": 90, "kategori": 120, "keterangan": 200, "jumlah": 110}
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

        tot = ttk.Frame(kanan)
        tot.pack(fill="x")
        self.l_masuk, self.l_keluar, self.l_saldo = [None] * 3
        labels = []
        for i, (judul, warna) in enumerate([("Pemasukan", "#1a7f37"), ("Pengeluaran", "#c0392b"), ("Saldo", "#222")]):
            box = ttk.Frame(tot)
            box.grid(row=0, column=i, padx=(0, 18))
            ttk.Label(box, text=judul, style="Judul.TLabel").pack(anchor="w")
            lbl = ttk.Label(box, style="Angka.TLabel", foreground=warna)
            lbl.pack(anchor="w")
            labels.append(lbl)
        self.l_masuk, self.l_keluar, self.l_saldo = labels
        self.l_jumlah = ttk.Label(tot, text="")
        self.l_jumlah.grid(row=0, column=3, sticky="e")

    # ---------- halaman: ringkasan ----------
    def _page_ringkasan(self):
        p = self._buat_page("ringkasan")
        ttk.Label(p, text="Ringkasan & Grafik", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        self.l_filter_info = ttk.Label(p, foreground="#666")
        self.l_filter_info.pack(anchor="w", pady=(0, 6))
        atas = ttk.Frame(p)
        atas.pack(fill="both", expand=True)

        kiri = ttk.LabelFrame(atas, text="Total per Kategori", padding=6)
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
        data = data[-12:]
        kiri, bawah, atas, kanan = 70, 40, 24, 15
        area_w, area_h = w - kiri - kanan, h - bawah - atas
        maks = max(max(d["masuk"], d["keluar"]) for d in data) or 1
        for i in range(5):
            y = atas + area_h * i / 4
            c.create_line(kiri, y, w - kanan, y, fill="#e6e6e6")
            c.create_text(kiri - 6, y, anchor="e", fill="#666", font=("Segoe UI", 8),
                          text=f"{maks * (4 - i) / 4 / 1000:,.0f}k".replace(",", "."))
        grup = area_w / len(data)
        lebar_bar = min(28, grup / 3)
        for i, d in enumerate(data):
            x0 = kiri + grup * i + grup / 2
            for geser, nilai, warna in [(-lebar_bar, d["masuk"], "#2ea44f"), (0, d["keluar"], "#d9534f")]:
                tinggi = area_h * nilai / maks
                c.create_rectangle(x0 + geser, atas + area_h - tinggi,
                                   x0 + geser + lebar_bar, atas + area_h, fill=warna, outline="")
            c.create_text(x0, h - bawah + 14, text=d["bulan"], fill="#444", font=("Segoe UI", 8))
        c.create_rectangle(kiri, 4, kiri + 10, 14, fill="#2ea44f", outline="")
        c.create_text(kiri + 14, 9, anchor="w", text="Pemasukan", font=("Segoe UI", 8))
        c.create_rectangle(kiri + 90, 4, kiri + 100, 14, fill="#d9534f", outline="")
        c.create_text(kiri + 104, 9, anchor="w", text="Pengeluaran", font=("Segoe UI", 8))

    # ---------- halaman: laporan ----------
    def _page_laporan(self):
        p = self._buat_page("laporan")
        ttk.Label(p, text="Laporan", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(p, text="Laporan dibuat dari data sesuai periode & filter di bawah.",
                  foreground="#666").pack(anchor="w", pady=(0, 10))

        per = ttk.LabelFrame(p, text="Periode", padding=10)
        per.pack(fill="x")
        ttk.Label(per, text="Dari").grid(row=0, column=0)
        ttk.Entry(per, textvariable=self.f_dari, width=12).grid(row=0, column=1, padx=6)
        ttk.Label(per, text="Sampai").grid(row=0, column=2)
        ttk.Entry(per, textvariable=self.f_sampai, width=12).grid(row=0, column=3, padx=6)
        ttk.Button(per, text="Terapkan", command=self.refresh).grid(row=0, column=4, padx=6)
        preset = ttk.Frame(per)
        preset.grid(row=1, column=0, columnspan=6, sticky="w", pady=(8, 0))
        for teks, kode in [("Bulan ini", "bulan"), ("30 hari terakhir", "30"),
                           ("Tahun ini", "tahun"), ("Semua", "semua")]:
            ttk.Button(preset, text=teks, command=lambda k=kode: self.preset(k)).pack(side="left", padx=(0, 6))

        self.l_info_lap = ttk.Label(p, font=("Segoe UI", 11), justify="left")
        self.l_info_lap.pack(anchor="w", pady=14)

        aksi = ttk.Frame(p)
        aksi.pack(anchor="w")
        ttk.Button(aksi, text="Ekspor CSV...", command=self.aksi_csv).pack(side="left", padx=(0, 8))
        ttk.Button(aksi, text="Buat Laporan HTML / Cetak", command=self.aksi_html).pack(side="left")
        ttk.Label(p, text="Tip: di browser tekan Ctrl+P, lalu pilih 'Simpan sebagai PDF'.",
                  foreground="#888").pack(anchor="w", pady=10)

    def _info_laporan(self):
        masuk, keluar, saldo = hitung_total(self.rows)
        self.l_info_lap.config(text=(
            f"Periode        : {self._periode_teks()}\n"
            f"Jumlah data  : {len(self.rows)} transaksi\n"
            f"Pemasukan   : {rupiah(masuk)}\n"
            f"Pengeluaran : {rupiah(keluar)}\n"
            f"Saldo            : {rupiah(saldo)}"))

    def preset(self, kode):
        h = date.today()
        if kode == "bulan":
            dari, sampai = h.replace(day=1), h
        elif kode == "30":
            dari, sampai = h - timedelta(days=30), h
        elif kode == "tahun":
            dari, sampai = date(h.year, 1, 1), h
        else:
            dari = sampai = None
        self.f_dari.set(dari.strftime("%Y-%m-%d") if dari else "")
        self.f_sampai.set(sampai.strftime("%Y-%m-%d") if sampai else "")
        self.refresh()
        self._info_laporan()

    # ---------- halaman: manajemen pengguna (admin) ----------
    def _page_users(self):
        p = self._buat_page("users")
        kiri = ttk.LabelFrame(p, text="Form Pengguna", padding=10)
        kiri.pack(side="left", fill="y", padx=(0, 8))
        self.u_username = tk.StringVar()
        self.u_nama = tk.StringVar()
        self.u_pass = tk.StringVar()
        self.u_role = tk.StringVar(value="user")

        def baris(r, teks, widget):
            ttk.Label(kiri, text=teks).grid(row=r, column=0, sticky="w", pady=4)
            widget.grid(row=r, column=1, pady=4, padx=(8, 0), sticky="ew")

        self.e_u_username = ttk.Entry(kiri, textvariable=self.u_username, width=24)
        baris(0, "Username", self.e_u_username)
        baris(1, "Nama lengkap", ttk.Entry(kiri, textvariable=self.u_nama, width=24))
        baris(2, "Password", ttk.Entry(kiri, textvariable=self.u_pass, width=24, show="*"))
        baris(3, "Role", ttk.Combobox(kiri, textvariable=self.u_role, values=ROLE_LIST,
                                       state="readonly", width=22))
        ttk.Label(kiri, text=f"Password minimal {MIN_PASSWORD} karakter.\n"
                             "Pengguna baru / hasil reset wajib\nmengganti password saat login.",
                  foreground="#888").grid(row=4, column=0, columnspan=2, sticky="w", pady=(6, 0))
        tombol = ttk.Frame(kiri)
        tombol.grid(row=5, column=0, columnspan=2, pady=(12, 0), sticky="ew")
        tombol.columnconfigure((0, 1), weight=1)
        for i, (t, c) in enumerate([("Tambah", self.u_tambah), ("Ubah Nama/Role", self.u_ubah),
                                    ("Reset Password", self.u_reset), ("Hapus", self.u_hapus),
                                    ("Bersihkan", self.u_bersihkan)]):
            ttk.Button(tombol, text=t, command=c).grid(row=i // 2, column=i % 2, padx=3, pady=3, sticky="ew")

        kanan = ttk.Frame(p)
        kanan.pack(side="left", fill="both", expand=True)
        ttk.Label(kanan, text="Daftar Pengguna", style="Judul.TLabel").pack(anchor="w")
        kol = ("id", "username", "nama", "role", "status")
        self.tree_user = ttk.Treeview(kanan, columns=kol, show="headings", selectmode="browse")
        for k, t, w in [("id", "ID", 40), ("username", "Username", 130), ("nama", "Nama", 180),
                        ("role", "Role", 110), ("status", "Status Password", 130)]:
            self.tree_user.heading(k, text=t)
            self.tree_user.column(k, width=w, anchor="w")
        self.tree_user.pack(fill="both", expand=True, pady=(4, 0))
        self.tree_user.bind("<<TreeviewSelect>>", self.u_saat_pilih)

    def _isi_users(self):
        self.tree_user.delete(*self.tree_user.get_children())
        for u in self.db.daftar_user():
            nama = u["nama"] + ("  (Anda)" if u["id"] == self.user["id"] else "")
            self.tree_user.insert("", "end", iid=str(u["id"]),
                                  values=(u["id"], u["username"], nama, ROLE_LABEL[u["role"]],
                                          "Wajib diganti" if u["wajib_ganti"] else "Normal"))
        self.selected_user_id = None

    def u_bersihkan(self):
        self.u_username.set("")
        self.u_nama.set("")
        self.u_pass.set("")
        self.u_role.set("user")
        self.selected_user_id = None
        self.e_u_username.state(["!disabled"])
        self.tree_user.selection_remove(self.tree_user.selection())

    def u_saat_pilih(self, _=None):
        sel = self.tree_user.selection()
        if not sel:
            return
        id_ = int(sel[0])
        u = next((x for x in self.db.daftar_user() if x["id"] == id_), None)
        if u:
            self.selected_user_id = id_
            self.u_username.set(u["username"])
            self.u_nama.set(u["nama"])
            self.u_role.set(u["role"])
            self.u_pass.set("")
            self.e_u_username.state(["disabled"])

    def u_tambah(self):
        username, nama, pw, role = (self.u_username.get().strip(), self.u_nama.get().strip(),
                                    self.u_pass.get(), self.u_role.get())
        if not re.fullmatch(r"[A-Za-z0-9_.]{3,20}", username):
            messagebox.showwarning("Validasi", "Username 3-20 karakter: huruf, angka, titik, atau underscore.")
            return
        if not nama:
            messagebox.showwarning("Validasi", "Nama lengkap wajib diisi.")
            return
        if len(pw) < MIN_PASSWORD:
            messagebox.showwarning("Validasi", f"Password minimal {MIN_PASSWORD} karakter.")
            return
        try:
            self.db.tambah_user(username, nama, pw, role)
        except sqlite3.IntegrityError:
            messagebox.showwarning("Validasi", "Username sudah dipakai.")
            return
        self._isi_users()
        self.u_bersihkan()
        messagebox.showinfo("Pengguna", "Pengguna berhasil ditambahkan.")

    def _user_terpilih(self):
        if self.selected_user_id is None:
            messagebox.showinfo("Pengguna", "Pilih dulu pengguna dari daftar.")
            return None
        return next((x for x in self.db.daftar_user() if x["id"] == self.selected_user_id), None)

    def u_ubah(self):
        u = self._user_terpilih()
        if not u:
            return
        nama, role = self.u_nama.get().strip(), self.u_role.get()
        if not nama:
            messagebox.showwarning("Validasi", "Nama lengkap wajib diisi.")
            return
        if u["role"] == "admin" and role != "admin":
            if u["id"] == self.user["id"]:
                messagebox.showwarning("Ditolak", "Anda tidak dapat menurunkan role akun Anda sendiri.")
                return
            if self.db.jumlah_admin() <= 1:
                messagebox.showwarning("Ditolak", "Harus ada minimal satu Administrator.")
                return
        self.db.ubah_user(u["id"], nama, role)
        if u["id"] == self.user["id"]:
            self.user["nama"] = nama
            self._set_nama()
        self._isi_users()
        self.u_bersihkan()

    def u_reset(self):
        u = self._user_terpilih()
        if not u:
            return
        pw = self.u_pass.get()
        if len(pw) < MIN_PASSWORD:
            messagebox.showwarning("Validasi", f"Isi kolom Password baru (minimal {MIN_PASSWORD} karakter).")
            return
        self.db.set_password(u["id"], pw, wajib=1)
        self._isi_users()
        self.u_bersihkan()
        messagebox.showinfo("Pengguna", f"Password '{u['username']}' direset. Pengguna wajib menggantinya saat login.")

    def u_hapus(self):
        u = self._user_terpilih()
        if not u:
            return
        if u["id"] == self.user["id"]:
            messagebox.showwarning("Ditolak", "Anda tidak dapat menghapus akun Anda sendiri.")
            return
        if u["role"] == "admin" and self.db.jumlah_admin() <= 1:
            messagebox.showwarning("Ditolak", "Harus ada minimal satu Administrator.")
            return
        if messagebox.askyesno("Konfirmasi", f"Hapus pengguna '{u['username']}'?"):
            self.db.hapus_user(u["id"])
            self._isi_users()
            self.u_bersihkan()

    # ---------- logika transaksi ----------
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
        self.l_filter_info.config(text=f"Periode: {self._periode_teks()}  |  Jenis: {f['jenis']}"
                                       + (f"  |  Cari: {f['cari']}" if f["cari"] else ""))
        self._gambar_grafik()
        self._info_laporan()
        self._isi_dashboard()
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
            self.db.ubah(self.selected_id, *data)
            self.refresh()

    def aksi_hapus(self):
        if not self.is_admin:
            messagebox.showwarning("Ditolak", "Hanya Administrator yang dapat menghapus transaksi.")
            return
        if self.selected_id is None:
            messagebox.showinfo("Hapus", "Pilih dulu baris yang ingin dihapus.")
            return
        if messagebox.askyesno("Konfirmasi", "Hapus transaksi yang dipilih?"):
            self.db.hapus(self.selected_id)
            self.refresh()
            self.bersihkan()

    def aksi_hapus_semua(self):
        if not self.is_admin:
            return
        if messagebox.askyesno("Konfirmasi", "Hapus SEMUA data transaksi? Tindakan ini tidak bisa dibatalkan."):
            self.db.hapus_semua()
            self.refresh()
            self.bersihkan()

    def aksi_contoh(self):
        if not self.is_admin:
            return
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
                               self._periode_teks(), self.user["nama"]))
        webbrowser.open("file://" + os.path.abspath(path))
        messagebox.showinfo("Laporan", "Laporan dibuka di browser.\n"
                                       "Tekan Ctrl+P untuk mencetak atau menyimpan sebagai PDF.")

    # ---------- akun ----------
    def logout(self):
        if messagebox.askyesno("Logout", "Keluar dari akun ini?"):
            self.app.logout()

    def _paksa_ganti(self):
        messagebox.showinfo("Keamanan", "Demi keamanan, Anda wajib mengganti password sebelum melanjutkan.")
        if not self.dialog_password(paksa=True):
            self.app.logout()

    def dialog_password(self, paksa=False):
        win = tk.Toplevel(self.app)
        win.title("Ubah Password")
        win.transient(self.app)
        win.resizable(False, False)
        win.grab_set()
        frm = ttk.Frame(win, padding=18)
        frm.pack()
        v_lama, v_baru, v_ulang = tk.StringVar(), tk.StringVar(), tk.StringVar()
        for i, (t, v) in enumerate([("Password lama", v_lama), ("Password baru", v_baru),
                                    ("Ulangi password baru", v_ulang)]):
            ttk.Label(frm, text=t).grid(row=i, column=0, sticky="w", pady=5)
            ttk.Entry(frm, textvariable=v, show="*", width=26).grid(row=i, column=1, padx=(10, 0), pady=5)
        ttk.Label(frm, text=f"Minimal {MIN_PASSWORD} karakter.", foreground="#888").grid(
            row=3, column=0, columnspan=2, sticky="w")
        hasil = {"ok": False}

        def simpan():
            if not self.db.login(self.user["username"], v_lama.get()):
                messagebox.showwarning("Validasi", "Password lama salah.", parent=win)
                return
            if len(v_baru.get()) < MIN_PASSWORD:
                messagebox.showwarning("Validasi", f"Password baru minimal {MIN_PASSWORD} karakter.", parent=win)
                return
            if v_baru.get() != v_ulang.get():
                messagebox.showwarning("Validasi", "Konfirmasi password tidak sama.", parent=win)
                return
            if v_baru.get() == v_lama.get():
                messagebox.showwarning("Validasi", "Password baru harus berbeda dari password lama.", parent=win)
                return
            self.db.set_password(self.user["id"], v_baru.get(), wajib=0)
            self.user["wajib_ganti"] = 0
            hasil["ok"] = True
            win.destroy()
            messagebox.showinfo("Password", "Password berhasil diubah.")

        tombol = ttk.Frame(frm)
        tombol.grid(row=4, column=0, columnspan=2, pady=(14, 0), sticky="e")
        ttk.Button(tombol, text="Simpan", command=simpan).pack(side="left", padx=4)
        ttk.Button(tombol, text="Batal", command=win.destroy).pack(side="left")
        win.bind("<Return>", lambda e: simpan())
        self.app.wait_window(win)
        return hasil["ok"]


# ----------------------------------------------------------------------
# Aplikasi utama
# ----------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("1150x700")
        self.minsize(960, 600)
        self.db = Database(DB_PATH)
        self.user = None
        self.gagal = 0
        self.kunci_sampai = 0
        self._style()
        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)
        self.show_login()
        if self.db.admin_baru:
            self.after(400, lambda: messagebox.showinfo(
                "Akun awal",
                "Akun administrator awal dibuat:\n\nUsername : admin\nPassword : admin123\n\n"
                "Anda akan diminta menggantinya setelah login."))

    def _style(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure("Treeview", rowheight=24)
        s.configure("Judul.TLabel", font=("Segoe UI", 10, "bold"))
        s.configure("Angka.TLabel", font=("Segoe UI", 13, "bold"))

    def _bersih(self):
        for w in self.container.winfo_children():
            w.destroy()
        self.config(menu=tk.Menu(self))

    def show_login(self):
        self._bersih()
        self.user = None
        self.title(f"{APP_TITLE} - Login")
        LoginFrame(self.container, self)

    def show_main(self):
        self._bersih()
        self.title(f"{APP_TITLE} - {self.user['nama']} ({ROLE_LABEL[self.user['role']]})")
        MainFrame(self.container, self)

    def logout(self):
        self.show_login()


if __name__ == "__main__":
    App().mainloop()
