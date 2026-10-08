-- Database Sistem Penggajian (MySQL / MariaDB)
CREATE DATABASE IF NOT EXISTS db_penggajian CHARACTER SET utf8mb4;
USE db_penggajian;

CREATE TABLE departemen (
  id_departemen   INT AUTO_INCREMENT PRIMARY KEY,
  nama_departemen VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE jabatan (
  id_jabatan        INT AUTO_INCREMENT PRIMARY KEY,
  nama_jabatan      VARCHAR(100) NOT NULL UNIQUE,
  gaji_pokok        DECIMAL(15,2) NOT NULL DEFAULT 0,
  tunjangan_jabatan DECIMAL(15,2) NOT NULL DEFAULT 0
);

CREATE TABLE karyawan (
  id_karyawan   INT AUTO_INCREMENT PRIMARY KEY,
  nik           VARCHAR(20) NOT NULL UNIQUE,
  nama          VARCHAR(150) NOT NULL,
  jenis_kelamin ENUM('L','P') NOT NULL,
  tgl_lahir     DATE,
  alamat        TEXT,
  no_hp         VARCHAR(20),
  email         VARCHAR(100),
  tgl_masuk     DATE NOT NULL,
  status_kerja  ENUM('tetap','kontrak','magang','nonaktif') NOT NULL DEFAULT 'tetap',
  nama_bank     VARCHAR(50),
  no_rekening   VARCHAR(30),
  npwp          VARCHAR(25),
  id_departemen INT NOT NULL,
  id_jabatan    INT NOT NULL,
  FOREIGN KEY (id_departemen) REFERENCES departemen(id_departemen),
  FOREIGN KEY (id_jabatan)    REFERENCES jabatan(id_jabatan)
);

CREATE TABLE absensi (
  id_absensi  INT AUTO_INCREMENT PRIMARY KEY,
  id_karyawan INT NOT NULL,
  tanggal     DATE NOT NULL,
  jam_masuk   TIME,
  jam_keluar  TIME,
  status      ENUM('hadir','izin','sakit','cuti','alpa') NOT NULL,
  UNIQUE (id_karyawan, tanggal),
  FOREIGN KEY (id_karyawan) REFERENCES karyawan(id_karyawan)
);

CREATE TABLE lembur (
  id_lembur    INT AUTO_INCREMENT PRIMARY KEY,
  id_karyawan  INT NOT NULL,
  tanggal      DATE NOT NULL,
  jam_mulai    TIME NOT NULL,
  jam_selesai  TIME NOT NULL,
  total_jam    DECIMAL(5,2) NOT NULL,
  upah_per_jam DECIMAL(15,2) NOT NULL,
  FOREIGN KEY (id_karyawan) REFERENCES karyawan(id_karyawan)
);

CREATE TABLE periode_gaji (
  id_periode  INT AUTO_INCREMENT PRIMARY KEY,
  bulan       TINYINT NOT NULL CHECK (bulan BETWEEN 1 AND 12),
  tahun       SMALLINT NOT NULL,
  tgl_mulai   DATE NOT NULL,
  tgl_selesai DATE NOT NULL,
  status      ENUM('draft','diproses','dibayar') NOT NULL DEFAULT 'draft',
  UNIQUE (bulan, tahun)
);

CREATE TABLE komponen_gaji (
  id_komponen   INT AUTO_INCREMENT PRIMARY KEY,
  nama_komponen VARCHAR(100) NOT NULL UNIQUE,   -- mis. Tunjangan Transport, BPJS, Potongan Alpa
  jenis         ENUM('tunjangan','potongan') NOT NULL,
  tipe_hitung   ENUM('tetap','persen') NOT NULL,
  nilai_default DECIMAL(15,2) NOT NULL DEFAULT 0
);

CREATE TABLE penggajian (
  id_penggajian    INT AUTO_INCREMENT PRIMARY KEY,
  id_karyawan      INT NOT NULL,
  id_periode       INT NOT NULL,
  gaji_pokok       DECIMAL(15,2) NOT NULL,
  total_tunjangan  DECIMAL(15,2) NOT NULL DEFAULT 0,
  total_lembur     DECIMAL(15,2) NOT NULL DEFAULT 0,
  total_potongan   DECIMAL(15,2) NOT NULL DEFAULT 0,
  pph21            DECIMAL(15,2) NOT NULL DEFAULT 0,
  gaji_bersih      DECIMAL(15,2) NOT NULL,
  tgl_bayar        DATE,
  UNIQUE (id_karyawan, id_periode),
  FOREIGN KEY (id_karyawan) REFERENCES karyawan(id_karyawan),
  FOREIGN KEY (id_periode)  REFERENCES periode_gaji(id_periode)
);

CREATE TABLE detail_penggajian (
  id_detail     INT AUTO_INCREMENT PRIMARY KEY,
  id_penggajian INT NOT NULL,
  id_komponen   INT NOT NULL,
  nominal       DECIMAL(15,2) NOT NULL,
  FOREIGN KEY (id_penggajian) REFERENCES penggajian(id_penggajian) ON DELETE CASCADE,
  FOREIGN KEY (id_komponen)   REFERENCES komponen_gaji(id_komponen)
);

CREATE TABLE users (
  id_user       INT AUTO_INCREMENT PRIMARY KEY,
  id_karyawan   INT UNIQUE,
  username      VARCHAR(50) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role          ENUM('admin','hrd','keuangan','karyawan') NOT NULL DEFAULT 'karyawan',
  FOREIGN KEY (id_karyawan) REFERENCES karyawan(id_karyawan)
);

-- Rumus: gaji_bersih = gaji_pokok + total_tunjangan + total_lembur - total_potongan - pph21
