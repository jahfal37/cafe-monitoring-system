import os
import time
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from mqtt_handler import MQTTHandler
import requests
import json

# =========================
# CONFIG
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(BASE_DIR, "config.json")

with open(config_path) as f:
    config = json.load(f)

BASE_URL = config.get("base_url")

# =========================
# INIT FIREBASE
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
cred_path = os.path.join(BASE_DIR, "serviceAccountKey.json")

if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()


class ROIStateMachine:
    def __init__(self, roi_id, cafe_id, device_code):
        if not cafe_id:
            raise ValueError("cafe_id wajib diisi")

        self.roi_id = roi_id
        self.cafe_id = cafe_id
        self.device_code = device_code

        self.state = "EMPTY"

        self.start_time = None
        self.no_person_start = None

        self.waiting_time = 0
        self.stay_time = 0
        self.sent = False
        self.service_sent = False
        self.transaction_tracks = set()
        self.valid_track_ids = set()
        # MQTT
        self.mqtt = MQTTHandler()
        self.alert_sent = False

        # stabilizer
        self.food_detected_frames = 0

        # =========================
        # CONFIG
        # =========================
        self.EMPTY_TIMEOUT = 60             # Meja kosong selama 1 menit agar reset kembali
        self.FOOD_STABLE_DURATION = 20  # Makanan harus menetap selama 5 detik (bisa kamu naikkan sesuai kebutuhan)
        self.food_start_time = None    # Menandai kapan makanan mulai terdeteksi      # Makanan Stabil Terdeteksi
        self.ALERT_THRESHOLD = 90          # Buzzer 15 menit (untuk sidang dipercepat 30 detik) 
        self.MIN_WAIT_TIME = 5

        # =========================
        # PERSON TRACKING
        # =========================
        self.person_timers = {}

        self.total_customers = 0

        self.CUSTOMER_VALID_TIME = 20    # Customer agar valid sebagai pelanggan 5 Menit (dipercepat 1 menit untuk sidang)
        self.TRACK_LOST_TIMEOUT = 20       # Tracking Hilang

        # =========================
        # ANTI DOUBLE COUNT
        # =========================
        self.counted_history = []

        self.RECOUNT_BLOCK_TIME = 900
        self.RECOUNT_DISTANCE = 120
        

    # =========================
    # BACKEND: KIRIM CUSTOMER
    # =========================
    def send_customer(self, jumlah):
        url = f"{BASE_URL}/api/tambah"

        data = {
            "cafe_id": self.cafe_id,
            "jumlah": int(jumlah),  # <-- Ganti jadi jumlah dinamis
            "table_number": f"T{self.roi_id}"
        }

        try:
            res = requests.post(url, json=data)
            print(f"[KIRIM AKUMULATIF] ROI {self.roi_id} → Total Orang: {jumlah} | Status: {res.status_code}")
        except Exception as e:
            print("[ERROR API]:", e)

    # =========================
    # BACKEND: KIRIM SERVICE
    # =========================
    def send_service(self, waiting_time):

        valid_count = self.get_valid_customer_count()

        if valid_count <= 0:
            return
        url = f"{BASE_URL}/api/ai/services"

        data = {
            "cafe_id": self.cafe_id,
            "device_code": self.device_code,
            "customer_code": f"T{self.roi_id}-{int(time.time())}",
            "customer_count": valid_count,
            "table_number": f"T{self.roi_id}",
            "waiting_time": int(waiting_time),
            "tanggal": datetime.now().strftime("%Y-%m-%d")
        }

        try:
            res = requests.post(url, json=data)

            print("\n========== SEND SERVICE ==========")
            print("DATA:", data)
            print("STATUS:", res.status_code)
            print("RESPONSE:", res.text)

        except Exception as e:
            print("[ERROR SERVICE]:", e)

    # =========================
    # BACKEND: TOTAL MEJA
    # =========================
    def send_table_total(self, total):
        url = f"{BASE_URL}/api/update-meja"

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

    def get_valid_customer_count(self):

        count = 0

        for pdata in self.person_timers.values():

            if pdata["counted"]:
                count += 1

        return count
    # =========================
    # UPDATE STATE
    # =========================
    def update(self, tracked_persons, food_count):

        now = time.time()

        # ambil ID aktif
        current_ids = set([p["id"] for p in tracked_persons])

        # =========================
        # INIT / UPDATE PERSON (DENGAN SPATIAL RE-ID)
        # =========================
        for person in tracked_persons:

            pid = person["id"]
            pos = person.get("pos", (0, 0))

            if pid not in self.person_timers:
                
                # 1. Cari apakah ada ID lama yang baru saja hilang di posisi terdekat
                matched_old_pid = None
                min_dist = self.RECOUNT_DISTANCE # Batas toleransi jarak (120 piksel)

                for old_pid, pdata in self.person_timers.items():
                    # Pastikan ID lama ini sedang tidak aktif di frame sekarang
                    if old_pid not in current_ids:
                        old_pos = pdata["pos"]
                        # Hitung jarak Euclidean antara koordinat baru dan koordinat lama
                        dist = ((pos[0] - old_pos[0])**2 + (pos[1] - old_pos[1])**2)**0.5
                        
                        if dist < min_dist:
                            min_dist = dist
                            matched_old_pid = old_pid

                # 2. Jika ditemukan ID lama yang cocok, wariskan semua datanya ke ID baru
                if matched_old_pid is not None:
                    self.person_timers[pid] = self.person_timers.pop(matched_old_pid)
                    print(f"[RE-ID MATCH] ID {matched_old_pid} hilang sementara, dilanjutkan oleh ID baru: {pid}")
                
                # 3. Jika benar-benar orang baru (tidak ada ID lama yang dekat), buat timer baru
                else:
                    self.person_timers[pid] = {
                        # pertama duduk
                        "seat_start": now,
                        # waiting dimulai
                        "waiting_start": now,
                        # served dimulai
                        "served_start": None,
                        # status
                        "counted": False,
                        # duration
                        "waiting_duration": 0,
                        "served_duration": 0,
                        "seat_duration": 0,
                        # floating timer
                        "floating_time": 0,
                        # tracking
                        "last_seen": now,
                        "pos": pos
                    }

            else:
                self.person_timers[pid]["last_seen"] = now
                self.person_timers[pid]["pos"] = pos
        # =========================
        # HANDLE TRACK HILANG
        # =========================
        for pid in list(self.person_timers.keys()):

            last_seen = self.person_timers[pid]["last_seen"]

            if now - last_seen > self.TRACK_LOST_TIMEOUT:
                del self.person_timers[pid]

        # =========================
        # UPDATE TIMER PERSON
        # =========================
        newly_counted_this_frame = 0
        for pid, pdata in self.person_timers.items():

            # total duduk
            seat_duration = now - pdata["seat_start"]
            pdata["seat_duration"] = int(seat_duration)

            # =========================
            # WAITING TIMER
            # =========================
            if pdata["served_start"] is None:

                waiting_duration = now - pdata["waiting_start"]

                pdata["waiting_duration"] = int(waiting_duration)

                pdata["served_duration"] = 0

            # =========================
            # SERVED TIMER
            # =========================
            else:

                served_duration = now - pdata["served_start"]

                pdata["served_duration"] = int(served_duration)

            # =========================
            # FLOATING TIMER
            # =========================
            if self.state == "WAITING":

                floating_time = int(now - pdata["seat_start"])

            elif self.state == "SERVED":

                if pdata["served_start"] is not None:
                    floating_time = int(now - pdata["served_start"])
                else:
                    floating_time = 0

            else:
                floating_time = 0

            pdata["floating_time"] = floating_time

            # =========================
            # VALID CUSTOMER
            # =========================
            if (
                pdata["served_duration"] >= self.CUSTOMER_VALID_TIME
                and not pdata["counted"]
                and self.state == "SERVED"
            ):
                pdata["counted"] = True
                self.total_customers += 1
                
                newly_counted_this_frame += 1 

                print(
                    f"[CUSTOMER] VALIDATED -> "
                    f"ID={pid} "
                    f"WAIT={pdata['waiting_duration']}s "
                    f"SERVED={pdata['served_duration']}s "
                    f"TOTAL={pdata['seat_duration']}s"
                )

        if newly_counted_this_frame > 0:
            self.send_customer(newly_counted_this_frame)

            if not self.service_sent:
                self.send_service(self.waiting_time)
                self.service_sent = True

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
            if self.food_start_time is None:
                self.food_start_time = now  # Kunci waktu pertama kali makanan terlihat
        else:
            self.food_start_time = None  # Reset jika makanan sempat hilang dari kamera

        # Makanan dinyatakan stabil jika sudah terdeteksi terus-menerus selama X detik
        food_stable = (
            self.food_start_time is not None 
            and (now - self.food_start_time) >= self.FOOD_STABLE_DURATION
        )

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

                self.stay_time = int(now - self.start_time)

                self.waiting_time = self.stay_time

            # ALERT
            if (
                self.waiting_time >= self.ALERT_THRESHOLD
                and not self.alert_sent
            ):

                self.trigger_buzzer()

                self.alert_sent = True

            # MAKANAN DATANG
            if food_stable and not self.sent:

                self.state = "SERVED"

                now_reset = time.time()

                for pid in self.person_timers:

                    pdata = self.person_timers[pid]

                    pdata["served_start"] = now_reset

                    pdata["waiting_duration"] = int(
                        now_reset - pdata["waiting_start"]
                    )

                    pdata["floating_time"] = 0

                self.sent = True

                for pid in self.person_timers:

                    pdata = self.person_timers[pid]

                    # mulai served timer baru
                    pdata["served_start"] = now_reset

                    # freeze waiting
                    pdata["waiting_duration"] = int(
                        now_reset - pdata["waiting_start"]
                    )

                    # reset floating timer
                    pdata["floating_time"] = 0

                self.sent = True

            # RESET KOSONG
            if self.no_person_start and (
                now - self.no_person_start > self.EMPTY_TIMEOUT
            ):
                self.reset()

        elif self.state == "SERVED":

            # =========================
            # KIRIM SERVICE SETELAH ADA CUSTOMER VALID
            # =========================
            valid_customer = self.get_valid_customer_count()

            if (
                valid_customer > 0
                and not self.service_sent
            ):

                self.service_sent = True

                print(
                    f"[SERVICE SENT] ROI={self.roi_id} "
                    f"CUSTOMER={valid_customer}"
                )

            # =========================
            # LOGIKA RESET LAMA
            # =========================
            if person_count == 0 and food_count == 0:

                if self.no_person_start is None:
                    self.no_person_start = now

                elif now - self.no_person_start > 60:
                    self.reset()

            else:
                self.no_person_start = None

        return (
            self.state,
            self.waiting_time,                
            self.stay_time
        )
    # =========================
    # GET FLOATING LABELS
    # =========================
    def get_floating_labels(self):

        labels = []

        for pid, pdata in self.person_timers.items():

            labels.append({

                "id": pid,

                "pos": pdata["pos"],

                "time": pdata.get("floating_time", 0),

                "state": self.state
            })

        return labels

    # =========================
    # BUZZER
    # =========================
    def trigger_buzzer(self):

        self.mqtt.send_buzzer(
            cafe_id=self.cafe_id,
            table_id=self.roi_id,
            waiting_time=self.waiting_time
        )

    # =========================
    # RESET
    # =========================
    def reset(self):

        self.state = "EMPTY"

        self.start_time = None

        self.no_person_start = None

        self.waiting_time = 0

        self.stay_time = 0

        self.sent = False
        self.service_sent = False

        self.alert_sent = False

        self.food_detected_frames = 0

        # reset tracking
        self.person_timers.clear()
