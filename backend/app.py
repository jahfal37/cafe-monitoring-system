from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import date

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/cafe_monitoring'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Pelanggan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tanggal = db.Column(db.Date)
    jumlah = db.Column(db.Integer)

@app.route("/")
def home():
    return "Backend Aktif"

@app.route("/api/tambah", methods=["POST"])
def tambah():
    data = request.json
    pelanggan = Pelanggan(
        tanggal=date.today(),
        jumlah=data["jumlah"]
    )
    db.session.add(pelanggan)
    db.session.commit()
    return jsonify({"message": "Data berhasil disimpan"})

from datetime import datetime

@app.route("/api/dashboard")
def dashboard():
    bulan = request.args.get("bulan")
    tahun = request.args.get("tahun")

    now = datetime.now()
    bulan = int(bulan) if bulan else now.month
    tahun = int(tahun) if tahun else now.year

    query = Pelanggan.query.filter(
        db.extract('month', Pelanggan.tanggal) == bulan,
        db.extract('year', Pelanggan.tanggal) == tahun
    )

    data = query.order_by(Pelanggan.tanggal).all()

    total = sum(p.jumlah for p in data)
    rata = round(total / len(data)) if data else 0

    bulan_list = [
        "", "Januari","Februari","Maret","April","Mei","Juni",
        "Juli","Agustus","September","Oktober","November","Desember"
    ]
    hari_list = [
        "Senin", "Selasa", "Rabu", "Kamis", 
        "Jumat", "Sabtu", "Minggu"
    ]

    nama_bulan = bulan_list[bulan]

    # <- ini harus di-indentasi
    data_harian = [
        {
            "hari": hari_list[p.tanggal.weekday()] if p.tanggal else "",
            "tanggal": p.tanggal.day if p.tanggal else "",
            "jumlah": p.jumlah
        }
        for p in data
    ]

    # <- ini juga harus di-indentasi
    return jsonify({
        "total_saat_ini": total,
        "rata_rata_bulan": rata,
        "bulan": nama_bulan,
        "tahun": tahun,
        "data_harian": data_harian
    })

if __name__ == "__main__":
    app.run(debug=True)
    
    