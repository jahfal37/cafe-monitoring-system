# roi_logic.py
import os
import time
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# =========================
# INIT FIREBASE (sekali saja)
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
cred_path = os.path.join(BASE_DIR, "../backend/serviceAccountKey.json")

if not os.path.exists(cred_path):
    raise FileNotFoundError(f"Firebase key not found: {cred_path}")

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

        self.current_count = 0
        self.max_count = 0

        self.already_logged = False
        self.customer_code = None

        self.food_detected_frames = 0

        # CONFIG
        self.EMPTY_TIMEOUT = 60
        self.WAITING_THRESHOLD = 60
        self.FOOD_STABLE_FRAMES = 5

    # =========================
    # MAIN UPDATE
    # =========================
    def update(self, person_count, food_detected):
        now = time.time()

        # ---------- PERSON TRACK ----------
        if person_count > 0:
            self.no_person_start = None
        else:
            if self.no_person_start is None:
                self.no_person_start = now

        # ---------- FOOD STABILIZER ----------
        if food_detected:
            self.food_detected_frames += 1
        else:
            self.food_detected_frames = 0

        food_stable = self.food_detected_frames >= self.FOOD_STABLE_FRAMES

        # =========================
        # STATE MACHINE
        # =========================

        # -------- EMPTY --------
        if self.state == "EMPTY":
            if person_count > 0:
                self.state = "OCCUPIED"
                self.start_time = now
                self.max_count = person_count
                self.already_logged = False

                # generate customer_code
                self.customer_code = self.generate_customer_code()

                print(f"[ROI {self.roi_id}] → OCCUPIED")

        # -------- OCCUPIED --------
        elif self.state == "OCCUPIED":

            if person_count > self.max_count:
                self.max_count = person_count

            if self.start_time and (now - self.start_time > self.WAITING_THRESHOLD):
                self.state = "WAITING_FOOD"

                if not self.already_logged:
                    self.send_pelanggan()
                    self.already_logged = True

                print(f"[ROI {self.roi_id}] → WAITING_FOOD")

            if self.no_person_start and (now - self.no_person_start > self.EMPTY_TIMEOUT):
                self.reset()
                print(f"[ROI {self.roi_id}] → EMPTY")

        # -------- WAITING FOOD --------
        elif self.state == "WAITING_FOOD":

            waiting_time = int(now - self.start_time)

            if person_count > self.max_count:
                self.max_count = person_count

            if food_stable:
                self.state = "SERVED"

                self.send_service(waiting_time)

                print(f"[ROI {self.roi_id}] → SERVED")

            if self.no_person_start and (now - self.no_person_start > self.EMPTY_TIMEOUT):
                self.reset()
                print(f"[ROI {self.roi_id}] → EMPTY")

        # -------- SERVED --------
        elif self.state == "SERVED":

            if self.no_person_start and (now - self.no_person_start > self.EMPTY_TIMEOUT):
                self.reset()
                print(f"[ROI {self.roi_id}] → EMPTY")

        self.current_count = person_count

        return self.state

    # =========================
    # FIREBASE FUNCTIONS
    # =========================

    def send_pelanggan(self):
        now = datetime.now()

        data = {
            "bulan": now.month,
            "tahun": now.year,
            "tanggal": now.day,
            "cafe_id": self.cafe_id,
            "jumlah": self.max_count
        }

        db.collection("pelanggan").add(data)
        print("[FIREBASE] pelanggan masuk")

    def send_service(self, waiting_time):
        now = datetime.now()

        status = "normal"
        if waiting_time > 900:  # >15 menit
            status = "long waiting"

        data = {
            "cafe_id": self.cafe_id,
            "customer_code": self.customer_code,
            "status": status,
            "table_number": self.roi_id,
            "tanggal": now.strftime("%Y-%m-%d"),
            "waiting_time": waiting_time
        }

        db.collection("services").add(data)
        print("[FIREBASE] service masuk")

    # =========================
    def generate_customer_code(self):
        now = datetime.now()
        return f"{self.cafe_id}_T{self.roi_id}_{now.strftime('%Y%m%d_%H%M%S')}"

    # =========================
    def reset(self):
        self.state = "EMPTY"
        self.start_time = None
        self.no_person_start = None
        self.current_count = 0
        self.max_count = 0
        self.already_logged = False
        self.customer_code = None
        self.food_detected_frames = 0