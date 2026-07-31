"""Purdue KIAT FPGA interlock dashboard: COM12 hardware + no-sensor simulation."""

import argparse
import csv
import math
import random
import time
from collections import deque
from pathlib import Path

import pygame

try:
    import serial
except ImportError:
    serial = None

WIDTH, HEIGHT, FPS = 1440, 860, 60
BLACK, PANEL, PANEL2 = (8, 9, 10), (20, 21, 23), (29, 31, 34)
GRID, GOLD, GOLD2 = (54, 57, 61), (207, 185, 145), (148, 117, 67)
WHITE, GRAY = (244, 244, 242), (158, 162, 166)
RED, BLUE, GREEN, ORANGE = (220, 65, 65), (72, 154, 219), (76, 190, 112), (231, 153, 62)

CMD = {"NORMAL": 0x10, "WARNING": 0x11, "VIBRATION": 0x12,
       "ESD_SIM": 0x13, "RESET": 0x14, "STOP": 0x15, "STATUS": 0xF0}
STATE_NAMES = {0: "NORMAL", 1: "WARNING", 2: "INTERLOCK", 3: "UNKNOWN"}


class UartBridge:
    def __init__(self, port, baud):
        self.port, self.baud, self.device = port, baud, None
        self.error = ""
        if serial is None:
            self.error = "pyserial is not installed"
            return
        try:
            self.device = serial.Serial(port, baud, timeout=0, write_timeout=0.2)
            self.device.reset_input_buffer()
        except Exception as exc:
            self.error = str(exc)

    @property
    def connected(self):
        return self.device is not None and self.device.is_open

    def send(self, value):
        if self.connected:
            self.device.write(bytes([value]))

    def read(self):
        if not self.connected:
            return []
        return list(self.device.read(self.device.in_waiting or 0))

    def close(self):
        if self.connected:
            self.device.close()


class Button:
    def __init__(self, rect, label, color, callback):
        self.rect, self.label, self.color, self.callback = pygame.Rect(rect), label, color, callback

    def draw(self, screen, font, mouse):
        color = tuple(min(255, c + 18) for c in self.color) if self.rect.collidepoint(mouse) else self.color
        pygame.draw.rect(screen, color, self.rect, border_radius=5)
        text = font.render(self.label, True, BLACK)
        screen.blit(text, text.get_rect(center=self.rect.center))


