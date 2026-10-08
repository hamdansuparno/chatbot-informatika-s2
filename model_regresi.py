"""
Model Decision Tree, Naive Bayes, KNN (klasifikasi) dan
Regresi Linear Sederhana + Berganda (regresi).

Data: angkatan kerja menurut pendidikan (2005-2022), 11 kolom:
Periode, Bulan, Tidak/belum pernah sekolah, Tidak/belum tamat SD, SD, SLTP,
SLTA Umum/SMU, SLTA Kejuruan/SMK, Akademi/Diploma, Universitas, Total

Cara pakai (di Command Prompt, di folder file ini):
    pip install pandas scikit-learn matplotlib openpyxl
    python model_ml.py "Data Training-1kagglenew.xlsx"
File boleh .xlsx atau .csv.
"""
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold, KFold, cross_val_predict
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, confusion_matrix,
                             r2_score, mean_absolute_error, mean_squared_error)

# ---------------------------------------------------------------- 1. DATA
path = sys.argv[1] if len(sys.argv) > 1 else "Data Training-1kagglenew.xlsx"
df = pd.read_csv(path) if path.lower().endswith(".csv") else pd.read_excel(path)

df = df.iloc[:, :11].copy()          # ambil 11 kolom pertama (abaikan kolom tambahan)
df.columns = ["Periode", "Bulan", "Tdk_Sekolah", "Tdk_Tamat_SD", "SD", "SLTP",
              "SLTA_Umum", "SLTA_Kejuruan", "Akademi_Diploma", "Universitas", "Total"]

df = df.drop_duplicates().reset_index(drop=True)    # hapus baris kembar (Agustus 2022)
df["Bulan"] = df["Bulan"].astype(str).str.lower().str.startswith("feb").map({True: 2, False: 8})
for c in df.columns:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df = df.dropna().reset_index(drop=True)
print(f"Jumlah data setelah dibersihkan: {len(df)} baris\n")

# Kolom Total dibuang (jumlah dari kolom lain), Universitas jadi target
fitur_edu = ["Tdk_Sekolah", "Tdk_Tamat_SD", "SD", "SLTP", "SLTA_Umum",
             "SLTA_Kejuruan", "Akademi_Diploma"]
fitur = ["Periode", "Bulan"] + fitur_edu

# ------------------------------------------------- 2. KLASIFIKASI (3 model)
# Target kategori: Universitas dibagi 3 kelompok sama banyak
df["Kategori_Univ"] = pd.qcut(df["Universitas"], 3, labels=["Rendah", "Sedang", "Tinggi"])
X = df[fitur]
y = df["Kategori_Univ"].astype(str)
labels = ["Rendah", "Sedang", "Tinggi"]

modelk = {
    "Decision Tree": DecisionTreeClassifier(max_depth=3, min_samples_leaf=2, random_state=42),
    "Naive Bayes":   GaussianNB(),
    "KNN (k=3)":     make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=3)),
}
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

print("=== KLASIFIKASI (Cross Validation 5-fold) ===")
hasil = []
for nama, m in modelk.items():
    pred = cross_val_predict(m, X, y, cv=cv)
    hasil.append({
        "Model": nama,
        "Akurasi": accuracy_score(y, pred),
        "Presisi": precision_score(y, pred, average="macro", zero_division=0),
        "Recall": recall_score(y, pred, average="macro", zero_division=0),
        "F1": f1_score(y, pred, average="macro", zero_division=0),
    })
    print(f"\n{nama} - Confusion Matrix (baris=aktual, kolom=prediksi: {labels})")
    print(confusion_matrix(y, pred, labels=labels))
print("\n", pd.DataFrame(hasil).round(3).to_string(index=False))

# Pohon keputusan dilatih pada seluruh data untuk divisualisasikan
dt = DecisionTreeClassifier(max_depth=3, min_samples_leaf=2, random_state=42).fit(X, y)
plt.figure(figsize=(16, 8))
plot_tree(dt, feature_names=fitur, class_names=dt.classes_, filled=True, fontsize=8)
plt.savefig("pohon_decision_tree.png", dpi=150, bbox_inches="tight")
plt.close()
print("\nVariabel terpenting (Decision Tree):")
print(pd.Series(dt.feature_importances_, index=fitur)
        .sort_values(ascending=False).round(3).head(5).to_string())

# ------------------------------------------------------- 3. REGRESI LINEAR
yr = df["Universitas"]
kf = KFold(n_splits=5, shuffle=True, random_state=42)


def evaluasi(nama, kolom):
    Xr = df[kolom]
    m = LinearRegression()
    pred = cross_val_predict(m, Xr, yr, cv=kf)
    m.fit(Xr, yr)
    print(f"\n--- {nama} ---")
    print(f"R2 (data latih)  : {m.score(Xr, yr):.4f}")
    print(f"R2 (cross val)   : {r2_score(yr, pred):.4f}")
    print(f"MAE (cross val)  : {mean_absolute_error(yr, pred):,.0f}")
    print(f"RMSE (cross val) : {np.sqrt(mean_squared_error(yr, pred)):,.0f}")
    print(f"Intercept        : {m.intercept_:,.2f}")
    for k, b in zip(kolom, m.coef_):
        print(f"  koefisien {k:16s}: {b:,.4f}")
    return m


print("\n=== REGRESI (target: Universitas) ===")
m_sederhana = evaluasi("Regresi Linear Sederhana (Periode -> Universitas)", ["Periode"])
m_berganda = evaluasi("Regresi Linear Berganda (semua fitur -> Universitas)", fitur)

# Grafik regresi sederhana
plt.figure(figsize=(7, 4))
plt.scatter(df["Periode"], yr, label="Data aktual")
xs = np.linspace(df["Periode"].min(), df["Periode"].max(), 100).reshape(-1, 1)
plt.plot(xs, m_sederhana.predict(pd.DataFrame(xs, columns=["Periode"])),
         color="red", label="Garis regresi")
plt.xlabel("Periode"); plt.ylabel("Universitas"); plt.legend()
plt.title("Regresi Linear Sederhana")
plt.savefig("regresi_sederhana.png", dpi=150, bbox_inches="tight")
plt.close()

print("\nSelesai. Gambar tersimpan: pohon_decision_tree.png, regresi_sederhana.png")
