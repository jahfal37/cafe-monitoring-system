# 🍽️ Cafe Monitoring System (AI-Based)

## 📌 Overview

This project is an **AI-based cafe monitoring system** designed to analyze customer activity and waiting time using computer vision.

The system detects:

* 👤 Customers (person)
* 🍔 Food & drinks
* 🪑 Table status

It then processes this information to determine:

* Waiting time
* Table occupancy
* Customer activity status

---

## 🎯 Objectives

* Automate monitoring of cafe customers
* Reduce manual observation
* Improve service efficiency
* Provide real-time alerts using IoT (ESP32 buzzer)

---

## 🧠 Technologies Used

* **Computer Vision:** YOLOv8 (Ultralytics)
* **Programming Language:** Python
* **Hardware:** Raspberry Pi 5, ESP32
* **Communication:** MQTT Protocol
* **Frontend:** HTML, CSS, JavaScript

---

## 🏗️ System Architecture

```
Camera → AI Model (YOLOv8 / ONNX)
        ↓
Detection (person, food, table)
        ↓
Decision Logic (waiting time) -> Dashboard Website 
        ↓
MQTT Broker
        ↓
ESP32 → Buzzer Alert
```

---

## 📂 Project Structure

```
cafe-monitoring-system/
│
├── ai/                # Model training & inference
├── backend/           # Logic & MQTT communication
├── frontend/          # Web interface
├── esp32/             # ESP32 code (buzzer)
```

---

## ⚙️ Installation

### 1. Clone Repository

```bash
git clone https://github.com/your-username/cafe-monitoring-system.git
cd cafe-monitoring-system
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## ▶️ How to Run

### Run AI Detection (YOLOv8)

```bash
python ai/inference/main.py
```

### Run Backend Logic + MQTT

```bash
python backend/app.py
```

---

## 📡 MQTT Communication

* Publisher: Raspberry Pi
* Subscriber: ESP32

---

## 🧪 Detection Logic

| Condition               | Status  |
| ----------------------- | ------- |
| person > 0 AND food = 0 | Waiting |
| person > 0 AND food > 0 | Eating  |
| person = 0              | Empty   |

---

## 🚀 Performance

| Model        | Device         | FPS        |
| ------------ | -------------- | ---------- |
| YOLOv8 (.pt) | Raspberry Pi 5 | ~8 FPS     |

## 📌 Future Improvements

* Multi-object tracking
* Web dashboard Monitoring
* Database integration
* AI model optimization

---

## 👨‍💻 Author

* Name: - Muhammad Nur Diaztara
        - Muhammad Jahfal Pratama Putra
* Project: Final Year Computer Engineering Capstone Project

---