class Dashboard:
    def __init__(self, args):
        pygame.init()
        pygame.display.set_caption("Purdue KIAT | FPGA Process Interlock")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.small = pygame.font.SysFont("arial", 14)
        self.font = pygame.font.SysFont("arial", 17)
        self.bold = pygame.font.SysFont("arial", 18, bold=True)
        self.metric = pygame.font.SysFont("consolas", 24, bold=True)
        self.title = pygame.font.SysFont("arial", 30, bold=True)
        self.uart = UartBridge(args.port, args.baud) if not args.demo else None
        self.hardware = bool(self.uart and self.uart.connected)
        self.smoke_frames = args.smoke_test

        self.state, self.trip_reason = "STOPPED", "NONE"
        self.motor_enable = self.event_latched = False
        self.requested_pwm = self.applied_pwm = 0
        self.mode, self.pending = "STOP", None
        self.last_poll, self.last_sample = 0, 0
        self.fault_until, self.next_random = 0.0, 0.0
        self.random_test = False
        self.rotor_angle, self.rotor_speed = 0.0, 0.0
        self.vibration = self.average = 0.0
        self.ax = self.ay = self.az = 0
        self.samples = deque([0.0] * 220, maxlen=220)
        self.averages = deque([0.0] * 220, maxlen=220)
        self.events = deque(maxlen=6)
        self.message = "COM12 connected; FPGA status polling active." if self.hardware else "OFFLINE DEMO: FPGA link unavailable."
        if self.uart and self.uart.error:
            self.message += " " + self.uart.error

        log_dir = Path(__file__).resolve().parents[1] / "logs"
        log_dir.mkdir(exist_ok=True)
        self.log_handle = (log_dir / "pygame_uart_demo.csv").open("w", newline="", buffering=1)
        self.writer = csv.writer(self.log_handle)
        self.writer.writerow(["time", "mode", "state", "motor_enable", "event_latched",
                              "ax", "ay", "az", "vibration", "average", "pwm"])
        self.buttons = [
            Button((24, 82, 126, 40), "RUN NORMAL", GOLD, lambda: self.command("NORMAL")),
            Button((158, 82, 112, 40), "WARNING", ORANGE, lambda: self.command("WARNING")),
            Button((278, 82, 164, 40), "STRONG VIB", RED, lambda: self.command("VIBRATION")),
            Button((450, 82, 112, 40), "ESD_SIM", RED, lambda: self.command("ESD_SIM")),
            Button((570, 82, 134, 40), "RANDOM", BLUE, self.toggle_random),
            Button((712, 82, 104, 40), "RESET", GOLD, lambda: self.command("RESET")),
            Button((824, 82, 94, 40), "STOP", GRAY, lambda: self.command("STOP")),
        ]
        self.add_event("SYSTEM", "UART CONNECTED" if self.hardware else "DEMO MODE")

    def add_event(self, kind, detail):
        self.events.appendleft((time.strftime("%H:%M:%S"), kind, detail))

    def command(self, name):
        self.pending = name
        if self.hardware:
            self.uart.send(CMD[name])
        self.mode = name
        if name == "NORMAL":
            self.requested_pwm, self.trip_reason = 40, "NONE"
        elif name == "WARNING":
            self.requested_pwm = 65
        elif name == "VIBRATION":
            self.requested_pwm, self.fault_until = 95, time.monotonic() + 1.4
            self.rotor_speed = max(self.rotor_speed, 17.0)
            self.trip_reason = "VIBRATION_SIM"
        elif name == "ESD_SIM":
            self.requested_pwm, self.trip_reason = 0, "ESD_SIM"
        elif name in ("RESET", "STOP"):
            self.requested_pwm, self.trip_reason = 0, "NONE"
        if not self.hardware:
            self.apply_demo_command(name)
        self.add_event("TX", f"{name} 0x{CMD[name]:02X}")

    def apply_demo_command(self, name):
        if name == "NORMAL": self.state, self.motor_enable, self.event_latched = "NORMAL", True, False
        elif name == "WARNING": self.state, self.motor_enable = "WARNING", True
        elif name == "VIBRATION": self.state, self.motor_enable = "INTERLOCK", False
        elif name == "ESD_SIM": self.state, self.motor_enable, self.event_latched = "INTERLOCK", False, True
        elif name in ("RESET", "STOP"): self.state, self.motor_enable, self.event_latched = "STOPPED", False, False

    def toggle_random(self):
        self.random_test = not self.random_test
        if self.random_test:
            self.command("NORMAL")
            self.next_random = time.monotonic() + random.uniform(3.0, 7.0)
            self.add_event("ARM", "RANDOM FAULT 3-7 s")
        else:
            self.add_event("DISARM", "RANDOM TEST")

    def process_uart(self):
        if not self.hardware:
            return
        for value in self.uart.read():
            if value & 0x80:
                state_code = (value >> 2) & 0x03
                stopped = bool(value & 0x01)
                self.event_latched = bool(value & 0x40)
                self.motor_enable = bool(value & 0x20)
                self.state = "STOPPED" if stopped and state_code == 0 else STATE_NAMES[state_code]
                if self.state == "INTERLOCK" and self.trip_reason == "NONE":
                    self.trip_reason = "ESD_SIM" if self.event_latched else "VIBRATION_SIM"
            else:
                self.add_event("ACK", f"0x{value:02X}")
                self.pending = None
        now = pygame.time.get_ticks()
        if now - self.last_poll >= 200:
            self.last_poll = now
            self.uart.send(CMD["STATUS"])

    def sample(self):
        now = time.monotonic()
        if self.random_test and now >= self.next_random and self.state != "INTERLOCK":
            self.random_test = False
            self.command(random.choice(("VIBRATION", "ESD_SIM")))
        fault = now < self.fault_until
        self.applied_pwm = self.requested_pwm if self.motor_enable else 0
        base = self.applied_pwm / 100.0
        amplitude = 2.0 + 40.0 * base * base
        if fault: amplitude += 52.0
        phase = now * (8.0 + 18.0 * max(base, 0.25))
        self.ax = int(amplitude * math.sin(phase) + random.gauss(0, 1.5))
        self.ay = int(amplitude * .70 * math.sin(phase * 1.17 + .8) + random.gauss(0, 1.3))
        self.az = int(amplitude * .45 * math.sin(phase * .87 + 1.6) + random.gauss(0, 1.0))
        self.vibration = abs(self.ax) + abs(self.ay) + abs(self.az)
        self.samples.append(self.vibration)
        self.average = sum(list(self.samples)[-12:]) / 12
        self.averages.append(self.average)
        self.writer.writerow([time.time(), self.mode, self.state, int(self.motor_enable),
                              int(self.event_latched), self.ax, self.ay, self.az,
                              self.vibration, f"{self.average:.2f}", self.applied_pwm])

    def update_motion(self):
        target = self.applied_pwm * 0.15
        if time.monotonic() < self.fault_until and self.state != "INTERLOCK": target += 9.0
        rate = 0.16 if target > self.rotor_speed else 0.075
        self.rotor_speed += (target - self.rotor_speed) * rate
        if abs(self.rotor_speed) < .02: self.rotor_speed = 0.0
        self.rotor_angle = (self.rotor_angle + self.rotor_speed / FPS) % (2 * math.pi)

    def panel(self, rect, title):
        pygame.draw.rect(self.screen, PANEL, rect, border_radius=6)
        pygame.draw.rect(self.screen, GOLD2, rect, 1, border_radius=6)
        self.screen.blit(self.bold.render(title, True, GOLD), (rect.x + 15, rect.y + 12))

    def draw_rig(self, rect):
        self.panel(rect, "ROTATING VIBRATION TEST RIG")
        cx, cy, radius = rect.centerx, rect.centery - 12, min(rect.width, rect.height) // 3
        shake = min(8, int(self.vibration / 17))
        if self.rotor_speed:
            cx += int(math.sin(self.rotor_angle * 3) * shake)
            cy += int(math.cos(self.rotor_angle * 2) * shake)
        pygame.draw.circle(self.screen, PANEL2, (cx, cy), radius)
        outline = RED if self.state == "INTERLOCK" else GOLD
        pygame.draw.circle(self.screen, outline, (cx, cy), radius, 4)
        for offset in (0, math.pi / 2):
            angle = self.rotor_angle + offset
            dx, dy = int(math.cos(angle) * radius), int(math.sin(angle) * radius)
            pygame.draw.line(self.screen, GRID, (cx-dx, cy-dy), (cx+dx, cy+dy), 2)
        ex = cx + int(math.cos(self.rotor_angle) * radius * .62)
        ey = cy + int(math.sin(self.rotor_angle) * radius * .62)
        pygame.draw.circle(self.screen, BLUE, (ex, ey), 17)
        pygame.draw.circle(self.screen, GREEN, (cx, cy), 13)
        pygame.draw.arc(self.screen, GOLD, (cx-radius-15, cy-radius-15, 2*radius+30, 2*radius+30),
                        self.rotor_angle, self.rotor_angle + 1.4, 4)
        speed = self.metric.render(f"{self.rotor_speed:04.1f} rad/s", True, WHITE)
        self.screen.blit(speed, speed.get_rect(center=(rect.centerx, rect.bottom - 62)))
        caption = "BLUE: eccentric motor   GREEN: BNO085 (simulated)"
        self.screen.blit(self.small.render(caption, True, GRAY),
                         self.small.render(caption, True, GRAY).get_rect(center=(rect.centerx, rect.bottom - 30)))

    def draw_plot(self, rect):
        self.panel(rect, "REAL-TIME VIBRATION | SIMULATED UNTIL BNO085 ARRIVES")
        plot = pygame.Rect(rect.x + 48, rect.y + 48, rect.width - 68, rect.height - 88)
        ymax = 140
        for value in range(0, ymax + 1, 35):
            y = plot.bottom - int(value / ymax * plot.height)
            pygame.draw.line(self.screen, GRID, (plot.left, y), (plot.right, y))
            self.screen.blit(self.small.render(str(value), True, GRAY), (plot.left - 34, y - 7))
        for data, color, width in ((self.samples, GOLD, 2), (self.averages, BLUE, 3)):
            vals, points = list(data), []
            for i, value in enumerate(vals):
                x = plot.left + int(i / (len(vals)-1) * plot.width)
                y = plot.bottom - int(min(ymax, value) / ymax * plot.height)
                points.append((x, y))
            pygame.draw.lines(self.screen, color, False, points, width)

    def draw_status(self, rect):
        self.panel(rect, "FPGA LIVE STATUS")
        state_color = RED if self.state == "INTERLOCK" else ORANGE if self.state == "WARNING" else GREEN if self.state == "NORMAL" else GRAY
        rows = [
            ("SYSTEM STATE", self.state, state_color),
            ("UART LINK", f"{self.uart.port} / 115200" if self.hardware else "OFFLINE DEMO", GREEN if self.hardware else ORANGE),
            ("MOTOR ENABLE", "ON" if self.motor_enable else "OFF", GREEN if self.motor_enable else RED),
            ("ESD EVENT", "LATCHED" if self.event_latched else "CLEAR", RED if self.event_latched else WHITE),
            ("TRIP REASON", self.trip_reason, RED if self.trip_reason != "NONE" else WHITE),
            ("ACCEL XYZ", f"{self.ax:+4d} {self.ay:+4d} {self.az:+4d}", WHITE),
            ("VIB / AVG", f"{self.vibration:5.1f} / {self.average:5.1f}", WHITE),
            ("PWM REQ / APPLIED", f"{self.requested_pwm:3d}% / {self.applied_pwm:3d}%", GOLD),
        ]
        y = rect.y + 50
        for label, value, color in rows:
            self.screen.blit(self.small.render(label, True, GRAY), (rect.x + 17, y))
            self.screen.blit(self.bold.render(value, True, color), (rect.x + 17, y + 18))
            y += 53
        self.screen.blit(self.small.render("RECENT UART / CONTROL EVENTS", True, GOLD), (rect.x + 17, y + 2))
        y += 27
        for stamp, kind, detail in self.events:
            self.screen.blit(self.small.render(f"{stamp}  {kind:<5} {detail}", True, GRAY), (rect.x + 17, y))
            y += 20

    def draw(self):
        self.screen.fill(BLACK)
        width, height = self.screen.get_size()
        self.screen.blit(self.title.render("PURDUE KIAT", True, GOLD), (24, 18))
        self.screen.blit(self.font.render("FPGA PHOTO PROCESS EQUIPMENT INTERLOCK", True, WHITE), (230, 29))
        link = "FPGA ONLINE" if self.hardware else "DEMO MODE"
        color = GREEN if self.hardware else ORANGE
        badge = self.bold.render(link, True, color)
        self.screen.blit(badge, (width - badge.get_width() - 25, 27))
        pygame.draw.line(self.screen, GOLD2, (24, 66), (width-24, 66), 2)
        mouse = pygame.mouse.get_pos()
        for button in self.buttons: button.draw(self.screen, self.small, mouse)
        top, bottom = 140, height - 62
        left_w, right_w = 365, 320
        self.draw_rig(pygame.Rect(24, top, left_w, bottom-top))
        self.draw_plot(pygame.Rect(405, top, width-left_w-right_w-92, bottom-top))
        self.draw_status(pygame.Rect(width-right_w-24, top, right_w, bottom-top))
        self.screen.blit(self.font.render(self.message, True, GRAY), (24, height-40))
        hint = "N Normal | W Warning | V Vibration | E ESD | A Random | R Reset | S Stop"
        hint_img = self.small.render(hint, True, GRAY)
        self.screen.blit(hint_img, (width-hint_img.get_width()-24, height-37))
        pygame.display.flip()

    def run(self):
        running, frame_count = True, 0
        keys = {pygame.K_n:"NORMAL", pygame.K_w:"WARNING", pygame.K_v:"VIBRATION",
                pygame.K_e:"ESD_SIM", pygame.K_r:"RESET", pygame.K_s:"STOP"}
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_a: self.toggle_random()
                    elif event.key in keys: self.command(keys[event.key])
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for button in self.buttons:
                        if button.rect.collidepoint(event.pos): button.callback(); break
            self.process_uart()
            now = pygame.time.get_ticks()
            if now - self.last_sample >= 100:
                self.last_sample = now; self.sample()
            self.update_motion(); self.draw(); self.clock.tick(FPS)
            frame_count += 1
            if self.smoke_frames and frame_count >= self.smoke_frames: running = False
        if self.uart: self.uart.close()
        self.log_handle.close(); pygame.quit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="COM12")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--demo", action="store_true", help="Do not open a serial port")
    parser.add_argument("--smoke-test", type=int, default=0, metavar="FRAMES")
    Dashboard(parser.parse_args()).run()


if __name__ == "__main__":
    main()

