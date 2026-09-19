/*
 * =====================================================================================
 *  PROJECT 03 - SMART ENERGY MONITORING & INTELLIGENT LOAD MANAGEMENT
 *  Firmware v17 - ESP32-S3 (N16R8)
 *
 *  Thay đổi chính so với v16:
 *   - Kết nối lại WiFi/MQTT KHÔNG CHẶN (non-blocking): logic sa thải tải luôn chạy cục bộ.
 *   - Đo dòng DC bằng giá trị trung bình analogReadMilliVolts() (có hiệu chuẩn eFuse),
 *     thay cho RMS theo công thức tuyến tính raw/4095*3.3.
 *   - Tích lũy điện năng Wh (hôm nay + tổng), lưu Flash (Preferences) mỗi 60 s.
 *   - Máy trạng thái sa thải tải: vượt ngưỡng liên tục T_OVER -> cắt LED;
 *     chỉ khôi phục khi an toàn liên tục T_SAFE + thời gian OFF tối thiểu + dự báo
 *     (P_hiện_tại + P_LED_ước_lượng) < ngưỡng  => chống bật/tắt liên tục (chattering).
 *   - Thành phần nâng cao: phát hiện đỉnh công suất (peak demand) + ngân sách điện năng ngày.
 *   - Lệnh có cmd_id -> thiết bị gửi ACK (trạng thái ĐÃ XÁC NHẬN) tách biệt trạng thái YÊU CẦU.
 *   - Timestamp NTP (epoch ms) trong mọi gói tin để đo độ trễ.
 *   - Safe mode: mất broker > 30 s -> tự bật quản lý tải cục bộ.
 *
 *  Thư viện: PubSubClient (Nick O'Leary), ArduinoJson (v6 hoặc v7).
 *  Board: ESP32S3 Dev Module. Core ESP32 2.x hoặc 3.x.
 * =====================================================================================
 */

#define ARDUINOJSON_USE_LONG_LONG 1
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <time.h>
#include <sys/time.h>

// -------------------------------------------------------------------------------------
// 1. BÍ MẬT (tạo file secrets.h cạnh file .ino, KHÔNG commit lên GitHub)
// -------------------------------------------------------------------------------------
#if __has_include("secrets.h")
  #include "secrets.h"
#else
  #define WIFI_SSID     "YOUR_WIFI"
  #define WIFI_PASSWORD "YOUR_PASSWORD"
  #define MQTT_USER     ""
  #define MQTT_PASS     ""
#endif

// -------------------------------------------------------------------------------------
// 2. MQTT - cây topic: smartenergy/<device_id>/<kênh>
// -------------------------------------------------------------------------------------
const char* DEVICE_ID   = "node9988";
const char* MQTT_BROKER = "broker.hivemq.com";
const int   MQTT_PORT   = 1883;

const char* T_TELEMETRY = "smartenergy/node9988/telemetry"; // 2 s/lần
const char* T_STATUS    = "smartenergy/node9988/status";    // retained + LWT: online/offline
const char* T_STATE     = "smartenergy/node9988/state";     // retained: cấu hình + trạng thái tải
const char* T_EVENT     = "smartenergy/node9988/event";     // cảnh báo, sa thải, khôi phục
const char* T_CMD       = "smartenergy/node9988/cmd";       // web/backend -> thiết bị (sub QoS1)
const char* T_ACK       = "smartenergy/node9988/ack";       // thiết bị -> xác nhận lệnh

// -------------------------------------------------------------------------------------
// 3. PHẦN CỨNG
// -------------------------------------------------------------------------------------
const int PIN_ACS712    = 1;    // ADC1_CH0. NÊN qua cầu phân áp 10k/20k (xem DIVIDER_RATIO)
const int PIN_RELAY_FAN = 12;   // Tải 1 - Quạt 12V (ưu tiên CAO), relay active LOW
const int PIN_RELAY_LED = 13;   // Tải 2 - LED 12V  (ưu tiên THẤP), relay active LOW
const int PIN_BUZZER    = 14;   // Buzzer 5V active qua transistor; đặt -1 nếu không lắp

