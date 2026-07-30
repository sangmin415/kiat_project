import csv
import math
import random
import time
import tkinter as tk
from collections import deque
from pathlib import Path

BLACK, GOLD, DARK_GOLD = "#000000", "#CFB991", "#8E6F3E"
WHITE, GRAY, RED = "#F5F5F5", "#A7A8AA", "#C62828"


class PurdueInterlockDemo:
    def __init__(self, root):
        self.root = root
        self.root.title("Purdue KIAT - Photo Process Interlock")
        self.root.geometry("1180x720")
        self.root.configure(bg=BLACK)
        self.mode, self.tick = "NORMAL", 0
        self.values = deque([5] * 180, maxlen=180)
        self.event_latched = False
        self.motor_enable = True
        self.log_path = Path("logs/windows_demo.csv")
        self.log_path.parent.mkdir(exist_ok=True)
        self.log = self.log_path.open("w", newline="", buffering=1)
        self.writer = csv.writer(self.log)
        self.writer.writerow(["time_ms", "vibration", "state", "event", "motor_enable"])
        self.build()
        self.update()

    def build(self):
        header = tk.Frame(self.root, bg=BLACK, pady=18)
        header.pack(fill="x")
        tk.Label(header, text="PURDUE KIAT", bg=BLACK, fg=GOLD,
                 font=("Arial", 25, "bold")).pack(side="left", padx=28)
        tk.Label(header, text="PHOTO PROCESS INTERLOCK / FDC MONITOR",
                 bg=BLACK, fg=WHITE, font=("Arial", 16)).pack(side="left")
        self.clock = tk.Label(header, bg=BLACK, fg=GRAY, font=("Consolas", 12))
        self.clock.pack(side="right", padx=28)

        controls = tk.Frame(self.root, bg="#111111", pady=10)
        controls.pack(fill="x")
        for label, mode in [("NORMAL", "NORMAL"), ("WARNING", "WARNING"),
                            ("VIBRATION TRIP", "INTERLOCK"),
                            ("ESD_SIM", "ESD_SIM"), ("RESET", "RESET")]:
            tk.Button(controls, text=label, command=lambda m=mode: self.set_mode(m),
                      bg=GOLD if mode != "INTERLOCK" else RED, fg=BLACK,
                      activebackground=DARK_GOLD, relief="flat",
                      font=("Arial", 10, "bold"), padx=16, pady=7).pack(side="left", padx=6)

        body = tk.Frame(self.root, bg=BLACK)
        body.pack(fill="both", expand=True, padx=24, pady=18)
        self.canvas = tk.Canvas(body, bg="#080808", highlightthickness=1,
                                highlightbackground=DARK_GOLD)
        self.canvas.pack(side="left", fill="both", expand=True)
        panel = tk.Frame(body, bg="#111111", width=260)
        panel.pack(side="right", fill="y", padx=(18, 0))
        panel.pack_propagate(False)
        self.status = self.metric(panel, "SYSTEM STATE", "NORMAL", GOLD)
        self.level = self.metric(panel, "VIBRATION LEVEL", "5", WHITE)
        self.motor = self.metric(panel, "MOTOR ENABLE", "ON", GOLD)
        self.event = self.metric(panel, "EVENT LATCH", "CLEAR", WHITE)
        self.uart = self.metric(panel, "UART", "DEMO MODE", GRAY)
        tk.Label(panel, text="CSV LOG\nlogs/windows_demo.csv", bg="#111111",
                 fg=GRAY, justify="left", font=("Consolas", 10)).pack(
                     anchor="w", padx=18, pady=22)

    @staticmethod
    def metric(parent, label, value, color):
        tk.Label(parent, text=label, bg="#111111", fg=GRAY,
                 font=("Arial", 9, "bold")).pack(anchor="w", padx=18, pady=(18, 2))
        widget = tk.Label(parent, text=value, bg="#111111", fg=color,
                          font=("Arial", 19, "bold"))
        widget.pack(anchor="w", padx=18)
        return widget

    def set_mode(self, mode):
        if mode == "RESET":
            self.mode, self.event_latched, self.motor_enable = "NORMAL", False, True
        elif not self.motor_enable:
            return
        else:
            self.mode = mode
            if mode in ("INTERLOCK", "ESD_SIM"):
                self.motor_enable = False
                self.event_latched = mode == "ESD_SIM"

    def next_value(self):
        base = {"NORMAL": 7, "WARNING": 30, "INTERLOCK": 66, "ESD_SIM": 10}[self.mode]
        return max(0, int(base + 3 * math.sin(self.tick / 8) + random.uniform(-2, 2)))

    def draw_plot(self):
        c = self.canvas
        c.delete("all")
        w, h = max(c.winfo_width(), 600), max(c.winfo_height(), 400)
        l, r, t, b = 62, w - 25, 35, h - 48
        c.create_text(l, 14, text="REAL-TIME VIBRATION TREND", anchor="w",
                      fill=GOLD, font=("Arial", 12, "bold"))
        for value, color, label in [(20, GOLD, "WARNING 20"), (50, RED, "INTERLOCK 50")]:
            y = b - value / 80 * (b - t)
            c.create_line(l, y, r, y, fill=color, dash=(6, 4))
            c.create_text(r - 4, y - 9, text=label, anchor="e", fill=color)
        for value in range(0, 81, 20):
            y = b - value / 80 * (b - t)
            c.create_line(l, y, r, y, fill="#292929")
            c.create_text(l - 10, y, text=str(value), anchor="e", fill=GRAY)
        points = []
        data = list(self.values)
        for i, value in enumerate(data):
            x = l + i / (len(data) - 1) * (r - l)
            y = b - value / 80 * (b - t)
            points.extend((x, y))
        c.create_line(*points, fill=GOLD, width=3, smooth=True)
        c.create_text((l + r) / 2, h - 18, text="LAST 30 SECONDS",
                      fill=GRAY, font=("Arial", 9))

    def update(self):
        self.tick += 1
        value = self.next_value()
        self.values.append(value)
        state_color = RED if self.mode in ("INTERLOCK", "ESD_SIM") else GOLD
        self.status.config(text=self.mode, fg=state_color)
        self.level.config(text=str(value), fg=state_color if value >= 50 else WHITE)
        self.motor.config(text="ON" if self.motor_enable else "OFF",
                          fg=GOLD if self.motor_enable else RED)
        self.event.config(text="LATCHED" if self.event_latched else "CLEAR",
                          fg=RED if self.event_latched else WHITE)
        self.clock.config(text=time.strftime("%Y-%m-%d  %H:%M:%S"))
        self.writer.writerow([self.tick * 100, value, self.mode,
                              int(self.event_latched), int(self.motor_enable)])
        self.draw_plot()
        self.root.after(100, self.update)


if __name__ == "__main__":
    root = tk.Tk()
    app = PurdueInterlockDemo(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.log.close(), root.destroy()))
    root.mainloop()

