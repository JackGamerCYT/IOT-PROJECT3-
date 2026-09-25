/* English report generator: node tools/make_report_en.js -> docs/REPORT_IOT_PROJECT03_EN.docx */
const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell,
  WidthType, ShadingType, PageBreak, TableOfContents, Header, Footer, PageNumber,
  LevelFormat, convertInchesToTwip,
} = require('docx');

const FONT = 'Times New Roman';
const W = 9360;
const ROOT = path.join(__dirname, '..');

const p = (text, o = {}) => new Paragraph({
  alignment: o.align || AlignmentType.JUSTIFIED,
  spacing: { after: o.after ?? 120, line: 276 },
  children: [new TextRun({ text, font: FONT, size: o.size || 26, bold: o.bold, italics: o.italics })],
});

const h = (text, level) => new Paragraph({
  heading: level,
  spacing: { before: 240, after: 120 },
  children: [new TextRun({ text, font: FONT, size: level === HeadingLevel.HEADING_1 ? 30 : 27,
                           bold: true, color: '1a3b5c' })],
});

const code = (lines) => lines.map((l, i) => new Paragraph({
  spacing: { after: i === lines.length - 1 ? 160 : 0, line: 240 },
  shading: { type: ShadingType.CLEAR, fill: 'F2F4F7' },
  indent: { left: convertInchesToTwip(0.15) },
  children: [new TextRun({ text: l || ' ', font: 'Consolas', size: 17 })],
}));

const bullets = (items) => items.map(t => new Paragraph({
  numbering: { reference: 'bul', level: 0 },
  spacing: { after: 80, line: 276 },
  alignment: AlignmentType.JUSTIFIED,
  children: [new TextRun({ text: t, font: FONT, size: 26 })],
}));

function table(rows, widths) {
  const total = widths.reduce((a, b) => a + b, 0);
  const cols = widths.map(x => Math.round(x / total * W));
  return new Table({
    columnWidths: cols,
    width: { size: W, type: WidthType.DXA },
    rows: rows.map((r, ri) => new TableRow({
      tableHeader: ri === 0,
      children: r.map((cell, ci) => new TableCell({
        width: { size: cols[ci], type: WidthType.DXA },
        shading: ri === 0 ? { type: ShadingType.CLEAR, fill: 'DCE6F1' } : undefined,
        margins: { top: 60, bottom: 60, left: 100, right: 100 },
        children: String(cell).split('\n').map(line => new Paragraph({
          spacing: { after: 0, line: 240 },
          children: [new TextRun({ text: line, font: FONT, size: 22, bold: ri === 0 })],
        })),
      })),
    })),
  });
}

const cap = (t) => new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { before: 60, after: 200 },
  children: [new TextRun({ text: t, font: FONT, size: 22, italics: true })],
});

const srcLines = f => fs.readFileSync(path.join(ROOT, f), 'utf8').replace(/\r/g, '').split('\n');

function srcBetween(file, startMark, endMark, maxLines = 200) {
  const L = srcLines(file);
  const i = L.findIndex(x => x.includes(startMark));
  if (i < 0) return ['(not found: ' + startMark + ')'];
  let j = L.findIndex((x, k) => k > i && x.includes(endMark));
  if (j < 0) j = Math.min(L.length, i + maxLines);
  return L.slice(i, j + 1);
}

const srcAll = f => srcLines(f).map((l, i) => String(i + 1).padStart(4, ' ') + ' | ' + l);

const codeBlock = (lines, size = 14) => lines.map(l => new Paragraph({
  spacing: { after: 0, line: 200 },
  children: [new TextRun({ text: l.replace(/\t/g, '    ') || ' ', font: 'Consolas', size })],
}));

const pageBreak = () => new Paragraph({ children: [new PageBreak()] });

// ===================================================================================
const body = [];
const bl = (n = 1) => { for (let i = 0; i < n; i++) body.push(p('')); };

// --- COVER ---
bl(2);
body.push(p('HO CHI MINH CITY UNIVERSITY OF TECHNOLOGY AND EDUCATION',
            { align: AlignmentType.CENTER, bold: true, size: 26 }));
body.push(p('FACULTY OF ELECTRICAL AND ELECTRONICS ENGINEERING',
            { align: AlignmentType.CENTER, bold: true, size: 26 }));
bl(3);
body.push(p('FINAL COURSE PROJECT REPORT', { align: AlignmentType.CENTER, bold: true, size: 32 }));
body.push(p('COURSE: IOT FOUNDATIONS AND APPLICATIONS',
            { align: AlignmentType.CENTER, bold: true, size: 28 }));
bl(1);
body.push(p('PROJECT 03: SMART ENERGY MONITORING AND INTELLIGENT LOAD MANAGEMENT',
            { align: AlignmentType.CENTER, bold: true, size: 30 }));
bl(4);
body.push(p('Team members:', { align: AlignmentType.CENTER, bold: true }));
body.push(p('Dang Dinh Manh – 24119055', { align: AlignmentType.CENTER }));
body.push(p('……………………… – …………', { align: AlignmentType.CENTER }));
body.push(p('……………………… – …………', { align: AlignmentType.CENTER }));
body.push(p('……………………… – …………', { align: AlignmentType.CENTER }));
bl(3);
body.push(p('Supervisor: ………………………', { align: AlignmentType.CENTER }));
body.push(p('Ho Chi Minh City, September 2026', { align: AlignmentType.CENTER, italics: true }));
body.push(pageBreak());

// --- TOC ---
body.push(h('TABLE OF CONTENTS', HeadingLevel.HEADING_1));
body.push(new TableOfContents('Contents', { hyperlink: true, headingStyleRange: '1-2' }));
body.push(p('(Open in Word, right-click the table of contents, choose Update Field → Update entire table to generate page numbers.)',
            { italics: true, size: 22 }));
body.push(pageBreak());

