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
    # Simple attitude view: no decorative mechanism, only the three controlled
    # axes and the resulting tilted stage plane.
    pygame.draw.rect(screen, PANEL, rect, border_radius=12)
    pygame.draw.rect(screen, GOLD, rect, 2, border_radius=12)
    screen.blit(font.render("3-AXIS ATTITUDE / LEVELING VIEW", True, TEXT), (rect.x+16, rect.y+14))
    screen.blit(small.render("R0 Roll (X)   R1 Pitch (Y)   R2 Yaw (Z)   |   zero-relative angles", True, GOLD), (rect.x+16, rect.y+45))

    cx, cy = rect.centerx, rect.centery+24
    roll = clamp(s["roll"], -30, 30)
    pitch = clamp(s["pitch"], -30, 30)
    yaw = clamp(s["yaw"], -45, 45)

    # Reference horizontal plane: thin gray outline.
    ref = [(cx-142, cy-54), (cx+142, cy-54), (cx+142, cy+54), (cx-142, cy+54)]
    pygame.draw.polygon(screen, (16, 37, 58), ref)
    pygame.draw.polygon(screen, GRID, ref, 2)
    screen.blit(small.render("REFERENCE LEVEL", True, GRID), (cx-58, cy-88))

    # Current wafer stage plane: perspective shift conveys Roll and Pitch.
    ldy, rdy = int(roll*1.5 + pitch*.45), int(-roll*1.5 + pitch*.45)
    depth = int(pitch*1.0)
    plane = [(cx-118, cy-42+ldy), (cx+118, cy-42+rdy),
             (cx+118, cy+42+rdy+depth), (cx-118, cy+42+ldy+depth)]
    pygame.draw.polygon(screen, (22, 93, 112), plane)
    pygame.draw.polygon(screen, CYAN, plane, 4)
    pygame.draw.line(screen, CYAN, plane[0], plane[2], 1)
    pygame.draw.line(screen, CYAN, plane[1], plane[3], 1)
    label = font.render("STAGE", True, TEXT)
    screen.blit(label, (cx-label.get_width()//2, cy-12+int(pitch*.7)))

    # R0 Roll: cyan X-axis through the stage.
    pygame.draw.line(screen, CYAN, (cx-175, cy+ldy), (cx+175, cy+rdy), 4)
    pygame.draw.polygon(screen, CYAN, [(cx+175,cy+rdy),(cx+160,cy+rdy-7),(cx+160,cy+rdy+7)])
    screen.blit(small.render(f"X / R0 ROLL  {roll:+.2f}°", True, CYAN), (cx-174, cy+100))

    # R1 Pitch: orange Y-axis, vertical perspective direction.
    pygame.draw.line(screen, ORANGE, (cx, cy+130+int(pitch)), (cx, cy-138+int(pitch)), 4)
    pygame.draw.polygon(screen, ORANGE, [(cx,cy-138+int(pitch)),(cx-7,cy-122+int(pitch)),(cx+7,cy-122+int(pitch))])
    screen.blit(small.render(f"Y / R1 PITCH  {pitch:+.2f}°", True, ORANGE), (cx+16, cy+100))

    # R2 Yaw: gold rotation arc around the Z axis.
    arc = pygame.Rect(cx-108, cy-108, 216, 216)
    begin = math.radians(-90)
    end = math.radians(-90 + yaw)
    pygame.draw.arc(screen, GOLD, arc, min(begin,end), max(begin,end), 5)
    pygame.draw.circle(screen, GOLD, (cx, cy), 9, 2)
    pygame.draw.line(screen, GOLD, (cx,cy), (cx,cy-82), 3)
    screen.blit(small.render(f"Z / R2 YAW  {yaw:+.2f}°", True, GOLD), (rect.right-180, cy+100))

    # Crosshair makes 0-degree alignment immediately visible.
    pygame.draw.line(screen, GRID, (cx-8,cy), (cx+8,cy), 1)
    pygame.draw.line(screen, GRID, (cx,cy-8), (cx,cy+8), 1)

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
