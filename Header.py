import json
import sqlite3
import threading
import os
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import paho.mqtt.client as mqtt

# =========================================================================
# 1. Cấu hình Đường dẫn động thông minh & Database [343, 345]
# =========================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "energy_data.db")

print(f"-> Đường dẫn file Database thực tế: {DB_FILE}")

# Thay 'localhost' bằng IP máy tính của bạn khi chạy thực tế (ví dụ '172.20.10.2')
MQTT_BROKER = "localhost" 
MQTT_PORT = 1883

TOPIC_TELEMETRY = "energy/device/telemetry"
TOPIC_STATUS = "energy/device/status"
TOPIC_CONTROL = "energy/device/control"

# Khởi tạo Cơ sở dữ liệu SQLite chuẩn cấu trúc chuỗi thời gian (time-series) [343, 345]
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Bảng lưu lịch sử đo đạc dòng, áp, công suất, năng lượng Wh
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            voltage REAL,
            current REAL,
            power REAL,
            energy REAL
        )
    """)
    # Bảng lưu lịch sử bật tắt thiết bị thực tế để AI đếm tần suất [343, 345]
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS control_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            load_id INTEGER,
            state TEXT
        )
    """)
    # Bảng cấu hình thiết bị
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS device_config (
            key TEXT PRIMARY KEY,
            value REAL
        )
    """)
    # Thiết lập giá trị mặc định ban đầu
    cursor.execute("INSERT OR IGNORE INTO device_config (key, value) VALUES ('peak_limit', 24.0)")
    cursor.execute("INSERT OR IGNORE INTO device_config (key, value) VALUES ('auto_mode', 1.0)")
    conn.commit()
    conn.close()

# Tự động gọi hàm khởi tạo khi khởi chạy chương trình
init_db()

# =========================================================================
# 2. Khởi tạo FastAPI REST API
# =========================================================================
app = FastAPI(title="Hệ thống REST API Giám Sát Năng Lượng Đồ Án IoT")

# Cấu hình CORS để giao diện Web / Frontend không bị chặn bảo mật khi kết nối
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Biến toàn cục lưu trạng thái thực tế cuối cùng nhận từ thiết bị [343, 345]
device_states = {
    "load_1": "OFF",
    "load_2": "OFF",
    "online": "OFFLINE"
}

# =========================================================================
# 3. Lập trình luồng MQTT ngầm (Background Thread) [343, 345]
# =========================================================================
mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    print(f"-> Đã kết nối thành công tới MQTT Broker với mã: {rc}")
    client.subscribe(TOPIC_TELEMETRY)
    client.subscribe(TOPIC_STATUS)
    client.publish("energy/backend/status", "ONLINE", retain=True)

def on_message(client, userdata, msg):
    global device_states
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)
        
        # Nhận dữ liệu đo đạc (Telemetry) gửi lên từ ESP32
        if msg.topic == TOPIC_TELEMETRY:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO telemetry (voltage, current, power, energy) 
                VALUES (?, ?, ?, ?)
            """, (data.get("voltage", 0), data.get("current", 0), data.get("power", 0), data.get("energy", 0)))
            conn.commit()
            conn.close()
            device_states["online"] = "ONLINE"
            print(f"[DATA REC] {data}")

        # Nhận tin xác nhận trạng thái thực tế (Acknowledged State) của Relay từ ESP32 [343, 345]
        elif msg.topic == TOPIC_STATUS:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            # Kiểm tra xem trạng thái Quạt (Load 1) có thay đổi thực tế không để ghi Control Log
            if "load_1" in data:
                new_state = data["load_1"]
                if new_state != device_states["load_1"]:
                    cursor.execute("INSERT INTO control_log (load_id, state) VALUES (?, ?)", (1, new_state))
                    device_states["load_1"] = new_state
                    print(f"-> Ghi nhận sự kiện đổi trạng thái Quạt (Load 1) -> {new_state}")
            
            # Kiểm tra xem trạng thái Đèn (Load 2) có thay đổi thực tế không để ghi Control Log
            if "load_2" in data:
                new_state = data["load_2"]
                if new_state != device_states["load_2"]:
                    cursor.execute("INSERT INTO control_log (load_id, state) VALUES (?, ?)", (2, new_state))
                    device_states["load_2"] = new_state
                    print(f"-> Ghi nhận sự kiện đổi trạng thái Đèn (Load 2) -> {new_state}")
            
            conn.commit()
            conn.close()
            print(f"[CONFIRMED STATE REC] Load 1: {device_states['load_1']} | Load 2: {device_states['load_2']}")
            
    except Exception as e:
        print(f"Lỗi khi xử lý bản tin MQTT: {e}")

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

