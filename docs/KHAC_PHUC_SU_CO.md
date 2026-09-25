# Web không nhận dữ liệu — cách tìm nguyên nhân

Trước hết cần hiểu: **web chỉ hiển thị, nó không tự tạo ra dữ liệu.** Chuỗi phải thông suốt:

```
ESP32 publish  →  broker.hivemq.com  →  (1) trình duyệt qua WSS 8884
                                      →  (2) backend Render qua TCP 1883 → Neon
```

Nếu ESP32 không publish thì cả web lẫn backend đều trống, badge **Thiết bị** đứng ở `?`.

## Bước 1 — Mở Serial Monitor, đọc 3 dòng đầu

Arduino IDE → Tools → Serial Monitor → **115200 baud** → nhấn nút EN trên ESP32 để khởi động lại.

Firmware v20 in ra ngay khi khởi động:

```
==========================================================
  SMART ENERGY v20  -  IoT PROJECT 03
  Device ID : node9988
  Broker    : broker.hivemq.com:1883
  Telemetry : smartenergy/node9988/telemetry
  ...
```

**Không thấy gì** → chọn sai cổng COM, sai baud, hoặc firmware chưa nạp được. Nạp lại, nhớ chọn board **ESP32S3 Dev Module**.

**Thấy topic là `smartenergy_node9988/telemetry`** (có gạch dưới, không có dấu `/` sau smartenergy) → bạn đang chạy **firmware cũ**. Đây là nguyên nhân phổ biến nhất: topic cũ khác topic web đang nghe nên hai bên không gặp nhau. Nạp lại file `firmware/esp32_firmware/esp32_firmware.ino` mới.

## Bước 2 — Đọc dòng CHẨN ĐOÁN, cứ 5 giây một lần

| Dòng trên Serial | Nghĩa là | Cách sửa |
|---|---|---|
| `WiFi "YOUR_WIFI": KHONG TIM THAY TEN WIFI` | Chưa tạo file `secrets.h` | Copy `secrets.example.h` thành `secrets.h`, điền đúng tên và mật khẩu WiFi, nạp lại |
| `SAI MAT KHAU WIFI` | Sai mật khẩu | Sửa `secrets.h` |
| `KHONG TIM THAY TEN WIFI` dù đã điền đúng | ESP32 chỉ bắt được WiFi **2.4 GHz** | Đổi sang băng tần 2.4 GHz, hoặc phát 4G từ điện thoại |
| `WiFi OK, IP 192.168.x.x ... MQTT chua noi duoc` | Vào mạng được nhưng không ra broker | Xem bước 3 |
| `MQTT loi rc=-2 (KHONG KET NOI DUOC TCP)` | Mạng chặn cổng 1883 | Mạng trường hay chặn. Phát 4G điện thoại thử lại |
| `>>> MQTT DA KET NOI <<<` | Đã lên broker | Sang bước 4 |

## Bước 3 — Mạng trường chặn cổng 1883

Đây là tình huống rất hay gặp ở mạng WiFi trường học. Cách kiểm tra nhanh: phát 4G từ điện thoại, đổi `secrets.h` sang WiFi đó, nạp lại. Nếu chạy được thì chắc chắn do mạng cũ chặn.

Lúc demo trước lớp nên chủ động dùng 4G điện thoại cho ESP32, đừng phụ thuộc WiFi trường.

## Bước 4 — MQTT đã kết nối mà web vẫn trống

Serial sẽ in mỗi 2 giây:

```
[#12 14:32:05] 2501.3mV I=0.000A P=0.00W E=0.000Wh | FAN:OFF LED:OFF(NONE) | MANUAL | MQTT:DA GUI buf=0
```

- `MQTT:DA GUI` → ESP32 đang phát thật. Nếu web vẫn trống thì lỗi nằm ở phía web:
  - Mở trang Vercel, nhìn badge **MQTT** trên đầu trang. Nếu đỏ thì trình duyệt không nối được broker (mạng chặn cổng 8884 hoặc dùng mạng công ty). Thử mở bằng 4G điện thoại.
  - Kéo xuống khung **MQTT LOG** ở cuối trang, nó in ra đúng topic đang nghe. So với dòng `Telemetry :` trên Serial, **hai chuỗi phải giống hệt nhau từng ký tự**.
- `MQTT:CHUA GUI` → mất kết nối broker giữa chừng, quay lại bước 2.

## Bước 5 — Kiểm tra bằng backend

Mở `https://smart-energy-backend-rrvs.onrender.com/api/status`

- `"latest": null` → backend chưa nhận gói nào. ESP32 chưa publish, hoặc publish sai topic.
- Có dữ liệu nhưng web trống → lỗi hiển thị phía trình duyệt, không phải phần cứng.

Backend nghe cùng một broker nhưng qua cổng 1883 từ máy chủ Render, không bị mạng trường ảnh hưởng. Nên nếu backend thấy dữ liệu mà trình duyệt không thấy, gần như chắc chắn mạng chỗ bạn chặn cổng 8884.

## Chưa gắn OLED và DS3231 thì sao?

Không sao cả. Firmware v20 đã đặt sẵn:

```cpp
#define USE_RTC  0
#define USE_OLED 0
```

Với cấu hình này chỉ cần **2 thư viện**: `PubSubClient` và `ArduinoJson`. Không cần RTClib, Adafruit SSD1306, Adafruit GFX — thiếu chúng là lỗi biên dịch chứ không phải lỗi chạy, và cũng là một nguyên nhân khiến "nạp mãi không được".

Mất RTC thì giờ lấy từ NTP khi có mạng; lúc mất mạng thiết bị vẫn cắt tải bình thường, chỉ là dữ liệu đệm không có mốc thời gian nên bỏ qua. Mất OLED thì chỉ mất phần hiển thị tại chỗ.

Khi nào mua module về, đổi hai dòng đó thành `1`, cài đủ 5 thư viện, nối SDA→GPIO 8, SCL→GPIO 9, VCC→3V3, GND→GND rồi nạp lại.

## Phần cứng tối thiểu để web chạy

Chỉ cần: **ESP32-S3 + cáp USB + WiFi**. Không cần ACS712, không cần relay, không cần OLED.

Firmware vẫn publish đều 2 giây một gói, chỉ là dòng điện đọc ra 0 A. Đủ để chứng minh toàn tuyến ESP32 → broker → backend → Neon → web hoạt động. Cắm thêm cảm biến và relay sau.

## Không có mạch thì test bằng giả lập

Trên laptop, tại thư mục dự án:

```powershell
pip install paho-mqtt
python tools/device_simulator.py
```

Giả lập gửi đúng topic và đúng định dạng như ESP32 thật. Nếu **giả lập hiện lên web mà ESP32 thì không**, lỗi chắc chắn nằm ở ESP32 hoặc mạng của nó, không phải ở web hay backend. Đây là phép thử phân định nhanh nhất.
