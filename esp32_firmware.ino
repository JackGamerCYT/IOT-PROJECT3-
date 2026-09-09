#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// ==========================================
// CẤU HÌNH WIFI & BROKER MQTT
// ==========================================
const char* ssid = "Tên_Wifi_Của_Bạn"; 
const char* password = "Mật_Khẩu_Wifi";
const char* mqtt_server = "172.20.10.2"; // IP thực tế của Laptop phát ra từ điện thoại

// Định nghĩa các cổng kết nối chân vật lý
const int acs712_pin = 34;   // Đọc Analog ADC từ cảm biến dòng ACS712
const int relay_1 = 12;      // Tải 1 (Ưu tiên Cao - Quạt 12V)
const int relay_2 = 13;      // Tải 2 (Ưu tiên Thấp - Đèn Led trang trí)

// Các thông số điện vật lý đo đạc
const float voltage_dc = 12.0; // Điện áp hệ thống DC 12V
float energy_wh = 0.0;
unsigned long last_sample_time = 0;

// Các biến phục vụ điều khiển quản lý tải thông minh (Hysteresis)
float peak_limit = 24.0;    // Ngưỡng công suất tối đa mặc định (W)
bool auto_mode = true;      // Chế độ tự động quản lý tải bằng logic cục bộ
float hysteresis = 4.0;     // Ngưỡng trễ an toàn để khôi phục Tải 2 (W)
bool load_1_state = false;
bool load_2_state = false;

WiFiClient espClient;
PubSubClient client(espClient);

// ==========================================
// THUẬT TOÁN ĐO DÒNG ĐIỆN RMS CHUẨN XÁC
// ==========================================
float readRMSCurrent() {
  float sum = 0;
  int sample_count = 1000;
  
  for (int i = 0; i < sample_count; i++) {
    float raw_voltage = (analogRead(acs712_pin) * 3.3) / 4095.0; // Đổi ADC ra vôn analog
    float current_offset = 1.65; // Điểm offset giữa của cảm biến ACS712 5A
    float current = (raw_voltage - current_offset) / 0.185; // Độ nhạy cảm biến 185mV/A
    sum += current * current;
    delayMicroseconds(50);
  }
  
  float rms_current = sqrt(sum / sample_count);
  if (rms_current < 0.05) rms_current = 0.0; // Loại bỏ nhiễu rò nhỏ
  return rms_current;
}

// ==========================================
// KẾT NỐI WIFI VÀ MQTT LWT
// ==========================================
void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Đang kết nối Wifi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi đã kết nối thành công!");
}

// Đồng bộ trạng thái thực tế về Server
void publishStates() {
  StaticJsonDocument<128> doc;
  doc["load_1"] = load_1_state ? "ON" : "OFF";
  doc["load_2"] = load_2_state ? "ON" : "OFF";
  char buffer[128];
  serializeJson(doc, buffer);
  client.publish("energy/device/status", buffer, true);
}