const float ACS_MV_PER_A  = 185.0;  // ACS712-05B
const float DIVIDER_RATIO = 1.0;    // 1.0 nếu nối thẳng; 0.6667 nếu dùng phân áp 10k (trên) / 20k (dưới)
const float V_NOMINAL     = 12.0;   // Điện áp nguồn tải (V) - giả định hằng, đo kiểm bằng VOM
const float I_DEADBAND_A  = 0.04;   // Dưới ngưỡng này coi như 0 A (nhiễu nền)

// -------------------------------------------------------------------------------------
// 4. THÔNG SỐ ĐO / ĐIỀU KHIỂN
// -------------------------------------------------------------------------------------
const unsigned long BLOCK_MS          = 250;    // 1 khối đo = 64 mẫu, 4 khối/giây
const int           SAMPLES_PER_BLOCK = 64;
const unsigned long TELEMETRY_MS      = 2000;   // chu kỳ publish + chu kỳ điều khiển
const unsigned long T_OVER_MS         = 4000;   // vượt ngưỡng liên tục bao lâu thì cắt
const unsigned long T_SAFE_MS         = 15000;  // an toàn liên tục bao lâu thì cho khôi phục
const unsigned long MIN_OFF_MS        = 20000;  // LED bị cắt tối thiểu
const unsigned long T_ALARM_MS        = 10000;  // vẫn vượt ngưỡng sau khi cắt -> báo động
const unsigned long OFFLINE_SAFE_MS   = 30000;  // mất broker bao lâu thì vào safe mode
const unsigned long SAVE_MS           = 60000;

float peak_limit_w = 3.0;    // ngưỡng công suất đỉnh (W) - cấu hình từ web
float hysteresis_w = 0.5;    // dải trễ (W)
float budget_wh    = 0.0;    // ngân sách điện năng/ngày (Wh), 0 = tắt
bool  auto_mode    = false;

// -------------------------------------------------------------------------------------
// 5. BIẾN TRẠNG THÁI
// -------------------------------------------------------------------------------------
enum ShedReason { SHED_NONE = 0, SHED_PEAK, SHED_BUDGET };
const char* shedName(int r) { return r == SHED_PEAK ? "PEAK" : r == SHED_BUDGET ? "BUDGET" : "NONE"; }

bool fan_on = false, led_on = false;
int  led_shed = SHED_NONE;
unsigned long led_switch_ms = 0;

float zero_mv = 2500.0, last_mv = 0;
float current_a = 0, power_w = 0;      // khối đo mới nhất
float demand_w = 0;                    // công suất trung bình cửa sổ 2 s (dùng để điều khiển)
double sum_block_p = 0; int n_block = 0;
double energy_today_wh = 0, energy_total_wh = 0;
float  peak_today_w = 0;
long   day_key = 0;

unsigned long over_since = 0, safe_since = 0;
float led_est_w = 0;                   // công suất LED ước lượng (học khi cắt/khôi phục)
float p_before_switch = -1; bool learn_pending = false;
bool alarm_over = false, alarm_budget = false, budget_warned = false;

bool safe_mode = false;
unsigned long mqtt_lost_ms = 0;
unsigned long last_block = 0, last_tele = 0, last_save = 0, last_mqtt_try = 0, last_wifi_try = 0;
unsigned long seq = 0;

WiFiClient net;
PubSubClient mqtt(net);
Preferences prefs;
String client_id;

// -------------------------------------------------------------------------------------
uint64_t epochMs() {
  struct timeval tv; gettimeofday(&tv, nullptr);
  if (tv.tv_sec < 1700000000) return 0;           // chưa đồng bộ NTP
  return (uint64_t)tv.tv_sec * 1000ULL + tv.tv_usec / 1000;
}
long todayKey() {
  time_t now = time(nullptr); if (now < 1700000000) return 0;
  struct tm t; localtime_r(&now, &t);
  return (t.tm_year + 1900) * 10000L + (t.tm_mon + 1) * 100L + t.tm_mday;
}

