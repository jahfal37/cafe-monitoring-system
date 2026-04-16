from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import date, datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity
)

import firebase_admin
from firebase_admin import credentials, firestore


# =====================================================
# APP CONFIG
# =====================================================
app = Flask(__name__)
CORS(app, origins=["http://localhost:5173"])

app.config["JWT_SECRET_KEY"] = "super-secret-key"

jwt = JWTManager(app)


# =====================================================
# FIREBASE INIT
# =====================================================
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()


# =====================================================
# HELPER
# =====================================================
bulan_list = [
    "", "Januari", "Februari", "Maret", "April",
    "Mei", "Juni", "Juli", "Agustus",
    "September", "Oktober", "November", "Desember"
]

hari_list = [
    "Senin", "Selasa", "Rabu", "Kamis",
    "Jumat", "Sabtu", "Minggu"
]


# =====================================================
# ROOT
# =====================================================
@app.route("/")
def home():
    return "Backend Aktif"


# =====================================================
# LOGIN
# =====================================================
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json

    if not data.get("username") or not data.get("password"):
        return jsonify({"error": "Username dan password wajib diisi"}), 400

    docs = db.collection("cafes")\
        .where("username", "==", data["username"])\
        .get()

    if not docs:
        return jsonify({"error": "Login gagal"}), 401

    cafe_doc = docs[0]
    cafe = cafe_doc.to_dict()

    if not check_password_hash(cafe["password"], data["password"]):
        return jsonify({"error": "Login gagal"}), 401

    access_token = create_access_token(
        identity={
            "id": cafe_doc.id,
            "role": cafe["role"]
        }
    )

    return jsonify({
        "message": "Login berhasil",
        "access_token": access_token,
        "user": {
            "id": cafe_doc.id,
            "name": cafe["name"],
            "role": cafe["role"]
        }
    })


# =====================================================
# TAMBAH DATA PELANGGAN
# =====================================================
@app.route("/api/tambah", methods=["POST"])
def tambah():
    data = request.json

    if not data.get("cafe_id") or not data.get("jumlah"):
        return jsonify({"error": "cafe_id dan jumlah wajib diisi"}), 400

    today = date.today()

    db.collection("pelanggan").add({
        "cafe_id": data["cafe_id"],
        "tanggal": today.isoformat(),
        "bulan": today.month,
        "tahun": today.year,
        "jumlah": int(data["jumlah"])
    })

    return jsonify({"message": "Data berhasil disimpan"})


# =====================================================
# DASHBOARD CAFE
# =====================================================
@app.route("/api/cafe/dashboard")
@jwt_required()
def dashboard_cafe():
    user = get_jwt_identity()
    cafe_id = user["id"]

    bulan = request.args.get("bulan")
    tahun = request.args.get("tahun")

    now = datetime.now()
    bulan = int(bulan) if bulan else now.month
    tahun = int(tahun) if tahun else now.year

    docs = db.collection("pelanggan")\
        .where("cafe_id", "==", cafe_id)\
        .where("bulan", "==", bulan)\
        .where("tahun", "==", tahun)\
        .stream()

    data = []

    for doc in docs:
        item = doc.to_dict()
        tanggal = datetime.strptime(item["tanggal"], "%Y-%m-%d")

        data.append({
            "hari": hari_list[tanggal.weekday()],
            "tanggal": tanggal.day,
            "jumlah": item["jumlah"]
        })

    total = sum(x["jumlah"] for x in data)
    rata = round(total / len(data)) if data else 0

    return jsonify({
        "total_saat_ini": total,
        "rata_rata_bulan": rata,
        "bulan": bulan_list[bulan],
        "tahun": tahun,
        "data_harian": data
    })


# =====================================================
# DASHBOARD BAPENDA
# =====================================================
@app.route("/api/bapenda/dashboard/<string:cafe_id>")
@jwt_required()
def dashboard_bapenda(cafe_id):
    user = get_jwt_identity()

    if user["role"] != "bapenda":
        return jsonify({"error": "Akses ditolak"}), 403

    bulan = request.args.get("bulan")
    tahun = request.args.get("tahun")

    now = datetime.now()
    bulan = int(bulan) if bulan else now.month
    tahun = int(tahun) if tahun else now.year

    docs = db.collection("pelanggan")\
        .where("cafe_id", "==", cafe_id)\
        .where("bulan", "==", bulan)\
        .where("tahun", "==", tahun)\
        .stream()

    data = []

    for doc in docs:
        item = doc.to_dict()
        tanggal = datetime.strptime(item["tanggal"], "%Y-%m-%d")

        data.append({
            "hari": hari_list[tanggal.weekday()],
            "tanggal": tanggal.day,
            "jumlah": item["jumlah"]
        })

    total = sum(x["jumlah"] for x in data)
    rata = round(total / len(data)) if data else 0

    return jsonify({
        "total_saat_ini": total,
        "rata_rata_bulan": rata,
        "bulan": bulan_list[bulan],
        "tahun": tahun,
        "data_harian": data
    })

