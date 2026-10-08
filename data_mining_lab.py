#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DATA MINING LAB  (satu file)
============================
Aplikasi desktop untuk menguji dan membandingkan beberapa algoritma data mining
pada dataset milik sendiri (CSV / Excel) atau dataset contoh.

Fitur:
  1. Dataset     : buka CSV/Excel atau dataset contoh (Iris, Wine, Breast Cancer),
                   pratinjau data, profil kolom (tipe, nilai kosong, min/rata-rata/maks)
  2. Pengaturan  : pilih kolom target & fitur, penanganan nilai kosong, scaling,
                   metode evaluasi (Hold-out atau K-Fold Cross Validation),
                   algoritma yang diuji + parameter dasarnya
  3. Hasil       : tabel peringkat (Akurasi, Presisi, Recall, F1, waktu), grafik
                   perbandingan, confusion matrix, laporan klasifikasi,
                   fitur penting, aturan Decision Tree, ekspor CSV / laporan TXT
  4. Clustering  : K-Means, cari k optimal (elbow + silhouette), simpan hasil cluster

Algoritma klasifikasi: Decision Tree, Random Forest, K-Nearest Neighbor,
Naive Bayes, Logistic Regression, SVM, Gradient Boosting.

Instalasi library (sekali saja):
    pip install pandas scikit-learn openpyxl
Jalankan:
    python data_mining_lab.py
