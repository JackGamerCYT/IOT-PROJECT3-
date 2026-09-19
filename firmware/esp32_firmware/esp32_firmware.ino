/*
 * =====================================================================================
 *  PROJECT 03 - SMART ENERGY MONITORING & INTELLIGENT LOAD MANAGEMENT
 *  Firmware v19 - ESP32-S3 (N16R8)
 *
 *  v19 thêm so với v17/v18:
 *   - DS3231 (I2C): giữ giờ khi mất WiFi; NTP -> RTC khi online, RTC -> hệ thống khi offline
 *   - SSD1306 OLED 128x64 (I2C): hiện giờ, công suất, điện năng, trạng thái tải, mạng
 *   - Bộ đệm vòng 600 bản ghi (~20 phút): mất broker thì lưu lại, có mạng gửi bù
 *     (gói gửi bù có "buffered":true, backend dùng ts thiết bị làm mốc thời gian)
 *
 *  Thư viện cần cài (Library Manager):
 *    PubSubClient · ArduinoJson · RTClib · Adafruit SSD1306 · Adafruit GFX Library
 *  Không lắp module nào thì đặt USE_RTC / USE_OLED = 0, firmware vẫn chạy đầy đủ.
 * =====================================================================================
 */

#define ARDUINOJSON_USE_LONG_LONG 1
#define USE_RTC  1
#define USE_OLED 1

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <time.h>
#include <sys/time.h>
#if USE_RTC || USE_OLED
  #include <Wire.h>
#endif
#if USE_RTC
  #include <RTClib.h>
#endif
#if USE_OLED
  #include <Adafruit_GFX.h>
  #include <Adafruit_SSD1306.h>
#endif

// -------------------------------------------------------------------------------------
// 1. BÍ MẬT (tạo secrets.h cạnh file .ino, KHÔNG commit)
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

const char* T_TELEMETRY = "smartenergy/node9988/telemetry";
const char* T_STATUS    = "smartenergy/node9988/status";
const char* T_STATE     = "smartenergy/node9988/state";
const char* T_EVENT     = "smartenergy/node9988/event";
const char* T_CMD       = "smartenergy/node9988/cmd";
const char* T_ACK       = "smartenergy/node9988/ack";

// -------------------------------------------------------------------------------------
// 3. PHẦN CỨNG
// -------------------------------------------------------------------------------------
const int PIN_ACS712    = 1;    // ADC1_CH0, nên qua cầu phân áp 10k/20k
const int PIN_RELAY_FAN = 12;   // Tải 1 - Quạt 12V (ưu tiên CAO), relay active LOW
const int PIN_RELAY_LED = 13;   // Tải 2 - LED 12V  (ưu tiên THẤP), relay active LOW
const int PIN_BUZZER    = 14;   // -1 nếu không lắp
const int PIN_I2C_SDA   = 8;    // DS3231 + SSD1306 dùng chung
const int PIN_I2C_SCL   = 9;
const uint8_t ADDR_OLED = 0x3C;

const float ACS_MV_PER_A  = 185.0;
const float DIVIDER_RATIO = 1.0;    // 0.6667 nếu dùng phân áp 10k (trên) / 20k (dưới)
const float V_NOMINAL     = 12.0;
const float I_DEADBAND_A  = 0.04;

// -------------------------------------------------------------------------------------
// 4. THÔNG SỐ ĐO / ĐIỀU KHIỂN
// -------------------------------------------------------------------------------------
const unsigned long BLOCK_MS          = 250;
const int           SAMPLES_PER_BLOCK = 64;
const unsigned long TELEMETRY_MS      = 2000;
const unsigned long T_OVER_MS         = 4000;
const unsigned long T_SAFE_MS         = 15000;
const unsigned long MIN_OFF_MS        = 20000;
const unsigned long T_ALARM_MS        = 10000;
const unsigned long OFFLINE_SAFE_MS   = 30000;
const unsigned long SAVE_MS           = 60000;
const unsigned long OLED_MS           = 500;
const int           BUF_SIZE          = 600;    // ~20 phút dữ liệu đệm

