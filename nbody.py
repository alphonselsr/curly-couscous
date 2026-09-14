"""Interactive 2D/3D n-body sandbox.

Run with: python nbody.py
Requires pygame (pip install -r requirements.txt).
"""

import math
from dataclasses import dataclass

import pygame


WIDTH, HEIGHT = 1200, 760
PANEL_WIDTH = 292
WORLD_RECT = pygame.Rect(PANEL_WIDTH, 0, WIDTH - PANEL_WIDTH, HEIGHT)
FPS = 60

BG = (9, 13, 24)
PANEL = (17, 24, 39)
PANEL_EDGE = (37, 49, 72)
TEXT = (226, 233, 245)
MUTED = (133, 149, 177)
ACCENT = (83, 211, 190)
ACCENT_DARK = (34, 95, 99)
ORANGE = (255, 166, 88)


@dataclass
class Body:
    x: float
    y: float
    vx: float
    vy: float
    z: float
    vz: float
    mass: float
    radius: float
    color: tuple[int, int, int]
    trail: list[tuple[float, float, float]]


class Slider:
    def __init__(self, rect, minimum, maximum, value, label, formatter=str):
        self.rect = pygame.Rect(rect)
        self.minimum = minimum
        self.maximum = maximum
        self.value = value
        self.label = label  
        self.formatter = formatter
        self.dragging = False

    def _set_from_x(self, x):
        ratio = max(0.0, min(1.0, (x - self.rect.left) / self.rect.width))
        self.value = self.minimum + ratio * (self.maximum - self.minimum)

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.inflate(0, 18).collidepoint(event.pos):
                self.dragging = True
                self._set_from_x(event.pos[0])
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_from_x(event.pos[0])
            return True
        return False

    def draw(self, surface, font, small_font):
        label = font.render(self.label, True, TEXT)
        value = small_font.render(self.formatter(self.value), True, ACCENT)
        surface.blit(label, (self.rect.left, self.rect.top - 25))
        surface.blit(value, (self.rect.right - value.get_width(), self.rect.top - 23))
        pygame.draw.rect(surface, (47, 61, 84), self.rect, border_radius=3)
        ratio = (self.value - self.minimum) / (self.maximum - self.minimum)
        fill = self.rect.copy()
        fill.width = max(6, int(fill.width * ratio))
        pygame.draw.rect(surface, ACCENT_DARK, fill, border_radius=3)
        knob_x = self.rect.left + int(self.rect.width * ratio)
        pygame.draw.circle(surface, ACCENT, (knob_x, self.rect.centery), 8)


class Button:
    def __init__(self, rect, text, accent=False):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.accent = accent

    def clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)

    def draw(self, surface, font, hovered=False):
        color = (31, 48, 67) if hovered else (24, 35, 53)
        if self.accent:
            color = (30, 107, 107) if hovered else (25, 80, 86)
        pygame.draw.rect(surface, color, self.rect, border_radius=5)
        pygame.draw.rect(surface, PANEL_EDGE, self.rect, 1, border_radius=5)
        label = font.render(self.text, True, TEXT)
        surface.blit(label, label.get_rect(center=self.rect.center))


