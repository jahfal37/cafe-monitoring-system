from ultralytics import YOLO
import cv2
import time
import os

from roi_manager import ROI, ROIManager
from roi_logic import ROIStateMachine

# =========================
# CONFIG
# =========================
cafe_id = "cafe1"

# =========================
# LOAD MODEL
# =========================
model_path = os.path.join("model", "best.pt")
model = YOLO(model_path)

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
# INIT CAMERA (WINDOWS)
# =========================
cap = cv2.VideoCapture(0)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

if not cap.isOpened():
    print("ERROR: Kamera tidak terbuka")
    exit()

# =========================
# INIT ROI
# =========================
roi_manager = ROIManager()

roi_manager.add_roi(ROI(1, [(0, 100), (300, 100), (300, 400), (0, 400)], offset_y=50))
roi_manager.add_roi(ROI(2, [(350, 100), (650, 100), (650, 400), (350, 400)], offset_y=50))

# =========================
# INIT STATE MACHINE
# =========================
roi_logic = {
    roi.roi_id: ROIStateMachine(roi.roi_id, cafe_id)
    for roi in roi_manager.rois
}

roi_states = {roi.roi_id: "EMPTY" for roi in roi_manager.rois}

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
    frame = cv2.flip(frame, 1)  # Mirror effect

    frame = cv2.resize(frame, (640, 480))

    # =========================
    # YOLO
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
        roi_results = {
            roi.roi_id: {"person": 0, "food": 0}
            for roi in roi_manager.rois
        }

    # =========================
    # UPDATE STATE MACHINE
    # =========================
    roi_timers = {}

    for roi_id, data in roi_results.items():

        person = data["person"]
        food = data["food"]

        state, waiting_time = roi_logic[roi_id].update(person, food)

        roi_states[roi_id] = state
        roi_timers[roi_id] = waiting_time

        # =========================
        # DEBUG LOG (PENTING)
        # =========================
        print(f"[T{roi_id}] P:{person} F:{food} | {state} | {waiting_time}s")

    # =========================
    # DRAW ROI
    # =========================
    roi_manager.draw_all_with_status(
        annotated_frame,
        roi_results,
        roi_states,
        roi_timers
    )

    # =========================
    # FPS
    # =========================
    now = time.time()
    fps = 1 / (now - prev_time)
    prev_time = now

    cv2.putText(
        annotated_frame,
        f"FPS: {int(fps)}",
        (20, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 0, 0),
        2
    )

    cv2.imshow("Cafe Monitoring System", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()