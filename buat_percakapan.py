#!/usr/bin/env python3
"""Pembuat 100 percakapan sehari-hari (perkenalan, curhat, diskusi) lawan jenis.

Jalankan:  python buat_percakapan.py [jumlah] [seed]
Hasil   :  percakapan.md
"""
import random
import sys

COWOK = [("Suparno", "Parno"), ("Budi", "Budi"), ("Andi", "Andi"), ("Raka", "Raka"),
         ("Dimas", "Dimas"), ("Fajar", "Fajar"), ("Rizky", "Rizky"), ("Bagas", "Bagas"),
         ("Yoga", "Yoga"), ("Eko", "Eko"), ("Hendra", "Hendra"), ("Irfan", "Irfan"),
         ("Joko", "Joko"), ("Arif", "Arif"), ("Taufik", "Opik"), ("Wahyu", "Wahyu"),
         ("Gilang", "Gilang"), ("Bayu", "Bayu"), ("Rendi", "Rendi"), ("Agus", "Agus"),
         ("Teguh", "Teguh"), ("Ilham", "Ilham"), ("Naufal", "Opal"), ("Dani", "Dani"),
         ("Satria", "Satria")]
CEWEK = [("Novita", "Novi"), ("Dina", "Dina"), ("Sari", "Sari"), ("Putri", "Putri"),
         ("Maya", "Maya"), ("Rani", "Rani"), ("Ayu", "Ayu"), ("Annisa", "Nisa"),
         ("Wulan", "Wulan"), ("Intan", "Intan"), ("Citra", "Citra"), ("Lina", "Lina"),
         ("Tika", "Tika"), ("Fitri", "Fitri"), ("Dewi", "Dewi"), ("Siti", "Siti"),
         ("Rina", "Rina"), ("Yuni", "Yuni"), ("Nadia", "Nadia"), ("Mega", "Mega"),
         ("Salsa", "Salsa"), ("Indah", "Indah"), ("Lestari", "Tari"), ("Bella", "Bella"),
         ("Dwi", "Dwi")]
KEGIATAN = ["mahasiswa Teknik Informatika", "mahasiswa Akuntansi", "guru SD", "analis data",
            "desainer grafis", "perawat", "mahasiswa S2 Manajemen", "karyawan bank",
            "penulis lepas", "apoteker", "programmer", "dosen muda",
            "mahasiswa Sastra Inggris", "arsitek", "admin e-commerce", "fotografer"]
HOBI = ["naik gunung", "memasak", "main futsal", "membaca novel", "fotografi", "bersepeda",
        "menonton film", "main gitar", "berkebun", "menulis blog", "lari pagi",
        "main badminton", "melukis", "mendengarkan podcast", "main catur", "travelling"]
MINUM = ["kopi susu", "es teh lemon", "teh tarik", "matcha latte", "es jeruk",
         "cokelat panas", "kopi hitam", "wedang jahe"]
TEMPAT = ["kafe dekat kampus", "perpustakaan kota", "kantin kampus", "taman kota",
          "toko buku", "stasiun", "acara seminar", "car free day", "warung bakso",
          "bazar buku", "ruang tunggu bandara", "pameran teknologi"]
KOTA = ["Jakarta", "Bandung", "Yogyakarta", "Surabaya", "Semarang", "Malang", "Medan",
        "Makassar", "Tangerang", "Bogor", "Depok", "Bekasi", "Denpasar", "Palembang"]
MASALAH_C = ["kerjaan numpuk dan atasanku menuntut terus",
             "skripsiku belum ada kemajuan",
             "aku bingung memilih lanjut kuliah atau kerja dulu",
             "aku merasa belum cukup mapan untuk serius dengan seseorang",
             "aku baru putus dan masih sulit move on",
             "aku sering lembur sampai lupa istirahat",
             "aku merasa teman-temanku sudah jauh lebih maju"]
MASALAH_W = ["pasanganku makin jarang memberi kabar",
             "keluargaku terus bertanya kapan aku menikah",
             "aku takut tidak lulus tepat waktu",
             "aku merasa tidak dihargai di tempat kerja",
             "aku baru putus dan masih sedih",
             "aku bingung memilih antara karier dan hubungan",
             "aku merasa minder dibanding teman-teman"]
VALID = ["Kedengarannya berat ya.", "Wajar kok kamu merasa begitu.",
         "Pasti nggak mudah menjalaninya.", "Terima kasih sudah mau cerita."]
