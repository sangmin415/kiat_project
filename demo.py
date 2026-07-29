"""Interactive virtual drone-detection demonstration.

This is a simulation-only front end: its vision score is derived from the
virtual camera scene. Replace `vision_score()` with local inference from a
supercomputer-trained model before connecting the real FPGA UART.
"""

from __future__ import annotations

import math
import random

import pygame

WIDTH, HEIGHT = 1280, 720
WORLD = pygame.Rect(35, 86, 560, 565)
CAMERA = pygame.Rect(685, 86, 560, 440)
FPS = 60

SKY = (21, 42, 68)
PANEL = (30, 57, 87)
GRID = (62, 91, 121)
TEXT = (232, 241, 248)
MUTED = (155, 177, 196)
BLUE = (74, 160, 255)
YELLOW = (252, 196, 78)
GREEN = (71, 211, 143)
RED = (255, 91, 102)


class FlyingObject:
    def __init__(self, kind: str, x: float, y: float, vx: float, vy: float, size: float):
        self.kind, self.x, self.y = kind, x, y
        self.vx, self.vy, self.size = vx, vy, size

    def update(self, dt: float) -> None:
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.x < -70 or self.x > WORLD.width + 70 or self.y < -70 or self.y > WORLD.height + 70:
            self.x = -55 if self.vx > 0 else WORLD.width + 55
            self.y = random.uniform(65, WORLD.height - 65)


def world_xy(obj: FlyingObject) -> tuple[int, int]:
    return int(WORLD.x + obj.x), int(WORLD.y + obj.y)