float peak_limit_w = 3.0;
float hysteresis_w = 0.5;
float budget_wh    = 0.0;
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
float current_a = 0, power_w = 0, demand_w = 0;
double sum_block_p = 0; int n_block = 0;
double energy_today_wh = 0, energy_total_wh = 0;
float  peak_today_w = 0;
long   day_key = 0;

unsigned long over_since = 0, safe_since = 0;
float led_est_w = 0, p_before_switch = -1;
bool learn_pending = false;
bool alarm_over = false, alarm_budget = false, budget_warned = false;

bool safe_mode = false;
unsigned long mqtt_lost_ms = 0;
unsigned long last_block = 0, last_tele = 0, last_save = 0, last_mqtt_try = 0,
              last_wifi_try = 0, last_oled = 0, last_flush = 0;
unsigned long seq = 0;

// Bộ đệm vòng khi mất kết nối
struct Rec { uint32_t ts; float i, p, e; uint8_t flags; };
Rec buf[BUF_SIZE];
int buf_head = 0, buf_count = 0;

bool have_rtc = false, have_oled = false;
const char* time_src = "none";

WiFiClient net;
PubSubClient mqtt(net);
Preferences prefs;
String client_id;
#if USE_RTC
  RTC_DS3231 rtc;
#endif
#if USE_OLED
  Adafruit_SSD1306 oled(128, 64, &Wire, -1);
#endif

// -------------------------------------------------------------------------------------
uint64_t epochMs() {
  struct timeval tv; gettimeofday(&tv, nullptr);
  if (tv.tv_sec < 1700000000) return 0;
  return (uint64_t)tv.tv_sec * 1000ULL + tv.tv_usec / 1000;
}
uint32_t epochS() { time_t t = time(nullptr); return t > 1700000000 ? (uint32_t)t : 0; }

long todayKey() {
  time_t now = time(nullptr); if (now < 1700000000) return 0;
  struct tm t; localtime_r(&now, &t);
  return (t.tm_year + 1900) * 10000L + (t.tm_mon + 1) * 100L + t.tm_mday;
}
void clockStr(char* out, size_t n) {
  time_t now = time(nullptr);
  if (now < 1700000000) { snprintf(out, n, "--:--:--"); return; }
  struct tm t; localtime_r(&now, &t);
  snprintf(out, n, "%02d:%02d:%02d", t.tm_hour, t.tm_min, t.tm_sec);
}

void setRelay(int pin, bool on) { digitalWrite(pin, on ? LOW : HIGH); }
void buzzer(bool on) { if (PIN_BUZZER >= 0) digitalWrite(PIN_BUZZER, on ? HIGH : LOW); }

