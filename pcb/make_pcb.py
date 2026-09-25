#!/usr/bin/env python3
"""
Sinh mạch in 1 lớp (chỉ BOTTOM) cho Project 03 - Smart Energy.
Toàn bộ linh kiện là loại cắm (through-hole), module relay để NGOÀI, chỉ cắm hàng rào.

Xuất ra:
  smart_energy.kicad_pcb            mở bằng KiCad 7/8/9
  BOTTOM_mirrored_iron.pdf          bản in 1:1 ĐÃ LẬT GƯƠNG để ủi đồng
  BOTTOM_normal_check.pdf           bản không lật, để đối chiếu khi dò mạch
  TOP_placement.pdf                 sơ đồ cắm linh kiện (nhìn từ mặt linh kiện)
  preview.png                       ảnh xem nhanh
  DRC_REPORT.txt                    kết quả tự kiểm tra khoảng cách

Chạy: python3 make_pcb.py
"""
import math
import os

W, H = 100.0, 80.0          # kích thước board (mm)
CLR = 0.4                    # khoảng cách đồng tối thiểu (mm)
POUR_CLR = 0.5               # khoảng cách của vùng phủ đồng GND
EDGE_KEEPOUT = 1.0

# ---------------------------------------------------------------- linh kiện
# pad: (tên, x, y, net, drill, dia, shape)  shape: 'circle' | 'rect'
PADS = []
COMPS = []                   # (ref, value, mô tả, [chỉ số pad])
SILK = []                    # (text, x, y, size, rot, layer)


def comp(ref, value, desc, pads):
    idx = []
    for name, x, y, net, drill, dia, shape in pads:
        idx.append(len(PADS))
        PADS.append(dict(ref=ref, name=name, x=x, y=y, net=net, drill=drill, dia=dia, shape=shape))
    COMPS.append(dict(ref=ref, value=value, desc=desc, pads=idx))


def header(ref, value, desc, x, y0, nets, pitch=2.54, drill=1.0, dia=2.0):
    pads = []
    for i, n in enumerate(nets):
        pads.append((str(i + 1), x, y0 + i * pitch, n, drill, dia, 'rect' if i == 0 else 'circle'))
    comp(ref, value, desc, pads)


NC = ''   # không nối

# ---- ESP32-S3-DevKitC-1 (2 hàng 1x22, cách nhau 22.86 mm = 0.9 inch) --------
# Thứ tự chân theo tài liệu Espressif (J1 trái, J3 phải), pin 1 ở phía cổng USB.
J1_NETS = ['+3V3', NC, NC, NC, NC, NC, NC, NC, NC, NC, NC, 'SDA', NC, NC, 'SCL',
           NC, NC, 'IN1', 'IN2', 'BUZZ', '+5V', 'GND']
J1_LBL = ['3V3', '3V3', 'RST', 'IO4', 'IO5', 'IO6', 'IO7', 'IO15', 'IO16', 'IO17', 'IO18',
          'IO8', 'IO3', 'IO46', 'IO9', 'IO10', 'IO11', 'IO12', 'IO13', 'IO14', '5V', 'GND']
J3_NETS = ['GND', NC, NC, 'ADC', NC, NC, NC, NC, NC, NC, NC, NC, NC, NC, NC, NC, NC,
           NC, NC, NC, 'GND', 'GND']
J3_LBL = ['GND', 'TX', 'RX', 'IO1', 'IO2', 'IO42', 'IO41', 'IO40', 'IO39', 'IO38', 'IO37',
          'IO36', 'IO35', 'IO0', 'IO45', 'IO48', 'IO47', 'IO21', 'IO20', 'IO19', 'GND', 'GND']

header('J1', '1x22', 'ESP32-S3 DevKitC hàng TRÁI', 40.0, 10.0, J1_NETS)
header('J3', '1x22', 'ESP32-S3 DevKitC hàng PHẢI', 62.86, 10.0, J3_NETS)

# ---- module I2C ------------------------------------------------------------
header('J4', '1x4', 'DS3231 (RTC)', 14.0, 15.08, ['+3V3', 'SDA', 'SCL', 'GND'])
header('J5', '1x4', 'OLED SSD1306', 24.0, 15.08, ['+3V3', 'SDA', 'SCL', 'GND'])

# ---- module relay 2 kênh (ĐỂ NGOÀI, chỉ cắm rào) ---------------------------
header('J6', '1x5', 'Relay 2 kênh (module ngoài)', 20.0, 40.0,
       ['IN1', 'IN2', '+3V3', '+5V', 'GND'])

# ---- module ACS712 + cầu phân áp ------------------------------------------
header('J7', '1x3', 'ACS712-05B', 88.0, 14.0, ['+5V', 'ACS_OUT', 'GND'])
comp('R1', '10k', 'Phân áp trên', [('1', 76.0, 16.54, 'ADC', 0.9, 1.9, 'rect'),
                                   ('2', 86.16, 16.54, 'ACS_OUT', 0.9, 1.9, 'circle')])
comp('R2', '20k', 'Phân áp dưới', [('1', 76.0, 20.0, 'ADC', 0.9, 1.9, 'rect'),
                                   ('2', 76.0, 30.16, 'GND', 0.9, 1.9, 'circle')])
comp('C2', '100nF', 'Lọc nhiễu ADC', [('1', 70.0, 20.0, 'ADC', 0.9, 1.9, 'rect'),
                                      ('2', 70.0, 25.08, 'GND', 0.9, 1.9, 'circle')])

# ---- khối nguồn (cột trái) -------------------------------------------------
comp('J8', 'DOMINO', 'Ngõ ra 12V đã qua cầu chì',
     [('1', 5.0, 8.0, '+12F', 1.3, 2.6, 'rect'), ('2', 5.0, 10.54, 'GND', 1.3, 2.6, 'circle')])
comp('J9', 'DOMINO', 'Nguồn 12V vào',
     [('1', 5.0, 15.0, 'GND', 1.3, 2.6, 'rect'), ('2', 5.0, 20.08, '+12V', 1.3, 2.6, 'circle')])
