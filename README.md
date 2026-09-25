# ⚡ Smart Energy Monitoring & Intelligent Load Management — IoT Project 03

Hệ thống IoT end-to-end: ESP32-S3 đo dòng DC bằng ACS712, tính công suất và điện năng, tự sa thải tải ưu tiên thấp khi vượt ngưỡng đỉnh, gửi dữ liệu qua MQTT về backend FastAPI + cơ sở dữ liệu chuỗi thời gian, hiển thị trên dashboard web thời gian thực kèm trợ lý dữ liệu.

```
 [Adapter 12V]─[cầu chì 2A]─┬─[LM2596 → 5V]──> ESP32-S3, ACS712, relay, OLED, DS3231
                            └─[ACS712 IP+→IP−]─┬─[Relay1]── Quạt 12V  (ưu tiên CAO)
                                               └─[Relay2]── LED 12V   (ưu tiên THẤP)
 ESP32-S3: đo 4 khối/giây · điều khiển cục bộ 2 s/lần · RTC giữ giờ · đệm 600 bản ghi khi mất mạng
      │ MQTT 1883   smartenergy/node9988/{telemetry,status,state,event,cmd,ack}
      ▼
 Broker MQTT ──WSS 8884──> Dashboard (Vercel): realtime, gửi lệnh, đo độ trễ
      │ MQTT 1883
      ▼
 Backend FastAPI (Render 24/7 hoặc laptop) ── SQLite / PostgreSQL(Neon) ── REST /api/*
                                            └── Trợ lý dữ liệu /api/chat
```

## 1. Đáp ứng yêu cầu đề 3

| Yêu cầu trong đề | Cách làm | Ở đâu |
|---|---|---|
| Đo dòng cách ly, điện áp thấp | ACS712-05B, tải DC 12 V, không chạm điện lưới | §3 |
| ≥ 2 tải điều khiển được | Quạt 12 V (ưu tiên cao) + LED 12 V (ưu tiên thấp) | §3 |
| Ghi rõ định mức và bảo vệ | Cầu chì 2 A, diode flyback, relay 10 A/30 VDC, phân áp ADC | `docs/WIRING.md` |
| Telemetry dòng + công suất/điện năng, nêu công thức, đơn vị, tần số | Trung bình 64 mẫu/250 ms, công suất TB 2 s, tích lũy Wh | §4.1 |
| MQTT topic có cấu trúc, QoS, availability | 6 topic, LWT retained | §5 |
| Time-series DB + REST lịch sử/cấu hình | SQLite hoặc PostgreSQL, 5 bảng, 12 endpoint | §6, §7 |
| Dashboard: công suất tức thời, điện năng tích lũy, lịch sử, chi phí, trạng thái tải, cảnh báo | `index.html` | §7 |
| Quản lý tải theo ưu tiên, khôi phục khi an toàn **ổn định** | Máy trạng thái 3 điều kiện + dự báo công suất | §4.2 |
| Phân biệt trạng thái **yêu cầu** và **đã xác nhận** | `cmd_id` → `ack`, UI hiện Yêu cầu / Xác nhận / độ trễ / timeout | §4.3 |
| **Nâng cao**: phát hiện đỉnh, ngân sách điện năng ngày | `peak_today_w`, `ALARM_OVER_LIMIT`, `budget_wh`, `BUDGET_WARN/EXCEEDED` | §4.2 |
| Hành vi an toàn khi mất mạng | Kết nối lại không chặn, SAFE MODE, RTC giữ giờ, đệm và gửi bù | §4.4 |
| Thí nghiệm: sai số, độ trễ, managed/unmanaged, mất kết nối | `/api/stats`, xuất CSV, bảng kịch bản | §10 |

## 2. Cấu trúc repo

