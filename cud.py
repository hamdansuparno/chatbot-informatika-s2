import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
from tkinter import ttk


class CUDApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CUD - Data Analysis")
        self.root.geometry("1100x650")

        self.df = None

        # Judul
        tk.Label(
            root,
            text="CUD - DATA ANALYSIS",
            font=("Arial", 20, "bold")
        ).pack(pady=10)

        # Tombol
        frame = tk.Frame(root)
        frame.pack(pady=5)

        tk.Button(
            frame,
            text="Buka CSV",
            width=15,
            command=self.buka_csv
        ).grid(row=0, column=0, padx=5)

        tk.Button(
            frame,
            text="Statistik",
            width=15,
            command=self.statistik
        ).grid(row=0, column=1, padx=5)

        tk.Button(
            frame,
            text="Cari Data",
            width=15,
            command=self.cari_data
        ).grid(row=0, column=2, padx=5)

        tk.Button(
            frame,
            text="Keluar",
            width=15,
            command=root.destroy
        ).grid(row=0, column=3, padx=5)

        # Kotak pencarian
        self.search = tk.Entry(root, width=50)
        self.search.pack(pady=5)
        self.search.insert(0, "Masukkan kata pencarian...")

        # Tabel
        table_frame = tk.Frame(root)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.tree = ttk.Treeview(table_frame)

        scrollbar_y = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.tree.yview
        )

        scrollbar_x = ttk.Scrollbar(
            table_frame,
            orient="horizontal",
            command=self.tree.xview
        )

        self.tree.configure(
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )

        scrollbar_y.pack(side="right", fill="y")
        scrollbar_x.pack(side="bottom", fill="x")

        self.tree.pack(fill="both", expand=True)

    def buka_csv(self):
        file = filedialog.askopenfilename(
            title="Pilih Dataset",
            filetypes=[
                ("CSV Files", "*.csv"),
                ("Excel Files", "*.xlsx"),
                ("All Files", "*.*")
            ]
        )

        if not file:
            return

        try:
            if file.endswith(".csv"):
                self.df = pd.read_csv(file)
            else:
                self.df = pd.read_excel(file)

            self.tampilkan_data(self.df)

            messagebox.showinfo(
                "Berhasil",
                f"Dataset berhasil dibuka.\n\n"
                f"Jumlah baris: {len(self.df)}\n"
                f"Jumlah kolom: {len(self.df.columns)}"
            )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Gagal membuka dataset:\n{e}"
            )

    def tampilkan_data(self, data):
        # Hapus tabel lama
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.tree["columns"] = list(data.columns)
        self.tree["show"] = "headings"

        for col in data.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)

        for _, row in data.iterrows():
            self.tree.insert(
                "",
                "end",
                values=list(row)
            )

    def cari_data(self):
        if self.df is None:
            messagebox.showwarning(
                "Peringatan",
                "Buka dataset terlebih dahulu."
            )
            return

        keyword = self.search.get().lower()

        if not keyword:
            self.tampilkan_data(self.df)
            return

        hasil = self.df[
            self.df.astype(str)
            .apply(
                lambda row: row.str.lower().str.contains(
                    keyword,
                    na=False
                ).any(),
                axis=1
            )
        ]

        self.tampilkan_data(hasil)

        messagebox.showinfo(
            "Pencarian",
            f"Ditemukan {len(hasil)} data."
        )

    def statistik(self):
        if self.df is None:
            messagebox.showwarning(
                "Peringatan",
                "Buka dataset terlebih dahulu."
            )
            return

        statistik = self.df.describe(include="all")

        window = tk.Toplevel(self.root)
        window.title("Statistik Dataset")
        window.geometry("1000x600")

        text = tk.Text(window, font=("Consolas", 10))
        text.pack(fill="both", expand=True)

        text.insert(
            "1.0",
            str(statistik)
        )


if __name__ == "__main__":
    root = tk.Tk()
    app = CUDApp(root)
    root.mainloop()