comp('F1', '2A', 'Cầu chì (đế 5x20 hoặc dây)',
     [('1', 5.0, 25.0, '+12V', 1.3, 2.6, 'rect'), ('2', 5.0, 30.08, '+12F', 1.3, 2.6, 'circle')])
comp('J10', '1x2', 'LM2596 ngõ VÀO (IN+/IN-)',
     [('1', 5.0, 35.0, '+12F', 1.0, 2.0, 'rect'), ('2', 5.0, 37.54, 'GND', 1.0, 2.0, 'circle')])
comp('J11', '1x2', 'LM2596 ngõ RA (OUT+/OUT-)',
     [('1', 5.0, 42.0, '+5V', 1.0, 2.0, 'rect'), ('2', 5.0, 44.54, 'GND', 1.0, 2.0, 'circle')])
comp('C1', '100uF', 'Lọc nguồn 5V', [('1', 12.0, 54.0, '+5V', 1.0, 2.0, 'rect'),
                                     ('2', 14.5, 54.0, 'GND', 1.0, 2.0, 'circle')])
comp('C3', '100nF', 'Lọc nguồn 3V3', [('1', 15.0, 29.0, '+3V3', 0.9, 1.9, 'rect'),
                                      ('2', 15.0, 34.08, 'GND', 0.9, 1.9, 'circle')])

# ---- dây nối GND trên mặt linh kiện (bắc qua đường 5V) --------------------
comp('JW1', 'DAY NOI', 'Dây nối GND bắc qua đường 5V',
     [('1', 23.5, 58.4, 'GND', 1.0, 2.0, 'rect'), ('2', 23.5, 63.2, 'GND', 1.0, 2.0, 'circle')])
comp('JW2', 'DAY NOI', 'Dây nối GND bắc qua 2 đường IN1/IN2',
     [('1', 31.0, 51.0, 'GND', 1.0, 2.0, 'rect'), ('2', 31.0, 58.0, 'GND', 1.0, 2.0, 'circle')])

# ---- còi báo động ----------------------------------------------------------
comp('BZ1', 'BUZZER 5V', 'Còi chíp 5V active', [('1', 12.0, 64.0, '+5V', 1.0, 2.2, 'rect'),
                                                ('2', 19.62, 64.0, 'BZC', 1.0, 2.2, 'circle')])
comp('Q1', 'S8050', 'NPN lái còi (E-B-C)', [('1', 30.0, 64.0, 'GND', 0.9, 1.9, 'rect'),
                                            ('2', 30.0, 66.54, 'QB', 0.9, 1.9, 'circle'),
                                            ('3', 30.0, 69.08, 'BZC', 0.9, 1.9, 'circle')])
comp('R3', '1k', 'Điện trở cực nền', [('1', 34.0, 66.54, 'QB', 0.9, 1.9, 'rect'),
                                      ('2', 44.16, 66.54, 'BUZZ', 0.9, 1.9, 'circle')])

# ---------------------------------------------------------------- đường mạch
# (net, [điểm...], bề rộng)
W_SIG, W_PWR, W_12V = 0.6, 1.0, 1.0
TRACKS = [
    # 12 V vào -> cầu chì -> LM2596 + domino ra
    ('+12V', [(5, 20.08), (2.6, 20.08), (2.6, 25), (5, 25)], W_12V),
    ('GND', [(5, 15), (5, 10.54)], W_PWR),
    ('+12F', [(5, 30.08), (7.5, 30.08), (7.5, 35), (5, 35)], W_12V),
    ('+12F', [(7.5, 30.08), (7.5, 8), (5, 8)], W_12V),

    # 5 V: LM2596 OUT -> bus dọc trái -> các nơi
    ('+5V', [(5, 42), (8.5, 42), (8.5, 74)], W_PWR),
    ('+5V', [(8.5, 47.62), (20, 47.62)], W_PWR),
    ('+5V', [(8.5, 54), (12, 54)], W_PWR),
    ('+5V', [(8.5, 60.8), (40, 60.8)], W_PWR),
    ('+5V', [(8.5, 64), (12, 64)], W_PWR),
    ('+5V', [(8.5, 74), (92, 74), (92, 14), (88, 14)], W_PWR),

    # 3V3: J1.1 -> lane y=6 -> cột x=11 -> RTC/OLED/relay + tụ lọc
    ('+3V3', [(40, 10), (40, 6), (11, 6), (11, 45.08), (20, 45.08)], W_SIG),
    ('+3V3', [(11, 15.08), (14, 15.08), (24, 15.08)], W_SIG),
    ('+3V3', [(11, 29), (15, 29)], W_SIG),

    # I2C
    ('SDA', [(14, 17.62), (24, 17.62), (36, 17.62), (36, 37.94), (40, 37.94)], W_SIG),
    ('SCL', [(14, 20.16), (24, 20.16), (33, 20.16), (33, 45.56), (40, 45.56)], W_SIG),

    # điều khiển relay
    ('IN1', [(20, 40), (28, 40), (28, 53.18), (40, 53.18)], W_SIG),
    ('IN2', [(20, 42.54), (26, 42.54), (26, 55.72), (40, 55.72)], W_SIG),

    # còi
    ('BZC', [(19.62, 64), (19.62, 71), (30, 71), (30, 69.08)], W_SIG),
    ('QB', [(34, 66.54), (30, 66.54)], W_SIG),
    ('BUZZ', [(44.16, 66.54), (46, 66.54), (46, 58.26), (40, 58.26)], W_SIG),

    # xương GND cho các module bị vây bởi đường 3V3/5V, ra ngoài qua dây nối JW1
    ('GND', [(14, 22.7), (24, 22.7), (30.5, 22.7)], W_SIG),
    ('GND', [(30.5, 22.7), (30.5, 51), (31, 51)], 0.8),
    ('GND', [(31, 58), (23.5, 58), (23.5, 58.4)], 0.8),
    ('GND', [(15, 34.08), (30.5, 34.08)], W_SIG),
    ('GND', [(20, 50.16), (20, 57), (23.5, 57), (23.5, 58)], W_SIG),
    ('GND', [(14.5, 54), (14.5, 57), (20, 57)], W_SIG),

    # cảm biến dòng -> cầu phân áp -> GPIO1
    ('ACS_OUT', [(86.16, 16.54), (88, 16.54)], W_SIG),
    ('ADC', [(76, 16.54), (70, 16.54), (66, 16.54), (62.86, 17.62)], W_SIG),
    ('ADC', [(76, 16.54), (76, 20)], W_SIG),
    ('ADC', [(70, 16.54), (70, 20)], W_SIG),
]

