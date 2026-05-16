from pathlib import Path
import gi
gi.require_version('Gst', '1.0')

from gi.repository import Gst
from gi.repository import Gst, GLib  # Tambahkan , GLib di sini

import hailo

import cv2
import time
import os
import json
import requests
import frame_store
import threading
import sys
import numpy as np

# =========================
# OPENCV OPTIMIZATION
# =========================
cv2.setNumThreads(1)

from roi_manager import ROI, ROIManager
from roi_logic import ROIStateMachine

from hailo_apps.hailo_app_python.core.common.buffer_utils import (
    get_caps_from_pad,
    get_numpy_from_buffer
)

from hailo_apps.hailo_app_python.core.gstreamer.gstreamer_app import (
    app_callback_class
)

from hailo_apps.hailo_app_python.apps.detection.detection_pipeline import (
    GStreamerDetectionApp
)

# =========================
# CONFIG
# =========================
def get_ngrok_url():

    try:

        res = requests.get(
            "http://127.0.0.1:4040/api/tunnels",
            timeout=2
        )

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

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(CURRENT_DIR, "config.json")

with open(config_path) as f:
    config = json.load(f)

HEF_PATH = config.get(
    "hef_path",
    "model/best.hef"
)

LABELS_PATH = config.get(
    "labels_path",
    "model/labels.json"
)

print("[HEF PATH]:", HEF_PATH)
print("[LABELS PATH]:", LABELS_PATH)

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

print("[CONFIG] Cafe ID:", cafe_id)
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
            },
            timeout=3
        )

        print("[REGISTER DEVICE]", res.status_code)

    except Exception as e:

        print("[ERROR REGISTER DEVICE]:", e)


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

        requests.put(
            UPDATE_URL,
            json={
                "status": "active",
                "cafe_id": cafe_id
            },
            timeout=1
        )

    except Exception as e:

        print("[ERROR UPDATE DEVICE]:", e)


# =========================
# ROI
# =========================
roi_manager = ROIManager()

roi_manager.add_roi(
    ROI(
        1,
        [(0,120),(640,120),(640,540),(0,540)],
        offset_y=50
    )
)

roi_manager.add_roi(
    ROI(
        2,
        [(640,120),(1280,120),(1280,540),(640,540)],
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
# CALLBACK CLASS
# =========================
class user_app_callback_class(app_callback_class):

    def __init__(self):
        super().__init__()


# =========================
# START
# =========================
register_device()

prev_time = time.time()

# =========================
# FRAME UPLOADER
# =========================
latest_upload = 0

# =========================
# INTERNAL TRACKER
# =========================
next_track_id = 1
active_tracks = {}

def upload_frame(frame):

    global latest_upload

    now = time.time()

    # upload max 5 detik
    if now - latest_upload < 5.0:
        return

    latest_upload = now

    try:

        _, jpg = cv2.imencode(
            ".jpg",
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), 70]
        )

        requests.post(
            f"{BASE_URL}/api/frame",
            files={
                "frame": (
                    "frame.jpg",
                    jpg.tobytes(),
                    "image/jpeg"
                )
            },
            data={
                "device_code": device_code
            },
            timeout=0.5
        )

    except Exception as e:
        print("[UPLOAD ERROR]", e)

# =========================
# SAFE UI RENDERER
# =========================
def show_frame_safe(frame):
    cv2.imshow("Cafe Monitoring System", frame)
    cv2.waitKey(1)
    return False  # Wajib me-return False agar GLib membuang tugas ini setelah selesai digambar