void setRelay(int pin, bool on) { digitalWrite(pin, on ? LOW : HIGH); }
void buzzer(bool on) { if (PIN_BUZZER >= 0) digitalWrite(PIN_BUZZER, on ? HIGH : LOW); }

void publishJson(const char* topic, JsonDocument& doc, bool retained = false) {
  if (!mqtt.connected()) return;
  char buf[768];
  size_t n = serializeJson(doc, buf, sizeof(buf));
  mqtt.publish(topic, (const uint8_t*)buf, n, retained);
}

void publishEvent(const char* type, const char* detail) {
  Serial.printf("[EVENT] %s %s | P=%.2fW limit=%.2fW\n", type, detail, demand_w, peak_limit_w);
  StaticJsonDocument<384> d;
  d["dev"] = DEVICE_ID; d["ts"] = epochMs(); d["type"] = type; d["detail"] = detail;
  d["power_w"] = demand_w; d["limit_w"] = peak_limit_w; d["energy_today_wh"] = energy_today_wh;
  publishJson(T_EVENT, d);
}

void fillState(JsonDocument& d) {
  d["dev"] = DEVICE_ID; d["ts"] = epochMs();
  d["fan"] = fan_on; d["led"] = led_on; d["led_shed"] = shedName(led_shed);
  d["auto_mode"] = auto_mode; d["safe_mode"] = safe_mode;
  d["peak_limit_w"] = peak_limit_w; d["hysteresis_w"] = hysteresis_w; d["budget_wh"] = budget_wh;
}
void publishState() { StaticJsonDocument<384> d; fillState(d); publishJson(T_STATE, d, true); }

void switchLed(bool on, int reason) {
  if (on == led_on) { led_shed = on ? SHED_NONE : reason; return; }
  p_before_switch = demand_w; learn_pending = true;
  led_on = on; led_shed = on ? SHED_NONE : reason; led_switch_ms = millis();
  setRelay(PIN_RELAY_LED, on);
  publishState();
}

// -------------------------------------------------------------------------------------
// 6. ĐO LƯỜNG
// -------------------------------------------------------------------------------------
float readMvAvg(int n) {
  uint32_t s = 0;
  for (int i = 0; i < n; i++) s += analogReadMilliVolts(PIN_ACS712);
  return (float)s / n / DIVIDER_RATIO;   // quy về điện áp thật ở chân OUT của ACS712
}

void calibrateZero() {
  // Chỉ gọi khi CẢ HAI tải đang tắt
  float s = 0;
  for (int i = 0; i < 20; i++) { s += readMvAvg(50); delay(10); }
  zero_mv = s / 20.0;
  Serial.printf("[CAL] zero = %.1f mV (lý thuyết ~2500 mV khi VCC=5.0V)\n", zero_mv);
}

void measureBlock() {
  unsigned long now = millis();
  float dt_h = (last_block ? (now - last_block) : BLOCK_MS) / 3600000.0;
  last_block = now;

  last_mv = readMvAvg(SAMPLES_PER_BLOCK);
  float i = (last_mv - zero_mv) / ACS_MV_PER_A;   // dòng DC một chiều
  if (i < I_DEADBAND_A) i = 0;                     // gồm cả giá trị âm do nhiễu
  current_a = i;
  power_w = V_NOMINAL * current_a;

  energy_today_wh += power_w * dt_h;
  energy_total_wh += power_w * dt_h;
  sum_block_p += power_w; n_block++;
}