// --- 1 ---
body.push(h('1. INTRODUCTION AND PROBLEM STATEMENT', HeadingLevel.HEADING_1));
body.push(p('Household and small laboratory electrical demand frequently exceeds a safe threshold for short intervals when several appliances run at the same time. The consequences are nuisance breaker trips, wasted energy and shortened wiring life. Users, however, rarely know how much power they are drawing at a given moment, or which device should be disconnected before the limit is crossed.'));
body.push(p('This project builds a complete IoT system that addresses the problem at a safe model scale: it measures the current and power of two 12 V DC loads in real time, stores the history in a time-series database, displays it on a web interface, automatically sheds the low-priority load when demand exceeds a peak limit, and restores it only when conditions have been stably safe.'));
body.push(p('Specific objectives:', { bold: true }));
body.push(...bullets([
  'Measure current and power with a quantified error; raw ADC counts are not accepted as a final measurement.',
  'Transmit data over MQTT with a structured topic hierarchy and detect device online/offline state through the Last Will and Testament mechanism.',
  'Store time-series data and expose REST APIs for history, configuration and statistics.',
  'Manage loads by priority, with an anti-chattering mechanism, and keep operating when the network is lost.',
  'Provide a real-time dashboard that clearly separates the requested state from the state the device has actually confirmed.',
  'Add an advanced component: peak demand detection and a daily energy budget.',
]));
body.push(p('Scope: the entire power circuit operates at 12 VDC and no part touches the mains supply, in accordance with the safety requirement of the assignment.'));

// --- 2 ---
body.push(h('2. REQUIREMENTS AND THEORETICAL BACKGROUND', HeadingLevel.HEADING_1));
body.push(h('2.1. Requirement mapping', HeadingLevel.HEADING_2));
body.push(table([
  ['Requirement', 'Implementation in this project'],
  ['Isolated, low-voltage current measurement', 'ACS712-05B Hall-effect sensor, 12 V DC loads'],
  ['At least two controllable loads', '12 V fan (high priority) and 12 V LED lamp (low priority)'],
  ['MQTT with structured topics, QoS, availability', 'Six topics under smartenergy/node9988, retained LWT'],
  ['Time-series database and REST API', 'SQLite or PostgreSQL, five tables, twelve endpoints'],
  ['Dashboard with full metrics and alarms', 'Real-time web interface, charts, event log'],
  ['Priority-based load management, anti-chattering', 'State machine with hysteresis, minimum time and power prediction'],
  ['Requested state distinct from acknowledged state', 'cmd_id and ack message pair'],
  ['Advanced component', 'Peak demand detection and daily energy budget'],
  ['Safe behaviour during network loss', 'Local safe mode, RTC timekeeping, store-and-forward buffer'],
], [40, 60]));
body.push(cap('Table 2.1. Mapping between assignment requirements and the implemented solution'));

body.push(h('2.2. Hall-effect current sensing', HeadingLevel.HEADING_2));
body.push(p('The ACS712 routes the load current through an integrated copper conduction path. The magnetic field produced is proportional to the current, is sensed by a Hall element and converted into an output voltage. The 5 A variant has a sensitivity of 185 mV/A and an output of half the supply voltage at zero current, that is 2.5 V on a 5 V rail. The conduction path is galvanically isolated from the signal circuit with a nominal withstand voltage of 2.1 kV, which is why this device satisfies the isolated-measurement requirement of the assignment.'));
body.push(...code(['I [A] = (V_out - V_zero) / 0.185', '',
                   'V_out : voltage at the sensor OUT pin (V)',
                   'V_zero: output voltage at zero current, obtained by calibration']));
body.push(p('Because the load is DC, the mean of many samples reflects the true load current and no RMS computation is required. Conversely, applying an RMS formula to a noisy DC signal adds the noise in quadrature and biases the result upwards; this was an actual defect found and corrected during development, described in chapter 12.'));

body.push(h('2.3. Power and energy', HeadingLevel.HEADING_2));
body.push(...code(['P [W] = U x I            (U = 12 V, treated as constant)',
                   'E [Wh] = sum of P x dt / 3600',
                   'Cost = E/1000 x tariff [currency per kWh]']));
body.push(p('The backend recomputes energy by trapezoidal integration over the telemetry series in order to cross-check the accumulator kept on the device. Gaps longer than ten seconds are excluded from the integral so that a loss of connectivity does not produce a fabricated value.'));

body.push(h('2.4. Hysteresis control and anti-chattering theory', HeadingLevel.HEADING_2));
body.push(p('A controller with a single threshold oscillates continuously whenever the measured quantity sits near that threshold. The classical remedy is a hysteresis band: shed the load when P exceeds P_peak but restore it only when P falls below P_peak minus H. For this system hysteresis alone is still insufficient, because restoring the load itself raises the demand and may immediately exceed the limit again. The project therefore applies three simultaneous conditions: a hysteresis band in power, a minimum dwell time, and a prediction step for the demand after restoration.'));

body.push(h('2.5. The MQTT protocol', HeadingLevel.HEADING_2));
body.push(p('MQTT is a publish/subscribe protocol over TCP, well suited to embedded devices because of its small packets and long-lived connections. It defines three quality-of-service levels: QoS 0 delivers at most once, QoS 1 at least once and QoS 2 exactly once. The Last Will and Testament mechanism lets the broker publish a predefined message when it loses contact with a device, so failures are detected without polling. The retained flag makes a newly subscribed client receive the most recent message on a topic immediately.'));
body.push(pageBreak());

// --- 3 ---
body.push(h('3. SYSTEM ARCHITECTURE', HeadingLevel.HEADING_1));
body.push(...code([
  '[12V adapter]-[2A fuse]-+-[LM2596 -> 5V]-> ESP32-S3, ACS712,',
  '                        |                   relays, OLED, DS3231',
  '                        +-[ACS712]-+-[Relay 1]- 12V fan  (HIGH priority)',
  '                                   +-[Relay 2]- 12V LED  (LOW priority)',
  '',
  'ESP32-S3: 4 sample blocks/s, local control loop every 2 s,',
  '          RTC timekeeping, 600-record store-and-forward buffer',
  '   | MQTT 1883   smartenergy/node9988/{telemetry,status,state,event,cmd,ack}',
  '   v',
  'MQTT broker --WSS 8884--> Dashboard (Vercel): live data, commands,',
  '                                              latency measurement',
  '   | MQTT 1883',
  '   v',
  'FastAPI backend (Render, 24/7) -- SQLite / PostgreSQL (Neon)',
  '                               -- REST /api/* + data assistant /api/chat',
]));
body.push(cap('Figure 3.1. Overall system architecture'));
body.push(p('The system has four layers. The device layer (ESP32-S3) performs measurement and real-time control; every switching decision is taken here, so protection does not depend on the network. The communication layer is the MQTT broker, which mediates between device, backend and interface. The data layer is the FastAPI backend: it subscribes to every topic, writes to the database and exposes REST APIs. The application layer is the web dashboard, which receives live values directly from the broker over WebSocket Secure and fetches history from the REST API.'));
body.push(p('One design point deserves emphasis. The dashboard is deployed on Vercel, a platform that serves static files and serverless functions whose lifetime is a few seconds per request. Such a platform cannot hold a persistent MQTT connection to ingest telemetry, so the ingest process must run on an always-on service (Render, or a local computer). Separating the ingest worker from the interface is therefore a technical consequence, not an arbitrary choice.'));
body.push(p('Main data flow: the ESP32 measures and publishes telemetry every two seconds; the backend writes it into the telemetry table with two timestamps, the instant the device created the packet and the instant the server received it, which makes end-to-end latency measurable. The control flow runs in the opposite direction: the dashboard or the REST API publishes a command on the cmd topic, the device applies it and publishes an ack message; the backend records both the command and the acknowledgement and computes the latency between them.'));

