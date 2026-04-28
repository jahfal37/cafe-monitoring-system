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
        self.alert_sent = False   # ✅ anti spam buzzer

        # stabilizer
        self.food_detected_frames = 0

        # CONFIG
        self.EMPTY_TIMEOUT = 60
        self.FOOD_STABLE_FRAMES = 5
        self.ALERT_THRESHOLD = 900  # 15 menit

    # =========================
    def update(self, person_count, food_count):
        now = time.time()

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

        # -------- EMPTY --------
        if self.state == "EMPTY":
            if person_count > 0:
                self.state = "WAITING"
                self.start_time = now
                self.sent = False
                self.alert_sent = False  # reset alert

                print(f"[ROI {self.roi_id}] → WAITING START")

        # -------- WAITING --------
        elif self.state == "WAITING":

            if self.start_time:
                self.waiting_time = int(now - self.start_time)

            # =========================
            # 🚨 MQTT ALERT (15 MENIT)
            # =========================
            if (
                self.waiting_time >= self.ALERT_THRESHOLD
                and not self.alert_sent
            ):
                self.trigger_buzzer()
                self.alert_sent = True

                print(f"[MQTT] ALERT T{self.roi_id} ({self.waiting_time}s)")

            # =========================
            # FOOD DATANG
            # =========================
            if food_stable and not self.sent:
                self.state = "SERVED"

                self.send_service(self.waiting_time)
                self.sent = True

                print(f"[ROI {self.roi_id}] → SERVED ({self.waiting_time}s)")

            # =========================
            # MEJA DITINGGAL
            # =========================
            if self.no_person_start and (now - self.no_person_start > self.EMPTY_TIMEOUT):
                print(f"[ROI {self.roi_id}] RESET (ditinggal sebelum serve)")
                self.reset()

        # -------- SERVED --------
        elif self.state == "SERVED":

            if self.no_person_start and (now - self.no_person_start > self.EMPTY_TIMEOUT):
                print(f"[ROI {self.roi_id}] → EMPTY")
                self.reset()

        return self.state, self.waiting_time

    # =========================
    # MQTT TRIGGER
    # =========================
    def trigger_buzzer(self):
        self.mqtt.send_buzzer(
            cafe_id=self.cafe_id,
            table_id=self.roi_id,
            waiting_time=self.waiting_time
        )

    # =========================
    # FIREBASE
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

        print(f"[FIREBASE] service masuk ROI {self.roi_id}")

    # =========================
    def reset(self):
        self.state = "EMPTY"
        self.start_time = None
        self.no_person_start = None
        self.waiting_time = 0
        self.sent = False
        self.alert_sent = False  # reset alert
        self.food_detected_frames = 0