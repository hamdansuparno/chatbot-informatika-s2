"""
db_data.py - Lapisan database (SQLite) untuk program pencarian data.

Tabel `mahasiswa` diisi 20 data contoh saat pertama kali dibuat.
Pencarian:
  - tidak peka huruf besar/kecil
  - bisa memakai beberapa kata sekaligus (semua kata harus cocok), mis. "informatika B"
  - bisa mencari di semua kolom atau satu kolom tertentu
  - aman dari SQL injection (parameter ?, kolom urut di-whitelist)
"""
import re
import sqlite3

DB_FILE = "data.db"
COLUMNS = ["nim", "nama", "jurusan", "kelas", "angkatan", "email"]
FIELDS = {"Semua kolom": None, "NIM": "nim", "Nama": "nama", "Jurusan": "jurusan",
          "Kelas": "kelas", "Angkatan": "angkatan", "Email": "email"}

SAMPLE = [
    ("2201001", "Andi Prasetyo", "Teknik Informatika", "A", 2022, "andi.p@kampus.ac.id"),
    ("2201002", "Budi Santoso", "Teknik Informatika", "B", 2022, "budi.s@kampus.ac.id"),
    ("2201003", "Citra Dewi", "Sistem Informasi", "A", 2022, "citra.d@kampus.ac.id"),
    ("2201004", "Dimas Aditya", "Teknik Elektro", "C", 2022, "dimas.a@kampus.ac.id"),
    ("2201005", "Eka Wulandari", "Manajemen", "B", 2022, "eka.w@kampus.ac.id"),
    ("2301001", "Fajar Nugroho", "Teknik Informatika", "A", 2023, "fajar.n@kampus.ac.id"),
    ("2301002", "Gita Lestari", "Sistem Informasi", "B", 2023, "gita.l@kampus.ac.id"),
    ("2301003", "Hendra Wijaya", "Akuntansi", "A", 2023, "hendra.w@kampus.ac.id"),
    ("2301004", "Intan Permata", "Teknik Informatika", "B", 2023, "intan.p@kampus.ac.id"),
    ("2301005", "Joko Susilo", "Teknik Elektro", "A", 2023, "joko.s@kampus.ac.id"),
    ("2401001", "Kartika Sari", "Manajemen", "A", 2024, "kartika.s@kampus.ac.id"),
    ("2401002", "Lukman Hakim", "Teknik Informatika", "C", 2024, "lukman.h@kampus.ac.id"),
    ("2401003", "Maya Anggraini", "Sistem Informasi", "A", 2024, "maya.a@kampus.ac.id"),
    ("2401004", "Nanda Putra", "Akuntansi", "B", 2024, "nanda.p@kampus.ac.id"),
    ("2401005", "Oktaviani Rahma", "Teknik Informatika", "A", 2024, "okta.r@kampus.ac.id"),
    ("2501001", "Putri Ayu", "Sistem Informasi", "B", 2025, "putri.a@kampus.ac.id"),
    ("2501002", "Rizky Ramadhan", "Teknik Elektro", "B", 2025, "rizky.r@kampus.ac.id"),
    ("2501003", "Siti Nurhaliza", "Manajemen", "C", 2025, "siti.n@kampus.ac.id"),
    ("2501004", "Teguh Prakoso", "Teknik Informatika", "B", 2025, "teguh.p@kampus.ac.id"),
    ("2501005", "Wahyu Hidayat", "Akuntansi", "A", 2025, "wahyu.h@kampus.ac.id"),
]


def _escape_like(s):
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class DataDB:
    def __init__(self, path=DB_FILE):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS mahasiswa (
                   id       INTEGER PRIMARY KEY AUTOINCREMENT,
                   nim      TEXT NOT NULL UNIQUE,
                   nama     TEXT NOT NULL,
                   jurusan  TEXT,
                   kelas    TEXT,
                   angkatan INTEGER,
                   email    TEXT)""")
        if self.count() == 0:
            self.conn.executemany(
                "INSERT INTO mahasiswa (nim,nama,jurusan,kelas,angkatan,email) "
                "VALUES (?,?,?,?,?,?)", SAMPLE)
        self.conn.commit()

    def count(self):
        return self.conn.execute("SELECT COUNT(*) FROM mahasiswa").fetchone()[0]

    # --------------------------------------------------------------- cari
    def search(self, keyword="", column=None, order="nama", desc=False):
        cols = [column] if column in COLUMNS else COLUMNS
        order = order if order in COLUMNS else "nama"
        sql = "SELECT * FROM mahasiswa"
        params, clauses = [], []
        for word in keyword.split():
            like = f"%{_escape_like(word)}%"
            clauses.append("(" + " OR ".join(
                f"CAST({c} AS TEXT) LIKE ? ESCAPE '\\'" for c in cols) + ")")
            params += [like] * len(cols)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += f" ORDER BY {order} COLLATE NOCASE {'DESC' if desc else 'ASC'}"
        return self.conn.execute(sql, params).fetchall()

    # ---------------------------------------------------------- CRUD
    @staticmethod
    def _validate(nim, nama, angkatan, email):
        if not nim.strip():
            raise ValueError("NIM wajib diisi.")
        if not nama.strip():
            raise ValueError("Nama wajib diisi.")
        if angkatan.strip() and not re.fullmatch(r"\d{4}", angkatan.strip()):
            raise ValueError("Angkatan harus 4 digit, mis. 2024.")
        if email.strip() and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email.strip()):
            raise ValueError("Format email tidak valid.")

    def add(self, nim, nama, jurusan, kelas, angkatan, email):
        self._validate(nim, nama, angkatan, email)
        try:
            self.conn.execute(
                "INSERT INTO mahasiswa (nim,nama,jurusan,kelas,angkatan,email) "
                "VALUES (?,?,?,?,?,?)",
                (nim.strip(), nama.strip(), jurusan.strip(), kelas.strip(),
                 int(angkatan) if angkatan.strip() else None, email.strip()))
            self.conn.commit()
        except sqlite3.IntegrityError:
            self.conn.rollback()
            raise ValueError("NIM sudah terdaftar.")

    def update(self, id_, nim, nama, jurusan, kelas, angkatan, email):
        self._validate(nim, nama, angkatan, email)
        try:
            self.conn.execute(
                "UPDATE mahasiswa SET nim=?,nama=?,jurusan=?,kelas=?,angkatan=?,email=? "
                "WHERE id=?",
                (nim.strip(), nama.strip(), jurusan.strip(), kelas.strip(),
                 int(angkatan) if angkatan.strip() else None, email.strip(), id_))
            self.conn.commit()
        except sqlite3.IntegrityError:
            self.conn.rollback()
            raise ValueError("NIM sudah dipakai data lain.")

    def delete(self, id_):
        self.conn.execute("DELETE FROM mahasiswa WHERE id=?", (id_,))
        self.conn.commit()

    def close(self):
        self.conn.close()
