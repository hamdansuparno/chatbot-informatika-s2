"""
linear_programming_solver.py
============================
Program Python untuk memecahkan persoalan Linear Programming (Pemrograman Linear)
sesuai materi perkuliahan POM-QM for Windows (Hal. 136).
Menggunakan pustaka scipy.optimize.linprog untuk mendapatkan solusi optimal matematis.
"""

import sys
import numpy as np
from scipy.optimize import linprog

# Pastikan konsol Windows UTF-8
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def solve_example_dosen():
    """
    Menyelesaikan contoh kasus dari slide dosen (POM-QM for Windows Hal. 136):
    Maximize Z = 3x + 3y
    Subject to:
      3x + 4y <= 14 (labor hours)
      6x + 4y <= 15 (pounds of material)
      x, y >= 0
    """
    print("=" * 65)
    print("   SOLVER LINEAR PROGRAMMING (POM-QM FOR WINDOWS - CONTOH 1)")
    print("=" * 65)
    print("Fungsi Tujuan  : Maximize Z = 3x + 3y")
    print("Fungsi Kendala :")
    print("  1. 3x + 4y <= 14  (labor hours)")
    print("  2. 6x + 4y <= 15  (pounds of material)")
    print("  3. x, y >= 0      (non-negativity restrictions)")
    print("-" * 65)

    # linprog di scipy secara default meminimalkan f^T * x
    # Untuk Maksimasi Max(Z), kita minimalkan -Z -> koefisien = [-3, -3]
    c = [-3.0, -3.0]
    A_ub = [
        [3.0, 4.0],
        [6.0, 4.0]
    ]
    b_ub = [14.0, 15.0]
    bounds = [(0, None), (0, None)]  # x >= 0, y >= 0

    res = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')

    if res.success:
        opt_x = res.x[0]
        opt_y = res.x[1]
        opt_z = -res.fun

        print("\n[+] HASIL OPTIMAL:")
        print(f"    Nilai x* (Variabel x) = {opt_x:.4f}  (atau 1/3)")
        print(f"    Nilai y* (Variabel y) = {opt_y:.4f}  (atau 13/4 = 3.25)")
        print(f"    Nilai Maksimum Z*     = {opt_z:.4f}  (atau 10.75)")

        print("\n[+] ANALISIS PENGGUNAAN SUMBER DAYA (SLACK):")
        labor_used = 3 * opt_x + 4 * opt_y
        material_used = 6 * opt_x + 4 * opt_y
        print(f"    - Labor hours terpakai : {labor_used:.2f} dari kapasitas 14.0 (Slack: {14.0 - labor_used:.4f})")
        print(f"    - Material terpakai    : {material_used:.2f} dari kapasitas 15.0 (Slack: {15.0 - material_used:.4f})")
        print("    -> Kedua kendala habis terpakai (Binding Constraints / Slack = 0).")
    else:
        print("[!] Solusi tidak ditemukan:", res.message)
    print("=" * 65)

if __name__ == "__main__":
    solve_example_dosen()
