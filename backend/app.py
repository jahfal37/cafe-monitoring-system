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
import threading
import time
import cv2
from flask import Response
import firebase_admin
from firebase_admin import credentials, firestore
from ultralytics import YOLO
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# baru boleh pakai
AI_PATH = os.path.join(BASE_DIR, "../ai")
sys.path.append(AI_PATH)

import frame_store

# path model
model_path = os.path.join(BASE_DIR, "../ai/model/best.pt")

model = YOLO(model_path)


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
    data = request.get_json()

    if not data or "username" not in data or "password" not in data:
        return jsonify({"error": "Data tidak lengkap"}), 400

    username = data["username"]
    password = data["password"]

    # 🔥 cari berdasarkan username
    docs = db.collection("cafes")\
        .where("username", "==", username)\
        .limit(1)\
        .stream()

    doc = next(docs, None)

    # ❗ kalau user tidak ada ATAU password salah → sama saja
    if not doc:
        return jsonify({"error": "Username atau password salah"}), 401

    cafe = doc.to_dict()

    if not check_password_hash(cafe.get("password"), password):
        return jsonify({"error": "Username atau password salah"}), 401

    access_token = create_access_token(
        identity=doc.id,
        additional_claims={"role": cafe.get("role")}
    )

    return jsonify({
        "access_token": access_token,
        "user": {
            "id": doc.id,
            "username": cafe.get("username"),
            "name": cafe.get("name"),
            "role": cafe.get("role")
        }
    })

# =====================================================
# TAMBAH DATA PELANGGAN
# =====================================================


@app.route("/api/tambah", methods=["POST"])
def tambah():
    try:
        data = request.json

        cafe_id = data.get("cafe_id")
        jumlah = int(data.get("jumlah", 0))
        table_number = data.get("table_number")

        if not cafe_id or jumlah <= 0:
            return jsonify({"error": "Data tidak valid"}), 400

        today = date.today()
        tanggal = today.isoformat()

        # 🔥 DOC ID = cafe + tanggal (UNIK PER HARI)
        doc_id = f"{cafe_id}_{tanggal}"

        doc_ref = db.collection("pelanggan").document(doc_id)
        doc = doc_ref.get()

        if doc.exists:
            # 🔥 TAMBAH jumlah (tidak bikin dokumen baru)
            doc_ref.update({
                "jumlah": firestore.Increment(jumlah)
            })
        else:
            # 🔥 BUAT BARU HANYA SEKALI PER HARI
            doc_ref.set({
                "cafe_id": cafe_id,
                "tanggal": tanggal,
                "bulan": today.month,
                "tahun": today.year,
                "jumlah": jumlah
            })

        print(f"[API] +{jumlah} pelanggan ({cafe_id})")

        return jsonify({"message": "Data berhasil diupdate"})

    except Exception as e:
        print("ERROR TAMBAH:", str(e))
        return jsonify({"error": str(e)}), 500

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
# SELECT CAFE BAPENDA
# =====================================================


@app.route("/api/bapenda/cafes", methods=["GET"])
@jwt_required()
def get_cafes_bapenda():
    identity = get_jwt_identity()

    user_doc = db.collection("cafes").document(identity).get()

    if not user_doc.exists:
        return jsonify({"error": "User tidak ditemukan"}), 404

    user = user_doc.to_dict()

    if user["role"] != "bapenda":
        return jsonify({"error": "Akses ditolak"}), 403

    docs = db.collection("cafes")\
        .where("role", "==", "cafe")\
        .stream()

    result = []

    for doc in docs:
        cafe = doc.to_dict()

        result.append({
            "id": doc.id,
            "name": cafe.get("name"),
            "address": cafe.get("address"),
            "open_time": cafe.get("open_time"),     # 🔥 TAMBAH INI
            "close_time": cafe.get("close_time"),   # 🔥 TAMBAH INI
            "table_count": cafe.get("table_count", 0),  # 🔥 TAMBAH INI
        })

    return jsonify(result)