class Simulation:
    def __init__(self):
        self.bodies: list[Body] = []
        self.selected = None
        self.dragging_body = None
        self.drag_origin = None
        self.paused = False
        self.show_trails = True
        self.show_vectors = True
        self.is_3d = False
        self.spawn_mass = 80.0
        self.reset(8)

    def reset(self, count):
        self.bodies.clear()
        cx = WORLD_RECT.centerx
        cy = WORLD_RECT.centery
        for index in range(count):
            angle = index * math.tau / max(count, 1)
            orbit = 90 + index * 19
            x = cx + math.cos(angle) * orbit
            y = cy + math.sin(angle) * orbit
            speed = 1.3 + index * 0.035
            depth = math.sin(angle * 1.7) * 115 if self.is_3d else 0
            self.bodies.append(Body(x, y, -math.sin(angle) * speed, math.cos(angle) * speed,
                                    depth, math.cos(angle * 1.4) * 0.25 if self.is_3d else 0,
                                    70 + index * 8, 5 + (index % 4), self.color_for(index), []))
        self.selected = 0 if self.bodies else None

    @staticmethod
    def color_for(index):
        colors = [(83, 211, 190), (255, 166, 88), (151, 126, 255), (255, 103, 115), (105, 179, 255)]
        return colors[index % len(colors)]

    def step(self, dt, gravity, softening):
        if self.paused:
            return
        accelerations = [(0.0, 0.0, 0.0) for _ in self.bodies]
        for first_index, first in enumerate(self.bodies):
            for second_index in range(first_index + 1, len(self.bodies)):
                second = self.bodies[second_index]
                dx = second.x - first.x
                dy = second.y - first.y
                dz = second.z - first.z if self.is_3d else 0
                distance_sq = dx * dx + dy * dy + dz * dz + softening * softening
                distance = math.sqrt(distance_sq)
                force = gravity / distance_sq
                ax = force * dx / distance
                ay = force * dy / distance
                az = force * dz / distance
                accelerations[first_index] = (accelerations[first_index][0] + ax * second.mass,
                                               accelerations[first_index][1] + ay * second.mass,
                                               accelerations[first_index][2] + az * second.mass)
                accelerations[second_index] = (accelerations[second_index][0] - ax * first.mass,
                                                accelerations[second_index][1] - ay * first.mass,
                                                accelerations[second_index][2] - az * first.mass)

        for index, body in enumerate(self.bodies):
            body.vx += accelerations[index][0] * dt
            body.vy += accelerations[index][1] * dt
            body.vz += accelerations[index][2] * dt
            body.x += body.vx * dt
            body.y += body.vy * dt
            body.z += body.vz * dt if self.is_3d else 0
            if self.show_trails and (not body.trail or abs(body.x - body.trail[-1][0]) > 2):
                body.trail.append((body.x, body.y, body.z))
                if len(body.trail) > 110:
                    body.trail.pop(0)

    def body_at(self, position):
        nearest = None
        nearest_distance = 16
        for index, body in enumerate(self.bodies):
            projected = self.project(body)
            distance = math.hypot(projected[0] - position[0], projected[1] - position[1])
            if distance < nearest_distance:
                nearest, nearest_distance = index, distance
        return nearest

    def add_body(self, position, velocity=(0, 0)):
        self.bodies.append(Body(position[0], position[1], velocity[0], velocity[1], 0, 0,
                                self.spawn_mass, 6, self.color_for(len(self.bodies)), []))
        self.selected = len(self.bodies) - 1

    def set_dimension(self, is_3d):
        self.is_3d = is_3d
        for index, body in enumerate(self.bodies):
            if is_3d:
                angle = index * math.tau / max(len(self.bodies), 1)
                body.z = math.sin(angle * 1.7) * 115
                body.vz = math.cos(angle * 1.4) * 0.25
            else:
                body.z = 0
                body.vz = 0
            body.trail.clear()

    def project(self, body):
        if not self.is_3d:
            return body.x, body.y, body.radius
        depth = max(0.55, min(1.5, 1 - body.z / 520))
        center_x, center_y = WORLD_RECT.center
        return (center_x + (body.x - center_x) * depth,
                center_y + (body.y - center_y) * depth,
                body.radius * depth)

    def draw(self, surface, small_font):
        draw_order = sorted(enumerate(self.bodies), key=lambda item: item[1].z)
        for index, body in draw_order:
            projected_x, projected_y, projected_radius = self.project(body)
            if self.show_trails and len(body.trail) > 1:
                points = []
                for x, y, z in body.trail:
                    trail_body = Body(x, y, 0, 0, z, 0, 0, 0, body.color, [])
                    point_x, point_y, _ = self.project(trail_body)
                    if WORLD_RECT.collidepoint(point_x, point_y):
                        points.append((int(point_x), int(point_y)))
                if len(points) > 1:
                    pygame.draw.lines(surface, body.color, False, points, 1)
            if self.show_vectors and (index == self.selected or len(self.bodies) < 12):
                tip = Body(body.x + body.vx * 16, body.y + body.vy * 16, 0, 0,
                           body.z + body.vz * 16, 0, 0, 0, body.color, [])
                end_x, end_y, _ = self.project(tip)
                pygame.draw.line(surface, body.color, (int(projected_x), int(projected_y)),
                                 (int(end_x), int(end_y)), 1)
            pygame.draw.circle(surface, (4, 7, 14), (int(projected_x), int(projected_y)), int(projected_radius + 3))
            pygame.draw.circle(surface, body.color, (int(projected_x), int(projected_y)), max(2, int(projected_radius)))
            if index == self.selected:
                pygame.draw.circle(surface, TEXT, (int(projected_x), int(projected_y)), int(projected_radius + 5), 1)
                tag = small_font.render(f"#{index + 1}", True, TEXT)
                surface.blit(tag, (projected_x + projected_radius + 7, projected_y - tag.get_height() / 2))