// --- 4 ---
body.push(h('4. HARDWARE', HeadingLevel.HEADING_1));
body.push(h('4.1. Bill of materials', HeadingLevel.HEADING_2));
body.push(table([
  ['No.', 'Component', 'Key specification', 'Role'],
  ['1', 'ESP32-S3 DevKitC-1 N16R8', 'Xtensa LX7 dual-core 240 MHz, Wi-Fi, 12-bit ADC', 'Main controller'],
  ['2', 'ACS712-05B', '±5 A, 185 mV/A, 2.1 kV isolation', 'Load current sensing'],
  ['3', '2-channel 5 V relay module', 'Opto-isolated, active low, 10 A/30 VDC contacts', 'Load switching'],
  ['4', 'LM2596 buck converter', '4–35 V in, 5.0 V out, 3 A', 'Supply for the control circuit'],
  ['5', 'DS3231', 'I2C RTC, ±2 ppm, battery backup', 'Timekeeping without network'],
  ['6', 'SSD1306 OLED', '0.96 inch, 128×64, I2C', 'Local display'],
  ['7', '12 V DC fan', 'about 0.2–0.4 A', 'Load 1, high priority'],
  ['8', '12 V LED bar', 'about 0.1–0.3 A', 'Load 2, low priority'],
  ['9', '12 V – 2 A adapter', '', 'Main supply'],
  ['10', '2 A fuse, 1N4007 diode, 10 kΩ/20 kΩ resistors', '', 'Protection and ADC divider'],
], [8, 30, 32, 30]));
body.push(cap('Table 4.1. Bill of materials'));

body.push(h('4.2. Pin assignment', HeadingLevel.HEADING_2));
body.push(table([
  ['Component', 'Pin', 'ESP32-S3', 'Function'],
  ['ACS712', 'OUT (through 10 kΩ/20 kΩ divider)', 'GPIO 1 (ADC1_CH0)', 'Analogue current signal'],
  ['Relay module', 'IN1', 'GPIO 12', 'Load 1 – 12 V fan'],
  ['Relay module', 'IN2', 'GPIO 13', 'Load 2 – 12 V LED'],
  ['DS3231 (0x68)', 'SDA / SCL', 'GPIO 8 / GPIO 9', 'Real-time clock'],
  ['SSD1306 (0x3C)', 'SDA / SCL', 'GPIO 8 / GPIO 9', 'Display, shared I2C bus'],
  ['Buzzer via S8050', 'Base through 1 kΩ', 'GPIO 14', 'Over-limit alarm'],
  ['LM2596', 'OUT+ / OUT−', '5V / GND', '5 V supply'],
], [24, 28, 22, 26]));
body.push(cap('Table 4.2. Pin connection table'));

body.push(h('4.3. Protection design and engineering decisions', HeadingLevel.HEADING_2));
body.push(...bullets([
  'A 10 kΩ/20 kΩ divider at the ACS712 output: at 5 A the sensor output reaches 3.43 V, beyond the safe ADC range of the ESP32-S3. The ratio of 0.667 maps the 0–5 V range onto 0–3.33 V.',
  'A 2 A fuse on the +12 V line, placed ahead of the sensor, protects the entire power circuit.',
  'A 1N4007 diode in reverse parallel with the fan suppresses the back-EMF produced when the inductive load is switched off.',
  'Relay contacts rated 10 A/30 VDC, many times the actual load current of under 1 A, provide a wide safety margin.',
  'Removing the JD-VCC jumper on the relay module and supplying VCC from 3.3 V ensures the ESP32 logic high fully turns the optocoupler off.',
  'The ESP32-S3 was chosen over the classic ESP32 because GPIO 12 on the latter is the MTDI strapping pin; a high level at boot selects the wrong flash voltage and prevents start-up.',
  'The LM2596 is fed upstream of the sensor so that the control circuit current is not counted in the load measurement.',
]));

// --- 5 ---
body.push(h('5. PROTOCOL AND NETWORKING', HeadingLevel.HEADING_1));
body.push(h('5.1. Topic hierarchy and quality of service', HeadingLevel.HEADING_2));
body.push(table([
  ['Topic', 'Direction', 'QoS / retain', 'Content'],
  ['smartenergy/node9988/telemetry', 'Device → system', 'QoS 0', 'Measurements, every 2 s'],
  ['smartenergy/node9988/status', 'Device → system', 'QoS 1, retained, LWT', 'online / offline'],
  ['smartenergy/node9988/state', 'Device → system', 'retained', 'Configuration and load state'],
  ['smartenergy/node9988/event', 'Device → system', 'QoS 0', 'Shedding, restoration, alarms'],
  ['smartenergy/node9988/cmd', 'Web/backend → device', 'QoS 1', 'Commands carrying cmd_id'],
  ['smartenergy/node9988/ack', 'Device → system', 'QoS 0', 'Command acknowledgement and actual state'],
], [34, 22, 20, 24]));
body.push(cap('Table 5.1. MQTT topic specification'));
body.push(p('Telemetry uses QoS 0 because each message completely supersedes the previous one; loss is detected through the monotonically increasing seq field, which also yields a packet success rate without the handshake overhead of QoS 1. Commands are subscribed at QoS 1. The PubSubClient library on the ESP32 only publishes at QoS 0, so command reliability is guaranteed at application level by the cmd_id/ack pair with a five second timeout; this is a known limitation stated in chapter 13.'));

