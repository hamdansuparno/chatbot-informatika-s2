"""
compare_stock_models.py
=======================
Script untuk membandingkan performa model Machine Learning:
- Gaussian Naive Bayes
- Logistic Regression
- Random Forest Classifier
dalam memprediksi arah pergerakan harga saham (Naik vs Turun).
Hasil perbandingan diekspor langsung ke file Excel multi-sheet (.xlsx).
"""

import os
import sys
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.naive_bayes import GaussianNB
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

# Pastikan konsol Windows UTF-8
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(BASE_DIR, "..", "TLKM_Saham_Historis_Orange.csv")
OUTPUT_EXCEL = os.path.join(BASE_DIR, "..", "Perbandingan_Naive_Bayes_Saham.xlsx")

def load_and_prepare_data(file_path):
    """Membaca data historis saham dan membentuk fitur teknikal & target arah pergerakan."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} tidak ditemukan!")

    if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
        df = pd.read_excel(file_path)
    else:
        df = pd.read_csv(file_path)

    # Pastikan ada kolom Date dan Close
    date_col = next((c for c in df.columns if 'date' in c.lower() or 'tanggal' in c.lower()), None)
    close_col = next((c for c in df.columns if 'close' in c.lower() or 'tutup' in c.lower()), None)

    if not close_col:
        # Gunakan kolom numerik terakhir sebagai harga close jika nama kolom tidak standar
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            close_col = numeric_cols[-1]
        else:
            raise ValueError("Dataset tidak memiliki kolom harga numerik untuk analisis saham.")

    if date_col:
        df['Date'] = pd.to_datetime(df[date_col])
        df = df.sort_values('Date').reset_index(drop=True)

    df['Close_Price'] = df[close_col].astype(float)

    # 1. Rekayasa Fitur Teknikal (Feature Engineering)
    df['Daily_Return'] = df['Close_Price'].pct_change()
    df['MA_5'] = df['Close_Price'].rolling(window=5).mean()
    df['MA_20'] = df['Close_Price'].rolling(window=20).mean()
    df['MA_Ratio'] = df['MA_5'] / df['MA_20']
    df['Volatility_5'] = df['Daily_Return'].rolling(window=5).std()
    df['Price_Momentum_5'] = df['Close_Price'] - df['Close_Price'].shift(5)

    if 'Volume' in df.columns:
        df['Volume_Clean'] = pd.to_numeric(df['Volume'], errors='coerce').fillna(0)
        df['Volume_Change'] = df['Volume_Clean'].pct_change()
    else:
        df['Volume_Change'] = 0.0

    # 2. Pembentukan Target: 1 jika harga besok NAIK (Close[t+1] > Close[t]), 0 jika TURUN
    df['Future_Close'] = df['Close_Price'].shift(-1)
    df['Target_Arah'] = (df['Future_Close'] > df['Close_Price']).astype(int)
    df['Target_Label'] = df['Target_Arah'].map({1: 'Naik', 0: 'Turun'})

    # Hapus baris dengan nilai NaN akibat rolling window & shift
    df_clean = df.dropna().reset_index(drop=True)
    return df_clean

def run_model_comparison(file_path=DATASET_PATH, output_excel=OUTPUT_EXCEL):
    print("=" * 65)
    print("   ANALISIS PERBANDINGAN MODEL PREDIKSI SAHAM & NAIVE BAYES")
    print("=" * 65)
    
    df = load_and_prepare_data(file_path)
    print(f"[+] Total data saham bersih: {len(df)} baris")
    naik_count = (df['Target_Arah'] == 1).sum()
    turun_count = (df['Target_Arah'] == 0).sum()
    print(f"[+] Distribusi Target -> Naik: {naik_count} ({naik_count/len(df)*100:.1f}%), Turun: {turun_count} ({turun_count/len(df)*100:.1f}%)")

    # Fitur-fitur untuk klasifikasi
    feature_cols = ['Daily_Return', 'MA_Ratio', 'Volatility_5', 'Price_Momentum_5', 'Volume_Change']
    X = df[feature_cols].values
    y = df['Target_Arah'].values

    # Pembagian Train-Test Split (80% latih, 20% uji) dengan urutan waktu (shuffle=False)
    X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
        X, y, df.index, test_size=0.20, shuffle=False
    )

    print(f"[+] Data Latih: {len(X_train)} sampel | Data Uji: {len(X_test)} sampel")

    # Standarisasi fitur
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Inisialisasi Model
    models = {
        "Gaussian Naive Bayes": GaussianNB(),
        "Logistic Regression": LogisticRegression(random_state=42),
        "Random Forest Classifier": RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    }

    results = []
    predictions_dict = {"Index": idx_test, "Tanggal": df.loc[idx_test, 'Date'].dt.strftime('%Y-%m-%d') if 'Date' in df.columns else idx_test, "Harga_Terakhir": df.loc[idx_test, 'Close_Price'], "Arah_Aktual": df.loc[idx_test, 'Target_Label']}
    cm_records = []

    print("\n[*] Menjalankan pelatihan & evaluasi performa model...")

    for name, model in models.items():
        # Latih model
        model.fit(X_train_scaled, y_train)
        y_pred = model.predict(X_test_scaled)
        
        # Hitung metrik
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        
        cm = confusion_matrix(y_test, y_pred)
        tn, fp, fn, tp = cm.ravel()

        results.append({
            "Model": name,
            "Akurasi (%)": round(acc * 100, 2),
            "Presisi (%)": round(prec * 100, 2),
            "Recall (%)": round(rec * 100, 2),
            "F1-Score (%)": round(f1 * 100, 2),
            "True Positive (TP)": int(tp),
            "False Positive (FP)": int(fp),
            "True Negative (TN)": int(tn),
            "False Negative (FN)": int(fn)
        })

        # Simpan prediksi per baris
        predictions_dict[f"Prediksi_{name}"] = [ 'Naik' if p == 1 else 'Turun' for p in y_pred ]
        
        cm_records.append({
            "Model": name,
            "Prediksi Turun (Aktual Turun) [TN]": int(tn),
            "Prediksi Naik (Aktual Turun) [FP]": int(fp),
            "Prediksi Turun (Aktual Naik) [FN]": int(fn),
            "Prediksi Naik (Aktual Naik) [TP]": int(tp)
        })

    # Buat DataFrame hasil
    df_metrics = pd.DataFrame(results)
    df_predictions = pd.DataFrame(predictions_dict)
    df_cm = pd.DataFrame(cm_records)

    print("\n" + "=" * 65)
    print("           RINGKASAN METRIK EVALUASI MODEL")
    print("=" * 65)
    print(df_metrics[['Model', 'Akurasi (%)', 'Presisi (%)', 'Recall (%)', 'F1-Score (%)']].to_string(index=False))
    print("=" * 65)

    # 4. Simpan ke File Excel dengan Banyak Sheet (Multi-sheet Excel)
    print(f"\n[*] Menyimpan hasil ke file Excel: {output_excel}")
    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
        df_metrics.to_excel(writer, sheet_name="Ringkasan_Performa", index=False)
        df_cm.to_excel(writer, sheet_name="Confusion_Matrix", index=False)
        df_predictions.to_excel(writer, sheet_name="Data_Prediksi_Uji", index=False)
        
        # Simpan juga sampel data fitur historis
        df_fitur_export = df[['Date', 'Close_Price', 'Daily_Return', 'MA_5', 'MA_20', 'Volatility_5', 'Target_Label']].head(500) if 'Date' in df.columns else df.head(500)
        df_fitur_export.to_excel(writer, sheet_name="Data_Historis_Fitur", index=False)

    print(f"[OK] File Excel perbandingan sukses dibuat!")
    return df_metrics, df_predictions

if __name__ == "__main__":
    run_model_comparison()
