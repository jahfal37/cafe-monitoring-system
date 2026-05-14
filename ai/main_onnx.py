from ultralytics import YOLO
import cv2
import time
import os
import json
import requests
import frame_store

cv2.setNumThreads(4)

from roi_manager import ROI, ROIManager
from roi_logic import ROIStateMachine

# =========================
# CONFIG
# =========================
def get_ngrok_url():
    try:
        res = requests.get("http://127.0.0.1:4040/api/tunnels")
        data = res.json()

        for tunnel in data["tunnels"]:
            if tunnel["proto"] == "https":
                return tunnel["public_url"]

    except Exception as e:
        print("[NGROK ERROR]", e)

    return None


# =========================
# LOAD CONFIG
# =========================
with open("config.json") as f:
    config = json.load(f)

# =========================
# BASE URL
# =========================
BASE_URL = (
    get_ngrok_url()
    or os.getenv("BASE_URL")
    or config.get("base_url")
)

print("[BASE_URL AKTIF]:", BASE_URL)

# =========================
# CAFE ID
# =========================
cafe_id = os.getenv(
    "CAFE_ID",
    config.get("cafe_id")
)

if not cafe_id:
    raise ValueError(
        "CAFE_ID belum diset di env atau config.json"
    )

# =========================
# DEVICE CODE
# =========================
raw_device = os.getenv(
    "DEVICE_CODE",
    config.get("device_code", "CAM001")
)

raw_device = raw_device.strip()

if not raw_device.startswith(f"{cafe_id}_"):
    device_code = f"{cafe_id}_{raw_device}"
else:
    device_code = raw_device

REGISTER_URL = f"{BASE_URL}/api/devices/register-ai"
UPDATE_URL = f"{BASE_URL}/api/devices/{device_code}"
SERVICE_URL = f"{BASE_URL}/api/ai/services"

# =========================
# DEBUG
# =========================
print("[CONFIG] Cafe ID:", cafe_id)
print("[CONFIG] Raw Device:", raw_device)
print("[CONFIG] Final Device:", device_code)

# =========================
# REGISTER DEVICE
# =========================
def register_device():

    try:

        res = requests.post(
            REGISTER_URL,
            json={
                "cafe_id": cafe_id,
                "device_code": device_code
            }
        )

        print(
            "[REGISTER DEVICE]",
            res.status_code,
            res.text
        )

    except Exception as e:

        print(
            "[ERROR REGISTER DEVICE]:",
            e
        )


# =========================
# UPDATE STATUS
# =========================
last_update_time = time.time()

def update_device_status():

    global last_update_time

    now = time.time()

    # anti spam
    if now - last_update_time < 5:
        return

    last_update_time = now

    try:

        res = requests.put(
            UPDATE_URL,
            json={
                "status": "active",
                "cafe_id": cafe_id
            }
        )

        print(
            "[UPDATE DEVICE]",
            res.status_code,
            res.text
        )

    except Exception as e:

        print(
            "[ERROR UPDATE DEVICE]:",
            e
        )


# =========================
# LOAD MODEL
# =========================
model = YOLO("model/best.onnx")

print("Classes:", model.names)

# =========================
# GET CLASS ID
# =========================
food_class_id = None
person_class_id = None

for k, v in model.names.items():

    if v == "food_drink":
        food_class_id = k

    elif v == "person":
        person_class_id = k

if food_class_id is None or person_class_id is None:

    print("ERROR: Class tidak lengkap!")
    exit()

print(
    f"Food ID: {food_class_id}, "
    f"Person ID: {person_class_id}"
)

# =========================
# CAMERA
# =========================
cap = cv2.VideoCapture(0)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 640)

if not cap.isOpened():

    print("ERROR: Kamera tidak terbuka")
    exit()

# =========================
# ROI
# =========================
roi_manager = ROIManager()

roi_manager.add_roi(
    ROI(
        1,
        [(0,120),(300,120),(300,520),(0,520)],
        offset_y=50
    )
)

roi_manager.add_roi(
    ROI(
        2,
        [(340,120),(640,120),(640,520),(340,520)],
        offset_y=50
    )
)

# =========================
# STATE MACHINE
# =========================
roi_logic = {
    roi.roi_id: ROIStateMachine(
        roi.roi_id,
        cafe_id,
        device_code
    )
    for roi in roi_manager.rois
}

roi_states = {
    roi.roi_id: "EMPTY"
    for roi in roi_manager.rois
}

# =========================
# START
# =========================
register_device()

prev_time = time.time()
last_send = time.time()