# --------------------------------------------------------------- lỗ bắt ốc
MOUNT = [(3.5, 3.5), (96.5, 3.5), (3.5, 76.5), (96.5, 76.5)]
MOUNT_D = 3.2

# --------------------------------------------------------------- chữ in lụa
def add_silk():
    LEFT_COL = {'J8', 'J9', 'F1', 'J10', 'J11'}
    for c in COMPS:
        p0 = PADS[c['pads'][0]]
        if c['ref'] in LEFT_COL:
            SILK.append((c['ref'], p0['x'] - 2.6, p0['y'] + 1.3, 1.0, 0))
        else:
            SILK.append((c['ref'], p0['x'], p0['y'] - 3.1, 1.1, 0))
    # nhãn từng chân của các rào cắm
    def pin_labels(ref, labels, dx, rot=0):
        c = next(x for x in COMPS if x['ref'] == ref)
        for i, lb in enumerate(labels):
            if i >= len(c['pads']):
                break
            p = PADS[c['pads'][i]]
            SILK.append((lb, p['x'] + dx, p['y'], 0.9, rot))
    pin_labels('J1', J1_LBL, -4.6)
    pin_labels('J3', J3_LBL, 4.6)
    pin_labels('J4', ['3V3', 'SDA', 'SCL', 'GND'], 4.4)
    pin_labels('J5', ['3V3', 'SDA', 'SCL', 'GND'], 4.4)
    pin_labels('J6', ['IN1', 'IN2', '3V3', '5V', 'GND'], 4.6)
    pin_labels('J7', ['5V', 'OUT', 'GND'], 4.4)
    pin_labels('J8', ['12V+', 'GND'], 3.6)
    pin_labels('J9', ['GND', '12V+'], 3.6)
    pin_labels('F1', ['IN', 'OUT'], 3.4)
    pin_labels('J10', ['IN+', 'IN-'], 3.4)
    pin_labels('J11', ['OUT+', 'OUT-'], 3.8)
    pin_labels('Q1', ['E', 'B', 'C'], -2.6)
    SILK.append(('JW1, JW2: han day dong tren MAT LINH KIEN', 52, 63.5, 0.95, 0))
    pin_labels('BZ1', ['+', '-'], 0)
    SILK.append(('SMART ENERGY - IoT PROJECT 03', 50, 78.2, 1.6, 0))
    SILK.append(('1 lop (BOTTOM) - linh kien cam', 62, 3.0, 1.2, 0))
    SILK.append(('ESP32-S3 DevKitC-1', 51.4, 70.0, 1.3, 0))
    SILK.append(('RELAY 2CH (ngoai)', 26.5, 37.5, 1.0, 0))


add_silk()

# ---------------------------------------------------------------- DRC đơn giản
def seg_pts(tr):
    return [(tr[1][i], tr[1][i + 1]) for i in range(len(tr[1]) - 1)]


def seg_dist(p, q, r, s):
    """khoảng cách nhỏ nhất giữa 2 đoạn thẳng"""
    def d_pt_seg(px, py, ax, ay, bx, by):
        vx, vy = bx - ax, by - ay
        L = vx * vx + vy * vy
        t = 0 if L == 0 else max(0, min(1, ((px - ax) * vx + (py - ay) * vy) / L))
        return math.hypot(px - (ax + t * vx), py - (ay + t * vy))
    # cắt nhau?
    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0])
    d1, d2 = ccw(p, q, r), ccw(p, q, s)
    d3, d4 = ccw(r, s, p), ccw(r, s, q)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
        return 0.0
    return min(d_pt_seg(*r, *p, *q), d_pt_seg(*s, *p, *q),
               d_pt_seg(*p, *r, *s), d_pt_seg(*q, *r, *s))


def d_pt_seg(px, py, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]
    L = vx * vx + vy * vy
    t = 0 if L == 0 else max(0, min(1, ((px - a[0]) * vx + (py - a[1]) * vy) / L))
    return math.hypot(px - (a[0] + t * vx), py - (a[1] + t * vy))


def drc():
    errs = []
    segs = []
    for net, pts, w in TRACKS:
        for a, b in [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]:
            segs.append((net, a, b, w))
    # đường - đường
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            n1, a1, b1, w1 = segs[i]
            n2, a2, b2, w2 = segs[j]
            if n1 == n2:
                continue
            d = seg_dist(a1, b1, a2, b2) - w1 / 2 - w2 / 2
            if d < CLR:
                errs.append(f"TRACK-TRACK {n1} vs {n2}: {a1}->{b1} / {a2}->{b2} khe {d:.2f}mm")
    # đường - pad
    for n, a, b, w in segs:
        for p in PADS:
            if p['net'] == n:
                continue
            d = d_pt_seg(p['x'], p['y'], a, b) - w / 2 - p['dia'] / 2
            if d < CLR:
                errs.append(f"TRACK-PAD {n} {a}->{b} vs {p['ref']}.{p['name']}({p['net'] or 'NC'}) khe {d:.2f}mm")
    # pad - pad
    for i in range(len(PADS)):
        for j in range(i + 1, len(PADS)):
            p, q = PADS[i], PADS[j]
            if p['ref'] == q['ref'] or (p['net'] and p['net'] == q['net']):
                continue
            d = math.hypot(p['x'] - q['x'], p['y'] - q['y']) - p['dia'] / 2 - q['dia'] / 2
            if d < CLR:
                errs.append(f"PAD-PAD {p['ref']}.{p['name']} vs {q['ref']}.{q['name']} khe {d:.2f}mm")
    # lỗ bắt ốc
    for mx, my in MOUNT:
        for p in PADS:
            d = math.hypot(p['x'] - mx, p['y'] - my) - MOUNT_D / 2 - p['dia'] / 2
            if d < CLR:
                errs.append(f"HOLE ({mx},{my}) vs {p['ref']}.{p['name']} khe {d:.2f}mm")
    # trong biên
    for p in PADS:
        if not (EDGE_KEEPOUT + p['dia'] / 2 <= p['x'] <= W - EDGE_KEEPOUT - p['dia'] / 2 and
                EDGE_KEEPOUT + p['dia'] / 2 <= p['y'] <= H - EDGE_KEEPOUT - p['dia'] / 2):
            errs.append(f"OUT-OF-BOARD {p['ref']}.{p['name']} ({p['x']},{p['y']})")
    return errs