"""

import os
import sys
import time
import queue
import threading
import traceback
import warnings
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    import numpy as np
    import pandas as pd
    from sklearn import datasets
    from sklearn.base import clone
    from sklearn.cluster import KMeans
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,
                                 f1_score, precision_score, recall_score, silhouette_score)
    from sklearn.model_selection import StratifiedKFold, train_test_split
    from sklearn.naive_bayes import GaussianNB
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import LabelEncoder, MinMaxScaler, OneHotEncoder, StandardScaler
    from sklearn.svm import SVC
    from sklearn.tree import DecisionTreeClassifier, export_text
except ImportError as _err:  # pragma: no cover
    _r = tk.Tk()
    _r.withdraw()
    messagebox.showerror(
        "Library belum terpasang",
        "Jalankan perintah ini di terminal / CMD lalu buka ulang aplikasi:\n\n"
        "    pip install pandas scikit-learn openpyxl\n\nDetail: %s" % _err)
    sys.exit(1)

warnings.filterwarnings("ignore")

APP_TITLE = "Data Mining Lab - Pengujian Algoritma"

SAMPEL = {
    "Iris (150 baris, 3 kelas)": "iris",
    "Wine (178 baris, 3 kelas)": "wine",
    "Breast Cancer (569 baris, 2 kelas)": "kanker",
}
ALGO_NAMA = ["Decision Tree", "Random Forest", "K-Nearest Neighbor", "Naive Bayes (Gaussian)",
             "Logistic Regression", "SVM (RBF)", "Gradient Boosting"]
ALGO_DEFAULT = {n: True for n in ALGO_NAMA}
ALGO_DEFAULT["Gradient Boosting"] = False  # lebih lambat, aktifkan manual
DAPAT_DIJELASKAN = {"Decision Tree", "Random Forest", "Gradient Boosting", "Logistic Regression"}
BERBASIS_POHON = {"Decision Tree", "Random Forest", "Gradient Boosting"}
SCALING_LIST = ["Standard (Z-score)", "Min-Max", "Tanpa scaling"]
METRIK_LIST = {"Akurasi": "acc", "Presisi": "prec", "Recall": "rec", "F1-Score": "f1"}


# ======================================================================
#  BAGIAN 1 - LOGIKA DATA MINING (tanpa GUI, bisa diuji terpisah)
# ======================================================================
def muat_contoh(kode):
    loader = {"iris": datasets.load_iris, "wine": datasets.load_wine,
              "kanker": datasets.load_breast_cancer}[kode]
    d = loader(as_frame=True)
    df = d.frame.drop(columns=["target"]).copy()
    df["kelas"] = [str(d.target_names[i]) for i in d.target]
    return df


def baca_file(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xlsm", ".xls"):
        df = pd.read_excel(path)
    else:
        try:
            df = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig")
        except UnicodeDecodeError:
            df = pd.read_csv(path, sep=None, engine="python", encoding="latin-1")
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(axis=1, how="all").dropna(axis=0, how="all").reset_index(drop=True)
    if df.shape[1] < 2 or df.shape[0] < 10:
        raise ValueError("Dataset minimal punya 2 kolom dan 10 baris.")
    return df


def kolom_numerik(s):
    return pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s)


def profil_dataset(df):
    baris = []
    for c in df.columns:
        s = df[c]
        num = kolom_numerik(s)
        baris.append({
            "Kolom": c, "Tipe": "numerik" if num else "kategorik",
            "Kosong": int(s.isna().sum()), "Unik": int(s.nunique()),
            "Min": round(float(s.min()), 3) if num else "",
            "Rata2": round(float(s.mean()), 3) if num else "",
            "Maks": round(float(s.max()), 3) if num else "",
        })
    return pd.DataFrame(baris).to_string(index=False)


def siapkan_data(df, target, fitur, hapus_kosong):
    """Membersihkan data & memisahkan X (fitur) dan y (target ter-encode)."""
    if not target:
        raise ValueError("Pilih kolom target terlebih dahulu.")
    fitur = [f for f in fitur if f != target]
    if not fitur:
        raise ValueError("Pilih minimal satu kolom fitur (selain kolom target).")
    data = df[fitur + [target]].copy().dropna(subset=[target])
    if hapus_kosong:
        data = data.dropna()
    if len(data) < 10:
        raise ValueError("Data terlalu sedikit (kurang dari 10 baris) setelah pembersihan.")

    y_raw = data[target].astype(str)
    n_kelas = y_raw.nunique()
    if n_kelas < 2:
        raise ValueError("Kolom target hanya memiliki 1 nilai. Pilih kolom kelas yang benar.")
    if n_kelas > 30:
        raise ValueError(f"Kolom target memiliki {n_kelas} nilai unik, sepertinya bukan kolom kelas.\n"
                         "Pilih kolom target yang berisi kategori (misal: Ya/Tidak, jenis, label).")
    le = LabelEncoder()
    y = le.fit_transform(y_raw)
    hitung = np.bincount(y)
    if hitung.min() < 2:
        raise ValueError(f"Kelas '{le.classes_[hitung.argmin()]}' hanya memiliki 1 data. "
                         "Setiap kelas minimal butuh 2 data.")

    X = data[fitur].copy()
    peringatan = []
    for c in X.columns:
        if pd.api.types.is_bool_dtype(X[c]):
            X[c] = X[c].astype(int)
        elif not kolom_numerik(X[c]):
            X[c] = X[c].astype(object).where(X[c].notna(), np.nan)
            if X[c].nunique() > 50 and X[c].nunique() > 0.5 * len(X):
                peringatan.append(f"Kolom '{c}' bersifat kategorik dengan banyak nilai unik "
                                  "(mirip ID/nama). Sebaiknya jangan dipakai sebagai fitur.")
    return X.reset_index(drop=True), y, list(le.classes_), peringatan


def buat_preprocessor(X, scaling):
    num = [c for c in X.columns if kolom_numerik(X[c])]
    kat = [c for c in X.columns if c not in num]
    langkah_num = [("imp", SimpleImputer(strategy="median"))]
    if scaling == SCALING_LIST[0]:
        langkah_num.append(("sc", StandardScaler()))
    elif scaling == SCALING_LIST[1]:
        langkah_num.append(("sc", MinMaxScaler()))
    bagian = []
    if num:
        bagian.append(("num", Pipeline(langkah_num), num))
    if kat:
        bagian.append(("kat", Pipeline([
            ("imp", SimpleImputer(strategy="most_frequent")),
            ("oh", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]), kat))
    return ColumnTransformer(bagian)


def daftar_algoritma(p):
    seed = p["seed"]
    return {
        "Decision Tree": lambda: DecisionTreeClassifier(
            criterion=p["dt_crit"], max_depth=p["dt_depth"], random_state=seed),
        "Random Forest": lambda: RandomForestClassifier(
            n_estimators=p["rf_n"], random_state=seed, n_jobs=-1),
        "K-Nearest Neighbor": lambda: KNeighborsClassifier(n_neighbors=p["knn_k"]),
        "Naive Bayes (Gaussian)": lambda: GaussianNB(),
        "Logistic Regression": lambda: LogisticRegression(max_iter=2000),
        "SVM (RBF)": lambda: SVC(kernel="rbf", random_state=seed),
        "Gradient Boosting": lambda: GradientBoostingClassifier(random_state=seed),
    }


def metrik(y_true, y_pred):
    return {
        "acc": accuracy_score(y_true, y_pred),
        "prec": precision_score(y_true, y_pred, average="weighted", zero_division=0),
        "rec": recall_score(y_true, y_pred, average="weighted", zero_division=0),
        "f1": f1_score(y_true, y_pred, average="weighted", zero_division=0),
    }


def nama_fitur(pipe):
    try:
        return [str(n).split("__", 1)[-1] for n in pipe.named_steps["pre"].get_feature_names_out()]
    except Exception:
        return None


def jelaskan_model(pipe, nama, kelas):
    """Mengambil fitur penting dan (untuk Decision Tree) aturan pohon."""
    clf = pipe.named_steps["clf"]
    names = nama_fitur(pipe)
    penting, aturan = [], None
    if hasattr(clf, "feature_importances_"):
        nilai = np.asarray(clf.feature_importances_, dtype=float)
    elif hasattr(clf, "coef_"):
        nilai = np.abs(np.asarray(clf.coef_, dtype=float)).mean(axis=0)
        nilai = nilai / (nilai.sum() or 1)
    else:
        nilai = None
    if nilai is not None:
        if not names or len(names) != len(nilai):
            names = [f"fitur_{i}" for i in range(len(nilai))]
        urut = np.argsort(nilai)[::-1][:15]
        penting = [(names[i], float(nilai[i])) for i in urut]
    if nama == "Decision Tree":
        legenda = ", ".join(f"{i} = {k}" for i, k in enumerate(kelas))
        aturan = (f"Kedalaman pohon: {clf.get_depth()}   |   Jumlah daun: {clf.get_n_leaves()}\n"
                  f"Keterangan kelas: {legenda}\n\n"
                  + export_text(clf, feature_names=list(names) if names else None, max_depth=8))
    return penting, aturan


def uji_algoritma(df, target, fitur, opsi, algos, params, progress):
    """Menjalankan pengujian semua algoritma terpilih. Mengembalikan dict hasil."""
    X, y, kelas, peringatan = siapkan_data(df, target, fitur, opsi["hapus_kosong"])
    pre = buat_preprocessor(X, opsi["scaling"])
    seed = opsi["seed"]
    catatan = []
    jumlah = np.bincount(y)

    if opsi["metode"] == "holdout":
        ts = opsi["test_size"] / 100.0
        try:
            Xtr, Xte, ytr, yte = train_test_split(
                X, y, test_size=ts, random_state=seed, stratify=y if opsi["stratify"] else None)
        except ValueError:
            Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=ts, random_state=seed)
            catatan.append("Stratifikasi dimatikan karena jumlah data per kelas tidak cukup.")
        splits = None
        metode_teks = (f"Hold-out: {100 - opsi['test_size']}% data latih ({len(ytr)}) / "
                       f"{opsi['test_size']}% data uji ({len(yte)}), seed {seed}")
    else:
        k = min(opsi["k"], int(jumlah.min()))
        if k < 2:
            raise ValueError("Data per kelas terlalu sedikit untuk K-Fold Cross Validation.")
        if k < opsi["k"]:
            catatan.append(f"Jumlah fold diturunkan menjadi {k} (data kelas terkecil hanya {jumlah.min()}).")
        splits = list(StratifiedKFold(n_splits=k, shuffle=True, random_state=seed).split(X, y))
        metode_teks = f"{k}-Fold Stratified Cross Validation, seed {seed}"

    pabrik = daftar_algoritma(params)
    label = list(range(len(kelas)))

    pre_pohon = buat_preprocessor(X, SCALING_LIST[2])  # pohon tidak butuh scaling -> aturan tetap satuan asli

    def buat_pipe(nama):
        return Pipeline([("pre", clone(pre_pohon if nama in BERBASIS_POHON else pre)),
                         ("clf", pabrik[nama]())])

    hasil = []
    for i, nama in enumerate(algos):
        progress(i, len(algos), f"Menguji {nama} ({i + 1}/{len(algos)})...")
        mulai = time.perf_counter()
        try:
            if splits is None:
                pipe = buat_pipe(nama)
                pipe.fit(Xtr, ytr)
                pred = pipe.predict(Xte)
                y_true, y_pred = yte, pred
                m, std = metrik(y_true, y_pred), None
                waktu = time.perf_counter() - mulai
            else:
                per_fold, yt_all, yp_all = [], [], []
                for tr, te in splits:
                    pipe = buat_pipe(nama)
                    pipe.fit(X.iloc[tr], y[tr])
                    pred = pipe.predict(X.iloc[te])
                    per_fold.append(metrik(y[te], pred))
                    yt_all.extend(y[te])
                    yp_all.extend(pred)
                m = {key: float(np.mean([d[key] for d in per_fold])) for key in per_fold[0]}
                std = float(np.std([d["acc"] for d in per_fold]))
                y_true, y_pred = np.array(yt_all), np.array(yp_all)
                waktu = time.perf_counter() - mulai
                pipe = buat_pipe(nama).fit(X, y) if nama in DAPAT_DIJELASKAN else None

            penting, aturan = ([], None)
            if pipe is not None and nama in DAPAT_DIJELASKAN:
                penting, aturan = jelaskan_model(pipe, nama, kelas)
            hasil.append({
                "nama": nama, **m, "std": std, "waktu": waktu,
                "cm": confusion_matrix(y_true, y_pred, labels=label),
                "laporan": classification_report(y_true, y_pred, labels=label,
                                                 target_names=[str(k) for k in kelas], zero_division=0),
                "penting": penting, "aturan": aturan, "error": None,
            })
        except Exception as e:  # satu algoritma gagal tidak menghentikan yang lain
            hasil.append({"nama": nama, "error": str(e)})
    progress(len(algos), len(algos), "Selesai.")
    return {"hasil": hasil, "kelas": kelas, "n_baris": len(y), "n_fitur": int(X.shape[1]),
            "n_fitur_asli": len(X.columns), "peringatan": peringatan, "catatan": catatan,
            "metode_teks": metode_teks, "target": target, "kfold": splits is not None}


def urutkan_hasil(hasil):
    ok = [h for h in hasil if not h.get("error")]
    ok.sort(key=lambda h: (h["acc"], h["f1"]), reverse=True)
    return ok, [h for h in hasil if h.get("error")]


def buat_laporan_teks(res, nama_data):
    ok, gagal = urutkan_hasil(res["hasil"])
    baris = ["=" * 78, "LAPORAN PENGUJIAN ALGORITMA DATA MINING",
             f"Dibuat      : {datetime.now():%d-%m-%Y %H:%M}", f"Dataset     : {nama_data}",
             f"Jumlah data : {res['n_baris']} baris, {res['n_fitur_asli']} fitur "
             f"({res['n_fitur']} setelah encoding)",
             f"Target      : {res['target']}  ({len(res['kelas'])} kelas: {', '.join(map(str, res['kelas']))})",
             f"Metode      : {res['metode_teks']}", "=" * 78, "",
             f"{'No':<4}{'Algoritma':<26}{'Akurasi':>9}{'Presisi':>9}{'Recall':>9}{'F1':>9}{'Waktu(s)':>10}"]
    for i, h in enumerate(ok, 1):
        baris.append(f"{i:<4}{h['nama']:<26}{h['acc'] * 100:>8.2f}%{h['prec'] * 100:>8.2f}%"
                     f"{h['rec'] * 100:>8.2f}%{h['f1'] * 100:>8.2f}%{h['waktu']:>10.3f}")
    for h in gagal:
        baris.append(f"-   {h['nama']:<26}GAGAL: {h['error']}")
    if ok:
        baris += ["", f"Kesimpulan: algoritma dengan akurasi tertinggi adalah {ok[0]['nama']} "
                      f"({ok[0]['acc'] * 100:.2f}%)."]
    for p in res["peringatan"] + res["catatan"]:
        baris.append("Catatan: " + p)
    for h in ok:
        baris += ["", "-" * 78, h["nama"].upper(), "-" * 78, h["laporan"],
                  "Confusion matrix (baris = aktual, kolom = prediksi):", str(h["cm"])]
        if h["aturan"]:
            baris += ["", "Aturan Decision Tree:", h["aturan"]]
    return "\n".join(baris)


# ---------------- clustering ----------------
def _siapkan_cluster(df, fitur, scaling):
    X = df[fitur].copy()
    for c in X.columns:
        if pd.api.types.is_bool_dtype(X[c]):
            X[c] = X[c].astype(int)
        elif not kolom_numerik(X[c]):
            X[c] = X[c].astype(object).where(X[c].notna(), np.nan)
    return buat_preprocessor(X, scaling).fit_transform(X)


def kmeans_jalankan(df, fitur, k, scaling, seed):
    Xt = _siapkan_cluster(df, fitur, scaling)
    if k >= len(Xt):
        raise ValueError("Jumlah cluster harus lebih kecil dari jumlah data.")
    km = KMeans(n_clusters=k, n_init=10, random_state=seed).fit(Xt)
    sil = silhouette_score(Xt, km.labels_, sample_size=min(2000, len(Xt)), random_state=seed)
    return {"labels": km.labels_, "sil": float(sil), "inertia": float(km.inertia_), "k": k}


def kmeans_elbow(df, fitur, kmax, scaling, seed, progress):
    Xt = _siapkan_cluster(df, fitur, scaling)
    kmax = min(kmax, len(Xt) - 1)
    hasil = []
    ks = list(range(2, kmax + 1))
    for i, k in enumerate(ks):
        progress(i, len(ks), f"Menguji k = {k}...")
        km = KMeans(n_clusters=k, n_init=10, random_state=seed).fit(Xt)
        sil = silhouette_score(Xt, km.labels_, sample_size=min(2000, len(Xt)), random_state=seed)
        hasil.append((k, float(km.inertia_), float(sil)))
    progress(len(ks), len(ks), "Selesai.")
    return hasil


# ======================================================================
#  BAGIAN 2 - KOMPONEN GRAFIK (Canvas)
# ======================================================================
class BarChart(tk.Canvas):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg="white", highlightthickness=0, **kw)
        self.data, self.judul, self.maks, self.fmt, self.best = [], "", None, "{:.3f}", None
        self.bind("<Configure>", lambda e: self.draw())

    def set(self, data, judul="", maks=None, fmt="{:.3f}", best=None):
        self.data, self.judul, self.maks, self.fmt, self.best = data, judul, maks, fmt, best
        self.draw()

    def draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 80 or h < 50:
            return
        if self.judul:
            self.create_text(8, 11, anchor="w", text=self.judul, font=("Segoe UI", 10, "bold"))
        if not self.data:
            self.create_text(w / 2, h / 2, text="Belum ada data", fill="#888")
            return
        atas, kiri, kanan = 28, min(190, int(w * 0.38)), 70
        tinggi = min(32, (h - atas - 6) / len(self.data))
        maks = self.maks or max(v for _, v in self.data) or 1
        for i, (lab, val) in enumerate(self.data):
            y = atas + i * tinggi
            teks = lab if len(lab) <= 26 else lab[:25] + "..."
            self.create_text(kiri - 6, y + tinggi / 2, anchor="e", text=teks, font=("Segoe UI", 9))
            panjang = max(0, (w - kiri - kanan) * val / maks)
            warna = "#2ea44f" if i == self.best else "#4a7bd0"
            self.create_rectangle(kiri, y + 3, kiri + panjang, y + tinggi - 3, fill=warna, outline="")
            self.create_text(kiri + panjang + 6, y + tinggi / 2, anchor="w",
                             text=self.fmt.format(val), font=("Segoe UI", 9))


class ConfusionChart(tk.Canvas):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg="white", highlightthickness=0, **kw)
        self.cm, self.kelas = None, []
        self.bind("<Configure>", lambda e: self.draw())

    def set(self, cm, kelas):
        self.cm, self.kelas = cm, kelas
        self.draw()

    def draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if self.cm is None or w < 80 or h < 80:
            return
        n = len(self.cm)
        kiri, atas = 100, 56
        sel = max(14, min((w - kiri - 10) / n, (h - atas - 10) / n, 90))
        self.create_text(kiri + n * sel / 2, 10, text="Prediksi", font=("Segoe UI", 9, "bold"))
        self.create_text(6, atas - 8, anchor="w", text="Aktual", font=("Segoe UI", 9, "bold"))
        for j in range(n):
            self.create_text(kiri + j * sel + sel / 2, atas - 14, text=str(self.kelas[j])[:9],
                             font=("Segoe UI", 8))
        for i in range(n):
            self.create_text(kiri - 6, atas + i * sel + sel / 2, anchor="e",
                             text=str(self.kelas[i])[:14], font=("Segoe UI", 8))
            total = self.cm[i].sum() or 1
            for j in range(n):
                t = self.cm[i][j] / total
                warna = "#%02x%02x%02x" % (int(255 - 218 * t), int(255 - 156 * t), int(255 - 20 * t))
                x0, y0 = kiri + j * sel, atas + i * sel
                self.create_rectangle(x0, y0, x0 + sel, y0 + sel, fill=warna, outline="#ddd")
                self.create_text(x0 + sel / 2, y0 + sel / 2, text=str(int(self.cm[i][j])),
                                 fill="white" if t > 0.55 else "#222", font=("Segoe UI", 10, "bold"))


class LineChart(tk.Canvas):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg="white", highlightthickness=0, **kw)
        self.xs, self.ys, self.judul, self.sumbu_y, self.tandai = [], [], "", "", None
        self.bind("<Configure>", lambda e: self.draw())

    def set(self, xs, ys, judul="", sumbu_y="", tandai=None):
        self.xs, self.ys, self.judul, self.sumbu_y, self.tandai = xs, ys, judul, sumbu_y, tandai
        self.draw()

    def draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 100 or h < 80:
            return
        self.create_text(8, 11, anchor="w", text=self.judul, font=("Segoe UI", 10, "bold"))
        if not self.xs:
            self.create_text(w / 2, h / 2, text="Klik 'Cari k optimal' untuk membuat grafik", fill="#888")
            return
        kiri, bawah, atas, kanan = 70, 36, 30, 20
        xmin, xmax, ymin, ymax = min(self.xs), max(self.xs), min(self.ys), max(self.ys)
        pad = (ymax - ymin) * 0.08 or 1
        ymin, ymax = ymin - pad, ymax + pad

        def px(x):
            return kiri + (x - xmin) / ((xmax - xmin) or 1) * (w - kiri - kanan)

        def py(y):
            return atas + (1 - (y - ymin) / ((ymax - ymin) or 1)) * (h - atas - bawah)

        for i in range(5):
            y = ymin + (ymax - ymin) * i / 4
            self.create_line(kiri, py(y), w - kanan, py(y), fill="#eee")
            self.create_text(kiri - 6, py(y), anchor="e", text=f"{y:,.1f}", font=("Segoe UI", 8), fill="#666")
        titik = []
        for x, y in zip(self.xs, self.ys):
            titik += [px(x), py(y)]
            self.create_text(px(x), h - bawah + 12, text=str(x), font=("Segoe UI", 8), fill="#444")
        if len(titik) >= 4:
            self.create_line(*titik, fill="#4a7bd0", width=2)
        for x, y in zip(self.xs, self.ys):
            warna = "#2ea44f" if x == self.tandai else "#4a7bd0"
            self.create_oval(px(x) - 4, py(y) - 4, px(x) + 4, py(y) + 4, fill=warna, outline="white")
        self.create_text(w / 2, h - 8, text="Jumlah cluster (k)", font=("Segoe UI", 8), fill="#666")
        self.create_text(8, atas - 6, anchor="w", text=self.sumbu_y, font=("Segoe UI", 8), fill="#666")


# ======================================================================
#  BAGIAN 3 - APLIKASI (GUI)
# ======================================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1220x780")
        self.minsize(1000, 640)
        self.df = None
        self.nama_data = ""
        self.hasil = None
        self.cluster_df = None
        self.q = None
        self.btn_aksi = []

        self._style()
        self._menu()
        self._build()
        self.status("Siap. Mulai dengan membuka dataset atau memuat dataset contoh.")

    # ---------- dasar ----------
    def _style(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure("Treeview", rowheight=24)
        s.configure("Judul.TLabel", font=("Segoe UI", 10, "bold"))
        s.configure("Besar.TButton", font=("Segoe UI", 11, "bold"), padding=8)

    def _menu(self):
        bar = tk.Menu(self)
        m = tk.Menu(bar, tearoff=0)
        m.add_command(label="Buka dataset (CSV / Excel)...", command=self.buka_file)
        m.add_separator()
        m.add_command(label="Keluar", command=self.destroy)
        bar.add_cascade(label="File", menu=m)
        h = tk.Menu(bar, tearoff=0)
        h.add_command(label="Panduan singkat", command=self.panduan)
        h.add_command(label="Tentang", command=lambda: messagebox.showinfo(
            "Tentang", f"{APP_TITLE}\nPython + Tkinter + scikit-learn + pandas"))
        bar.add_cascade(label="Bantuan", menu=h)
        self.config(menu=bar)

    def panduan(self):
        messagebox.showinfo("Panduan singkat", (
            "1. Tab Dataset: buka CSV/Excel atau muat dataset contoh.\n"
            "2. Tab Pengaturan: pilih kolom target (kelas) dan fitur, atur praproses,\n"
            "    metode evaluasi, dan algoritma yang ingin diuji.\n"
            "3. Klik 'Jalankan Pengujian'. Hasil muncul di tab Hasil.\n"
            "4. Klik tiap algoritma di tabel untuk melihat confusion matrix,\n"
            "    laporan klasifikasi, fitur penting, dan aturan Decision Tree.\n"
            "5. Tab Clustering: K-Means tanpa target (unsupervised).\n\n"
            "Tips: gunakan K-Fold CV bila data sedikit agar hasil lebih stabil."))

    def _build(self):
        bawah = ttk.Frame(self)
        bawah.pack(side="bottom", fill="x")
        self.l_status = ttk.Label(bawah, anchor="w")
        self.l_status.pack(side="left", fill="x", expand=True, padx=8, pady=3)
        self.pb = ttk.Progressbar(bawah, length=220, mode="determinate")
        self.pb.pack(side="right", padx=8, pady=3)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=8, pady=(8, 2))
        self.tab = {}
        for kunci, judul in [("data", "  1. Dataset  "), ("set", "  2. Pengaturan  "),
                             ("hasil", "  3. Hasil  "), ("cluster", "  4. Clustering  ")]:
            f = ttk.Frame(self.nb, padding=8)
            self.nb.add(f, text=judul)
            self.tab[kunci] = f
        self._tab_dataset(self.tab["data"])
        self._tab_pengaturan(self.tab["set"])
        self._tab_hasil(self.tab["hasil"])
        self._tab_cluster(self.tab["cluster"])

    def status(self, teks):
        self.l_status.config(text=teks)

    # ---------- proses latar belakang ----------
    def bg(self, fungsi, selesai, total=0, teks="Memproses..."):
        self._sibuk(True, teks, total)
        self.q = queue.Queue()
        q = self.q

        def kerja():
            try:
                q.put(("done", fungsi(lambda i, n, t: q.put(("progress", i, n, t)))))
            except Exception as e:
                q.put(("error", str(e), traceback.format_exc()))

        threading.Thread(target=kerja, daemon=True).start()
        self._poll(selesai)

    def _poll(self, selesai):
        try:
            while True:
                m = self.q.get_nowait()
                if m[0] == "progress":
                    self.pb["maximum"] = max(m[2], 1)
                    self.pb["value"] = m[1]
                    self.status(m[3])
                elif m[0] == "done":
                    self._sibuk(False)
                    selesai(m[1])
                    return
                else:
                    self._sibuk(False)
                    self.status("Terjadi kesalahan.")
                    print(m[2], file=sys.stderr)
                    messagebox.showerror("Kesalahan", m[1])
                    return
        except queue.Empty:
            pass
        self.after(100, lambda: self._poll(selesai))

    def _sibuk(self, aktif, teks="", total=0):
        for b in self.btn_aksi:
            b.config(state="disabled" if aktif else "normal")
        self.pb.stop()
        if aktif:
            self.status(teks)
            if total:
                self.pb.config(mode="determinate", maximum=total, value=0)
            else:
                self.pb.config(mode="indeterminate")
                self.pb.start(12)
        else:
            self.pb.config(mode="determinate", value=0)

    # ---------- TAB 1: dataset ----------
    def _tab_dataset(self, p):
        atas = ttk.Frame(p)
        atas.pack(fill="x")
        ttk.Button(atas, text="Buka File (CSV / Excel)...", command=self.buka_file).pack(side="left")
        ttk.Label(atas, text="   atau dataset contoh:").pack(side="left")
        self.v_sampel = tk.StringVar(value=list(SAMPEL)[0])
        ttk.Combobox(atas, textvariable=self.v_sampel, values=list(SAMPEL), state="readonly",
                     width=34).pack(side="left", padx=6)
        ttk.Button(atas, text="Muat Contoh", command=self.muat_sampel).pack(side="left")

        self.l_info = ttk.Label(p, text="Belum ada dataset dimuat.", style="Judul.TLabel")
        self.l_info.pack(anchor="w", pady=(10, 4))

        wrap = ttk.LabelFrame(p, text="Pratinjau data (maks. 200 baris pertama)", padding=4)
        wrap.pack(fill="both", expand=True)
        self.tree_data = ttk.Treeview(wrap, show="headings", height=10)
        sy = ttk.Scrollbar(wrap, orient="vertical", command=self.tree_data.yview)
        sx = ttk.Scrollbar(wrap, orient="horizontal", command=self.tree_data.xview)
        self.tree_data.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        sy.pack(side="right", fill="y")
        sx.pack(side="bottom", fill="x")
        self.tree_data.pack(fill="both", expand=True)

        pf = ttk.LabelFrame(p, text="Profil kolom", padding=4)
        pf.pack(fill="both", expand=True, pady=(8, 0))
        self.t_profil = tk.Text(pf, height=9, font="TkFixedFont", wrap="none", state="disabled")
        sy2 = ttk.Scrollbar(pf, orient="vertical", command=self.t_profil.yview)
        self.t_profil.configure(yscrollcommand=sy2.set)
        sy2.pack(side="right", fill="y")
        self.t_profil.pack(fill="both", expand=True)

    def buka_file(self):
        path = filedialog.askopenfilename(
            title="Pilih dataset", filetypes=[("Dataset", "*.csv *.txt *.xlsx *.xls"), ("Semua file", "*.*")])
        if not path:
            return
        try:
            df = baca_file(path)
        except Exception as e:
            messagebox.showerror("Gagal membaca file", str(e))
            return
        self._set_dataset(df, os.path.basename(path))

    def muat_sampel(self):
        self._set_dataset(muat_contoh(SAMPEL[self.v_sampel.get()]), self.v_sampel.get().split(" (")[0])

    def _set_dataset(self, df, nama):
        self.df, self.nama_data, self.hasil, self.cluster_df = df, nama, None, None
        n_num = sum(kolom_numerik(df[c]) for c in df.columns)
        self.l_info.config(text=f"{nama}: {len(df)} baris x {df.shape[1]} kolom  |  "
                                f"numerik: {n_num}, kategorik: {df.shape[1] - n_num}  |  "
                                f"nilai kosong: {int(df.isna().sum().sum())}")
        kol = list(df.columns)[:100]
        self.tree_data.delete(*self.tree_data.get_children())
        self.tree_data["columns"] = kol
        for c in kol:
            self.tree_data.heading(c, text=c)
            self.tree_data.column(c, width=max(70, min(160, len(c) * 9)), anchor="w")
        for row in df[kol].head(200).itertuples(index=False):
            self.tree_data.insert("", "end", values=["" if pd.isna(v) else v for v in row])
        self._isi_text(self.t_profil, profil_dataset(df))

        self.cb_target["values"] = list(df.columns)
        self.v_target.set(df.columns[-1])
        self.lb.delete(0, "end")
        for c in df.columns:
            self.lb.insert("end", c)
        self.lb.selection_set(0, "end")
        self._saat_target()
        self._kosongkan_hasil()
        self.status(f"Dataset '{nama}' dimuat. Lanjut ke tab Pengaturan.")
        self.nb.select(self.tab["set"])

    @staticmethod
    def _isi_text(widget, teks):
        widget.config(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", teks)
        widget.config(state="disabled")

    # ---------- TAB 2: pengaturan ----------
    def _tab_pengaturan(self, p):
        p.columnconfigure((0, 1, 2), weight=1, uniform="kol")
        p.rowconfigure(0, weight=1)

        # kolom 0 - data
        f1 = ttk.LabelFrame(p, text="1. Data", padding=10)
        f1.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        ttk.Label(f1, text="Kolom target (kelas yang diprediksi):").pack(anchor="w")
        self.v_target = tk.StringVar()
        self.cb_target = ttk.Combobox(f1, textvariable=self.v_target, state="readonly")
        self.cb_target.pack(fill="x", pady=(2, 8))
        self.cb_target.bind("<<ComboboxSelected>>", lambda e: self._saat_target())
        ttk.Label(f1, text="Kolom fitur (Ctrl / Shift untuk pilih banyak):").pack(anchor="w")
        fl = ttk.Frame(f1)
        fl.pack(fill="both", expand=True, pady=2)
        self.lb = tk.Listbox(fl, selectmode="extended", exportselection=False, height=12)
        sc = ttk.Scrollbar(fl, command=self.lb.yview)
        self.lb.configure(yscrollcommand=sc.set)
        sc.pack(side="right", fill="y")
        self.lb.pack(fill="both", expand=True)
        bt = ttk.Frame(f1)
        bt.pack(fill="x", pady=(4, 0))
        ttk.Button(bt, text="Pilih semua", command=lambda: (self.lb.selection_set(0, "end"), self._saat_target())
                   ).pack(side="left")
        ttk.Button(bt, text="Kosongkan", command=lambda: self.lb.selection_clear(0, "end")
                   ).pack(side="left", padx=6)

        # kolom 1 - praproses + evaluasi
        tengah = ttk.Frame(p)
        tengah.grid(row=0, column=1, sticky="nsew", padx=6)
        f2 = ttk.LabelFrame(tengah, text="2. Praproses", padding=10)
        f2.pack(fill="x")
        self.v_kosong = tk.StringVar(value="imputasi")
        ttk.Label(f2, text="Nilai kosong (missing value):").pack(anchor="w")
        ttk.Radiobutton(f2, text="Isi otomatis (median / modus)", variable=self.v_kosong,
                        value="imputasi").pack(anchor="w")
        ttk.Radiobutton(f2, text="Hapus baris yang kosong", variable=self.v_kosong,
                        value="hapus").pack(anchor="w")
        ttk.Label(f2, text="Scaling fitur numerik:").pack(anchor="w", pady=(8, 0))
        self.v_scaling = tk.StringVar(value=SCALING_LIST[0])
        ttk.Combobox(f2, textvariable=self.v_scaling, values=SCALING_LIST, state="readonly").pack(fill="x")
        ttk.Label(f2, text="Kolom kategorik di-encode otomatis (One-Hot).\n"
                           "Algoritma berbasis pohon (Decision Tree, Random Forest,\n"
                           "Gradient Boosting) tidak memakai scaling, sehingga aturan\n"
                           "pohon tetap dalam satuan asli.",
                  foreground="#777", justify="left").pack(anchor="w", pady=(6, 0))

        f3 = ttk.LabelFrame(tengah, text="3. Metode evaluasi", padding=10)
        f3.pack(fill="x", pady=(8, 0))
        self.v_metode = tk.StringVar(value="holdout")
        self.v_test, self.v_k, self.v_seed = tk.IntVar(value=30), tk.IntVar(value=5), tk.IntVar(value=42)
        self.v_strat = tk.BooleanVar(value=True)
        ttk.Radiobutton(f3, text="Hold-out (split data latih / uji)", variable=self.v_metode,
                        value="holdout").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(f3, text="   Data uji (%)").grid(row=1, column=0, sticky="w")
        ttk.Spinbox(f3, from_=10, to=50, textvariable=self.v_test, width=6).grid(row=1, column=1, sticky="w")
        ttk.Checkbutton(f3, text="Stratified (proporsi kelas dijaga)", variable=self.v_strat
                        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=(18, 0))
        ttk.Radiobutton(f3, text="K-Fold Cross Validation", variable=self.v_metode,
                        value="kfold").grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Label(f3, text="   Jumlah fold (k)").grid(row=4, column=0, sticky="w")
        ttk.Spinbox(f3, from_=2, to=20, textvariable=self.v_k, width=6).grid(row=4, column=1, sticky="w")
        ttk.Label(f3, text="Random seed").grid(row=5, column=0, sticky="w", pady=(8, 0))
        ttk.Spinbox(f3, from_=0, to=99999, textvariable=self.v_seed, width=8).grid(
            row=5, column=1, sticky="w", pady=(8, 0))

        # kolom 2 - algoritma
        f4 = ttk.LabelFrame(p, text="4. Algoritma yang diuji", padding=10)
        f4.grid(row=0, column=2, sticky="nsew", padx=(6, 0))
        self.v_algo = {n: tk.BooleanVar(value=ALGO_DEFAULT[n]) for n in ALGO_NAMA}
        self.v_dt_crit, self.v_dt_depth = tk.StringVar(value="gini"), tk.StringVar(value="")
        self.v_rf_n, self.v_knn_k = tk.IntVar(value=100), tk.IntVar(value=5)
        for i, n in enumerate(ALGO_NAMA):
            ttk.Checkbutton(f4, text=n, variable=self.v_algo[n]).grid(row=i * 2, column=0, sticky="w", pady=(6, 0))
            sub = ttk.Frame(f4)
            sub.grid(row=i * 2 + 1, column=0, sticky="w", padx=(22, 0))
            if n == "Decision Tree":
                ttk.Label(sub, text="kriteria").pack(side="left")
                ttk.Combobox(sub, textvariable=self.v_dt_crit, values=["gini", "entropy"],
                             state="readonly", width=8).pack(side="left", padx=4)
                ttk.Label(sub, text="max depth").pack(side="left")
                ttk.Entry(sub, textvariable=self.v_dt_depth, width=4).pack(side="left", padx=4)
            elif n == "Random Forest":
                ttk.Label(sub, text="jumlah pohon").pack(side="left")
                ttk.Spinbox(sub, from_=10, to=1000, increment=10, textvariable=self.v_rf_n,
                            width=6).pack(side="left", padx=4)
            elif n == "K-Nearest Neighbor":
                ttk.Label(sub, text="k tetangga").pack(side="left")
                ttk.Spinbox(sub, from_=1, to=50, textvariable=self.v_knn_k, width=5).pack(side="left", padx=4)
            elif n == "Gradient Boosting":
                ttk.Label(sub, text="(lebih lambat pada data besar)", foreground="#888").pack(side="left")
        bt2 = ttk.Frame(f4)
        bt2.grid(row=len(ALGO_NAMA) * 2, column=0, sticky="w", pady=(10, 0))
        ttk.Button(bt2, text="Pilih semua", command=lambda: [v.set(True) for v in self.v_algo.values()]
                   ).pack(side="left")
        ttk.Button(bt2, text="Kosongkan", command=lambda: [v.set(False) for v in self.v_algo.values()]
                   ).pack(side="left", padx=6)

        # tombol jalankan
        bawah = ttk.Frame(p)
        bawah.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        b = ttk.Button(bawah, text="Jalankan Pengujian", style="Besar.TButton", command=self.jalankan_uji)
        b.pack(side="left")
        self.btn_aksi.append(b)
        ttk.Label(bawah, text="   Pengujian berjalan di latar belakang, jendela tetap responsif.",
                  foreground="#777").pack(side="left")

    def _saat_target(self):
        t = self.v_target.get()
        if self.df is not None and t in self.df.columns:
            idx = list(self.df.columns).index(t)
            self.lb.selection_clear(idx)

    def _fitur_terpilih(self):
        return [self.lb.get(i) for i in self.lb.curselection()]

    @staticmethod
    def _angka(var, nama, minimal, maksimal):
        try:
            v = int(var.get())
        except (tk.TclError, ValueError):
            raise ValueError(f"Nilai '{nama}' harus berupa bilangan bulat.")
        if not minimal <= v <= maksimal:
            raise ValueError(f"Nilai '{nama}' harus antara {minimal} dan {maksimal}.")
        return v

    def _ambil_opsi(self):
        if self.df is None:
            raise ValueError("Muat dataset terlebih dahulu (tab Dataset).")
        target = self.v_target.get()
        fitur = [f for f in self._fitur_terpilih() if f != target]
        algos = [n for n in ALGO_NAMA if self.v_algo[n].get()]
        if not algos:
            raise ValueError("Pilih minimal satu algoritma untuk diuji.")
        depth_txt = self.v_dt_depth.get().strip()
        if depth_txt:
            if not depth_txt.isdigit() or int(depth_txt) < 1:
                raise ValueError("Max depth Decision Tree harus bilangan bulat >= 1 (atau kosongkan).")
            depth = int(depth_txt)
        else:
            depth = None
        seed = self._angka(self.v_seed, "Random seed", 0, 99999)
        opsi = {
            "metode": self.v_metode.get(), "test_size": self._angka(self.v_test, "Data uji (%)", 10, 50),
            "k": self._angka(self.v_k, "Jumlah fold", 2, 20), "seed": seed,
            "stratify": self.v_strat.get(), "scaling": self.v_scaling.get(),
            "hapus_kosong": self.v_kosong.get() == "hapus",
        }
        params = {"seed": seed, "dt_crit": self.v_dt_crit.get(), "dt_depth": depth,
                  "rf_n": self._angka(self.v_rf_n, "Jumlah pohon", 10, 1000),
                  "knn_k": self._angka(self.v_knn_k, "k tetangga", 1, 50)}
        return target, fitur, opsi, algos, params

    def jalankan_uji(self):
        try:
            target, fitur, opsi, algos, params = self._ambil_opsi()
        except ValueError as e:
            messagebox.showwarning("Pengaturan belum lengkap", str(e))
            return
        df = self.df
        self.bg(lambda prog: uji_algoritma(df, target, fitur, opsi, algos, params, prog),
                self._selesai_uji, total=len(algos), teks="Memulai pengujian...")

    # ---------- TAB 3: hasil ----------
    def _tab_hasil(self, p):
        bar = ttk.Frame(p)
        bar.pack(fill="x")
        ttk.Button(bar, text="Ekspor Tabel (CSV)...", command=self.ekspor_csv).pack(side="left")
        ttk.Button(bar, text="Simpan Laporan Lengkap (TXT)...", command=self.ekspor_txt).pack(side="left", padx=6)
        self.l_ringkas = ttk.Label(p, text="Belum ada hasil. Jalankan pengujian di tab Pengaturan.",
                                   wraplength=1100, justify="left")
        self.l_ringkas.pack(anchor="w", pady=6)

        kol = ("no", "algoritma", "acc", "prec", "rec", "f1", "waktu")
        self.tree_hasil = ttk.Treeview(p, columns=kol, show="headings", height=7, selectmode="browse")
        for k, t, w, a in [("no", "No", 40, "center"), ("algoritma", "Algoritma", 200, "w"),
                           ("acc", "Akurasi", 130, "e"), ("prec", "Presisi", 90, "e"),
                           ("rec", "Recall", 90, "e"), ("f1", "F1-Score", 90, "e"),
                           ("waktu", "Waktu (detik)", 100, "e")]:
            self.tree_hasil.heading(k, text=t)
            self.tree_hasil.column(k, width=w, anchor=a)
        self.tree_hasil.tag_configure("best", background="#e6f4ea")
        self.tree_hasil.tag_configure("gagal", foreground="#c0392b")
        self.tree_hasil.pack(fill="x")
        self.tree_hasil.bind("<<TreeviewSelect>>", self._saat_pilih_hasil)

        pw = ttk.PanedWindow(p, orient="horizontal")
        pw.pack(fill="both", expand=True, pady=(8, 0))
        kiri = ttk.Frame(pw)
        kanan = ttk.Frame(pw)
        pw.add(kiri, weight=1)
        pw.add(kanan, weight=1)

        top = ttk.Frame(kiri)
        top.pack(fill="x")
        ttk.Label(top, text="Bandingkan berdasarkan:").pack(side="left")
        self.v_metrik = tk.StringVar(value="Akurasi")
        cb = ttk.Combobox(top, textvariable=self.v_metrik, values=list(METRIK_LIST), state="readonly", width=12)
        cb.pack(side="left", padx=6)
        cb.bind("<<ComboboxSelected>>", lambda e: self._gambar_perbandingan())
        self.chart_banding = BarChart(kiri)
        self.chart_banding.pack(fill="both", expand=True, pady=(4, 0))

        self.nb_detail = ttk.Notebook(kanan)
        self.nb_detail.pack(fill="both", expand=True)
        f_cm, f_lap, f_fit, f_aturan = (ttk.Frame(self.nb_detail) for _ in range(4))
        self.nb_detail.add(f_cm, text=" Confusion Matrix ")
        self.nb_detail.add(f_lap, text=" Laporan Klasifikasi ")
        self.nb_detail.add(f_fit, text=" Fitur Penting ")
        self.nb_detail.add(f_aturan, text=" Aturan Decision Tree ")
        self.chart_cm = ConfusionChart(f_cm)
        self.chart_cm.pack(fill="both", expand=True)
        self.t_lap = self._text_scroll(f_lap)
        self.chart_fit = BarChart(f_fit)
        self.chart_fit.pack(fill="both", expand=True)
        self.t_aturan = self._text_scroll(f_aturan)

    @staticmethod
    def _text_scroll(parent):
        t = tk.Text(parent, font="TkFixedFont", wrap="none", state="disabled")
        sy = ttk.Scrollbar(parent, orient="vertical", command=t.yview)
        sx = ttk.Scrollbar(parent, orient="horizontal", command=t.xview)
        t.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        sy.pack(side="right", fill="y")
        sx.pack(side="bottom", fill="x")
        t.pack(fill="both", expand=True)
        return t

    def _kosongkan_hasil(self):
        self.tree_hasil.delete(*self.tree_hasil.get_children())
        self.chart_banding.set([])
        self.chart_cm.set(None, [])
        self.chart_fit.set([])
        for t in (self.t_lap, self.t_aturan):
            self._isi_text(t, "")
        self.l_ringkas.config(text="Belum ada hasil. Jalankan pengujian di tab Pengaturan.")

    def _selesai_uji(self, res):
        self.hasil = res
        ok, gagal = urutkan_hasil(res["hasil"])
        self.tree_hasil.delete(*self.tree_hasil.get_children())
        for i, h in enumerate(ok, 1):
            acc = f"{h['acc'] * 100:.2f}%" + (f" ± {h['std'] * 100:.2f}" if h["std"] is not None else "")
            self.tree_hasil.insert("", "end", iid=h["nama"], tags=("best",) if i == 1 else (),
                                   values=(i, h["nama"], acc, f"{h['prec'] * 100:.2f}%", f"{h['rec'] * 100:.2f}%",
                                           f"{h['f1'] * 100:.2f}%", f"{h['waktu']:.3f}"))
        for h in gagal:
            self.tree_hasil.insert("", "end", iid=h["nama"], tags=("gagal",),
                                   values=("-", h["nama"], "GAGAL", "", "", "", ""))
        teks = (f"Dataset: {self.nama_data}  |  {res['n_baris']} baris, {res['n_fitur_asli']} fitur, "
                f"{len(res['kelas'])} kelas  |  {res['metode_teks']}")
        if ok:
            teks += f"\nAlgoritma terbaik (akurasi): {ok[0]['nama']} - {ok[0]['acc'] * 100:.2f}%"
        for c in res["peringatan"] + res["catatan"]:
            teks += "\nCatatan: " + c
        for h in gagal:
            teks += f"\n{h['nama']} gagal: {h['error']}"
        self.l_ringkas.config(text=teks)
        self._gambar_perbandingan()
        self.nb.select(self.tab["hasil"])
        if ok:
            self.tree_hasil.selection_set(ok[0]["nama"])
        self.status("Pengujian selesai." if ok else "Semua algoritma gagal, periksa catatan di tab Hasil.")

    def _gambar_perbandingan(self):
        if not self.hasil:
            return
        ok, _ = urutkan_hasil(self.hasil["hasil"])
        kunci = METRIK_LIST[self.v_metrik.get()]
        data = sorted([(h["nama"], h[kunci]) for h in ok], key=lambda x: x[1], reverse=True)
        self.chart_banding.set(data, judul=f"Perbandingan {self.v_metrik.get()}", maks=1.0,
                               fmt="{:.2%}", best=0 if data else None)

    def _saat_pilih_hasil(self, _=None):
        sel = self.tree_hasil.selection()
        if not sel or not self.hasil:
            return
        h = next((x for x in self.hasil["hasil"] if x["nama"] == sel[0]), None)
        if not h or h.get("error"):
            return
        self.chart_cm.set(h["cm"], self.hasil["kelas"])
        self._isi_text(self.t_lap, f"{h['nama']}\n\n{h['laporan']}\n\nConfusion matrix "
                                   f"(baris = aktual, kolom = prediksi):\n{h['cm']}")
        if h["penting"]:
            self.chart_fit.set([(n, v) for n, v in h["penting"]], judul="Fitur penting (15 teratas)",
                               fmt="{:.3f}")
        else:
            self.chart_fit.set([], judul="Fitur penting hanya tersedia untuk Decision Tree, "
                                         "Random Forest, Gradient Boosting, Logistic Regression")
        self._isi_text(self.t_aturan, h["aturan"] or "Aturan pohon hanya tersedia untuk algoritma Decision Tree.")

    def ekspor_csv(self):
        if not self.hasil:
            messagebox.showinfo("Ekspor", "Belum ada hasil untuk diekspor.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                            initialfile="hasil_pengujian.csv")
        if not path:
            return
        ok, _ = urutkan_hasil(self.hasil["hasil"])
        pd.DataFrame([{"Peringkat": i, "Algoritma": h["nama"], "Akurasi": round(h["acc"], 4),
                       "Presisi": round(h["prec"], 4), "Recall": round(h["rec"], 4),
                       "F1": round(h["f1"], 4), "Waktu (detik)": round(h["waktu"], 3)}
                      for i, h in enumerate(ok, 1)]).to_csv(path, index=False, sep=";", encoding="utf-8-sig")
        messagebox.showinfo("Ekspor", f"Tersimpan:\n{path}")

    def ekspor_txt(self):
        if not self.hasil:
            messagebox.showinfo("Ekspor", "Belum ada hasil untuk disimpan.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Teks", "*.txt")],
                                            initialfile="laporan_pengujian.txt")
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(buat_laporan_teks(self.hasil, self.nama_data))
            messagebox.showinfo("Ekspor", f"Tersimpan:\n{path}")

    # ---------- TAB 4: clustering ----------
    def _tab_cluster(self, p):
        kiri = ttk.LabelFrame(p, text="K-Means Clustering", padding=10)
        kiri.pack(side="left", fill="y", padx=(0, 8))
        ttk.Label(kiri, text="Memakai kolom fitur yang dipilih di tab\nPengaturan (kolom target tidak dipakai).",
                  foreground="#666").pack(anchor="w")
        ttk.Label(kiri, text="Jumlah cluster (k):").pack(anchor="w", pady=(12, 0))
        self.v_kc = tk.IntVar(value=3)
        ttk.Spinbox(kiri, from_=2, to=30, textvariable=self.v_kc, width=8).pack(anchor="w")
        b1 = ttk.Button(kiri, text="Jalankan K-Means", command=self.jalankan_kmeans)
        b1.pack(fill="x", pady=(12, 4))
        b2 = ttk.Button(kiri, text="Cari k optimal (2 - 10)", command=self.cari_k)
        b2.pack(fill="x", pady=4)
        ttk.Button(kiri, text="Simpan hasil + cluster (CSV)...", command=self.simpan_cluster).pack(fill="x", pady=4)
        self.btn_aksi += [b1, b2]

        kanan = ttk.Frame(p)
        kanan.pack(side="left", fill="both", expand=True)
        self.chart_elbow = LineChart(kanan, height=240)
        self.chart_elbow.pack(fill="x")
        self.chart_elbow.set([], [], judul="Elbow Method (inertia vs k)")
        self.t_cluster = self._text_scroll(kanan)

    def _fitur_cluster(self):
        if self.df is None:
            raise ValueError("Muat dataset terlebih dahulu.")
        target = self.v_target.get()
        fitur = [f for f in self._fitur_terpilih() if f != target]
        if not fitur:
            raise ValueError("Pilih minimal satu kolom fitur di tab Pengaturan.")
        return fitur

    def jalankan_kmeans(self):
        try:
            fitur = self._fitur_cluster()
            k = self._angka(self.v_kc, "Jumlah cluster", 2, 30)
            seed = self._angka(self.v_seed, "Random seed", 0, 99999)
        except ValueError as e:
            messagebox.showwarning("Clustering", str(e))
            return
        df, scaling = self.df, self.v_scaling.get()
        self.bg(lambda prog: kmeans_jalankan(df, fitur, k, scaling, seed),
                lambda r: self._selesai_kmeans(r, fitur), teks="Menjalankan K-Means...")

    def _selesai_kmeans(self, r, fitur):
        d = self.df.copy()
        d["cluster"] = r["labels"]
        teks = [f"K-Means dengan k = {r['k']}",
                f"Silhouette score : {r['sil']:.4f}   (-1 s/d 1, makin tinggi makin baik)",
                f"Inertia (WCSS)   : {r['inertia']:,.2f}", "",
                "Jumlah data per cluster:", d["cluster"].value_counts().sort_index().to_string()]
        num = [c for c in fitur if kolom_numerik(d[c])][:12]
        if num:
            teks += ["", "Rata-rata fitur numerik per cluster:",
                     d.groupby("cluster")[num].mean().round(3).T.to_string()]
        target = self.v_target.get()
        if target in d.columns and 1 < d[target].nunique() <= 30:
            teks += ["", f"Sebaran kolom '{target}' di tiap cluster:",
                     pd.crosstab(d["cluster"], d[target]).to_string()]
        self._isi_text(self.t_cluster, "\n".join(teks))
        self.cluster_df = d
        self.status(f"K-Means selesai (k = {r['k']}, silhouette = {r['sil']:.3f}).")

    def cari_k(self):
        try:
            fitur = self._fitur_cluster()
            seed = self._angka(self.v_seed, "Random seed", 0, 99999)
        except ValueError as e:
            messagebox.showwarning("Clustering", str(e))
            return
        df, scaling = self.df, self.v_scaling.get()
        self.bg(lambda prog: kmeans_elbow(df, fitur, 10, scaling, seed, prog),
                self._selesai_elbow, total=9, teks="Mencari k optimal...")

    def _selesai_elbow(self, hasil):
        terbaik = max(hasil, key=lambda x: x[2])
        self.chart_elbow.set([h[0] for h in hasil], [h[1] for h in hasil],
                             judul="Elbow Method (inertia vs k)  -  titik hijau = silhouette tertinggi",
                             sumbu_y="Inertia", tandai=terbaik[0])
        baris = ["Hasil pencarian k:", f"{'k':>3}{'Inertia':>16}{'Silhouette':>14}"]
        baris += [f"{k:>3}{ine:>16,.2f}{sil:>14.4f}" for k, ine, sil in hasil]
        baris += ["", f"Saran: k = {terbaik[0]} (silhouette tertinggi = {terbaik[2]:.4f}).",
                  "Perhatikan juga 'siku' pada grafik inertia sebagai pertimbangan tambahan."]
        self._isi_text(self.t_cluster, "\n".join(baris))
        self.v_kc.set(terbaik[0])
        self.status(f"Saran k optimal berdasarkan silhouette: {terbaik[0]}.")

    def simpan_cluster(self):
        if self.cluster_df is None:
            messagebox.showinfo("Simpan", "Jalankan K-Means terlebih dahulu.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                            initialfile="hasil_cluster.csv")
        if path:
            self.cluster_df.to_csv(path, index=False, sep=";", encoding="utf-8-sig")
            messagebox.showinfo("Simpan", f"Tersimpan:\n{path}")


if __name__ == "__main__":
    App().mainloop()
