from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import date, datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)

import firebase_admin
from firebase_admin import credentials, firestore, db



# =====================================================
# APP CONFIG
# =====================================================
app = Flask(__name__)
CORS(app, origins=["http://localhost:5173"])

app.config["JWT_SECRET_KEY"] = "super-secret-key-yang-panjang-minimal-32-karakter"

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
        identity=cafe_doc.id,
        additional_claims={"role": cafe["role"]}
    )

    return jsonify({
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
    user_id = get_jwt_identity()
    claims = get_jwt()

    if claims["role"] != "cafe":
        return jsonify({"error": "Akses ditolak"}), 403

    print("DEBUG LOGIN ID:", user_id)

    bulan = request.args.get("bulan")
    tahun = request.args.get("tahun")

    now = datetime.now()
    bulan = int(bulan) if bulan else now.month
    tahun = int(tahun) if tahun else now.year

    docs = db.collection("pelanggan")\
        .where("cafe_id", "==", user_id)\
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

    print("JUMLAH DATA:", len(data))

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
    claims = get_jwt()

    if claims["role"] != "bapenda":
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

# =====================================================
# REGISTER BAPENDA
# =====================================================
@app.route("/api/register-bapenda", methods=["POST"])
def register_bapenda():
    data = request.json

    doc_ref = db.collection("cafes").document()

    doc_ref.set({
        "name": "Admin Bapenda",
        "username": data["username"],
        "password": generate_password_hash(data["password"]),
        "role": "bapenda"
    })

    return jsonify({"message": "Bapenda dibuat"})


# =====================================================
# CAFE CRUD
# =====================================================
@app.route("/api/cafes/<string:cafe_id>", methods=["GET"])
@jwt_required()
def get_cafe(cafe_id):
    user_id = get_jwt_identity()

    # 🔒 pastikan hanya cafe sendiri
    if user_id != cafe_id:
        return jsonify({"error": "Akses ditolak"}), 403

    doc = db.collection("cafes").document(cafe_id).get()

    if not doc.exists:
        return jsonify({"error": "Cafe tidak ditemukan"}), 404

    cafe = doc.to_dict()
    cafe["id"] = doc.id

    cafe.pop("password", None)

    return jsonify(cafe)


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


@app.route("/api/cafes/<string:cafe_id>", methods=["PUT"])
@jwt_required()
def update_cafe(cafe_id):
    user_id = get_jwt_identity()

    # 🔒 hanya boleh edit cafe sendiri
    if user_id != cafe_id:
        return jsonify({"error": "Akses ditolak"}), 403

    data = request.json

    doc_ref = db.collection("cafes").document(cafe_id)

    if not doc_ref.get().exists:
        return jsonify({"error": "Cafe tidak ditemukan"}), 404

    try:
        update_data = {
            "name": data.get("name", ""),
            "address": data.get("address", ""),
            "open_time": data.get("open_time", ""),
            "close_time": data.get("close_time", ""),
            "table_count": int(data.get("table_count", 0)),
            "camera_count": int(data.get("camera_count", 0)),
            "username": data.get("username", "")
        }

        # update password kalau diisi
        if data.get("password"):
            update_data["password"] = generate_password_hash(data["password"])

        doc_ref.update(update_data)

        return jsonify({"message": "Cafe berhasil diupdate"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =====================================================
# DUMMY GENERATOR
# =====================================================

@app.route("/api/seed-pelanggan", methods=["POST"])
def seed_pelanggan():
    try:
        data = request.get_json()

        cafe_id = data.get("cafe_id")
        records = data.get("records")

        if not cafe_id or not records:
            return jsonify({
                "error": "cafe_id dan records wajib diisi"
            }), 400

        inserted = 0

        for item in records:
            if not item.get("tanggal") or not item.get("jumlah"):
                continue

            tanggal_obj = datetime.strptime(item["tanggal"], "%Y-%m-%d")

            db.collection("pelanggan").add({
                "cafe_id": cafe_id,
                "tanggal": item["tanggal"],
                "bulan": tanggal_obj.month,
                "tahun": tanggal_obj.year,
                "jumlah": int(item["jumlah"])
            })

            inserted += 1

        return jsonify({
            "message": f"{inserted} data berhasil ditambahkan"
        }), 201

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

# ============================
# GET SERVICES
# ============================
@app.route("/api/services", methods=["GET"])
@jwt_required()
def get_services():
    try:
        cafe_id = get_jwt_identity()
        tanggal = request.args.get("tanggal")

        print("=== DEBUG SERVICES ===")
        print("JWT ID:", cafe_id)
        print("TANGGAL:", tanggal)

        if not tanggal:
            return jsonify({"error": "Tanggal wajib diisi"}), 400

        # 🔥 Query hanya cafe_id dulu (untuk hindari index issue)
        docs = db.collection("services")\
            .where("cafe_id", "==", cafe_id)\
            .stream()

        data = []
        total_wait = 0
        max_wait = 0
        long_wait_count = 0

        for doc in docs:
            item = doc.to_dict()

            # 🔥 filter tanggal di python (AMAN dari masalah index)
            if item.get("tanggal") != tanggal:
                continue

            print("DATA MASUK:", item)

            data.append(item)
            waiting = int(item.get("waiting_time", 0))
            total_wait += waiting

            if waiting > max_wait:
                max_wait = waiting

            if item.get("status") == "long":
                long_wait_count += 1

        rata = round(total_wait / len(data)) if data else 0

        print("TOTAL DATA:", len(data))

        return jsonify({
            "rata_rata": rata,
            "terlama": max_wait,
            "long_wait": long_wait_count,
            "data": data
        })

    except Exception as e:
        print("ERROR SERVICES:", str(e))
        return jsonify({"error": str(e)}), 500

# ============================
# POST SERVICES
# ============================
@app.route("/api/services", methods=["POST"])
@jwt_required()
def add_service():
    data = request.json

    required = [
        "cafe_id",
        "customer_code",
        "table_number",
        "waiting_time",
        "tanggal"
    ]

    if not all(k in data for k in required):
        return jsonify({"error": "Field tidak lengkap"}), 400

    status = "long" if int(data["waiting_time"]) >= 30 else "normal"

    db.collection("services").add({
        "cafe_id": data["cafe_id"],
        "customer_code": data["customer_code"],
        "table_number": data["table_number"],
        "waiting_time": int(data["waiting_time"]),
        "status": status,
        "tanggal": data["tanggal"]
    })

    return jsonify({"message": "Data service berhasil ditambahkan"})

# ============================
# GET DEVICES
# ============================
@app.route("/api/devices", methods=["GET"])
@jwt_required()
def get_devices():
    cafe_id = get_jwt_identity()

    docs = db.collection("devices")\
        .where("cafe_id", "==", cafe_id)\
        .stream()

    data = []
    active = 0

    for doc in docs:
        item = doc.to_dict()
        data.append(item)

        if item.get("status") == "active":
            active += 1

    total = len(data)
    inactive = total - active

    return jsonify({
        "total": total,
        "active": active,
        "inactive": inactive,
        "devices": data
    })

# ============================
# POST DEVICES
# ============================
@app.route("/api/devices", methods=["POST"])
@jwt_required()
def add_device():
    cafe_id = get_jwt_identity()
    data = request.json

    if not data.get("device_code"):
        return jsonify({"error": "device_code wajib"}), 400

    db.collection("devices").add({
        "cafe_id": cafe_id,
        "device_code": data["device_code"],
        "status": "inactive",
        "last_update": datetime.utcnow().isoformat()
    })

    return jsonify({"message": "Device ditambahkan"})
    
# ============================
# PUT DEVICES YOLO
# ============================
@app.route("/api/devices/<string:device_code>", methods=["PUT"])
def update_device(device_code):
    data = request.json

    docs = db.collection("devices")\
        .where("device_code", "==", device_code)\
        .get()

    if not docs:
        return jsonify({"error": "Device tidak ditemukan"}), 404

    docs[0].reference.update({
        "status": data["status"],
        "last_update": datetime.utcnow().isoformat()
    })

    return jsonify({"message": "Status diupdate"})

# =====================================================
# RUN APP
# =====================================================
if __name__ == "__main__":
    app.run(debug=True)