TANYA = ["Sudah berapa lama kamu merasa begini?", "Menurutmu, apa yang paling mengganggu?",
         "Kamu mau aku dengarkan saja atau mau ada saran juga?"]
SARAN = ["Coba pecah masalahnya jadi langkah kecil, mulai dari yang paling mudah.",
         "Mungkin kamu perlu istirahat sebentar lalu bicara terbuka dengan orang yang terkait.",
         "Kalau terasa terlalu berat, nggak apa-apa minta bantuan orang terdekat atau konselor.",
         "Tulis dulu apa yang kamu rasakan, biasanya pikiran jadi lebih jelas."]
TERIMA = ["Iya, masuk akal. Aku coba ya.", "Makasih, aku jadi lebih tenang.",
          "Benar juga. Selama ini aku cuma memendam sendiri."]
BANTU = ["Kapan pun butuh teman cerita, kabari aku ya.",
         "Kalau mau, minggu depan kita ngobrol lagi dan kamu ceritakan perkembangannya.",
         "Kamu nggak sendirian, ya. Semangat!"]
DISKUSI = [
    ("lima tahun lagi kamu ingin jadi apa",
     "Aku ingin punya karier yang stabil dan tetap punya waktu untuk keluarga.",
     "Kalau aku, ingin mencoba beberapa bidang dulu sebelum menentukan pilihan."),
    ("enak mana, kerja di startup atau perusahaan besar",
     "Startup belajarnya cepat tapi ritmenya padat.",
     "Perusahaan besar lebih terstruktur, tapi geraknya kadang lambat."),
    ("apakah perlu lanjut S2 setelah lulus",
     "Perlu kalau memang mau mendalami bidang atau jadi dosen.",
     "Pengalaman kerja dulu juga berharga, jadi tahu apa yang sebenarnya dibutuhkan."),
    ("bagaimana kalau pindah ke kota lain demi pekerjaan",
     "Menantang, tapi bisa membuka banyak kesempatan baru.",
     "Aku akan pertimbangkan biaya hidup dan jarak dengan keluarga."),
    ("apa ide usaha kecil yang cocok untuk anak muda",
     "Usaha makanan atau jasa digital modalnya relatif kecil.",
     "Yang penting dimulai kecil dan dievaluasi rutin."),
]
JUDUL = ["Perkenalan santai di tempat umum", "Perkenalan versi gaul (lo-gue)",
         "Perkenalan lewat teman (WhatsApp)", "Perkenalan lewat aplikasi kencan",
         "Curhat dari pihak laki-laki", "Curhat dari pihak perempuan",
         "Diskusi tentang pikiran dan masa depan", "Minta maaf setelah salah paham",
         "Menyatakan perasaan dengan sopan", "Menolak dengan sopan dan tetap berteman",
         "Perkenalan serius (ta'aruf)", "Janjian bertemu pertama kali"]
JUMLAH = [9, 9, 9, 9, 8, 8, 8, 8, 8, 8, 8, 8]  # total 100


def dlg(a, b, pasang):
    """pasang = [(teks_a, teks_b), ...] -> baris bergantian."""
    out = []
    for ta, tb in pasang:
        if ta:
            out.append((a, ta))
        if tb:
            out.append((b, tb))
    return out


def kenalan(x, r):
    C, c, W, w = x["C"], x["c"], x["W"], x["w"]
    buka = r.choice([
        ("Permisi, boleh duduk di sini? Kursi lain penuh.", "Oh, silakan. Nggak apa-apa kok."),
        ("Maaf, itu buku yang kamu bawa bagus ya. Boleh tahu judulnya?",
         "Boleh. Ini buku yang lagi aku baca minggu ini."),
        ("Halo, kayaknya kita sering ketemu di sini ya?", "Iya, aku juga merasa begitu."),
    ])
    p = [buka,
         (f"Kenalin, aku {C}, biasa dipanggil {c}.", f"Aku {W}, panggil aja {w}. Salam kenal, Mas {c}."),
         (f"Salam kenal, {w}. Kamu sering ke sini?", f"Lumayan. Tempatnya tenang, enak buat ngobrol dan kerja."),
         (f"Kegiatanmu sehari-hari apa, {w}?", f"Aku {x['kw']}. Kalau Mas {c}?"),
         (f"Aku {x['kc']}. Hobimu apa?", f"Aku suka {x['hw']}. Mas {c} sendiri?"),
         (f"Aku suka {x['hc']}. Beda ya, tapi seru juga bisa tukar cerita.", "Setuju. Mau tukar nomor WhatsApp?"),
         ("Boleh. Nanti aku chat duluan ya.", "Siap, sampai nanti!")]
    return dlg(C, W, p)