def run_mqtt():
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_forever()
    except Exception as e:
        print(f"Không thể kết nối MQTT Broker: {e}. Đảm bảo phần mềm Mosquitto đang chạy!")

# Chạy MQTT Client trong luồng ngầm độc lập để không làm nghẽn FastAPI chính
threading.Thread(target=run_mqtt, daemon=True).start()

# =========================================================================
# 4. Giao diện Web HTML Dashboard tích hợp [343, 345]
# =========================================================================
dashboard_html = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IoT Energy Dashboard</title>
    <!-- Tailwind CSS và Chart.js qua CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        body { font-family: 'Inter', sans-serif; }
    </style>
</head>
<body class="bg-slate-900 text-white min-h-screen">
    <div class="container mx-auto px-4 py-8">
        <!-- Header -->
        <header class="flex justify-between items-center mb-8 border-b border-slate-800 pb-4">
            <div>
                <h1 class="text-3xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
                    Smart Energy Portal
                </h1>
                <p class="text-slate-400 text-sm mt-1">Đề tài số 3: Giám sát điện năng & Quản lý tải thông minh</p>
            </div>
            <div id="status-badge" class="px-4 py-1.5 rounded-full text-xs font-semibold bg-red-500/20 text-red-400 border border-red-500/30">
                THIẾT BỊ: OFFLINE
            </div>
        </header>

        <!-- Main Grid Layout -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <!-- Left & Middle: Controls & Charts -->
            <div class="lg:col-span-2 space-y-8">
                <!-- Real-time Stats Cards [343, 345] -->
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div class="bg-slate-800/50 p-4 rounded-2xl border border-slate-700/50">
                        <p class="text-xs text-slate-400 font-medium">ĐIỆN ÁP</p>
                        <p id="stat-voltage" class="text-2xl font-bold mt-1 text-cyan-400">0.0 V</p>
                    </div>
                    <div class="bg-slate-800/50 p-4 rounded-2xl border border-slate-700/50">
                        <p class="text-xs text-slate-400 font-medium">DÒNG ĐIỆN RMS</p>
                        <p id="stat-current" class="text-2xl font-bold mt-1 text-emerald-400">0.00 A</p>
                    </div>
                    <div class="bg-slate-800/50 p-4 rounded-2xl border border-slate-700/50">
                        <p class="text-xs text-slate-400 font-medium">CÔNG SUẤT</p>
                        <p id="stat-power" class="text-2xl font-bold mt-1 text-amber-400">0.0 W</p>
                    </div>
                    <div class="bg-slate-800/50 p-4 rounded-2xl border border-slate-700/50">
                        <p class="text-xs text-slate-400 font-medium">NĂNG LƯỢNG Wh</p>
                        <p id="stat-energy" class="text-2xl font-bold mt-1 text-indigo-400">0.00 Wh</p>
                    </div>
                </div>

                <!-- Fan & Load Control Section [343, 345] -->
                <div class="bg-slate-800/40 p-6 rounded-2xl border border-slate-700/50">
                    <div class="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
                        <h2 class="text-xl font-bold flex items-center gap-2">
                            <span class="w-2.5 h-2.5 rounded-full bg-cyan-400"></span> Điều Khiển Thiết Bị
                        </h2>
                        <!-- Auto Mode Toggle -->
                        <label class="relative inline-flex items-center cursor-pointer">
                            <input type="checkbox" id="auto-mode-toggle" class="sr-only peer">
                            <div class="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-gradient-to-r peer-checked:from-cyan-500 peer-checked:to-blue-600"></div>
                            <span class="ml-3 text-sm font-medium text-slate-300">Tự Động Quản Lý Tải (Auto)</span>
                        </label>
                    </div>

                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <!-- Card Tải 1 (Quạt) -->
                        <div class="bg-slate-900/60 p-5 rounded-xl border border-slate-800 flex items-center justify-between">
                            <div class="flex items-center gap-4">
                                <div class="p-3 bg-cyan-500/10 rounded-lg text-cyan-400">
                                    <!-- Fan Icon -->
                                    <svg class="w-8 h-8 animate-spin" id="fan-icon" style="animation-duration: 3s; animation-play-state: paused;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
                                </div>
                                <div>
                                    <h3 class="font-bold text-lg">Quạt 12V (Tải 1)</h3>
                                    <p class="text-xs text-slate-400">Tải ưu tiên cao</p>
                                </div>
                            </div>
                            <button id="btn-load-1" onclick="toggleLoad(1)" class="px-6 py-2.5 rounded-xl font-bold bg-slate-700 text-slate-300 transition-all hover:scale-105 active:scale-95">
                                BẬT
                            </button>
                        </div>

                        <!-- Card Tải 2 (Đèn trang trí) -->
                        <div class="bg-slate-900/60 p-5 rounded-xl border border-slate-800 flex items-center justify-between">
                            <div class="flex items-center gap-4">
                                <div class="p-3 bg-amber-500/10 rounded-lg text-amber-400">
                                    <!-- Light Bulb Icon -->
                                    <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path></svg>
                                </div>
                                <div>
                                    <h3 class="font-bold text-lg">Đèn Led (Tải 2)</h3>
                                    <p class="text-xs text-slate-400">Tải phụ (Sẽ cắt trước) [343, 345]</p>
                                </div>
                            </div>
                            <button id="btn-load-2" onclick="toggleLoad(2)" class="px-6 py-2.5 rounded-xl font-bold bg-slate-700 text-slate-300 transition-all hover:scale-105 active:scale-95">
                                BẬT
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Charts Section [343, 345] -->
                <div class="bg-slate-800/40 p-6 rounded-2xl border border-slate-700/50">
                    <h2 class="text-xl font-bold mb-6 flex items-center gap-2">
                        <span class="w-2.5 h-2.5 rounded-full bg-emerald-400"></span> Diễn Biến Tiêu Thụ Công Suất (Thời Gian Thực)
                    </h2>
                    <div class="h-[300px]">
                        <canvas id="energyChart"></canvas>
                    </div>
                </div>
            </div>

            <!-- Right: Config & AI Chatbox -->
            <div class="space-y-8 flex flex-col justify-between">
                <!-- Limit Power Config Card -->
                <div class="bg-slate-800/40 p-6 rounded-2xl border border-slate-700/50">
                    <h2 class="text-xl font-bold mb-4 flex items-center gap-2">
                        <span class="w-2.5 h-2.5 rounded-full bg-amber-400"></span> Ngưỡng Công Suất Đỉnh [343, 345]
                    </h2>
                    <div class="space-y-4">
                        <div>
                            <label class="text-xs text-slate-400">Giới hạn cài đặt (W):</label>
                            <input type="number" id="input-peak-limit" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2 mt-1 focus:outline-none focus:border-cyan-400 text-white font-bold" value="24.0">
                        </div>
                        <button onclick="updatePeakLimit()" class="w-full py-2.5 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold rounded-xl shadow-lg shadow-cyan-500/10 transition-all hover:shadow-cyan-500/20 active:scale-[0.98]">
                            CẬP NHẬT CẤU HÌNH
                        </button>
                    </div>
                </div>

                <!-- Beautiful AI Chatbox Section with DB Connection -->
                <div class="bg-slate-800/40 rounded-2xl border border-slate-700/50 flex flex-col flex-grow min-h-[380px]">
                    <!-- Chat Header -->
                    <div class="p-4 border-b border-slate-700 flex items-center gap-3 bg-gradient-to-r from-slate-800 to-slate-900 rounded-t-2xl">
                        <div class="w-8 h-8 rounded-full bg-cyan-500/20 text-cyan-400 flex items-center justify-center font-bold">
                            🤖
                        </div>
                        <div>
                            <h3 class="font-bold text-sm">Trợ lý Đồ án AI</h3>
                            <p class="text-[10px] text-cyan-400 flex items-center gap-1">
                                <span class="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse"></span> Online • Sẵn sàng hỗ trợ
                            </p>
                        </div>
                    </div>
                    <!-- Chat Messages -->
                    <div id="chat-messages" class="p-4 space-y-3 flex-grow overflow-y-auto max-h-[220px] text-sm flex flex-col">
                        <div class="bg-slate-900/50 p-3 rounded-2xl border border-slate-800/80 max-w-[85%] text-slate-300">
                            Trợ lý AI chuyên trách đề tài số 3, bạn đang gặp vướng mắc gì?Hãy hỏi tôi nhé!
                        </div>
                    </div>
                    <!-- Chat Input -->
                    <div class="p-4 border-t border-slate-700 bg-slate-900/40 rounded-b-2xl flex gap-2">
                        <input type="text" id="chat-input" onkeydown="handleChatKey(event)" placeholder="Hỏi AI về số lần bật, số liệu biểu đồ..." class="flex-grow bg-slate-950 border border-slate-700 rounded-xl px-4 py-2 text-white focus:outline-none focus:border-cyan-400 text-sm">
                        <button onclick="sendChatMessage()" class="p-2 bg-cyan-500 hover:bg-cyan-400 text-slate-950 rounded-xl font-bold transition-all active:scale-95 flex items-center justify-center">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"></path></svg>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Script tương tác logic và vẽ Chart -->
    <script>
        const API_URL = "http://" + window.location.hostname + ":8000/api";
        let chart;
        let isAutoMode = true;
        let currentStates = { load_1: "OFF", load_2: "OFF" };

        // Khởi tạo đồ thị
        function initChart() {
            const ctx = document.getElementById('energyChart').getContext('2d');
            chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Công suất tiêu thụ (W)',
                        data: [],
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        borderWidth: 2,
                        tension: 0.4,
                        fill: true,
                        pointRadius: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { display: false }, ticks: { color: '#94a3b8' } },
                        y: { grid: { color: '#334155' }, ticks: { color: '#94a3b8' } }
                    }
                }
            });
        }

        // Cập nhật giao diện nút bấm bật tắt quạt và LED [343, 345]
        function updateUIControls(data) {
            isAutoMode = data.auto_mode;
            document.getElementById("auto-mode-toggle").checked = isAutoMode;

            currentStates.load_1 = data.load_1_state;
            currentStates.load_2 = data.load_2_state;

            const btn1 = document.getElementById("btn-load-1");
            const btn2 = document.getElementById("btn-load-2");
            const fanIcon = document.getElementById("fan-icon");

            // Cập nhật quạt (Tải 1 - Quạt)
            if (currentStates.load_1 === "ON") {
                btn1.innerText = "TẮT";
                btn1.className = "px-6 py-2.5 rounded-xl font-bold bg-red-600 text-white transition-all hover:scale-105 active:scale-95";
                fanIcon.style.animationPlayState = "running";
            } else {
                btn1.innerText = "BẬT";
                btn1.className = "px-6 py-2.5 rounded-xl font-bold bg-cyan-500 text-slate-950 transition-all hover:scale-105 active:scale-95";
                fanIcon.style.animationPlayState = "paused";
            }

            // Cập nhật đèn LED (Tải 2)
            if (currentStates.load_2 === "ON") {
                btn2.innerText = "TẮT";
                btn2.className = "px-6 py-2.5 rounded-xl font-bold bg-red-600 text-white transition-all hover:scale-105 active:scale-95";
            } else {
                btn2.innerText = "BẬT";
                btn2.className = "px-6 py-2.5 rounded-xl font-bold bg-amber-500 text-slate-950 transition-all hover:scale-105 active:scale-95";
            }

            // Vô hiệu hóa nút thủ công nếu đang ở chế độ Auto [343, 345]
            if (isAutoMode) {
                btn1.disabled = true;
                btn2.disabled = true;
                btn1.classList.add("opacity-50", "cursor-not-allowed");
                btn2.classList.add("opacity-50", "cursor-not-allowed");
            } else {
                btn1.disabled = false;
                btn2.disabled = false;
                btn1.classList.remove("opacity-50", "cursor-not-allowed");
                btn2.classList.remove("opacity-50", "cursor-not-allowed");
            }

            // Online/Offline status
            const badge = document.getElementById("status-badge");
            if (data.online_status === "ONLINE") {
                badge.innerText = "THIẾT BỊ: ONLINE";
                badge.className = "px-4 py-1.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
            } else {
                badge.innerText = "THIẾT BỊ: OFFLINE";
                badge.className = "px-4 py-1.5 rounded-full text-xs font-semibold bg-red-500/20 text-red-400 border border-red-500/30";
            }
        }

        // Gọi API điều khiển Tải
        async function toggleLoad(loadId) {
            const currentState = loadId === 1 ? currentStates.load_1 : currentStates.load_2;
            const targetState = currentState === "ON" ? "OFF" : "ON";
            
            try {
                const response = await fetch(`${API_URL}/control`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ load_id: loadId, state: targetState })
                });
                const resData = await response.json();
                console.log(resData.message);
            } catch (err) {
                console.error("Lỗi gửi lệnh điều khiển:", err);
            }
        }

        // Gọi API cập nhật cấu hình
        async function updatePeakLimit() {
            const peakLimit = parseFloat(document.getElementById("input-peak-limit").value);
            try {
                await fetch(`${API_URL}/config`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ peak_limit: peakLimit, auto_mode: isAutoMode })
                });
                alert("Cập nhật ngưỡng công suất thành công!");
            } catch (err) {
                console.error("Lỗi cập nhật cấu hình:", err);
            }
        }

        // Đồng bộ nút gạt Auto/Manual
        document.getElementById("auto-mode-toggle").addEventListener('change', async function() {
            isAutoMode = this.checked;
            try {
                await fetch(`${API_URL}/config`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ auto_mode: isAutoMode })
                });
            } catch (err) {
                console.error("Lỗi cập nhật chế độ Auto/Manual:", err);
            }
        });

        // Định kỳ lấy dữ liệu tức thời và cập nhật thống kê [343, 345]
        async function fetchCurrentData() {
            try {
                const response = await fetch(`${API_URL}/energy/current`);
                const data = await response.json();
                
                if (data.voltage !== undefined) {
                    document.getElementById("stat-voltage").innerText = `${data.voltage.toFixed(1)} V`;
                    document.getElementById("stat-current").innerText = `${data.current.toFixed(2)} A`;
                    document.getElementById("stat-power").innerText = `${data.power.toFixed(1)} W`;
                    document.getElementById("stat-energy").innerText = `${data.energy.toFixed(2)} Wh`;
                    document.getElementById("input-peak-limit").value = data.peak_limit;
                }
                updateUIControls(data);
            } catch (err) {
                console.error("Lỗi đọc dữ liệu hiện tại:", err);
            }
        }

        // Định kỳ lấy dữ liệu lịch sử để vẽ biểu đồ
        async function fetchHistory() {
            try {
                const response = await fetch(`${API_URL}/energy/history`);
                const data = await response.json();
                
                const labels = data.map(item => {
                    const t = new Date(item.timestamp);
                    return `${t.getHours().toString().padStart(2,'0')}:${t.getMinutes().toString().padStart(2,'0')}:${t.getSeconds().toString().padStart(2,'0')}`;
                });
                const powerData = data.map(item => item.power);

                chart.data.labels = labels;
                chart.data.datasets[0].data = powerData;
                chart.update();
            } catch (err) {
                console.error("Lỗi đọc lịch sử:", err);
            }
        }

        // Xử lý gửi tin nhắn Chatbox AI
        async function sendChatMessage() {
            const input = document.getElementById("chat-input");
            const message = input.value.trim();
            if (!message) return;

            const chatMessages = document.getElementById("chat-messages");

            // Hiển thị tin nhắn người dùng
            const userMsgHtml = `<div class="bg-cyan-500 text-slate-950 p-3 rounded-2xl max-w-[85%] self-end ml-auto font-medium mb-2">${message}</div>`;
            chatMessages.innerHTML += userMsgHtml;
            input.value = "";
            chatMessages.scrollTop = chatMessages.scrollHeight;

            // Hiển thị trạng thái AI đang gõ
            const botLoadingId = "bot-loading-" + Date.now();
            const botLoadingHtml = `<div id="${botLoadingId}" class="bg-slate-900/50 p-3 rounded-2xl border border-slate-800 max-w-[85%] text-slate-400 italic mb-2">Đang truy vấn cơ sở dữ liệu...</div>`;
            chatMessages.innerHTML += botLoadingHtml;
            chatMessages.scrollTop = chatMessages.scrollHeight;

            try {
                const response = await fetch(`${API_URL}/chat`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: message })
                });
                const resData = await response.json();
                
                // Xóa trạng thái đang gõ và hiển thị phản hồi thực tế từ AI
                document.getElementById(botLoadingId).remove();
                const botMsgHtml = `<div class="bg-slate-900/50 p-3 rounded-2xl border border-slate-800 max-w-[85%] text-slate-300 mb-2">${resData.reply}</div>`;
                chatMessages.innerHTML += botMsgHtml;
                chatMessages.scrollTop = chatMessages.scrollHeight;
            } catch (err) {
                document.getElementById(botLoadingId).remove();
                const errorHtml = `<div class="bg-red-500/10 text-red-400 border border-red-500/20 p-3 rounded-2xl max-w-[85%] mb-2">Gặp lỗi kết nối tới Server AI!</div>`;
                chatMessages.innerHTML += errorHtml;
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
        }

        function handleChatKey(e) {
            if (e.key === 'Enter') {
                sendChatMessage();
            }
        }

        // Khởi động khi tải trang
        initChart();
        fetchCurrentData();
        fetchHistory();

        // Đặt chu kỳ lấy mẫu
        setInterval(fetchCurrentData, 2000); // 2 giây lấy dữ liệu tức thời 1 lần
        setInterval(fetchHistory, 5000);     // 5 giây cập nhật biểu đồ 1 lần
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def read_root():
    return dashboard_html

