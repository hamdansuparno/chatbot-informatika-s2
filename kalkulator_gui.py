#!/usr/bin/env python3
"""Kalkulator GUI (Tkinter).

Letakkan file ini satu folder dengan kalkulator.py, lalu jalankan:
    python kalkulator_gui.py
"""

import tkinter as tk
from tkinter import ttk

from kalkulator import format_hasil, hitung

TOMBOL = [
    ["C", "(", ")", "⌫"],
    ["sqrt(", "^", "%", "/"],
    ["7", "8", "9", "*"],
    ["4", "5", "6", "-"],
    ["1", "2", "3", "+"],
    ["ans", "0", ".", "="],
]


class KalkulatorGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Kalkulator")
        self.resizable(False, False)
        self.ans = 0
        self.riwayat = []

        self.var = tk.StringVar()
        self.info = tk.StringVar(value="Ketik atau klik tombol, Enter untuk hitung")

        frame = ttk.Frame(self, padding=10)
        frame.grid()

        self.entry = ttk.Entry(frame, textvariable=self.var, font=("Segoe UI", 20),
                               justify="right", width=18)
        self.entry.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 4))
        self.entry.focus()

        ttk.Label(frame, textvariable=self.info, foreground="#666",
                  wraplength=280).grid(row=1, column=0, columnspan=4, sticky="w")

        for r, baris in enumerate(TOMBOL, start=2):
            for c, teks in enumerate(baris):
                ttk.Button(frame, text=teks, width=7,
                           command=lambda t=teks: self.tekan(t)
                           ).grid(row=r, column=c, padx=2, pady=2, ipady=8)

        self.daftar = tk.Listbox(frame, height=5, font=("Consolas", 10))
        self.daftar.grid(row=len(TOMBOL) + 2, column=0, columnspan=4,
                         sticky="ew", pady=(8, 0))
        self.daftar.bind("<Double-Button-1>", self.pakai_riwayat)

        self.bind("<Return>", lambda e: self.selesai())
        self.bind("<Escape>", lambda e: self.var.set(""))

    def tekan(self, t):
        if t == "C":
            self.var.set("")
            self.info.set("")
        elif t == "⌫":
            self.var.set(self.var.get()[:-1])
        elif t == "=":
            self.selesai()
        else:
            self.entry.insert(tk.END, t)
        self.entry.focus()
        self.entry.icursor(tk.END)

    def selesai(self):
        teks = self.var.get().strip()
        if not teks:
            return
        try:
            nilai = hitung(teks, self.ans)
            hasil = format_hasil(nilai)
        except ZeroDivisionError:
            self.info.set("Error: tidak bisa membagi dengan nol")
            return
        except (ValueError, TypeError, SyntaxError, OverflowError) as err:
            self.info.set(f"Error: {err}")
            return
        self.ans = nilai
        self.daftar.insert(0, f"{teks} = {hasil}")
        self.var.set(hasil)
        self.info.set(f"Hasil: {hasil}")
        self.entry.icursor(tk.END)

    def pakai_riwayat(self, _):
        pilih = self.daftar.curselection()
        if pilih:
            hasil = self.daftar.get(pilih[0]).split(" = ")[-1]
            self.entry.insert(tk.END, hasil)


if __name__ == "__main__":
    KalkulatorGUI().mainloop()

