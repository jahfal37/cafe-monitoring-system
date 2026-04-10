from ultralytics import YOLO
import cv2
import time

# Load model
model = YOLO("best.pt")
print("Classes:", model.names)

# Ambil class ID untuk food_drink secara dinamis
target_class_id = None
for k, v in model.names.items():
    if v == "food_drink":
        target_class_id = k

if target_class_id is None:
    print("ERROR: 'food_drink' class not found in model!")
    exit()

print(f"Food/Drink class ID: {target_class_id}")

# Inisialisasi webcam
cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

print("Resolution:", cap.get(cv2.CAP_PROP_FRAME_WIDTH),
      cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

# FPS tracking
prev_time = time.time()

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    results = model(frame, conf=0.5, classes=[target_class_id])

    annotated_frame = results[0].plot()

    boxes = results[0].boxes
    count = len(boxes) if boxes is not None else 0

    # Display count
    cv2.putText(
        annotated_frame,
        f"Food/Drink Count: {count}",
        (20, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2
    )

    # FPS calculation
    current_time = time.time()
    fps = 1 / (current_time - prev_time)
    prev_time = current_time

    cv2.putText(
        annotated_frame,
        f"FPS: {int(fps)}",
        (20, 90),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 0, 0),
        2
    )

    cv2.imshow("Food & Drink Detection", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()