def gaul(x, r):
    C, c, W, w = x["C"], x["c"], x["W"], x["w"]
    p = [("Eh, sori, lo anak sini juga ya? Kayaknya gue pernah lihat lo.", "Iya, gue lagi nungguin temen. Lo siapa?"),
         (f"Gue {c}. Lo?", f"Gue {w}. Salam kenal ya."),
         ("Lo biasanya ngapain kalau weekend?", f"Paling {x['hw']}, atau rebahan hehe. Lo?"),
         (f"Gue sih {x['hc']}. Kapan-kapan ikut aja kalau mau.", "Wah, boleh juga tuh. Tapi gue masih pemula."),
         ("Santai, gue juga dulu pemula kok. Yang penting dicoba.", "Oke deh. Minta IG lo dong."),
         ("Nih, cari aja username gue. Follow back ya.", "Siap, nanti gue follow. Makasih ya, " + c + "!")]
    return dlg(C, W, p)


def lewat_teman(x, r):
    C, c, W, w = x["C"], x["c"], x["W"], x["w"]
    p = [(f"Halo {w}, ini {c}, temannya {x['tmn']}. Maaf ganggu, boleh kenalan?",
          f"Halo {c}, nggak ganggu kok. {x['tmn']} sudah cerita sedikit 😊"),
         (f"Syukurlah. Katanya kamu suka {x['hw']} ya?", "Iya, itu hobiku dari dulu. Kamu suka juga?"),
         (f"Aku sukanya {x['hc']}, tapi tertarik juga sama {x['hw']}.", "Wah, boleh nanti aku kasih rekomendasi."),
         ("Mau banget. Kamu sekarang di mana?", f"Aku lagi di {x['kota']}, kerja sebagai {x['kw']}. Kamu?"),
         (f"Aku di {x['kota2']}, {x['kc']}.", "Oh, berarti beda kota ya. Tapi chat tetap bisa kok."),
         ("Siap. Kapan-kapan kita video call biar lebih akrab?", "Boleh. Akhir pekan ini ya.")]
    return dlg(C, W, p)


def aplikasi(x, r):
    C, c, W, w = x["C"], x["c"], x["W"], x["w"]
    p = [(f"Halo {w}, aku lihat di profilmu kamu suka {x['hw']}. Aku juga tertarik!",
          f"Halo {c}! Iya, itu hobiku. Kamu pernah coba?"),
         ("Belum sering sih, masih belajar. Kamu sudah lama?", "Sudah dua tahun. Kalau mau, aku ceritain pengalamanku."),
         ("Boleh banget. Sebelumnya kenalan dulu ya. Aku " + x["kc"] + ", asal " + x["kota"] + ".",
          f"Aku {x['kw']}, tinggal di {x['kota2']}."),
         ("Wah, lumayan dekat. Kamu nyaman kalau kita ngobrol dulu di sini beberapa hari?",
          "Nyaman. Aku memang lebih suka kenal pelan-pelan dan bertemu di tempat ramai dulu."),
         ("Sepakat. Keamanan dan kenyamanan nomor satu.", "Setuju. Terima kasih sudah menghargai itu, " + c + "."),
         (f"Sama-sama. Kita lanjut ngobrol soal {x['hw']} besok malam?", "Boleh, aku kosong jam 8.")]
    return dlg(C, W, p)


def curhat(x, r, cowok_curhat):
    C, c, W, w = x["C"], x["c"], x["W"], x["w"]
    if cowok_curhat:
        a, an, b, bn, masalah = C, c, W, w, r.choice(MASALAH_C)
    else:
        a, an, b, bn, masalah = W, w, C, c, r.choice(MASALAH_W)
    p = [(f"{bn}, kamu sibuk nggak? Aku mau curhat sebentar.", "Nggak kok, ceritain aja. Aku dengerin."),
         (f"Akhir-akhir ini aku lagi pusing, soalnya {masalah}.", f"{r.choice(VALID)} {r.choice(TANYA)}"),
         (f"Sudah beberapa minggu. Aku jadi susah tidur dan sering kepikiran terus.",
          f"{r.choice(VALID)} Terima kasih sudah percaya cerita ke aku."),
         ("Menurutmu aku harus bagaimana?", r.choice(SARAN)),
         (r.choice(TERIMA), r.choice(BANTU)),
         (f"Makasih ya, {bn}. Lega rasanya sudah cerita.", "Sama-sama. Jaga kesehatan ya.")]
    return dlg(a, b, p)