body.push(h('5.2. Message format', HeadingLevel.HEADING_2));
body.push(...code([
  '{"dev":"node9988","ts":1789550319106,"seq":42,',
  ' "current_a":0.352,"power_w":4.224,"energy_today_wh":0.0931,',
  ' "energy_total_wh":1.204,"peak_today_w":4.301,',
  ' "fan":true,"led":true,"led_shed":"NONE","auto_mode":true,"safe_mode":false,',
  ' "peak_limit_w":3.5,"hysteresis_w":0.5,"budget_wh":0,"led_est_w":1.8,',
  ' "alarm_over":false,"alarm_budget":false,"sensor_mv":2565.1,"zero_mv":2500.0,',
  ' "diff_mv":65.1,"rssi":-55,"uptime_s":84,"time_src":"ntp","buffered_count":0}',
]));
body.push(p('The ts field is Unix time in milliseconds, taken from NTP or from the DS3231. Every message carries the device identifier, so the system scales to multiple nodes without changing the structure.'));

body.push(h('5.3. Availability detection', HeadingLevel.HEADING_2));
body.push(p('On connection the device registers an "offline" will on the status topic with the retained flag, then publishes "online" itself. If the device loses power or drops off the network, the broker publishes "offline" once the fifteen second keepalive expires, so the dashboard and the backend learn exactly when the device stopped working. The dashboard additionally tracks data freshness: if no new packet arrives within six seconds, that is three telemetry periods, it displays a stale-data warning.'));

// --- 6 ---
body.push(h('6. BACKEND AND DATA', HeadingLevel.HEADING_1));
body.push(h('6.1. Database schema', HeadingLevel.HEADING_2));
body.push(table([
  ['Table', 'Main columns', 'Purpose'],
  ['telemetry', 'ts_device, ts_server, seq, current_a, power_w, energy_today_wh, peak_today_w, fan, led, led_shed, auto_mode, safe_mode, peak_limit_w, alarm_over, sensor_mv, rssi', 'Measurement time series'],
  ['events', 'ts_device, ts_server, type, detail, power_w, limit_w', 'Shedding, restoration, alarms'],
  ['availability', 'ts_server, status', 'Online/offline history'],
  ['commands', 'cmd_id, source, payload, ts_client, ts_seen_server, ts_ack_server, ack_ok, latency_ms', 'Command log and acknowledgement latency'],
  ['settings', 'key, value', 'Electricity tariff'],
], [18, 52, 30]));
body.push(cap('Table 6.1. Database schema'));
body.push(p('The backend supports SQLite (local development) and PostgreSQL (the Neon service for 24/7 deployment) simultaneously. The data access layer converts the syntax between the two engines, so a single code base runs in both environments. Data older than the configured retention period is purged every six hours.'));

body.push(h('6.2. REST endpoints', HeadingLevel.HEADING_2));
body.push(table([
  ['Endpoint', 'Function'],
  ['GET /api/status', 'Latest telemetry, availability, data freshness, energy and cost for the day'],
  ['GET /api/history?minutes=&bucket_s=', 'Aggregated time series, capped at 300 points'],
  ['GET /api/energy/daily?days=', 'Energy, peak and cost per day'],
  ['GET /api/events | /api/availability | /api/commands', 'Logs'],
  ['POST /api/command', 'Send a command, wait for acknowledgement, return requested and confirmed state'],
  ['POST /api/config', 'Peak limit, hysteresis, budget, automatic mode'],
  ['GET /api/stats?minutes=', 'Statistics for the experimental chapter'],
  ['POST /api/chat', 'Data assistant'],
  ['GET /api/export/{table}.csv', 'Data export for the report'],
], [38, 62]));
body.push(cap('Table 6.2. REST API list'));
body.push(p('The /api/stats endpoint aggregates, over a time window: peak power, mean power, energy, total time above the limit, load switching count, packet success rate derived from gaps in seq, and both device-to-server and command-to-acknowledgement latency as mean, 95th percentile and maximum. This is exactly the data set used in the experimental chapter.'));

// --- 7 ---
body.push(h('7. APPLICATION AND USER INTERFACE', HeadingLevel.HEADING_1));
body.push(p('The dashboard is a single web page. It receives live values directly from the broker over WebSocket Secure and fetches history from the REST API, so the interface keeps showing real-time data even when the backend is temporarily unavailable; only the history section is lost.'));
body.push(...bullets([
  'Six metric cards: instantaneous power with its limit, current, energy for the day with a budget progress bar, estimated cost, peak power for the day, and load management mode.',
  'A real-time chart with a selectable window of 1, 5, 15 or 60 minutes and three series: power, peak limit and current; power on the left axis in watts, current on the right axis in amperes.',
  'A load control panel that separates the requested state from the state confirmed by the device, with acknowledgement latency and a timeout warning.',
  'A configuration panel: automatic mode, peak limit, hysteresis, daily budget, zero-point calibration, energy reset and electricity tariff.',
  'An alarm and event log that merges live messages with history fetched from the backend.',
  'A history panel: power charts over 1 hour, 6 hours, 24 hours and 7 days, plus a bar chart of daily energy for the last seven days, refreshed automatically every thirty seconds.',
  'An experiment panel: latency in both directions, packet success rate, unacknowledged command count, a statistics button and CSV export.',
  'A data assistant and an MQTT log window for troubleshooting during the live demonstration.',
]));
body.push(p('The local OLED shows the time from the DS3231, power, current, energy for the day, the state of both loads, Wi-Fi and MQTT icons and the number of buffered records. This demonstrates during the presentation that the device operates independently of the network.'));

body.push(h('7.1. Data assistant', HeadingLevel.HEADING_2));
body.push(p('The assistant runs entirely inside the backend. A question is normalised by stripping Vietnamese diacritics, classified into an intent by regular expressions, and then answered by querying the database directly and formatting the real figures. Because no free text is generated, there is no possibility of fabricated numbers, unlike an approach based on a large language model.'));
body.push(p('For control phrasings the system does not execute anything by itself; it returns an action descriptor, the interface shows a confirmation button, and only a user click sends the command. This is a mandatory safety constraint when natural language is allowed to operate relays.'));

body.push(h('7.2. Backend ingest code', HeadingLevel.HEADING_2));
body.push(p('The backend subscribes to all six topics. For telemetry messages the noteworthy detail is the handling of buffered packets: a packet carrying the "buffered" flag uses the device timestamp as its storage timestamp, so data forwarded after a network outage lands at the correct position on the history chart instead of piling up at the moment of reception.'));
body.push(...codeBlock(srcBetween('backend/main.py', 'def on_message(client, userdata, msg):',
                                  'print(f"[MQTT] bad message')));