# =========================================================================
# 5. REST API Chatbox AI hỗ trợ Đồ án & Truy vấn DB [343, 345]
# =========================================================================
@app.post("/api/chat")
def chat_assistant(chat_input: dict):
    user_msg = chat_input.get("message", "").lower()
    reply = ""
    
    # 1. Kết nối DB để sẵn sàng lấy số liệu thực tế
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # A. CÁC LỆNH ĐIỀU KHIỂN THIẾT BỊ TRỰC TIẾP QUA CHATBOX AI [343, 345]
        if "bật quạt" in user_msg or "bat quat" in user_msg:
            # Gửi tin MQTT điều khiển quạt bật
            payload = json.dumps({"load_id": 1, "action": "ON"})
            mqtt_client.publish(TOPIC_CONTROL, payload)
            reply = "🟢 **Lệnh đã truyền:** Tôi đã gửi tín hiệu MQTT yêu cầu **bật Quạt (Tải 1)** thành công!"
            
        elif "tắt quạt" in user_msg or "tat quat" in user_msg:
            payload = json.dumps({"load_id": 1, "action": "OFF"})
            mqtt_client.publish(TOPIC_CONTROL, payload)
            reply = "🔴 **Lệnh đã truyền:** Tôi đã gửi tín hiệu MQTT yêu cầu **tắt Quạt (Tải 1)** thành công!"
            
        elif "bật đèn" in user_msg or "bat den" in user_msg:
            payload = json.dumps({"load_id": 2, "action": "ON"})
            mqtt_client.publish(TOPIC_CONTROL, payload)
            reply = "🟢 **Lệnh đã truyền:** Tôi đã gửi tín hiệu MQTT yêu cầu **bật Đèn (Tải 2)** thành công!"
            
        elif "tắt đèn" in user_msg or "tat den" in user_msg:
            payload = json.dumps({"load_id": 2, "action": "OFF"})
            mqtt_client.publish(TOPIC_CONTROL, payload)
            reply = "🔴 **Lệnh đã truyền:** Tôi đã gửi tín hiệu MQTT yêu cầu **tắt Đèn (Tải 2)** thành công!"

        # B. TRUY VẤN LỊCH SỬ BẬT TẮT THIẾT BỊ (ĐẾM RELAY TOGGLES) [343, 345]
        elif "quạt" in user_msg and ("bao nhiêu lần" in user_msg or "mấy lần" in user_msg or "tần suất" in user_msg):
            # Truy vấn số lần Quạt (Load 1) được bật hôm nay
            cursor.execute("""
                SELECT COUNT(*) FROM control_log 
                WHERE load_id = 1 AND state = 'ON' AND date(timestamp) = date('now', 'localtime')
            """)
            on_count = cursor.fetchone()[0]
            reply = f"📊 Theo cơ sở dữ liệu hệ thống, trong ngày hôm nay **Quạt (Tải 1)** đã được bật tổng cộng **{on_count} lần**."
            
        elif "đèn" in user_msg and ("bao nhiêu lần" in user_msg or "mấy lần" in user_msg or "tần suất" in user_msg):
            # Truy vấn số lần Đèn (Load 2) được bật hôm nay
            cursor.execute("""
                SELECT COUNT(*) FROM control_log 
                WHERE load_id = 2 AND state = 'ON' AND date(timestamp) = date('now', 'localtime')
            """)
            on_count = cursor.fetchone()[0]
            reply = f"📊 Thống kê hôm nay: **Đèn Led (Tải 2)** đã được kích hoạt bật tổng cộng **{on_count} lần** từ hệ thống."

        # C. TRUY VẤN THÔNG SỐ ĐIỆN NĂNG THỜI GIAN THỰC & BIỂU ĐỒ [343, 345]
        elif "công suất trung bình" in user_msg or "trung bình" in user_msg:
            cursor.execute("SELECT AVG(power) FROM telemetry")
            avg_power = cursor.fetchone()[0]
            if avg_power is not None:
                reply = f"📈 **Số liệu biểu đồ:** Công suất tiêu thụ trung bình của hệ thống đạt **{avg_power:.2f} W**."
            else:
                reply = "Chưa có đủ dữ liệu trên biểu đồ để tính toán công suất trung bình."
                
        elif "công suất lớn nhất" in user_msg or "cực đại" in user_msg or "lớn nhất" in user_msg or "max" in user_msg:
            cursor.execute("SELECT MAX(power) FROM telemetry")
            max_power = cursor.fetchone()[0]
            if max_power is not None:
                reply = f"⚡ Công suất tiêu thụ lớn nhất ghi nhận được trên biểu đồ là **{max_power:.1f} W**."
            else:
                reply = "Chưa tìm thấy bản tin đo đạc nào được lưu trữ để xác định công suất lớn nhất."

        elif "điện năng" in user_msg or "wh" in user_msg or "tiêu thụ" in user_msg:
            cursor.execute("SELECT energy FROM telemetry ORDER BY id DESC LIMIT 1")
            last_energy = cursor.fetchone()
            if last_energy and last_energy[0] is not None:
                energy_val = last_energy[0]
                reply = f"🔋 Tổng năng lượng tiêu thụ tích lũy hiện tại của các tải đạt **{energy_val:.3f} Wh**."
            else:
                reply = "Chưa có bản ghi đo đạc năng lượng Wh nào được gửi lên từ ESP32."

        elif "tiền điện" in user_msg:
            # Ước tính tiền điện dựa trên Wh tiêu thụ thực tế (Giá trung bình 2.500đ / kWh) [343, 345]
            cursor.execute("SELECT energy FROM telemetry ORDER BY id DESC LIMIT 1")
            last_energy = cursor.fetchone()
            if last_energy and last_energy[0] is not None:
                kwh = last_energy[0] / 1000.0
                cost = kwh * 2500
                reply = f"💰 **Ước tính tiêu thụ:** Với **{last_energy[0]:.3f} Wh** đã tiêu thụ, tiền điện ước tính (tính theo đơn giá 2.500đ/kWh) là khoảng **{cost:.2f} VNĐ**."
            else:
                reply = "Chưa có dữ liệu Wh tiêu thụ để ước tính hóa đơn tiền điện."

        elif "vôn" in user_msg or "áp" in user_msg or "ampe" in user_msg or "dòng" in user_msg:
            cursor.execute("SELECT voltage, current FROM telemetry ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                reply = f"🔌 **Thông số tức thời:** Điện áp đo được là **{row[0]:.1f} V** và cường độ dòng điện RMS hiện tại là **{row[1]:.2f} A**."
            else:
                reply = "Mạch chưa nhận được số liệu đo đạc nào từ cảm biến ACS712."

        # D. CÁC CÂU HỎI THƯỜNG GẶP VỀ HÀN MẠCH, THUẬT TOÁN, BÁO CÁO [343, 345]
        elif "hạ áp" in user_msg or "lm2596" in user_msg:
            reply = ("Để hàn mạch hạ áp LM2596 gọn đẹp trên phíp lỗ xanh:<br>"
                     "1. Bạn hàn 4 chân **Header cái (Female)** làm bệ cắm rời cho module.<br>"
                     "2. Hàn **Header đực (Male)** hướng xuống dưới tại 4 lỗ IN/OUT của LM2596 rồi cắm vào bệ để dễ thay thế.<br>"
                     "3. Căn chỉnh núm xoay biến trở để áp ra đúng **5V** trước khi cắm nuôi chip ESP32.")
        elif "nối chân" in user_msg or "sơ đồ" in user_msg:
            reply = ("Sơ đồ đấu nối đề tài số 3:<br>"
                     "• **ACS712 OUT** nối chân **GPIO 34** (Analog ADC) của ESP32.<br>"
                     "• **Relay IN1** (Quạt - Ưu tiên Cao) nối chân **GPIO 12**.<br>"
                     "• **Relay IN2** (Đèn Led - Ưu tiên Thấp) nối chân **GPIO 13**.<br>"
                     "• Nguồn 5V sau hạ áp LM2596 cấp trực tiếp vào chân 5V và GND của ESP32.")
        elif "thuật toán" in user_msg or "ngắt tải" in user_msg or "hysteresis" in user_msg:
            reply = ("Thuật toán Quản lý tải thông minh (Hysteresis):<br>"
                     "• Khi **Công suất thực tế > Ngưỡng đỉnh (Peak Limit)**: ESP32 ngắt ngay Relay 2 (Đèn Led - ưu tiên thấp).<br>"
                     "• Khi **Công suất thực tế giảm xuống dưới ngưỡng an toàn (Peak Limit - Trễ 4W)**: ESP32 tự động khôi phục Relay 2.<br>"
                     "• Thuật toán này giúp bảo vệ mạng lưới điện và chống chập chờn relay.")
        elif "báo cáo" in user_msg or "điểm" in user_msg:
            reply = ("Để báo cáo đạt điểm 8+ tuyệt đối, nhóm cần trình bày:<br>"
                     "1. **Bảng so sánh** đỉnh công suất trước và sau khi quản lý tải (Managed vs Unmanaged).<br>"
                     "2. **Đo đạc độ trễ** truyền tin từ thiết bị lên server (Event-to-Dashboard Latency).<br>"
                     "3. **Kịch bản offline cục bộ** khi mất kết nối mạng để thể hiện tính an toàn.")
        else:
            reply = ("Tôi là Trợ lý AI chuyên trách Đề tài số 3. Bạn có thể hỏi tôi các câu lệnh như:<br>"
                     "• *'Hôm nay quạt đã bật bao nhiêu lần?'*<br>"
                     "• *'Công suất trung bình trên biểu đồ là bao nhiêu?'*<br>"
                     "• *'Ước tính hóa đơn tiền điện hiện tại'*<br>"
                     "• Hoặc ra lệnh trực tiếp: *'Bật quạt'*, *'Tắt đèn led'*...")
            
    except Exception as e:
        reply = f"Lỗi truy vấn dữ liệu AI: {e}"
    finally:
        conn.close()
        
    return {"reply": reply}

# =========================================================================
# 6. Các cổng REST API phục vụ cho Dashboard [343, 345]
# =========================================================================
@app.get("/api/energy/current")
def get_current_data():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, voltage, current, power, energy FROM telemetry ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    
    # Lấy các thông số cấu hình giới hạn công suất
    cursor.execute("SELECT value FROM device_config WHERE key = 'peak_limit'")
    peak_limit_row = cursor.fetchone()
    peak_limit = peak_limit_row[0] if peak_limit_row else 24.0

    cursor.execute("SELECT value FROM device_config WHERE key = 'auto_mode'")
    auto_mode_row = cursor.fetchone()
    auto_mode = auto_mode_row[0] if auto_mode_row else 1.0
    conn.close()
    
    if row:
        return {
            "timestamp": row[0],
            "voltage": row[1],
            "current": row[2],
            "power": row[3],
            "energy": row[4],
            "load_1_state": device_states["load_1"],
            "load_2_state": device_states["load_2"],
            "online_status": device_states["online"],
            "peak_limit": peak_limit,
            "auto_mode": True if auto_mode == 1.0 else False
        }
    return {
        "message": "Chưa có dữ liệu cảm biến gửi lên", 
        "load_1_state": device_states["load_1"], 
        "load_2_state": device_states["load_2"],
        "online_status": device_states["online"],
        "peak_limit": peak_limit,
        "auto_mode": True if auto_mode == 1.0 else False
    }

@app.get("/api/energy/history")
def get_history_data():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, power, energy FROM telemetry ORDER BY id DESC LIMIT 30")
    rows = cursor.fetchall()
    conn.close()
    return [{"timestamp": r[0], "power": r[1], "energy": r[2]} for r in reversed(rows)]

@app.post("/api/config")
def update_config(config_data: dict):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    if "peak_limit" in config_data:
        val = float(config_data["peak_limit"])
        cursor.execute("UPDATE device_config SET value = ? WHERE key = 'peak_limit'", (val,))
        # Đồng bộ cấu hình xuống ESP32 bằng MQTT [343, 345]
        mqtt_client.publish("energy/device/config/limit", str(val), retain=True)
    if "auto_mode" in config_data:
        val = 1.0 if config_data["auto_mode"] else 0.0
        cursor.execute("UPDATE device_config SET value = ? WHERE key = 'auto_mode'", (val,))
        mqtt_client.publish("energy/device/config/mode", str(val), retain=True)
    conn.commit()
    conn.close()
    return {"status": "success", "updated_config": config_data}

@app.post("/api/control")
def control_load(control_data: dict):
    load_id = control_data.get("load_id")
    state = control_data.get("state")
    
    if load_id not in [1, 2] or state not in ["ON", "OFF"]:
        raise HTTPException(status_code=400, detail="Dữ liệu điều khiển không hợp lệ")
    
    payload = json.dumps({"load_id": load_id, "action": state})
    mqtt_client.publish(TOPIC_CONTROL, payload)
    
    return {"status": "command_sent", "message": f"Yêu cầu chuyển đổi Tải {load_id} sang {state} đã được truyền đi."}

# Khởi động server
if __name__ == "__main__":
    import uvicorn
    # reload=True giúp server tự động cập nhật khi bạn lưu file
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
