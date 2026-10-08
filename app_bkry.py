```python
"""
===========================================================
 APPBAKRY / FRAMEGABKRY
 Aplikasi Analisis Data Python dalam SATU FILE

 Jalankan:
     python framegabkry.py

 Instalasi library:
     pip install pandas openpyxl matplotlib scikit-learn
===========================================================
"""

import os
import sqlite3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import pandas as pd

# Matplotlib
try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    MATPLOTLIB = True
except ImportError:
    MATPLOTLIB = False

# Scikit-learn
try:
    from sklearn.model_selection import train_test_split
    from sklearn.naive_bayes import GaussianNB
    from sklearn.metrics import accuracy_score, classification_report
    from sklearn.linear_model import LinearRegression
    SKLEARN = True
except ImportError:
    SKLEARN = False


# =========================================================
# KONFIGURASI
# =========================================================

APP_NAME = "APPBAKRY"
VERSION = "1.0.0"
DATABASE = "appbakry.db"


# =========================================================
# DATABASE
# =========================================================

def init_database():
    conn = sqlite3.connect(DATABASE)

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            rows_count INTEGER,
            columns_count INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def save_history(filename, rows, columns):
    conn = sqlite3.connect(DATABASE)

    conn.execute(
        """
        INSERT INTO history
        (filename, rows_count, columns_count)
        VALUES (?, ?, ?)
        """,
        (filename, rows, columns)
    )

    conn.commit()
    conn.close()


# =========================================================
# APLIKASI
# =========================================================

class AppBakry:

    def __init__(self, root):

        self.root = root

        self.root.title(
            f"{APP_NAME} - FrameGabkry"
        )

        self.root.geometry("1250x750")

        self.root.minsize(1000, 600)

        self.df = None
        self.filename = ""

        self.create_menu()
        self.create_header()
        self.create_toolbar()
        self.create_table()
        self.create_statusbar()

    # =====================================================
    # MENU
    # =====================================================

    def create_menu(self):

        menu = tk.Menu(self.root)

        self.root.config(menu=menu)

        # File
        file_menu = tk.Menu(
            menu,
            tearoff=0
        )

        file_menu.add_command(
            label="Buka CSV",
            command=self.open_csv
        )

        file_menu.add_command(
            label="Buka Excel",
            command=self.open_excel
        )

        file_menu.add_separator()

        file_menu.add_command(
            label="Export CSV",
            command=self.export_csv
        )

        file_menu.add_command(
            label="Export Excel",
            command=self.export_excel
        )

        file_menu.add_separator()

        file_menu.add_command(
            label="Keluar",
            command=self.root.destroy
        )

        menu.add_cascade(
            label="File",
            menu=file_menu
        )

        # Analisis
        analysis_menu = tk.Menu(
            menu,
            tearoff=0
        )

        analysis_menu.add_command(
            label="Statistik",
            command=self.show_statistics
        )

        analysis_menu.add_command(
            label="Grafik",
            command=self.show_graph
        )

        analysis_menu.add_command(
            label="Naive Bayes",
            command=self.naive_bayes
        )

        analysis_menu.add_command(
            label="Regresi Linear",
            command=self.linear_regression
        )

        menu.add_cascade(
            label="Analisis",
            menu=analysis_menu
        )

        # Database
        database_menu = tk.Menu(
            menu,
            tearoff=0
        )

        database_menu.add_command(
            label="Riwayat Dataset",
            command=self.show_history
        )

        menu.add_cascade(
            label="Database",
            menu=database_menu
        )

        # Bantuan
        help_menu = tk.Menu(
            menu,
            tearoff=0
        )

        help_menu.add_command(
            label="Tentang",
            command=self.about
        )

        menu.add_cascade(
            label="Bantuan",
            menu=help_menu
        )

    # =====================================================
    # HEADER
    # =====================================================

    def create_header(self):

        frame = tk.Frame(
            self.root,
            bd=1,
            relief="solid"
        )

        frame.pack(
            fill="x",
            padx=10,
            pady=10
        )

        title = tk.Label(
            frame,
            text="APPBAKRY",
            font=("Arial", 24, "bold")
        )

        title.pack(
            pady=(10, 0)
        )

        subtitle = tk.Label(
            frame,
            text="FRAMEGABKRY - DATA ANALYSIS FRAMEWORK",
            font=("Arial", 11)
        )

        subtitle.pack(
            pady=(0, 10)
        )

    # =====================================================
    # TOOLBAR
    # =====================================================

    def create_toolbar(self):

        frame = tk.Frame(
            self.root
        )

        frame.pack(
            fill="x",
            padx=10,
            pady=5
        )

        buttons = [
            ("Buka CSV", self.open_csv),
            ("Buka Excel", self.open_excel),
            ("Statistik", self.show_statistics),
            ("Grafik", self.show_graph),
            ("Naive Bayes", self.naive_bayes),
            ("Regresi", self.linear_regression),
            ("Export CSV", self.export_csv),
            ("Export Excel", self.export_excel),
        ]

        for text, command in buttons:

            tk.Button(
                frame,
                text=text,
                command=command,
                width=14
            ).pack(
                side="left",
                padx=3
            )

        # Search

        search_frame = tk.Frame(
            self.root
        )

        search_frame.pack(
            fill="x",
            padx=10,
            pady=5
        )

        tk.Label(
            search_frame,
            text="Cari:"
        ).pack(
            side="left"
        )

        self.search_entry = tk.Entry(
            search_frame
        )

        self.search_entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=5
        )

        tk.Button(
            search_frame,
            text="Cari Data",
            command=self.search_data
        ).pack(
            side="left"
        )

        tk.Button(
            search_frame,
            text="Reset",
            command=self.reset_data
        ).pack(
            side="left",
            padx=5
        )

    # =====================================================
    # TABLE
    # =====================================================

    def create_table(self):

        frame = tk.Frame(
            self.root
        )

        frame.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=5
        )

        self.tree = ttk.Treeview(
            frame,
            show="headings"
        )

        scroll_y = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=self.tree.yview
        )

        scroll_x = ttk.Scrollbar(
            frame,
            orient="horizontal",
            command=self.tree.xview
        )

        self.tree.configure(
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set
        )

        scroll_y.pack(
            side="right",
            fill="y"
        )

        scroll_x.pack(
            side="bottom",
            fill="x"
        )

        self.tree.pack(
            fill="both",
            expand=True
        )

    # =====================================================
    # STATUS
    # =====================================================

    def create_statusbar(self):

        self.status = tk.Label(
            self.root,
            text="Belum ada dataset.",
            anchor="w",
            relief="sunken"
        )

        self.status.pack(
            fill="x",
            side="bottom"
        )

    # =====================================================
    # DISPLAY DATA
    # =====================================================

    def display_data(self, df):

        for item in self.tree.get_children():

            self.tree.delete(item)

        self.tree["columns"] = list(
            df.columns
        )

        for column in df.columns:

            self.tree.heading(
                column,
                text=str(column)
            )

            self.tree.column(
                column,
                width=130,
                anchor="center"
            )

        # Batasi tampilan agar GUI tidak terlalu berat

        display_df = df.head(5000)

        for _, row in display_df.iterrows():

            values = []

            for value in row:

                if pd.isna(value):

                    values.append("")

                else:

                    values.append(str(value))

            self.tree.insert(
                "",
                "end",
                values=values
            )

        self.status.config(
            text=(
                f"Dataset: {self.filename} | "
                f"Baris: {len(df):,} | "
                f"Kolom: {len(df.columns)}"
            )
        )

    # =====================================================
    # OPEN CSV
    # =====================================================

    def open_csv(self):

        file = filedialog.askopenfilename(
            title="Pilih File CSV",
            filetypes=[
                ("CSV", "*.csv"),
                ("All Files", "*.*")
            ]
        )

        if not file:
            return

        try:

            self.df = pd.read_csv(
                file
            )

            self.filename = os.path.basename(
                file
            )

            self.display_data(
                self.df
            )

            save_history(
                self.filename,
                len(self.df),
                len(self.df.columns)
            )

            messagebox.showinfo(
                "Berhasil",
                "Dataset CSV berhasil dibuka."
            )

        except Exception as e:

            messagebox.showerror(
                "Error",
                str(e)
            )

    # =====================================================
    # OPEN EXCEL
    # =====================================================

    def open_excel(self):

        file = filedialog.askopenfilename(
            title="Pilih File Excel",
            filetypes=[
                ("Excel", "*.xlsx *.xls"),
                ("All Files", "*.*")
            ]
        )

        if not file:
            return

        try:

            self.df = pd.read_excel(
                file
            )

            self.filename = os.path.basename(
                file
            )

            self.display_data(
                self.df
            )

            save_history(
                self.filename,
                len(self.df),
                len(self.df.columns)
            )

            messagebox.showinfo(
                "Berhasil",
                "Dataset Excel berhasil dibuka."
            )

        except Exception as e:

            messagebox.showerror(
                "Error",
                str(e)
            )

    # =====================================================
    # SEARCH
    # =====================================================

    def search_data(self):

        if self.df is None:

            messagebox.showwarning(
                "Peringatan",
                "Buka dataset terlebih dahulu."
            )

            return

        keyword = (
            self.search_entry
            .get()
            .strip()
            .lower()
        )

        if not keyword:

            self.display_data(
                self.df
            )

            return

        mask = (
            self.df
            .astype(str)
            .apply(
                lambda row:
                row.str.lower()
                .str.contains(
                    keyword,
                    na=False
                )
                .any(),
                axis=1
            )
        )

        result = self.df[mask]

        self.display_data(
            result
        )

        self.status.config(
            text=f"Hasil pencarian: {len(result)} data"
        )

    # =====================================================
    # RESET
    # =====================================================

    def reset_data(self):

        if self.df is not None:

            self.search_entry.delete(
                0,
                tk.END
            )

            self.display_data(
                self.df
            )

    # =====================================================
    # STATISTICS
    # =====================================================

    def show_statistics(self):

        if self.df is None:

            messagebox.showwarning(
                "Peringatan",
                "Buka dataset terlebih dahulu."
            )

            return

        window = tk.Toplevel(
            self.root
        )

        window.title(
            "Statistik Dataset"
        )

        window.geometry(
            "1000x650"
        )

        text = tk.Text(
            window,
            font=("Consolas", 10)
        )

        text.pack(
            fill="both",
            expand=True
        )

        text.insert(
            "end",
            "====================================\n"
        )

        text.insert(
            "end",
            "STATISTIK DATASET\n"
        )

        text.insert(
            "end",
            "====================================\n\n"
        )

        text.insert(
            "end",
            f"Nama file : {self.filename}\n"
        )

        text.insert(
            "end",
            f"Jumlah baris : {len(self.df)}\n"
        )

        text.insert(
            "end",
            f"Jumlah kolom : {len(self.df.columns)}\n\n"
        )

        text.insert(
            "end",
            "TIPE DATA\n"
        )

        text.insert(
            "end",
            str(self.df.dtypes)
        )

        text.insert(
            "end",
            "\n\nSTATISTIK NUMERIK\n"
        )

        try:

            text.insert(
                "end",
                str(
                    self.df.describe()
                )
            )

        except:

            text.insert(
                "end",
                "Tidak ada data numerik."
            )

    # =====================================================
    # GRAPH
    # =====================================================

    def show_graph(self):

        if self.df is None:

            messagebox.showwarning(
                "Peringatan",
                "Buka dataset terlebih dahulu."
            )

            return

        if not MATPLOTLIB:

            messagebox.showerror(
                "Library",
                "Install matplotlib terlebih dahulu:\n"
                "pip install matplotlib"
            )

            return

        numeric = self.df.select_dtypes(
            include="number"
        )

        if numeric.empty:

            messagebox.showwarning(
                "Grafik",
                "Dataset tidak mempunyai kolom numerik."
            )

            return

        column = numeric.columns[0]

        window = tk.Toplevel(
            self.root
        )

        window.title(
            f"Grafik - {column}"
        )

        window.geometry(
            "900x600"
        )

        fig = Figure(
            figsize=(8, 5),
            dpi=100
        )

        ax = fig.add_subplot(
            111
        )

        ax.plot(
            numeric[column].values
        )

        ax.set_title(
            f"Grafik {column}"
        )

        ax.set_xlabel(
            "Index"
        )

        ax.set_ylabel(
            column
        )

        ax.grid(
            True
        )

        canvas = FigureCanvasTkAgg(
            fig,
            master=window
        )

        canvas.draw()

        canvas.get_tk_widget().pack(
            fill="both",
            expand=True
        )

    # =====================================================
    # NAIVE BAYES
    # =====================================================

    def naive_bayes(self):

        if self.df is None:

            messagebox.showwarning(
                "Peringatan",
                "Buka dataset terlebih dahulu."
            )

            return

        if not SKLEARN:

            messagebox.showerror(
                "Library",
                "Install scikit-learn terlebih dahulu:\n"
                "pip install scikit-learn"
            )

            return

        numeric = self.df.select_dtypes(
            include="number"
        )

        if len(numeric.columns) < 2:

            messagebox.showwarning(
                "Naive Bayes",
                "Minimal membutuhkan 2 kolom numerik."
            )

            return

        X = numeric.iloc[:, :-1]
        y = numeric.iloc[:, -1]

        # Hilangkan missing value

        data = pd.concat(
            [X, y],
            axis=1
        ).dropna()

        X = data.iloc[:, :-1]
        y = data.iloc[:, -1]

        # Naive Bayes membutuhkan target kategori.
        # Jika target numerik kontinu, ubah menjadi kategori.

        if y.nunique() > 20:

            y = pd.qcut(
                y,
                q=3,
                labels=[
                    "Rendah",
                    "Sedang",
                    "Tinggi"
                ],
                duplicates="drop"
            )

        try:

            X_train, X_test, y_train, y_test = train_test_split(
                X,
                y,
                test_size=0.2,
                random_state=42,
                stratify=y
            )

            model = GaussianNB()

            model.fit(
                X_train,
                y_train
            )

            prediction = model.predict(
                X_test
            )

            accuracy = accuracy_score(
                y_test,
                prediction
            )

            result = (
                "====================================\n"
                "HASIL NAIVE BAYES\n"
                "====================================\n\n"
                f"Data training : {len(X_train)}\n"
                f"Data testing  : {len(X_test)}\n"
                f"Akurasi       : {accuracy:.2%}\n\n"
                "CLASSIFICATION REPORT\n\n"
                f"{classification_report(y_test, prediction)}"
            )

            self.show_result(
                "Hasil Naive Bayes",
                result
            )

        except Exception as e:

            messagebox.showerror(
                "Naive Bayes Error",
                str(e)
            )

    # =====================================================
    # REGRESSION
    # =====================================================

    def linear_regression(self):

        if self.df is None:

            messagebox.showwarning(
                "Peringatan",
                "Buka dataset terlebih dahulu."
            )

            return

        if not SKLEARN:

            messagebox.showerror(
                "Library",
                "Install scikit-learn terlebih dahulu."
            )

            return

        numeric = self.df.select_dtypes(
            include="number"
        )

        if len(numeric.columns) < 2:

            messagebox.showwarning(
                "Regresi",
                "Minimal membutuhkan 2 kolom numerik."
            )

            return

        data = numeric.dropna()

        X = data.iloc[:, :-1]
        y = data.iloc[:, -1]

        try:

            model = LinearRegression()

            model.fit(
                X,
                y
            )

            prediction = model.predict(
                X
            )

            r2 = model.score(
                X,
                y
            )

            result = (
                "====================================\n"
                "REGRESI LINEAR\n"
                "====================================\n\n"
                f"Variabel X:\n{list(X.columns)}\n\n"
                f"Variabel Y:\n{numeric.columns[-1]}\n\n"
                f"Intercept:\n{model.intercept_}\n\n"
                f"Koefisien:\n{model.coef_}\n\n"
                f"R² Score:\n{r2:.4f}\n\n"
                "Model berhasil dibuat."
            )

            self.show_result(
                "Regresi Linear",
                result
            )

        except Exception as e:

            messagebox.showerror(
                "Regresi Error",
                str(e)
            )

    # =====================================================
    # RESULT WINDOW
    # =====================================================

    def show_result(
        self,
        title,
        result
    ):

        window = tk.Toplevel(
            self.root
        )

        window.title(
            title
        )

        window.geometry(
            "900x650"
        )

        text = tk.Text(
            window,
            font=("Consolas", 10)
        )

        text.pack(
            fill="both",
            expand=True
        )

        text.insert(
            "1.0",
            result
        )

    # =====================================================
    # EXPORT CSV
    # =====================================================

    def export_csv(self):

        if self.df is None:

            messagebox.showwarning(
                "Peringatan",
                "Tidak ada dataset."
            )

            return

        file = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[
                ("CSV", "*.csv")
            ]
        )

        if not file:
            return

        try:

            self.df.to_csv(
                file,
                index=False
            )

            messagebox.showinfo(
                "Berhasil",
                "Data berhasil diekspor."
            )

        except Exception as e:

            messagebox.showerror(
                "Error",
                str(e)
            )

    # =====================================================
    # EXPORT EXCEL
    # =====================================================

    def export_excel(self):

        if self.df is None:

            messagebox.showwarning(
                "Peringatan",
                "Tidak ada dataset."
            )

            return

        file = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[
                ("Excel", "*.xlsx")
            ]
        )

        if not file:
            return

        try:

            self.df.to_excel(
                file,
                index=False
            )

            messagebox.showinfo(
                "Berhasil",
                "Data berhasil diekspor ke Excel."
            )

        except Exception as e:

            messagebox.showerror(
                "Error",
                str(e)
            )

    # =====================================================
    # HISTORY
    # =====================================================

    def show_history(self):

        window = tk.Toplevel(
            self.root
        )

        window.title(
            "Riwayat Dataset"
        )

        window.geometry(
            "800x500"
        )

        tree = ttk.Treeview(
            window,
            columns=(
                "id",
                "filename",
                "rows",
                "columns",
                "date"
            ),
            show="headings"
        )

        headings = {
            "id": "ID",
            "filename": "File",
            "rows": "Baris",
            "columns": "Kolom",
            "date": "Tanggal"
        }

        for column, heading in headings.items():

            tree.heading(
                column,
                text=heading
            )

            tree.column(
                column,
                width=130
            )

        tree.pack(
            fill="both",
            expand=True
        )

        conn = sqlite3.connect(
            DATABASE
        )

        rows = conn.execute(
            """
            SELECT id,
                   filename,
                   rows_count,
                   columns_count,
                   created_at
            FROM history
            ORDER BY id DESC
            """
        ).fetchall()

        conn.close()

        for row in rows:

            tree.insert(
                "",
                "end",
                values=row
            )

    # =====================================================
    # ABOUT
    # =====================================================

    def about(self):

        messagebox.showinfo(
            "Tentang APPBAKRY",
            f"{APP_NAME}\n\n"
            f"FrameGabkry Data Analysis Framework\n"
            f"Version {VERSION}\n\n"
            "Python Desktop Data Analysis\n"
            "CSV | Excel | SQLite | Statistik\n"
            "Naive Bayes | Regresi Linear | Grafik"
        )


# =========================================================
# MAIN
# =========================================================

def main():

    init_database()

    root = tk.Tk()

    app = AppBakry(
        root
    )

    root.mainloop()


if __name__ == "__main__":

    main()
```
