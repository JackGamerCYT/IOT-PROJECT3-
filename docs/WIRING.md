# Sơ đồ kết nối phần cứng — Project 03 (ESP32-S3)

## 1. Danh mục linh kiện

| STT | Linh kiện | Thông số | SL |
|---|---|---|---|
| 1 | ESP32-S3 DevKitC (N16R8) | 16 MB flash, 8 MB PSRAM, ADC 12-bit | 1 |
| 2 | Cảm biến dòng ACS712-05B | Hall cách ly, ±5 A, 185 mV/A, Vout = 2.5 V tại 0 A | 1 |
| 3 | Module relay 2 kênh 5 V | Opto cách ly, kích mức thấp, tiếp điểm 10 A/30 VDC | 1 |
| 4 | Module hạ áp LM2596 | 4–35 V vào, ra chỉnh 5.0 V, 3 A | 1 |
| 5 | DS3231 | RTC I2C, pin CR2032, sai số ±2 ppm | 1 |
| 6 | OLED SSD1306 | 0.96", 128×64, I2C | 1 |
| 7 | Quạt DC 12 V (Tải 1 — ưu tiên cao) | ~0.2–0.4 A | 1 |
| 8 | LED bar 12 V (Tải 2 — ưu tiên thấp) | ~0.1–0.3 A | 1 |
| 9 | Adapter 12 V – 2 A | | 1 |
| 10 | Điện trở 10 kΩ, 20 kΩ | cầu phân áp cho ADC | 1 cặp |
| 11 | Cầu chì 2 A + đế | bảo vệ đường 12 V | 1 |
| 12 | Diode 1N4007 | chống sức điện động ngược của quạt | 1 |
| 13 | Buzzer 5 V active + transistor S8050 + R 1 kΩ | báo động (tuỳ chọn) | 1 |

## 2. Bảng chân (Pinout)

### Khối nguồn
| Từ | Đến | Ghi chú |
|---|---|---|
| Adapter 12 V (+) | Cầu chì 2 A → Domino 12V+ | Toàn bộ dòng tải đi qua cầu chì |
| Domino 12V+ | LM2596 IN+ | |
| Domino 12V− | LM2596 IN−, GND chung | Nối chung mass 12 V và 5 V |
| LM2596 OUT+ | Chân 5V ESP32, VCC relay, VCC ACS712 | Chỉnh đúng 5.00 V **trước khi** cắm ESP32 |

### Khối tín hiệu
| Linh kiện | Chân | ESP32-S3 | Chức năng |
|---|---|---|---|
| ACS712 | OUT | **GPIO 1** (ADC1_CH0) qua phân áp 10 kΩ/20 kΩ | Đo dòng tải DC |
| Relay 2CH | IN1 | **GPIO 12** | Tải 1 — Quạt 12 V |
| Relay 2CH | IN2 | **GPIO 13** | Tải 2 — LED 12 V |
| DS3231 | SDA / SCL | **GPIO 8 / GPIO 9** | RTC, địa chỉ 0x68 |
| SSD1306 | SDA / SCL | **GPIO 8 / GPIO 9** | OLED, địa chỉ 0x3C |
| DS3231, SSD1306 | VCC | **3V3** | Hai module dùng chung bus I2C |
| Buzzer (qua S8050) | Base qua R 1 kΩ | **GPIO 14** | Báo động, đặt `PIN_BUZZER = -1` nếu không lắp |

Cầu phân áp ADC: `OUT ACS712 → R 10 kΩ → nút đo (vào GPIO 1) → R 20 kΩ → GND`. Hệ số 20/(10+20) = 0.667, đưa dải 0–5 V về 0–3.33 V. Khai báo `DIVIDER_RATIO = 0.6667` trong firmware. Nếu không lắp phân áp thì để `1.0`, nhưng chỉ an toàn khi dòng tải luôn dưới ~3 A.

### Mạch động lực
```
+12V (sau cầu chì) ──> ACS712 IP+ ; ACS712 IP- ──┬── COM1 (relay 1) ── NO1 ── Quạt 12V (+)
                                                 └── COM2 (relay 2) ── NO2 ── LED 12V (+)
Quạt 12V (−), LED 12V (−) ──> GND 12V
Diode 1N4007: catot về (+) quạt, anot về (−) quạt
LM2596 lấy nguồn TRƯỚC ACS712 để không tính dòng của mạch điều khiển vào phép đo
```
Relay kích mức thấp: `digitalWrite(pin, LOW)` = đóng tiếp điểm = tải BẬT.

## 3. Lưu ý an toàn và độ chính xác

- **Mức logic relay**: module 5 V điều khiển bằng GPIO 3.3 V có thể không tắt hẳn opto. Tháo jumper JD-VCC rồi cấp JD-VCC = 5 V, VCC = 3.3 V.
- **Không dùng ESP32 classic với GPIO 12**: đó là chân strapping MTDI, mức cao lúc khởi động làm sai điện áp flash. Dự án dùng ESP32-S3 nên GPIO 12/13 an toàn.
- **Không dùng GPIO 35–37** trên bản N16R8 (dành cho PSRAM octal).
- **Calib điểm 0**: lúc khởi động firmware đo trung bình điện áp khi cả 2 tải tắt. Phải giữ tải tắt trong ~1 giây đầu, hoặc bấm "Calib điểm 0" trên dashboard sau này.
- **Kiểm tra trước khi cắm chip**: đo thông mạch 12V–GND và 5V–GND bằng đồng hồ ở nấc còi, không được kêu.
- **Toàn bộ mạch chỉ làm việc với 12 VDC**, không có phần nào chạm điện lưới, đúng yêu cầu "cấm mạch đo điện áp lưới tự chế" của đề.

## 4. Quy trình hàn trên phíp lỗ

1. Hàn hàng rào cái cho ESP32, DS3231, OLED, relay trước; hàn 2 chân chéo để định vị rồi mới hàn hết.
2. Rút hết module ra khỏi rào cái trước khi hàn các đường dây còn lại.
3. Đường 12 V và GND đi dây đồng 0.5–1.0 mm phủ thiếc dày, chịu được 2–3 A.
4. Đo ngắn mạch, cấp 12 V, chỉnh LM2596 ra đúng 5.00 V.
5. Ngắt nguồn, cắm module, cấp lại điện, kiểm tra OLED sáng và Serial in `[CAL] zero = ...`.
