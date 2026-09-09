# 🔌 Sơ Đồ Kết Nối Phần Cứng & Hướng Dẫn Hàn Mạch (Hardware Wiring & Soldering Guide)

Tài liệu này hướng dẫn chi tiết cách sơ đồ đấu nối chân (Pinout), mạch nguyên lý động lực và quy trình hàn linh kiện lên **tấm phíp lỗ đôi màu xanh (double-sided perfboard)** cho **Đề tài số 3: Smart Energy Monitoring and Intelligent Load Management**.

---

## 1. Danh mục Linh kiện & Thông số Kỹ thuật

1. **Board điều khiển trung tâm:** ESP32 DevKit V1 (30 chân).
2. **Cảm biến dòng điện:** ACS712 loại 5A (Cảm biến Hall cách ly an toàn, điện áp ra $1.65	ext{V} \pm 185	ext{mV/A}$).
3. **Module chấp hành:** Module Relay 2 kênh 5V (Optocoupler cách ly, kích mức thấp Active Low).
4. **Module nguồn:** Mạch hạ áp Buck DC-DC LM2596 (Đầu vào $4-35	ext{V}$, Đầu ra tinh chỉnh $5.0	ext{V DC}$).
5. **Tải giả lập hạ áp (DC 12V):** 
   - **Tải 1 (Ưu tiên Cao):** Quạt DC 12V (Dòng tiêu thụ $\sim 0.2A - 0.4A$).
   - **Tải 2 (Ưu tiên Thấp):** Đèn LED 12V (Dòng tiêu thụ $\sim 0.1A - 0.3A$).
6. **Nguồn cấp chính:** Adapter DC 12V - 2A hoặc 3A.
7. **Phụ kiện đấu nối:** Cầu đấu Domino Terminal Block 2-pin/3-pin (pitch 5.08mm), Hàng rào cái (Female Header), Dây đơn lõi đồng mạ thiếc.

---

## 2. Bảng Sơ đồ Kết nối Chân (Pinout Table)

### A. Khối Nguồn & Cảm biến
| Linh kiện nguồn/cảm biến | Chân linh kiện | Kết nối với ESP32 / Mạch | Chức năng |
| :--- | :--- | :--- | :--- |
| **Adapter 12V IN** | (+) / (-) | Domino Nguồn 12V IN | Cấp nguồn 12V tổng cho toàn mạch |
| **LM2596 IN+ / IN-** | IN+ / IN- | Domino Nguồn 12V IN | Nhận nguồn 12V vào module hạ áp |
| **LM2596 OUT+ / OUT-** | OUT+ / OUT- | Chân **5V** / **GND** của ESP32 | Hạ áp xuống 5.0V chuẩn nuôi ESP32 & Relay |
| **ACS712 VCC / GND** | VCC / GND | Chân **5V** / **GND** của ESP32 | Nguồn nuôi cảm biến |
| **ACS712 OUT** | OUT | Chân **GPIO 34** (ADC1_CH6) | Tín hiệu Analog đo dòng RMS |

### B. Khối Chấp hành Relay & Tải 12V
| Linh kiện chấp hành | Chân linh kiện | Kết nối với ESP32 / Tải | Chức năng |
| :--- | :--- | :--- | :--- |
| **Relay 2CH VCC / GND** | VCC / GND | Chân **5V** / **GND** của ESP32 | Nguồn nuôi cuộn dây Relay |
| **Relay 2CH IN1** | IN1 | Chân **GPIO 12** | Điều khiển Relay 1 (Quạt 12V - Tải 1) |
| **Relay 2CH IN2** | IN2 | Chân **GPIO 13** | Điều khiển Relay 2 (Đèn LED - Tải 2) |
| **ACS712 IP+ / IP-** | IP+ / IP- | Mạch nối tiếp đường Dương (+12V) | Đo dòng điện đi qua các Tải |

---

## 3. Sơ đồ Nguyên lý Mạch Động lực (12V Power & Relay Circuit)

```text
                               ┌───────────────────────────┐
                               │  Nguồn 12V IN (Adapter)   │
                               └─────────┬─────────┬───────┘
                                         │(+)      │(-)
                                         │         └──────────────────────────┐
                                         ▼                                    │
                               ┌──────────────────┐                           │
                               │ Cảm biến ACS712  │                           │
                               │ (Chân IP+ -> IP-)│                           │
                               └─────────┬────────┘                           │
                                         │(+12V Sau cảm biến)                 │
                                         ├──────────────────────────┐         │
                                         ▼                          ▼         │
                               ┌──────────────────┐       ┌──────────────────┐│
                               │ Relay 1 COM Pin  │       │ Relay 2 COM Pin  ││
                               └─────────┬────────┘       └─────────┬────────┘│
                                         │(NO Pin)                  │(NO Pin) │
                                         ▼                          ▼         │
                               ┌──────────────────┐       ┌──────────────────┐│
                               │  Quạt DC 12V (+) │       │  Đèn LED 12V (+) ││
                               └─────────┬────────┘       └─────────┬────────┘│
                                         │(-)                       │(-)      │
                                         └──────────────────────────┴─────────┴─ (GND 12V Chung)
```

---

## 4. Quy trình Bố trí Linh kiện & Hàn Phíp Lỗ Xanh (Perfboard Layout)

1. **Vị trí Trung tâm (ESP32):** Hàn 2 hàng rào cái (Female Header) cắm rời ESP32. Tuyệt đối không hàn chết ESP32 lên phíp để dễ tháo nạp code và thay thế khi cần.
2. **Vị trí Khối Nguồn (Góc Trái):** Đặt Cầu đấu Domino Nguồn 12V sát mép phíp. Module LM2596 cắm trên 4 chân rào đực.
3. **Vị trí Khối Tải ra (Góc Phải):** Đặt các cổng Domino 2-pin ra cho Quạt và Đèn LED ở sát mép phíp để thao tác vặn tua-vít vặn dây điện dễ dàng.
4. **Quy tắc Đi đường mạch Thiếc:**
   - **Đường Nguồn/Công suất (12V & GND):** Đi đường thiếc phủ dày dọc theo các lỗ phíp (chèn thêm dây đồng đơn lõi) để đảm bảo chịu dòng điện tới 3A không bị nóng mạch.
   - **Đường Tín hiệu (GPIO 34, 12, 13):** Đi dây bus bọc cách điện gọn gàng ở mặt dưới phíp.

---

## 5. Các bước Kiểm tra An toàn trước khi Khóa Nguồn (Pre-Power Test)

> ⚠️ **CẢNH BÁO:** Rút ESP32, ACS712 và Relay ra khỏi hàng rào cái trước khi thực hiện bước này!

1. **Đo Chập Mạch (Short Circuit Check):** Dùng đồng hồ VOM nấc đo thông mạch đo giữa `12V` và `GND`, giữa `5V` và `GND`. Nếu đồng hồ KHÔNG kêu bíp là an toàn.
2. **Hiệu chỉnh Điện áp Nguồn LM2596:** 
   - Cắm Adapter 12V vào Domino Nguồn IN.
   - Dùng VOM đo điện áp tại 2 chân `OUT+` và `OUT-` trên rào cắm LM2596.
   - Dùng tua-vít dẹp tinh chỉnh biến trở xoay trên LM2596 cho đến khi VOM hiển thị chính xác **`5.00V DC`**.
3. **Lắp ráp & Khởi động:**
   - Ngắt nguồn 12V.
   - Cắm ESP32, ACS712 và Relay vào đúng vị trí hàng rào cái.
   - Bật nguồn 12V và kiểm tra đèn nguồn LED đỏ trên ESP32 sáng ổn định.
