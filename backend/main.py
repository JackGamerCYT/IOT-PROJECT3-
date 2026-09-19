"""
Project 03 - Smart Energy Monitoring & Intelligent Load Management
Backend: FastAPI + MQTT ingest + time-series DB (SQLite hoặc PostgreSQL/Neon)

Chọn CSDL bằng biến môi trường DATABASE_URL:
  - không đặt            -> SQLite file backend/energy_data.db  (chạy trên laptop)
  - postgresql://...     -> PostgreSQL / Neon                   (chạy 24/7 trên Render)

Chạy:  pip install -r requirements.txt && python main.py   ->  http://localhost:8000
"""
import csv
import io
import json
import os
import sqlite3
import threading
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional

import paho.mqtt.client as mqtt
import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

# ----------------------------------------------------------------------------------
# Cấu hình
# ----------------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.getenv("DATABASE_URL", "")
DB_FILE = os.getenv("DB_FILE", os.path.join(BASE_DIR, "energy_data.db"))
DASHBOARD = os.path.join(BASE_DIR, "..", "dashboard", "index.html")

MQTT_HOST = os.getenv("MQTT_HOST", "broker.hivemq.com")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASS = os.getenv("MQTT_PASS", "")
DEVICE_ID = os.getenv("DEVICE_ID", "node9988")
BASE = f"smartenergy/{DEVICE_ID}"
TOPICS = {k: f"{BASE}/{k}" for k in ("telemetry", "status", "state", "event", "cmd", "ack")}

API_KEY = os.getenv("API_KEY", "")   # đặt khi deploy công khai: mọi POST/PUT phải có header X-API-Key
TZ = timezone(timedelta(hours=int(os.getenv("TZ_OFFSET_H", "7"))))
RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "60"))   # dọn dữ liệu cũ (Neon free 0.5 GB)
STALE_S = 6.0
HTTP_PORT = int(os.getenv("PORT", "8000"))

now_ms = lambda: int(time.time() * 1000)


