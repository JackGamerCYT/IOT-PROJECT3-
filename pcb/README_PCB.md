# Mạch in 1 lớp cho Project 03 — hướng dẫn ủi đồng

Board **100 × 80 mm**, **chỉ 1 lớp đồng mặt dưới (BOTTOM)**, toàn bộ linh kiện là loại **cắm (through-hole)**, module relay **để ngoài**, trên mạch chỉ có hàng rào cắm.

File trong thư mục này:

| File | Dùng để làm gì |
|---|---|
| `BOTTOM_mirrored_iron.pdf` | **Bản in để ủi** — đã lật gương sẵn, tỉ lệ 1:1 |
| `BOTTOM_normal_check.pdf` | Bản không lật, dùng đối chiếu khi dò mạch bằng đồng hồ |
| `TOP_placement.pdf` | Sơ đồ cắm linh kiện, nhìn từ mặt linh kiện |
| `smart_energy.kicad_pcb` | Mở bằng KiCad 7/8/9 nếu muốn sửa |
| `make_pcb.py` | Script sinh lại toàn bộ (sửa toạ độ rồi chạy `python3 make_pcb.py`) |
| `ASSEMBLY_SHEET.pdf` | **Phiếu lắp ráp 3 trang**: sơ đồ vị trí, thứ tự lắp có ô tick, bảng đấu dây ra module ngoài, danh sách đo kiểm |
| `BOM_DRILL.md` | Danh sách linh kiện + mũi khoan |
| `DRC_REPORT.txt` | Kết quả tự kiểm tra khoảng cách và thông mạch |

Thông số thiết kế: đường tín hiệu 0.6 mm, đường nguồn 1.0 mm, khe cách điện tối thiểu 0.4 mm, phủ đồng GND toàn mặt dưới, pad 2.0 mm (domino 2.6 mm).

Vùng phủ đồng GND có **thermal relief**: mỗi chân GND nối với vùng đồng bằng 4 nan rộng 0.9 mm thay vì dính liền cả mảng. Nhờ vậy mỏ hàn không bị hút nhiệt, mối hàn ăn thiếc dễ hơn nhiều. Script cũng tự bỏ các mảnh đồng mảnh hơn 0.6 mm và các mảnh đồng cô lập không nối GND, nên bản in không còn sợi đồng vụn khó ăn mòn.

## 1. Bảng nối chân

| Rào | Chân trên mạch | Nối tới |
|---|---|---|
| **J1** (1×22) | hàng **trái** ESP32-S3 DevKitC-1 | 3V3, IO8, IO9, IO12, IO13, IO14, 5V, GND |
| **J3** (1×22) | hàng **phải** ESP32-S3 DevKitC-1 | IO1 (ADC), GND |
| **J4** (1×4) | 3V3 · SDA · SCL · GND | module DS3231 |
| **J5** (1×4) | 3V3 · SDA · SCL · GND | module OLED SSD1306 |
| **J6** (1×5) | IN1 · IN2 · 3V3 · 5V · GND | **module relay 2 kênh để ngoài** |
| **J7** (1×3) | 5V · OUT · GND | module ACS712-05B |
| **J9** | GND · 12V+ | nguồn adapter 12 V vào |
| **F1** | IN · OUT | cầu chì 2 A (đế 5×20 hoặc đoạn dây) |
| **J8** | 12V+ · GND | 12 V **đã qua cầu chì**, đi ra ACS712 IP+ và cọc COM của relay |
| **J10** | IN+ · IN− | ngõ vào module LM2596 |
| **J11** | OUT+ · OUT− | ngõ ra 5 V của LM2596 |

Cách đấu module relay: tháo jumper JD-VCC trên module, nối **JD-VCC ↔ chân 5V của J6**, **VCC ↔ chân 3V3 của J6**, GND/IN1/IN2 theo tên. Nhờ vậy cuộn dây relay chạy 5 V còn opto chạy mức 3.3 V của ESP32, tắt dứt khoát.

Mạch động lực (12 V qua ACS712 rồi qua tiếp điểm relay tới quạt và đèn) đi **dây ngoài**, không chạy trên mạch in. Trên board chỉ có dòng nuôi mạch điều khiển, nên đường 12 V rộng 1 mm là đủ.

## 2. Hai dây nối trên mặt linh kiện (JW1, JW2)

Mạch 1 lớp không tránh được vài chỗ giao nhau. Thiết kế này chỉ cần **2 đoạn dây đồng** hàn ở **mặt linh kiện**:

