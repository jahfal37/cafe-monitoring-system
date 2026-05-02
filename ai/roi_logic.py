import os
import time
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from mqtt_handler import MQTTHandler

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
    def __init__(self, roi_id, cafe_id="cafe1"):
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
        self.CUSTOMER_VALID_TIME = 10  # 5 menit
        self.TRACK_LOST_TIMEOUT = 8  # toleransi hilang ID (detik)

        # =========================
        # 🆕 ANTI DOUBLE COUNT (15 MENIT)
        # =========================
        self.counted_history = []
        # format: {"pos": (x,y), "time": timestamp}

        self.RECOUNT_BLOCK_TIME = 900   # 15 menit
        self.RECOUNT_DISTANCE = 120     # toleransi pixel

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
        # VALIDASI CUSTOMER (ANTI DOUBLE COUNT)
        # =========================
        for pid, pdata in self.person_timers.items():

            duration = now - pdata["start"]
            pdata["duration"] = int(duration)

            print(f"ID {pid} | durasi {duration:.1f}s | counted {pdata['counted']}")

            # 🔥 hanya proses kalau sudah SERVED
            if self.state != "SERVED":
                continue

            # 🔥 sudah pernah dihitung → skip
            if pdata["counted"]:
                continue

            # 🔥 belum cukup durasi → skip
            if duration < self.CUSTOMER_VALID_TIME:
                continue

            pos = pdata.get("pos", (0, 0))
            is_duplicate = False

            for hist in self.counted_history:
                dist = ((pos[0] - hist["pos"][0])**2 + (pos[1] - hist["pos"][1])**2) ** 0.5
                time_diff = now - hist["time"]

                if dist < self.RECOUNT_DISTANCE and time_diff < self.RECOUNT_BLOCK_TIME:
                    is_duplicate = True
                    break

            pdata["counted"] = True  # 🔥 set dulu biar aman

            if not is_duplicate:
                self.total_customers += 1
                self.send_customer(pid, duration)

                self.counted_history.append({
                    "pos": pos,
                    "time": now
                })

                print(f"[CUSTOMER] ID {pid} dihitung (baru)")
            else:
                print(f"[SKIP] ID {pid} dianggap pelanggan lama (<15 menit)")

        # =========================
        # CLEAN HISTORY (biar tidak numpuk)
        # =========================
        self.counted_history = [
            h for h in self.counted_history
            if now - h["time"] < self.RECOUNT_BLOCK_TIME
        ]

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
        # STATE MACHINE (TIDAK DIUBAH)
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

            if self.waiting_time >= self.ALERT_THRESHOLD and not self.alert_sent:
                self.trigger_buzzer()
                self.alert_sent = True

            if food_stable and not self.sent:
                self.state = "SERVED"
                self.send_service(self.waiting_time)
                self.sent = True

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
    def send_service(self, waiting_time):
        now = datetime.now()

        status = "normal"
        if waiting_time > 900:
            status = "long waiting"

        data = {
            "cafe_id": self.cafe_id,
            "customer_code": f"T{self.roi_id}_{now.strftime('%H%M%S')}",
            "status": status,
            "table_number": f"T{self.roi_id}",
            "tanggal": now.strftime("%Y-%m-%d"),
            "waiting_time": waiting_time
        }

        db.collection("services").add(data)

    # =========================
    def send_customer(self, person_id, duration):
        now = datetime.now()

        data = {
            "cafe_id": self.cafe_id,
            "table_number": f"T{self.roi_id}",
            "person_id": person_id,
            "duration": int(duration),
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "total_customers": self.total_customers
        }

        db.collection("customers").add(data)

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