# ----------------------------------------------------------------------------------
# Lớp CSDL dùng chung cho SQLite và PostgreSQL
# ----------------------------------------------------------------------------------
class DB:
    def __init__(self, url: str, sqlite_path: str):
        self.pg = url.startswith(("postgres://", "postgresql://"))
        if self.pg:
            import psycopg
            from psycopg.rows import dict_row
            from psycopg_pool import ConnectionPool
            self.pool = ConnectionPool(url, min_size=1, max_size=5, timeout=15,
                                       kwargs={"row_factory": dict_row, "autocommit": True})
            self.pool.wait(timeout=30)
            print(f"[DB] PostgreSQL: {url.split('@')[-1].split('?')[0]}")
        else:
            self.conn = sqlite3.connect(sqlite_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.lock = threading.Lock()
            print(f"[DB] SQLite: {sqlite_path}")

    def _sql(self, sql: str) -> str:
        return sql.replace("?", "%s") if self.pg else sql

    def query(self, sql, args=(), one=False):
        if self.pg:
            with self.pool.connection() as c:
                rows = c.execute(self._sql(sql), args).fetchall()
        else:
            with self.lock:
                rows = [dict(r) for r in self.conn.execute(sql, args).fetchall()]
        return (rows[0] if rows else None) if one else rows

    def execute(self, sql, args=()):
        if self.pg:
            with self.pool.connection() as c:
                c.execute(self._sql(sql), args)
        else:
            with self.lock:
                self.conn.execute(sql, args)
                self.conn.commit()

    def insert_ignore(self, table, cols, args, key):
        ph = ",".join("?" * len(cols))
        tail = f" ON CONFLICT ({key}) DO NOTHING" if self.pg else ""
        head = "INSERT INTO" if self.pg else "INSERT OR IGNORE INTO"
        self.execute(f"{head} {table}({','.join(cols)}) VALUES({ph}){tail}", args)

    def upsert_setting(self, key, value):
        if self.pg:
            self.execute("INSERT INTO settings VALUES(?,?) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (key, value))
        else:
            self.execute("INSERT OR REPLACE INTO settings VALUES(?,?)", (key, value))

    def init_schema(self):
        T = {"PK": "BIGSERIAL PRIMARY KEY", "INT": "BIGINT", "REAL": "DOUBLE PRECISION"} if self.pg else \
            {"PK": "INTEGER PRIMARY KEY AUTOINCREMENT", "INT": "INTEGER", "REAL": "REAL"}
        stmts = [
            f"""CREATE TABLE IF NOT EXISTS telemetry (
                id {T['PK']}, dev TEXT, ts_device {T['INT']}, ts_server {T['INT']} NOT NULL, seq {T['INT']},
                current_a {T['REAL']}, power_w {T['REAL']}, energy_today_wh {T['REAL']}, energy_total_wh {T['REAL']},
                peak_today_w {T['REAL']}, fan {T['INT']}, led {T['INT']}, led_shed TEXT, auto_mode {T['INT']},
                safe_mode {T['INT']}, peak_limit_w {T['REAL']}, hysteresis_w {T['REAL']}, budget_wh {T['REAL']},
                alarm_over {T['INT']}, alarm_budget {T['INT']}, sensor_mv {T['REAL']}, rssi {T['INT']})""",
            "CREATE INDEX IF NOT EXISTS idx_tel_ts ON telemetry(ts_server)",
            f"""CREATE TABLE IF NOT EXISTS events (
                id {T['PK']}, dev TEXT, ts_device {T['INT']}, ts_server {T['INT']} NOT NULL,
                type TEXT, detail TEXT, power_w {T['REAL']}, limit_w {T['REAL']})""",
            "CREATE INDEX IF NOT EXISTS idx_evt_ts ON events(ts_server)",
            f"CREATE TABLE IF NOT EXISTS availability (id {T['PK']}, ts_server {T['INT']} NOT NULL, status TEXT)",
            f"""CREATE TABLE IF NOT EXISTS commands (
                cmd_id TEXT PRIMARY KEY, dev TEXT, source TEXT, payload TEXT, ts_client {T['INT']},
                ts_seen_server {T['INT']}, ts_ack_server {T['INT']}, ack_ok {T['INT']}, ack_error TEXT,
                ack_state TEXT, latency_ms {T['INT']})""",
            "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)",
        ]
        for s in stmts:
            self.execute(s)
        self.insert_ignore("settings", ["key", "value"], ("tariff_vnd_per_kwh", "3000"), "key")

    def purge(self, days: int):
        cut = now_ms() - days * 86_400_000
        for t in ("telemetry", "events", "availability"):
            self.execute(f"DELETE FROM {t} WHERE ts_server < ?", (cut,))
        self.execute("DELETE FROM commands WHERE COALESCE(ts_seen_server, ts_client) < ?", (cut,))


db = DB(DATABASE_URL, DB_FILE)
db.init_schema()
q, exec_ = db.query, db.execute


def get_setting(key, default=None):
    r = q("SELECT value FROM settings WHERE key=?", (key,), one=True)
    return r["value"] if r else default


# ----------------------------------------------------------------------------------
# MQTT ingest
# ----------------------------------------------------------------------------------
live = {"status": "unknown", "status_ts": 0, "state": None, "mqtt_connected": False}
ack_waiters: dict[str, threading.Event] = {}

TEL_COLS = ["current_a", "power_w", "energy_today_wh", "energy_total_wh", "peak_today_w",
            "fan", "led", "led_shed", "auto_mode", "safe_mode", "peak_limit_w", "hysteresis_w",
            "budget_wh", "alarm_over", "alarm_budget", "sensor_mv", "rssi"]


def on_connect(client, userdata, flags, reason_code, properties):
    live["mqtt_connected"] = not reason_code.is_failure
    print(f"[MQTT] connected to {MQTT_HOST}: {reason_code}")
    for name, t in TOPICS.items():
        client.subscribe(t, qos=0 if name == "telemetry" else 1)


def on_disconnect(client, userdata, flags, reason_code, properties):
    live["mqtt_connected"] = False
    print(f"[MQTT] disconnected: {reason_code}")


def on_message(client, userdata, msg):
    ts = now_ms()
    kind = msg.topic.rsplit("/", 1)[-1]
    raw = msg.payload.decode("utf-8", "replace")
    try:
        if kind == "status":
            status = raw.strip().lower()
            if status != live["status"]:
                exec_("INSERT INTO availability(ts_server,status) VALUES(?,?)", (ts, status))
            live.update(status=status, status_ts=ts)
            return
        data = json.loads(raw)
        if kind == "telemetry":
            vals = [int(v) if isinstance(v, bool) else v for v in (data.get(c) for c in TEL_COLS)]
            exec_(f"INSERT INTO telemetry(dev,ts_device,ts_server,seq,{','.join(TEL_COLS)}) "
                  f"VALUES(?,?,?,?,{','.join('?' * len(TEL_COLS))})",
                  (data.get("dev"), data.get("ts") or None, ts, data.get("seq"), *vals))
            if live["status"] != "online":
                live.update(status="online", status_ts=ts)
        elif kind == "state":
            live["state"] = data
        elif kind == "event":
            exec_("INSERT INTO events(dev,ts_device,ts_server,type,detail,power_w,limit_w) VALUES(?,?,?,?,?,?,?)",
                  (data.get("dev"), data.get("ts") or None, ts, data.get("type"), data.get("detail"),
                   data.get("power_w"), data.get("limit_w")))
        elif kind == "cmd":
            cidv = data.get("cmd_id") or f"anon-{ts}"
            db.insert_ignore("commands", ["cmd_id", "dev", "source", "payload", "ts_client", "ts_seen_server"],
                             (cidv, DEVICE_ID, data.get("src", "unknown"), raw, data.get("ts"), ts), "cmd_id")
            exec_("UPDATE commands SET ts_seen_server=COALESCE(ts_seen_server,?) WHERE cmd_id=?", (ts, cidv))
        elif kind == "ack":
            cidv = data.get("cmd_id", "")
            row = q("SELECT ts_seen_server FROM commands WHERE cmd_id=?", (cidv,), one=True)
            lat = ts - row["ts_seen_server"] if row and row["ts_seen_server"] else None
            exec_("UPDATE commands SET ts_ack_server=?, ack_ok=?, ack_error=?, ack_state=?, latency_ms=? WHERE cmd_id=?",
                  (ts, int(bool(data.get("ok"))), data.get("error"), raw, lat, cidv))
            live["state"] = {k: v for k, v in data.items() if k not in ("cmd_id", "cmd_ts", "ok", "error")}
            if cidv in ack_waiters:
                ack_waiters[cidv].set()
    except Exception as e:
        print(f"[MQTT] bad message on {msg.topic}: {e} | {raw[:120]}")


mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                    client_id=f"se_backend_{DEVICE_ID}_{uuid.uuid4().hex[:6]}")
if MQTT_USER:
    mqttc.username_pw_set(MQTT_USER, MQTT_PASS)
mqttc.on_connect, mqttc.on_disconnect, mqttc.on_message = on_connect, on_disconnect, on_message
mqttc.reconnect_delay_set(1, 10)


def housekeeping():
    while True:
        time.sleep(6 * 3600)
        try:
            db.purge(RETENTION_DAYS)
            print(f"[DB] purged data older than {RETENTION_DAYS} days")
        except Exception as e:
            print(f"[DB] purge failed: {e}")


@asynccontextmanager
async def lifespan(app):
    mqttc.connect_async(MQTT_HOST, MQTT_PORT, keepalive=30)
    mqttc.loop_start()
    threading.Thread(target=housekeeping, daemon=True).start()
    yield
    mqttc.loop_stop()


app = FastAPI(title="Smart Energy IoT API", version="18.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ----------------------------------------------------------------------------------
# Tính toán
# ----------------------------------------------------------------------------------
def integrate_wh(rows, max_gap_s=10):
    """Tích phân hình thang P(t) -> Wh; khoảng mất dữ liệu > max_gap_s không tính."""
    wh = 0.0
    for a, b in zip(rows, rows[1:]):
        dt = (b["ts_server"] - a["ts_server"]) / 1000
        if 0 < dt <= max_gap_s and a["power_w"] is not None and b["power_w"] is not None:
            wh += (a["power_w"] + b["power_w"]) / 2 * dt / 3600
    return wh


def pct(values, p):
    if not values:
        return None
    s = sorted(values)
    return s[min(len(s) - 1, int(round(p / 100 * (len(s) - 1))))]


def day_start_ms(d: datetime):
    return int(d.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)


def require_key(x_api_key: Optional[str] = Header(None)):
    """Chỉ bật khi biến môi trường API_KEY được đặt (bắt buộc khi backend chạy public)."""
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(401, "Thiếu hoặc sai X-API-Key")


# ----------------------------------------------------------------------------------
# REST API
# ----------------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(DASHBOARD)


@app.get("/api/health")
def health():
    return {"ok": True, "mqtt_connected": live["mqtt_connected"], "broker": MQTT_HOST,
            "topic_base": BASE, "db": "postgres" if db.pg else "sqlite"}


@app.get("/api/status")
def status():
    last = q("SELECT * FROM telemetry ORDER BY ts_server DESC LIMIT 1", one=True)
    age = (now_ms() - last["ts_server"]) / 1000 if last else None
    tariff = float(get_setting("tariff_vnd_per_kwh", 3000))
    today_rows = q("SELECT ts_server, power_w FROM telemetry WHERE ts_server>=? ORDER BY ts_server",
                   (day_start_ms(datetime.now(TZ)),))
    e_today = integrate_wh(today_rows)
    return {
        "device": DEVICE_ID, "availability": live["status"], "availability_since": live["status_ts"],
        "mqtt_connected": live["mqtt_connected"], "data_age_s": age,
        "stale": age is None or age > STALE_S, "latest": last, "confirmed_state": live["state"],
        "energy_today_wh_backend": round(e_today, 4),
        "cost_today_vnd": round(e_today / 1000 * tariff, 1), "tariff_vnd_per_kwh": tariff,
    }


@app.get("/api/history")
def history(minutes: int = Query(60, ge=1, le=10080), bucket_s: Optional[int] = Query(None, ge=1)):
    since = now_ms() - minutes * 60_000
    b = bucket_s or max(2, minutes * 60 // 300)
    rows = q(f"""SELECT (ts_server/{b * 1000})*{b * 1000} AS t, AVG(power_w) AS power_w, MAX(power_w) AS power_max_w,
                 AVG(current_a) AS current_a, MAX(energy_today_wh) AS energy_today_wh, AVG(peak_limit_w) AS peak_limit_w,
                 MAX(led) AS led, MAX(fan) AS fan, COUNT(*) AS n
                 FROM telemetry WHERE ts_server>=? GROUP BY 1 ORDER BY 1""", (since,))
    return {"bucket_s": b, "points": rows}


@app.get("/api/energy/daily")
def energy_daily(days: int = Query(7, ge=1, le=90)):
    tariff = float(get_setting("tariff_vnd_per_kwh", 3000))
    today = datetime.now(TZ)
    out = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        s = day_start_ms(d)
        rows = q("SELECT ts_server, power_w FROM telemetry WHERE ts_server>=? AND ts_server<? ORDER BY ts_server",
                 (s, s + 86_400_000))
        wh = integrate_wh(rows)
        out.append({"date": d.strftime("%Y-%m-%d"), "energy_wh": round(wh, 4),
                    "peak_w": max((r["power_w"] or 0 for r in rows), default=0),
                    "cost_vnd": round(wh / 1000 * tariff, 1), "samples": len(rows)})
    return out


@app.get("/api/events")
def events(limit: int = Query(50, le=1000)):
    return q("SELECT * FROM events ORDER BY ts_server DESC LIMIT ?", (limit,))


@app.get("/api/availability")
def availability(limit: int = Query(50, le=1000)):
    return q("SELECT * FROM availability ORDER BY ts_server DESC LIMIT ?", (limit,))


@app.get("/api/commands")
def commands(limit: int = Query(50, le=1000)):
    return q("SELECT * FROM commands ORDER BY COALESCE(ts_seen_server, ts_client) DESC LIMIT ?", (limit,))


class Command(BaseModel):
    fan: Optional[bool] = None
    led: Optional[bool] = None
    auto_mode: Optional[bool] = None
    peak_limit_w: Optional[float] = Field(None, ge=0.5, le=60)
    hysteresis_w: Optional[float] = Field(None, ge=0.1, le=10)
    budget_wh: Optional[float] = Field(None, ge=0, le=10000)
    calibrate: Optional[bool] = None
    reset_energy: Optional[bool] = None
    wait_ack_s: float = Field(3.0, ge=0, le=10, description="Chờ ACK tối đa (giây)")


@app.post("/api/command", dependencies=[Depends(require_key)])
def send_command(cmd: Command):
    body = cmd.model_dump(exclude_none=True)
    wait = body.pop("wait_ack_s")
    if not body:
        raise HTTPException(400, "Không có trường lệnh nào")
    cid = "rest-" + uuid.uuid4().hex[:10]
    payload = {"cmd_id": cid, "ts": now_ms(), "src": "rest", **body}
    db.insert_ignore("commands", ["cmd_id", "dev", "source", "payload", "ts_client"],
                     (cid, DEVICE_ID, "rest", json.dumps(payload), payload["ts"]), "cmd_id")
    ev = ack_waiters[cid] = threading.Event()
    mqttc.publish(TOPICS["cmd"], json.dumps(payload), qos=1)
    acked = ev.wait(wait) if wait else False
    ack_waiters.pop(cid, None)
    return {"cmd_id": cid, "requested": body, "confirmed": acked,
            "command": q("SELECT * FROM commands WHERE cmd_id=?", (cid,), one=True)}


@app.post("/api/config", dependencies=[Depends(require_key)])
def set_config(cmd: Command):
    """Alias của /api/command, chỉ nhận các trường cấu hình."""
    if cmd.fan is not None or cmd.led is not None:
        raise HTTPException(400, "Dùng /api/command để bật/tắt tải")
    return send_command(cmd)


class Settings(BaseModel):
    tariff_vnd_per_kwh: float = Field(..., gt=0, le=100000)


@app.get("/api/settings")
def get_settings():
    return {r["key"]: float(r["value"]) for r in q("SELECT * FROM settings")}


@app.put("/api/settings", dependencies=[Depends(require_key)])
def put_settings(s: Settings):
    db.upsert_setting("tariff_vnd_per_kwh", str(s.tariff_vnd_per_kwh))
    return get_settings()


@app.get("/api/stats")
def stats(from_ms: Optional[int] = None, to_ms: Optional[int] = None, minutes: int = 10):
    """Số liệu cho phần Thực nghiệm: managed vs unmanaged, độ trễ, tỉ lệ nhận gói."""
    to_ms = to_ms or now_ms()
    from_ms = from_ms or to_ms - minutes * 60_000
    rows = q("SELECT * FROM telemetry WHERE ts_server BETWEEN ? AND ? ORDER BY ts_server", (from_ms, to_ms))
    ev = q("SELECT type, COUNT(*) AS n FROM events WHERE ts_server BETWEEN ? AND ? GROUP BY type", (from_ms, to_ms))
    cmds = q("SELECT latency_ms, ack_ok FROM commands WHERE ts_seen_server BETWEEN ? AND ?", (from_ms, to_ms))

    missing, over_s, led_switches = 0, 0.0, 0
    for a, b in zip(rows, rows[1:]):
        if a["seq"] is not None and b["seq"] is not None and b["seq"] > a["seq"]:
            missing += b["seq"] - a["seq"] - 1
        dt = (b["ts_server"] - a["ts_server"]) / 1000
        if dt <= 10 and a["power_w"] is not None and a["peak_limit_w"] is not None and a["power_w"] > a["peak_limit_w"]:
            over_s += dt
        if a["led"] != b["led"]:
            led_switches += 1
    lat = [r["ts_server"] - r["ts_device"] for r in rows if r["ts_device"]]
    clat = [c["latency_ms"] for c in cmds if c["latency_ms"] is not None]
    powers = [r["power_w"] for r in rows if r["power_w"] is not None]
    n = len(rows)
    return {
        "window": {"from_ms": from_ms, "to_ms": to_ms, "duration_s": (to_ms - from_ms) / 1000},
        "packets": {"received": n, "missing_by_seq": missing,
                    "success_rate": round(n / (n + missing), 4) if n else None},
        "power": {"peak_w": max(powers, default=None), "avg_w": round(sum(powers) / n, 3) if n else None,
                  "energy_wh": round(integrate_wh(rows), 4), "over_limit_duration_s": round(over_s, 1)},
        "control": {"led_switch_count": led_switches, "events": {e["type"]: e["n"] for e in ev}},
        "latency_device_to_backend_ms": {"n": len(lat), "avg": round(sum(lat) / len(lat), 1) if lat else None,
                                         "p95": pct(lat, 95), "max": max(lat, default=None),
                                         "note": "cần NTP đồng bộ trên ESP32 và máy chạy backend"},
        "latency_cmd_to_ack_ms": {"n": len(clat), "avg": round(sum(clat) / len(clat), 1) if clat else None,
                                  "p95": pct(clat, 95), "max": max(clat, default=None),
                                  "unacked": sum(1 for c in cmds if c["ack_ok"] is None)},
    }


@app.get("/api/export/{table}.csv")
def export_csv(table: str, minutes: int = Query(1440, ge=1, le=525600)):
    if table not in ("telemetry", "events", "commands", "availability"):
        raise HTTPException(404, "table không hợp lệ")
    col = "ts_seen_server" if table == "commands" else "ts_server"
    rows = q(f"SELECT * FROM {table} WHERE {col}>=? ORDER BY {col}", (now_ms() - minutes * 60_000,))
    buf = io.StringIO()
    if rows:
        w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename={table}.csv"})


if __name__ == "__main__":
    print(f"Broker: {MQTT_HOST}:{MQTT_PORT}  topics: {BASE}/#\nDashboard: http://localhost:{HTTP_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=HTTP_PORT)
