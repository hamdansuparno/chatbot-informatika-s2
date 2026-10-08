"""
Visualisasi Chernoff Faces dengan Python (matplotlib + numpy + pandas).

Setiap baris data -> satu wajah. Hingga 10 variabel dipetakan ke fitur wajah:
  0 lebar wajah        5 kemiringan alis
  1 tinggi wajah       6 panjang hidung
  2 ukuran mata        7 lebar mulut
  3 kemiringan mata    8 lengkung mulut (cemberut -> senyum)
  4 ukuran pupil       9 bukaan mulut

Contoh pemakaian:
  python chernoff_faces.py                       # data demo
  python chernoff_faces.py --csv data.csv --label kelas --max-faces 30
  python chernoff_faces.py --csv data.csv --cols umur bmi glukosa --label outcome
"""
import argparse

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Circle, Polygon

FEATURE_NAMES = [
    "lebar wajah", "tinggi wajah", "ukuran mata", "kemiringan mata",
    "ukuran pupil", "kemiringan alis", "panjang hidung", "lebar mulut",
    "lengkung mulut", "bukaan mulut",
]


def lerp(a, b, t):
    return a + (b - a) * t


def minmax(X):
    """Normalisasi tiap kolom ke [0, 1]; kolom konstan -> 0.5."""
    X = np.asarray(X, dtype=float)
    mn, mx = X.min(axis=0), X.max(axis=0)
    rng = np.where(mx - mn == 0, 1, mx - mn)
    Z = (X - mn) / rng
    Z[:, (mx - mn) == 0] = 0.5
    return Z


def bezier(p0, p1, p2, n=40):
    t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 2 * np.array(p0) + 2 * (1 - t) * t * np.array(p1) + t ** 2 * np.array(p2)


def draw_face(ax, v, cx, cy, color="#4C72B0"):
    """Gambar satu wajah di (cx, cy). v = 10 nilai dalam [0, 1]."""
    v = list(v) + [0.5] * (10 - len(v))

    # Kepala
    w = lerp(0.70, 1.00, v[0])
    h = lerp(0.85, 1.25, v[1])
    ax.add_patch(Ellipse((cx, cy), w, h, fc=color, ec="black", lw=1.2, alpha=0.35))
    ax.add_patch(Ellipse((cx, cy), w, h, fc="none", ec="black", lw=1.2))

    # Mata
    ex = w * 0.22
    ey = cy + h * 0.14
    ew = lerp(0.08, 0.22, v[2])
    eh = ew * 0.7
    slant = lerp(-25, 25, v[3])
    pr = ew * lerp(0.15, 0.40, v[4])
    for side in (-1, 1):
        x = cx + side * ex
        ax.add_patch(Ellipse((x, ey), ew, eh, angle=side * slant,
                             fc="white", ec="black", lw=1))
        ax.add_patch(Circle((x, ey), pr, fc="black"))

        # Alis
        bs = lerp(-0.08, 0.08, v[5]) * side
        by = ey + eh * 0.5 + 0.06
        ax.plot([x - ew * 0.6, x + ew * 0.6],
                [by - bs, by + bs], color="black", lw=1.8)

    # Hidung
    nl = lerp(0.06, 0.22, v[6])
    ax.plot([cx, cx - 0.03], [cy + h * 0.05, cy + h * 0.05 - nl],
            color="black", lw=1.2)
    ax.plot([cx - 0.03, cx + 0.03], [cy + h * 0.05 - nl] * 2,
            color="black", lw=1.2)

    # Mulut (dua kurva bezier -> bisa terbuka)
    mw = lerp(0.18, 0.55, v[7]) * (w / 0.85)
    my = cy - h * 0.28
    peak = lerp(-0.12, 0.12, v[8])      # <0 cemberut, >0 senyum (arah ke bawah)
    opening = lerp(0.0, 0.12, v[9])
    left, right = (cx - mw / 2, my), (cx + mw / 2, my)
    # Senyum: bagian tengah mulut lebih RENDAH dari sudut -> peak negatif di sumbu y
    upper = bezier(left, (cx, my - peak * 2), right)
    lower = bezier(left, (cx, my - peak * 2 - opening * 2), right)
    if opening > 0.01:
        ax.add_patch(Polygon(np.vstack([upper, lower[::-1]]),
                             fc="#7a1f1f", ec="black", lw=1))
    ax.plot(upper[:, 0], upper[:, 1], color="black", lw=1.6)
    ax.plot(lower[:, 0], lower[:, 1], color="black", lw=1.6)


