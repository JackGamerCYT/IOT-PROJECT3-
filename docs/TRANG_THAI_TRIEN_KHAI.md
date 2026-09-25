# Trạng thái triển khai và việc còn lại

Cập nhật: 23/09/2026

## 1. Đang chạy

| Thành phần | Địa chỉ / vị trí | Ghi chú |
|---|---|---|
| Repo | https://github.com/JackGamerCYT/IOT-PROJECT3- | `index.html` phải nằm ở **gốc** repo |
| Backend (worker ingest + REST API) | https://smart-energy-backend-rrvs.onrender.com | Render gói free, deploy bằng `render.yaml` |
| Cơ sở dữ liệu | Neon PostgreSQL, region Singapore | Dùng chuỗi **pooled** (`-pooler`, `?sslmode=require`) |
| Broker MQTT | `broker.hivemq.com` — 1883 (TCP), 8884 (WSS) | Công khai, không xác thực |
| Dashboard | Vercel, nguồn là `index.html` ở gốc repo | `DEFAULT_API` đã trỏ về Render |

Biến môi trường đã đặt trên Render: `DATABASE_URL`, `API_KEY`.

## 2. Luồng dữ liệu

```
ESP32 đo (4 khối/giây) → gộp trung bình 2 s → publish MQTT
        ↓
broker.hivemq.com   (chỉ trung chuyển, KHÔNG lưu)
        ↓ subscribe
Backend FastAPI trên Render  → INSERT
        ↓
Neon PostgreSQL   ← dữ liệu nằm lại ở đây
        ↓ REST API
Dashboard trên Vercel (realtime lấy thẳng từ broker qua WSS)
```

Broker không lưu lịch sử, nên backend phải chạy liên tục thì dữ liệu mới vào được database.

## 3. Dữ liệu lưu ở đâu

| Bảng | Nội dung | Tần suất ghi |
|---|---|---|
| `telemetry` | Dòng, công suất, Wh trong ngày, Wh tổng, đỉnh, trạng thái 2 tải, ngưỡng, RSSI | 1 dòng / 2 giây |
| `events` | SHED, RESTORE, ALARM_OVER_LIMIT, BUDGET_*, MANUAL_OVERRIDE, RECOVERED | Khi có sự kiện |
| `availability` | online / offline (phát hiện bằng LWT) | Khi đổi trạng thái |
| `commands` | Mọi lệnh, nguồn gửi, thời điểm nhận, thời điểm xác nhận, độ trễ ms | Khi có lệnh |
| `settings` | Đơn giá điện (đ/kWh) | Khi người dùng sửa |

Mỗi dòng `telemetry` có `ts_device` (thiết bị tạo gói) và `ts_server` (backend nhận). Hiệu số chính là độ trễ đầu cuối dùng cho thí nghiệm E2.

Khối lượng: khoảng 43.000 dòng/ngày ≈ 6 MB/ngày. Neon free 0.5 GB, backend tự xoá dữ liệu cũ hơn `RETENTION_DAYS` (mặc định 60 ngày) mỗi 6 giờ.

## 4. Cách kiểm chứng từng chặng

| Chặng | Cách kiểm tra | Kết quả đúng |
|---|---|---|
| Backend + database | `/api/health` | `"db":"postgres"`, `"mqtt_connected":true` |
| Có dữ liệu mới | `/api/status` | `latest` khác null, `data_age_s` nhỏ hơn 6 |
| Lịch sử | `/api/history?minutes=10` | Mảng điểm theo thời gian |
| Bằng chứng thô | `/api/export/telemetry.csv?minutes=60` | File CSV mở bằng Excel |
| Database | Neon Console → SQL Editor | Xem mục 5 |
| Giao diện | Trang Vercel, 4 badge trên đầu | Thiết bị / Dữ liệu / MQTT / Backend đều xanh |

## 5. Câu lệnh SQL kiểm tra trên Neon

```sql
SELECT count(*) AS so_dong FROM telemetry;

SELECT to_timestamp(ts_server/1000) AT TIME ZONE 'Asia/Bangkok' AS thoi_gian,
       power_w, current_a, energy_today_wh, fan, led, auto_mode
FROM telemetry ORDER BY ts_server DESC LIMIT 10;

SELECT to_timestamp(ts_server/1000) AT TIME ZONE 'Asia/Bangkok' AS thoi_gian,
       type, detail, power_w, limit_w
FROM events ORDER BY ts_server DESC LIMIT 10;

-- Độ trễ thiết bị -> backend (ms)
SELECT round(avg(ts_server - ts_device)) AS trung_binh,
       max(ts_server - ts_device) AS lon_nhat, count(*) AS n
FROM telemetry WHERE ts_device IS NOT NULL;

-- Độ trễ lệnh -> xác nhận (ms)
SELECT source, count(*) AS so_lenh, round(avg(latency_ms)) AS tre_trung_binh
FROM commands WHERE latency_ms IS NOT NULL GROUP BY source;
```

## 6. Việc còn lại

- [ ] Xoá `vercel.json` và thư mục `dashboard/` cũ trên GitHub nếu còn (file cũ trong đó chưa nối backend)
- [ ] Tạo cron trên cron-job.org gọi `/api/health` mỗi 10 phút để Render không ngủ
- [ ] Hàn mạch theo `docs/WIRING.md`, nhớ cầu phân áp 10 kΩ/20 kΩ cho chân ADC
- [ ] Nạp firmware: cài `PubSubClient`, `ArduinoJson`, `RTClib`, `Adafruit SSD1306`, `Adafruit GFX`; tạo `secrets.h`; đặt `DIVIDER_RATIO = 0.6667` nếu đã lắp phân áp
- [ ] Chạy 8 thí nghiệm ở mục 10 README, điền số vào mục 11 báo cáo
- [ ] Điền tên 3 thành viên còn lại: trang bìa và mục 15 của báo cáo, mục 12 README
- [ ] Quay video demo dự phòng cho buổi bảo vệ

## 7. Hạn chế đã biết (đã ghi trong báo cáo)

- Broker công khai không xác thực: ai biết topic đều đọc dữ liệu và gửi lệnh được
- `API_KEY` nằm trong repo công khai nên chỉ có tác dụng hình thức; muốn riêng tư thì đổi khoá trên Render, xoá `DEFAULT_API_KEY` trong `index.html` và nhập khoá ở ô API Key trên giao diện
- Gói free của Render ngủ sau ~15 phút không có truy cập, gây thủng dữ liệu nếu không có cron ping
- Điện áp giả định cố định 12 V, không đo trực tiếp
- Một cảm biến đo tổng dòng nên công suất từng tải chỉ là ước lượng
