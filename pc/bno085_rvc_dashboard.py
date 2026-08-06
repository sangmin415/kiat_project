"""PC-calculated BNO085 three-axis servo controller over a full-duplex FPGA UART."""
from __future__ import annotations
import argparse, math, time
from collections import deque
import pygame
try:
    import serial
except ImportError:
    serial = None

W, H = 1280, 760
BG, PANEL, TEXT, GRID = (7,22,42), (15,48,82), (234,243,250), (42,82,120)
GOLD, CYAN, ORANGE, RED, GREEN = (210,184,128), (94,218,234), (255,171,74), (239,89,101), (104,218,153)

# Start with a one-to-one mechanical mapping: a 1 degree sensor error commands
# about 1 degree of counter-rotation at each SG90 axis.  Change only the sign
# of an axis after mechanical assembly proves that its physical direction is reversed.
AXIS_BALANCE = {
    "roll":  (-1, 53),
    "pitch": (-1, 53),
    "yaw":   (-1, 53),
}

class RvcParser:
    def __init__(self):
        self.buf = bytearray()
        self.bad_checksum = 0
        self.zero_events = 0

    def feed(self, data):
        self.buf.extend(data)
        out = []
        while True:
            # The FPGA emits this B-key event between UART bytes. It may arrive
            # after a partial RVC frame, so locate it before consuming the frame.
            event_at = self.buf.find(b"\x55\x5a\x42\xf1")
            if event_at >= 0:
                del self.buf[:event_at + 4]
                self.zero_events += 1
                continue
            start = self.buf.find(b"\xaa\xaa")
            if start < 0:
                self.buf[:] = b"\xaa" if self.buf.endswith(b"\xaa") else b""
                return out
            if start:
                del self.buf[:start]
            if len(self.buf) < 19:
                return out
            frame = bytes(self.buf[:19])
            del self.buf[:19]
            if sum(frame[2:18]) & 255 != frame[18]:
                self.bad_checksum += 1
                continue
            value = lambda i: int.from_bytes(frame[i:i+2], "little", signed=True)
            out.append(dict(seq=frame[2], yaw=value(3)/100, pitch=value(5)/100,
                            roll=value(7)/100, ax=value(9), ay=value(11), az=value(13)))

def sim(t, seq):
    return dict(seq=seq & 255, roll=14*math.sin(t*.8), pitch=10*math.sin(t*.5+.7),
                yaw=35*math.sin(t*.2), ax=int(70*math.sin(t*5)), ay=int(60*math.sin(t*4)),
                az=1000+int(45*math.sin(t*6)))

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def servo_ticks(axis, angle, zero):
    # 12 MHz FPGA ticks: the 1.1-1.9 ms (9600-tick) servo range gives
    # about 53 ticks/degree for a 180 degree servo.  The minus sign commands
    # counter-rotation, i.e. active level compensation.
    direction, ticks_per_degree = AXIS_BALANCE[axis]
    return int(clamp(18000 + direction * round((angle-zero) * ticks_per_degree), 13200, 22800))

def send_servo_command(uart, ticks):
    payload = b"".join(int(v).to_bytes(2, "big") for v in ticks)
    uart.write(b"\x55\xa5" + payload + bytes([sum(payload) & 0xff]))

def card(screen, f1, f2, rect, name, val, color):
    pygame.draw.rect(screen, PANEL, rect, border_radius=12)
    pygame.draw.rect(screen, color, rect, 2, border_radius=12)
    screen.blit(f1.render(name, True, color), (rect.x+14, rect.y+12))
    screen.blit(f2.render(f"{val:+06.2f} deg", True, TEXT), (rect.x+14, rect.y+43))