@app.route("/api/register-bapenda", methods=["POST"])
def register_bapenda():
    data = request.json

    if not data.get("username") or not data.get("password"):
        return jsonify({"error": "Username dan password wajib diisi"}), 400

    existing = db.collection("cafes")\
        .where("username", "==", data["username"])\
        .get()

    if existing:
        return jsonify({"error": "Username sudah digunakan"}), 400

    doc_ref = db.collection("cafes").document()

    doc_ref.set({
        "name": data.get("name", "Admin Bapenda"),
        "username": data["username"],
        "password": generate_password_hash(data["password"]),
        "role": "bapenda",
        "address": "-",
        "open_time": "-",
        "close_time": "-",
        "table_count": 0,
        "camera_count": 0,
        "created_at": datetime.utcnow()
    })

    return jsonify({
        "message": "Akun bapenda berhasil dibuat",
        "id": doc_ref.id
    }), 201

# =====================================================
# DEVICE
# =====================================================
@app.route("/api/devices", methods=["POST"])
def add_device():
    data = request.json

    if not data.get("cafe_id") or not data.get("device_code"):
        return jsonify({"error": "Data tidak lengkap"}), 400

    db.collection("devices").add({
        "cafe_id": data["cafe_id"],
        "device_code": data["device_code"],
        "status": data.get("status", "inactive"),
        "created_at": datetime.utcnow()
    })

    return jsonify({"message": "Device berhasil ditambahkan"})


@app.route("/api/devices/stats/<string:cafe_id>", methods=["GET"])
def device_stats(cafe_id):
    docs = db.collection("devices")\
        .where("cafe_id", "==", cafe_id)\
        .stream()

    devices = [doc.to_dict() for doc in docs]

    total = len(devices)
    active = len([d for d in devices if d["status"] == "active"])
    inactive = total - active

    return jsonify({
        "total": total,
        "active": active,
        "inactive": inactive
    })


@app.route("/api/devices/update/<string:device_code>", methods=["PUT"])
def update_device(device_code):
    data = request.json

    if "status" not in data:
        return jsonify({"error": "Status wajib diisi"}), 400

    if data["status"] not in ["active", "inactive"]:
        return jsonify({"error": "Status tidak valid"}), 400

    docs = db.collection("devices")\
        .where("device_code", "==", device_code)\
        .get()

    if not docs:
        return jsonify({"error": "Device tidak ditemukan"}), 404

    docs[0].reference.update({
        "status": data["status"]
    })

    return jsonify({"message": "Status berhasil diupdate"})


# =====================================================
# CAFE CRUD
# =====================================================
@app.route("/api/cafes", methods=["GET"])
def get_cafes():
    docs = db.collection("cafes").stream()

    result = []

    for doc in docs:
        cafe = doc.to_dict()
        cafe["id"] = doc.id

        cafe.pop("password", None)

        result.append(cafe)

    return jsonify(result)


@app.route("/api/cafes", methods=["POST"])
def add_cafe():
    data = request.json

    required_fields = [
        "name",
        "address",
        "open_time",
        "close_time",
        "table_count",
        "camera_count",
        "username",
        "password"
    ]

    if not all(field in data for field in required_fields):
        return jsonify({"error": "Semua field wajib diisi"}), 400

    existing = db.collection("cafes")\
        .where("username", "==", data["username"])\
        .get()

    if existing:
        return jsonify({"error": "Username sudah digunakan"}), 400

    doc_ref = db.collection("cafes").document()

    doc_ref.set({
        "name": data["name"],
        "address": data["address"],
        "open_time": data["open_time"],
        "close_time": data["close_time"],
        "table_count": int(data["table_count"]),
        "camera_count": int(data["camera_count"]),
        "username": data["username"],
        "password": generate_password_hash(data["password"]),
        "role": "cafe",
        "created_at": datetime.utcnow()
    })

    return jsonify({
        "message": "Cafe berhasil ditambahkan",
        "id": doc_ref.id
    }), 201


@app.route("/api/cafes/<string:cafe_id>", methods=["GET"])
def get_cafe(cafe_id):
    doc = db.collection("cafes").document(cafe_id).get()

    if not doc.exists:
        return jsonify({"error": "Cafe tidak ditemukan"}), 404

    cafe = doc.to_dict()
    cafe["id"] = doc.id

    cafe.pop("password", None)

    return jsonify(cafe)


@app.route("/api/cafes/<string:cafe_id>", methods=["PUT"])
def update_cafe(cafe_id):
    data = request.json

    doc_ref = db.collection("cafes").document(cafe_id)

    if not doc_ref.get().exists:
        return jsonify({"error": "Cafe tidak ditemukan"}), 404

    update_data = {
        "name": data["name"],
        "address": data["address"],
        "open_time": data["open_time"],
        "close_time": data["close_time"],
        "table_count": int(data["table_count"]),
        "camera_count": int(data["camera_count"]),
        "username": data["username"]
    }

    if data.get("password"):
        update_data["password"] = generate_password_hash(data["password"])

    doc_ref.update(update_data)

    return jsonify({"message": "Cafe berhasil diupdate"})



# =====================================================
# RUN APP
# =====================================================
if __name__ == "__main__":
    app.run(debug=True)