def draw_drone(surface: pygame.Surface, x: int, y: int, size: int, color: tuple[int, int, int]) -> None:
    pygame.draw.line(surface, color, (x - size, y - size // 2), (x + size, y + size // 2), 3)
    pygame.draw.line(surface, color, (x - size, y + size // 2), (x + size, y - size // 2), 3)
    for px, py in ((x - size, y - size // 2), (x + size, y + size // 2), (x - size, y + size // 2), (x + size, y - size // 2)):
        pygame.draw.circle(surface, color, (px, py), 5)
    pygame.draw.ellipse(surface, color, (x - size // 2, y - size // 3, size, max(8, size * 2 // 3)))


def draw_bird(surface: pygame.Surface, x: int, y: int, color: tuple[int, int, int]) -> None:
    pygame.draw.arc(surface, color, (x - 19, y - 7, 19, 15), math.pi * 1.08, math.pi * 1.95, 2)
    pygame.draw.arc(surface, color, (x, y - 7, 19, 15), math.pi * 1.05, math.pi * 1.92, 2)


def draw_helicopter(surface: pygame.Surface, x: int, y: int, color: tuple[int, int, int]) -> None:
    pygame.draw.ellipse(surface, color, (x - 17, y - 8, 34, 16), 2)
    pygame.draw.line(surface, color, (x + 15, y), (x + 45, y - 6), 2)
    pygame.draw.line(surface, color, (x + 45, y - 13), (x + 45, y + 2), 2)
    pygame.draw.line(surface, color, (x - 24, y - 16), (x + 24, y - 16), 2)


def draw_object(
    surface: pygame.Surface,
    obj: FlyingObject,
    x: int,
    y: int,
    color: tuple[int, int, int],
    size: int | None = None,
) -> None:
    if obj.kind == "drone":
        draw_drone(surface, x, y, max(11, int(size if size is not None else obj.size)), color)
    elif obj.kind == "bird":
        draw_bird(surface, x, y, color)
    else:
        draw_helicopter(surface, x, y, color)


def vision_score(drone: FlyingObject) -> int:
    """Temporary simulator score; substitute real CPU inference here."""
    dx = drone.x - WORLD.width / 2
    dy = drone.y - WORLD.height / 2
    distance = math.hypot(dx, dy)
    if distance > 238:
        return 0
    return max(0, min(99, int(92 - distance * 0.22 + drone.size * 1.1)))


def label(font: pygame.font.Font, surface: pygame.Surface, text: str, pos: tuple[int, int], color=TEXT) -> None:
    surface.blit(font.render(text, True, color), pos)


def main() -> None:
    pygame.init()
    pygame.display.set_caption("KIAT Drone Detection - Virtual Environment Demo")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    title = pygame.font.SysFont("consolas", 25, bold=True)
    body = pygame.font.SysFont("consolas", 17)
    small = pygame.font.SysFont("consolas", 14)

    objects = [
        FlyingObject("drone", -30, 275, 72, -9, 16),
        FlyingObject("bird", 520, 115, -105, 17, 9),
        FlyingObject("helicopter", 600, 470, -38, -4, 15),
    ]
    drone = objects[0]
    running, paused = True, False
    stable_frames = 0
    state = "NORMAL"

    while running:
        dt = clock.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                paused = not paused
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                drone.x, drone.y = -30, 275
                stable_frames, state = 0, "NORMAL"

        if not paused:
            for obj in objects:
                obj.update(dt)

        score = vision_score(drone)
        detected = score >= 70
        stable_frames = min(5, stable_frames + 1) if detected else max(0, stable_frames - 2)
        state = "DETECT" if stable_frames >= 5 else "SUSPECT" if stable_frames else "NORMAL"
        packet = f"D,{score:02d}" if detected else "N,00"

        screen.fill(SKY)
        label(title, screen, "KIAT DRONE DETECTION / HARDWARE-IN-THE-LOOP", (35, 28))
        label(small, screen, "Space: pause/resume    R: reset drone    Esc: exit", (35, 57), MUTED)

        pygame.draw.rect(screen, PANEL, WORLD)
        pygame.draw.rect(screen, PANEL, CAMERA)
        for x in range(WORLD.x, WORLD.right, 56):
            pygame.draw.line(screen, GRID, (x, WORLD.y), (x, WORLD.bottom), 1)
        for y in range(WORLD.y, WORLD.bottom, 56):
            pygame.draw.line(screen, GRID, (WORLD.x, y), (WORLD.right, y), 1)
        label(body, screen, "3D-airspace substitute: live 2D world", (WORLD.x + 14, WORLD.y + 14))
        label(body, screen, "Virtual camera frame -> CPU vision", (CAMERA.x + 14, CAMERA.y + 14))

        zone = pygame.Rect(WORLD.centerx - 190, WORLD.centery - 150, 380, 300)
        pygame.draw.rect(screen, MUTED, zone, 2, border_radius=4)
        label(small, screen, "camera field", (zone.x + 7, zone.y + 7), MUTED)
        for obj in objects:
            x, y = world_xy(obj)
            color = BLUE if obj.kind == "drone" else YELLOW if obj.kind == "bird" else GREEN
            draw_object(screen, obj, x, y, color)
            label(small, screen, obj.kind, (x - 24, y + 28), color)

        # A separate camera rendering: only objects inside the camera field are visible.
        for obj in objects:
            x, y = world_xy(obj)
            if zone.collidepoint(x, y):
                cx = CAMERA.x + (x - zone.x) * CAMERA.width // zone.width
                cy = CAMERA.y + 45 + (y - zone.y) * 330 // zone.height
                color = RED if obj.kind == "drone" and detected else BLUE if obj.kind == "drone" else YELLOW if obj.kind == "bird" else GREEN
                draw_object(screen, obj, cx, cy, color, max(12, int(obj.size * 1.45)))
                if obj.kind == "drone" and detected:
                    box = pygame.Rect(cx - 42, cy - 42, 84, 84)
                    pygame.draw.rect(screen, RED, box, 2)
                    label(small, screen, f"drone {score}%", (box.x, box.y - 20), RED)

        pygame.draw.rect(screen, PANEL, (685, 550, 560, 101), border_radius=4)
        state_color = RED if state == "DETECT" else YELLOW if state == "SUSPECT" else GREEN
        label(body, screen, "PC detector", (702, 567))
        label(body, screen, f"confidence: {score:02d}%", (702, 595), state_color)
        label(body, screen, "UART packet", (900, 567))
        label(body, screen, packet, (900, 595), state_color)
        label(body, screen, "FPGA FSM", (1050, 567))
        label(body, screen, state, (1050, 595), state_color)
        label(small, screen, "DETECT: FPGA 7-seg dEtECt / RGB red / buzzer output", (702, 626), MUTED)

        if paused:
            label(title, screen, "PAUSED", (555, 680), YELLOW)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()