body.push(h('7.3. Database access layer', HeadingLevel.HEADING_2));
body.push(p('The DB class lets the same source run on SQLite during development and on PostgreSQL in production by translating parameter markers and conditional insert syntax:'));
body.push(...codeBlock(srcBetween('backend/main.py', 'class DB:', 'def init_schema(self):')));

body.push(h('7.4. Real-time chart code', HeadingLevel.HEADING_2));
body.push(p('The browser keeps a WebSocket connection to the broker and appends a point as soon as a message arrives, rather than polling the server. The buffer is trimmed by time rather than by point count, so changing the display window does not distort the horizontal axis:'));
body.push(...codeBlock(srcBetween('index.html', 'function rtRedraw()', "$('rt-pause').onclick")));

// --- 8 ---
body.push(h('8. CONTROL AND SYSTEM INTELLIGENCE', HeadingLevel.HEADING_1));
body.push(h('8.1. Priority-based load shedding algorithm', HeadingLevel.HEADING_2));
body.push(...code([
  'Every 2 seconds, with P the 2-second mean power:',
  '',
  'IF managed AND LED is on AND (P > P_peak continuously >= 4 s)',
  '    -> SHED the LED, state SHED_PEAK, emit event SHED',
  '',
  'ELSE IF managed AND LED is off AND state = SHED_PEAK',
  '    AND (P < P_peak - H continuously >= 15 s)',
  '    AND (LED has been off >= 20 s)',
  '    AND (P + estimated P_LED < P_peak)',
  '    -> RESTORE the LED, emit event RESTORE',
  '',
  'IF LED is off AND P still > P_peak continuously >= 10 s',
  '    -> ALARM_OVER_LIMIT + buzzer (the high-priority fan is never shed)',
]));
body.push(p('The three restoration conditions complement one another. The hysteresis band prevents oscillation caused by measurement noise around the threshold. The minimum dwell time prevents oscillation caused by rapidly varying loads. The prediction condition is the most important: the power of the LED lamp is estimated from the power step observed each time the lamp changes state, using an exponential moving average with weights 0.7 and 0.3. If the present demand plus the estimated lamp power exceeds the limit, the system does not restore, because it knows the load would have to be shed again immediately.'));
body.push(p('The fan is the high-priority load and is never shed automatically. When demand remains above the limit after the lamp has been shed, the system raises an alarm and leaves the decision to the operator instead of disconnecting an important appliance on its own.'));

body.push(h('8.2. Advanced component: peak detection and daily energy budget', HeadingLevel.HEADING_2));
body.push(p('The device continuously records the peak power of the day and publishes it in telemetry. When demand stays above the limit while the low-priority load has already been shed, the system raises a peak alarm, that is, it detects a situation in which the available shedding measure is insufficient.'));
body.push(p('The daily energy budget allows a watt-hour quota per day. At eighty per cent of the quota the system issues an early warning. Once the quota is exceeded the low-priority load is shed and is only re-enabled on the following day. This policy is fully explainable in terms of rules, which makes it convenient to defend and to verify, unlike a black-box approach.'));

body.push(h('8.3. Requested state versus confirmed state', HeadingLevel.HEADING_2));
body.push(p('Every command carries a randomly generated cmd_id. The device applies the command and then publishes an ack message containing the same cmd_id together with the actual state of both relays after application. The interface displays two separate lines, measures the latency with the browser clock and reports an error if no acknowledgement arrives within five seconds. This mechanism exposes the true nature of a distributed system: a command that has been sent is not a command that has been executed.'));
body.push(p('One case deserves attention: a user switching a load by hand while automatic mode is active. The device switches to manual mode and emits a MANUAL_OVERRIDE event, rather than letting two mechanisms fight over the same relay.'));

body.push(h('8.4. Measurement code', HeadingLevel.HEADING_2));
body.push(p('The following function runs four times per second on the ESP32. Three technical points are worth noting: averaging 64 samples to suppress noise, taking the absolute value of the deviation so that the measurement does not depend on the sensor wiring polarity, and automatically re-calibrating the zero point while both loads are off.'));
body.push(...codeBlock(srcBetween('firmware/esp32_firmware/esp32_firmware.ino',
  'void measureBlock()', 'sum_block_p += power_w; n_block++;')));
body.push(p('The absolute value arises from a real defect: the first version wrote "if (i < deadband) i = 0", which forced every negative value to zero. When the IP+ and IP− terminals of the sensor were connected the other way round, the output voltage fell below the 2.5 V reference, the computed current became negative and was discarded entirely; the system reported 0 A while the load was running. Chapter 12 records the full account.'));
body.push(p('The automatic zero tracking addresses reference drift when the supply changes. Measurements recorded a drift of about 30 mV between USB powering and LM2596 powering, equivalent to an error of 0.17 A if left uncompensated.'));

body.push(h('8.5. Load management state machine code', HeadingLevel.HEADING_2));
body.push(...codeBlock(srcBetween('firmware/esp32_firmware/esp32_firmware.ino',
  'void controlStep()', 'buzzer(alarm_over);')));

body.push(h('8.6. Command acknowledgement code', HeadingLevel.HEADING_2));
body.push(p('The device receives a command, applies it, then publishes an acknowledgement carrying the same command identifier and the actual state of both relays:'));
body.push(...codeBlock(srcBetween('firmware/esp32_firmware/esp32_firmware.ino',
  'void onMqtt(char* topic', 'Serial.printf("[CMD]')));