// -------------------------------------------------------------------------------------
// 7. MÁY TRẠNG THÁI QUẢN LÝ TẢI (chạy mỗi 2 s, KHÔNG phụ thuộc mạng)
// -------------------------------------------------------------------------------------
void controlStep() {
  unsigned long now = millis();

  // Học công suất LED từ bước nhảy công suất sau lần chuyển trạng thái trước
  if (learn_pending && now - led_switch_ms >= TELEMETRY_MS) {
    float delta = fabs(demand_w - p_before_switch);
    if (delta > 0.2) led_est_w = (led_est_w <= 0) ? delta : 0.7 * led_est_w + 0.3 * delta;
    learn_pending = false;
  }

  bool over = demand_w > peak_limit_w;
  bool safe = demand_w < peak_limit_w - hysteresis_w;
  over_since = over ? (over_since ? over_since : now) : 0;
  safe_since = safe ? (safe_since ? safe_since : now) : 0;
  if (demand_w > peak_today_w) peak_today_w = demand_w;

  // Ngày mới -> reset năng lượng ngày, gỡ khóa ngân sách
  long k = todayKey();
  if (k && k != day_key) {
    if (day_key) { energy_today_wh = 0; peak_today_w = 0; budget_warned = false; alarm_budget = false; }
    day_key = k;
    if (led_shed == SHED_BUDGET && (auto_mode || safe_mode)) switchLed(true, SHED_NONE);
  }

  bool managed = auto_mode || safe_mode;

  // --- Ngân sách điện năng ngày ---
  if (budget_wh > 0) {
    if (!budget_warned && energy_today_wh >= 0.8 * budget_wh) { budget_warned = true; publishEvent("BUDGET_WARN", "80% ngan sach ngay"); }
    if (!alarm_budget && energy_today_wh >= budget_wh) { alarm_budget = true; publishEvent("BUDGET_EXCEEDED", "vuot ngan sach ngay"); }
  }
  if (managed && alarm_budget && led_on) {
    switchLed(false, SHED_BUDGET);
    publishEvent("SHED", "LED - vuot ngan sach ngay");
  }

  // --- Sa thải theo đỉnh công suất ---
  if (managed && led_on && over_since && now - over_since >= T_OVER_MS) {
    switchLed(false, SHED_PEAK);
    publishEvent("SHED", "LED - vuot nguong dinh");
  } else if (managed && !led_on && led_shed == SHED_PEAK && !alarm_budget &&
             safe_since && now - safe_since >= T_SAFE_MS &&
             now - led_switch_ms >= MIN_OFF_MS &&
             demand_w + led_est_w < peak_limit_w) {
    switchLed(true, SHED_NONE);
    publishEvent("RESTORE", "LED - dieu kien an toan on dinh");
  }

  // --- Báo động: vẫn vượt ngưỡng dù LED đã tắt (tải ưu tiên cao không bị cắt) ---
  bool should_alarm = over_since && now - over_since >= T_ALARM_MS && !led_on;
  if (should_alarm && !alarm_over) { alarm_over = true; publishEvent("ALARM_OVER_LIMIT", "van vuot nguong sau khi sa thai"); }
  if (!over && alarm_over) { alarm_over = false; publishEvent("ALARM_CLEAR", "cong suat da ve duoi nguong"); }
  buzzer(alarm_over);
}

// -------------------------------------------------------------------------------------
// 8. TELEMETRY
// -------------------------------------------------------------------------------------
void publishTelemetry() {
  seq++;
  StaticJsonDocument<768> d;
  d["dev"] = DEVICE_ID; d["ts"] = epochMs(); d["seq"] = seq;
  d["current_a"] = serialized(String(current_a, 3));
  d["power_w"] = serialized(String(demand_w, 3));      // trung bình 2 s
  d["energy_today_wh"] = serialized(String(energy_today_wh, 4));
  d["energy_total_wh"] = serialized(String(energy_total_wh, 3));
  d["peak_today_w"] = serialized(String(peak_today_w, 3));
  d["fan"] = fan_on; d["led"] = led_on; d["led_shed"] = shedName(led_shed);
  d["auto_mode"] = auto_mode; d["safe_mode"] = safe_mode;
  d["peak_limit_w"] = peak_limit_w; d["hysteresis_w"] = hysteresis_w; d["budget_wh"] = budget_wh;
  d["led_est_w"] = serialized(String(led_est_w, 2));
  d["alarm_over"] = alarm_over; d["alarm_budget"] = alarm_budget;
  d["sensor_mv"] = serialized(String(last_mv, 1)); d["zero_mv"] = serialized(String(zero_mv, 1));
  d["rssi"] = WiFi.RSSI(); d["uptime_s"] = millis() / 1000;
  publishJson(T_TELEMETRY, d);

  Serial.printf("[#%lu] %.1fmV I=%.3fA P=%.2fW E=%.3fWh | FAN:%s LED:%s(%s) | %s%s | MQTT:%s\n",
    seq, last_mv, current_a, demand_w, energy_today_wh, fan_on ? "ON" : "OFF", led_on ? "ON" : "OFF",
    shedName(led_shed), auto_mode ? "AUTO" : "MANUAL", safe_mode ? " SAFE" : "", mqtt.connected() ? "ok" : "down");
}

