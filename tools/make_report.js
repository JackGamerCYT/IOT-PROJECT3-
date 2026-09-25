/* Sinh báo cáo đồ án: node tools/make_report.js  ->  docs/BAO_CAO_IOT_PROJECT03.docx */
const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, PageBreak, TableOfContents, Header, Footer, PageNumber,
  LevelFormat, convertInchesToTwip,
} = require('docx');

const FONT = 'Times New Roman';
const W = 9360; // bề rộng bảng (DXA) cho lề 1 inch trên khổ A4

const p = (text, o = {}) => new Paragraph({
  alignment: o.align || AlignmentType.JUSTIFIED,
  spacing: { after: o.after ?? 120, line: 276 },
  indent: o.indent,
  children: [new TextRun({ text, font: FONT, size: o.size || 26, bold: o.bold, italics: o.italics })],
});

const h = (text, level) => new Paragraph({
  heading: level,
  spacing: { before: 240, after: 120 },
  children: [new TextRun({ text, font: FONT, size: level === HeadingLevel.HEADING_1 ? 30 : 27, bold: true, color: '1a3b5c' })],
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

const path = require('path');
const ROOT = path.join(__dirname, '..');

function srcLines(file) {
  return fs.readFileSync(path.join(ROOT, file), 'utf8').replace(/\r/g, '').split('\n');
}

/** Lấy đoạn mã giữa 2 chuỗi mốc (kể cả dòng mốc đầu), dùng để trích hàm. */
function srcBetween(file, startMark, endMark, maxLines = 200) {
  const L = srcLines(file);
  const i = L.findIndex(x => x.includes(startMark));
  if (i < 0) return ['(khong tim thay: ' + startMark + ')'];
  let j = L.findIndex((x, k) => k > i && x.includes(endMark));
  if (j < 0) j = Math.min(L.length, i + maxLines);
  return L.slice(i, j + 1);
}

/** Toàn bộ file, kèm số dòng. */
function srcAll(file) {
  return srcLines(file).map((l, i) => String(i + 1).padStart(4, ' ') + ' | ' + l);
}

/** In khối mã dài, cỡ chữ nhỏ, tự xuống trang. */
function codeBlock(lines, size = 14) {
  return lines.map((l, i) => new Paragraph({
    spacing: { after: 0, line: 200 },
    children: [new TextRun({ text: l.replace(/\t/g, '    ') || ' ', font: 'Consolas', size })],
  }));
}

const pageBreak = () => new Paragraph({ children: [new PageBreak()] });

// ===================================================================================
const body = [];
const bl = (n = 1) => { for (let i = 0; i < n; i++) body.push(p('')); };

// --- TRANG BÌA ---
bl(2);
body.push(p('TRƯỜNG ĐẠI HỌC SƯ PHẠM KỸ THUẬT TP. HỒ CHÍ MINH', { align: AlignmentType.CENTER, bold: true, size: 26 }));
body.push(p('KHOA ĐIỆN – ĐIỆN TỬ', { align: AlignmentType.CENTER, bold: true, size: 26 }));
bl(3);
body.push(p('BÁO CÁO ĐỒ ÁN CUỐI KỲ', { align: AlignmentType.CENTER, bold: true, size: 32 }));
body.push(p('MÔN: IOT FOUNDATIONS AND APPLICATIONS', { align: AlignmentType.CENTER, bold: true, size: 28 }));
bl(1);
body.push(p('ĐỀ TÀI 03: GIÁM SÁT ĐIỆN NĂNG VÀ QUẢN LÝ TẢI THÔNG MINH', { align: AlignmentType.CENTER, bold: true, size: 30 }));
body.push(p('(Smart Energy Monitoring and Intelligent Load Management)', { align: AlignmentType.CENTER, italics: true, size: 26 }));
bl(4);
body.push(p('Nhóm sinh viên thực hiện:', { align: AlignmentType.CENTER, bold: true }));
body.push(p('Đặng Đình Mạnh – 24119055', { align: AlignmentType.CENTER }));
body.push(p('……………………… – …………', { align: AlignmentType.CENTER }));
body.push(p('……………………… – …………', { align: AlignmentType.CENTER }));
body.push(p('……………………… – …………', { align: AlignmentType.CENTER }));
bl(3);
body.push(p('Giảng viên hướng dẫn: ………………………', { align: AlignmentType.CENTER }));
body.push(p('TP. Hồ Chí Minh, tháng 9 năm 2026', { align: AlignmentType.CENTER, italics: true }));
body.push(new Paragraph({ children: [new PageBreak()] }));

// --- MỤC LỤC ---
body.push(h('MỤC LỤC', HeadingLevel.HEADING_1));
body.push(new TableOfContents('Mục lục', { hyperlink: true, headingStyleRange: '1-2' }));
body.push(p('(Mở file trong Word, bấm chuột phải vào mục lục → Update Field → Update entire table để sinh số trang.)', { italics: true, size: 22 }));
body.push(new Paragraph({ children: [new PageBreak()] }));

// --- 1 ---
body.push(h('1. GIỚI THIỆU VÀ BÀI TOÁN', HeadingLevel.HEADING_1));
body.push(p('Nhu cầu điện của hộ gia đình và phòng thí nghiệm nhỏ thường vượt ngưỡng an toàn trong những khoảng ngắn, khi nhiều thiết bị cùng hoạt động. Hệ quả là nhảy aptomat, hao phí điện năng và rút ngắn tuổi thọ dây dẫn. Người dùng lại hiếm khi biết chính xác mình đang tiêu thụ bao nhiêu, vào lúc nào, và thiết bị nào nên được cắt trước khi vượt ngưỡng.'));
body.push(p('Đồ án xây dựng một hệ thống IoT hoàn chỉnh giải quyết bài toán trên ở quy mô mô hình an toàn: đo dòng điện và công suất của hai tải một chiều 12 V theo thời gian thực, lưu lịch sử vào cơ sở dữ liệu chuỗi thời gian, hiển thị trên giao diện web, tự động sa thải tải ưu tiên thấp khi công suất vượt ngưỡng đỉnh và khôi phục khi điều kiện đã an toàn ổn định.'));
body.push(p('Mục tiêu cụ thể:', { bold: true }));
body.push(...bullets([
  'Đo dòng và công suất với sai số được định lượng, không chấp nhận giá trị ADC thô làm kết quả cuối.',
  'Truyền số liệu bằng MQTT với cây topic có cấu trúc, phát hiện thiết bị online/offline bằng cơ chế Last Will and Testament.',
  'Lưu trữ chuỗi thời gian và cung cấp REST API cho lịch sử, cấu hình và thống kê.',
  'Quản lý tải theo mức ưu tiên, có cơ chế chống đóng cắt liên tục và vẫn hoạt động khi mất kết nối mạng.',
  'Cung cấp dashboard thời gian thực, phân biệt rõ trạng thái được yêu cầu và trạng thái đã được thiết bị xác nhận.',
  'Bổ sung thành phần nâng cao: phát hiện đỉnh công suất và ngân sách điện năng theo ngày.',
]));
body.push(p('Phạm vi: toàn bộ mạch động lực làm việc ở 12 VDC, không có phần nào tiếp xúc điện lưới, phù hợp yêu cầu an toàn của đề bài.'));

// --- 2 ---
body.push(h('2. YÊU CẦU VÀ CƠ SỞ LÝ THUYẾT', HeadingLevel.HEADING_1));
body.push(h('2.1. Bảng đối chiếu yêu cầu', HeadingLevel.HEADING_2));
body.push(table([
  ['Yêu cầu của đề', 'Giải pháp trong đồ án'],
  ['Đo dòng/điện năng cách ly, điện áp thấp', 'Cảm biến Hall ACS712-05B, tải DC 12 V'],
  ['Ít nhất hai tải điều khiển được', 'Quạt 12 V (ưu tiên cao) và đèn LED 12 V (ưu tiên thấp)'],
  ['MQTT có cấu trúc topic, QoS, trạng thái sẵn sàng', 'Sáu topic dưới smartenergy/node9988, LWT retained'],
  ['CSDL chuỗi thời gian và REST API', 'SQLite hoặc PostgreSQL, năm bảng, mười hai endpoint'],
  ['Dashboard đầy đủ chỉ số và cảnh báo', 'Giao diện web thời gian thực, biểu đồ, nhật ký sự kiện'],
  ['Quản lý tải theo ưu tiên, chống đóng cắt liên tục', 'Máy trạng thái với trễ, thời gian tối thiểu và dự báo công suất'],
  ['Phân biệt lệnh yêu cầu và trạng thái xác nhận', 'Cơ chế cmd_id và bản tin ack'],
  ['Thành phần nâng cao', 'Phát hiện đỉnh công suất và ngân sách điện năng ngày'],
  ['Hành vi an toàn khi mất mạng', 'Chế độ an toàn cục bộ, RTC giữ giờ, bộ đệm gửi bù'],
], [40, 60]));
body.push(cap('Bảng 2.1. Đối chiếu yêu cầu đề bài và giải pháp'));

body.push(h('2.2. Nguyên lý cảm biến dòng hiệu ứng Hall', HeadingLevel.HEADING_2));
body.push(p('ACS712 dẫn dòng tải qua một đường dẫn đồng tích hợp. Từ trường sinh ra tỉ lệ với dòng điện được cảm nhận bởi phần tử Hall và chuyển thành điện áp ra. Bản 5 A có độ nhạy 185 mV/A và điện áp ra ở 0 A bằng một nửa điện áp nguồn, tức 2.5 V khi cấp 5 V. Đường dẫn dòng cách ly về điện với mạch tín hiệu, điện áp chịu đựng danh định 2.1 kV, đây là lý do cảm biến này phù hợp với yêu cầu "isolated measurement" của đề.'));
body.push(p('Dòng điện được suy ra theo công thức:'));
body.push(...code(['I [A] = (V_out − V_zero) / 0.185', '', 'V_out : điện áp tại chân OUT (V)', 'V_zero: điện áp ra khi dòng bằng 0, xác định bằng hiệu chuẩn']));
body.push(p('Vì tải là một chiều, giá trị trung bình của nhiều mẫu phản ánh đúng dòng tải; không cần tính hiệu dụng RMS như với tải xoay chiều. Trái lại, nếu áp dụng công thức RMS cho tín hiệu một chiều có nhiễu, nhiễu sẽ cộng theo bình phương và làm kết quả cao hơn giá trị thật, đây là lỗi đã được phát hiện và sửa trong quá trình thực hiện đồ án.'));

body.push(h('2.3. Công suất và điện năng', HeadingLevel.HEADING_2));
body.push(...code(['P [W] = U × I          (U = 12 V, coi là hằng số)', 'E [Wh] = Σ P × Δt / 3600', 'Chi phí [đ] = E/1000 × đơn giá [đ/kWh]']));
body.push(p('Backend tính lại điện năng bằng tích phân hình thang trên chuỗi telemetry để đối chiếu với giá trị tích lũy trên thiết bị; khoảng mất dữ liệu dài hơn 10 giây không được tính vào tích phân nhằm tránh suy diễn sai khi mất kết nối.'));

body.push(h('2.4. Lý thuyết điều khiển có trễ và chống đóng cắt liên tục', HeadingLevel.HEADING_2));
body.push(p('Một bộ điều khiển chỉ dùng một ngưỡng duy nhất sẽ dao động liên tục khi đại lượng đo nằm quanh ngưỡng đó. Cách khắc phục kinh điển là thêm dải trễ (hysteresis): cắt tải khi P > P_peak nhưng chỉ khôi phục khi P < P_peak − H. Với hệ thống này, riêng dải trễ vẫn chưa đủ, vì bản thân việc khôi phục tải làm công suất tăng trở lại và có thể vượt ngưỡng ngay lập tức. Đồ án vì vậy áp dụng đồng thời ba điều kiện: dải trễ theo công suất, thời gian duy trì tối thiểu theo thời gian, và một bước dự báo công suất sau khi khôi phục.'));

body.push(h('2.5. Giao thức MQTT', HeadingLevel.HEADING_2));
body.push(p('MQTT là giao thức publish/subscribe chạy trên TCP, phù hợp cho thiết bị nhúng nhờ gói tin nhỏ và kết nối duy trì lâu dài. Ba mức chất lượng dịch vụ: QoS 0 gửi tối đa một lần, QoS 1 bảo đảm ít nhất một lần, QoS 2 bảo đảm đúng một lần. Cơ chế Last Will and Testament cho phép broker tự công bố một bản tin định trước khi mất kết nối với thiết bị, nhờ đó phát hiện được sự cố mà không cần thăm dò định kỳ. Cờ retained giúp một client vừa đăng ký nhận ngay bản tin gần nhất của topic.'));
body.push(new Paragraph({ children: [new PageBreak()] }));

// --- 3 ---
body.push(h('3. KIẾN TRÚC HỆ THỐNG', HeadingLevel.HEADING_1));
body.push(...code([
  '[Adapter 12V]-[cầu chì 2A]-+-[LM2596 -> 5V]-> ESP32-S3, ACS712,',
  '                           |                   relay, OLED, DS3231',
  '                           +-[ACS712]-+-[Relay 1]- Quạt 12V (ưu tiên CAO)',
  '                                      +-[Relay 2]- LED 12V  (ưu tiên THẤP)',
  '',
  'ESP32-S3: đo 4 khối/giây, điều khiển cục bộ 2 s/lần,',
  '          RTC giữ giờ, đệm 600 bản ghi khi mất mạng',
  '   | MQTT 1883   smartenergy/node9988/{telemetry,status,state,event,cmd,ack}',
  '   v',
  'Broker MQTT --WSS 8884--> Dashboard (Vercel): realtime, gửi lệnh,',
  '                                                đo độ trễ',
  '   | MQTT 1883',
  '   v',
  'Backend FastAPI (Render 24/7) -- SQLite / PostgreSQL (Neon)',
  '                               -- REST /api/* + trợ lý dữ liệu /api/chat',
]));
body.push(cap('Hình 3.1. Kiến trúc tổng thể hệ thống'));
body.push(p('Hệ thống gồm bốn lớp. Lớp thiết bị (ESP32-S3) chịu trách nhiệm đo lường và điều khiển thời gian thực; mọi quyết định đóng cắt đều được thực hiện tại đây nên không phụ thuộc vào mạng. Lớp truyền thông là broker MQTT, đóng vai trò trung gian giữa thiết bị, backend và giao diện. Lớp dữ liệu là backend FastAPI: đăng ký nhận mọi topic, ghi vào cơ sở dữ liệu và cung cấp REST API. Lớp ứng dụng là dashboard web, nhận số liệu tức thời trực tiếp từ broker qua WebSocket Secure và lấy dữ liệu lịch sử từ REST API.'));
body.push(p('Một điểm thiết kế cần nhấn mạnh: dashboard được triển khai trên Vercel, là nền tảng chỉ phục vụ tệp tĩnh và hàm serverless có vòng đời vài giây cho mỗi yêu cầu. Nền tảng này không thể duy trì một kết nối MQTT liên tục để hứng telemetry, do đó tiến trình ingest bắt buộc phải chạy ở một dịch vụ luôn hoạt động (Render hoặc máy tính cục bộ). Việc tách worker ingest khỏi giao diện là hệ quả kỹ thuật chứ không phải lựa chọn tùy ý.'));
body.push(p('Luồng dữ liệu chính: ESP32 đo và publish telemetry mỗi 2 giây; backend ghi vào bảng telemetry kèm hai mốc thời gian (thời điểm thiết bị tạo gói và thời điểm máy chủ nhận), nhờ đó đo được độ trễ đầu cuối. Luồng điều khiển đi theo chiều ngược lại: dashboard hoặc REST API publish lệnh lên topic cmd, thiết bị áp dụng rồi publish bản tin ack; backend ghi lại cả lệnh lẫn xác nhận, tính độ trễ giữa hai mốc.'));

// --- 4 ---
body.push(h('4. PHẦN CỨNG', HeadingLevel.HEADING_1));
body.push(h('4.1. Danh mục linh kiện', HeadingLevel.HEADING_2));
body.push(table([
  ['STT', 'Linh kiện', 'Thông số chính', 'Vai trò'],
  ['1', 'ESP32-S3 DevKitC N16R8', 'Xtensa LX7 dual-core 240 MHz, WiFi, ADC 12-bit', 'Vi điều khiển trung tâm'],
  ['2', 'ACS712-05B', '±5 A, 185 mV/A, cách ly 2.1 kV', 'Đo dòng tải'],
  ['3', 'Module relay 2 kênh 5 V', 'Opto cách ly, kích mức thấp, 10 A/30 VDC', 'Đóng cắt hai tải'],
  ['4', 'LM2596', 'Vào 4–35 V, ra 5.0 V, 3 A', 'Hạ áp nuôi mạch điều khiển'],
  ['5', 'DS3231', 'RTC I2C, ±2 ppm, pin dự phòng', 'Giữ giờ khi mất mạng'],
  ['6', 'OLED SSD1306', '0.96 inch, 128×64, I2C', 'Hiển thị tại chỗ'],
  ['7', 'Quạt DC 12 V', 'khoảng 0.2–0.4 A', 'Tải 1, ưu tiên cao'],
  ['8', 'LED bar 12 V', 'khoảng 0.1–0.3 A', 'Tải 2, ưu tiên thấp'],
  ['9', 'Adapter 12 V – 2 A', '', 'Nguồn chính'],
  ['10', 'Cầu chì 2 A, diode 1N4007, R 10 kΩ/20 kΩ', '', 'Bảo vệ và phân áp ADC'],
], [8, 30, 32, 30]));
body.push(cap('Bảng 4.1. Danh mục linh kiện'));

body.push(h('4.2. Sơ đồ chân', HeadingLevel.HEADING_2));
body.push(table([
  ['Linh kiện', 'Chân', 'ESP32-S3', 'Chức năng'],
  ['ACS712', 'OUT (qua phân áp 10 kΩ/20 kΩ)', 'GPIO 1 (ADC1_CH0)', 'Tín hiệu analog đo dòng'],
  ['Relay 2CH', 'IN1', 'GPIO 12', 'Tải 1 – Quạt 12 V'],
  ['Relay 2CH', 'IN2', 'GPIO 13', 'Tải 2 – LED 12 V'],
  ['DS3231 (0x68)', 'SDA / SCL', 'GPIO 8 / GPIO 9', 'Đồng hồ thời gian thực'],
  ['SSD1306 (0x3C)', 'SDA / SCL', 'GPIO 8 / GPIO 9', 'Hiển thị, chung bus I2C'],
  ['Buzzer qua S8050', 'Base qua R 1 kΩ', 'GPIO 14', 'Báo động vượt ngưỡng'],
  ['LM2596', 'OUT+ / OUT−', '5V / GND', 'Cấp nguồn 5 V'],
], [24, 28, 22, 26]));
body.push(cap('Bảng 4.2. Bảng kết nối chân'));

body.push(h('4.3. Thiết kế bảo vệ và các quyết định kỹ thuật', HeadingLevel.HEADING_2));
body.push(...bullets([
  'Cầu phân áp 10 kΩ/20 kΩ tại đầu ra ACS712: tại 5 A điện áp ra đạt 3.43 V, vượt dải đo an toàn của ADC ESP32-S3. Hệ số 0.667 đưa dải 0–5 V về 0–3.33 V.',
  'Cầu chì 2 A trên đường +12 V, đặt trước cảm biến, bảo vệ toàn bộ mạch động lực.',
  'Diode 1N4007 mắc ngược song song với quạt để triệt sức điện động ngược khi ngắt tải cảm.',
  'Tiếp điểm relay 10 A/30 VDC, lớn hơn nhiều lần dòng tải thực tế dưới 1 A, bảo đảm biên an toàn.',
  'Tháo jumper JD-VCC của module relay và cấp VCC 3.3 V để mức logic cao của ESP32 tắt được opto hoàn toàn.',
  'Chọn ESP32-S3 thay cho ESP32 classic vì GPIO 12 trên bản classic là chân strapping MTDI, mức cao lúc khởi động sẽ đặt sai điện áp flash và gây lỗi nạp.',
  'Module LM2596 lấy nguồn ở phía trước cảm biến để dòng tiêu thụ của mạch điều khiển không bị tính vào kết quả đo của tải.',
]));

// --- 5 ---
body.push(h('5. GIAO THỨC VÀ MẠNG', HeadingLevel.HEADING_1));
body.push(h('5.1. Cây topic và chất lượng dịch vụ', HeadingLevel.HEADING_2));
body.push(table([
  ['Topic', 'Hướng', 'QoS / retain', 'Nội dung'],
  ['smartenergy/node9988/telemetry', 'Thiết bị → hệ thống', 'QoS 0', 'Số liệu đo, chu kỳ 2 giây'],
  ['smartenergy/node9988/status', 'Thiết bị → hệ thống', 'QoS 1, retained, LWT', 'online / offline'],
  ['smartenergy/node9988/state', 'Thiết bị → hệ thống', 'retained', 'Cấu hình và trạng thái tải'],
  ['smartenergy/node9988/event', 'Thiết bị → hệ thống', 'QoS 0', 'Sa thải, khôi phục, cảnh báo'],
  ['smartenergy/node9988/cmd', 'Web/Backend → thiết bị', 'QoS 1', 'Lệnh kèm cmd_id'],
  ['smartenergy/node9988/ack', 'Thiết bị → hệ thống', 'QoS 0', 'Xác nhận lệnh và trạng thái thực tế'],
], [34, 22, 20, 24]));
body.push(cap('Bảng 5.1. Đặc tả cây topic MQTT'));
body.push(p('Telemetry dùng QoS 0 vì bản tin sau thay thế hoàn toàn bản tin trước; mất mát được phát hiện qua trường seq tăng đơn điệu, từ đó tính được tỉ lệ nhận gói mà không cần chi phí bắt tay của QoS 1. Lệnh điều khiển dùng QoS 1 ở chiều đăng ký. Thư viện PubSubClient trên ESP32 chỉ hỗ trợ publish ở QoS 0, vì vậy độ tin cậy của lệnh được bảo đảm ở tầng ứng dụng bằng cặp cmd_id/ack kèm thời gian chờ 5 giây, đây là một hạn chế đã biết và được nêu ở mục 12.'));

body.push(h('5.2. Định dạng bản tin', HeadingLevel.HEADING_2));
body.push(...code([
  '{"dev":"node9988","ts":1789550319106,"seq":42,',
  ' "current_a":0.352,"power_w":4.224,"energy_today_wh":0.0931,',
  ' "energy_total_wh":1.204,"peak_today_w":4.301,',
  ' "fan":true,"led":true,"led_shed":"NONE","auto_mode":true,"safe_mode":false,',
  ' "peak_limit_w":3.5,"hysteresis_w":0.5,"budget_wh":0,"led_est_w":1.8,',
  ' "alarm_over":false,"alarm_budget":false,"sensor_mv":2565.1,"zero_mv":2500.0,',
  ' "rssi":-55,"uptime_s":84,"time_src":"ntp","rtc":true,"buffered_count":0}',
]));
body.push(p('Trường ts là thời gian Unix theo mili giây lấy từ NTP hoặc DS3231. Mọi bản tin đều mang định danh thiết bị, nhờ đó hệ thống mở rộng cho nhiều node mà không phải đổi cấu trúc.'));

body.push(h('5.3. Phát hiện trạng thái sẵn sàng', HeadingLevel.HEADING_2));
body.push(p('Khi kết nối, thiết bị đăng ký di chúc "offline" trên topic status với cờ retained, rồi tự publish "online". Nếu thiết bị mất điện hoặc rớt mạng, broker tự công bố "offline" sau khi hết thời gian keepalive 15 giây. Dashboard và backend nhờ đó biết chính xác thời điểm thiết bị ngừng hoạt động. Ngoài ra dashboard còn theo dõi độ tươi của dữ liệu: quá 6 giây, tức ba chu kỳ telemetry, mà không nhận được gói mới thì hiển thị cảnh báo dữ liệu cũ.'));

// --- 6 ---
body.push(h('6. BACKEND VÀ DỮ LIỆU', HeadingLevel.HEADING_1));
body.push(h('6.1. Lược đồ cơ sở dữ liệu', HeadingLevel.HEADING_2));
body.push(table([
  ['Bảng', 'Cột chính', 'Ý nghĩa'],
  ['telemetry', 'ts_device, ts_server, seq, current_a, power_w, energy_today_wh, peak_today_w, fan, led, led_shed, auto_mode, safe_mode, peak_limit_w, alarm_over, sensor_mv, rssi', 'Chuỗi thời gian số liệu đo'],
  ['events', 'ts_device, ts_server, type, detail, power_w, limit_w', 'Sa thải, khôi phục, cảnh báo'],
  ['availability', 'ts_server, status', 'Lịch sử online/offline'],
  ['commands', 'cmd_id, source, payload, ts_client, ts_seen_server, ts_ack_server, ack_ok, latency_ms', 'Nhật ký lệnh và độ trễ xác nhận'],
  ['settings', 'key, value', 'Đơn giá điện'],
], [18, 52, 30]));
body.push(cap('Bảng 6.1. Lược đồ cơ sở dữ liệu'));
body.push(p('Backend hỗ trợ đồng thời SQLite (chạy trên máy cá nhân) và PostgreSQL (dịch vụ Neon khi triển khai 24/7). Lớp truy cập dữ liệu tự chuyển đổi cú pháp giữa hai hệ quản trị, nhờ đó cùng một mã nguồn chạy được ở cả hai môi trường. Dữ liệu cũ hơn số ngày cấu hình được dọn định kỳ để phù hợp dung lượng miễn phí của Neon.'));

body.push(h('6.2. Các endpoint REST chính', HeadingLevel.HEADING_2));
body.push(table([
  ['Endpoint', 'Chức năng'],
  ['GET /api/status', 'Telemetry mới nhất, trạng thái online, độ tươi dữ liệu, điện năng và chi phí trong ngày'],
  ['GET /api/history?minutes=&bucket_s=', 'Chuỗi thời gian đã gộp theo khoảng, giới hạn 300 điểm'],
  ['GET /api/energy/daily?days=', 'Điện năng, đỉnh và chi phí theo từng ngày'],
  ['GET /api/events | /api/availability | /api/commands', 'Các nhật ký'],
  ['POST /api/command', 'Gửi lệnh, chờ xác nhận, trả về cả trạng thái yêu cầu và đã xác nhận'],
  ['POST /api/config', 'Ngưỡng đỉnh, dải trễ, ngân sách, chế độ tự động'],
  ['GET /api/stats?minutes=', 'Thống kê phục vụ thực nghiệm'],
  ['POST /api/chat', 'Trợ lý dữ liệu'],
  ['GET /api/export/{bảng}.csv', 'Xuất dữ liệu phục vụ báo cáo'],
], [38, 62]));
body.push(cap('Bảng 6.2. Danh mục REST API'));
body.push(p('Endpoint /api/stats tổng hợp trong một khoảng thời gian: đỉnh công suất, công suất trung bình, điện năng, tổng thời gian vượt ngưỡng, số lần đóng cắt tải, tỉ lệ nhận gói suy ra từ khoảng trống của seq, độ trễ thiết bị đến máy chủ và độ trễ lệnh đến xác nhận theo giá trị trung bình, phân vị 95 và giá trị lớn nhất. Đây chính là bộ số liệu dùng cho chương thực nghiệm.'));

// --- 7 ---
body.push(h('7. ỨNG DỤNG VÀ GIAO DIỆN', HeadingLevel.HEADING_1));
body.push(p('Dashboard là một trang web đơn, nhận số liệu tức thời trực tiếp từ broker qua WebSocket Secure và lấy lịch sử từ REST API. Cách này giúp giao diện vẫn hiển thị thời gian thực ngay cả khi backend tạm ngừng, chỉ mất phần lịch sử.'));
body.push(...bullets([
  'Sáu thẻ chỉ số: công suất tức thời kèm ngưỡng, dòng điện, điện năng trong ngày kèm thanh tiến độ ngân sách, chi phí ước tính, đỉnh công suất trong ngày, chế độ quản lý tải.',
  'Đồ thị thời gian thực năm phút gần nhất với ba đường: công suất, ngưỡng đỉnh và dòng điện; trục trái theo W, trục phải theo A.',
  'Khung điều khiển hai tải, hiển thị tách bạch trạng thái được yêu cầu và trạng thái đã được thiết bị xác nhận, kèm độ trễ xác nhận và cảnh báo khi quá thời gian chờ.',
  'Khung cấu hình: chế độ tự động, ngưỡng đỉnh, dải trễ, ngân sách ngày, hiệu chuẩn điểm không, đặt lại điện năng, đơn giá điện.',
  'Nhật ký cảnh báo và sự kiện, hợp nhất dữ liệu thời gian thực với lịch sử lấy từ backend.',
  'Khung lịch sử: biểu đồ công suất theo 1 giờ, 6 giờ, 24 giờ, 7 ngày và biểu đồ cột điện năng bảy ngày gần nhất.',
  'Khung đo đạc thực nghiệm: độ trễ hai chiều, tỉ lệ nhận gói, số lệnh chưa xác nhận, nút lấy thống kê và xuất CSV.',
  'Trợ lý dữ liệu và cửa sổ nhật ký MQTT phục vụ gỡ lỗi khi trình diễn.',
]));
body.push(p('Màn hình OLED tại chỗ hiển thị giờ lấy từ DS3231, công suất, dòng điện, điện năng trong ngày, ngưỡng, trạng thái hai tải, biểu tượng WiFi và MQTT, số bản ghi đang nằm trong bộ đệm. Nhờ vậy khi trình diễn vẫn chứng minh được thiết bị hoạt động độc lập với mạng.'));
body.push(h('7.1. Trợ lý dữ liệu', HeadingLevel.HEADING_2));
body.push(p('Trợ lý chạy hoàn toàn cục bộ trong backend. Câu hỏi được chuẩn hóa bằng cách bỏ dấu tiếng Việt, phân loại ý định bằng biểu thức chính quy, sau đó truy vấn trực tiếp cơ sở dữ liệu và ghép câu trả lời từ số liệu thật. Vì không sinh văn bản tự do nên không tồn tại nguy cơ bịa số, khác với cách gọi mô hình ngôn ngữ lớn.'));
body.push(p('Với câu mang tính điều khiển, hệ thống không tự thực thi mà trả về mô tả hành động; giao diện hiện nút xác nhận, người dùng bấm thì lệnh mới được gửi. Đây là ràng buộc an toàn bắt buộc khi cho phép ngôn ngữ tự nhiên tác động lên relay.'));

body.push(h('7.2. Mã nguồn khâu thu nhận dữ liệu ở backend', HeadingLevel.HEADING_2));
body.push(p('Backend đăng ký toàn bộ sáu topic. Với bản tin telemetry, điểm đáng chú ý là cách xử lý gói gửi bù: gói mang cờ "buffered" sẽ dùng mốc thời gian của thiết bị làm mốc lưu trữ, nhờ đó dữ liệu ghi bù sau khi mất mạng nằm đúng vị trí trên đồ thị lịch sử thay vì dồn cục vào thời điểm nhận.'));
body.push(...codeBlock(srcBetween('backend/main.py', 'def on_message(client, userdata, msg):',
  'print(f"[MQTT] bad message')));

body.push(h('7.3. Mã nguồn lớp truy cập cơ sở dữ liệu', HeadingLevel.HEADING_2));
body.push(p('Lớp DB cho phép cùng một mã nguồn chạy được trên SQLite khi phát triển và PostgreSQL khi triển khai, bằng cách chuyển đổi ký hiệu tham số và cú pháp chèn có điều kiện:'));
body.push(...codeBlock(srcBetween('backend/main.py', 'class DB:', 'def init_schema(self):')));

body.push(h('7.4. Mã nguồn đồ thị thời gian thực trên trình duyệt', HeadingLevel.HEADING_2));
body.push(p('Trình duyệt giữ một kết nối WebSocket tới broker và vẽ thêm điểm ngay khi có bản tin, không hỏi vòng máy chủ. Bộ đệm giữ theo thời gian thay vì theo số điểm, nên đổi cửa sổ hiển thị không làm sai trục hoành:'));
body.push(...codeBlock(srcBetween('index.html', 'function rtRedraw()', '$(\'rt-pause\').onclick')));

// --- 8 ---
body.push(h('8. ĐIỀU KHIỂN VÀ TRÍ TUỆ HỆ THỐNG', HeadingLevel.HEADING_1));
body.push(h('8.1. Thuật toán sa thải tải theo ưu tiên', HeadingLevel.HEADING_2));
body.push(...code([
  'Mỗi 2 giây, với P là công suất trung bình 2 giây:',
  '',
  'NẾU quản-lý-bật VÀ LED đang bật VÀ (P > P_peak liên tục ≥ 4 s)',
  '    -> CẮT LED, trạng thái SHED_PEAK, sinh sự kiện SHED',
  '',
  'NGƯỢC LẠI NẾU quản-lý-bật VÀ LED đang tắt VÀ trạng thái = SHED_PEAK',
  '    VÀ (P < P_peak − H liên tục ≥ 15 s)',
  '    VÀ (LED đã tắt ≥ 20 s)',
  '    VÀ (P + P_LED_ước_lượng < P_peak)',
  '    -> BẬT LẠI LED, sinh sự kiện RESTORE',
  '',
  'NẾU LED đã tắt mà P vẫn > P_peak liên tục ≥ 10 s',
  '    -> ALARM_OVER_LIMIT + buzzer (quạt ưu tiên cao KHÔNG bị cắt)',
]));
body.push(p('Ba điều kiện khôi phục hoạt động bổ sung cho nhau. Dải trễ ngăn dao động do nhiễu đo quanh ngưỡng. Thời gian duy trì tối thiểu ngăn dao động do tải thay đổi nhanh. Điều kiện dự báo là phần quan trọng nhất: công suất của đèn LED được ước lượng ngay từ bước nhảy công suất đo được mỗi lần đèn đổi trạng thái, theo bộ lọc trung bình trượt có trọng số 0.7 và 0.3. Nếu tổng công suất hiện tại cộng với công suất ước lượng của đèn vượt ngưỡng, hệ thống không khôi phục, vì biết chắc sẽ phải cắt lại ngay sau đó.'));
body.push(p('Quạt là tải ưu tiên cao và không bao giờ bị cắt tự động. Khi công suất vẫn vượt ngưỡng sau khi đã sa thải đèn, hệ thống chuyển sang cảnh báo để người vận hành quyết định, thay vì tự ý cắt thiết bị quan trọng.'));

body.push(h('8.2. Thành phần nâng cao: phát hiện đỉnh và ngân sách điện năng ngày', HeadingLevel.HEADING_2));
body.push(p('Thiết bị liên tục ghi nhận đỉnh công suất trong ngày và công bố trong telemetry. Khi công suất vượt ngưỡng kéo dài mà tải ưu tiên thấp đã bị cắt, hệ thống phát cảnh báo đỉnh, tức là phát hiện tình huống mà biện pháp sa thải hiện có không đủ.'));
body.push(p('Ngân sách điện năng ngày cho phép đặt hạn mức Wh cho mỗi ngày. Khi đạt 80 phần trăm hạn mức, hệ thống cảnh báo sớm. Khi vượt hạn mức, tải ưu tiên thấp bị cắt và chỉ được mở lại khi sang ngày mới. Chính sách này có thể giải thích được hoàn toàn bằng luật, thuận tiện cho việc bảo vệ và kiểm chứng, khác với cách tiếp cận hộp đen.'));

body.push(h('8.3. Phân biệt trạng thái yêu cầu và trạng thái xác nhận', HeadingLevel.HEADING_2));
body.push(p('Mỗi lệnh mang một cmd_id sinh ngẫu nhiên. Thiết bị áp dụng lệnh rồi publish bản tin ack chứa cmd_id cùng trạng thái thực tế của hai relay sau khi áp dụng. Giao diện hiển thị hai dòng riêng biệt, đo độ trễ bằng đồng hồ trình duyệt và báo lỗi nếu quá 5 giây chưa có xác nhận. Cơ chế này bộc lộ đúng bản chất của hệ phân tán: lệnh được gửi đi không đồng nghĩa với việc thiết bị đã thực hiện.'));
body.push(p('Một trường hợp đáng chú ý là khi người dùng bật tải bằng tay trong lúc chế độ tự động đang hoạt động. Thiết bị chuyển sang chế độ thủ công và sinh sự kiện MANUAL_OVERRIDE, thay vì để hai cơ chế tranh chấp quyền điều khiển cùng một relay.'));

body.push(h('8.4. Mã nguồn khâu đo lường', HeadingLevel.HEADING_2));
body.push(p('Hàm dưới đây chạy 4 lần mỗi giây trên ESP32. Ba điểm kỹ thuật đáng chú ý: lấy trung bình 64 mẫu để khử nhiễu, lấy trị tuyệt đối của độ lệch để phép đo không phụ thuộc chiều đấu dây của cảm biến, và tự hiệu chỉnh điểm không khi cả hai tải đều tắt.'));
body.push(...codeBlock(srcBetween('firmware/esp32_firmware/esp32_firmware.ino',
  'void measureBlock()', 'sum_block_p += power_w; n_block++;')));
body.push(p('Việc lấy trị tuyệt đối xuất phát từ một lỗi thực tế: bản đầu tiên viết "if (i < deadband) i = 0", tức là mọi giá trị âm đều bị ép về không. Khi cọc IP+ và IP− của cảm biến bị đấu ngược, điện áp ra thấp hơn mức 2.5 V nên dòng điện tính ra mang dấu âm và bị loại bỏ hoàn toàn; hệ thống báo 0 A dù tải đang chạy. Chi tiết được ghi ở chương 12.'));
body.push(p('Cơ chế tự hiệu chỉnh điểm không giải quyết hiện tượng trôi mức tham chiếu khi đổi nguồn cấp. Thực nghiệm ghi nhận độ trôi khoảng 30 mV giữa lúc cấp nguồn bằng cổng USB và lúc cấp bằng mạch LM2596, tương đương sai số 0.17 A nếu không bù.'));

body.push(h('8.5. Mã nguồn máy trạng thái quản lý tải', HeadingLevel.HEADING_2));
body.push(...codeBlock(srcBetween('firmware/esp32_firmware/esp32_firmware.ino',
  'void controlStep()', 'buzzer(alarm_over);')));

body.push(h('8.6. Mã nguồn cơ chế xác nhận lệnh', HeadingLevel.HEADING_2));
body.push(p('Thiết bị nhận lệnh, áp dụng, rồi phát lại bản tin xác nhận mang cùng mã lệnh và trạng thái thực tế của hai rơ-le sau khi áp dụng:'));
body.push(...codeBlock(srcBetween('firmware/esp32_firmware/esp32_firmware.ino',
  'void onMqtt(char* topic', 'Serial.printf("[CMD]')));

// --- 9 ---
body.push(h('9. BẢO MẬT VÀ ĐỘ TIN CẬY', HeadingLevel.HEADING_1));
body.push(h('9.1. Độ tin cậy khi mất kết nối', HeadingLevel.HEADING_2));
body.push(...bullets([
  'Thủ tục kết nối lại WiFi và MQTT không chặn vòng lặp chính; việc đo và điều khiển vẫn chạy đúng chu kỳ 2 giây trong lúc thử kết nối lại.',
  'Mất broker quá 30 giây, thiết bị chuyển sang chế độ an toàn: tự kích hoạt quản lý tải cục bộ ngay cả khi đang ở chế độ thủ công.',
  'DS3231 giữ giờ khi mất WiFi, nên bản ghi trong thời gian mất mạng vẫn có mốc thời gian đúng; khi có mạng, giờ NTP được ghi ngược lại vào RTC mỗi 10 phút.',
  'Bộ đệm vòng 600 bản ghi, tương đương khoảng 20 phút, lưu số liệu trong lúc mất kết nối và gửi bù 5 gói mỗi 200 ms khi kết nối trở lại. Gói gửi bù mang cờ buffered và backend dùng mốc thời gian của thiết bị nên đồ thị lịch sử không bị dồn cục.',
  'Kết nối lại sinh sự kiện RECOVERED kèm thời lượng mất kết nối và số gói gửi bù, phục vụ kiểm chứng trong thực nghiệm.',
  'Cấu hình quan trọng được lưu vào bộ nhớ Flash nên thiết bị giữ nguyên ngưỡng và chế độ sau khi mất điện.',
]));
body.push(h('9.2. Bảo mật', HeadingLevel.HEADING_2));
body.push(table([
  ['Mối đe dọa', 'Ảnh hưởng', 'Biện pháp hiện tại', 'Hướng hoàn thiện'],
  ['Người lạ publish lệnh lên topic cmd', 'Đóng cắt tải trái phép', 'Topic đặt tên khó đoán; mọi lệnh được ghi nhật ký kèm nguồn gốc', 'Broker có xác thực và ACL, tách quyền theo topic'],
  ['Nghe lén telemetry', 'Lộ thói quen sử dụng điện', 'Không có dữ liệu cá nhân trong bản tin', 'MQTT over TLS cổng 8883'],
  ['Gọi REST API tùy tiện', 'Thay đổi cấu hình từ xa', 'Bắt buộc header X-API-Key cho mọi POST và PUT', 'Xác thực theo tài khoản, phân quyền xem và điều khiển'],
  ['Lộ mật khẩu WiFi trong mã nguồn', 'Truy cập trái phép mạng nội bộ', 'Tách sang tệp secrets.h và loại khỏi Git', 'Nạp cấu hình qua chế độ AP lần đầu'],
  ['Trợ lý ngôn ngữ tự nhiên hiểu sai ý định', 'Đóng cắt ngoài mong muốn', 'Bắt buộc xác nhận thủ công trước khi gửi lệnh', 'Nhật ký kiểm toán theo người dùng'],
], [24, 22, 30, 24]));
body.push(cap('Bảng 9.1. Phân tích rủi ro và biện pháp'));
body.push(p('Hạn chế lớn nhất về bảo mật là broker công cộng không yêu cầu xác thực. Đây là lựa chọn có ý thức để hệ thống chạy được ngay trong điều kiện mạng của nhà trường, và mã nguồn đã sẵn sàng cho việc chuyển sang broker có tài khoản chỉ bằng thay đổi cấu hình.'));

// --- 10 ---
body.push(h('10. PHƯƠNG PHÁP THỰC NGHIỆM', HeadingLevel.HEADING_1));
body.push(table([
  ['Mã', 'Thí nghiệm', 'Cách tiến hành', 'Đại lượng thu thập'],
  ['E1', 'Sai số phép đo', 'Mắc nối tiếp đồng hồ đo dòng chuẩn; đo bốn trường hợp: không tải, quạt, đèn, cả hai; mỗi trường hợp 30 mẫu', 'Sai số tuyệt đối, sai số phần trăm, độ lệch chuẩn'],
  ['E2', 'Độ trễ thiết bị đến dashboard', 'So mốc thời gian trong gói với thời điểm hiển thị, 100 gói liên tiếp', 'Trung bình, phân vị 95, lớn nhất'],
  ['E3', 'Độ trễ lệnh đến xác nhận', 'Bấm bật/tắt 30 lần, đọc số liệu trên giao diện và bảng commands', 'Trung bình, phân vị 95, số lệnh quá hạn'],
  ['E4', 'So sánh có và không quản lý tải', 'Hai lần chạy 10 phút với cùng tải và cùng ngưỡng, một lần tắt chế độ tự động, một lần bật', 'Đỉnh công suất, điện năng, thời gian vượt ngưỡng, số lần đóng cắt'],
  ['E5', 'Chống đóng cắt liên tục', 'Đặt ngưỡng sát tổng công suất hai tải; so sánh cấu hình đầy đủ với cấu hình bỏ dải trễ và thời gian tối thiểu', 'Số lần đóng cắt trong 10 phút'],
  ['E6', 'Mất kết nối và khôi phục', 'Ngắt router 60 giây trong lúc đang vượt ngưỡng', 'Thời điểm phát hiện offline, hành vi cục bộ, số gói gửi bù, khoảng trống dữ liệu'],
  ['E7', 'Ngân sách điện năng ngày', 'Đặt hạn mức nhỏ, quan sát cảnh báo và hành vi cắt tải', 'Thời điểm cảnh báo 80 phần trăm và vượt hạn mức'],
  ['E8', 'Độ trôi của đồng hồ thời gian thực', 'So giờ DS3231 với NTP sau 24 giờ', 'Sai lệch giây mỗi ngày'],
], [8, 22, 42, 28]));
body.push(cap('Bảng 10.1. Ma trận thí nghiệm'));
body.push(p('Công cụ thu thập: giao diện hiển thị trực tiếp độ trễ và tỉ lệ nhận gói; endpoint /api/stats tổng hợp theo khoảng thời gian; chức năng xuất CSV cho phép xử lý lại bằng bảng tính. Mọi số liệu trong chương kết quả đều lấy từ ba nguồn này, không nhập tay.'));

// --- 11 ---
body.push(h('11. KẾT QUẢ VÀ BÀN LUẬN', HeadingLevel.HEADING_1));
body.push(p('Các bảng dưới đây được điền sau khi chạy thực nghiệm trên mạch thật.', { italics: true }));
body.push(h('11.1. Sai số phép đo (E1)', HeadingLevel.HEADING_2));
body.push(table([
  ['Trường hợp', 'Đồng hồ chuẩn (A)', 'Hệ thống đo (A)', 'Sai số (A)', 'Sai số (%)', 'Độ lệch chuẩn (A)'],
  ['Không tải', '', '', '', '', ''],
  ['Chỉ quạt', '', '', '', '', ''],
  ['Chỉ đèn LED', '', '', '', '', ''],
  ['Cả hai tải', '', '', '', '', ''],
], [22, 18, 16, 14, 14, 16]));
body.push(cap('Bảng 11.1. Kết quả đo sai số'));

body.push(h('11.2. Độ trễ (E2, E3)', HeadingLevel.HEADING_2));
body.push(table([
  ['Chỉ tiêu', 'Số mẫu', 'Trung bình (ms)', 'Phân vị 95 (ms)', 'Lớn nhất (ms)'],
  ['Thiết bị → backend', '', '', '', ''],
  ['Thiết bị → dashboard', '', '', '', ''],
  ['Lệnh → xác nhận', '', '', '', ''],
], [30, 16, 18, 18, 18]));
body.push(cap('Bảng 11.2. Kết quả đo độ trễ'));

body.push(h('11.3. So sánh có và không quản lý tải (E4)', HeadingLevel.HEADING_2));
body.push(table([
  ['Chỉ tiêu trong 10 phút', 'Không quản lý', 'Có quản lý', 'Chênh lệch'],
  ['Đỉnh công suất (W)', '', '', ''],
  ['Điện năng tiêu thụ (Wh)', '', '', ''],
  ['Thời gian vượt ngưỡng (s)', '', '', ''],
  ['Số lần đóng cắt tải', '', '', ''],
  ['Tỉ lệ nhận gói (%)', '', '', ''],
], [34, 22, 22, 22]));
body.push(cap('Bảng 11.3. Hiệu quả của cơ chế quản lý tải'));

body.push(h('11.4. Chống đóng cắt liên tục (E5) và mất kết nối (E6)', HeadingLevel.HEADING_2));
body.push(table([
  ['Cấu hình', 'Số lần đóng cắt / 10 phút', 'Nhận xét'],
  ['Đủ ba điều kiện (H = 0.5 W, 15 s, 20 s, có dự báo)', '', ''],
  ['Chỉ một ngưỡng, không trễ, không thời gian tối thiểu', '', ''],
], [42, 24, 34]));
body.push(cap('Bảng 11.4. Hiệu quả cơ chế chống đóng cắt liên tục'));
body.push(table([
  ['Chỉ tiêu (E6)', 'Giá trị'],
  ['Thời điểm phát hiện offline sau khi ngắt mạng (s)', ''],
  ['Hành vi cắt tải cục bộ trong lúc mất mạng', ''],
  ['Số bản ghi được gửi bù sau khi khôi phục', ''],
  ['Khoảng trống dữ liệu còn lại trên đồ thị (s)', ''],
  ['Thời gian từ khi có mạng đến khi dữ liệu liên tục trở lại (s)', ''],
], [58, 42]));
body.push(cap('Bảng 11.5. Kết quả thí nghiệm mất kết nối'));
body.push(h('11.5. Bàn luận', HeadingLevel.HEADING_2));
body.push(p('Phần bàn luận cần trả lời bốn câu hỏi: sai số đo có đủ nhỏ so với ngưỡng điều khiển hay không; độ trễ đầu cuối có phù hợp với chu kỳ điều khiển 2 giây hay không; cơ chế quản lý tải giảm được bao nhiêu phần trăm thời gian vượt ngưỡng so với khi không quản lý; và hệ thống ứng xử ra sao khi mất mạng. Nếu sai số đo lớn hơn khoảng một phần mười ngưỡng, cần xem lại cầu phân áp, chất lượng nguồn 5 V và việc hiệu chuẩn điểm không.'));

// --- 12 ---
body.push(h('12. QUÁ TRÌNH PHÁT TRIỂN VÀ CÁC LỖI ĐÃ KHẮC PHỤC', HeadingLevel.HEADING_1));
body.push(p('Hệ thống trải qua nhiều vòng sửa lỗi. Phần này ghi lại các lỗi có giá trị kỹ thuật, vì chúng minh hoạ đúng những cái bẫy đặc trưng của một hệ IoT nhiều tầng: lỗi không nằm ở một chỗ mà ẩn ở ranh giới giữa các tầng.'));
body.push(table([
  ['Lỗi', 'Biểu hiện', 'Nguyên nhân', 'Cách khắc phục'],
  ['Đồ thị không vẽ', 'Các ô số liệu cập nhật nhưng đường đồ thị đứng yên ở 0',
   'Viết chart.data.datasets.data thay vì datasets[0].data; ngoại lệ bị khối try/catch nuốt mất',
   'Sửa chỉ số mảng, chuyển sang bộ đệm theo thời gian'],
  ['Dòng điện luôn bằng 0', 'Tải chạy thật nhưng công suất báo 0 W',
   'Câu lệnh kẹp giá trị âm về 0; khi cọc IP+/IP− đấu ngược thì toàn bộ số đo bị loại',
   'Lấy trị tuyệt đối của độ lệch điện áp'],
  ['Điểm không bị trôi', 'Cảm biến 2499 mV trong khi điểm không lưu là 2530 mV',
   'Mức tham chiếu đổi khi chuyển từ nguồn USB sang nguồn LM2596',
   'Tự hiệu chỉnh điểm không khi cả hai tải tắt, hằng số thời gian 12 giây'],
  ['Mất mạng thì ngừng bảo vệ', 'Khi rớt broker, thiết bị ngừng cắt tải',
   'Thủ tục kết nối lại dùng vòng lặp chặn kèm delay, khoá luôn vòng điều khiển',
   'Kết nối lại không chặn; tách vòng điều khiển khỏi tác vụ mạng'],
  ['Tính dòng sai về bản chất', 'Số đo cao hơn thực tế khi tải nhỏ',
   'Áp dụng công thức hiệu dụng cho tải một chiều nên nhiễu cộng theo bình phương',
   'Dùng trung bình mẫu, đúng với tải một chiều'],
  ['Web và thiết bị không gặp nhau', 'Cả hai đều báo kết nối broker thành công nhưng không có dữ liệu',
   'Cây topic cũ dùng dấu gạch dưới, bản mới dùng dấu gạch chéo',
   'Thống nhất một cây topic, in tên topic ra Serial để đối chiếu'],
  ['Trang web báo 404', 'Trang triển khai không mở được',
   'Tệp giao diện nằm trong thư mục con, nền tảng tìm tệp ở thư mục gốc',
   'Đưa tệp giao diện ra thư mục gốc kho mã'],
  ['Đóng cắt liên tục', 'Tải phụ bật tắt dồn dập quanh ngưỡng',
   'Một ngưỡng duy nhất, khôi phục xong lại vượt ngưỡng ngay',
   'Ba điều kiện đồng thời: dải trễ, thời gian tối thiểu, dự báo công suất sau khôi phục'],
], [16, 22, 32, 30]));
body.push(cap('Bảng 12.1. Các lỗi đã phát hiện và cách khắc phục'));
body.push(p('Bài học rút ra: ở hệ phân tán, một tầng báo "thành công" không có nghĩa là hệ thống chạy đúng. Thiết bị báo gửi thành công, trình duyệt báo kết nối thành công, nhưng nếu hai bên dùng hai tên topic khác nhau thì dữ liệu vẫn không bao giờ gặp nhau. Vì vậy nhóm bổ sung các điểm quan sát ở từng tầng: tên topic in ra cổng nối tiếp, ô độ tươi dữ liệu trên giao diện, endpoint trạng thái của backend, và truy vấn trực tiếp cơ sở dữ liệu.'));
body.push(pageBreak());

body.push(h('13. HẠN CHẾ', HeadingLevel.HEADING_1));
body.push(...bullets([
  'Broker MQTT công cộng không có xác thực; bất kỳ ai biết tên topic đều có thể đọc dữ liệu và gửi lệnh.',
  'Điện áp được giả định cố định 12 V thay vì đo trực tiếp, nên sai số của công suất phụ thuộc vào độ ổn định của nguồn.',
  'ACS712 5 A có độ phân giải hạn chế với các tải nhỏ dưới 0.3 A; cảm biến INA219 hoặc INA226 sẽ cho kết quả tốt hơn nhiều ở dải này.',
  'Chỉ dùng một cảm biến đo tổng dòng, nên công suất của từng tải chỉ là ước lượng từ bước nhảy khi đóng cắt.',
  'Thư viện PubSubClient chỉ publish được ở QoS 0; độ tin cậy của lệnh dựa vào cơ chế xác nhận ở tầng ứng dụng.',
  'Bộ đệm offline nằm trong RAM nên mất khi thiết bị khởi động lại; có thể nâng cấp sang bộ nhớ LittleFS.',
  'Gói miễn phí của dịch vụ triển khai tự ngừng khi không có lưu lượng, cần một tác vụ định kỳ đánh thức, và điều này vẫn có thể gây thủng dữ liệu ngắn.',
]));

// --- 13 ---
body.push(h('14. KẾT LUẬN', HeadingLevel.HEADING_1));
body.push(p('Đồ án đã xây dựng hoàn chỉnh một hệ thống IoT giám sát điện năng và quản lý tải thông minh, chạy thông suốt từ cảm biến đến giao diện web. Hệ thống đo dòng và công suất với quy trình hiệu chuẩn rõ ràng, truyền số liệu qua MQTT có cấu trúc topic và cơ chế phát hiện trạng thái sẵn sàng, lưu lịch sử vào cơ sở dữ liệu chuỗi thời gian kèm REST API, đồng thời cung cấp dashboard thời gian thực có phân biệt trạng thái yêu cầu và trạng thái đã xác nhận.'));
body.push(p('Đóng góp đáng kể nhất về mặt kỹ thuật nằm ở phần điều khiển và độ tin cậy. Cơ chế khôi phục tải dựa trên ba điều kiện đồng thời, trong đó có bước dự báo công suất sau khôi phục, giải quyết triệt để hiện tượng đóng cắt liên tục mà một ngưỡng đơn thuần không xử lý được. Thiết kế tách biệt vòng điều khiển cục bộ khỏi tác vụ mạng, kết hợp đồng hồ thời gian thực và bộ đệm gửi bù, giúp hệ thống giữ được cả chức năng an toàn lẫn tính toàn vẹn dữ liệu khi mất kết nối.'));
body.push(p('Hướng phát triển tiếp theo: chuyển sang broker có xác thực và mã hóa TLS; thay ACS712 bằng INA226 để đo cả điện áp và dòng với độ phân giải cao hơn; mở rộng thành nhiều node đo với khả năng điều phối tải giữa các node; bổ sung dự báo phụ tải ngắn hạn để sa thải chủ động trước khi vượt ngưỡng thay vì phản ứng sau.'));

// --- 14 ---
body.push(h('15. TÀI LIỆU THAM KHẢO', HeadingLevel.HEADING_1));
body.push(...[
  '[1] Allegro MicroSystems, "ACS712: Fully Integrated, Hall Effect-Based Linear Current Sensor IC", Datasheet, Rev. 18.',
  '[2] Espressif Systems, "ESP32-S3 Technical Reference Manual", 2024.',
  '[3] Espressif Systems, "ESP32-S3 Series Datasheet — ADC Characteristics and Calibration", 2024.',
  '[4] OASIS, "MQTT Version 5.0 — OASIS Standard", 2019.',
  '[5] Analog Devices/Maxim Integrated, "DS3231 Extremely Accurate I2C-Integrated RTC/TCXO/Crystal", Datasheet.',
  '[6] Solomon Systech, "SSD1306 Advance Information — 128×64 Dot Matrix OLED/PLED Segment/Common Driver".',
  '[7] S. Ramírez, "FastAPI Documentation", https://fastapi.tiangolo.com',
  '[8] Eclipse Foundation, "Eclipse Paho MQTT Python Client Documentation".',
  '[9] N. O\'Leary, "PubSubClient — Arduino Client for MQTT", https://pubsubclient.knolleary.net',
  '[10] B. Blanchon, "ArduinoJson Documentation", https://arduinojson.org',
  '[11] IEEE, "IEEE Std 1547 — Standard for Interconnection and Interoperability of Distributed Energy Resources", 2018 (tham khảo khái niệm sa thải tải).',
  '[12] K. Ogata, "Modern Control Engineering", 5th ed., Prentice Hall, 2010 (chương về điều khiển on-off và hysteresis).',
].map(t => new Paragraph({
  spacing: { after: 100, line: 276 }, alignment: AlignmentType.JUSTIFIED,
  indent: { left: convertInchesToTwip(0.35), hanging: convertInchesToTwip(0.35) },
  children: [new TextRun({ text: t, font: FONT, size: 26 })],
})));

// --- 15 ---
body.push(h('16. PHÂN CÔNG THÀNH VIÊN', HeadingLevel.HEADING_1));
body.push(table([
  ['STT', 'Họ và tên', 'MSSV', 'Nhiệm vụ', 'Tỉ lệ đóng góp'],
  ['1', 'Đặng Đình Mạnh', '24119055', 'Thiết kế mạch, firmware ESP32-S3, thuật toán quản lý tải', ''],
  ['2', '', '', 'Backend FastAPI, cơ sở dữ liệu, triển khai dịch vụ', ''],
  ['3', '', '', 'Dashboard web, trợ lý dữ liệu, giao diện người dùng', ''],
  ['4', '', '', 'Thực nghiệm, đo sai số và độ trễ, viết báo cáo', ''],
], [8, 26, 16, 36, 14]));
body.push(cap('Bảng 16.1. Phân công nhiệm vụ'));
body.push(p('Mã nguồn đầy đủ: https://github.com/JackGamerCYT/IOT-PROJECT3-'));

// ================================ PHỤ LỤC ================================
body.push(pageBreak());
body.push(h('PHỤ LỤC A. MÃ NGUỒN FIRMWARE ESP32-S3 (ĐẦY ĐỦ)', HeadingLevel.HEADING_1));
body.push(p('Tệp firmware/esp32_firmware/esp32_firmware.ino. Biên dịch bằng Arduino IDE, board ESP32S3 Dev Module, hai thư viện PubSubClient và ArduinoJson. Thông tin Wi-Fi đặt trong tệp riêng secrets.h nên không có mặt trong kho mã công khai.', { italics: true }));
body.push(...codeBlock(srcAll('firmware/esp32_firmware/esp32_firmware.ino'), 13));

body.push(pageBreak());
body.push(h('PHỤ LỤC B. MÃ NGUỒN BACKEND (ĐẦY ĐỦ)', HeadingLevel.HEADING_1));
body.push(p('Tệp backend/main.py. Chạy bằng FastAPI + Uvicorn, thư viện paho-mqtt và psycopg. Không đặt biến DATABASE_URL thì dùng SQLite, có đặt thì dùng PostgreSQL.', { italics: true }));
body.push(...codeBlock(srcAll('backend/main.py'), 13));

body.push(pageBreak());
body.push(h('PHỤ LỤC C. MÃ NGUỒN TRỢ LÝ DỮ LIỆU', HeadingLevel.HEADING_1));
body.push(p('Trích từ backend/main.py: hàm phân loại ý định và sinh câu trả lời từ truy vấn cơ sở dữ liệu.', { italics: true }));
body.push(...codeBlock(srcBetween('backend/main.py', 'def chat_answer(question: str) -> dict:',
  'class ChatIn(BaseModel):', 400), 13));

body.push(pageBreak());
body.push(h('PHỤ LỤC D. MÃ NGUỒN GIAO DIỆN (TRÍCH)', HeadingLevel.HEADING_1));
body.push(p('Trích từ index.html: xử lý bản tin MQTT, gửi lệnh và đối chiếu xác nhận.', { italics: true }));
body.push(...codeBlock(srcBetween('index.html', 'function onTelemetry(d) {', 'let configTouched', 60), 13));
body.push(...codeBlock(srcBetween('index.html', 'function publishCmd(body, onDone)', 'window.sendLoad', 60), 13));

body.push(pageBreak());
body.push(h('PHỤ LỤC E. PHIẾU GHI SỐ LIỆU THỰC NGHIỆM', HeadingLevel.HEADING_1));
body.push(p('In phiếu này ra để ghi tay tại chỗ, sau đó nhập lại vào chương 11.', { italics: true }));
body.push(h('E1. Sai số phép đo dòng điện', HeadingLevel.HEADING_2));
body.push(table([
  ['Lần đo', 'Không tải (A)', 'Quạt (A)', 'Đèn (A)', 'Cả hai (A)', 'Đồng hồ chuẩn (A)'],
  ...Array.from({ length: 10 }, (_, i) => [String(i + 1), '', '', '', '', '']),
  ['Trung bình', '', '', '', '', ''],
  ['Độ lệch chuẩn', '', '', '', '', ''],
], [14, 18, 16, 16, 18, 18]));
body.push(h('E2, E3. Độ trễ', HeadingLevel.HEADING_2));
body.push(table([
  ['Lần', 'Thiết bị → dashboard (ms)', 'Lệnh → xác nhận (ms)', 'Ghi chú'],
  ...Array.from({ length: 10 }, (_, i) => [String(i + 1), '', '', '']),
  ['Trung bình', '', '', ''],
  ['Phân vị 95', '', '', ''],
], [10, 30, 30, 30]));
body.push(h('E4. So sánh có và không quản lý tải', HeadingLevel.HEADING_2));
body.push(table([
  ['Chỉ tiêu 10 phút', 'Không quản lý', 'Có quản lý', 'Chênh lệch (%)'],
  ['Đỉnh công suất (W)', '', '', ''],
  ['Điện năng (Wh)', '', '', ''],
  ['Thời gian vượt ngưỡng (s)', '', '', ''],
  ['Số lần đóng cắt', '', '', ''],
  ['Tỉ lệ nhận gói (%)', '', '', ''],
], [34, 22, 22, 22]));
body.push(h('E6. Mất kết nối và khôi phục', HeadingLevel.HEADING_2));
body.push(table([
  ['Nội dung quan sát', 'Kết quả'],
  ['Thời điểm ngắt mạng', ''],
  ['Thời điểm badge chuyển OFFLINE', ''],
  ['Hành vi cắt tải trong lúc mất mạng', ''],
  ['Thời điểm cắm lại mạng', ''],
  ['Số gói được gửi bù', ''],
  ['Khoảng trống còn lại trên đồ thị (s)', ''],
], [58, 42]));

// ===================================================================================
const doc = new Document({
  creator: 'Nhóm đề tài 03',
  title: 'Báo cáo IoT Project 03 - Smart Energy Monitoring and Intelligent Load Management',
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
        run: { font: FONT, size: 30, bold: true, color: '1a3b5c' }, paragraph: { spacing: { before: 280, after: 140 } } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { font: FONT, size: 27, bold: true, color: '1a3b5c' }, paragraph: { spacing: { before: 200, after: 100 } } },
    ],
  },
  sections: [{
    properties: { page: { margin: { top: 1440, right: 1080, bottom: 1440, left: 1440 } } },
    headers: {
      default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
        children: [new TextRun({ text: 'IoT Project 03 — Smart Energy Monitoring & Intelligent Load Management', font: FONT, size: 18, italics: true, color: '666666' })] })] }),
    },
    footers: {
      default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
        children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 20 })] })] }),
    },
    children: body,
  }],
});

Packer.toBuffer(doc).then(b => {
  fs.writeFileSync(process.argv[2] || 'docs/BAO_CAO_IOT_PROJECT03.docx', b);
  console.log('OK');
});