def trace(screen, font, rect, values, color, title, scale):
    pygame.draw.rect(screen, PANEL, rect, border_radius=10)
    screen.blit(font.render(title, True, TEXT), (rect.x+12, rect.y+10))
    for k in range(1, 4):
        y = rect.y + rect.height*k//4
        pygame.draw.line(screen, GRID, (rect.x, y), (rect.right, y), 1)
    if len(values) > 1:
        pts = [(rect.x + i*(rect.width-1)//(len(values)-1),
                rect.centery-int(clamp(v/scale, -1, 1)*rect.height*.35))
               for i, v in enumerate(values)]
        pygame.draw.lines(screen, color, False, pts, 2)

def stage(screen, font, small, rect, s):
    # Digital twin of the supplied printed FPV gimbal:
    # bottom yaw servo -> blue U-frame -> inner roll servo -> upper rear pitch servo.
    pygame.draw.rect(screen, PANEL, rect, border_radius=12)
    pygame.draw.rect(screen, GOLD, rect, 2, border_radius=12)
    screen.blit(font.render("3-AXIS GIMBAL / WAFER STAGE", True, TEXT), (rect.x+16, rect.y+14))
    screen.blit(small.render("Printed FPV frame: R2 yaw base / R0 roll inner / R1 pitch rear", True, GOLD), (rect.x+16, rect.y+45))

    cx, cy = rect.centerx, rect.centery+8
    roll = int(clamp(s["roll"], -20, 20) * 1.1)
    pitch = int(clamp(s["pitch"], -20, 20) * 1.2)
    yaw = int(clamp(s["yaw"], -30, 30) * 0.7)
    blue = (42, 54, 112)
    blue_hi = (88, 108, 186)
    servo = (182, 132, 58)
    servo_hi = (227, 180, 96)
    black = (30, 34, 40)

    # R2 / YAW: lower vertical servo and rotating blue pedestal.
    yaw_servo = pygame.Rect(cx-43+yaw, cy+102, 86, 92)
    pygame.draw.rect(screen, servo, yaw_servo, border_radius=5)
    pygame.draw.rect(screen, GOLD, yaw_servo, 2, border_radius=5)
    pygame.draw.rect(screen, servo_hi, (yaw_servo.x-14, yaw_servo.y+14, 14, 18), border_radius=2)
    pygame.draw.rect(screen, servo_hi, (yaw_servo.right, yaw_servo.y+14, 14, 18), border_radius=2)
    turret = pygame.Rect(cx-105+yaw, cy+74, 210, 38)
    pygame.draw.rect(screen, blue, turret, border_radius=12)
    pygame.draw.rect(screen, blue_hi, turret, 3, border_radius=12)
    pygame.draw.ellipse(screen, GOLD, (cx-28+yaw, cy+86, 56, 16), 2)
    screen.blit(small.render("R2 / YAW", True, TEXT), (yaw_servo.x+12, yaw_servo.bottom+4))

    # Blue Gimbal_Main_Base and the tall right-side printed Tilt Mount.
    base = pygame.Rect(cx-128+yaw, cy+26, 256, 58)
    pygame.draw.rect(screen, blue, base, border_radius=12)
    pygame.draw.rect(screen, blue_hi, base, 3, border_radius=12)
    right_leg = pygame.Rect(cx+76+yaw, cy-84, 48, 150)
    left_leg = pygame.Rect(cx-124+yaw, cy-8, 38, 76)
    pygame.draw.rect(screen, blue, right_leg, border_radius=9)
    pygame.draw.rect(screen, blue_hi, right_leg, 3, border_radius=9)
    pygame.draw.rect(screen, blue, left_leg, border_radius=8)
    pygame.draw.rect(screen, blue_hi, left_leg, 3, border_radius=8)
    pygame.draw.circle(screen, (12, 20, 35), (right_leg.centerx, cy+21), 14)
    pygame.draw.circle(screen, blue_hi, (right_leg.centerx, cy+21), 14, 3)

    # R0 / ROLL: gold servo inside the lower U-frame.
    r0 = pygame.Rect(cx-53+yaw, cy+30-roll, 94, 42)
    pygame.draw.rect(screen, servo, r0, border_radius=5)
    pygame.draw.rect(screen, GOLD, r0, 2, border_radius=5)
    pygame.draw.circle(screen, servo_hi, (r0.left+17, r0.centery), 9)
    screen.blit(small.render("R0", True, TEXT), (r0.centerx-8, r0.y+13))

    # Camera/BNO085 carrier: dark front cylinder and blue roll ring.
    camera_y = cy-66+pitch-roll
    ring = pygame.Rect(cx-90+yaw, camera_y-18, 110, 82)
    pygame.draw.rect(screen, blue, ring, border_radius=18)
    pygame.draw.rect(screen, blue_hi, ring, 3, border_radius=18)
    body = pygame.Rect(cx-158+yaw, camera_y-8, 106, 60)
    pygame.draw.rect(screen, black, body, border_radius=15)
    pygame.draw.rect(screen, (80, 84, 95), body, 3, border_radius=15)
    pygame.draw.circle(screen, (8, 12, 18), (body.left+8, body.centery), 28)
    pygame.draw.circle(screen, GOLD, (body.left+8, body.centery), 28, 3)
    pygame.draw.circle(screen, (28, 55, 70), (body.left+8, body.centery), 17)

    # R1 / PITCH: gold rear servo mounted above/behind the camera carrier.
    r1 = pygame.Rect(cx+18+yaw, camera_y-42, 116, 44)
    pygame.draw.rect(screen, servo, r1, border_radius=5)
    pygame.draw.rect(screen, GOLD, r1, 2, border_radius=5)
    horn = pygame.Rect(r1.left-16, r1.centery-7, 18, 14)
    pygame.draw.rect(screen, servo_hi, horn, border_radius=3)
    screen.blit(small.render("R1 / PITCH", True, TEXT), (r1.x+20, r1.y+13))

    # Replace the original FPV camera function with our sensor platform label.
    plate = pygame.Rect(cx-40+yaw, camera_y+13, 68, 26)
    pygame.draw.rect(screen, (18, 93, 112), plate, border_radius=4)
    pygame.draw.rect(screen, CYAN, plate, 2, border_radius=4)
    tag = small.render("BNO085 STAGE", True, TEXT)
    screen.blit(tag, (cx-42+yaw, camera_y+68))

    # Real assembly axis legend.
    screen.blit(small.render(f"R0 Roll {s['roll']:+.1f}°", True, CYAN), (rect.x+18, rect.bottom-54))
    screen.blit(small.render(f"R1 Pitch {s['pitch']:+.1f}°", True, ORANGE), (rect.x+18, rect.bottom-34))
    screen.blit(small.render(f"R2 Yaw {s['yaw']:+.1f}°", True, GOLD), (rect.x+18, rect.bottom-14))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--simulate", action="store_true")
    a = ap.parse_args()
    if not a.simulate and not a.port:
        ap.error("use --simulate or --port COMxx (/dev/ttyUSB1 in WSL)")
    if not a.simulate and serial is None:
        raise RuntimeError("Install pyserial first.")

    uart = None if a.simulate else serial.Serial(a.port, a.baud, timeout=0)
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("PURDUE KIAT | BNO085 FPGA GIMBAL MONITOR")
    title = pygame.font.SysFont("consolas", 27, True)
    label = pygame.font.SysFont("consolas", 18, True)
    value = pygame.font.SysFont("consolas", 30, True)
    clock = pygame.time.Clock()
    rvc = RvcParser()
    sample = sim(0, 0)
    seq = 0
    next_sim = 0
    next_command = 0
    last_rx = 0
    zero = {"roll": 0.0, "pitch": 0.0, "yaw": 0.0}
    last_zero_source = "startup"
    last_zero_time = 0.0
    last_ticks = (18000, 18000, 18000)
    hist = {x: deque(maxlen=150) for x in ("roll", "pitch", "yaw", "vib")}
    running = True

    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                running = False
            if e.type == pygame.KEYDOWN and e.key == pygame.K_z:
                zero = {key: sample[key] for key in ("roll", "pitch", "yaw")}
                last_zero_source = "PC Z"
                last_zero_time = time.monotonic()

        now = time.monotonic()
        fresh = []
        if a.simulate and now >= next_sim:
            seq += 1
            fresh = [sim(now, seq)]
            next_sim = now + .01
        elif not a.simulate:
            fresh = rvc.feed(uart.read(uart.in_waiting or 1))

        if rvc.zero_events:
            zero = {key: sample[key] for key in ("roll", "pitch", "yaw")}
            last_zero_source = "FPGA keypad B"
            last_zero_time = now
            rvc.zero_events = 0

        if fresh:
            sample = fresh[-1]
            last_rx = now
            for p in fresh:
                hist["roll"].append(p["roll"])
                hist["pitch"].append(p["pitch"])
                hist["yaw"].append(p["yaw"])
                hist["vib"].append(math.sqrt(p["ax"]**2+p["ay"]**2+(p["az"]-1000)**2))

        # Feed the FPGA command watchdog at a deterministic 50 Hz, independent
        # of the sensor packet timing.
        if uart and now >= next_command:
            last_ticks = (servo_ticks("roll", sample["roll"], zero["roll"]),
                          servo_ticks("pitch", sample["pitch"], zero["pitch"]),
                          servo_ticks("yaw", sample["yaw"], zero["yaw"]))
            send_servo_command(uart, last_ticks)
            next_command = now + .02

        relative = {key: sample[key] - zero[key] for key in ("roll", "pitch", "yaw")}
        screen.fill(BG)
        screen.blit(title.render("PURDUE KIAT | BNO085 FPGA GIMBAL MONITOR", True, GOLD), (28, 18))
        live = a.simulate or now-last_rx < .5
        screen.blit(label.render("SIMULATION" if a.simulate else ("PC CONTROL: "+a.port), True,
                                 CYAN if a.simulate else ORANGE), (30, 57))
        screen.blit(label.render(f"BALANCE 1:1 | R0 {last_ticks[0]} R1 {last_ticks[1]} R2 {last_ticks[2]} | B/Z: set zero", True, GREEN), (480, 57))
        for i, (n, k, c) in enumerate((("ROLL / R0", "roll", CYAN), ("PITCH / R1", "pitch", ORANGE), ("YAW / R2", "yaw", GOLD))):
            card(screen, label, value, pygame.Rect(28+i*220, 94, 205, 92), n, relative[k], c)
        status = pygame.Rect(700, 94, 552, 92)
        pygame.draw.rect(screen, PANEL, status, border_radius=12)
        screen.blit(label.render("RVC VALID" if live else "WAITING FOR RVC DATA", True, GREEN if live else RED), (status.x+14, status.y+12))
        zero_age = "-" if last_zero_time == 0 else f"{now-last_zero_time:.1f}s ago"
        screen.blit(label.render(f"ZERO: {last_zero_source} ({zero_age}) | SEQ {sample['seq']:03d} | checksum {rvc.bad_checksum}", True, TEXT), (status.x+14, status.y+54))
        stage(screen, label, pygame.font.SysFont("consolas", 14, True), pygame.Rect(28, 205, 790, 525), relative)
        trace(screen, label, pygame.Rect(842, 205, 410, 115), hist["roll"], CYAN, "ROLL - degrees", 35)
        trace(screen, label, pygame.Rect(842, 338, 410, 115), hist["pitch"], ORANGE, "PITCH - degrees", 35)
        trace(screen, label, pygame.Rect(842, 471, 410, 115), hist["yaw"], GOLD, "YAW - degrees", 60)
        trace(screen, label, pygame.Rect(842, 604, 410, 126), hist["vib"], RED, "ACCELERATION VIBRATION - mg", 300)
        pygame.display.flip()
        clock.tick(60)

    if uart:
        uart.close()
    pygame.quit()

if __name__ == "__main__":
    main()
