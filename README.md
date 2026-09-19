# ⚡ Smart Energy Monitoring & Intelligent Load Management — Project 03

Hệ thống IoT end-to-end: ESP32-S3 đo dòng DC bằng ACS712, tính công suất/điện năng, sa thải tải ưu tiên thấp khi vượt ngưỡng đỉnh, gửi dữ liệu qua MQTT → backend FastAPI + SQLite → dashboard web thời gian thực.

```
 [12V adapter]──┬─[LM2596 5V]──> ESP32-S3, ACS712, relay
                └─[ACS712 IP+→IP-]──┬─[Relay1 COM→NO]── Quạt 12V (ưu tiên CAO)
                                    └─[Relay2 COM→NO]── LED 12V  (ưu tiên THẤP)
 ESP32-S3 (đo 4 khối/s, điều khiển cục bộ 2 s/lần)
      │ MQTT 1883  smartenergy/node9988/{telemetry,status,state,event,cmd,ack}
      ▼
 broker.hivemq.com ──WSS 8884──> Dashboard (trình duyệt): realtime + gửi lệnh + đo độ trễ
      │ MQTT 1883
      ▼
 Backend FastAPI (laptop) ── SQLite energy_data.db ── REST /api/*  ──> Dashboard: lịch sử, ngày, thống kê
```

## 1. Đáp ứng yêu cầu đề 3

| Yêu cầu trong đề | Cách làm |
|---|---|
| Đo dòng cách ly, điện áp thấp | ACS712-05B (Hall, cách ly), tải DC 12V, không đụng điện lưới |
| ≥ 2 tải điều khiển được | Quạt 12V (ưu tiên cao) + LED 12V (ưu tiên thấp) qua relay 2 kênh |
| Ghi rõ thông số điện và bảo vệ | Mục 3: cầu chì, diode, định mức relay, phân áp ADC |
| Telemetry dòng + công suất/điện năng, nêu rõ cách tính, đơn vị, tần số | Mục 4.1 |
| MQTT có topic cấu trúc, QoS, availability | Mục 5 (LWT `status` retained) |
| Time-series DB + REST lịch sử/cấu hình | SQLite (mục 6) + FastAPI (mục 7, Swagger tại `/docs`) |
| Dashboard: công suất tức thời, điện năng tích lũy, lịch sử, chi phí, trạng thái tải, cảnh báo | `dashboard/index.html` |
| Quản lý tải theo ưu tiên, khôi phục khi an toàn **ổn định** | Máy trạng thái (mục 4.2): T_OVER, T_SAFE, MIN_OFF, dự báo công suất |
| Phân biệt trạng thái **yêu cầu** và **đã xác nhận** | `cmd_id` → `ack`; UI hiện "Yêu cầu" / "Xác nhận" / độ trễ / timeout |
| **Nâng cao**: peak-demand detection, ngân sách ngày | Phát hiện đỉnh (peak_today, ALARM_OVER_LIMIT) + ngân sách Wh/ngày (BUDGET_WARN/EXCEEDED, cắt LED) |
| Xử lý mất mạng an toàn | Kết nối lại không chặn; mất broker > 30 s → SAFE MODE, tự quản lý tải |
| Thí nghiệm: sai số, độ trễ, managed/unmanaged, mất kết nối | Mục 9 + `/api/stats` + xuất CSV |

## 2. Cấu trúc repo

```
firmware/esp32_firmware/esp32_firmware.ino   Firmware v17 (ESP32-S3)
firmware/esp32_firmware/secrets.example.h    Copy thành secrets.h, điền WiFi (không commit)
backend/main.py                              FastAPI + MQTT ingest + SQLite
backend/requirements.txt
dashboard/index.html                         Dashboard (được backend phục vụ tại "/", hoặc deploy Vercel)
tools/device_simulator.py                    Giả lập ESP32 để test khi chưa có phần cứng
docs/                                        WIRING.md, báo cáo
```

## 3. Phần cứng (ESP32-S3 N16R8)

| Linh kiện | Chân | Nối tới | Ghi chú |
|---|---|---|---|
| ACS712-05B | VCC / GND | 5V / GND | Ra 2.5 V tại 0 A, 185 mV/A |
| ACS712 | OUT | **GPIO 1** (ADC1_CH0) qua **phân áp 10 kΩ / 20 kΩ** | 5 A → 3.43 V, vượt dải ADC. Có phân áp thì đặt `DIVIDER_RATIO = 0.6667` |
| Relay 2CH (active LOW) | IN1 / IN2 | GPIO 12 / GPIO 13 | Nên tháo jumper JD-VCC: JD-VCC = 5V, VCC = 3.3V để 3.3V tắt hẳn opto |
| Buzzer 5V (tuỳ chọn) | + | GPIO 14 qua NPN (S8050) | `PIN_BUZZER = -1` nếu không lắp |
| LM2596 | OUT | 5V / GND | Chỉnh đúng 5.0 V trước khi cắm ESP32 |