```
firmware/esp32_firmware/
  esp32_firmware.ino        Firmware v20 (ESP32-S3 + ACS712 + relay; DS3231/OLED tuỳ chọn)
  secrets.example.h         Copy thành secrets.h, điền WiFi (đã .gitignore)
backend/
  main.py                   FastAPI + MQTT ingest + SQLite/PostgreSQL + trợ lý dữ liệu
  requirements.txt
index.html                  Dashboard, đặt ở GỐC repo để Vercel phục vụ ngay tại "/"
tools/device_simulator.py   Giả lập ESP32 để test khi chưa có phần cứng
docs/
  WIRING.md                 Sơ đồ đấu nối, an toàn, quy trình hàn
  BAO_CAO_IOT_PROJECT03.docx  Báo cáo đồ án 14 đề mục
  PINOUT.xlsx               Bảng chân + danh mục linh kiện
  TRANG_THAI_TRIEN_KHAI.md  Hiện trạng deploy, cách kiểm chứng, việc còn lại
  KHAC_PHUC_SU_CO.md        Web không nhận dữ liệu: cách đọc Serial và tìm nguyên nhân
render.yaml                 Cấu hình deploy backend lên Render
PUSH.md                     Hướng dẫn đẩy code lên GitHub
```

## 3. Phần cứng

| Linh kiện | Chân | ESP32-S3 | Ghi chú |
|---|---|---|---|
| ACS712-05B | OUT | **GPIO 1** qua phân áp 10 kΩ/20 kΩ | 185 mV/A, 2.5 V tại 0 A |
| Relay 2CH (active LOW) | IN1 / IN2 | **GPIO 12 / 13** | Quạt / LED |
| DS3231 (0x68) | SDA / SCL | **GPIO 8 / 9** | Giữ giờ khi mất WiFi |
| SSD1306 (0x3C) | SDA / SCL | **GPIO 8 / 9** | Chung bus I2C với DS3231 |
| Buzzer qua S8050 | — | **GPIO 14** | `-1` nếu không lắp |
| LM2596 | OUT | 5 V / GND | Chỉnh 5.00 V trước khi cắm chip |

Chi tiết đấu nối, mạch động lực, an toàn: `docs/WIRING.md`.

## 4. Firmware v20

### 4.1 Đo lường
- Mỗi 250 ms đọc 64 mẫu `analogReadMilliVolts()` (dùng hiệu chuẩn eFuse của chip), lấy trung bình → `V_out = mV / DIVIDER_RATIO`
- `I [A] = (V_out − V_zero) / 185`; nếu `I < 0.04 A` coi bằng 0 (nhiễu nền). `V_zero` calib lúc khởi động khi 2 tải tắt, hoặc bằng lệnh `calibrate`
- `P [W] = 12 V × I` (điện áp coi là hằng, đo kiểm bằng VOM — ghi trong phần hạn chế)
- `E [Wh] += P × Δt/3600` mỗi khối, lưu Flash mỗi 60 s, reset lúc 0h theo giờ địa phương
- `power_w` gửi lên là **trung bình 2 s** (8 khối); telemetry và vòng điều khiển cùng chu kỳ 2 s

### 4.2 Máy trạng thái quản lý tải
```
LED_ON ──(P > P_peak liên tục ≥ 4 s)──> SHED_PEAK
SHED_PEAK ──(P < P_peak − H liên tục ≥ 15 s  VÀ  LED đã tắt ≥ 20 s
             VÀ  P + P_LED_ước_lượng < P_peak)──> LED_ON
LED_ON ──(E_hôm_nay ≥ ngân sách)──> SHED_BUDGET ──(sang ngày mới)──> LED_ON
LED đã tắt mà vẫn vượt ngưỡng ≥ 10 s → ALARM_OVER_LIMIT + buzzer (quạt ưu tiên cao KHÔNG bị cắt)
```
`P_LED_ước_lượng` được học từ bước nhảy công suất mỗi lần LED đổi trạng thái, nhờ vậy thiết bị không khôi phục khi biết chắc sẽ vượt ngưỡng lại. Ba điều kiện cùng lúc (trễ theo công suất, thời gian tắt tối thiểu, dự báo) là cơ chế chống đóng cắt liên tục.

### 4.3 Lệnh và xác nhận
Web/backend publish `cmd` kèm `cmd_id`. ESP32 áp dụng, publish `ack` chứa `cmd_id` và **trạng thái thực tế** sau khi áp dụng. Dashboard hiển thị riêng "Yêu cầu" và "Xác nhận", đo độ trễ, báo timeout sau 5 s. Bật/tắt tay khi đang AUTO sẽ chuyển thiết bị về MANUAL và sinh sự kiện `MANUAL_OVERRIDE`.