// --- 9 ---
body.push(h('9. SECURITY AND RELIABILITY', HeadingLevel.HEADING_1));
body.push(h('9.1. Behaviour during network loss', HeadingLevel.HEADING_2));
body.push(...bullets([
  'Wi-Fi and MQTT reconnection never blocks the main loop; measurement and control keep running on their two-second cycle while reconnection is attempted.',
  'If the broker is unreachable for more than thirty seconds the device enters safe mode: local load management is activated even if the device was in manual mode.',
  'The DS3231 keeps time without Wi-Fi, so records created during an outage carry correct timestamps; when the network returns, NTP time is written back to the RTC every ten minutes.',
  'A 600-record circular buffer, about twenty minutes, stores data during an outage and forwards it at five packets per 200 ms on reconnection. Forwarded packets carry the buffered flag and the backend uses the device timestamp, so the history chart is not distorted.',
  'Reconnection emits a RECOVERED event carrying the outage duration and the number of forwarded packets, which is used as evidence in the experiments.',
  'Critical configuration is stored in flash, so thresholds and mode survive a power cycle.',
]));
body.push(h('9.2. Security', HeadingLevel.HEADING_2));
body.push(table([
  ['Threat', 'Impact', 'Current mitigation', 'Planned improvement'],
  ['A stranger publishes on the cmd topic', 'Unauthorised load switching', 'Hard-to-guess topic name; every command is logged with its source', 'Authenticated broker with per-topic ACL'],
  ['Telemetry eavesdropping', 'Usage patterns disclosed', 'No personal data in the messages', 'MQTT over TLS on port 8883'],
  ['Arbitrary REST calls', 'Remote configuration changes', 'X-API-Key header required on every POST and PUT', 'Per-user authentication, separate view and control rights'],
  ['Wi-Fi password exposed in source', 'Unauthorised access to the local network', 'Moved to secrets.h and excluded from Git', 'Provisioning through a first-boot access point'],
  ['The assistant misreads an intent', 'Unintended switching', 'Manual confirmation required before any command is sent', 'Per-user audit log'],
], [24, 22, 30, 24]));
body.push(cap('Table 9.1. Risk analysis and mitigations'));
body.push(p('The main security limitation is the public broker without authentication. This was a conscious choice so that the system works under the network conditions available at the university, and the source is already prepared for a switch to an authenticated broker through configuration only.'));

// --- 10 ---
body.push(h('10. EXPERIMENTAL METHOD', HeadingLevel.HEADING_1));
body.push(table([
  ['ID', 'Experiment', 'Procedure', 'Quantities collected'],
  ['E1', 'Measurement error', 'A reference ammeter in series; four cases: no load, fan, lamp, both; 30 samples each', 'Absolute and percentage error, standard deviation'],
  ['E2', 'Device to dashboard latency', 'Compare the packet timestamp with the display instant over 100 consecutive packets', 'Mean, 95th percentile, maximum'],
  ['E3', 'Command to acknowledgement latency', 'Thirty on/off operations, read from the interface and the commands table', 'Mean, 95th percentile, timeouts'],
  ['E4', 'Managed versus unmanaged operation', 'Two ten-minute runs with identical loads and limit, automatic mode off then on', 'Peak power, energy, time above limit, switching count'],
  ['E5', 'Anti-chattering', 'Set the limit close to the combined load; compare the full configuration against one without hysteresis and minimum time', 'Switching operations per ten minutes'],
  ['E6', 'Network loss and recovery', 'Disconnect the router for sixty seconds while above the limit', 'Offline detection instant, local behaviour, forwarded packets, residual data gap'],
  ['E7', 'Daily energy budget', 'Set a small quota and observe the warning and shedding behaviour', 'Time of the 80 % warning and of the quota breach'],
  ['E8', 'RTC drift', 'Compare DS3231 time against NTP after 24 hours', 'Seconds of drift per day'],
], [8, 22, 42, 28]));
body.push(cap('Table 10.1. Experiment matrix'));
body.push(p('Instrumentation: the interface displays latency and packet success rate directly; the /api/stats endpoint aggregates them over a window; CSV export allows the raw data to be reprocessed in a spreadsheet. Every figure in the results chapter comes from these three sources and none is entered by hand.'));

// --- 11 ---
body.push(h('11. RESULTS AND DISCUSSION', HeadingLevel.HEADING_1));
body.push(p('The tables below are completed after running the experiments on the physical prototype.', { italics: true }));
body.push(h('11.1. Measurement error (E1)', HeadingLevel.HEADING_2));
body.push(table([
  ['Case', 'Reference (A)', 'System (A)', 'Error (A)', 'Error (%)', 'Std. dev. (A)'],
  ['No load', '', '', '', '', ''],
  ['Fan only', '', '', '', '', ''],
  ['LED lamp only', '', '', '', '', ''],
  ['Both loads', '', '', '', '', ''],
], [22, 18, 16, 14, 14, 16]));
body.push(cap('Table 11.1. Measurement error results'));
body.push(h('11.2. Latency (E2, E3)', HeadingLevel.HEADING_2));
body.push(table([
  ['Metric', 'Samples', 'Mean (ms)', '95th percentile (ms)', 'Maximum (ms)'],
  ['Device → backend', '', '', '', ''],
  ['Device → dashboard', '', '', '', ''],
  ['Command → acknowledgement', '', '', '', ''],
], [30, 16, 18, 18, 18]));
body.push(cap('Table 11.2. Latency results'));
body.push(h('11.3. Managed versus unmanaged operation (E4)', HeadingLevel.HEADING_2));
body.push(table([
  ['Metric over 10 minutes', 'Unmanaged', 'Managed', 'Difference'],
  ['Peak power (W)', '', '', ''],
  ['Energy consumed (Wh)', '', '', ''],
  ['Time above limit (s)', '', '', ''],
  ['Load switching operations', '', '', ''],
  ['Packet success rate (%)', '', '', ''],
], [34, 22, 22, 22]));
body.push(cap('Table 11.3. Effectiveness of load management'));
body.push(h('11.4. Anti-chattering (E5) and network loss (E6)', HeadingLevel.HEADING_2));
body.push(table([
  ['Configuration', 'Switching operations / 10 min', 'Comment'],
  ['All three conditions (H = 0.5 W, 15 s, 20 s, with prediction)', '', ''],
  ['Single threshold, no hysteresis, no minimum time', '', ''],
], [42, 24, 34]));
body.push(cap('Table 11.4. Effectiveness of the anti-chattering mechanism'));
body.push(table([
  ['Observation (E6)', 'Result'],
  ['Offline detected after disconnection (s)', ''],
  ['Local shedding behaviour during the outage', ''],
  ['Records forwarded after recovery', ''],
  ['Residual gap on the chart (s)', ''],
  ['Time from reconnection to continuous data (s)', ''],
], [58, 42]));
body.push(cap('Table 11.5. Network loss experiment results'));
body.push(h('11.5. Discussion', HeadingLevel.HEADING_2));
body.push(p('The discussion should answer four questions: whether the measurement error is small enough relative to the control threshold; whether the end-to-end latency is compatible with the two-second control cycle; by what percentage load management reduces the time spent above the limit compared with unmanaged operation; and how the system behaves when the network is lost. If the measurement error exceeds roughly one tenth of the threshold, the voltage divider, the quality of the 5 V rail and the zero-point calibration should be reviewed.'));

