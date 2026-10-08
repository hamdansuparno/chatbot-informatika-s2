"""
Kalkulator Luas Segitiga - GUI bergaya Windows (Python + tkinter).

Fitur:
  - Tab 1: Luas dari alas dan tinggi          L = 1/2 x alas x tinggi
  - Tab 2: Luas dari tiga sisi (Heron)        L = sqrt(s(s-a)(s-b)(s-c))
  - Gambar segitiga otomatis (skala menyesuaikan jendela), garis tinggi,
    siku-siku, titik sudut A-B-C, dan label ukuran
  - Menu bar, status bar, pilihan satuan, validasi input

Jalankan:  python luas_segitiga.py     (hanya butuh Python 3 bawaan, tanpa pip)
"""
import math
import tkinter as tk
from tkinter import ttk, messagebox

FONT = "Segoe UI"


def fmt(x):
    """Format angka gaya Indonesia: 2 desimal, koma sebagai desimal."""
    s = f"{x:.2f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Kalkulator Luas Segitiga")
        self.geometry("900x540")
        self.minsize(800, 500)
        self.configure(bg="#f0f0f0")

        style = ttk.Style(self)
        style.theme_use("vista" if "vista" in style.theme_names() else "clam")
        self.option_add("*Font", (FONT, 10))
        style.configure("Hasil.TLabel", font=(FONT, 20, "bold"), foreground="#0b5cad")
        style.configure("Judul.TLabel", font=(FONT, 14, "bold"))

        self.pts = ((0, 0), (8, 0), (2.8, 5))
        self.labels = {"base": "alas", "height": "tinggi"}

        self._menu()
        self._layout()
        self.canvas.bind("<Configure>", lambda e: self.draw())
        self.set_status("Siap")

    # ------------------------------------------------------------------ UI
    def _menu(self):
        bar = tk.Menu(self)
        file_m = tk.Menu(bar, tearoff=0)
        file_m.add_command(label="Reset semua", command=self.reset_all)
        file_m.add_separator()
        file_m.add_command(label="Keluar", command=self.destroy)
        bar.add_cascade(label="File", menu=file_m)
        help_m = tk.Menu(bar, tearoff=0)
        help_m.add_command(label="Rumus", command=self.show_rumus)
        help_m.add_command(label="Tentang", command=self.show_about)
        bar.add_cascade(label="Bantuan", menu=help_m)
        self.config(menu=bar)

    def _layout(self):
        left = ttk.Frame(self, padding=(12, 12, 6, 6))
        left.pack(side="left", fill="y")
        right = ttk.Frame(self, padding=(6, 12, 12, 6))
        right.pack(side="left", fill="both", expand=True)

        ttk.Label(left, text="Luas Segitiga", style="Judul.TLabel").pack(anchor="w")
        ttk.Label(left, text="Pilih metode, isi ukuran, lalu klik Hitung.",
                  foreground="#555").pack(anchor="w", pady=(0, 10))

        unit_row = ttk.Frame(left)
        unit_row.pack(fill="x", pady=(0, 8))
        ttk.Label(unit_row, text="Satuan:").pack(side="left")
        self.unit = tk.StringVar(value="cm")
        ttk.Combobox(unit_row, textvariable=self.unit, width=6, state="readonly",
                     values=["mm", "cm", "m", "km"]).pack(side="left", padx=8)

        nb = ttk.Notebook(left)
        nb.pack(fill="x")
        tab1 = ttk.Frame(nb)
        tab2 = ttk.Frame(nb)
        nb.add(tab1, text="Alas & Tinggi")
        nb.add(tab2, text="Tiga Sisi (Heron)")
        self.e1 = self._make_tab(tab1, ["Alas", "Tinggi"], self.hitung_alas_tinggi)
        self.e2 = self._make_tab(tab2, ["Sisi a", "Sisi b", "Sisi c"], self.hitung_heron)

        box = ttk.LabelFrame(left, text="Hasil", padding=10)
        box.pack(fill="x", pady=(12, 0))
        self.var_hasil = tk.StringVar(value="-")
        self.var_detail = tk.StringVar(value="Belum ada perhitungan.")
        ttk.Label(box, textvariable=self.var_hasil, style="Hasil.TLabel").pack(anchor="w")
        ttk.Label(box, textvariable=self.var_detail, justify="left",
                  wraplength=300, foreground="#333").pack(anchor="w", pady=(6, 0))

        ttk.Button(left, text="Keluar", command=self.destroy, width=12).pack(
            anchor="e", pady=(12, 0))

        self.canvas = tk.Canvas(right, bg="white", highlightthickness=1,
                                highlightbackground="#a0a0a0")
        self.canvas.pack(fill="both", expand=True)

        self.status = tk.StringVar()
        ttk.Label(self, textvariable=self.status, relief="sunken", anchor="w",
                  padding=(8, 2)).pack(side="bottom", fill="x")

    def _make_tab(self, parent, fields, command):
        entries = []
        for i, txt in enumerate(fields):
            ttk.Label(parent, text=txt).grid(row=i, column=0, sticky="w",
                                             padx=(12, 6), pady=8)
            e = ttk.Entry(parent, width=14)
            e.grid(row=i, column=1, sticky="ew", padx=(0, 12), pady=8)
            e.bind("<Return>", lambda ev: command())
            entries.append(e)
        parent.columnconfigure(1, weight=1)
        btns = ttk.Frame(parent)
        btns.grid(row=len(fields), column=0, columnspan=2, pady=(6, 12))
        ttk.Button(btns, text="Hitung", width=12, command=command).pack(side="left", padx=4)
        ttk.Button(btns, text="Reset", width=12,
                   command=lambda: self.reset_entries(entries)).pack(side="left", padx=4)
        return entries

    # ------------------------------------------------------------ perhitungan
    @staticmethod
    def _num(entry, nama):
        s = entry.get().strip().replace(",", ".")
        try:
            v = float(s)
        except ValueError:
            raise ValueError(f"{nama} harus berupa angka.")
        if v <= 0:
            raise ValueError(f"{nama} harus lebih besar dari 0.")
        return v

    def hitung_alas_tinggi(self):
        try:
            a = self._num(self.e1[0], "Alas")
            t = self._num(self.e1[1], "Tinggi")
        except ValueError as err:
            return self.error(str(err))
        u = self.unit.get()
        luas = 0.5 * a * t
        self.var_hasil.set(f"{fmt(luas)} {u}²")
        self.var_detail.set(f"L = ½ × alas × tinggi\n  = ½ × {fmt(a)} × {fmt(t)}\n  = {fmt(luas)} {u}²")
        self.pts = ((0, 0), (a, 0), (a * 0.35, t))
        self.labels = {"base": f"alas = {fmt(a)} {u}", "height": f"t = {fmt(t)} {u}"}
        self.draw()
        self.set_status(f"Luas = {fmt(luas)} {u}²")

    def hitung_heron(self):
        try:
            a = self._num(self.e2[0], "Sisi a")
            b = self._num(self.e2[1], "Sisi b")
            c = self._num(self.e2[2], "Sisi c")
        except ValueError as err:
            return self.error(str(err))
        if a + b <= c or a + c <= b or b + c <= a:
            return self.error("Ketiga sisi tidak membentuk segitiga.\n"
                              "Jumlah dua sisi harus lebih besar dari sisi ketiga.")
        u = self.unit.get()
        s = (a + b + c) / 2
        luas = math.sqrt(s * (s - a) * (s - b) * (s - c))
        self.var_hasil.set(f"{fmt(luas)} {u}²")
        self.var_detail.set(
            f"s = (a + b + c) / 2 = {fmt(s)}\n"
            f"L = √[s(s−a)(s−b)(s−c)]\n"
            f"  = √[{fmt(s)} × {fmt(s-a)} × {fmt(s-b)} × {fmt(s-c)}]\n"
            f"  = {fmt(luas)} {u}²")
        x = (b * b + c * c - a * a) / (2 * c)
        y = math.sqrt(max(b * b - x * x, 0))
        self.pts = ((0, 0), (c, 0), (x, y))
        self.labels = {"ab": f"c = {fmt(c)}", "bc": f"a = {fmt(a)}", "ca": f"b = {fmt(b)}"}
        self.draw()
        self.set_status(f"Luas = {fmt(luas)} {u}²")

    # -------------------------------------------------------------- gambar
    def draw(self):
        c = self.canvas
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if w < 100 or h < 100:
            return

        top, bot = (206, 228, 252), (255, 255, 255)
        for y in range(0, h, 3):
            t = y / h
            col = "#%02x%02x%02x" % tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
            c.create_rectangle(0, y, w, y + 3, fill=col, outline=col)
        for gx in range(0, w, 32):
            c.create_line(gx, 0, gx, h, fill="#d6e6f7")
        for gy in range(0, h, 32):
            c.create_line(0, gy, w, gy, fill="#d6e6f7")

        (ax, ay), (bx, by), (cx, cy) = self.pts
        minx, maxx = min(ax, bx, cx), max(ax, bx, cx)
        maxy = max(cy, 1e-9)
        pad_x, pad_y = 90, 90
        s = min((w - 2 * pad_x) / max(maxx - minx, 1e-9), (h - 2 * pad_y) / maxy)
        off_x = (w - (maxx - minx) * s) / 2
        base_y = h - (h - maxy * s) / 2

        def P(px, py):
            return off_x + (px - minx) * s, base_y - py * s

        A, B, C = P(ax, ay), P(bx, by), P(cx, cy)
        F = P(cx, 0)

        c.create_polygon(A[0] + 6, A[1] + 6, B[0] + 6, B[1] + 6, C[0] + 6, C[1] + 6,
                         fill="#b7c4d4", outline="")
        c.create_polygon(*A, *B, *C, fill="#7fb4f2", outline="#0b5cad",
                         width=3, joinstyle="round")

        if cy > 0:
            c.create_line(*C, *F, fill="#c0392b", width=2, dash=(6, 4))
            d = 12 if cx < (ax + bx) / 2 else -12
            c.create_line(F[0] + d, F[1], F[0] + d, F[1] - 12, F[0], F[1] - 12,
                          fill="#c0392b", width=1.5)
            if bx < cx or cx < ax:
                c.create_line(A[0], A[1], B[0], B[1], fill="#0b5cad", width=3)

        for (px, py), name, dx, dy in ((A, "A", -16, 8), (B, "B", 16, 8), (C, "C", 0, -16)):
            c.create_oval(px - 5, py - 5, px + 5, py + 5, fill="white",
                          outline="#0b5cad", width=2)
            c.create_text(px + dx, py + dy, text=name, fill="#0b3d75",
                          font=(FONT, 13, "bold"))

        lb = self.labels
        if "base" in lb:
            c.create_text((A[0] + B[0]) / 2, A[1] + 30, text=lb["base"],
                          fill="#0b3d75", font=(FONT, 12, "bold"))
            c.create_text(F[0] + (20 if cx < (ax + bx) / 2 else -20) + 10,
                          (C[1] + F[1]) / 2, text=lb["height"], anchor="w" if cx < (ax + bx) / 2 else "e",
                          fill="#c0392b", font=(FONT, 12, "bold"))
        if "ab" in lb:
            c.create_text((A[0] + B[0]) / 2, A[1] + 30, text=lb["ab"],
                          fill="#0b3d75", font=(FONT, 12, "bold"))
            c.create_text((B[0] + C[0]) / 2 + 28, (B[1] + C[1]) / 2 - 8, text=lb["bc"],
                          fill="#0b3d75", font=(FONT, 12, "bold"))
            c.create_text((A[0] + C[0]) / 2 - 28, (A[1] + C[1]) / 2 - 8, text=lb["ca"],
                          fill="#0b3d75", font=(FONT, 12, "bold"))

        c.create_text(14, 12, anchor="nw", text="Visualisasi Segitiga",
                      fill="#0b3d75", font=(FONT, 12, "bold"))

    # --------------------------------------------------------------- utilitas
    def set_status(self, text):
        self.status.set("  " + text)

    def error(self, msg):
        messagebox.showwarning("Input tidak valid", msg, parent=self)
        self.set_status("Input tidak valid")

    def reset_entries(self, entries):
        for e in entries:
            e.delete(0, "end")
        entries[0].focus_set()
        self.var_hasil.set("-")
        self.var_detail.set("Belum ada perhitungan.")
        self.pts = ((0, 0), (8, 0), (2.8, 5))
        self.labels = {"base": "alas", "height": "tinggi"}
        self.draw()
        self.set_status("Siap")

    def reset_all(self):
        self.reset_entries(self.e2)
        self.reset_entries(self.e1)

    def show_rumus(self):
        messagebox.showinfo(
            "Rumus Luas Segitiga",
            "1. Alas & tinggi\n    L = ½ × alas × tinggi\n\n"
            "2. Tiga sisi (rumus Heron)\n    s = (a + b + c) / 2\n"
            "    L = √[s(s−a)(s−b)(s−c)]", parent=self)

    def show_about(self):
        messagebox.showinfo("Tentang", "Kalkulator Luas Segitiga\nPython + tkinter", parent=self)


if __name__ == "__main__":
    App().mainloop()