### 4.4 Khi mất mạng
- Kết nối lại WiFi/MQTT không chặn vòng lặp chính → đo và điều khiển vẫn chạy
- Mất broker > 30 s → `safe_mode = true`, tự bật quản lý tải cục bộ dù đang MANUAL
- DS3231 giữ giờ, nên bản ghi vẫn có mốc thời gian đúng; NTP → RTC mỗi 10 phút khi online
- Bộ đệm vòng 600 bản ghi (~20 phút). Có mạng lại thì gửi bù 5 gói/200 ms, gói bù có cờ `"buffered": true` và backend dùng `ts` của thiết bị làm mốc thời gian
- Kết nối lại sinh sự kiện `RECOVERED` kèm thời gian mất kết nối và số gói gửi bù

### 4.5 Nạp firmware
1. Arduino IDE, board **ESP32S3 Dev Module**
2. Library Manager cài **2 thư viện**: `PubSubClient` và `ArduinoJson`
3. Copy `secrets.example.h` → `secrets.h`, điền WiFi
4. Firmware mặc định `USE_RTC 0` / `USE_OLED 0` — chạy được khi **chưa gắn** DS3231 và OLED. Khi nào gắn thì đổi thành `1` và cài thêm `RTClib`, `Adafruit SSD1306`, `Adafruit GFX Library`
5. Có lắp phân áp thì đặt `DIVIDER_RATIO = 0.6667`
6. Upload, mở Serial 115200, **giữ 2 tải tắt** trong 1 giây đầu để calib điểm 0

## 5. Đặc tả MQTT

Gốc topic `smartenergy/<device_id>/`, mặc định `device_id = node9988`.

| Topic | Hướng | QoS / retain | Nội dung |
|---|---|---|---|
| `telemetry` | ESP32 → | 0 | số liệu đo, 2 s/lần |
| `status` | ESP32 → | LWT QoS 1, retained | `online` / `offline` |
| `state` | ESP32 → | retained | cấu hình + trạng thái tải |
| `event` | ESP32 → | 0 | `{type, detail, power_w, limit_w, ts}` |
| `cmd` | web/backend → ESP32 | 1 | `{cmd_id, ts, src, fan?, led?, auto_mode?, peak_limit_w?, hysteresis_w?, budget_wh?, calibrate?, reset_energy?}` |
| `ack` | ESP32 → | 0 | `{cmd_id, cmd_ts, ok, error?, ...state}` |

```json
{"dev":"node9988","ts":1789550319106,"seq":42,"current_a":0.352,"power_w":4.224,
 "energy_today_wh":0.0931,"energy_total_wh":1.204,"peak_today_w":4.301,
 "fan":true,"led":true,"led_shed":"NONE","auto_mode":true,"safe_mode":false,
 "peak_limit_w":3.5,"hysteresis_w":0.5,"budget_wh":0,"led_est_w":1.8,
 "alarm_over":false,"alarm_budget":false,"sensor_mv":2565.1,"zero_mv":2500.0,
 "rssi":-55,"uptime_s":84,"time_src":"ntp","rtc":true,"buffered_count":0}
```

Lý do chọn QoS: telemetry QoS 0 vì gói sau thay gói trước và mất gói được phát hiện qua `seq`; lệnh QoS 1 để không mất lệnh. PubSubClient chỉ publish được QoS 0, nên độ tin cậy của lệnh được bảo đảm ở tầng ứng dụng bằng ACK + timeout 5 s (ghi trong phần hạn chế).

Các loại sự kiện: `SHED`, `RESTORE`, `ALARM_OVER_LIMIT`, `ALARM_CLEAR`, `BUDGET_WARN`, `BUDGET_EXCEEDED`, `MANUAL_OVERRIDE`, `RECOVERED`.

## 6. Cơ sở dữ liệu

Backend tự chọn: có biến `DATABASE_URL` → PostgreSQL (Neon), không có → SQLite. Schema giống nhau, tạo tự động lần chạy đầu.

| Bảng | Cột chính |
|---|---|
| `telemetry` | ts_device, ts_server, seq, current_a, power_w, energy_today_wh, energy_total_wh, peak_today_w, fan, led, led_shed, auto_mode, safe_mode, peak_limit_w, hysteresis_w, budget_wh, alarm_over, alarm_budget, sensor_mv, rssi |
| `events` | ts_device, ts_server, type, detail, power_w, limit_w |
| `availability` | ts_server, status |
| `commands` | cmd_id, source, payload, ts_client, ts_seen_server, ts_ack_server, ack_ok, ack_error, ack_state, latency_ms |
| `settings` | tariff_vnd_per_kwh |