def draw_text(surface, font, text, position, color=TEXT):
    surface.blit(font.render(text, True, color), position)


def draw_world_backdrop(surface, is_3d):
    pygame.draw.rect(surface, BG, WORLD_RECT)
    for x in range(WORLD_RECT.left + 20, WORLD_RECT.right, 48):
        pygame.draw.line(surface, (13, 22, 37), (x, WORLD_RECT.top), (x, WORLD_RECT.bottom), 1)
    for y in range(20, WORLD_RECT.bottom, 48):
        pygame.draw.line(surface, (13, 22, 37), (WORLD_RECT.left, y), (WORLD_RECT.right, y), 1)
    for index in range(34):
        x = WORLD_RECT.left + ((index * 113) % (WORLD_RECT.width - 18)) + 9
        y = ((index * 71) % (WORLD_RECT.height - 18)) + 9
        brightness = 54 + (index * 17) % 42
        pygame.draw.circle(surface, (brightness, brightness + 8, brightness + 18), (x, y), 1)
    if is_3d:
        center = WORLD_RECT.center
        pygame.draw.ellipse(surface, (25, 63, 75), WORLD_RECT.inflate(-130, -170), 1)
        pygame.draw.line(surface, (27, 69, 75), (center[0] - 250, center[1]), (center[0] + 250, center[1]), 1)
        pygame.draw.line(surface, (27, 69, 75), (center[0], center[1] - 180), (center[0], center[1] + 180), 1)