// --- 12 ---
body.push(h('12. DEVELOPMENT PROCESS AND DEFECTS RESOLVED', HeadingLevel.HEADING_1));
body.push(p('The system went through several rounds of debugging. This chapter records the defects with technical value, because they illustrate the characteristic traps of a multi-layer IoT system: a fault rarely sits in one place, it hides at the boundary between layers.'));
body.push(table([
  ['Defect', 'Symptom', 'Root cause', 'Resolution'],
  ['Chart never plotted', 'Metric cards updated but the curve stayed flat at zero',
   'chart.data.datasets.data written instead of datasets[0].data; the exception was swallowed by a try/catch block',
   'Fixed the array index and moved to a time-based buffer'],
  ['Current always zero', 'Loads were running but power read 0 W',
   'A clamp forced negative values to zero, so a reversed IP+/IP− connection discarded the entire measurement',
   'Take the absolute value of the voltage deviation'],
  ['Zero point drift', 'Sensor read 2499 mV while the stored zero was 2530 mV',
   'The reference level changed when the supply moved from USB to the LM2596',
   'Automatic zero tracking while both loads are off, time constant of twelve seconds'],
  ['Protection stopped during outage', 'Load shedding ceased when the broker was unreachable',
   'The reconnection routine used a blocking loop with delay, which stalled the control loop',
   'Non-blocking reconnection; the control loop was decoupled from network tasks'],
  ['Fundamentally wrong current computation', 'Readings biased high at small loads',
   'An RMS formula applied to a DC signal adds noise in quadrature',
   'Use the sample mean, which is correct for a DC load'],
  ['Device and web never met', 'Both reported a successful broker connection yet no data appeared',
   'The old topic tree used an underscore while the new one used a slash',
   'A single topic tree, with the topic name printed to the serial port for comparison'],
  ['Web deployment returned 404', 'The deployed page would not open',
   'The interface file lived in a subdirectory while the platform looked for it at the repository root',
   'Moved the interface file to the repository root'],
  ['Continuous switching', 'The auxiliary load cycled rapidly around the threshold',
   'A single threshold; after restoration the limit was exceeded again immediately',
   'Three simultaneous conditions: hysteresis, minimum time, predicted power after restoration'],
], [16, 22, 32, 30]));
body.push(cap('Table 12.1. Defects found and how they were resolved'));
body.push(p('The lesson is that in a distributed system a layer reporting success does not mean the system is working. The device reported a successful publish, the browser reported a successful connection, yet with two different topic names the data could never meet. The team therefore added observation points at every layer: the topic name printed to the serial port, the data freshness indicator on the interface, the backend status endpoint, and direct database queries.'));
body.push(pageBreak());

// --- 13 ---
body.push(h('13. LIMITATIONS', HeadingLevel.HEADING_1));
body.push(...bullets([
  'The public MQTT broker has no authentication; anyone who knows the topic names can read the data and send commands.',
  'The supply voltage is assumed to be a constant 12 V rather than measured, so the accuracy of the power figure depends on the stability of the supply.',
  'The 5 A ACS712 has limited resolution for loads below about 0.3 A; an INA219 or INA226 would perform considerably better in that range.',
  'A single sensor measures the total current, so the power of an individual load is only an estimate derived from the step observed at switching.',
  'The PubSubClient library only publishes at QoS 0; command reliability relies on the application-level acknowledgement mechanism.',
  'The offline buffer lives in RAM and is lost on reset; it could be upgraded to LittleFS storage.',
  'The free tier of the hosting service suspends the instance without traffic, so a periodic keep-alive task is required and short data gaps remain possible.',
]));

// --- 14 ---
body.push(h('14. CONCLUSION', HeadingLevel.HEADING_1));
body.push(p('The project delivers a complete IoT system for energy monitoring and intelligent load management, working end to end from the sensor to the web interface. It measures current and power with a documented calibration procedure, transmits data over MQTT with a structured topic hierarchy and availability detection, stores history in a time-series database with REST access, and provides a real-time dashboard that distinguishes requested state from confirmed state.'));
body.push(p('The most substantial technical contribution lies in control and reliability. The restoration mechanism based on three simultaneous conditions, including a prediction of the power after restoration, fully resolves the continuous switching that a single threshold cannot address. Decoupling the local control loop from network tasks, combined with a real-time clock and a store-and-forward buffer, preserves both the safety function and data integrity during a network outage.'));
body.push(p('Future work: migrate to an authenticated broker with TLS; replace the ACS712 with an INA226 to measure both voltage and current at higher resolution; extend the design to several measurement nodes with load coordination between them; and add short-term load forecasting so that shedding becomes anticipatory rather than reactive.'));

// --- 15 ---
body.push(h('15. REFERENCES', HeadingLevel.HEADING_1));
body.push(...[
  '[1] Allegro MicroSystems, "ACS712: Fully Integrated, Hall Effect-Based Linear Current Sensor IC", Datasheet, Rev. 18.',
  '[2] Espressif Systems, "ESP32-S3 Technical Reference Manual", 2024.',
  '[3] Espressif Systems, "ESP32-S3 Series Datasheet — ADC Characteristics and Calibration", 2024.',
  '[4] Espressif Systems, "ESP32-S3-DevKitC-1 v1.1 User Guide", esp-dev-kits documentation.',
  '[5] OASIS, "MQTT Version 5.0 — OASIS Standard", 2019.',
  '[6] Analog Devices, "DS3231 Extremely Accurate I2C-Integrated RTC/TCXO/Crystal", Datasheet.',
  '[7] Solomon Systech, "SSD1306 Advance Information — 128x64 Dot Matrix OLED/PLED Driver".',
  '[8] S. Ramirez, "FastAPI Documentation", https://fastapi.tiangolo.com',
  '[9] Eclipse Foundation, "Eclipse Paho MQTT Python Client Documentation".',
  '[10] N. O\'Leary, "PubSubClient — Arduino Client for MQTT", https://pubsubclient.knolleary.net',
  '[11] B. Blanchon, "ArduinoJson Documentation", https://arduinojson.org',
  '[12] K. Ogata, "Modern Control Engineering", 5th ed., Prentice Hall, 2010 (on-off control and hysteresis).',
].map(t => new Paragraph({
  spacing: { after: 100, line: 276 }, alignment: AlignmentType.JUSTIFIED,
  indent: { left: convertInchesToTwip(0.35), hanging: convertInchesToTwip(0.35) },
  children: [new TextRun({ text: t, font: FONT, size: 26 })],
})));