Dữ liệu cũ hơn `RETENTION_DAYS` (mặc định 60) được xóa tự động mỗi 6 giờ.

## 7. REST API (tài liệu tự sinh tại `/docs`)

| Method | Path | Mô tả |
|---|---|---|
| GET | `/api/health` | Trạng thái backend, broker, loại CSDL |
| GET | `/api/status` | Telemetry mới nhất, online/offline, độ tươi dữ liệu, Wh và chi phí hôm nay |
| GET | `/api/history?minutes=&bucket_s=` | Chuỗi thời gian đã gộp (trung bình/đỉnh) |
| GET | `/api/energy/daily?days=` | Wh, đỉnh, chi phí theo ngày |
| GET | `/api/events`, `/api/availability`, `/api/commands` | Nhật ký |
| POST | `/api/command` | `{"fan":true,"wait_ack_s":3}` → trả `requested` và `confirmed` |
| POST | `/api/config` | Ngưỡng, dải trễ, ngân sách, chế độ auto |
| GET/PUT | `/api/settings` | Đơn giá điện |
| GET | `/api/stats?minutes=` | Đỉnh, Wh, thời gian vượt ngưỡng, số lần đóng cắt, tỉ lệ nhận gói, độ trễ |
| POST | `/api/chat` | Trợ lý dữ liệu (§8) |
| GET | `/api/export/{bảng}.csv` | Xuất dữ liệu cho báo cáo |

Khi đặt biến `API_KEY`, mọi POST/PUT phải kèm header `X-API-Key`.

## 8. Trợ lý dữ liệu (chatbot)

Chạy hoàn toàn cục bộ, không gọi API bên ngoài: câu hỏi được chuẩn hoá (bỏ dấu), phân loại ý định bằng biểu thức chính quy, rồi **truy vấn thẳng cơ sở dữ liệu** và ghép câu trả lời từ số liệu thật. Vì không sinh văn bản tự do nên không có nguy cơ bịa số.

Ví dụ hỏi được: *hôm nay dùng bao nhiêu điện*, *tiền điện 7 ngày qua*, *đỉnh công suất hôm nay*, *sa thải tải mấy lần*, *thiết bị offline lúc nào*, *lệnh điều khiển gần đây*, *trạng thái hiện tại*, *so sánh theo ngày*.

Ra lệnh được: *bật quạt*, *tắt đèn*, *bật chế độ tự động*, *đặt ngưỡng 3.5 W*, *đặt ngân sách 20 Wh*. Những câu này **không tự thực thi**: backend trả về trường `action`, dashboard hiện nút "Xác nhận gửi lệnh", người dùng bấm thì mới gọi `/api/command`. Đây là ràng buộc an toàn bắt buộc khi cho ngôn ngữ tự nhiên điều khiển relay.

## 9. Chạy và triển khai

### 9.1 Chạy trên máy (phát triển và demo)
```bash
cd backend
pip install -r requirements.txt
python main.py                       # http://localhost:8000
python ../tools/device_simulator.py  # tuỳ chọn: giả lập ESP32 khi chưa có mạch
```

### 9.2 Hiện trạng triển khai (cập nhật 23/09/2026)

| Thành phần | Địa chỉ | Trạng thái |
|---|---|---|
| Backend + REST API | https://smart-energy-backend-rrvs.onrender.com | Đang chạy, `"db":"postgres"`, `"mqtt_connected":true` |
| Cơ sở dữ liệu | Neon PostgreSQL (pooled, Singapore) | Đã nối, bảng tạo tự động |
| Broker | broker.hivemq.com — TCP 1883 (thiết bị/backend), WSS 8884 (web) | Công khai, không xác thực |
| Dashboard | Vercel, deploy từ `index.html` ở gốc repo | Đang chạy |
| Repo | https://github.com/JackGamerCYT/IOT-PROJECT3- | — |

Kiểm tra nhanh toàn tuyến: `/api/health` → `/api/status` → `/api/history?minutes=10` → `/api/export/telemetry.csv?minutes=60` → SQL Editor trên Neon.