Bảo vệ: cầu chì 1–2 A trên đường +12V trước ACS712; diode 1N4007 ngược song song quạt (tải cảm); relay SRD-05VDC định mức 10 A/30 VDC ≫ tải < 1 A; chung GND cho 12V và 5V.

> Bản cũ ghi "ESP32 DevKit + GPIO34". Trên ESP32 classic, GPIO12 là chân strapping (có thể làm lỗi boot), nên đã chuyển hẳn sang ESP32-S3. Nhớ sửa file `so-do-noi-chan-iot.xlsx` và `docs/WIRING.md` cho khớp.

## 4. Firmware

### 4.1 Đo lường (công thức, đơn vị, tần số)
- Mỗi 250 ms đọc 64 mẫu `analogReadMilliVolts()` (đã hiệu chuẩn eFuse), lấy trung bình → `V_out = mV / DIVIDER_RATIO`
- `I [A] = (V_out − V_zero) / 185 mV/A`; `I < 0.04 A` → 0 (nhiễu nền). `V_zero` được calib lúc khởi động (2 tải tắt) hoặc bằng lệnh `calibrate`
- `P [W] = 12 V × I` (điện áp coi như hằng, đo kiểm bằng VOM, ghi vào phần hạn chế)
- `E [Wh] += P × Δt / 3600` mỗi khối 250 ms, lưu Flash mỗi 60 s, reset lúc 0h (NTP, GMT+7)
- `power_w` gửi lên là **trung bình 2 s** (8 khối). Telemetry và vòng điều khiển cùng chu kỳ 2 s

### 4.2 Máy trạng thái quản lý tải (chạy cả khi mất mạng)
```
LED_ON ──(P > P_peak liên tục ≥ 4 s)──> SHED_PEAK ──(P < P_peak − H liên tục ≥ 15 s
   ▲                                                   VÀ LED đã tắt ≥ 20 s
   └───────────────────────────────────────────────────VÀ P + P_LED_ước_lượng < P_peak)
LED_ON ──(E_hôm_nay ≥ ngân sách)──> SHED_BUDGET ──(sang ngày mới)──> LED_ON
Vẫn vượt ngưỡng ≥ 10 s khi LED đã tắt → ALARM_OVER_LIMIT + buzzer (quạt ưu tiên cao KHÔNG bị cắt)
```
- `P_LED_ước_lượng` học từ bước nhảy công suất sau mỗi lần LED đổi trạng thái. Nhờ vậy không khôi phục khi biết chắc sẽ vượt lại, tránh bật/tắt liên tục
- Chỉ chạy khi `auto_mode` hoặc `safe_mode`. Lệnh bật/tắt tay khi đang AUTO → chuyển MANUAL (sự kiện `MANUAL_OVERRIDE`)
- Mất broker > 30 s → `safe_mode = true`; kết nối lại → sự kiện `RECOVERED` (kèm thời gian mất kết nối)

### 4.3 Nạp
1. Arduino IDE, board **ESP32S3 Dev Module**, cài thư viện `PubSubClient`, `ArduinoJson`
2. Copy `secrets.example.h` → `secrets.h`, điền WiFi
3. Upload, mở Serial 115200. **Tắt cả 2 tải** trong ~1 s đầu để calib điểm 0

## 5. Đặc tả MQTT

Broker `broker.hivemq.com` (TCP 1883 cho ESP32/backend, WSS 8884 `/mqtt` cho web). Gốc topic: `smartenergy/<device_id>/`

| Topic | Hướng | QoS / retain | Payload |
|---|---|---|---|
| `telemetry` | ESP → | 0 | xem dưới, 2 s/lần |
| `status` | ESP → | LWT QoS1, retained | `online` / `offline` |
| `state` | ESP → | retained | cấu hình + trạng thái tải hiện tại |
| `event` | ESP → | 0 | `{type, detail, power_w, limit_w, ts}` |
| `cmd` | web/backend → ESP | 1 (ESP subscribe QoS1) | `{cmd_id, ts, src, fan?, led?, auto_mode?, peak_limit_w?, hysteresis_w?, budget_wh?, calibrate?, reset_energy?}` |
| `ack` | ESP → | 0 | `{cmd_id, cmd_ts, ok, error?, ...state}` (trạng thái **thực tế** sau khi áp dụng) |

