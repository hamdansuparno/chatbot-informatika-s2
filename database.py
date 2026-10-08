"""
database.py - Lapisan database (SQLite) untuk sistem daftar & login.

Keamanan:
  - Password TIDAK disimpan polos. Disimpan sebagai hash PBKDF2-HMAC-SHA256
    dengan salt acak unik per pengguna (200.000 iterasi).
  - Pesan gagal login dibuat umum agar tidak membocorkan apakah username ada.
  - Akun terkunci 5 menit setelah 5 kali salah password.
  - Query memakai parameter (?), aman dari SQL injection.
"""
import hashlib
import hmac
import os
import re
import sqlite3
from datetime import datetime, timedelta

DB_FILE = "users.db"
ITERATIONS = 200_000
MAX_FAILED = 5
LOCK_MINUTES = 5

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{4,20}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _now():
    return datetime.now().replace(microsecond=0)


def hash_password(password, salt=None, iterations=ITERATIONS):
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return digest.hex(), salt.hex()


def validate_password(password):
    if len(password) < 8:
        raise ValueError("Password minimal 8 karakter.")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise ValueError("Password harus mengandung huruf dan angka.")


class UserDB:
    def __init__(self, path=DB_FILE):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                username        TEXT NOT NULL UNIQUE COLLATE NOCASE,
                nama_lengkap    TEXT NOT NULL,
                email           TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash   TEXT NOT NULL,
                salt            TEXT NOT NULL,
                iterations      INTEGER NOT NULL,
                created_at      TEXT NOT NULL,
                last_login      TEXT,
                failed_attempts INTEGER NOT NULL DEFAULT 0,
                locked_until    TEXT
            );
            CREATE TABLE IF NOT EXISTS login_log (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                waktu    TEXT NOT NULL,
                status   TEXT NOT NULL        -- 'berhasil' / 'gagal' / 'terkunci'
            );
            """
        )
        self.conn.commit()

    def _log(self, username, status):
        self.conn.execute(
            "INSERT INTO login_log (username, waktu, status) VALUES (?, ?, ?)",
            (username, _now().isoformat(sep=" "), status),
        )

    # ---------------------------------------------------------- daftar
    def register(self, username, nama, email, password):
        username, nama, email = username.strip(), nama.strip(), email.strip()
        if not USERNAME_RE.match(username):
            raise ValueError("Username 4-20 karakter: huruf, angka, atau underscore.")
        if not nama:
            raise ValueError("Nama lengkap wajib diisi.")
        if not EMAIL_RE.match(email):
            raise ValueError("Format email tidak valid.")
        validate_password(password)

        pw_hash, salt = hash_password(password)
        try:
            self.conn.execute(
                """INSERT INTO users (username, nama_lengkap, email, password_hash,
                                      salt, iterations, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (username, nama, email, pw_hash, salt, ITERATIONS,
                 _now().isoformat(sep=" ")),
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            self.conn.rollback()
            raise ValueError("Username atau email sudah terdaftar.")

    # ----------------------------------------------------------- login
    def login(self, username, password):
        """Mengembalikan dict data user bila berhasil, selain itu ValueError."""
        username = username.strip()
        generic = "Username atau password salah."
        row = self.conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        if row is None:
            self._log(username, "gagal")
            self.conn.commit()
            raise ValueError(generic)

        if row["locked_until"] and datetime.fromisoformat(row["locked_until"]) > _now():
            self._log(username, "terkunci")
            self.conn.commit()
            raise ValueError(
                f"Akun terkunci sementara hingga {row['locked_until'][11:]}. "
                "Coba lagi nanti.")

        calc, _ = hash_password(password, bytes.fromhex(row["salt"]), row["iterations"])
        if not hmac.compare_digest(calc, row["password_hash"]):
            fails = row["failed_attempts"] + 1
            locked = None
            if fails >= MAX_FAILED:
                locked = (_now() + timedelta(minutes=LOCK_MINUTES)).isoformat(sep=" ")
                fails = 0
            self.conn.execute(
                "UPDATE users SET failed_attempts=?, locked_until=? WHERE id=?",
                (fails, locked, row["id"]))
            self._log(username, "gagal")
            self.conn.commit()
            if locked:
                raise ValueError(f"Terlalu banyak percobaan. Akun dikunci {LOCK_MINUTES} menit.")
            raise ValueError(f"{generic} Sisa percobaan: {MAX_FAILED - fails}.")

        prev_login = row["last_login"]
        self.conn.execute(
            "UPDATE users SET failed_attempts=0, locked_until=NULL, last_login=? WHERE id=?",
            (_now().isoformat(sep=" "), row["id"]))
        self._log(row["username"], "berhasil")
        self.conn.commit()
        return {"id": row["id"], "username": row["username"], "nama": row["nama_lengkap"],
                "email": row["email"], "last_login": prev_login,
                "created_at": row["created_at"]}

    # --------------------------------------------------- ganti password
    def change_password(self, username, old_password, new_password):
        row = self.conn.execute(
            "SELECT password_hash, salt, iterations FROM users WHERE username = ?",
            (username,)).fetchone()
        if row is None:
            raise ValueError("User tidak ditemukan.")
        calc, _ = hash_password(old_password, bytes.fromhex(row["salt"]), row["iterations"])
        if not hmac.compare_digest(calc, row["password_hash"]):
            raise ValueError("Password lama salah.")
        validate_password(new_password)
        pw_hash, salt = hash_password(new_password)
        self.conn.execute(
            "UPDATE users SET password_hash=?, salt=?, iterations=? WHERE username=?",
            (pw_hash, salt, ITERATIONS, username))
        self.conn.commit()

    def close(self):
        self.conn.close()
