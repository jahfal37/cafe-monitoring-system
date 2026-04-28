from ultralytics import YOLO
import cv2
import time
from firebase_handler import FirebaseHandler

from roi_manager import ROI, ROIManager

firebase = FirebaseHandler()
cafe_id = "cafe1"

# =========================
# LOAD MODEL
# =========================
model = YOLO("model/best.pt")
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

print(f"Food ID: {food_class_id}, Person ID: {person_class_id}")

# =========================
# INIT CAMERA
# =========================
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# =========================
# INIT ROI
# =========================
roi_manager = ROIManager()

roi_manager.add_roi(ROI(1, [(0, 300), (300, 300), (300, 400), (0, 400)], offset_y=50))
roi_manager.add_roi(ROI(2, [(400, 200), (700, 200), (700, 400), (400, 400)], offset_y=50))

# =========================
# SESSION TRACKING
# =========================

roi_sessions = {
    roi.roi_id: {
        "start_time": None,
        "counted": False
    }
    for roi in roi_manager.rois
} 

# =========================
# INIT STATE
# =========================
roi_states = {roi.roi_id: "Empty" for roi in roi_manager.rois}

# =========================
# FPS
# =========================
prev_time = time.time()

# =========================
# MAIN LOOP
# =========================
while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    frame = cv2.resize(frame, (640, 480))

    # =========================
    # YOLO INFERENCE
    # =========================
    results = model(
        frame,
        conf=0.5,
        classes=[food_class_id, person_class_id],
        imgsz=640,
        verbose=False
    )

    annotated_frame = results[0].plot()
    boxes = results[0].boxes

    # =========================
    # COUNT OBJECT
    # =========================
    if boxes is not None and len(boxes) > 0:
        roi_results = roi_manager.count_objects(
            boxes,
            boxes.cls,
            food_class_id,
            person_class_id
        )
    else:
        roi_results = {roi.roi_id: {"person": 0, "food": 0}
                       for roi in roi_manager.rois}

    # =========================
    # UPDATE STATE
    # =========================
    for roi_id, data in roi_results.items():
        state = roi_states[roi_id]
        session = roi_sessions[roi_id]

        person = data["person"]

        # =========================
        # START TIMER SAAT ACTIVE
        # =========================
        if state == "Active" and session["start_time"] is None:
            session["start_time"] = time.time()

        # =========================
        # HITUNG PELANGGAN (SETELAH 1 MENIT)
        # =========================
        if state == "Active" and not session["counted"]:
            elapsed = time.time() - session["start_time"]

            if elapsed >= 60:
                firebase.update_pelanggan(cafe_id)
                session["counted"] = True
                print(f"[FIREBASE] Pelanggan counted T{roi_id}")

        # =========================
        # SAAT SERVED → KIRIM SERVICE
        # =========================
        if state == "Served" and session["start_time"] is not None:

            waiting_time = int(time.time() - session["start_time"])

            firebase.save_service(
                cafe_id=cafe_id,
                table_number=roi_id,
                waiting_time=waiting_time
            )

            print(f"[FIREBASE] Service saved T{roi_id}")

            # reset session
            roi_sessions[roi_id] = {
                "start_time": None,
                "counted": False
            }

        # =========================
        # RESET SAAT EMPTY
        # =========================
        if state == "Empty":
            roi_sessions[roi_id] = {
                "start_time": None,
                "counted": False
            }

    # =========================
    # DRAW ROI + STATUS (ke annotated_frame!)
    # =========================
    roi_manager.draw_all_with_status(
        annotated_frame,
        roi_results,
        roi_states
    )

    # =========================
    # FPS
    # =========================
    current_time = time.time()
    fps = 1 / (current_time - prev_time)
    prev_time = current_time

    cv2.putText(
        annotated_frame,
        f"FPS: {int(fps)}",
        (20, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 0, 0),
        2
    )

    # =========================
    # SHOW
    # =========================
    cv2.imshow("Cafe Monitoring System", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()