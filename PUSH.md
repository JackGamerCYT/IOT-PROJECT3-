# Cách đưa toàn bộ dự án lên GitHub

Repo đích: https://github.com/JackGamerCYT/IOT-PROJECT3-

## Cách 1 — repo đã clone sẵn trên máy (khuyên dùng)

Mở PowerShell tại thư mục repo:

```powershell
# 1. Lấy bản mới nhất về trước cho khỏi xung đột
git pull

# 2. Xoá các file cũ đã bị thay thế (bỏ qua nếu báo không tìm thấy)
git rm -rf dashboard vercel.json firmware/esp32_firmware.ino gitignore 2>$null

# 3. Copy nội dung thư mục iot-p3 trong file zip vào thư mục repo, ghi đè khi được hỏi
#    (làm bằng File Explorer, hoặc lệnh dưới đây — sửa đường dẫn nguồn cho đúng)
Copy-Item -Path "$HOME\Downloads\iot-p3\*" -Destination . -Recurse -Force

# 4. Kiểm tra không có file bí mật nào lọt vào
git status
#    KHÔNG được thấy: secrets.h, energy_data.db, __pycache__

# 5. Commit và đẩy lên
git add -A
git commit -m "v19: RTC DS3231 + OLED, dem du lieu offline, tro ly du lieu, bao cao do an"
git push
```

## Cách 2 — chưa có repo trên máy

```powershell
cd $HOME\Documents
git clone https://github.com/JackGamerCYT/IOT-PROJECT3-.git
cd IOT-PROJECT3-
# rồi làm tiếp từ bước 2 ở Cách 1
```

## Cách 3 — không dùng dòng lệnh

1. Mở https://github.com/JackGamerCYT/IOT-PROJECT3-
2. Xoá thủ công `firmware/esp32_firmware.ino`, `gitignore`, và thư mục `dashboard/` nếu còn (mở file → biểu tượng thùng rác → Commit)
3. Bấm **Add file → Upload files**, kéo thả `index.html` và các thư mục `backend`, `firmware`, `tools`, `docs`, cùng `README.md`, `render.yaml`, `PUSH.md`, `.gitignore`
4. Ghi commit message rồi **Commit changes**

GitHub web không upload được file ẩn như `.gitignore` bằng kéo thả. Tạo nó bằng **Add file → Create new file**, gõ tên `.gitignore` rồi dán nội dung từ file trong zip.

## Sau khi push

| Việc | Nơi làm |
|---|---|
| Deploy backend | Render → New → Blueprint → chọn repo → điền `DATABASE_URL`, `API_KEY` |
| Deploy giao diện | Vercel → Add New → Project → Import repo → Preset Other, Root Directory để TRỐNG |
| Nối hai bên | Sửa `const DEFAULT_API` trong `index.html` (ở gốc repo) thành URL Render, push lại |
| Chống ngủ | cron-job.org gọi `<url-render>/api/health` mỗi 10 phút |

## Kiểm tra trước khi nộp

```powershell
git log --oneline -3          # thấy commit mới nhất
git ls-files | Select-String "secrets.h"   # không ra kết quả nào
```

Nếu mật khẩu WiFi cũ đã từng được commit trong các bản trước, lịch sử Git vẫn còn lưu. Cách xử lý đơn giản nhất là đổi mật khẩu WiFi đó, vì xoá lịch sử Git phức tạp hơn nhiều.