void publishJson(const char* topic, JsonDocument& doc, bool retained = false) {
  if (!mqtt.connected()) return;
  char b[768];
  size_t n = serializeJson(doc, b, sizeof(b));
  mqtt.publish(topic, (const uint8_t*)b, n, retained);
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
// 6. ĐỒNG HỒ THỜI GIAN THỰC
// -------------------------------------------------------------------------------------
void initRTC() {
#if USE_RTC
  if (!rtc.begin(&Wire)) { Serial.println("[RTC] khong tim thay DS3231"); return; }
  have_rtc = true;
  if (rtc.lostPower()) Serial.println("[RTC] mat nguon, gio chua dung - se chinh lai khi co NTP");
  DateTime n = rtc.now();
  if (n.unixtime() > 1700000000) {   // lấy giờ RTC làm giờ hệ thống ngay khi khởi động
    struct timeval tv; tv.tv_sec = (time_t)n.unixtime(); tv.tv_usec = 0;
    settimeofday(&tv, nullptr);
    time_src = "rtc";
    Serial.printf("[RTC] gio tu DS3231: %04d-%02d-%02d %02d:%02d:%02d\n",
                  n.year(), n.month(), n.day(), n.hour(), n.minute(), n.second());
  }
#endif
}

void syncRtcFromNtp() {
#if USE_RTC
  if (!have_rtc) return;
  uint32_t s = epochS();
  if (!s) return;
  DateTime cur = rtc.now();
  long diff = (long)cur.unixtime() - (long)s;
  if (diff > 2 || diff < -2) {                     // lệch quá 2 s mới ghi lại
    rtc.adjust(DateTime(s));
    Serial.println("[RTC] da dong bo DS3231 theo NTP");
  }
#endif
}

// -------------------------------------------------------------------------------------
// 7. OLED
// -------------------------------------------------------------------------------------
void initOLED() {
#if USE_OLED
  if (!oled.begin(SSD1306_SWITCHCAPVCC, ADDR_OLED)) { Serial.println("[OLED] khong tim thay SSD1306"); return; }
  have_oled = true;
  oled.clearDisplay(); oled.setTextColor(SSD1306_WHITE); oled.setTextSize(1);
  oled.setCursor(0, 24); oled.println(" SMART ENERGY v19"); oled.display();
#endif
}

void drawOLED() {
#if USE_OLED
  if (!have_oled) return;
  char t[16]; clockStr(t, sizeof(t));
  oled.clearDisplay();

  oled.setTextSize(1); oled.setCursor(0, 0); oled.print(t);
  oled.setCursor(70, 0);
  oled.print(WiFi.status() == WL_CONNECTED ? "W" : "-");
  oled.print(mqtt.connected() ? "M" : "-");
  if (buf_count) { oled.print(" B"); oled.print(buf_count); }
  else { oled.print(auto_mode ? " AUT" : " MAN"); }

  oled.drawFastHLine(0, 10, 128, SSD1306_WHITE);

  oled.setTextSize(2); oled.setCursor(0, 15);
  oled.print(demand_w, 2); oled.setTextSize(1); oled.print(" W");

  oled.setCursor(0, 34);
  oled.print(current_a, 3); oled.print("A  ");
  oled.print(energy_today_wh, 2); oled.print("Wh");

  oled.setCursor(0, 45);
  oled.print("Lim "); oled.print(peak_limit_w, 1); oled.print("W");
  if (alarm_over)       oled.print(" !OVER");
  else if (alarm_budget) oled.print(" !BUDG");
  else if (safe_mode)    oled.print(" SAFE");

  oled.setCursor(0, 56);
  oled.print("FAN:"); oled.print(fan_on ? "ON " : "OFF");
  oled.print(" LED:"); oled.print(led_on ? "ON" : "OFF");
  if (!led_on && led_shed != SHED_NONE) { oled.print("/"); oled.print(shedName(led_shed)); }
  oled.display();
#endif
}

// -------------------------------------------------------------------------------------
// 8. ĐO LƯỜNG
// -------------------------------------------------------------------------------------
float readMvAvg(int n) {
  uint32_t s = 0;
  for (int i = 0; i < n; i++) s += analogReadMilliVolts(PIN_ACS712);
  return (float)s / n / DIVIDER_RATIO;
}

void calibrateZero() {
  float s = 0;
  for (int i = 0; i < 20; i++) { s += readMvAvg(50); delay(10); }
  zero_mv = s / 20.0;
  Serial.printf("[CAL] zero = %.1f mV (ly thuyet ~2500 mV khi VCC = 5.0 V)\n", zero_mv);
}

void measureBlock() {
  unsigned long now = millis();
  float dt_h = (last_block ? (now - last_block) : BLOCK_MS) / 3600000.0;
  last_block = now;

  last_mv = readMvAvg(SAMPLES_PER_BLOCK);
  float i = (last_mv - zero_mv) / ACS_MV_PER_A;
  if (i < I_DEADBAND_A) i = 0;
  current_a = i;
  power_w = V_NOMINAL * current_a;

  energy_today_wh += power_w * dt_h;
  energy_total_wh += power_w * dt_h;
  sum_block_p += power_w; n_block++;
}

// -------------------------------------------------------------------------------------
// 9. MÁY TRẠNG THÁI QUẢN LÝ TẢI (chạy cả khi mất mạng)
// -------------------------------------------------------------------------------------
void controlStep() {
  unsigned long now = millis();

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

  long k = todayKey();
  if (k && k != day_key) {
    if (day_key) { energy_today_wh = 0; peak_today_w = 0; budget_warned = false; alarm_budget = false; }
    day_key = k;
    if (led_shed == SHED_BUDGET && (auto_mode || safe_mode)) switchLed(true, SHED_NONE);
  }

  bool managed = auto_mode || safe_mode;

  if (budget_wh > 0) {
    if (!budget_warned && energy_today_wh >= 0.8 * budget_wh) { budget_warned = true; publishEvent("BUDGET_WARN", "80% ngan sach ngay"); }
    if (!alarm_budget && energy_today_wh >= budget_wh) { alarm_budget = true; publishEvent("BUDGET_EXCEEDED", "vuot ngan sach ngay"); }
  }
  if (managed && alarm_budget && led_on) {
    switchLed(false, SHED_BUDGET);
    publishEvent("SHED", "LED - vuot ngan sach ngay");
  }

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

  bool should_alarm = over_since && now - over_since >= T_ALARM_MS && !led_on;
  if (should_alarm && !alarm_over) { alarm_over = true; publishEvent("ALARM_OVER_LIMIT", "van vuot nguong sau khi sa thai"); }
  if (!over && alarm_over) { alarm_over = false; publishEvent("ALARM_CLEAR", "cong suat da ve duoi nguong"); }
  buzzer(alarm_over);
}

// -------------------------------------------------------------------------------------
// 10. TELEMETRY + BỘ ĐỆM OFFLINE
// -------------------------------------------------------------------------------------
void bufferPush() {
  uint32_t ts = epochS();
  if (!ts) return;                       // không có mốc thời gian đáng tin thì không đệm
  buf[buf_head] = { ts, current_a, demand_w, (float)energy_today_wh,
                    (uint8_t)((fan_on ? 1 : 0) | (led_on ? 2 : 0) | (auto_mode ? 4 : 0) | (safe_mode ? 8 : 0)) };
  buf_head = (buf_head + 1) % BUF_SIZE;
  if (buf_count < BUF_SIZE) buf_count++;
}

void bufferFlush(int max_msgs) {
  while (buf_count > 0 && max_msgs-- > 0 && mqtt.connected()) {
    int idx = (buf_head - buf_count + BUF_SIZE) % BUF_SIZE;
    Rec& r = buf[idx];
    StaticJsonDocument<384> d;
    d["dev"] = DEVICE_ID; d["ts"] = (uint64_t)r.ts * 1000ULL; d["buffered"] = true;
    d["current_a"] = serialized(String(r.i, 3));
    d["power_w"] = serialized(String(r.p, 3));
    d["energy_today_wh"] = serialized(String(r.e, 4));
    d["fan"] = (bool)(r.flags & 1); d["led"] = (bool)(r.flags & 2);
    d["auto_mode"] = (bool)(r.flags & 4); d["safe_mode"] = (bool)(r.flags & 8);
    d["peak_limit_w"] = peak_limit_w;
    publishJson(T_TELEMETRY, d);
    buf_count--;
  }
}

void publishTelemetry() {
  seq++;
  StaticJsonDocument<768> d;
  d["dev"] = DEVICE_ID; d["ts"] = epochMs(); d["seq"] = seq;
  d["current_a"] = serialized(String(current_a, 3));
  d["power_w"] = serialized(String(demand_w, 3));
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
  d["time_src"] = time_src; d["rtc"] = have_rtc; d["buffered_count"] = buf_count;
  publishJson(T_TELEMETRY, d);

  char t[16]; clockStr(t, sizeof(t));
  Serial.printf("[#%lu %s] %.1fmV I=%.3fA P=%.2fW E=%.3fWh | FAN:%s LED:%s(%s) | %s%s | MQTT:%s buf=%d\n",
    seq, t, last_mv, current_a, demand_w, energy_today_wh, fan_on ? "ON" : "OFF", led_on ? "ON" : "OFF",
    shedName(led_shed), auto_mode ? "AUTO" : "MANUAL", safe_mode ? " SAFE" : "",
    mqtt.connected() ? "ok" : "down", buf_count);
}

// -------------------------------------------------------------------------------------
// 11. XỬ LÝ LỆNH
// -------------------------------------------------------------------------------------
void onMqtt(char* topic, byte* payload, unsigned int len) {
  StaticJsonDocument<512> in;
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
  fillState(ack);
  publishJson(T_ACK, ack);
  publishState();
  Serial.printf("[CMD] id=%s ok=%d %s\n", cmd_id, ok, err.c_str());
}

// -------------------------------------------------------------------------------------
// 12. MẠNG (không chặn)
// -------------------------------------------------------------------------------------
void networkTask() {
  unsigned long now = millis();

  if (WiFi.status() != WL_CONNECTED) {
    if (now - last_wifi_try > 15000) {
      last_wifi_try = now; WiFi.disconnect(); WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
      Serial.println("[NET] WiFi reconnect...");
    }
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
          char b[80];
          snprintf(b, sizeof(b), "mat ket noi %lus, gui bu %d goi", (now - mqtt_lost_ms) / 1000, buf_count);
          safe_mode = false; publishEvent("RECOVERED", b);
        }
        mqtt_lost_ms = 0;
        publishState();
        Serial.printf("[NET] MQTT connected (buf=%d)\n", buf_count);
      } else {
        Serial.printf("[NET] MQTT fail rc=%d\n", mqtt.state());
      }
    }
  }

  if (mqtt.connected()) {
    mqtt.loop();
    if (buf_count && now - last_flush > 200) { last_flush = now; bufferFlush(5); }   // gửi bù từ từ
  } else {
    if (!mqtt_lost_ms) mqtt_lost_ms = now ? now : 1;
    if (!safe_mode && now - mqtt_lost_ms > OFFLINE_SAFE_MS) {
      safe_mode = true;
      Serial.println("[SAFE] Mat broker > 30s -> quan ly tai cuc bo, bat dau dem du lieu");
    }
  }

  // NTP -> RTC mỗi 10 phút khi online
  static unsigned long last_sync = 0;
  if (WiFi.status() == WL_CONNECTED && epochS() && (!last_sync || now - last_sync > 600000)) {
    last_sync = now; time_src = "ntp"; syncRtcFromNtp();
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

#if USE_RTC || USE_OLED
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
  Wire.setClock(400000);
  initRTC();
  initOLED();
#endif

  prefs.begin("energy", false);
  peak_limit_w    = prefs.getFloat("limit", peak_limit_w);
  hysteresis_w    = prefs.getFloat("hyst", hysteresis_w);
  budget_wh       = prefs.getFloat("budget", budget_wh);
  auto_mode       = prefs.getBool("auto", auto_mode);
  energy_today_wh = prefs.getDouble("e_today", 0);
  energy_total_wh = prefs.getDouble("e_total", 0);
  day_key         = prefs.getLong("day", 0);

  Serial.println("\n=== SMART ENERGY v19 === Giu 2 tai TAT de calib diem 0...");
  calibrateZero();

  uint64_t mac = ESP.getEfuseMac();
  client_id = String("SE_") + DEVICE_ID + "_" + String((uint32_t)(mac & 0xFFFFFFFF), HEX);

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  last_wifi_try = millis();
  configTime(7 * 3600, 0, "pool.ntp.org", "time.google.com");

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
    controlStep();                       // điều khiển cục bộ trước
    if (mqtt.connected()) publishTelemetry();
    else bufferPush();                   // mất mạng: đệm lại để gửi bù
  }

  if (now - last_oled >= OLED_MS) { last_oled = now; drawOLED(); }

  if (now - last_save >= SAVE_MS) {
    last_save = now;
    prefs.putDouble("e_today", energy_today_wh);
    prefs.putDouble("e_total", energy_total_wh);
    prefs.putLong("day", day_key);
  }

  networkTask();
}