```json
{"dev":"node9988","ts":1789550319106,"seq":42,"current_a":0.352,"power_w":4.224,
 "energy_today_wh":0.0931,"energy_total_wh":1.204,"peak_today_w":4.301,
 "fan":true,"led":true,"led_shed":"NONE","auto_mode":true,"safe_mode":false,
 "peak_limit_w":3.5,"hysteresis_w":0.5,"budget_wh":0,"led_est_w":1.8,
 "alarm_over":false,"alarm_budget":false,"sensor_mv":2565.1,"zero_mv":2500.0,"rssi":-55,"uptime_s":84}
```
Lý do chọn QoS: telemetry QoS0 vì gói sau thay gói trước, mất 1 gói chấp nhận được và được đếm qua `seq`. Lệnh QoS1 để không mất lệnh. PubSubClient chỉ **publish** được QoS0, nên lệnh được đảm bảo bằng ACK ở tầng ứng dụng kèm timeout 5 s trên web (ghi vào phần hạn chế). Event types: `SHED, RESTORE, ALARM_OVER_LIMIT, ALARM_CLEAR, BUDGET_WARN, BUDGET_EXCEEDED, MANUAL_OVERRIDE, RECOVERED`.

## 6. Cơ sở dữ liệu (SQLite)

| Bảng | Cột chính |
|---|---|
| `telemetry` | ts_device, ts_server, seq, current_a, power_w, energy_today_wh, energy_total_wh, peak_today_w, fan, led, led_shed, auto_mode, safe_mode, peak_limit_w, hysteresis_w, budget_wh, alarm_over, alarm_budget, sensor_mv, rssi |
| `events` | ts_device, ts_server, type, detail, power_w, limit_w |
| `availability` | ts_server, status |
| `commands` | cmd_id, source (web/rest), payload, ts_client, ts_seen_server, ts_ack_server, ack_ok, ack_error, ack_state, latency_ms |
| `settings` | tariff_vnd_per_kwh |

## 7. REST API (đầy đủ tại `http://localhost:8000/docs`)

| Method | Path | Mô tả |
|---|---|---|
| GET | `/api/status` | Telemetry mới nhất, online/offline, độ tươi dữ liệu, trạng thái đã xác nhận, Wh và chi phí hôm nay |
| GET | `/api/history?minutes=60&bucket_s=` | Chuỗi thời gian đã gộp (avg/max) |
| GET | `/api/energy/daily?days=7` | Wh, đỉnh, chi phí theo ngày (tích phân hình thang) |
| GET | `/api/events`, `/api/availability`, `/api/commands` | Nhật ký |
| POST | `/api/command` | `{"fan":true,"wait_ack_s":3}` → trả `requested` và `confirmed` |
| POST | `/api/config` | `{"auto_mode":true,"peak_limit_w":3.5,"hysteresis_w":0.5,"budget_wh":20}` |
| GET/PUT | `/api/settings` | Đơn giá điện |
| GET | `/api/stats?minutes=10` | Đỉnh, Wh, thời gian vượt ngưỡng, số lần đóng cắt, tỉ lệ nhận gói, độ trễ |
| GET | `/api/export/{telemetry|events|commands|availability}.csv?minutes=` | Xuất bảng cho báo cáo |

## 8. Chạy hệ thống

```bash
cd backend
pip install -r requirements.txt
python main.py                      # http://localhost:8000
```
- Mở **http://localhost:8000** (dashboard do backend phục vụ, có đủ lịch sử)
- Chưa có phần cứng: `python tools/device_simulator.py` (chạy song song)
- Deploy Vercel: đặt root = `dashboard/`. Realtime vẫn chạy qua WSS. Để có lịch sử, backend phải truy cập được qua **HTTPS** (ví dụ `cloudflared tunnel --url http://localhost:8000`), rồi mở `https://<vercel>/?api=https://<tunnel>`
- Tuỳ chọn: `?broker=ws://<ip>:9001` để dùng broker Mosquitto nội bộ khi WiFi trường chặn HiveMQ
- Biến môi trường backend: `MQTT_HOST`, `MQTT_PORT`, `MQTT_USER`, `MQTT_PASS`, `DEVICE_ID`, `DB_FILE`, `PORT`

## 8B. Deploy cloud 24/7 (Neon Postgres + Render + Vercel)

Backend chạy được cả SQLite lẫn PostgreSQL: có biến `DATABASE_URL` thì dùng Postgres, không có thì dùng file SQLite. Không phải sửa code.

1. **Tạo database Neon**: Vercel → tab Storage → Marketplace → Neon (hoặc vào thẳng neon.tech). Copy chuỗi **pooled connection** dạng `postgresql://user:pass@ep-xxx-pooler.region.aws.neon.tech/neondb?sslmode=require`
2. **Deploy backend lên Render**: Render → New → **Blueprint** → chọn repo này (file `render.yaml` đã có sẵn). Vào tab Environment điền:
   - `DATABASE_URL` = chuỗi Neon ở trên
   - `API_KEY` = một chuỗi ngẫu nhiên tự đặt (bắt buộc, vì backend giờ nằm công khai trên Internet)
   Deploy xong sẽ có URL dạng `https://smart-energy-backend.onrender.com`. Mở `<URL>/api/health`, thấy `"db":"postgres"` là đã nối đúng Neon. Bảng được tạo tự động ở lần chạy đầu.