# =========================
# CALLBACK
# =========================
def app_callback(pad, info, user_data):
    
    global prev_time

    buffer = info.get_buffer()

    if buffer is None:
        return Gst.PadProbeReturn.OK

    format, width, height = get_caps_from_pad(pad)

    frame = get_numpy_from_buffer(
        buffer,
        format,
        width,
        height
    )
    frame = cv2.cvtColor(
        frame,
        cv2.COLOR_RGB2BGR
    )

    annotated_frame = frame.copy()

    # =========================
    # UPDATE DEVICE STATUS
    # =========================
    update_device_status()

    # =========================
    # GET HAILO ROI
    # =========================
    roi = hailo.get_roi_from_buffer(buffer)

    detections = roi.get_objects_typed(
        hailo.HAILO_DETECTION
    )

    tracked_persons_per_roi = {
        roi.roi_id: []
        for roi in roi_manager.rois
    }

    roi_results = {
        roi.roi_id: {
            "person": 0,
            "food": 0
        }
        for roi in roi_manager.rois
    }

    # =========================
    # DETECTION LOOP
    # =========================
    for detection in detections:

        class_id = detection.get_class_id()
        confidence = detection.get_confidence()

        bbox = detection.get_bbox()
        x1 = int(bbox.xmin() * width)
        y1 = int(bbox.ymin() * height)
        x2 = int(bbox.xmax() * width)
        y2 = int(bbox.ymax() * height)

        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)

        # ====================================================
        # GAMBAR KOTAK & LABEL (BERSIH, SESUAI ID BARU)
        # ====================================================
        color = (255, 255, 255)  # Default putih jika ada objek lain
        label_text = "unknown"

        if class_id == 2:
            color = (0, 255, 0)      # Hijau untuk Person
            label_text = "person"
        elif class_id == 1:
            color = (0, 0, 255)      # Merah untuk Food
            label_text = "food_drink"

        # Hanya gambar jika itu person (2) atau food (1)
        if class_id in [1, 2]:
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(annotated_frame, f"{label_text} {confidence:.2f}", (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # =========================
        # INTERNAL TRACKER
        # =========================
        global next_track_id, active_tracks
        track_id = None
        now_track = time.time()
        
        # Bersihkan ID lama (> 2 detik)
        active_tracks = {tid: data for tid, data in active_tracks.items() if now_track - data["last_seen"] < 2.0}
        
        # Cari ID terdekat (Euclidean)
        min_dist = 999999
        matched_id = None
        
        for tid, data in active_tracks.items():
            px, py = data["pos"]
            dist = ((cx - px) ** 2 + (cy - py) ** 2) ** 0.5
            if dist < 250 and dist < min_dist:
                min_dist = dist
                matched_id = tid
                
        if matched_id is not None:
            track_id = matched_id
            active_tracks[track_id] = {"pos": (cx, cy), "last_seen": now_track}
        else:
            track_id = next_track_id
            next_track_id += 1
            active_tracks[track_id] = {"pos": (cx, cy), "last_seen": now_track}
            
        # =========================
        # ROI LOGIC 
        # =========================
        import numpy as np

        # 1. JIKA OBJEK ADALAH PERSON (CLASS ID 2)
        if class_id == 2:
            for roi_data in roi_manager.rois:
                poly = np.array(roi_data.points, np.int32)
                is_inside = cv2.pointPolygonTest(poly, (float(cx), float(cy)), False) >= 0
                
                if is_inside:
                    roi_results[roi_data.roi_id]["person"] += 1
                    tracked_persons_per_roi[roi_data.roi_id].append({
                        "id": track_id,
                        "pos": (cx, cy)
                    })

        # 2. JIKA OBJEK ADALAH FOOD_DRINK (CLASS ID 1)
        elif class_id == 1: 
            for roi_data in roi_manager.rois:
                poly = np.array(roi_data.points, np.int32)
                if cv2.pointPolygonTest(poly, (float(cx), float(cy)), False) >= 0:
                    roi_results[roi_data.roi_id]["food"] += 1
                
                
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
    # DRAW FLOATING TIMERS
    # =========================
    for roi in roi_manager.rois:
        for item in roi_logic[roi.roi_id].get_floating_labels():
            timer_text = f"ID:{item['id']} {item['time']//60:02d}:{item['time']%60:02d}"
            
            # Kuning untuk WAITING, Hijau untuk SERVED
            text_color = (0, 255, 255) if item["state"] == "WAITING" else (0, 255, 0)
            
            tx, ty = item["pos"][0] - 30, item["pos"][1] + 35
            
            # Gambar background hitam agar teks jelas
            (w_txt, h_txt), _ = cv2.getTextSize(timer_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(annotated_frame, (tx - 5, ty - h_txt - 5), (tx + w_txt + 5, ty + 5), (0, 0, 0), -1)
            
            # Gambar teksnya
            cv2.putText(annotated_frame, timer_text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 2)

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
        0.6,
        (255,0,0),
        2
    )

    # =========================
    # STORE FRAME FOR WEB
    # =========================
    frame_store.latest_frame = annotated_frame.copy()

    threading.Thread(
        target=upload_frame,
        args=(annotated_frame.copy(),),
        daemon=True
    ).start()

    # =========================
    # NO OPENCV WINDOW HERE
    # =========================
    # IMPORTANT:
    # Titipkan gambar ke Main Thread agar tidak crash
    GLib.idle_add(show_frame_safe, annotated_frame.copy())

    return Gst.PadProbeReturn.OK


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    
    register_device()
    
    # ---------------------------------------------------------
    # MEMBUAT ABSOLUTE PATH SECARA DINAMIS
    # ---------------------------------------------------------
    # 1. Dapatkan lokasi direktori tempat main_hailo.py ini berada
    # (Yaitu di: /home/diaz/hailo-rpi5-examples/basic_pipelines/cafe_monitoring)
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 2. Naik dua level ke folder root (hailo-rpi5-examples)
    root_repo_dir = os.path.abspath(os.path.join(current_script_dir, "../../"))
    
    # 3. Gabungkan dengan folder resources
    absolute_hef_path = os.path.join(root_repo_dir, "resources", "best.hef")
    absolute_labels_path = os.path.join(root_repo_dir, "resources", "labels.json")

    # Pastikan file benar-benar ada sebelum GStreamer berjalan
    if not os.path.exists(absolute_hef_path):
        print(f"\n[ERROR FATAL] Model tidak ditemukan di:\n{absolute_hef_path}")
        print("Pastikan kamu sudah memindahkan file best.hef ke folder resources!")
        sys.exit(1)
        
    if not os.path.exists(absolute_labels_path):
        print(f"\n[ERROR FATAL] Labels tidak ditemukan di:\n{absolute_labels_path}")
        print("Pastikan kamu sudah memindahkan file labels.json ke folder resources!")
        sys.exit(1)

    print(f"\n[SISTEM] Memuat HEF dari: {absolute_hef_path}")
    print(f"[SISTEM] Memuat Labels dari: {absolute_labels_path}\n")

    # ---------------------------------------------------------
    # ARGUMEN SISTEM
    # ---------------------------------------------------------
    sys.argv = [
        "main_hailo.py",
        "--input", "/dev/video0",
        "--hef-path", absolute_hef_path,           # Menggunakan absolute path
        "--labels-json", absolute_labels_path, # Menggunakan absolute path
    ]
    
    # Menyesuaikan dengan nama class & fungsi di kodemu yang baru
    user_data = user_app_callback_class()
    app = GStreamerDetectionApp(app_callback=app_callback, user_data=user_data)
    app.run()
