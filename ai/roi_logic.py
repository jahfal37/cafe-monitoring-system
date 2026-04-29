import os
import time
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from mqtt_handler import MQTTHandler
import requests

# =========================
# INIT FIREBASE
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
cred_path = os.path.join(BASE_DIR, "../backend/serviceAccountKey.json")

if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()


class ROIStateMachine:
    def __init__(self, roi_id, cafe_id):
        if not cafe_id:
            raise ValueError("cafe_id wajib diisi")

        self.roi_id = roi_id
        self.cafe_id = cafe_id

        self.roi_id = roi_id
        self.cafe_id = cafe_id

        self.state = "EMPTY"

        self.start_time = None
        self.no_person_start = None

        self.waiting_time = 0
        self.sent = False

        # MQTT
        self.mqtt = MQTTHandler()
        self.alert_sent = False

        # stabilizer
        self.food_detected_frames = 0

        # CONFIG
        self.EMPTY_TIMEOUT = 60
        self.FOOD_STABLE_FRAMES = 5
        self.ALERT_THRESHOLD = 900  # 15 menit

        # =========================
        # 🆕 PER PERSON TRACKING
        # =========================
        self.person_timers = {}
        self.total_customers = 0
        self.CUSTOMER_VALID_TIME = 10  # minimal detik sebelum dianggap customer
        self.TRACK_LOST_TIMEOUT = 8    # toleransi hilang ID (detik)

        # =========================
        # 🆕 ANTI DOUBLE COUNT (15 MENIT)
        # =========================
        self.counted_history = []
        # format: {"pos": (x,y), "time": timestamp}

        self.RECOUNT_BLOCK_TIME = 900   # 15 menit
        self.RECOUNT_DISTANCE = 120     # toleransi pixel

    # =========================
    # BACKEND: KIRIM CUSTOMER
    # =========================
    def send_customer(self, person_id, duration):
        url = "http://127.0.0.1:5000/api/tambah"

        data = {
            "cafe_id": self.cafe_id,
            "jumlah": 1,
            "table_number": f"T{self.roi_id}"
        }

        try:
            res = requests.post(url, json=data)
            print(f"[KIRIM] ROI {self.roi_id} →", res.status_code, res.text)
        except Exception as e:
            print("[ERROR API]:", e)

    # =========================
    # BACKEND: KIRIM SERVICE
    # =========================
    def send_service(self, waiting_time):
        url = "http://127.0.0.1:5000/api/services"

        data = {
            "cafe_id": self.cafe_id,
            "customer_code": f"T{self.roi_id}-{int(time.time())}",
            "table_number": f"T{self.roi_id}",
            "waiting_time": int(waiting_time),
            "tanggal": datetime.now().strftime("%Y-%m-%d")
        }

        try:
            res = requests.post(url, json=data)
            print(f"[SERVICE] ROI {self.roi_id} →", res.status_code)
        except Exception as e:
            print("[ERROR SERVICE]:", e)

    # =========================
    # BACKEND: TOTAL MEJA (OPSIONAL)
    # =========================
    def send_table_total(self, total):
        url = "http://127.0.0.1:5000/api/update-meja"

        data = {
            "cafe_id": self.cafe_id,
            "table_number": f"T{self.roi_id}",
            "total": total
        }

        try:
            requests.post(url, json=data)
            print(f"[KIRIM TOTAL] {self.roi_id} = {total}")
        except Exception as e:
            print("ERROR:", e)

    # =========================
    def update(self, tracked_persons, food_count):
        now = time.time()

        # ambil ID aktif
        current_ids = set([p["id"] for p in tracked_persons])

        # =========================
        # INIT / UPDATE PERSON
        # =========================
        for person in tracked_persons:
            pid = person["id"]
            pos = person.get("pos", (0, 0))

            if pid not in self.person_timers:
                self.person_timers[pid] = {
                    "start": now,
                    "counted": False,
                    "duration": 0,
                    "last_seen": now,
                    "pos": pos
                }
            else:
                self.person_timers[pid]["last_seen"] = now
                self.person_timers[pid]["pos"] = pos

        # =========================
        # HANDLE ORANG HILANG (GRACE PERIOD)
        # =========================
        for pid in list(self.person_timers.keys()):
            last_seen = self.person_timers[pid]["last_seen"]

            if now - last_seen > self.TRACK_LOST_TIMEOUT:
                del self.person_timers[pid]

        # =========================
        # VALIDASI CUSTOMER
        # =========================
        for pid, pdata in self.person_timers.items():

            duration = now - pdata["start"]
            pdata["duration"] = int(duration)

            if (
                duration >= self.CUSTOMER_VALID_TIME
                and not pdata["counted"]
                and self.state == "SERVED"
            ):
                pdata["counted"] = True
                self.total_customers += 1

                self.send_customer(pid, duration)

                print(f"[CUSTOMER] ID {pid} dihitung")

        # =========================
        # CONVERT COUNT
        # =========================
        person_count = len(current_ids)

        # =========================
        # TRACK KOSONG
        # =========================
        if person_count == 0:
            if self.no_person_start is None:
                self.no_person_start = now
        else:
            self.no_person_start = None

        # =========================
        # FOOD STABILIZER
        # =========================
        if food_count > 0:
            self.food_detected_frames += 1
        else:
            self.food_detected_frames = 0

        food_stable = self.food_detected_frames >= self.FOOD_STABLE_FRAMES

        # =========================
        # STATE MACHINE
        # =========================
        if self.state == "EMPTY":
            if person_count > 0:
                self.state = "WAITING"
                self.start_time = now
                self.sent = False
                self.alert_sent = False

        elif self.state == "WAITING":

            if self.start_time:
                self.waiting_time = int(now - self.start_time)

            # 🔔 ALERT jika terlalu lama
            if self.waiting_time >= self.ALERT_THRESHOLD and not self.alert_sent:
                self.trigger_buzzer()
                self.alert_sent = True

            # 🍽️ makanan datang → SERVED
            if food_stable and not self.sent:
                self.state = "SERVED"
                self.send_service(self.waiting_time)

                # 🔥 RESET TIMER SEMUA ORANG (BIAR VALID SETELAH SERVED)
                now_reset = time.time()
                for pid in self.person_timers:
                    self.person_timers[pid]["start"] = now_reset

                self.sent = True

            # ⛔ reset jika kosong
            if self.no_person_start and (
                now - self.no_person_start > self.EMPTY_TIMEOUT
            ):
                self.reset()

        elif self.state == "SERVED":
            if self.no_person_start and (
                now - self.no_person_start > self.EMPTY_TIMEOUT
            ):
                self.reset()

        return self.state, self.waiting_time

    # =========================
    def trigger_buzzer(self):
        self.mqtt.send_buzzer(
            cafe_id=self.cafe_id,
            table_id=self.roi_id,
            waiting_time=self.waiting_time
        )

    # =========================
    def reset(self):
        self.state = "EMPTY"
        self.start_time = None
        self.no_person_start = None
        self.waiting_time = 0
        self.sent = False
        self.alert_sent = False
        self.food_detected_frames = 0

        # reset tracking (tapi history tetap)
        self.person_timers.clear()