// -------------------------------------------------------------------------------------
// 9. XỬ LÝ LỆNH  {"cmd_id":"..","ts":..,"fan":true,"led":false,"auto_mode":true,
//                 "peak_limit_w":3.5,"hysteresis_w":0.6,"budget_wh":20,"calibrate":true,"reset_energy":true}
// -------------------------------------------------------------------------------------
void onMqtt(char* topic, byte* payload, unsigned int len) {
  StaticJsonDocument<512> in;
  // ép kiểu const -> ArduinoJson COPY chuỗi, an toàn khi publish lại buffer bên trong callback
  if (deserializeJson(in, (const char*)payload, len)) return;

  char cmd_id[40] = "";
  strlcpy(cmd_id, in["cmd_id"] | "", sizeof(cmd_id));
  uint64_t t_cmd = in["ts"] | (uint64_t)0;
  bool ok = true; String err = "";

  if (in["fan"].is<bool>() || in["led"].is<bool>()) {
    if (auto_mode) { auto_mode = false; publishEvent("MANUAL_OVERRIDE", "lenh tay -> chuyen MANUAL"); }
    if (in["fan"].is<bool>()) { fan_on = in["fan"]; setRelay(PIN_RELAY_FAN, fan_on); }
    if (in["led"].is<bool>()) switchLed(in["led"].as<bool>(), SHED_NONE);
  }
  if (in["auto_mode"].is<bool>()) auto_mode = in["auto_mode"];
  if (!in["peak_limit_w"].isNull()) {
    float v = in["peak_limit_w"]; if (v >= 0.5 && v <= 60) peak_limit_w = v; else { ok = false; err += "peak_limit_w ngoai [0.5,60]; "; }
  }
  if (!in["hysteresis_w"].isNull()) {
    float v = in["hysteresis_w"]; if (v >= 0.1 && v <= 10) hysteresis_w = v; else { ok = false; err += "hysteresis_w ngoai [0.1,10]; "; }
  }
  if (!in["budget_wh"].isNull()) {
    float v = in["budget_wh"]; if (v >= 0 && v <= 10000) { budget_wh = v; alarm_budget = false; budget_warned = false; }
    else { ok = false; err += "budget_wh ngoai [0,10000]; "; }
  }
  if (in["reset_energy"] == true) { energy_today_wh = 0; peak_today_w = 0; alarm_budget = false; budget_warned = false; }
  if (in["calibrate"] == true) {
    if (fan_on || led_on) { ok = false; err += "tat ca 2 tai truoc khi calib; "; } else calibrateZero();
  }

  prefs.putFloat("limit", peak_limit_w); prefs.putFloat("hyst", hysteresis_w);
  prefs.putFloat("budget", budget_wh);   prefs.putBool("auto", auto_mode);

  StaticJsonDocument<512> ack;
  ack["cmd_id"] = cmd_id; ack["cmd_ts"] = t_cmd; ack["ok"] = ok;
  if (!ok) ack["error"] = err;
  fillState(ack);                          // trạng thái THỰC TẾ sau khi áp dụng
  publishJson(T_ACK, ack);
  publishState();
  Serial.printf("[CMD] id=%s ok=%d %s\n", cmd_id, ok, err.c_str());
}