def chernoff_faces(data, labels=None, names=None, ncols=6, title="Chernoff Faces",
                   save=None, show=True):
    Z = minmax(data)
    n = len(Z)
    nrows = int(np.ceil(n / ncols))
    cell_w, cell_h = 1.5, 1.9

    palette = plt.get_cmap("tab10")
    colors = ["#4C72B0"] * n
    uniq = None
    if labels is not None:
        uniq = list(dict.fromkeys(labels))
        colors = [palette(uniq.index(l) % 10) for l in labels]

    fig, ax = plt.subplots(figsize=(1.9 * ncols, 2.3 * nrows + 1.5))
    for i in range(n):
        r, c = divmod(i, ncols)
        cx, cy = c * cell_w, -r * cell_h
        draw_face(ax, Z[i], cx, cy, colors[i])
        if names is not None:
            ax.text(cx, cy - 0.78, str(names[i]), ha="center", va="top", fontsize=8)

    ax.set_xlim(-0.9, ncols * cell_w - 0.6)
    ax.set_ylim(-(nrows - 1) * cell_h - 1.3, 0.9)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, fontsize=14, weight="bold")

    if uniq is not None:
        handles = [plt.Line2D([], [], marker="o", ls="", color=palette(k % 10), label=str(u))
                   for k, u in enumerate(uniq)]
        ax.legend(handles=handles, title="Kelompok", loc="upper left",
                  bbox_to_anchor=(1.0, 1.0), frameon=False)

    plt.tight_layout()
    if save:
        fig.savefig(save, dpi=200, bbox_inches="tight")
        print(f"Tersimpan: {save}")
    if show:
        plt.show()
    return fig


def demo_data(seed=42, per_group=8):
    """Data sintetis 3 kelompok x 6 variabel."""
    rng = np.random.default_rng(seed)
    centers = {"A": [2, 8, 3, 5, 1, 6], "B": [6, 3, 7, 2, 5, 4], "C": [9, 6, 5, 9, 8, 1]}
    rows = []
    for g, c in centers.items():
        for _ in range(per_group):
            rows.append(dict(zip(
                ["v1", "v2", "v3", "v4", "v5", "v6"],
                np.array(c) + rng.normal(0, 0.9, 6))) | {"kelompok": g})
    return pd.DataFrame(rows)


def main():
    p = argparse.ArgumentParser(description="Chernoff faces")
    p.add_argument("--csv", help="path file CSV (default: data demo)")
    p.add_argument("--cols", nargs="+", help="kolom numerik (maks 10); default: semua numerik")
    p.add_argument("--label", help="kolom kategori untuk pewarnaan")
    p.add_argument("--max-faces", type=int, default=24)
    p.add_argument("--ncols", type=int, default=6)
    p.add_argument("--out", default="chernoff_faces.png")
    p.add_argument("--no-show", action="store_true")
    a = p.parse_args()

    if a.csv:
        df = pd.read_csv(a.csv)
        label_col = a.label
    else:
        df = demo_data()
        label_col = a.label or "kelompok"

    cols = a.cols or [c for c in df.select_dtypes("number").columns if c != label_col]
    cols = cols[:10]
    df = df.dropna(subset=cols).head(a.max_faces)

    labels = df[label_col].tolist() if label_col else None
    mapping = "\n".join(f"{FEATURE_NAMES[i]} <- {c}" for i, c in enumerate(cols))
    print("Pemetaan variabel -> fitur wajah:\n" + mapping)

    chernoff_faces(df[cols].values, labels=labels, names=df.index.tolist(),
                   ncols=a.ncols, save=a.out, show=not a.no_show)


if __name__ == "__main__":
    main()