def connectivity():
    """Kiểm tra mỗi net có thật sự nối liền không (kể cả GND qua vùng phủ đồng + dây nối)."""
    from shapely.geometry import Point, LineString, box
    from shapely.ops import unary_union
    msgs = []
    pour_parts = gnd_pour_parts()
    for net in sorted({p['net'] for p in PADS if p['net']}):
        items = []
        for p in PADS:
            if p['net'] == net:
                items.append(('pad:' + p['ref'] + '.' + p['name'],
                              Point(p['x'], p['y']).buffer(p['dia'] / 2 + 0.02, 24)))
        for n, pts, w in TRACKS:
            if n == net:
                items.append(('trk', LineString(pts).buffer(w / 2 + 0.02, cap_style=2)))
        if net == 'GND':
            for i, g in enumerate(pour_parts):
                items.append((f'pour{i}', g))
        parent = list(range(len(items)))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]; a = parent[a]
            return a

        def uni(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                if items[i][1].intersects(items[j][1]):
                    uni(i, j)
        # dây nối tay (JW*) nối 2 pad của nó
        for c in COMPS:
            if c['ref'].startswith('JW'):
                ids = [k for k, (nm, _) in enumerate(items) if nm.startswith('pad:' + c['ref'])]
                for k in ids[1:]:
                    uni(ids[0], k)
        roots = {find(k) for k, (nm, _) in enumerate(items) if nm.startswith('pad:')}
        if len(roots) > 1:
            groups = {}
            for k, (nm, _) in enumerate(items):
                if nm.startswith('pad:'):
                    groups.setdefault(find(k), []).append(nm[4:])
            msgs.append(f'NET {net} bị chia {len(roots)} nhóm: ' +
                        ' | '.join(','.join(v) for v in groups.values()))
    return msgs


THERMAL_SPOKE = 0.9      # bề rộng nan nối nhiệt của pad GND (mm)
MIN_POUR_W = 0.6         # bề rộng đồng nhỏ nhất được giữ lại (mm)
MIN_POUR_AREA = 8.0      # mảnh đồng nhỏ hơn thế này thì bỏ (mm2)


def gnd_pour_parts():
    """Vùng phủ đồng GND: trừ khe cách điện, tạo thermal relief cho pad GND,
    bỏ mảnh đồng quá mảnh hoặc cô lập."""
    from shapely.geometry import Point, LineString, box
    from shapely.ops import unary_union
    obst = [Point(p['x'], p['y']).buffer(p['dia'] / 2 + POUR_CLR, 32) for p in PADS
            if p['net'] != 'GND']
    obst += [LineString(pts).buffer(w / 2 + POUR_CLR, cap_style=2, join_style=2)
             for net, pts, w in TRACKS if net != 'GND']
    obst += [Point(x, y).buffer(MOUNT_D / 2 + 0.6, 32) for x, y in MOUNT]

    # thermal relief: vòng cách điện quanh pad GND, chừa 4 nan nối
    for p in PADS:
        if p['net'] != 'GND':
            continue
        r_in, r_out = p['dia'] / 2, p['dia'] / 2 + POUR_CLR
        ring = Point(p['x'], p['y']).buffer(r_out, 48).difference(
            Point(p['x'], p['y']).buffer(r_in - 0.05, 48))
        h = THERMAL_SPOKE / 2
        spokes = unary_union([
            box(p['x'] - r_out - 0.3, p['y'] - h, p['x'] + r_out + 0.3, p['y'] + h),
            box(p['x'] - h, p['y'] - r_out - 0.3, p['x'] + h, p['y'] + r_out + 0.3)])
        obst.append(ring.difference(spokes))

    pour = box(EDGE_KEEPOUT, EDGE_KEEPOUT, W - EDGE_KEEPOUT, H - EDGE_KEEPOUT)
    pour = pour.difference(unary_union(obst))
    pour = pour.buffer(-MIN_POUR_W / 2).buffer(MIN_POUR_W / 2)   # bỏ đồng quá mảnh
    parts = [g for g in (pour.geoms if hasattr(pour, 'geoms') else [pour])
             if g.area >= MIN_POUR_AREA]
    gnd_cu = [Point(p['x'], p['y']).buffer(p['dia'] / 2 + 0.05, 24) for p in PADS
              if p['net'] == 'GND']
    gnd_cu += [LineString(pts).buffer(w / 2 + 0.05, cap_style=2) for net, pts, w in TRACKS
               if net == 'GND']
    return [g for g in parts if any(g.intersects(x) for x in gnd_cu)]


# ---------------------------------------------------------------- KiCad
LAYERS = """  (layers
    (0 "F.Cu" signal)
    (31 "B.Cu" signal)
    (36 "B.SilkS" user "B.Silkscreen")
    (37 "F.SilkS" user "F.Silkscreen")
    (38 "B.Mask" user)
    (39 "F.Mask" user)
    (44 "Edge.Cuts" user)
    (45 "Margin" user)
    (46 "B.CrtYd" user "B.Courtyard")
    (47 "F.CrtYd" user "F.Courtyard")
    (48 "B.Fab" user)
    (49 "F.Fab" user)
  )"""


def write_kicad(path):
    nets = sorted({p['net'] for p in PADS if p['net']} | {t[0] for t in TRACKS})
    nidx = {n: i + 1 for i, n in enumerate(nets)}
    o = ['(kicad_pcb (version 20221018) (generator make_pcb.py)', '  (general (thickness 1.6))',
         '  (paper "A4")', LAYERS,
         '  (setup (pad_to_mask_clearance 0.05) (pcbplotparams))',
         '  (net 0 "")']
    for n in nets:
        o.append(f'  (net {nidx[n]} "{n}")')
    for c in COMPS:
        p0 = PADS[c['pads'][0]]
        o.append(f'  (footprint "SE:{c["ref"]}" (layer "F.Cu") (at {p0["x"]} {p0["y"]})'
                 f' (attr through_hole)')
        o.append(f'    (fp_text reference "{c["ref"]}" (at 0 -3.2) (layer "F.SilkS")'
                 f' (effects (font (size 1 1) (thickness 0.15))))')
        o.append(f'    (fp_text value "{c["value"]}" (at 0 3.2) (layer "F.Fab") hide'
                 f' (effects (font (size 1 1) (thickness 0.15))))')
        for k in c['pads']:
            p = PADS[k]
            net = f' (net {nidx[p["net"]]} "{p["net"]}")' if p['net'] else ''
            o.append(f'    (pad "{p["name"]}" thru_hole {p["shape"]} (at {p["x"]-p0["x"]:.3f}'
                     f' {p["y"]-p0["y"]:.3f}) (size {p["dia"]} {p["dia"]}) (drill {p["drill"]})'
                     f' (layers "*.Cu" "*.Mask"){net})')
        o.append('  )')
    for net, pts, w in TRACKS:
        for a, b in [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]:
            o.append(f'  (segment (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (width {w})'
                     f' (layer "B.Cu") (net {nidx[net]}))')
    for mx, my in MOUNT:
        o.append(f'  (footprint "SE:MountingHole" (layer "F.Cu") (at {mx} {my}) (attr through_hole)'
                 f' (pad "" np_thru_hole circle (at 0 0) (size {MOUNT_D} {MOUNT_D})'
                 f' (drill {MOUNT_D}) (layers "*.Cu" "*.Mask")))')
    edge = [(0, 0), (W, 0), (W, H), (0, H), (0, 0)]
    for a, b in [(edge[i], edge[i + 1]) for i in range(4)]:
        o.append(f'  (gr_line (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (layer "Edge.Cuts")'
                 f' (width 0.15))')
    for t, x, y, s, rot in SILK:
        o.append(f'  (gr_text "{t}" (at {x} {y} {rot}) (layer "F.SilkS")'
                 f' (effects (font (size {s} {s}) (thickness {max(0.12, s*0.15):.2f}))))')
    # vùng phủ đồng GND mặt dưới
    poly = ' '.join(f'(xy {x} {y})' for x, y in [(1, 1), (W - 1, 1), (W - 1, H - 1), (1, H - 1)])
    o.append(f'  (zone (net {nidx["GND"]}) (net_name "GND") (layers "B.Cu") (hatch edge 0.5)'
             f' (connect_pads (clearance {POUR_CLR})) (min_thickness 0.3)'
             f' (fill yes (thermal_gap 0.5) (thermal_bridge_width 0.6))'
             f' (polygon (pts {poly})))')
    o.append(')')
    open(path, 'w').write('\n'.join(o))


# ---------------------------------------------------------------- bản vẽ in
def build_geometry():
    from shapely.geometry import Point, LineString, box
    from shapely.ops import unary_union
    prim = []
    for p in PADS:
        prim.append(box(p['x'] - p['dia'] / 2, p['y'] - p['dia'] / 2,
                        p['x'] + p['dia'] / 2, p['y'] + p['dia'] / 2) if p['shape'] == 'rect'
                    else Point(p['x'], p['y']).buffer(p['dia'] / 2, 64))
    for net, pts, w in TRACKS:
        prim.append(LineString(pts).buffer(w / 2, cap_style=2, join_style=2))
    return unary_union(gnd_pour_parts() + prim), prim


def draw(path, mirror, show_silk, title):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MPoly, Circle, Rectangle, PathPatch
    from matplotlib.path import Path

    fig = plt.figure(figsize=((W + 20) / 25.4, (H + 20) / 25.4))
    ax = fig.add_axes([10 / (W + 20), 10 / (H + 20), W / (W + 20), H / (H + 20)])
    ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.set_aspect('equal'); ax.axis('off')

    def fx(x):
        return W - x if mirror else x

    if not show_silk:
        copper, prim = build_geometry()
        gs = copper.geoms if hasattr(copper, 'geoms') else [copper]
        verts, codes = [], []
        for g in gs:                          # mỗi đa giác: viền ngoài + các lỗ
            for ring in [g.exterior] + list(g.interiors):
                pts = [(fx(x), y) for x, y in ring.coords]
                verts += pts
                codes += [Path.MOVETO] + [Path.LINETO] * (len(pts) - 2) + [Path.CLOSEPOLY]
        ax.add_patch(PathPatch(Path(verts, codes), facecolor='black', edgecolor='none',
                               zorder=1))
        for p in PADS:                        # tâm khoan
            ax.add_patch(Circle((fx(p['x']), p['y']), 0.25, facecolor='white',
                                edgecolor='none', zorder=4))
    else:
        for net, pts, w in TRACKS:
            ax.plot([fx(x) for x, _ in pts], [y for _, y in pts], color='#b0b0b0',
                    lw=w * 2.2, solid_capstyle='butt', zorder=1)
        for p in PADS:
            ax.add_patch(Circle((fx(p['x']), p['y']), p['dia'] / 2, facecolor='none',
                                edgecolor='#333333', lw=0.5, zorder=2))
            ax.add_patch(Circle((fx(p['x']), p['y']), p['drill'] / 2, facecolor='white',
                                edgecolor='#333333', lw=0.4, zorder=3))
        for t, x, y, s, rot in SILK:
            ax.text(fx(x), y, t, fontsize=s * 2.6, ha='center', va='center',
                    color='#004080', zorder=4)
        for c in COMPS:                      # khung linh kiện
            xs = [PADS[i]['x'] for i in c['pads']]; ys = [PADS[i]['y'] for i in c['pads']]
            x0, x1, y0, y1 = min(xs) - 1.4, max(xs) + 1.4, min(ys) - 1.4, max(ys) + 1.4
            ax.add_patch(Rectangle((min(fx(x0), fx(x1)), y0), x1 - x0, y1 - y0,
                                   facecolor='none', edgecolor='#88aacc', lw=0.5, zorder=1))
    for mx, my in MOUNT:
        ax.add_patch(Circle((fx(mx), my), MOUNT_D / 2, facecolor='white',
                            edgecolor='black' if show_silk else 'white', lw=0.5, zorder=5))
    ax.add_patch(MPoly([(0, 0), (W, 0), (W, H), (0, H)], closed=True, facecolor='none',
                       edgecolor='black', lw=0.6, zorder=6))
    fig.text(0.5, 0.985, title, ha='center', va='top', fontsize=8)
    fig.text(0.5, 0.012, f'Ti le 1:1 — in KHONG scale (fit=100%) — {W:.0f} x {H:.0f} mm',
             ha='center', fontsize=7)
    fig.savefig(path, dpi=600 if path.endswith('.png') else None)
    plt.close(fig)


ASSEMBLY = [
    # (thứ tự, ref, linh kiện, giá trị, hướng lắp / ghi chú)
    ('1', 'JW1, JW2', 'Dây nối (chân điện trở cắt)', '—',
     'Hàn TRƯỚC TIÊN, ở MẶT LINH KIỆN. JW1 dài 4.8mm, JW2 dài 7mm'),
    ('2', 'R1', 'Điện trở 1/4W', '10k (nâu-đen-cam)', 'Không phân cực, nằm ngang'),
    ('3', 'R2', 'Điện trở 1/4W', '20k (đỏ-đen-cam)', 'Không phân cực, nằm dọc'),
    ('4', 'R3', 'Điện trở 1/4W', '1k (nâu-đen-đỏ)', 'Không phân cực, nằm ngang'),
    ('5', 'C2', 'Tụ gốm', '100nF (104)', 'Không phân cực'),
    ('6', 'C3', 'Tụ gốm', '100nF (104)', 'Không phân cực'),
    ('7', 'Q1', 'Transistor NPN', 'S8050', 'Chân E–B–C từ TRÊN xuống, mặt phẳng quay ra PHẢI'),
    ('8', 'C1', 'Tụ hoá', '100uF/16V', 'CÓ CỰC: chân dài (+) vào pad vuông C1.1'),
    ('9', 'J4, J5', 'Rào cắm cái 1x4', '—', 'DS3231 và OLED; pad vuông là chân 1 (3V3)'),
    ('10', 'J6', 'Rào cắm cái 1x5', '—', 'Relay 2 kênh; pad vuông là chân 1 (IN1)'),
    ('11', 'J7', 'Rào cắm cái 1x3', '—', 'ACS712; pad vuông là chân 1 (5V)'),
    ('12', 'J10, J11', 'Rào cắm cái 1x2', '—', 'LM2596 vào/ra'),
    ('13', 'J1, J3', 'Rào cắm cái 1x22 (2 thanh)', '—',
     'ESP32-S3; cắm chip vào rào rồi mới hàn để 2 hàng thẳng nhau'),
    ('14', 'J8, J9', 'Domino 2 chân 5.08mm', '—', 'Miệng bắt vít quay RA MÉP BOARD'),
    ('15', 'F1', 'Đế cầu chì 5x20 hoặc dây', '2A', 'Lắp sau cùng, tháo được khi đo kiểm'),
    ('16', 'BZ1', 'Còi chip 5V active', '—', 'CÓ CỰC: chân (+) vào pad vuông BZ1.1'),
]

EXT_WIRING = [
    ('J9 (12V+ / GND)', 'Adapter 12V', 'Nguồn tổng vào mạch'),
    ('J10 IN+ / IN-', 'LM2596 IN+ / IN-', 'Cấp 12V cho mạch hạ áp'),
    ('J11 OUT+ / OUT-', 'LM2596 OUT+ / OUT-', 'Chỉnh ĐÚNG 5.00V trước khi cắm ESP32'),
    ('J8 12V+', 'ACS712 chân IP+', 'Dòng tải đi ra ngoài board'),
    ('ACS712 IP-', 'COM1 và COM2 của relay', 'Đo tổng dòng của cả 2 tải'),
    ('NO1 relay', 'Quạt 12V (+)', 'Tải 1 - ưu tiên cao'),
    ('NO2 relay', 'Đèn LED 12V (+)', 'Tải 2 - ưu tiên thấp, bị sa thải'),
    ('Quạt (-) , LED (-)', 'J8 GND', 'Mass chung 12V'),
    ('J7 (5V/OUT/GND)', 'ACS712 VCC/OUT/GND', 'Phần tín hiệu của cảm biến'),
    ('J6 IN1 / IN2', 'Relay IN1 / IN2', 'Tín hiệu điều khiển từ ESP32'),
    ('J6 5V', 'Chân JD-VCC của relay', 'THÁO jumper JD-VCC trên module'),
    ('J6 3V3', 'Chân VCC của relay', 'Nuôi opto bằng 3.3V để tắt dứt khoát'),
    ('J6 GND', 'Relay GND', ''),
    ('J4 / J5', 'DS3231 / OLED: 3V3-SDA-SCL-GND', 'Hai module dùng chung bus I2C'),
]

TEST_STEPS = [
    'Chưa cắm module: đo thông mạch 12V-GND, 5V-GND, 3V3-GND — KHÔNG được kêu',
    'Soi đèn kiểm tra đường mạch đứt hoặc dính thiếc, nhất là giữa các chân rào',
    'Cấp 12V vào J9, đo J11 OUT+ so với GND: chỉnh biến trở LM2596 về đúng 5.00V',
    'Ngắt điện, cắm ESP32 vào J1/J3 đúng chiều (chân 1 ở pad vuông)',
    'Cấp điện lại, đo chân 3V3 của J4: phải có 3.3V',
    'Đo thông mạch J4.SDA - J5.SDA - chân IO8 của J1 (phải kêu)',
    'Đo thông mạch J6.IN1 - IO12, J6.IN2 - IO13 (phải kêu)',
    'Đo thông mạch J7.OUT - R1 - IO1 của J3 (phải kêu)',
    'Đo GND của J4, J5, J6, J7 với GND của J9: tất cả phải thông (nhờ JW1, JW2)',
    'Nạp firmware, mở Serial 115200, giữ 2 tải TẮT trong 1 giây đầu để calib điểm 0',
]


def assembly_sheet(path):
    """Phiếu lắp ráp in được: sơ đồ + bảng thứ tự lắp + đấu dây ngoài + đo kiểm."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.patches import Circle, Rectangle

    with PdfPages(path) as pdf:
        # ---- trang 1: sơ đồ lắp ----
        fig = plt.figure(figsize=(11.69, 8.27))          # A4 ngang
        ax = fig.add_axes([0.04, 0.05, 0.62, 0.86])
        ax.set_xlim(-2, W + 2); ax.set_ylim(H + 2, -2); ax.set_aspect('equal'); ax.axis('off')
        ax.add_patch(Rectangle((0, 0), W, H, facecolor='#fbfbf7', edgecolor='black', lw=1))
        for net, pts, w in TRACKS:
            ax.plot([x for x, _ in pts], [y for _, y in pts], color='#d8d8d8', lw=w * 1.6,
                    solid_capstyle='butt', zorder=1)
        for c in COMPS:
            xs = [PADS[i]['x'] for i in c['pads']]; ys = [PADS[i]['y'] for i in c['pads']]
            x0, x1, y0, y1 = min(xs) - 1.5, max(xs) + 1.5, min(ys) - 1.5, max(ys) + 1.5
            hi = c['ref'].startswith('JW')
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor='#fff3cd' if hi else 'none',
                                   edgecolor='#d08a00' if hi else '#6f9fd8', lw=0.9, zorder=2))
            if c['ref'] in ('J8', 'J9', 'F1', 'J10', 'J11'):
                ax.text(x1 + 0.6, (y0 + y1) / 2, c['ref'], fontsize=6.5, ha='left', va='center',
                        color='#b00000', fontweight='bold', zorder=5)
            else:
                ax.text((x0 + x1) / 2, y0 - 1.0, c['ref'], fontsize=6.5, ha='center', va='bottom',
                        color='#b00000', fontweight='bold', zorder=5)
        for p in PADS:
            ax.add_patch(Circle((p['x'], p['y']), p['dia'] / 2, facecolor='#e8e8e8',
                                edgecolor='#444444', lw=0.5, zorder=3))
            if p['shape'] == 'rect':                      # đánh dấu chân 1
                ax.add_patch(Rectangle((p['x'] - p['dia'] / 2 - 0.35, p['y'] - p['dia'] / 2 - 0.35),
                                       p['dia'] + 0.7, p['dia'] + 0.7, facecolor='none',
                                       edgecolor='#b00000', lw=0.8, zorder=4))
            ax.add_patch(Circle((p['x'], p['y']), p['drill'] / 2, facecolor='white',
                                edgecolor='#444444', lw=0.4, zorder=4))
        for mx, my in MOUNT:
            ax.add_patch(Circle((mx, my), MOUNT_D / 2, facecolor='white', edgecolor='black',
                                lw=0.6, zorder=4))
        ax.text(W / 2, -1.2, 'NHIN TU MAT LINH KIEN (mat tren)', fontsize=8, ha='center')

        tx = fig.add_axes([0.68, 0.05, 0.30, 0.86]); tx.axis('off')
        lines = ['CHU THICH', '', 'O vuong do  = chan so 1 cua linh kien',
                 'Khung vang   = day noi JW1 / JW2 (han o MAT LINH KIEN)',
                 'Duong xam    = duong mach nam o MAT DUOI', '',
                 'DANH SACH RAO CAM', '']
        for c in COMPS:
            if c['ref'].startswith('J'):
                lines.append(f"  {c['ref']:<4} {c['desc']}")
        lines += ['', 'LINH KIEN ROI', '']
        for c in COMPS:
            if not c['ref'].startswith('J'):
                lines.append(f"  {c['ref']:<4} {c['value']:<12} {c['desc']}")
        tx.text(0, 1, '\n'.join(lines), fontsize=7.4, va='top', family='DejaVu Sans', linespacing=1.5)
        fig.suptitle('PHIEU LAP RAP - SMART ENERGY IoT PROJECT 03  |  Board 100 x 80 mm, 1 lop',
                     fontsize=11, y=0.97)
        pdf.savefig(fig); plt.close(fig)

        # ---- trang 2: thứ tự lắp ----
        fig = plt.figure(figsize=(8.27, 11.69)); ax = fig.add_axes([0, 0, 1, 1]); ax.axis('off')
        ax.text(0.5, 0.965, 'THU TU LAP LINH KIEN (danh dau vao o vuong)', fontsize=13,
                ha='center', fontweight='bold')
        y = 0.925
        ax.text(0.055, y, 'STT', fontsize=8.5, fontweight='bold')
        ax.text(0.115, y, 'Ref', fontsize=8.5, fontweight='bold')
        ax.text(0.215, y, 'Linh kien', fontsize=8.5, fontweight='bold')
        ax.text(0.40, y, 'Gia tri', fontsize=8.5, fontweight='bold')
        ax.text(0.545, y, 'Huong lap / ghi chu', fontsize=8.5, fontweight='bold')
        y -= 0.012
        ax.plot([0.04, 0.96], [y, y], color='black', lw=0.8)
        y -= 0.026
        for stt, ref, name, val, note in ASSEMBLY:
            ax.add_patch(plt.Rectangle((0.045, y - 0.006), 0.016, 0.014, fill=False, lw=0.8))
            ax.text(0.075, y, stt, fontsize=8)
            ax.text(0.115, y, ref, fontsize=8, fontweight='bold')
            ax.text(0.215, y, name, fontsize=8)
            ax.text(0.40, y, val, fontsize=8)
            for i, part in enumerate(_wrap(note, 52)):
                ax.text(0.545, y - i * 0.016, part, fontsize=7.6)
            y -= 0.018 + 0.016 * (len(_wrap(note, 52)) - 1) + 0.014
        y -= 0.01
        ax.plot([0.04, 0.96], [y, y], color='black', lw=0.8); y -= 0.03
        ax.text(0.05, y, 'LUU Y', fontsize=10, fontweight='bold'); y -= 0.022
        for t in ['Han JW1, JW2 TRUOC khi han cac linh kien cao xung quanh.',
                  'Linh kien thap han truoc, cao han sau: day noi > dien tro > tu > rao > domino.',
                  'Pad vuong tren mach = chan 1. C1 va BZ1 CO CUC, cam sai la hong.',
                  'Chinh LM2596 ra dung 5.00V TRUOC khi cam ESP32 vao J1/J3.']:
            ax.text(0.06, y, '- ' + t, fontsize=8.2); y -= 0.02
        pdf.savefig(fig); plt.close(fig)

        # ---- trang 3: đấu dây ngoài + đo kiểm ----
        fig = plt.figure(figsize=(8.27, 11.69)); ax = fig.add_axes([0, 0, 1, 1]); ax.axis('off')
        ax.text(0.5, 0.965, 'DAU DAY RA MODULE BEN NGOAI', fontsize=13, ha='center',
                fontweight='bold')
        y = 0.925
        ax.text(0.075, y, 'Tren board', fontsize=8.5, fontweight='bold')
        ax.text(0.37, y, 'Noi toi', fontsize=8.5, fontweight='bold')
        ax.text(0.63, y, 'Ghi chu', fontsize=8.5, fontweight='bold')
        y -= 0.012; ax.plot([0.04, 0.96], [y, y], color='black', lw=0.8); y -= 0.026
        for a, b, c in EXT_WIRING:
            ax.add_patch(plt.Rectangle((0.045, y - 0.006), 0.014, 0.012, fill=False, lw=0.7))
            ax.text(0.075, y, a, fontsize=8)
            ax.text(0.37, y, b, fontsize=8)
            for i, part in enumerate(_wrap(c, 40)):
                ax.text(0.63, y - i * 0.015, part, fontsize=7.6)
            y -= 0.028
        y -= 0.02
        ax.text(0.5, y, 'DO KIEM TRUOC KHI CAP DIEN LAN DAU', fontsize=12, ha='center',
                fontweight='bold'); y -= 0.035
        for i, t in enumerate(TEST_STEPS, 1):
            ax.add_patch(plt.Rectangle((0.045, y - 0.006), 0.014, 0.012, fill=False, lw=0.7))
            for k, part in enumerate(_wrap(f'{i}. {t}', 88)):
                ax.text(0.075, y - k * 0.016, part, fontsize=8.2)
            y -= 0.022 + 0.016 * (len(_wrap(f'{i}. {t}', 88)) - 1)
        y -= 0.03
        ax.text(0.05, max(y, 0.02), 'AN TOAN: toan mach chay 12VDC, khong dau vao dien luoi. '
                         'Deo gang + kinh khi an mon dong.', fontsize=8.2, color='#b00000')
        pdf.savefig(fig); plt.close(fig)


def _wrap(t, n):
    out, line = [], ''
    for w in t.split():
        if len(line) + len(w) + 1 > n:
            out.append(line); line = w
        else:
            line = (line + ' ' + w).strip()
    out.append(line)
    return out or ['']


def bom_md(path):
    rows = ['| Ref | Giá trị | Mô tả | Số chân | Mũi khoan (mm) |', '|---|---|---|---|---|']
    for c in COMPS:
        d = PADS[c['pads'][0]]['drill']
        rows.append(f"| {c['ref']} | {c['value']} | {c['desc']} | {len(c['pads'])} | {d} |")
    rows.append(f'| — | — | Lỗ bắt ốc (4 góc) | 4 | {MOUNT_D} |')
    open(path, 'w').write('# Danh sách linh kiện và mũi khoan\n\n' + '\n'.join(rows) + '\n')


if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    errs = drc()
    open(os.path.join(here, 'DRC_REPORT.txt'), 'w').write(
        ('KHONG CO LOI - khoang cach toi thieu %.1f mm\n' % CLR) if not errs
        else '\n'.join(errs) + f'\n\nTONG: {len(errs)} loi\n')
    cerr = connectivity()
    with open(os.path.join(here, 'DRC_REPORT.txt'), 'a') as f:
        f.write('\n--- THONG MACH ---\n' + ('Tat ca net lien mach.\n' if not cerr
                else '\n'.join(cerr) + '\n'))
    print(f'DRC: {len(errs)} lỗi | Thông mạch: {len(cerr)} lỗi')
    for e in cerr:
        print('  ', e)
    for e in errs[:25]:
        print('  ', e)
    write_kicad(os.path.join(here, 'smart_energy.kicad_pcb'))
    draw(os.path.join(here, 'BOTTOM_mirrored_iron.pdf'), True, False,
         'LOP DAY (BOTTOM) - DA LAT GUONG - DUNG DE IN UI DONG')
    draw(os.path.join(here, 'BOTTOM_normal_check.pdf'), False, False,
         'LOP DAY (BOTTOM) - KHONG LAT - de doi chieu khi do mach')
    draw(os.path.join(here, 'TOP_placement.pdf'), False, True,
         'SO DO CAM LINH KIEN (nhin tu mat linh kien)')
    draw(os.path.join(here, 'preview.png'), False, True, 'SO DO CAM LINH KIEN')
    bom_md(os.path.join(here, 'BOM_DRILL.md'))
    assembly_sheet(os.path.join(here, 'ASSEMBLY_SHEET.pdf'))
    print('Đã xuất: kicad_pcb, 4 PDF (gồm phiếu lắp ráp), preview.png, BOM_DRILL.md')