// -------------------------------------------------------------------------------------
// 10. KẾT NỐI KHÔNG CHẶN
// -------------------------------------------------------------------------------------
void networkTask() {
  unsigned long now = millis();

  if (WiFi.status() != WL_CONNECTED) {
    if (now - last_wifi_try > 15000) { last_wifi_try = now; WiFi.disconnect(); WiFi.begin(WIFI_SSID, WIFI_PASSWORD); Serial.println("[NET] WiFi reconnect..."); }
  } else if (!mqtt.connected()) {
    if (now - last_mqtt_try > 5000) {
      last_mqtt_try = now;
      bool auth = strlen(MQTT_USER) > 0;
      bool c = mqtt.connect(client_id.c_str(), auth ? MQTT_USER : nullptr, auth ? MQTT_PASS : nullptr,
                            T_STATUS, 1, true, "offline");
      if (c) {
        mqtt.publish(T_STATUS, "online", true);
        mqtt.subscribe(T_CMD, 1);
        if (safe_mode) {
          char buf[64]; snprintf(buf, sizeof(buf), "mat ket noi %lus", (now - mqtt_lost_ms) / 1000);
          safe_mode = false; publishEvent("RECOVERED", buf);
        }
        mqtt_lost_ms = 0;
        publishState();
        Serial.println("[NET] MQTT connected");
      } else {
        Serial.printf("[NET] MQTT fail rc=%d\n", mqtt.state());
      }
    }
  }

  if (mqtt.connected()) mqtt.loop();
  else {
    if (!mqtt_lost_ms) mqtt_lost_ms = now ? now : 1;
    if (!safe_mode && now - mqtt_lost_ms > OFFLINE_SAFE_MS) {
      safe_mode = true;
      Serial.println("[SAFE] Mat broker > 30s -> bat quan ly tai cuc bo");
    }
  }
}

// -------------------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(500);
  pinMode(PIN_RELAY_FAN, OUTPUT); setRelay(PIN_RELAY_FAN, false);
  pinMode(PIN_RELAY_LED, OUTPUT); setRelay(PIN_RELAY_LED, false);
  if (PIN_BUZZER >= 0) { pinMode(PIN_BUZZER, OUTPUT); buzzer(false); }

  analogReadResolution(12);
  analogSetPinAttenuation(PIN_ACS712, ADC_11db);

  prefs.begin("energy", false);
  peak_limit_w    = prefs.getFloat("limit", peak_limit_w);
  hysteresis_w    = prefs.getFloat("hyst", hysteresis_w);
  budget_wh       = prefs.getFloat("budget", budget_wh);
  auto_mode       = prefs.getBool("auto", auto_mode);
  energy_today_wh = prefs.getDouble("e_today", 0);
  energy_total_wh = prefs.getDouble("e_total", 0);
  day_key         = prefs.getLong("day", 0);

  Serial.println("\n=== SMART ENERGY v17 === Giu 2 tai TAT de calib diem 0...");
  calibrateZero();

  uint64_t mac = ESP.getEfuseMac();
  client_id = String("SE_") + DEVICE_ID + "_" + String((uint32_t)(mac & 0xFFFFFFFF), HEX);

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  last_wifi_try = millis();
  configTime(7 * 3600, 0, "pool.ntp.org", "time.google.com");   // GMT+7

  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  mqtt.setBufferSize(1024);
  mqtt.setKeepAlive(15);
  mqtt.setSocketTimeout(3);
  mqtt.setCallback(onMqtt);
}

void loop() {
  unsigned long now = millis();

  if (now - last_block >= BLOCK_MS) measureBlock();

  if (now - last_tele >= TELEMETRY_MS) {
    last_tele = now;
    demand_w = n_block ? sum_block_p / n_block : 0;
    sum_block_p = 0; n_block = 0;
    controlStep();        // điều khiển cục bộ TRƯỚC, mạng SAU
    publishTelemetry();
  }

  if (now - last_save >= SAVE_MS) {
    last_save = now;
    prefs.putDouble("e_today", energy_today_wh);
    prefs.putDouble("e_total", energy_total_wh);
    prefs.putLong("day", day_key);
  }

  networkTask();
}
