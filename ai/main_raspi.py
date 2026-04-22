from ultralytics import YOLO
import cv2
import time

# Load model (gunakan versi ringan)
model = YOLO("best.pt")

print("Classes:", model.names)

# Ambil class ID
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

# Kamera (Linux / Raspberry Pi)
cap = cv2.VideoCapture(0)  # HAPUS CAP_DSHOW

# Turunkan resolusi untuk performa
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print("Resolution:",
      cap.get(cv2.CAP_PROP_FRAME_WIDTH),
      cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

prev_time = time.time()

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    # Resize tambahan (opsional, bantu FPS)
    frame = cv2.resize(frame, (640, 480))

    # Inference (gunakan stream=True untuk efisiensi)
    results = model(
        frame,
        conf=0.5,
        classes=[food_class_id, person_class_id],
        imgsz=640,
        verbose=False
    )

    annotated_frame = results[0].plot()

    boxes = results[0].boxes

    food_count = 0
    person_count = 0

    if boxes is not None:
        for cls in boxes.cls:
            if int(cls) == food_class_id:
                food_count += 1
            elif int(cls) == person_class_id:
                person_count += 1

    # Overlay text
    cv2.putText(annotated_frame, f"Food: {food_count}",
                (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
                0.8, (0, 255, 0), 2)

    cv2.putText(annotated_frame, f"Person: {person_count}",
                (20, 80), cv2.FONT_HERSHEY_SIMPLEX,
                0.8, (255, 255, 0), 2)

    # FPS
    current_time = time.time()
    fps = 1 / (current_time - prev_time)
    prev_time = current_time

    cv2.putText(annotated_frame, f"FPS: {int(fps)}",
                (20, 120), cv2.FONT_HERSHEY_SIMPLEX,
                0.8, (255, 0, 0), 2)

    cv2.imshow("Detection", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()