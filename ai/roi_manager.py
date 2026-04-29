import cv2
import numpy as np


class ROI:
    def __init__(self, roi_id, points, offset_y=0):
        self.roi_id = roi_id
        self.offset_y = offset_y

        shifted_points = [(x, y + offset_y) for (x, y) in points]
        self.points = np.array(shifted_points, dtype=np.int32)

    def contains(self, x, y):
        return cv2.pointPolygonTest(self.points, (int(x), int(y)), False) >= 0

    def draw(self, frame, color=(0, 255, 0)):
        cv2.polylines(frame, [self.points], True, color, 2)


class ROIManager:
    def __init__(self):
        self.rois = []

    def add_roi(self, roi):
        self.rois.append(roi)

    def draw_all_with_status(self, frame, roi_results, roi_states, roi_timers=None):

        for roi in self.rois:
            # =========================
            # DRAW ROI
            # =========================
            roi.draw(frame)

            # =========================
            # DATA
            # =========================
            data = roi_results.get(roi.roi_id, {"person": 0, "food": 0})
            state = roi_states.get(roi.roi_id, "UNKNOWN")

            person = data["person"]
            food = data["food"]

            max_person = max(1, person)
            max_food = max(1, food)

            # =========================
            # TIMER FORMAT
            # =========================
            time_str = "--:--"

            if roi_timers and roi.roi_id in roi_timers:
                timer = roi_timers[roi.roi_id]
                minutes = timer // 60
                seconds = timer % 60
                time_str = f"{minutes:02d}:{seconds:02d}"

            # hanya tampilkan saat WAITING
            if state == "EMPTY":
                time_str = "--:--"

            # =========================
            # TEXT POSITION
            # =========================
            left_x = int(np.min(roi.points[:, 0]))
            top_y = int(np.min(roi.points[:, 1])) - 10
            top_y = max(top_y, 20)

            text = f"T{roi.roi_id} | P:{person} F:{food} | {state} | {time_str}"

            if state == "SERVED":
                text = f"T{roi.roi_id} | P:{max_person} F:{max_food} | {state} | {time_str}"
            # =========================
            # BACKGROUND
            # =========================
            (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)

            cv2.rectangle(
                frame,
                (left_x, top_y - h - 5),
                (left_x + w, top_y),
                (0, 0, 0),
                -1
            )

            # =========================
            # COLOR BY STATE
            # =========================
            if state == "WAITING":
                color = (0, 255, 255)   # kuning
            elif state == "SERVED":
                color = (0, 255, 0)     # hijau
            elif state == "EMPTY":
                color = (150, 150, 150)
            else:
                color = (255, 255, 255)

            # =========================
            # DRAW TEXT
            # =========================
            cv2.putText(
                frame,
                text,
                (left_x, top_y - 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2
            )

    def count_objects(self, boxes, class_ids, food_id, person_id):

        result = {
            roi.roi_id: {"person": 0, "food": 0}
            for roi in self.rois
        }

        if boxes is None or len(boxes) == 0:
            return result

        for box, cls in zip(boxes.xyxy, class_ids):
            x1, y1, x2, y2 = box

            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)

            for roi in self.rois:
                if roi.contains(cx, cy):
                    if int(cls) == person_id:
                        result[roi.roi_id]["person"] += 1
                    elif int(cls) == food_id:
                        result[roi.roi_id]["food"] += 1

        return result