def main():
    pygame.init()
    pygame.display.set_caption("Orbit Lab - N-Body Sandbox")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    title_font = pygame.font.Font(None, 27)
    font = pygame.font.Font(None, 19)
    small_font = pygame.font.Font(None, 16)
    sim = Simulation()
    sliders = {
        "bodies": Slider((24, 112, 244, 6), 2, 30, 8, "PLANETS", lambda value: str(round(value))),
        "gravity": Slider((24, 178, 244, 6), 0.1, 3.0, 1.0, "GRAVITY", lambda value: f"{value:.2f}"),
        "speed": Slider((24, 244, 244, 6), 0.1, 2.5, 1.0, "TIME SCALE", lambda value: f"{value:.1f}x"),
        "softening": Slider((24, 310, 244, 6), 1, 30, 8, "SOFTENING", lambda value: str(round(value))),
    }
    reset_button = Button((24, 353, 118, 34), "RESET SYSTEM", True)
    pause_button = Button((150, 353, 118, 34), "PAUSE")
    trails_button = Button((24, 408, 118, 30), "TRAILS: ON")
    vectors_button = Button((150, 408, 118, 30), "VECTORS: ON")
    mode_button = Button((24, 451, 244, 34), "MODE: 2D", True)
    running = True

    while running:
        dt = min(clock.tick(FPS) / 16.666, 2.0) * sliders["speed"].value
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            slider_changed = any(slider.handle(event) for slider in sliders.values())
            if slider_changed and event.type == pygame.MOUSEMOTION:
                continue
            if reset_button.clicked(event):
                sim.reset(round(sliders["bodies"].value))
            elif pause_button.clicked(event):
                sim.paused = not sim.paused
                pause_button.text = "RESUME" if sim.paused else "PAUSE"
            elif trails_button.clicked(event):
                sim.show_trails = not sim.show_trails
                trails_button.text = f"TRAILS: {'ON' if sim.show_trails else 'OFF'}"
            elif vectors_button.clicked(event):
                sim.show_vectors = not sim.show_vectors
                vectors_button.text = f"VECTORS: {'ON' if sim.show_vectors else 'OFF'}"
            elif mode_button.clicked(event):
                sim.set_dimension(not sim.is_3d)
                mode_button.text = f"MODE: {'3D' if sim.is_3d else '2D'}"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and WORLD_RECT.collidepoint(event.pos):
                sim.dragging_body = sim.body_at(event.pos)
                sim.drag_origin = event.pos
                if sim.dragging_body is None:
                    sim.add_body(event.pos)
                    sliders["bodies"].value = min(sliders["bodies"].maximum, len(sim.bodies))
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if sim.dragging_body is not None and sim.drag_origin is not None:
                    body = sim.bodies[sim.dragging_body]
                    body.vx = (event.pos[0] - sim.drag_origin[0]) * 0.035
                    body.vy = (event.pos[1] - sim.drag_origin[1]) * 0.035
                sim.dragging_body = None
                sim.drag_origin = None
            elif event.type == pygame.MOUSEMOTION and sim.dragging_body is not None:
                body = sim.bodies[sim.dragging_body]
                if sim.is_3d:
                    depth_scale = max(0.55, min(1.5, 1 - body.z / 520))
                    center_x, center_y = WORLD_RECT.center
                    body.x = center_x + (event.pos[0] - center_x) / depth_scale
                    body.y = center_y + (event.pos[1] - center_y) / depth_scale
                else:
                    body.x, body.y = event.pos
                body.trail.clear()
                sim.selected = sim.dragging_body
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3 and WORLD_RECT.collidepoint(event.pos):
                sim.selected = sim.body_at(event.pos)

        sim.step(dt, sliders["gravity"].value, sliders["softening"].value)
        draw_world_backdrop(screen, sim.is_3d)
        pygame.draw.rect(screen, PANEL, (0, 0, PANEL_WIDTH, HEIGHT))
        pygame.draw.line(screen, PANEL_EDGE, (PANEL_WIDTH, 0), (PANEL_WIDTH, HEIGHT), 1)
        draw_text(screen, title_font, "ORBIT LAB", (24, 24), ACCENT)
        draw_text(screen, small_font, "N-BODY GRAVITY SANDBOX", (25, 51), MUTED)
        pygame.draw.line(screen, PANEL_EDGE, (24, 77), (268, 77), 1)
        draw_text(screen, font, "SIMULATION", (24, 88), MUTED)
        for slider in sliders.values():
            slider.draw(screen, font, small_font)
        for button in (reset_button, pause_button, trails_button, vectors_button, mode_button):
            button.draw(screen, font, button.rect.collidepoint(pygame.mouse.get_pos()))
        draw_text(screen, font, "CREATE / EDIT", (24, 506), MUTED)
        draw_text(screen, small_font, "Left click empty space: add planet", (24, 534), TEXT)
        draw_text(screen, small_font, "Drag a planet: move + launch", (24, 556), TEXT)
        draw_text(screen, small_font, "Right click a planet: select", (24, 578), TEXT)
        draw_text(screen, font, f"BODIES  {len(sim.bodies):02d}", (24, 642), TEXT)
        status = "PAUSED" if sim.paused else ("3D SPACE" if sim.is_3d else "2D PLANE")
        draw_text(screen, small_font, status, (24, 668), ORANGE if sim.paused else ACCENT)
        if sim.selected is not None and sim.selected < len(sim.bodies):
            body = sim.bodies[sim.selected]
            speed = math.sqrt(body.vx ** 2 + body.vy ** 2 + body.vz ** 2)
            draw_text(screen, small_font, f"SELECTED  #{sim.selected + 1}", (150, 642), body.color)
            draw_text(screen, small_font, f"mass {body.mass:.0f}   speed {speed:.2f}", (150, 668), MUTED)
        sim.draw(screen, small_font)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()