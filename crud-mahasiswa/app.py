"""
Aplikasi CRUD Data Mahasiswa
Stack: Python + Flask + SQLite
"""
import sqlite3
from datetime import date

from flask import Flask, render_template, request, redirect, url_for, flash, g

app = Flask(__name__)
app.secret_key = "ganti-dengan-kunci-rahasia-kamu"
DATABASE = "mahasiswa.db"


# ---------- Database ----------
def get_db():
    """Buka koneksi SQLite (satu koneksi per request)."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Buat tabel jika belum ada. Data tetap tersimpan di file mahasiswa.db."""
    db = sqlite3.connect(DATABASE)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS mahasiswa (
            nim            INTEGER PRIMARY KEY,
            nama           TEXT NOT NULL,
            program_studi  TEXT NOT NULL,
            angkatan       INTEGER NOT NULL,
            ipk            REAL NOT NULL
        )
        """
    )
    db.commit()
    db.close()


# ---------- Validasi ----------
def validasi(form, nim_wajib=True):
    """Kembalikan (data, daftar_error). Semua aturan soal ada di sini."""
    errors = []
    nim_str = form.get("nim", "").strip()
    nama = form.get("nama", "").strip()
    prodi = form.get("program_studi", "").strip()
    angkatan_str = form.get("angkatan", "").strip()
    ipk_str = form.get("ipk", "").strip().replace(",", ".")

    nim = None
    if nim_wajib:
        if not nim_str:
            errors.append("NIM tidak boleh kosong.")
        elif not nim_str.isdigit():
            errors.append("NIM harus berupa angka.")
        else:
            nim = int(nim_str)

    if not nama:
        errors.append("Nama tidak boleh kosong.")
    if not prodi:
        errors.append("Program studi tidak boleh kosong.")

    angkatan = None
    if not angkatan_str:
        errors.append("Angkatan tidak boleh kosong.")
    elif not angkatan_str.isdigit():
        errors.append("Angkatan harus berupa angka (contoh: 2023).")
    else:
        angkatan = int(angkatan_str)

    ipk = None
    if not ipk_str:
        errors.append("IPK tidak boleh kosong.")
    else:
        try:
            ipk = float(ipk_str)
            if not 0.00 <= ipk <= 4.00:
                errors.append("IPK harus di antara 0.00 dan 4.00.")
        except ValueError:
            errors.append("IPK harus berupa angka (contoh: 3.50).")

    data = {"nim": nim, "nama": nama, "program_studi": prodi,
            "angkatan": angkatan, "ipk": ipk}
    return data, errors


def tambah_lama_studi(row):
    """Lama Studi = tahun sekarang - angkatan (dihitung, tidak disimpan)."""
    d = dict(row)
    d["lama_studi"] = date.today().year - d["angkatan"]
    return d


# ---------- Route ----------
@app.route("/")
def index():
    rows = get_db().execute("SELECT * FROM mahasiswa ORDER BY nim").fetchall()
    mahasiswa = [tambah_lama_studi(r) for r in rows]
    return render_template("index.html", mahasiswa=mahasiswa)


@app.route("/mahasiswa/<int:nim>")
def detail(nim):
    row = get_db().execute("SELECT * FROM mahasiswa WHERE nim = ?", (nim,)).fetchone()
    if row is None:
        flash("Data mahasiswa tidak ditemukan.", "error")
        return redirect(url_for("index"))
    return render_template("detail.html", m=tambah_lama_studi(row))


@app.route("/tambah", methods=["GET", "POST"])
def tambah():
    if request.method == "POST":
        data, errors = validasi(request.form)
        db = get_db()
        # Cek NIM duplikat
        if not errors and db.execute(
            "SELECT 1 FROM mahasiswa WHERE nim = ?", (data["nim"],)
        ).fetchone():
            errors.append(f"NIM {data['nim']} sudah terdaftar.")
        # Cek nama kembar (tidak membedakan huruf besar/kecil)
        if not errors and db.execute(
            "SELECT 1 FROM mahasiswa WHERE LOWER(nama) = LOWER(?)", (data["nama"],)
        ).fetchone():
            errors.append(f"Nama '{data['nama']}' sudah terdaftar.")
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("form.html", m=request.form, mode="tambah")
        db.execute(
            "INSERT INTO mahasiswa (nim, nama, program_studi, angkatan, ipk) "
            "VALUES (?, ?, ?, ?, ?)",
            (data["nim"], data["nama"], data["program_studi"],
             data["angkatan"], data["ipk"]),
        )
        db.commit()
        flash("Mahasiswa berhasil ditambahkan.", "success")
        return redirect(url_for("index"))
    return render_template("form.html", m={}, mode="tambah")


@app.route("/ubah/<int:nim>", methods=["GET", "POST"])
def ubah(nim):
    db = get_db()
    row = db.execute("SELECT * FROM mahasiswa WHERE nim = ?", (nim,)).fetchone()
    if row is None:
        flash("Data mahasiswa tidak ditemukan.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        data, errors = validasi(request.form, nim_wajib=False)
        # Cek nama kembar hanya jika nama diganti, dan abaikan data sendiri
        if (not errors and data["nama"].lower() != row["nama"].lower()
                and db.execute(
                    "SELECT 1 FROM mahasiswa WHERE LOWER(nama) = LOWER(?) AND nim != ?",
                    (data["nama"], nim)).fetchone()):
            errors.append(f"Nama '{data['nama']}' sudah terdaftar.")
        if errors:
            for e in errors:
                flash(e, "error")
            form = request.form.to_dict()
            form["nim"] = nim
            return render_template("form.html", m=form, mode="ubah")
        db.execute(
            "UPDATE mahasiswa SET nama=?, program_studi=?, angkatan=?, ipk=? "
            "WHERE nim=?",
            (data["nama"], data["program_studi"], data["angkatan"], data["ipk"], nim),
        )
        db.commit()
        flash("Data mahasiswa berhasil diubah.", "success")
        return redirect(url_for("index"))
    return render_template("form.html", m=dict(row), mode="ubah")


@app.route("/hapus/<int:nim>", methods=["POST"])
def hapus(nim):
    db = get_db()
    db.execute("DELETE FROM mahasiswa WHERE nim = ?", (nim,))
    db.commit()
    flash("Data mahasiswa berhasil dihapus.", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