// Xử lý dữ liệu nhận từ Dashboard qua MQTT Broker
void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Nhận bản tin từ topic [");
  Serial.print(topic);
  Serial.println("]");
  
  String msg = "";
  for (unsigned int i = 0; i < length; i++) {
    msg += (char)payload[i];
  }
  
  // 1. Đồng bộ cấu hình ngưỡng cắt tải từ xa
  if (String(topic) == "energy/device/config/limit") {
    peak_limit = msg.toFloat();
    Serial.print("Cập nhật ngưỡng công suất mới: ");
    Serial.println(peak_limit);
  }
  // 2. Chuyển đổi chế độ hoạt động (Tự động / Thủ công)
  else if (String(topic) == "energy/device/config/mode") {
    auto_mode = (msg == "1.0" || msg == "1");
    Serial.print("Chế độ tự động (Auto): ");
    Serial.println(auto_mode ? "BẬT" : "TẮT");
  }
  // 3. Nhận lệnh điều khiển thủ công từ Web
  else if (String(topic) == "energy/device/control") {
    StaticJsonDocument<128> doc;
    deserializeJson(doc, msg);
    int load_id = doc["load_id"];
    String action = doc["action"]; // "ON" hoặc "OFF"
    
    if (!auto_mode) { // Chỉ cho phép điều khiển tay khi đã tắt Auto
      if (load_id == 1) {
        load_1_state = (action == "ON");
        digitalWrite(relay_1, load_1_state ? LOW : HIGH); // Module Relay kích mức thấp (Low)
      } else if (load_id == 2) {
        load_2_state = (action == "ON");
        digitalWrite(relay_2, load_2_state ? LOW : HIGH);
      }
      publishStates(); // Gửi trạng thái phản hồi lập tức để Backend ghi Control Log
    }
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Đang thử kết nối MQTT... ");
    // Cài đặt LWT (Last Will and Testament): Tự động báo mất mạng nếu ESP32 mất kết nối đột ngột
    if (client.connect("ESP32_EnergyNode", "energy/device/availability", 1, true, "OFFLINE")) {
      Serial.println("Đã kết nối MQTT Broker!");
      client.publish("energy/device/availability", "ONLINE", true);
      client.subscribe("energy/device/control");
      client.subscribe("energy/device/config/limit");
      client.subscribe("energy/device/config/mode");
      publishStates(); // Đồng bộ trạng thái ngay khi có mạng trở lại
    } else {
      Serial.print("Thất bại, lỗi rc=");
      Serial.print(client.state());
      Serial.println(" Thử lại sau 5 giây");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(acs712_pin, INPUT);
  
  // Khởi tạo các chân Relay điều khiển
  pinMode(relay_1, OUTPUT);
  pinMode(relay_2, OUTPUT);
  
  // Mới khởi động: Bật cả 2 tải để đo đếm ban đầu
  load_1_state = true;
  load_2_state = true;
  digitalWrite(relay_1, LOW); 
  digitalWrite(relay_2, LOW);

  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
  last_sample_time = millis();
}

// ==========================================
// VÒNG LẶP CHÍNH & TRÍ TUỆ CỤC BỘ OFFLINE
// ==========================================
void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  unsigned long current_time = millis();
  if (current_time - last_sample_time >= 2000) { // Cứ 2 giây đo đạc 1 lần
    float dt = (current_time - last_sample_time) / 1000.0;
    last_sample_time = current_time;

    // 1. Tiến hành đo đạc thông số điện năng
    float current_rms = readRMSCurrent();
    float power_w = voltage_dc * current_rms;
    energy_wh += power_w * (dt / 3600.0); // Tích lũy điện năng tiêu thụ Wh

    // 2. Thuật toán quản lý tải thông minh (Hysteresis) - Hoạt động tốt cả khi mất mạng
    if (auto_mode) {
      if (power_w > peak_limit) {
        if (load_2_state) {
          load_2_state = false;
          digitalWrite(relay_2, HIGH); // Tự động sa thải tải phụ (Tải 2) ngay lập tức
          Serial.println("⚠️ Quá tải! Đã tự động cắt Đèn Led (Tải 2) để bảo vệ hệ thống!");
          publishStates(); // Gửi trạng thái phản hồi lập tức để Backend ghi Control Log
        }
      } else if (power_w < (peak_limit - hysteresis)) {
        if (!load_2_state) {
          load_2_state = true;
          digitalWrite(relay_2, LOW); // Tự động khôi phục tải phụ khi công suất đã ổn định
          Serial.println("🟢 Công suất an toàn. Tự động bật lại Đèn Led.");
          publishStates();
        }
      }
    }

    // 3. Gửi thông số đo đạc (Telemetry) lên Server qua MQTT
    StaticJsonDocument<256> doc;
    doc["voltage"] = voltage_dc;
    doc["current"] = current_rms;
    doc["power"] = power_w;
    doc["energy"] = energy_wh;
    
    char buffer[256];
    serializeJson(doc, buffer);
    client.publish("energy/device/telemetry", buffer);
    
    // In thông số ra màn hình để theo dõi
    Serial.printf("U: %.1fV | I: %.2fA | P: %.1fW | E: %.3fWh\n", voltage_dc, current_rms, power_w, energy_wh);
  }
}