// --- 16 ---
body.push(h('16. TEAM CONTRIBUTIONS', HeadingLevel.HEADING_1));
body.push(table([
  ['No.', 'Full name', 'Student ID', 'Responsibilities', 'Contribution'],
  ['1', 'Dang Dinh Manh', '24119055', 'Circuit design, ESP32-S3 firmware, load management algorithm', ''],
  ['2', '', '', 'FastAPI backend, database, service deployment', ''],
  ['3', '', '', 'Web dashboard, data assistant, user interface', ''],
  ['4', '', '', 'Experiments, error and latency measurement, report writing', ''],
], [8, 26, 16, 36, 14]));
body.push(cap('Table 16.1. Task allocation'));
body.push(p('Full source code: https://github.com/JackGamerCYT/IOT-PROJECT3-'));

// ---------------------------- APPENDICES ----------------------------
body.push(pageBreak());
body.push(h('APPENDIX A. COMPLETE ESP32-S3 FIRMWARE SOURCE', HeadingLevel.HEADING_1));
body.push(p('File firmware/esp32_firmware/esp32_firmware.ino. Built with the Arduino IDE, board ESP32S3 Dev Module, two libraries: PubSubClient and ArduinoJson. Wi-Fi credentials live in a separate secrets.h file and are therefore absent from the public repository.',
            { italics: true }));
body.push(...codeBlock(srcAll('firmware/esp32_firmware/esp32_firmware.ino'), 13));

body.push(pageBreak());
body.push(h('APPENDIX B. COMPLETE BACKEND SOURCE', HeadingLevel.HEADING_1));
body.push(p('File backend/main.py. Runs on FastAPI with Uvicorn, using paho-mqtt and psycopg. Without the DATABASE_URL variable it uses SQLite; with it, PostgreSQL.',
            { italics: true }));
body.push(...codeBlock(srcAll('backend/main.py'), 13));

body.push(pageBreak());
body.push(h('APPENDIX C. DATA ASSISTANT SOURCE', HeadingLevel.HEADING_1));
body.push(p('Extracted from backend/main.py: intent classification and answer generation from database queries.',
            { italics: true }));
body.push(...codeBlock(srcBetween('backend/main.py', 'def chat_answer(question: str) -> dict:',
                                  'class ChatIn(BaseModel):', 400), 13));

body.push(pageBreak());
body.push(h('APPENDIX D. DASHBOARD SOURCE (EXTRACT)', HeadingLevel.HEADING_1));
body.push(p('Extracted from index.html: telemetry handling, command dispatch and acknowledgement matching.',
            { italics: true }));
body.push(...codeBlock(srcBetween('index.html', 'function onTelemetry(d) {', 'let configTouched', 60), 13));
body.push(...codeBlock(srcBetween('index.html', 'function publishCmd(body, onDone)', 'window.sendLoad', 60), 13));

body.push(pageBreak());
body.push(h('APPENDIX E. EXPERIMENT DATA SHEETS', HeadingLevel.HEADING_1));
body.push(p('Print these sheets to record readings on the bench, then transfer them into chapter 11.',
            { italics: true }));
body.push(h('E1. Current measurement error', HeadingLevel.HEADING_2));
body.push(table([
  ['Run', 'No load (A)', 'Fan (A)', 'Lamp (A)', 'Both (A)', 'Reference (A)'],
  ...Array.from({ length: 10 }, (_, i) => [String(i + 1), '', '', '', '', '']),
  ['Mean', '', '', '', '', ''],
  ['Std. dev.', '', '', '', '', ''],
], [14, 18, 16, 16, 18, 18]));
body.push(h('E2, E3. Latency', HeadingLevel.HEADING_2));
body.push(table([
  ['Run', 'Device → dashboard (ms)', 'Command → ack (ms)', 'Notes'],
  ...Array.from({ length: 10 }, (_, i) => [String(i + 1), '', '', '']),
  ['Mean', '', '', ''],
  ['95th percentile', '', '', ''],
], [10, 30, 30, 30]));
body.push(h('E4. Managed versus unmanaged operation', HeadingLevel.HEADING_2));
body.push(table([
  ['Metric over 10 minutes', 'Unmanaged', 'Managed', 'Difference (%)'],
  ['Peak power (W)', '', '', ''],
  ['Energy (Wh)', '', '', ''],
  ['Time above limit (s)', '', '', ''],
  ['Switching operations', '', '', ''],
  ['Packet success rate (%)', '', '', ''],
], [34, 22, 22, 22]));
body.push(h('E6. Network loss and recovery', HeadingLevel.HEADING_2));
body.push(table([
  ['Observation', 'Result'],
  ['Time of disconnection', ''],
  ['Time the badge turned OFFLINE', ''],
  ['Local shedding behaviour during the outage', ''],
  ['Time of reconnection', ''],
  ['Records forwarded', ''],
  ['Residual gap on the chart (s)', ''],
], [58, 42]));

// ===================================================================================
const doc = new Document({
  creator: 'Project 03 Team',
  title: 'IoT Project 03 - Smart Energy Monitoring and Intelligent Load Management',
  numbering: {
    config: [{
      reference: 'bul',
      levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: convertInchesToTwip(0.35), hanging: convertInchesToTwip(0.2) } } } }],
    }],
  },
  styles: {
    default: { document: { run: { font: FONT, size: 26 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { font: FONT, size: 30, bold: true, color: '1a3b5c' },
        paragraph: { spacing: { before: 280, after: 140 } } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { font: FONT, size: 27, bold: true, color: '1a3b5c' },
        paragraph: { spacing: { before: 200, after: 100 } } },
    ],
  },
  sections: [{
    properties: { page: { margin: { top: 1440, right: 1080, bottom: 1440, left: 1440 } } },
    headers: {
      default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
        children: [new TextRun({ text: 'IoT Project 03 — Smart Energy Monitoring & Intelligent Load Management',
                                 font: FONT, size: 18, italics: true, color: '666666' })] })] }),
    },
    footers: {
      default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
        children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 20 })] })] }),
    },
    children: body,
  }],
});

Packer.toBuffer(doc).then(b => {
  fs.writeFileSync(process.argv[2] || 'docs/REPORT_IOT_PROJECT03_EN.docx', b);
  console.log('OK');
});