@app.route("/api/cafes", methods=["GET"])
@jwt_required()
def get_cafes():
    docs = db.collection("cafes").stream()

    result = []
    for doc in docs:
        cafe = doc.to_dict()
        cafe["id"] = doc.id
        cafe.pop("password", None)
        result.append(cafe)

    return jsonify(result)


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

    # 🔥 SEMUA HARUS DI DALAM FUNCTION
    for doc in docs:
        item = doc.to_dict()
        tanggal_field = item.get("tanggal")

        try:
            if isinstance(tanggal_field, str):
                tanggal = datetime.strptime(tanggal_field, "%Y-%m-%d")
            elif isinstance(tanggal_field, int):
                tanggal = datetime(tahun, bulan, tanggal_field)
            else:
                continue

            data.append({
                "hari": hari_list[tanggal.weekday()],
                "tanggal": tanggal.day,
                "jumlah": item.get("jumlah", 0)
            })

        except Exception as e:
            print("SKIP DATA ERROR:", item, e)
            continue

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

    username = data["username"]

    doc_ref = db.collection("cafes").document(username)

    # 🔥 cek kalau sudah ada
    if doc_ref.get().exists:
        return jsonify({"error": "Username sudah digunakan"}), 400

    doc_ref.set({
        "name": "Admin Bapenda",
        "username": username,
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
    if user_id != cafe_id and get_jwt()["role"] != "bapenda":
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

    username = data["username"]

    doc_ref = db.collection("cafes").document(username)

    # 🔥 cek langsung by ID (TANPA QUERY)
    if doc_ref.get().exists:
        return jsonify({"error": "Username sudah digunakan"}), 400

    doc_ref.set({
        "name": data["name"],
        "address": data["address"],
        "open_time": data["open_time"],
        "close_time": data["close_time"],
        "table_count": int(data["table_count"]),
        "camera_count": int(data["camera_count"]),
        "username": username,
        "password": generate_password_hash(data["password"]),
        "role": "cafe",
        "created_at": datetime.utcnow()
    })

    return jsonify({
        "message": "Cafe berhasil ditambahkan",
        "id": username   # 🔥 sekarang ID = username
    }), 201


@app.route("/api/cafes/<string:cafe_id>", methods=["PUT"])
@jwt_required()
def update_cafe(cafe_id):
    user_id = get_jwt_identity()

    # 🔒 hanya boleh edit cafe sendiri
    if user_id != cafe_id and get_jwt()["role"] != "bapenda":
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
# GET DEVICES BAPENDA
# ============================


@app.route("/api/bapenda/devices/<string:cafe_id>", methods=["GET"])
@jwt_required()
def get_devices_bapenda(cafe_id):
    claims = get_jwt()

    # 🔒 hanya bapenda
    if claims["role"] != "bapenda":
        return jsonify({"error": "Akses ditolak"}), 403

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
# DELETE CAFE (BAPENDA)
# ============================


@app.route("/api/cafes/<string:cafe_id>", methods=["DELETE"])
@jwt_required()
def delete_cafe(cafe_id):
    claims = get_jwt()

    if claims["role"] != "bapenda":
        return jsonify({"error": "Akses ditolak"}), 403

    doc_ref = db.collection("cafes").document(cafe_id)

    if not doc_ref.get().exists:
        return jsonify({"error": "Cafe tidak ditemukan"}), 404

    doc_ref.delete()

    return jsonify({"message": "Cafe berhasil dihapus"})

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
# VIDEO STREAMING (AMBIL DARI frame_store)
# =====================================================
class CameraStream:
    def __init__(self, src=0):
        self.src = src
        self.frame = None
        self.lock = threading.Lock()
        self.running = True

        thread = threading.Thread(target=self.update, daemon=True)
        thread.start()

    def update(self):
        while self.running:
            frame = frame_store.frame  # 🔥 ambil dari main.py

            if frame is None:
                time.sleep(0.01)
                continue

            annotated_frame = frame.copy()

            # label kamera (optional)
            cv2.putText(
                annotated_frame,
                f"AI Camera {self.src}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2
            )

            with self.lock:
                self.frame = annotated_frame

            time.sleep(0.03)

    def get_frame(self):
        with self.lock:
            return self.frame

    def stop(self):
        self.running = False


# =========================
# CAMERA MANAGER (LAZY LOAD)
# =========================
cameras = {}


def get_camera(index):
    if index not in cameras:
        print(f"[INFO] Membuat stream virtual {index}")
        cameras[index] = CameraStream(index)
    return cameras[index]


# =========================
# FRAME GENERATOR
# =========================
def gen_frames(camera):
    while True:
        frame = camera.get_frame()

        if frame is None:
            time.sleep(0.01)
            continue

        ret, buffer = cv2.imencode(
            '.jpg',
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), 70]
        )

        if not ret:
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' +
               buffer.tobytes() + b'\r\n')


# =========================
# ROUTES
# =========================
@app.route('/video_feed_1')
def video_feed_1():
    cam = get_camera(0)
    return Response(
        gen_frames(cam),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/video_feed_2')
def video_feed_2():
    cam = get_camera(1)
    return Response(
        gen_frames(cam),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route("/api/meja-summary", methods=["GET"])
def meja_summary():
    docs = db.collection("pelanggan").stream()

    result = {}

    for doc in docs:
        item = doc.to_dict()
        meja = item.get("table_number", "unknown")

        result[meja] = result.get(meja, 0) + item.get("jumlah", 0)

    return jsonify(result)


@app.route("/api/update-meja", methods=["POST"])
def update_meja():
    try:
        data = request.json

        cafe_id = data.get("cafe_id")
        table_number = data.get("table_number")
        total = int(data.get("total", 0))

        if not cafe_id or not table_number:
            return jsonify({"error": "Data tidak lengkap"}), 400

        today = date.today().isoformat()

        # 🔥 DOC ID UNIK (kunci konsistensi)
        doc_id = f"{cafe_id}_{today}_{table_number}"

        payload = {
            "cafe_id": cafe_id,
            "table_number": table_number,
            "tanggal": today,
            "bulan": date.today().month,
            "tahun": date.today().year,
            "total": total,
            "updated_at": datetime.utcnow().isoformat()
        }

        db.collection("pelanggan").document(doc_id).set(payload)

        print(f"[UPDATE MEJA] {table_number} = {total}")

        return jsonify({"message": "Update berhasil"})

    except Exception as e:
        print("ERROR UPDATE:", str(e))
        return jsonify({"error": str(e)}), 500


# =====================================================
# RUN APP
# =====================================================
if __name__ == "__main__":
    app.run(debug=True)
