# ⚡ Smart Energy Monitoring and Intelligent Load Management (IoT Project 03)

![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi)
![ESP32](https://img.shields.io/badge/Hardware-ESP32-red?style=for-the-badge&logo=espressif)
![MQTT](https://img.shields.io/badge/Protocol-MQTT-purple?style=for-the-badge&logo=eclipse-mosquitto)
![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?style=for-the-badge&logo=sqlite)
![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)

> **Hệ thống Giám sát Điện năng & Quản lý Tải thông minh End-to-End** thuộc Đề tài số 3 bộ môn Internet of Things (Đại học Bách Khoa TP.HCM). Hệ thống đo đạc dòng điện/công suất thực tế, hiển thị đồ thị thời gian thực, tự động sa thải tải phụ khi vượt ngưỡng công suất đỉnh ($P > P_{peak}$) bằng thuật toán trễ (Hysteresis rule) và tích hợp Trợ lý AI tư vấn trực tiếp trên Web.

---

## 📌 Bảng Mục Lục
1. [Tính năng chính](#-tính-năng-chính-key-features)
2. [Kiến trúc Hệ thống](#-kiến-trúc-hệ-thống-system-architecture)
3. [Cấu trúc Thư mục Repository](#-cấu-trúc-thư-mục-repository)
4. [Sơ đồ Kết nối Phần cứng](#-sơ-đồ-kết-nối-phần-cứng-hardware-pinout)
5. [Hướng dẫn Cài đặt & Khởi chạy](#-hướng-dẫn-cài-đặt--khởi-chạy)
6. [Danh mục REST API](#-danh-mục-rest-api)
7. [Kịch bản Kiểm thử & Báo cáo](#-kịch-bản-kiểm-thử--báo-cáo)

---

## 📖 Tính năng chính (Key Features)

- **Đo đạc Điện năng An toàn:** Sử dụng cảm biến dòng cách ly ACS712 (5A) đo đạc tải DC 12V (Quạt 12V & LED 12V), lấy mẫu 1000 điểm tính dòng RMS và tích lũy điện năng Wh.
- **Truyền thông MQTT Thời gian thực:** Đăng ký QoS, Last Will and Testament (LWT) trên topic `energy/device/availability` để tự động phát hiện trạng thái thiết bị Online/Offline.
- **Backend FastAPI & SQLite Time-Series DB:** Lưu trữ lịch sử đo đạc (`telemetry`), nhật ký tác động điều khiển (`control_log`) và cấu hình ngưỡng công suất (`device_config`).
- **Web Dashboard & Trợ lý AI Chatbot:** Đồ thị sóng công suất thời gian thực (Chart.js), giao diện điều khiển quạt/đèn trực quan và Khung Chatbox AI thông minh tự động tra cứu dữ liệu SQLite để trả lời số lần bật/tắt thiết bị, tính tiền điện và nhận lệnh điều khiển trực tiếp bằng giọng nói/văn bản.
- **Tự động Sa thải Tải (Intelligent Load Shedding):** Thuật toán trễ (Hysteresis) tự động cắt Tải 2 (Đèn LED - Ưu tiên thấp) khi công suất vượt ngưỡng đỉnh ($P > P_{peak}$) và khôi phục khi công suất trở lại mức an toàn ($P < P_{peak} - Hysteresis$).
- **Trí tuệ Cục bộ (Offline Resilience):** ESP32 tự duy trì logic sa thải tải cục bộ ngay cả khi mất mạng WiFi/MQTT Broker, đảm bảo an toàn đường dây 24/7.

---

## 🛠️ Kiến trúc Hệ thống (System Architecture)

```text
[ Adapter 12V ] ──> [ LM2596 (5V) ] ──> Cấp nguồn cho ESP32 & Cảm biến

[ Cảm biến ACS712 ] ──(ADC GPIO34)──> [ ESP32 MCU Node ]
                                            │
[ Module Relay 2CH ] <──(GPIO 12/13)────────┤ (Thuật toán Hysteresis Cục bộ)
  ├─ Tải 1: Quạt 12V (Ưu tiên Cao)          │
  └─ Tải 2: LED 12V (Ưu tiên Thấp)          │
                                       (Wi-Fi / MQTT)
                                            │
                                            ▼
                                  [ Mosquitto MQTT Broker ]
                                            │
                                      (paho-mqtt / REST)
                                            │
                                            ▼
                                   [ FastAPI Backend ]
                                     ├── SQLite DB (energy_data.db)
                                     ├── Web Dashboard (HTML5 / Tailwind CSS / Chart.js)
                                     └── Local AI Expert Chatbot
```

---

## 📁 Cấu trúc Thư mục Repository

```text
smart-energy-iot/
├── backend/
│   ├── main.py              # FastAPI Server, Web Dashboard & Chatbox AI Engine
│   └── requirements.txt     # Danh sách thư viện Python phụ thuộc
├── firmware/
│   └── esp32_firmware/
│       └── esp32_firmware.ino  # Firmware C++ hoàn chỉnh nạp cho ESP32
├── docs/
│   ├── WIRING.md            # Sơ đồ và hướng dẫn hàn mạch chi tiết
│   ├── bao-cao-iot.docx     # Báo cáo Đồ án Word chuẩn 14 đề mục kỹ thuật
│   ├── iot_project_tracker.xlsx     # Bảng tổng hợp linh kiện & shopping list
│   └── iot_step_by_step_guide.xlsx  # Kế hoạch tiến độ thực hiện theo tuần
├── .gitignore               # Cấu hình bỏ qua file tạm / Database SQLite
└── README.md                # Tài liệu hướng dẫn dự án (File này)
```

---

## 🔌 Sơ đồ Kết nối Phần cứng (Hardware Pinout)

| Linh kiện | Chân Linh kiện | Chân kết nối ESP32 | Chức năng kỹ thuật |
| :--- | :--- | :--- | :--- |
| **Cảm biến ACS712 (5A)** | VCC / GND / OUT | 5V / GND / **GPIO 34** (ADC1) | Đọc tín hiệu điện áp dòng điện RMS |
| **Module Relay 2CH (Active Low)** | VCC / GND / IN1 / IN2 | 5V / GND / **GPIO 12** / **GPIO 13** | Điều khiển Quạt 12V (Tải 1) & Đèn LED (Tải 2) |
| **Module Hạ Áp LM2596** | IN+ / IN- / OUT+ / OUT- | 12V IN / GND / 5V OUT / GND | Hạ áp từ Adapter 12V xuống 5V nuôi ESP32 |

---

## 🚀 Hướng dẫn Cài đặt & Khởi chạy

### 1. Khởi chạy Backend Python
```bash
# 1. Di chuyển vào thư mục backend
cd backend

# 2. Cài đặt các thư viện Python phụ thuộc
pip install -r requirements.txt

# 3. Khởi chạy Server Backend
python main.py
```
> **Truy cập Dashboard:** Mở trình duyệt gõ `http://localhost:8000` (trên máy tính) hoặc `http://<IP_LAPTOP>:8000` (trên điện thoại).

### 2. Nạp Firmware cho ESP32
1. Mở file `firmware/esp32_firmware/esp32_firmware.ino` bằng **Arduino IDE**.
2. Cài đặt các thư viện qua Library Manager: `PubSubClient` và `ArduinoJson`.
3. Sửa thông số `ssid`, `password` và `mqtt_server` (IP thực tế của Laptop).
4. Chọn Board **ESP32 Dev Module** và cổng COM tương ứng, sau đó nhấn **Upload**.

---

## 📑 Danh mục REST API

- `GET /` : Trả về Giao diện Web Dashboard tích hợp Khung Chatbox AI.
- `GET /api/energy/current` : Lấy thông số điện năng tức thời (V, A, W, Wh), trạng thái tải và chế độ Auto/Manual.
- `GET /api/energy/history` : Lấy 30 bản ghi lịch sử công suất gần nhất để vẽ biểu đồ sóng.
- `POST /api/config` : Cập nhật ngưỡng công suất đỉnh (`peak_limit`) và chế độ Auto/Manual.
- `POST /api/control` : Gửi lệnh bật/tắt tải thủ công (`{"load_id": 1, "state": "ON"}`).
- `POST /api/chat` : Khung chat AI tự động truy vấn SQLite trả lời số liệu lịch sử & nhận lệnh điều khiển.

---
New Features: Header( update 0.2)

## 👥 Thành viên Thực hiện

| STT | Họ và Tên | Mã số Sinh viên | Vai trò & Nhiệm vụ Phân công |
| :---: | :--- | :--- | :--- |
| 1 | Nguyễn Văn A | 2110001 | Trưởng nhóm, Thiết kế Mạch hàn Phíp xanh & Firmware ESP32 |
| 2 | Trần Thị B | 2110002 | Lập trình Backend FastAPI, Database SQLite & MQTT Broker |
| 3 | Lê Văn C | 2110003 | Thiết kế Web Dashboard UI/UX & Tích hợp Chatbox AI |
| 4 | Phạm Văn D | 2110004 | Thực nghiệm đo đạc sai số, Đánh giá độ trễ & Viết Báo cáo |

---

## 📄 Giấy phép (License)
Dự án được phát hành dưới Giấy phép [MIT License](LICENSE).
