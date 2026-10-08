"""
nlp_utils.py
============
Fungsi-fungsi utilitas pemrosesan teks (NLP Preprocessing)
untuk pembersihan teks sebelum masuk ke model Machine Learning.
"""

import re

def clean_text(text: str) -> str:
    """
    Membersihkan teks input pengguna:
    1. Mengubah ke huruf kecil (case-folding)
    2. Menghapus tanda baca / simbol non-alfanumerik
    3. Merapikan spasi berlebih
    """
    if not text:
        return ""
    text = str(text).lower()
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
