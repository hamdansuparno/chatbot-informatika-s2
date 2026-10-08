"""
login_app.py - Program Daftar & Login (Python + tkinter + SQLite).

Jalankan:  python login_app.py
Butuh file database.py di folder yang sama. Database dibuat otomatis (users.db).
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from database import UserDB

FONT = "Segoe UI"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sistem Login")
        self.geometry("420x520")
        self.resizable(False, False)
        self.db = UserDB()

        style = ttk.Style(self)
        style.theme_use("vista" if "vista" in style.theme_names() else "clam")
        self.option_add("*Font", (FONT, 10))
        style.configure("Judul.TLabel", font=(FONT, 18, "bold"), foreground="#0b5cad")
        style.configure("Sub.TLabel", foreground="#555555")

        self.container = ttk.Frame(self, padding=20)
        self.container.pack(fill="both", expand=True)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.show_auth()

    def clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    # ------------------------------------------------- halaman login/daftar
    def show_auth(self):
        self.clear()
        ttk.Label(self.container, text="Selamat Datang", style="Judul.TLabel").pack()
        ttk.Label(self.container, text="Silakan login atau buat akun baru",
                  style="Sub.TLabel").pack(pady=(0, 12))

        nb = ttk.Notebook(self.container)
        nb.pack(fill="both", expand=True)
        tab_login = ttk.Frame(nb, padding=16)
        tab_daftar = ttk.Frame(nb, padding=16)
        nb.add(tab_login, text="Login")
        nb.add(tab_daftar, text="Daftar")
        self._build_login(tab_login)
        self._build_register(tab_daftar, nb, tab_login)

    def _field(self, parent, label, secret=False):
        ttk.Label(parent, text=label).pack(anchor="w", pady=(8, 2))
        e = ttk.Entry(parent, show="•" if secret else "")
        e.pack(fill="x")
        return e

    def _show_pw_check(self, parent, entries):
        var = tk.BooleanVar()

        def toggle():
            for e in entries:
                e.config(show="" if var.get() else "•")
        ttk.Checkbutton(parent, text="Tampilkan password", variable=var,
                        command=toggle).pack(anchor="w", pady=(8, 0))

    def _build_login(self, f):
        self.l_user = self._field(f, "Username")
        self.l_pass = self._field(f, "Password", secret=True)
        self._show_pw_check(f, [self.l_pass])
        ttk.Button(f, text="Login", command=self.do_login).pack(fill="x", pady=(18, 0))
        self.l_user.focus_set()
        for e in (self.l_user, self.l_pass):
            e.bind("<Return>", lambda ev: self.do_login())

    def _build_register(self, f, nb, tab_login):
        self.r_nama = self._field(f, "Nama lengkap")
        self.r_email = self._field(f, "Email")
        self.r_user = self._field(f, "Username")
        self.r_pass = self._field(f, "Password (min. 8, huruf + angka)", secret=True)
        self.r_pass2 = self._field(f, "Ulangi password", secret=True)
        self._show_pw_check(f, [self.r_pass, self.r_pass2])
        ttk.Button(f, text="Daftar", command=lambda: self.do_register(nb, tab_login)).pack(
            fill="x", pady=(14, 0))

    # ---------------------------------------------------------------- aksi
    def do_register(self, nb, tab_login):
        if self.r_pass.get() != self.r_pass2.get():
            return messagebox.showwarning("Daftar", "Konfirmasi password tidak sama.")
        try:
            self.db.register(self.r_user.get(), self.r_nama.get(),
                             self.r_email.get(), self.r_pass.get())
        except ValueError as err:
            return messagebox.showwarning("Daftar", str(err))
        messagebox.showinfo("Daftar", "Akun berhasil dibuat. Silakan login.")
        username = self.r_user.get().strip()
        for e in (self.r_nama, self.r_email, self.r_user, self.r_pass, self.r_pass2):
            e.delete(0, "end")
        nb.select(tab_login)
        self.l_user.delete(0, "end")
        self.l_user.insert(0, username)
        self.l_pass.focus_set()

    def do_login(self):
        try:
            user = self.db.login(self.l_user.get(), self.l_pass.get())
        except ValueError as err:
            self.l_pass.delete(0, "end")
            return messagebox.showerror("Login gagal", str(err))
        self.show_home(user)

    # --------------------------------------------------------- halaman utama
    def show_home(self, user):
        self.clear()
        ttk.Label(self.container, text=f"Halo, {user['nama']}!",
                  style="Judul.TLabel").pack(pady=(30, 4))
        ttk.Label(self.container, text="Anda berhasil login.", style="Sub.TLabel").pack()

        box = ttk.LabelFrame(self.container, text="Info akun", padding=14)
        box.pack(fill="x", pady=24)
        rows = [("Username", user["username"]), ("Email", user["email"]),
                ("Terdaftar", user["created_at"]),
                ("Login sebelumnya", user["last_login"] or "Ini login pertama Anda")]
        for i, (k, v) in enumerate(rows):
            ttk.Label(box, text=k + ":").grid(row=i, column=0, sticky="w", pady=3)
            ttk.Label(box, text=v).grid(row=i, column=1, sticky="w", padx=10)

        ttk.Button(self.container, text="Ganti password",
                   command=lambda: self.ganti_password(user["username"])).pack(fill="x", pady=4)
        ttk.Button(self.container, text="Logout", command=self.show_auth).pack(fill="x", pady=4)

    def ganti_password(self, username):
        old = simpledialog.askstring("Ganti password", "Password lama:", show="•", parent=self)
        if old is None:
            return
        new = simpledialog.askstring("Ganti password", "Password baru:", show="•", parent=self)
        if new is None:
            return
        try:
            self.db.change_password(username, old, new)
        except ValueError as err:
            return messagebox.showwarning("Ganti password", str(err))
        messagebox.showinfo("Ganti password", "Password berhasil diubah.")

    def on_close(self):
        self.db.close()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
