from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import date, datetime

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173"])

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/cafe_monitoring'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Pelanggan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tanggal = db.Column(db.Date)
    jumlah = db.Column(db.Integer)

    from datetime import datetime

class Device(db.Model):
    __tablename__ = "devices"

    id = db.Column(db.Integer, primary_key=True)
    device_code = db.Column(db.String(50), unique=True, nullable=False)
    cafe_name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.Enum("active", "inactive"), nullable=False, default="inactive")
    last_update = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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

@app.route("/api/devices", methods=["GET"])
def get_devices():
    devices = Device.query.all()

    result = [
        {
            "device_code": d.device_code,
            "cafe_name": d.cafe_name,
            "status": d.status,
            "last_update": d.last_update.strftime("%H:%M %d-%m-%Y") 
                if d.last_update else "-"
        }
        for d in devices
    ]

    return jsonify(result)


@app.route("/api/devices/stats", methods=["GET"])
def device_stats():
    total = Device.query.count()
    active = Device.query.filter_by(status="active").count()
    inactive = total - active

    return jsonify({
        "total": total,
        "active": active,
        "inactive": inactive
    })


@app.route("/api/devices/update/<string:device_code>", methods=["PUT"])
def update_device(device_code):
    data = request.json

    if not data or "status" not in data:
        return jsonify({"error": "Status wajib diisi"}), 400

    device = Device.query.filter_by(device_code=device_code).first()

    if not device:
        return jsonify({"error": "Device tidak ditemukan"}), 404

    if data["status"] not in ["active", "inactive"]:
        return jsonify({"error": "Status tidak valid"}), 400

    device.status = data["status"]
    db.session.commit()

    return jsonify({"message": "Status berhasil diupdate"})


with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
    
    