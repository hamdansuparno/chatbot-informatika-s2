#!/usr/bin/env python3
"""Kalkulator sederhana berbasis terminal.

Cara pakai:
    python kalkulator.py

Contoh input:
    2 + 3 * 4
    (10 - 2) ** 2 / 4
    sqrt(144) + log10(1000)
    ans * 2          <- 'ans' = hasil terakhir
"""

import ast
import math
import operator

# Operator yang diizinkan
OPERATOR = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Fungsi dan konstanta yang diizinkan
FUNGSI = {
    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "log": math.log, "log10": math.log10, "log2": math.log2,
    "abs": abs, "round": round, "floor": math.floor, "ceil": math.ceil,
    "fact": math.factorial, "exp": math.exp,
}
KONSTANTA = {"pi": math.pi, "e": math.e}


def hitung_node(node, ans):
    """Evaluasi pohon ekspresi secara aman (tanpa eval)."""
    if isinstance(node, ast.Expression):
        return hitung_node(node.body, ans)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in OPERATOR:
        kiri = hitung_node(node.left, ans)
        kanan = hitung_node(node.right, ans)
        if isinstance(node.op, ast.Pow) and abs(kanan) > 1000:
            raise ValueError("Pangkat terlalu besar (maksimal 1000)")
        return OPERATOR[type(node.op)](kiri, kanan)
    if isinstance(node, ast.UnaryOp) and type(node.op) in OPERATOR:
        return OPERATOR[type(node.op)](hitung_node(node.operand, ans))
    if isinstance(node, ast.Name):
        if node.id == "ans":
            return ans
        if node.id in KONSTANTA:
            return KONSTANTA[node.id]
        raise ValueError(f"Nama tidak dikenal: {node.id}")
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id not in FUNGSI:
            raise ValueError(f"Fungsi tidak dikenal: {node.func.id}")
        argumen = [hitung_node(a, ans) for a in node.args]
        return FUNGSI[node.func.id](*argumen)
    raise ValueError("Ekspresi tidak valid")


def hitung(teks, ans=0):
    teks = teks.replace("^", "**").replace(",", ".")
    pohon = ast.parse(teks, mode="eval")
    return hitung_node(pohon, ans)


def format_hasil(x):
    if isinstance(x, float) and x.is_integer() and abs(x) < 1e15:
        return str(int(x))
    if isinstance(x, float):
        return f"{x:.10g}"
    return str(x)


BANTUAN = """Perintah:
  bantuan   tampilkan bantuan ini
  riwayat   tampilkan riwayat perhitungan
  hapus     hapus riwayat
  keluar    tutup kalkulator

Operator : + - * / // % ** (atau ^)
Fungsi   : sqrt sin cos tan log log10 log2 abs round floor ceil fact exp
Konstanta: pi e
Khusus   : ans = hasil terakhir"""


def main():
    ans = 0
    riwayat = []
    print("=== Kalkulator Python === (ketik 'bantuan' untuk panduan)")
    while True:
        try:
            teks = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSampai jumpa!")
            break
        if not teks:
            continue
        perintah = teks.lower()
        if perintah in ("keluar", "exit", "quit", "q"):
            print("Sampai jumpa!")
            break
        if perintah == "bantuan":
            print(BANTUAN)
            continue
        if perintah == "riwayat":
            if not riwayat:
                print("Riwayat kosong.")
            for i, (ekspresi, hasil) in enumerate(riwayat, 1):
                print(f"{i}. {ekspresi} = {hasil}")
            continue
        if perintah == "hapus":
            riwayat.clear()
            print("Riwayat dihapus.")
            continue
        try:
            hasil = hitung(teks, ans)
        except ZeroDivisionError:
            print("Error: tidak bisa membagi dengan nol")
        except (ValueError, TypeError, SyntaxError, OverflowError) as err:
            print(f"Error: {err}")
        else:
            ans = hasil
            tampil = format_hasil(hasil)
            riwayat.append((teks, tampil))
            print(tampil)


if __name__ == "__main__":
    main()