# =========================
# MAIN LOOP
# =========================
while True:

    ret, frame = cap.read()

    if not ret:

        print("Failed to grab frame")
        break

    # =========================
    # UPDATE STATUS
    # =========================
    update_device_status()

    # =========================
    # PREPROCESS
    # =========================
    frame = cv2.flip(frame, 1)

    frame = cv2.resize(
        frame,
        (640, 640)
    )

    # =========================
    # YOLO TRACK
    # =========================
    results = model.track(
        frame,
        conf=0.5,
        classes=[
            food_class_id,
            person_class_id
        ],
        imgsz=640,
        persist=True,
        verbose=False,
        tracker="bytetrack.yaml"
    )

    annotated_frame = frame.copy()

    if results and len(results) > 0:

        annotated_frame = results[0].plot()

        boxes = results[0].boxes

    else:

        boxes = None

    # =========================
    # TRACK PERSON PER ROI
    # =========================
    tracked_persons_per_roi = {
        roi.roi_id: []
        for roi in roi_manager.rois
    }

    # =========================
    # COUNT OBJECTS
    # =========================
    if boxes is not None and len(boxes) > 0:

        roi_results = roi_manager.count_objects(
            boxes,
            boxes.cls,
            food_class_id,
            person_class_id
        )

        for box in boxes:

            cls = int(box.cls[0])

            # =========================
            # PERSON TRACK
            # =========================
            if cls == person_class_id:

                # tracker kadang None
                if box.id is None:
                    continue

                # tracker kadang kosong
                if len(box.id) == 0:
                    continue

                track_id = int(box.id[0])

                x1, y1, x2, y2 = map(
                    int,
                    box.xyxy[0]
                )

                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)

                for roi in roi_manager.rois:

                    if roi.contains(cx, cy):

                        tracked_persons_per_roi[
                            roi.roi_id
                        ].append({
                            "id": track_id,
                            "pos": (cx, cy)
                        })

    else:

        roi_results = {
            roi.roi_id: {
                "person": 0,
                "food": 0
            }
            for roi in roi_manager.rois
        }

    # =========================
    # UPDATE ROI STATE
    # =========================
    roi_timers = {}
    roi_stay_timers = {}

    for roi_id, data in roi_results.items():

        food = data["food"]

        tracked_persons = tracked_persons_per_roi.get(
            roi_id,
            []
        )

        state, waiting_time, stay_time = (
            roi_logic[roi_id].update(
                tracked_persons,
                food
            )
        )

        roi_states[roi_id] = state

        roi_timers[roi_id] = waiting_time

        roi_stay_timers[roi_id] = stay_time

        last_log_time = 0
        if time.time() - last_log_time > 5:

            last_log_time = time.time()

            print(
                f"[T{roi_id}] "
                f"P:{len(tracked_persons)} "
                f"F:{food} | "
                f"{state} | "
                f"WAIT:{waiting_time}s"
            )

    # =========================
    # DRAW ROI
    # =========================
    roi_manager.draw_all_with_status(
        annotated_frame,
        roi_results,
        roi_states,
        roi_timers,
        roi_stay_timers
    )

    # =========================
    # DRAW FLOATING TIMER
    # =========================
    for roi in roi_manager.rois:

        labels = roi_logic[
            roi.roi_id
        ].get_floating_labels()

        for item in labels:

            pid = item["id"]

            x, y = item["pos"]

            t = item["time"]

            state = item["state"]

            # =========================
            # FORMAT TIMER
            # =========================
            minutes = t // 60

            seconds = t % 60

            timer_text = (
                f"ID:{pid} "
                f"{minutes:02d}:{seconds:02d}"
            )

            # =========================
            # COLOR
            # =========================
            if state == "WAITING":

                color = (0, 255, 255)

            elif state == "SERVED":

                color = (0, 255, 0)

            else:

                color = (255, 255, 255)

            # =========================
            # POSITION
            # =========================
            text_x = x - 30

            text_y = y + 35

            # =========================
            # TEXT SIZE
            # =========================
            (w, h), _ = cv2.getTextSize(
                timer_text,
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                2
            )

            # =========================
            # BACKGROUND
            # =========================
            cv2.rectangle(
                annotated_frame,
                (text_x - 5, text_y - h - 5),
                (text_x + w + 5, text_y + 5),
                (0, 0, 0),
                -1
            )

            # =========================
            # DRAW TEXT
            # =========================
            cv2.putText(
                annotated_frame,
                timer_text,
                (text_x, text_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2
            )

    # =========================
    # DRAW CUSTOMER COUNT
    # =========================
    y_offset = 40

    for roi in roi_manager.rois:

        total = roi_logic[
            roi.roi_id
        ].total_customers

        cv2.putText(
            annotated_frame,
            f"T{roi.roi_id} C:{total}",
            (10, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 255, 255),
            1,
        )

        y_offset += 25

    # =========================
    # FPS
    # =========================
    now = time.time()

    delta = now - prev_time

    fps = 1 / delta if delta > 0 else 0

    prev_time = now

    cv2.putText(
        annotated_frame,
        f"FPS:{int(fps)}",
        (10, 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (255, 0, 0),
        1,
    )

    # =========================
    # SEND FRAME
    # =========================
    now = time.time()

    if now - last_send > 5:

        last_send = now

        ret, buffer = cv2.imencode(
            ".jpg",
            annotated_frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), 50]
        )

        if ret:

            try:

                requests.post(
                    f"{BASE_URL}/api/frame",
                    files={
                        "frame": (
                            "frame.jpg",
                            buffer.tobytes(),
                            "image/jpeg"
                        )
                    },
                    data={
                        "device_code": device_code
                    },
                    timeout=3
                )

                print("[SEND FRAME OK]")

            except Exception as e:

                print(
                    "[ERROR SEND FRAME]",
                    e
                )
    # =========================
    # DELAY LOOP
    # =========================
    time.sleep(0.05)

    # =========================
    # SHOW
    # =========================
    cv2.imshow(
        "Cafe Monitoring System",
        annotated_frame
    )

    # =========================
    # EXIT
    # =========================
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break
# =========================
# CLEANUP
# =========================
cap.release()

cv2.destroyAllWindows()