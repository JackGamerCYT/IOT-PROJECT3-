"""
Giả lập ESP32 (cùng topic/JSON với firmware v17) để test backend + dashboard khi chưa cắm phần cứng.
    python tools/device_simulator.py [--host broker.hivemq.com] [--port 1883]
Quạt ~2.4 W, LED ~1.8 W. Có sa thải tải đơn giản (T_OVER 4 s, T_SAFE 15 s, MIN_OFF 20 s).
"""
import argparse, json, random, time
import paho.mqtt.client as mqtt

ap = argparse.ArgumentParser()
ap.add_argument("--host", default="broker.hivemq.com")
ap.add_argument("--port", type=int, default=1883)
ap.add_argument("--dev", default="node9988")
a = ap.parse_args()
B = f"smartenergy/{a.dev}"
now_ms = lambda: int(time.time() * 1000)

s = dict(fan=False, led=False, led_shed="NONE", auto_mode=False, safe_mode=False,
         peak_limit_w=3.0, hysteresis_w=0.5, budget_wh=0.0)
e_today = e_total = peak = 0.0
seq, over_since, safe_since, led_switch, led_est = 0, 0, 0, 0, 0.0
P_FAN, P_LED = 2.4, 1.8


def state():
    return {"dev": a.dev, "ts": now_ms(), **s}


def event(t, detail, p):
    c.publish(f"{B}/event", json.dumps({"dev": a.dev, "ts": now_ms(), "type": t, "detail": detail,
                                        "power_w": p, "limit_w": s["peak_limit_w"], "energy_today_wh": e_today}), qos=1)


def on_connect(cl, u, f, rc, p):
    cl.publish(f"{B}/status", "online", qos=1, retain=True)
    cl.subscribe(f"{B}/cmd", qos=1)
    cl.publish(f"{B}/state", json.dumps(state()), retain=True)
    print("connected", rc)


def on_message(cl, u, m):
    global e_today, peak, led_switch
    d = json.loads(m.payload)
    time.sleep(random.uniform(0.02, 0.08))  # thời gian xử lý giả lập
    ok, err = True, ""
    if "fan" in d or "led" in d:
        if s["auto_mode"]:
            s["auto_mode"] = False
            event("MANUAL_OVERRIDE", "lenh tay -> chuyen MANUAL", 0)
        if "fan" in d: s["fan"] = bool(d["fan"])
        if "led" in d:
            s["led"] = bool(d["led"]); s["led_shed"] = "NONE"; led_switch = time.time()
    if "auto_mode" in d: s["auto_mode"] = bool(d["auto_mode"])
    for k, lo, hi in (("peak_limit_w", .5, 60), ("hysteresis_w", .1, 10), ("budget_wh", 0, 10000)):
        if k in d:
            if lo <= float(d[k]) <= hi: s[k] = float(d[k])
            else: ok, err = False, err + f"{k} ngoai [{lo},{hi}]; "
    if d.get("reset_energy"): e_today = peak = 0
    if d.get("calibrate") and (s["fan"] or s["led"]): ok, err = False, "tat ca 2 tai truoc khi calib; "
    ack = {"cmd_id": d.get("cmd_id", ""), "cmd_ts": d.get("ts", 0), "ok": ok, **state()}
    if not ok: ack["error"] = err
    cl.publish(f"{B}/ack", json.dumps(ack), qos=1)
    cl.publish(f"{B}/state", json.dumps(state()), retain=True)


c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"sim_{a.dev}_{random.randint(0, 9999)}")
c.will_set(f"{B}/status", "offline", qos=1, retain=True)
c.on_connect, c.on_message = on_connect, on_message
c.connect(a.host, a.port, 15)
c.loop_start()

while True:
    time.sleep(2)
    t = time.time()
    p = (P_FAN if s["fan"] else 0) + (P_LED if s["led"] else 0)
    p = max(0.0, p + random.gauss(0, 0.05)) if p else max(0.0, random.gauss(0, 0.02))
    p = 0.0 if p < 0.48 else p
    e_today += p * 2 / 3600; e_total += p * 2 / 3600; peak = max(peak, p)
    L, H = s["peak_limit_w"], s["hysteresis_w"]
    over_since = (over_since or t) if p > L else 0
    safe_since = (safe_since or t) if p < L - H else 0
    if s["auto_mode"]:
        if s["led"] and over_since and t - over_since >= 4:
            s.update(led=False, led_shed="PEAK"); led_switch = t; led_est = P_LED
            event("SHED", "LED - vuot nguong dinh", p)
        elif (not s["led"] and s["led_shed"] == "PEAK" and safe_since and t - safe_since >= 15
              and t - led_switch >= 20 and p + led_est < L):
            s.update(led=True, led_shed="NONE"); led_switch = t
            event("RESTORE", "LED - dieu kien an toan on dinh", p)
    seq += 1
    i = p / 12
    c.publish(f"{B}/telemetry", json.dumps({
        "dev": a.dev, "ts": now_ms(), "seq": seq, "current_a": round(i, 3), "power_w": round(p, 3),
        "energy_today_wh": round(e_today, 4), "energy_total_wh": round(e_total, 3), "peak_today_w": round(peak, 3),
        **{k: s[k] for k in ("fan", "led", "led_shed", "auto_mode", "safe_mode", "peak_limit_w", "hysteresis_w", "budget_wh")},
        "led_est_w": led_est, "alarm_over": False, "alarm_budget": False,
        "sensor_mv": round(2500 + i * 185, 1), "zero_mv": 2500.0, "rssi": -55, "uptime_s": seq * 2,
        "time_src": "ntp", "rtc": True, "buffered_count": 0}))
    print(f"#{seq} P={p:.2f}W fan={s['fan']} led={s['led']} auto={s['auto_mode']}")