def diskusi(x, r):
    C, c, W, w = x["C"], x["c"], x["W"], x["w"]
    q, j1, j2 = r.choice(DISKUSI)
    p = [(f"{w}, kamu pernah mikir nggak: {q}?", "Sering banget. Kamu sendiri gimana?"),
         (j1, "Menarik. " + j2),
         ("Berarti kita punya pandangan yang saling melengkapi ya.", "Iya. Kadang butuh sudut pandang orang lain biar nggak terjebak pikiran sendiri."),
         ("Setuju. Biasanya kamu ambil keputusan pakai apa, perasaan atau data?", "Dua-duanya. Aku tulis plus-minusnya dulu, baru dengar kata hati."),
         ("Boleh juga caranya, nanti aku coba.", "Kabari kalau sudah ketemu hasilnya ya."),
         ("Pasti. Makasih sudah mau diskusi, " + w + ".", f"Sama-sama, {c}.")]
    return dlg(C, W, p)


def minta_maaf(x, r):
    C, c, W, w = x["C"], x["c"], x["W"], x["w"]
    sebab = r.choice(["lupa membalas pesan seharian", "telat datang ke janji kita",
                      "salah ngomong waktu kemarin", "membatalkan janji mendadak"])
    p = [(f"{w}, aku mau minta maaf soal kemarin. Aku {sebab}.", "Iya, jujur aku sempat kecewa."),
         ("Aku paham. Nggak ada alasan yang membenarkan, tapi aku nggak bermaksud menyepelekan kamu.",
          "Makasih sudah mau mengakui. Aku cuma ingin dihargai."),
         ("Kamu benar. Ke depan aku kabari lebih dulu kalau ada halangan.", "Oke, itu cukup buatku."),
         ("Boleh aku traktir " + x["minum"] + " sebagai tanda maaf?", "Hehe boleh, tapi lain kali jangan diulang ya."),
         ("Siap, janji.", f"Sudah ya, kita mulai lagi dari awal, {c}.")]
    return dlg(C, W, p)


def nyatakan(x, r):
    C, c, W, w = x["C"], x["c"], x["W"], x["w"]
    p = [(f"{w}, boleh aku bicara serius sebentar?", "Boleh, ada apa?"),
         ("Selama beberapa bulan kita dekat, aku merasa nyaman dan senang bersamamu.", "Aku juga senang berteman denganmu."),
         ("Aku ingin jujur: aku punya perasaan lebih dari teman. Aku nggak minta jawaban sekarang.",
          "Terima kasih sudah jujur dan sopan menyampaikannya."),
         ("Aku cuma nggak mau memendam dan berpura-pura.", "Boleh aku pikirkan dulu beberapa hari?"),
         ("Tentu, ambil waktumu.", f"Terima kasih sudah menghargai perasaanku, {c}."),
         ("Apa pun jawabannya, aku tetap menghargai pertemananmu.", "Aku kabari akhir pekan ini ya.")]
    return dlg(C, W, p)


def menolak(x, r):
    C, c, W, w = x["C"], x["c"], x["W"], x["w"]
    p = [(f"{c}, terima kasih sudah jujur soal perasaanmu kemarin.", "Sama-sama. Gimana keputusanmu?"),
         ("Aku sudah memikirkannya baik-baik. Aku menyayangimu sebagai teman, tapi aku belum bisa lebih dari itu.",
          "Aku mengerti. Terima kasih sudah menjawab dengan jelas."),
         ("Maaf kalau ini mengecewakan. Kamu orang baik dan aku nggak mau menggantung perasaanmu.",
          "Nggak apa-apa. Lebih baik jelas daripada menebak-nebak."),
         ("Semoga kita tetap bisa berteman ya.", "Boleh, tapi beri aku sedikit waktu supaya perasaanku tenang dulu."),
         ("Tentu, ambil waktu yang kamu butuhkan.", "Makasih sudah menghargai, " + w + ".")]
    return dlg(W, C, p)