- **JW1** — nối GND bắc qua đường 5 V, dài 4.8 mm
- **JW2** — nối GND bắc qua hai đường IN1/IN2, dài 7 mm

Dùng chân điện trở cắt ra là vừa. Thiếu 2 dây này thì phần GND của DS3231, OLED, relay và tụ lọc sẽ hở mạch.

## 3. Quy trình ủi đồng

1. **In** file `BOTTOM_mirrored_iron.pdf` bằng máy in laser lên giấy in chuyển nhiệt (hoặc giấy ảnh bóng). Trong hộp thoại in phải chọn **Scale 100% / Actual size**, tuyệt đối không chọn Fit to page. In xong đo lại board trên giấy phải đúng 100 × 80 mm.
2. **Cắt phíp** đồng 1 mặt đúng 100 × 80 mm, chà mặt đồng bằng giấy nhám mịn rồi lau cồn cho sạch dầu mỡ.
3. **Ủi**: úp mặt mực xuống đồng, bàn ủi để mức cotton (khoảng 160–180 °C), ủi đều 5–8 phút, miết kỹ mép board.
4. **Ngâm nước** ấm 10 phút rồi bóc giấy thật từ từ. Chỗ nào mực thiếu thì tô lại bằng bút lông dầu.
5. **Ăn mòn**: FeCl₃ hoặc hỗn hợp HCl + H₂O₂ (3:1), lắc nhẹ 10–20 phút. **Đeo găng và kính, làm nơi thoáng.**
6. **Rửa sạch**, lau mực bằng cồn hoặc axeton.
7. **Khoan**: mũi 0.9 mm cho điện trở/transistor, 1.0 mm cho hàng rào và tụ, 1.3 mm cho domino và cầu chì, 3.2 mm cho 4 lỗ bắt ốc.
8. **Kiểm tra trước khi hàn**: đồng hồ nấc thông mạch, đo 12V–GND, 5V–GND, 3V3–GND, **không được kêu**. Soi đèn tìm đường đứt hoặc dính.
9. **Hàn** theo thứ tự: dây nối JW1/JW2 → điện trở, diode → transistor, tụ → hàng rào → domino → cuối cùng là cầu chì và còi.
10. **Chỉnh LM2596 ra đúng 5.00 V trước khi cắm ESP32.** Cấp 12 V vào J9, đo tại J11 OUT+ và GND.

## 4. Kiểm tra sau khi hàn

| Bước | Cách đo | Đạt khi |
|---|---|---|
| Ngắn mạch nguồn | Đo trở giữa 12V–GND, 5V–GND, 3V3–GND khi chưa cắm module | Không kêu tít, trở > vài trăm Ω |
| Điện áp | Cấp 12 V, đo J11 OUT+ | 5.00 V ± 0.05 |
| 3V3 | Cắm ESP32, đo chân 3V3 của J4 | 3.3 V |
| I2C | Đo thông mạch J4.SDA ↔ J5.SDA ↔ chân IO8 của J1 | Kêu tít |
| Relay | Đo J6.IN1 ↔ IO12 của J1, J6.IN2 ↔ IO13 | Kêu tít |
| ADC | Đo J7.OUT ↔ R1, và R1 ↔ IO1 của J3 | Kêu tít |
| GND | Đo GND của J4, J5, J6, J7 với GND của J9 | Tất cả đều thông (nhờ JW1, JW2) |

## 5. Ghi chú thiết kế

- Cầu phân áp **R1 10 kΩ / R2 20 kΩ** hạ mức ra của ACS712 từ 0–5 V xuống 0–3.33 V cho ADC. Sau khi lắp nhớ đặt `DIVIDER_RATIO = 0.6667` trong firmware.
- **C2 100 nF** song song R2 lọc nhiễu cho đường ADC, **C1 100 µF** lọc 5 V, **C3 100 nF** lọc 3V3.
- **Q1 S8050** lái còi, **R3 1 kΩ** hạn dòng cực nền. Chân theo thứ tự **E–B–C** từ trên xuống, mặt phẳng quay ra ngoài board; kiểm tra lại datasheet transistor bạn mua.
- LM2596 lấy nguồn **trước** ACS712, nên dòng của mạch điều khiển không bị tính vào phép đo tải.
- Thứ tự chân của J1/J3 lấy theo tài liệu ESP32-S3-DevKitC-1 v1.1 của Espressif. Nếu board bạn mua khác thứ tự, sửa `J1_NETS`/`J3_NETS` trong `make_pcb.py` rồi chạy lại script.
