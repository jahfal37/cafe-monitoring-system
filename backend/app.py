from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import date, datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate



app = Flask(__name__)
CORS(app, origins=["http://localhost:5173"])

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/cafe_monitoring'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)



class Pelanggan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cafe_id = db.Column(db.Integer, db.ForeignKey('cafes.id'), nullable=False)
    tanggal = db.Column(db.Date)
    jumlah = db.Column(db.Integer)

class Device(db.Model):
    __tablename__ = "devices"

    id = db.Column(db.Integer, primary_key=True)
    cafe_id = db.Column(db.Integer, db.ForeignKey('cafes.id'), nullable=False)
    device_code = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(db.Enum("active", "inactive"), nullable=False, default="inactive")
    last_update = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    cafe = db.relationship('Cafe', backref=db.backref('devices', lazy=True))


class Cafe(db.Model):
    __tablename__ = "cafes"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    open_time = db.Column(db.Time, nullable=False)
    close_time = db.Column(db.Time, nullable=False)
    table_count = db.Column(db.Integer, nullable=False)
    camera_count = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    role = db.Column(db.Enum('bapenda', 'cafe'), nullable=False, default='cafe')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@app.route("/")
def home():
    return "Backend Aktif"

@app.route("/api/tambah", methods=["POST"])
def tambah():
    data = request.json

    pelanggan = Pelanggan(
        cafe_id=data["cafe_id"],   # 🔥 WAJIB ADA
        tanggal=date.today(),
        jumlah=data["jumlah"]
    )

    db.session.add(pelanggan)
    db.session.commit()

    return jsonify({"message": "Data berhasil disimpan"})

from datetime import datetime

@app.route("/api/dashboard")
def dashboard():

    cafe_id = request.args.get("cafe_id")
    bulan = request.args.get("bulan")
    tahun = request.args.get("tahun")

    if not cafe_id:
        return jsonify({"error": "cafe_id wajib dikirim"}), 400

    now = datetime.now()
    bulan = int(bulan) if bulan else now.month
    tahun = int(tahun) if tahun else now.year

    query = Pelanggan.query.filter(
        Pelanggan.cafe_id == int(cafe_id),   # 🔥 FILTER CAFE
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
        "Senin","Selasa","Rabu","Kamis",
        "Jumat","Sabtu","Minggu"
    ]

    return jsonify({
        "total_saat_ini": total,
        "rata_rata_bulan": rata,
        "bulan": bulan_list[bulan],
        "tahun": tahun,
        "data_harian": [
            {
                "hari": hari_list[p.tanggal.weekday()],
                "tanggal": p.tanggal.day,
                "jumlah": p.jumlah
            }
            for p in data
        ]
    })
@app.route("/api/devices/stats/<int:cafe_id>", methods=["GET"])
def device_stats(cafe_id):

    total = Device.query.filter_by(cafe_id=cafe_id).count()
    active = Device.query.filter_by(cafe_id=cafe_id, status="active").count()
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

@app.route("/api/devices", methods=["POST"])    
def add_device():
    data = request.json

    device = Device(
        cafe_id=data["cafe_id"],
        device_code=data["device_code"],
        status=data.get("status", "inactive")
    )

    db.session.add(device)
    db.session.commit()

    return jsonify({"message": "Device berhasil ditambahkan"})


@app.route("/api/cafes", methods=["GET"]) # GET /api/cafes - Mendapatkan semua cafe
def get_cafes():
    cafes = Cafe.query.order_by(Cafe.created_at.desc()).all()

    result = [
        {
            "id": c.id,
            "name": c.name,
            "address": c.address,
            "open_time": c.open_time.strftime("%H:%M"),
            "close_time": c.close_time.strftime("%H:%M"),
            "table_count": c.table_count,
            "camera_count": c.camera_count
        }
        for c in cafes
    ]

    return jsonify(result)

@app.route("/api/cafes", methods=["POST"]) # POST /api/cafes - Menambahkan cafe baru
def add_cafe():
    data = request.json

    required_fields = [
        "name", "address", "open_time", "close_time",
        "table_count", "camera_count", "username", "password"
    ]

    if not all(field in data for field in required_fields):
        return jsonify({"error": "Semua field wajib diisi"}), 400

    # Cek username unik
    if Cafe.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "Username sudah digunakan"}), 400

    new_cafe = Cafe(
        name=data["name"],
        address=data["address"],
        open_time=datetime.strptime(data["open_time"], "%H:%M").time(),
        close_time=datetime.strptime(data["close_time"], "%H:%M").time(),
        table_count=int(data["table_count"]),
        camera_count=int(data["camera_count"]),
        username=data["username"],
        password=generate_password_hash(data["password"])
    )

    db.session.add(new_cafe)
    db.session.commit()

    return jsonify({"message": "Cafe berhasil ditambahkan"}), 201

@app.route("/api/cafes/<int:cafe_id>", methods=["GET"]) # GET /api/cafes/<id> - Edit page
def get_cafe(cafe_id):
    cafe = Cafe.query.get_or_404(cafe_id)

    return jsonify({
        "id": cafe.id,
        "name": cafe.name,
        "address": cafe.address,
        "open_time": cafe.open_time.strftime("%H:%M"),
        "close_time": cafe.close_time.strftime("%H:%M"),
        "table_count": cafe.table_count,
        "camera_count": cafe.camera_count,
        "username": cafe.username
    })

@app.route("/api/cafes/<int:cafe_id>", methods=["PUT"]) # PUT /api/cafes/<id> - Update cafe
def update_cafe(cafe_id):
    cafe = Cafe.query.get_or_404(cafe_id)
    data = request.json

    cafe.name = data["name"]
    cafe.address = data["address"]
    cafe.open_time = datetime.strptime(data["open_time"], "%H:%M").time()
    cafe.close_time = datetime.strptime(data["close_time"], "%H:%M").time()
    cafe.table_count = int(data["table_count"])
    cafe.camera_count = int(data["camera_count"])
    cafe.username = data["username"]

    if data.get("password"):
        cafe.password = generate_password_hash(data["password"])

    db.session.commit()

    return jsonify({"message": "Cafe berhasil diupdate"})

@app.route("/api/cafes/<int:cafe_id>", methods=["GET"]) 
def get_cafe_detail(cafe_id):
    cafe = Cafe.query.get_or_404(cafe_id)

    return jsonify({
        "id": cafe.id,
        "name": cafe.name,
        "address": cafe.address,
        "open_time": cafe.open_time.strftime("%H:%M"),
        "close_time": cafe.close_time.strftime("%H:%M"),
        "table_count": cafe.table_count,
        "camera_count": cafe.camera_count
    })

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username dan password wajib diisi"}), 400

    cafe = Cafe.query.filter_by(username=username).first()

    if not cafe:
        return jsonify({"error": "Username tidak ditemukan"}), 404

    if not check_password_hash(cafe.password, password):
        return jsonify({"error": "Password salah"}), 401

    return jsonify({
        "message": "Login berhasil",
        "cafe_id": cafe.id,
        "name": cafe.name,
        "role": cafe.role
    })

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
    
    