"""
crud_mahasiswa.py
=================
Aplikasi CRUD (Create, Read, Update, Delete) dengan GUI Tkinter + SQLite.
Tidak perlu instal paket tambahan: tkinter dan sqlite3 sudah bawaan Python.

Jalankan:  python crud_mahasiswa.py
Data tersimpan di file mahasiswa.db (dibuat otomatis di folder yang sama).
"""

import sqlite3
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

DB_FILE = Path(__file__).with_name("mahasiswa.db")
FIELDS = ("nim", "nama", "jurusan")


class Database:
    """Lapisan data: semua perintah SQL ada di sini."""

    def __init__(self, path):
        self.con = sqlite3.connect(path)
        self.con.execute(
            """CREATE TABLE IF NOT EXISTS mahasiswa (
                   id      INTEGER PRIMARY KEY AUTOINCREMENT,
                   nim     TEXT NOT NULL UNIQUE,
                   nama    TEXT NOT NULL,
                   jurusan TEXT)"""
        )
        self.con.commit()

    def semua(self, kata=""):  # READ (daftar + pencarian)
        like = f"%{kata}%"
        return self.con.execute(
            "SELECT id, nim, nama, jurusan FROM mahasiswa "
            "WHERE nim LIKE ? OR nama LIKE ? OR jurusan LIKE ? ORDER BY nim",
            (like, like, like),
        ).fetchall()

    def satu(self, id_):  # READ (satu baris)
        return self.con.execute(
            "SELECT nim, nama, jurusan FROM mahasiswa WHERE id = ?", (id_,)
        ).fetchone()

    def tambah(self, nim, nama, jurusan):  # CREATE
        with self.con:
            self.con.execute(
                "INSERT INTO mahasiswa (nim, nama, jurusan) VALUES (?, ?, ?)",
                (nim, nama, jurusan),
            )

    def ubah(self, id_, nim, nama, jurusan):  # UPDATE
        with self.con:
            self.con.execute(
                "UPDATE mahasiswa SET nim = ?, nama = ?, jurusan = ? WHERE id = ?",
                (nim, nama, jurusan, id_),
            )

    def hapus(self, id_):  # DELETE
        with self.con:
            self.con.execute("DELETE FROM mahasiswa WHERE id = ?", (id_,))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CRUD Data Mahasiswa")
        self.geometry("720x480")
        self.minsize(640, 420)
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
        for i, (k, label) in enumerate(zip(FIELDS, ("NIM", "Nama", "Jurusan"))):
            ttk.Label(box, text=label).grid(row=i, column=0, sticky="w", pady=3)
            ttk.Entry(box, textvariable=self.var[k]).grid(
                row=i, column=1, sticky="ew", padx=(8, 0), pady=3)

        tombol = ttk.Frame(box)
        tombol.grid(row=3, column=0, columnspan=2, pady=(8, 0), sticky="w")
        for teks, perintah in (("Tambah", self.tambah), ("Ubah", self.ubah),
                               ("Hapus", self.hapus), ("Bersihkan", self.bersihkan)):
            ttk.Button(tombol, text=teks, command=perintah).pack(side="left", padx=(0, 6))

    def _buat_tabel(self):
        cari = ttk.Frame(self)
        cari.pack(fill="x", padx=12)
        ttk.Label(cari, text="Cari:").pack(side="left")
        ttk.Entry(cari, textvariable=self.var_cari).pack(side="left", fill="x", expand=True, padx=6)

        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=12, pady=8)
        self.tabel = ttk.Treeview(frame, columns=FIELDS, show="headings", selectmode="browse")
        for k, lebar in zip(FIELDS, (120, 260, 200)):
            self.tabel.heading(k, text=k.upper())
            self.tabel.column(k, width=lebar, anchor="w")
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.tabel.yview)
        self.tabel.configure(yscrollcommand=scroll.set)
        self.tabel.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.tabel.bind("<<TreeviewSelect>>", self.pilih)

    # ------------------------------------------------------------- aksi
    def _ambil(self):
        return tuple(self.var[k].get().strip() for k in FIELDS)

    def muat(self):
        self.tabel.delete(*self.tabel.get_children())
        for id_, nim, nama, jurusan in self.db.semua(self.var_cari.get().strip()):
            self.tabel.insert("", "end", iid=str(id_), values=(nim, nama, jurusan))

    def pilih(self, _event=None):
        pilihan = self.tabel.selection()
        if not pilihan:
            return
        self.id_terpilih = int(pilihan[0])
        # Ambil dari database (bukan dari tabel) agar NIM berawalan 0 tidak berubah
        for k, nilai in zip(FIELDS, self.db.satu(self.id_terpilih)):
            self.var[k].set(nilai)

    def bersihkan(self):
        for v in self.var.values():
            v.set("")
        self.id_terpilih = None
        self.tabel.selection_remove(*self.tabel.selection())

    def tambah(self):
        nim, nama, jurusan = self._ambil()
        if not nim or not nama:
            messagebox.showwarning("Peringatan", "NIM dan Nama wajib diisi.")
            return
        try:
            self.db.tambah(nim, nama, jurusan)
        except sqlite3.IntegrityError:
            messagebox.showerror("Gagal", f"NIM {nim} sudah ada.")
            return
        self.bersihkan()
        self.muat()

    def ubah(self):
        if self.id_terpilih is None:
            messagebox.showwarning("Peringatan", "Pilih data di tabel terlebih dahulu.")
            return
        nim, nama, jurusan = self._ambil()
        if not nim or not nama:
            messagebox.showwarning("Peringatan", "NIM dan Nama wajib diisi.")
            return
        try:
            self.db.ubah(self.id_terpilih, nim, nama, jurusan)
        except sqlite3.IntegrityError:
            messagebox.showerror("Gagal", f"NIM {nim} sudah dipakai data lain.")
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


if __name__ == "__main__":
    App().mainloop()