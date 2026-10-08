"""
crud_mahasiswa.py  (versi 2)
============================
Aplikasi CRUD dengan GUI Tkinter + SQLite.

Baru di versi ini:
  - Kolom tambahan: Angkatan, IPK, Email (dengan validasi)
  - Tombol Ekspor CSV dan Ekspor Excel (mengekspor data yang sedang tampil)
  - Database lama otomatis ditambah kolom baru (data lama tetap aman)
  - Database disimpan di sebelah file .py / .exe, jadi aman untuk PyInstaller

Jalankan:  py crud_mahasiswa.py
Ekspor Excel butuh:  py -m pip install openpyxl   (CSV tidak butuh apa pun)
"""

import csv
import sqlite3
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


def folder_aplikasi():
    """Folder tempat database disimpan (sebelah .py, atau sebelah .exe)."""
    if getattr(sys, "frozen", False):  # dijalankan sebagai .exe PyInstaller
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


DB_FILE = folder_aplikasi() / "mahasiswa.db"
FIELDS = ("nim", "nama", "jurusan", "angkatan", "ipk", "email")
LABELS = ("NIM", "Nama", "Jurusan", "Angkatan", "IPK", "Email")
LEBAR = (120, 180, 170, 80, 60, 190)


class Database:
    """Lapisan data: semua perintah SQL ada di sini."""

    def __init__(self, path):
        self.con = sqlite3.connect(path)
        self.con.execute(
            """CREATE TABLE IF NOT EXISTS mahasiswa (
                   id       INTEGER PRIMARY KEY AUTOINCREMENT,
                   nim      TEXT NOT NULL UNIQUE,
                   nama     TEXT NOT NULL,
                   jurusan  TEXT,
                   angkatan INTEGER,
                   ipk      REAL,
                   email    TEXT)"""
        )
        # Migrasi: database versi 1 belum punya kolom baru
        ada = {r[1] for r in self.con.execute("PRAGMA table_info(mahasiswa)")}
        for kolom, tipe in (("angkatan", "INTEGER"), ("ipk", "REAL"), ("email", "TEXT")):
            if kolom not in ada:
                self.con.execute(f"ALTER TABLE mahasiswa ADD COLUMN {kolom} {tipe}")
        self.con.commit()

    def semua(self, kata=""):  # READ (daftar + pencarian)
        like = f"%{kata}%"
        return self.con.execute(
            "SELECT id, nim, nama, jurusan, angkatan, ipk, email FROM mahasiswa "
            "WHERE nim LIKE ? OR nama LIKE ? OR jurusan LIKE ? OR email LIKE ? "
            "ORDER BY nim",
            (like, like, like, like),
        ).fetchall()

    def satu(self, id_):  # READ (satu baris)
        return self.con.execute(
            "SELECT nim, nama, jurusan, angkatan, ipk, email FROM mahasiswa WHERE id = ?",
            (id_,),
        ).fetchone()

    def tambah(self, data):  # CREATE
        with self.con:
            self.con.execute(
                "INSERT INTO mahasiswa (nim, nama, jurusan, angkatan, ipk, email) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                data,
            )

    def ubah(self, id_, data):  # UPDATE
        with self.con:
            self.con.execute(
                "UPDATE mahasiswa SET nim = ?, nama = ?, jurusan = ?, "
                "angkatan = ?, ipk = ?, email = ? WHERE id = ?",
                (*data, id_),
            )

    def hapus(self, id_):  # DELETE
        with self.con:
            self.con.execute("DELETE FROM mahasiswa WHERE id = ?", (id_,))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CRUD Data Mahasiswa")
        self.geometry("900x520")
        self.minsize(780, 460)
        self.db = Database(DB_FILE)
        self.id_terpilih = None
        self.var = {k: tk.StringVar() for k in FIELDS}
        self.var_cari = tk.StringVar()
        self._buat_form()
        self._buat_tabel()
        self.var_cari.trace_add("write", lambda *_: self.muat())
        self.muat()

    # ---------------------------------------------------------- tampilan
    def _buat_form(self):
        box = ttk.LabelFrame(self, text="Form Data", padding=10)
        box.pack(fill="x", padx=12, pady=(12, 6))
        box.columnconfigure(1, weight=1)
        box.columnconfigure(3, weight=1)
        for i, (k, label) in enumerate(zip(FIELDS, LABELS)):
            baris, kolom = i % 3, (i // 3) * 2
            ttk.Label(box, text=label).grid(
                row=baris, column=kolom, sticky="w", pady=3,
                padx=(0 if kolom == 0 else 16, 0))
            ttk.Entry(box, textvariable=self.var[k]).grid(
                row=baris, column=kolom + 1, sticky="ew", padx=(8, 0), pady=3)

        tombol = ttk.Frame(box)
        tombol.grid(row=3, column=0, columnspan=4, pady=(8, 0), sticky="w")
        for teks, perintah in (("Tambah", self.tambah), ("Ubah", self.ubah),
                               ("Hapus", self.hapus), ("Bersihkan", self.bersihkan)):
            ttk.Button(tombol, text=teks, command=perintah).pack(side="left", padx=(0, 6))
        ttk.Separator(tombol, orient="vertical").pack(side="left", fill="y", padx=8)
        for teks, perintah in (("Ekspor CSV", self.ekspor_csv),
                               ("Ekspor Excel", self.ekspor_excel)):
            ttk.Button(tombol, text=teks, command=perintah).pack(side="left", padx=(0, 6))

    def _buat_tabel(self):
        cari = ttk.Frame(self)
        cari.pack(fill="x", padx=12)
        ttk.Label(cari, text="Cari:").pack(side="left")
        ttk.Entry(cari, textvariable=self.var_cari).pack(
            side="left", fill="x", expand=True, padx=6)

        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=12, pady=8)
        self.tabel = ttk.Treeview(frame, columns=FIELDS, show="headings", selectmode="browse")
        for k, label, lebar in zip(FIELDS, LABELS, LEBAR):
            self.tabel.heading(k, text=label.upper())
            self.tabel.column(k, width=lebar, anchor="center" if k in ("angkatan", "ipk") else "w")
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.tabel.yview)
        self.tabel.configure(yscrollcommand=scroll.set)
        self.tabel.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.tabel.bind("<<TreeviewSelect>>", self.pilih)

    # ------------------------------------------------------------ bantu
    def _ambil(self):
        """Baca dan validasi form. Mengembalikan tuple siap simpan, atau None."""
        v = {k: self.var[k].get().strip() for k in FIELDS}
        if not v["nim"] or not v["nama"]:
            messagebox.showwarning("Peringatan", "NIM dan Nama wajib diisi.")
            return None

        angkatan = None
        if v["angkatan"]:
            if not (v["angkatan"].isdigit() and len(v["angkatan"]) == 4):
                messagebox.showwarning("Peringatan", "Angkatan harus 4 digit, misalnya 2026.")
                return None
            angkatan = int(v["angkatan"])

        ipk = None
        if v["ipk"]:
            try:
                ipk = float(v["ipk"].replace(",", "."))
            except ValueError:
                ipk = None
            if ipk is None or not 0 <= ipk <= 4:
                messagebox.showwarning("Peringatan", "IPK harus berupa angka 0 sampai 4.")
                return None

        email = v["email"]
        if email and (email.count("@") != 1 or "." not in email.split("@")[1]):
            messagebox.showwarning("Peringatan", "Format email tidak valid.")
            return None

        return (v["nim"], v["nama"], v["jurusan"], angkatan, ipk, email)

    @staticmethod
    def _teks(nilai):
        return "" if nilai is None else str(nilai)

    # ------------------------------------------------------------- aksi
    def muat(self):
        self.tabel.delete(*self.tabel.get_children())
        for id_, *kolom in self.db.semua(self.var_cari.get().strip()):
            nim, nama, jurusan, angkatan, ipk, email = kolom
            ipk_teks = "" if ipk is None else f"{ipk:.2f}"
            self.tabel.insert("", "end", iid=str(id_),
                              values=(nim, nama, jurusan, self._teks(angkatan), ipk_teks, email))

    def pilih(self, _event=None):
        pilihan = self.tabel.selection()
        if not pilihan:
            return
        self.id_terpilih = int(pilihan[0])
        # Ambil dari database (bukan dari tabel) agar NIM berawalan 0 tidak berubah
        for k, nilai in zip(FIELDS, self.db.satu(self.id_terpilih)):
            self.var[k].set(self._teks(nilai))

    def bersihkan(self):
        for v in self.var.values():
            v.set("")
        self.id_terpilih = None
        self.tabel.selection_remove(*self.tabel.selection())

    def tambah(self):
        data = self._ambil()
        if data is None:
            return
        try:
            self.db.tambah(data)
        except sqlite3.IntegrityError:
            messagebox.showerror("Gagal", f"NIM {data[0]} sudah ada.")
            return
        self.bersihkan()
        self.muat()

    def ubah(self):
        if self.id_terpilih is None:
            messagebox.showwarning("Peringatan", "Pilih data di tabel terlebih dahulu.")
            return
        data = self._ambil()
        if data is None:
            return
        try:
            self.db.ubah(self.id_terpilih, data)
        except sqlite3.IntegrityError:
            messagebox.showerror("Gagal", f"NIM {data[0]} sudah dipakai data lain.")
            return
        self.bersihkan()
        self.muat()

    def hapus(self):
        if self.id_terpilih is None:
            messagebox.showwarning("Peringatan", "Pilih data di tabel terlebih dahulu.")
            return
        if messagebox.askyesno("Konfirmasi", "Hapus data yang dipilih?"):
            self.db.hapus(self.id_terpilih)
            self.bersihkan()
            self.muat()

    # ----------------------------------------------------------- ekspor
    def _siap_ekspor(self, ekstensi, jenis):
        """Ambil data yang sedang tampil + minta lokasi simpan. None jika batal."""
        baris = [r[1:] for r in self.db.semua(self.var_cari.get().strip())]
        if not baris:
            messagebox.showinfo("Info", "Tidak ada data untuk diekspor.")
            return None
        path = filedialog.asksaveasfilename(
            defaultextension=ekstensi, initialfile=f"mahasiswa{ekstensi}",
            filetypes=[(jenis, f"*{ekstensi}")])
        return (baris, path) if path else None

    def ekspor_csv(self):
        hasil = self._siap_ekspor(".csv", "File CSV")
        if hasil is None:
            return
        baris, path = hasil
        try:
            # utf-8-sig agar Excel membaca huruf dengan benar
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(LABELS)
                w.writerows(baris)
        except OSError as e:
            messagebox.showerror("Gagal", f"File tidak bisa disimpan:\n{e}")
            return
        messagebox.showinfo("Berhasil", f"{len(baris)} data diekspor ke:\n{path}")

    def ekspor_excel(self):
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font
        except ImportError:
            messagebox.showerror(
                "openpyxl belum terpasang",
                "Jalankan di terminal:\n\npy -m pip install openpyxl\n\nlalu coba lagi.")
            return
        hasil = self._siap_ekspor(".xlsx", "File Excel")
        if hasil is None:
            return
        baris, path = hasil
        wb = Workbook()
        ws = wb.active
        ws.title = "Mahasiswa"
        ws.append(list(LABELS))
        for sel in ws[1]:
            sel.font = Font(bold=True)
        for b in baris:
            ws.append(list(b))  # NIM tetap berupa teks, angka 0 di depan aman
        for huruf, lebar in zip("ABCDEF", LEBAR):
            ws.column_dimensions[huruf].width = lebar / 6
        try:
            wb.save(path)
        except OSError as e:  # misalnya file sedang terbuka di Excel
            messagebox.showerror("Gagal", f"File tidak bisa disimpan:\n{e}")
            return
        messagebox.showinfo("Berhasil", f"{len(baris)} data diekspor ke:\n{path}")


if __name__ == "__main__":
    App().mainloop()