### 9.3 Các bước triển khai lại từ đầu: Neon + Render + Vercel
1. **Neon**: tạo project, copy chuỗi **pooled connection** (`...-pooler...?sslmode=require`)
2. **Render**: New → Blueprint → chọn repo (đã có `render.yaml`) → điền `DATABASE_URL` và `API_KEY` → Apply. Mở `<url>/api/health`, phải thấy `"db":"postgres"` và `"mqtt_connected":true`
3. **Vercel**: Add New → Project → Import repo → Framework Preset = Other, Root Directory để trống, Build/Output Command để trống → Deploy (file `index.html` nằm ngay ở gốc repo nên Vercel phục vụ được luôn)
4. Sửa `const DEFAULT_API = '...'` trong `index.html` thành URL Render rồi push lại; dán `API_KEY` vào ô API Key trên dashboard
5. **Chống ngủ**: gói free của Render tắt service sau ~15 phút không có request, kéo theo mất kết nối MQTT. Tạo job trên cron-job.org gọi `<url>/api/health` mỗi 10 phút

Vì sao cần Render: Vercel chỉ chạy hàm serverless sống vài giây mỗi request, không giữ được kết nối MQTT liên tục để hứng telemetry. Kiến trúc vì vậy tách **worker ingest** (Render) khỏi **giao diện** (Vercel).

Biến môi trường backend: `DATABASE_URL`, `API_KEY`, `MQTT_HOST`, `MQTT_PORT`, `MQTT_USER`, `MQTT_PASS`, `DEVICE_ID`, `TZ_OFFSET_H`, `RETENTION_DAYS`, `PORT`.

## 10. Kịch bản thí nghiệm

| # | Thí nghiệm | Cách làm | Số liệu thu |
|---|---|---|---|
| E1 | Sai số đo | Đồng hồ vạn năng/DC meter nối tiếp, 4 trường hợp: không tải, quạt, LED, cả hai; mỗi trường hợp 30 mẫu | Sai số tuyệt đối và %, độ lệch chuẩn |
| E2 | Độ trễ thiết bị → dashboard | Bật tải, đọc ô "Thiết bị → Dashboard" và `latency_device_to_backend_ms` | Trung bình, p95, max |
| E3 | Độ trễ lệnh → xác nhận | Bấm BẬT/TẮT 30 lần | Trung bình, p95, số lệnh timeout |
| E4 | Unmanaged vs managed | 10 phút AUTO tắt với cả 2 tải bật, ngưỡng 3.5 W → `/api/stats`; lặp lại với AUTO bật | Đỉnh W, Wh, `over_limit_duration_s`, `led_switch_count` |
| E5 | Chống đóng cắt liên tục | Đặt ngưỡng sát tổng công suất, so sánh với cấu hình `hysteresis_w = 0.1`, `MIN_OFF_MS = 0` | Số lần đóng cắt trong 10 phút |
| E6 | Mất mạng | Tắt router 60 s khi đang vượt ngưỡng | Thời điểm OFFLINE (LWT), LED vẫn bị cắt cục bộ, sự kiện `RECOVERED`, số gói gửi bù, khoảng trống dữ liệu |
| E7 | Ngân sách ngày | Đặt `budget_wh` nhỏ (0.5 Wh) | Thời điểm `BUDGET_WARN`/`BUDGET_EXCEEDED`, LED bị cắt |
| E8 | Độ trôi của RTC | So giờ DS3231 với NTP sau 24 giờ | Sai lệch giây/ngày |

## 11. Hạn chế và bảo mật

- Broker HiveMQ công khai không có xác thực: ai biết topic đều đọc và gửi lệnh được. Khắc phục bằng HiveMQ Cloud/EMQX có TLS + tài khoản (firmware và backend đã có sẵn `MQTT_USER`/`MQTT_PASS`) và ACL tách quyền topic `cmd`
- `API_KEY` chỉ bảo vệ REST API, không bảo vệ topic MQTT
- Không đo điện áp thật, giả định 12 V cố định; ACS712 5 A có độ phân giải hạn chế với tải nhỏ. Muốn chính xác hơn dùng INA219/INA226 đo cả V và I
- Một cảm biến đo tổng dòng nên công suất từng tải chỉ là ước lượng từ bước nhảy khi đóng cắt
- ESP32 chỉ publish QoS 0; bộ đệm offline nằm trong RAM nên mất khi reset (có thể nâng cấp sang LittleFS)

## 12. Thành viên

| STT | Họ tên | MSSV | Nhiệm vụ |
|---|---|---|---|
| 1 | Đặng Đình Mạnh | 24119055 | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