def taaruf(x, r):
    C, c, W, w = x["C"], x["c"], x["W"], x["w"]
    p = [("Assalamualaikum, terima kasih sudah bersedia bertemu. Saya " + C + ", bekerja sebagai " + x["kc"] + ".",
          f"Waalaikumsalam. Saya {W}, {x['kw']}. Senang bisa berkenalan."),
         ("Boleh saya tahu, apa yang paling Anda cari dalam pernikahan nanti?",
          "Pasangan yang jujur, mau saling mendengarkan, dan sama-sama bertumbuh. Bagaimana dengan Anda?"),
         ("Saya juga ingin pasangan yang bisa berdiskusi soal keuangan dan rencana keluarga.", "Itu penting. Saya setuju."),
         ("Soal kebiasaan, saya cukup sering sibuk di akhir bulan. Saya ingin terbuka sejak awal.",
          f"Terima kasih sudah jujur. Saya sendiri suka {x['hw']} di akhir pekan."),
         ("Menurut saya itu bisa kita atur bersama.", "Baik. Bagaimana kalau kita lanjutkan dengan didampingi keluarga?"),
         ("Setuju. Saya akan menyampaikan ke keluarga saya.", "Saya juga. Terima kasih atas waktunya.")]
    return dlg(C, W, p)


def janjian(x, r):
    C, c, W, w = x["C"], x["c"], x["W"], x["w"]
    p = [(f"Hai {w}, jadi ketemuan hari Sabtu? Aku sudah reservasi di {x['tempat']}.", "Jadi dong! Jam berapa?"),
         ("Jam 4 sore ya. Kalau kamu telat nggak apa-apa, aku tunggu.", "Siap. Aku usahakan tepat waktu."),
         (f"Kamu mau pesan apa nanti? Aku biasanya {x['minum']}.", f"Aku ikut {x['minum']} juga deh."),
         ("Oke. Kalau nanti bingung mau ngobrol apa, kita mulai dari hobi saja ya.", f"Boleh. Aku sudah siap cerita soal {x['hw']}."),
         ("Sampai ketemu Sabtu, hati-hati di jalan.", f"Sampai ketemu, {c}!")]
    return dlg(C, W, p)


FUNGSI = [kenalan, gaul, lewat_teman, aplikasi,
          lambda x, r: curhat(x, r, True), lambda x, r: curhat(x, r, False),
          diskusi, minta_maaf, nyatakan, menolak, taaruf, janjian]


def buat(jumlah=100, seed=2026):
    r = random.Random(seed)
    jenis = []
    for i, n in enumerate(JUMLAH):
        jenis += [i] * n
    jenis = (jenis * (jumlah // len(jenis) + 1))[:jumlah]
    hasil = []
    for no, j in enumerate(jenis, start=1):
        if no % 20 == 1:
            (C, c), (W, w) = COWOK[0], CEWEK[0]
        else:
            (C, c), (W, w) = r.choice(COWOK[1:]), r.choice(CEWEK[1:])
        kc, kw = r.sample(KEGIATAN, 2)
        hc, hw = r.sample(HOBI, 2)
        k1, k2 = r.sample(KOTA, 2)
        tmn = r.choice([n for n, _ in COWOK + CEWEK if n not in (C, W)])
        x = dict(C=C, c=c, W=W, w=w, kc=kc, kw=kw, hc=hc, hw=hw, kota=k1, kota2=k2,
                 tmn=tmn, minum=r.choice(MINUM), tempat=r.choice(TEMPAT))
        baris = FUNGSI[j](x, r)
        hasil.append((no, JUDUL[j], x, baris))
    return hasil


def tulis(hasil, path="percakapan.md"):
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {len(hasil)} Percakapan Sehari-hari Lawan Jenis\n\n")
        f.write("Dibuat dari template dengan nama, kota, hobi, dan kegiatan yang divariasikan.\n\n")
        for no, judul, x, baris in hasil:
            f.write(f"## {no}. {judul}\n\n")
            f.write(f"*Tokoh: {x['C']} ({x['c']}) & {x['W']} ({x['w']}) | Kota: {x['kota']}*\n\n")
            for nama, teks in baris:
                f.write(f"**{nama}:** {teks}\n\n")
            f.write("---\n\n")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    s = int(sys.argv[2]) if len(sys.argv) > 2 else 2026
    tulis(buat(n, s))
    print(f"Selesai: {n} percakapan -> percakapan.md")