3. **Nối dashboard**: mở `dashboard/index.html`, sửa dòng `const DEFAULT_API = '';` thành URL Render ở trên, rồi push để Vercel deploy lại. Trên dashboard, dán `API_KEY` vào ô **API Key** rồi bấm Lưu (lưu trong trình duyệt, không nằm trong repo).
4. **Chống ngủ**: gói free của Render tắt service sau khoảng 15 phút không có request HTTP, lúc đó kết nối MQTT cũng dừng nên dữ liệu bị thủng. Tạo một job trên cron-job.org (miễn phí) gọi `https://<render-url>/api/health` mỗi 10 phút. Gói free có 750 giờ/tháng nên ping liên tục vẫn đủ cho 1 service.
5. **Dung lượng**: Neon free khoảng 0.5 GB. Telemetry 2 s/lần ≈ 1.3 triệu dòng/tháng, nên backend tự xóa dữ liệu cũ hơn `RETENTION_DAYS` (mặc định 60 ngày).

Ghi chú cho báo cáo: kiến trúc này tách **worker ingest** (Render, luôn chạy, giữ kết nối MQTT) khỏi **giao diện** (Vercel, chỉ là file tĩnh). Vercel chạy serverless function, không giữ được kết nối MQTT lâu dài nên không thể tự ingest — đây là lý do kỹ thuật nên đưa vào phần Architecture.

Giới hạn còn lại: `API_KEY` chỉ bảo vệ REST API. Topic MQTT trên broker public vẫn ai cũng publish được, muốn chặn hẳn thì phải chuyển sang broker có xác thực (HiveMQ Cloud/EMQX) và điền `MQTT_USER`/`MQTT_PASS` cho cả firmware lẫn backend.

## 9. Kịch bản thí nghiệm (bắt buộc theo đề)

| # | Thí nghiệm | Cách làm | Số liệu |
|---|---|---|---|
| E1 | Sai số đo | Đồng hồ vạn năng/USB-DC meter nối tiếp. Đo 4 trường hợp: 0 tải, quạt, LED, cả hai; mỗi trường hợp 30 mẫu | Sai số tuyệt đối/%, độ lệch chuẩn |
| E2 | Độ trễ sự kiện → dashboard | Bật tải, đọc "Thiết bị → Dashboard" và `latency_device_to_backend_ms` (cần NTP) | TB, p95, max |
| E3 | Độ trễ lệnh → xác nhận | Bấm BẬT/TẮT 30 lần | TB, p95; số lệnh timeout |
| E4 | Unmanaged vs managed | 10 phút AUTO tắt, cả 2 tải bật, ngưỡng 3.5 W → `/api/stats`; lặp lại với AUTO bật | Đỉnh W, Wh, `over_limit_duration_s`, `led_switch_count` |
| E5 | Chống chattering | Chọn ngưỡng sát P(quạt+LED), so sánh với hysteresis 0.1 W / MIN_OFF=0 (bản không bảo vệ) | Số lần đóng cắt / 10 phút |
| E6 | Mất mạng | Tắt WiFi router 60 s khi đang vượt ngưỡng | Thời điểm OFFLINE (LWT), LED vẫn bị cắt cục bộ, thời gian `RECOVERED`, số gói mất qua `seq` |
| E7 | Ngân sách ngày | `budget_wh` nhỏ (ví dụ 0.5 Wh) | Thời điểm BUDGET_WARN/EXCEEDED, LED bị cắt |

## 10. Hạn chế và bảo mật
- HiveMQ public không có xác thực: ai biết topic đều đọc/gửi lệnh được. Hướng khắc phục: HiveMQ Cloud/EMQX với TLS + user/pass (code đã có sẵn `MQTT_USER/PASS`), ACL tách quyền topic `cmd`
- Không đo điện áp thật (giả định 12 V). ACS712 5 A có độ phân giải khoảng 0.02 A/count với tải nhỏ. Có thể thay bằng INA219/INA226 để đo cả V và I
- Một cảm biến đo tổng dòng, nên công suất từng tải chỉ là ước lượng
- ESP32 chỉ publish QoS0; khi mất mạng không lưu đệm telemetry, nhưng Wh vẫn tích lũy trên thiết bị

## Thành viên
| STT | Họ tên | MSSV | Nhiệm vụ |
|---|---|---|---|
| 1 | | | |
