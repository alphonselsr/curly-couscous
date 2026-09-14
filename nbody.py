"""Interactive 2D n-body sandbox with gravity and elastic collisions.

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
    mass: float
    radius: float
    color: tuple[int, int, int]
    trail: list[tuple[float, float]]


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
        self.collisions = True
        self.spawn_mass = 80.0
        self.track_all = True
        self.camera_2d_center = [WORLD_RECT.centerx, WORLD_RECT.centery]
        self.camera_2d_zoom = 1.0
        self.particles = []
        self.reset_particles()
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
            self.bodies.append(Body(x, y, -math.sin(angle) * speed, math.cos(angle) * speed,
                                    70 + index * 8, 5 + (index % 4), self.color_for(index), []))
        self.selected = 0 if self.bodies else None
        self.camera_2d_center = [WORLD_RECT.centerx, WORLD_RECT.centery]
        self.camera_2d_zoom = 1.0

    @staticmethod
    def color_for(index):
        colors = [(83, 211, 190), (255, 166, 88), (151, 126, 255), (255, 103, 115), (105, 179, 255)]
        return colors[index % len(colors)]

    def step(self, dt, gravity, softening, restitution):
        if self.paused:
            return
        substeps = max(1, min(4, math.ceil(dt)))
        sub_dt = dt / substeps
        for _ in range(substeps):
            accelerations = [(0.0, 0.0) for _ in self.bodies]
            for first_index, first in enumerate(self.bodies):
                for second_index in range(first_index + 1, len(self.bodies)):
                    second = self.bodies[second_index]
                    dx = second.x - first.x
                    dy = second.y - first.y
                    distance_sq = max(dx * dx + dy * dy + softening * softening, 0.01)
                    distance = math.sqrt(distance_sq)
                    force = gravity / distance_sq
                    ax = force * dx / distance
                    ay = force * dy / distance
                    accelerations[first_index] = (accelerations[first_index][0] + ax * second.mass,
                                                   accelerations[first_index][1] + ay * second.mass)
                    accelerations[second_index] = (accelerations[second_index][0] - ax * first.mass,
                                                    accelerations[second_index][1] - ay * first.mass)

            for index, body in enumerate(self.bodies):
                body.vx += accelerations[index][0] * sub_dt
                body.vy += accelerations[index][1] * sub_dt
                body.x += body.vx * sub_dt
                body.y += body.vy * sub_dt
            if self.collisions:
                self.resolve_collisions(restitution)

        if self.show_trails:
            for body in self.bodies:
                if not body.trail or math.hypot(body.x - body.trail[-1][0], body.y - body.trail[-1][1]) > 3:
                    body.trail.append((body.x, body.y))
                    if len(body.trail) > 90:
                        body.trail.pop(0)

    def resolve_collisions(self, restitution):
        for first_index, first in enumerate(self.bodies):
            for second in self.bodies[first_index + 1:]:
                dx = second.x - first.x
                dy = second.y - first.y
                distance_sq = dx * dx + dy * dy
                minimum_distance = first.radius + second.radius
                if distance_sq >= minimum_distance * minimum_distance:
                    continue
                distance = math.sqrt(distance_sq) if distance_sq > 0.0001 else 0.01
                nx, ny = dx / distance, dy / distance
                overlap = minimum_distance - distance
                total_mass = first.mass + second.mass
                first.x -= nx * overlap * second.mass / total_mass
                first.y -= ny * overlap * second.mass / total_mass
                second.x += nx * overlap * first.mass / total_mass
                second.y += ny * overlap * first.mass / total_mass
                relative_velocity = (second.vx - first.vx) * nx + (second.vy - first.vy) * ny
                if relative_velocity >= 0:
                    continue
                impulse = -(1 + restitution) * relative_velocity / (1 / first.mass + 1 / second.mass)
                first.vx -= impulse * nx / first.mass
                first.vy -= impulse * ny / first.mass
                second.vx += impulse * nx / second.mass
                second.vy += impulse * ny / second.mass

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
        world_position = self.screen_to_world(position)
        self.bodies.append(Body(world_position[0], world_position[1], velocity[0], velocity[1],
                                self.spawn_mass, 6, self.color_for(len(self.bodies)), []))
        self.selected = len(self.bodies) - 1
        if self.track_all:
            self.update_2d_tracking()

    def update_2d_tracking(self):
        if not self.track_all or not self.bodies:
            return
        min_x = min(body.x - body.radius for body in self.bodies)
        max_x = max(body.x + body.radius for body in self.bodies)
        min_y = min(body.y - body.radius for body in self.bodies)
        max_y = max(body.y + body.radius for body in self.bodies)
        target_center = [(min_x + max_x) * 0.5, (min_y + max_y) * 0.5]
        available_width = WORLD_RECT.width - 72
        available_height = WORLD_RECT.height - 72
        target_zoom = min(1.0, available_width / max(max_x - min_x, 1),
                          available_height / max(max_y - min_y, 1))
        self.camera_2d_center[0] = target_center[0]
        self.camera_2d_center[1] = target_center[1]
        self.camera_2d_zoom = target_zoom

    def screen_to_world(self, position):
        if not self.track_all:
            return position
        return ((position[0] - WORLD_RECT.centerx) / self.camera_2d_zoom + self.camera_2d_center[0],
                (position[1] - WORLD_RECT.centery) / self.camera_2d_zoom + self.camera_2d_center[1])

    def reset_particles(self):
        self.particles = []
        for index in range(150):
            angle = index * 2.399963
            distance = 180 + (index * 47) % 620
            self.particles.append((
                WORLD_RECT.centerx + math.cos(angle) * distance,
                WORLD_RECT.centery + math.sin(angle * 1.31) * distance * 0.7,
                1 + index % 2,
                38 + (index * 17) % 46,
            ))

    def project(self, body):
        if not self.track_all:
            return body.x, body.y, body.radius
        return (WORLD_RECT.centerx + (body.x - self.camera_2d_center[0]) * self.camera_2d_zoom,
                WORLD_RECT.centery + (body.y - self.camera_2d_center[1]) * self.camera_2d_zoom,
                body.radius * self.camera_2d_zoom)

    def draw_particles(self, surface):
        particle_layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for x, y, radius, brightness in self.particles:
            if self.track_all:
                screen_x = int(WORLD_RECT.centerx + (x - self.camera_2d_center[0]) * self.camera_2d_zoom)
                screen_y = int(WORLD_RECT.centery + (y - self.camera_2d_center[1]) * self.camera_2d_zoom)
            else:
                screen_x, screen_y = int(x), int(y)
            if WORLD_RECT.collidepoint(screen_x, screen_y):
                pygame.draw.circle(particle_layer, (150, 202, 221, brightness),
                                   (screen_x, screen_y), max(1, int(radius * self.camera_2d_zoom)))
        surface.blit(particle_layer, (0, 0))

    def draw(self, surface, small_font):
        trail_layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for index, body in enumerate(self.bodies):
            projected_x, projected_y, projected_radius = self.project(body)
            if self.show_trails and len(body.trail) > 1:
                if self.track_all:
                    trail_points = [(int(WORLD_RECT.centerx + (x - self.camera_2d_center[0]) * self.camera_2d_zoom),
                                     int(WORLD_RECT.centery + (y - self.camera_2d_center[1]) * self.camera_2d_zoom))
                                    for x, y in body.trail]
                else:
                    trail_points = [(int(x), int(y)) for x, y in body.trail]
                for trail_index in range(1, len(trail_points)):
                    alpha = int(12 + 105 * trail_index / len(trail_points))
                    pygame.draw.line(trail_layer, (*body.color, alpha), trail_points[trail_index - 1],
                                     trail_points[trail_index], 2)
        surface.blit(trail_layer, (0, 0))
        for index, body in enumerate(self.bodies):
            projected_x, projected_y, projected_radius = self.project(body)
            if self.show_vectors and (index == self.selected or len(self.bodies) < 12):
                end_x, end_y, _ = self.project(Body(body.x + body.vx * 16, body.y + body.vy * 16,
                                                     0, 0, body.mass, body.radius, body.color, []))
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


def draw_world_backdrop(surface):
    for y in range(WORLD_RECT.top, WORLD_RECT.bottom):
        ratio = y / HEIGHT
        color = (8 + int(7 * ratio), 12 + int(9 * ratio), 24 + int(16 * ratio))
        pygame.draw.line(surface, color, (WORLD_RECT.left, y), (WORLD_RECT.right, y))
    for x in range(WORLD_RECT.left + 20, WORLD_RECT.right, 48):
        pygame.draw.line(surface, (16, 26, 43), (x, WORLD_RECT.top), (x, WORLD_RECT.bottom), 1)
    for y in range(20, WORLD_RECT.bottom, 48):
        pygame.draw.line(surface, (16, 26, 43), (WORLD_RECT.left, y), (WORLD_RECT.right, y), 1)
    for index in range(34):
        x = WORLD_RECT.left + ((index * 113) % (WORLD_RECT.width - 18)) + 9
        y = ((index * 71) % (WORLD_RECT.height - 18)) + 9
        brightness = 54 + (index * 17) % 42
        pygame.draw.circle(surface, (brightness, brightness + 8, brightness + 18), (x, y), 1)


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
    tracking_button = Button((24, 451, 118, 30), "TRACK: ON", True)
    collisions_button = Button((150, 451, 118, 30), "COLLISIONS: ON", True)
    running = True

    while running:
        dt = min(clock.tick(FPS) / 16.666, 2.0) * sliders["speed"].value
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            slider_changed = any(slider.handle(event) for slider in sliders.values())
            if slider_changed:
                continue
            if reset_button.clicked(event):
                sim.reset(round(sliders["bodies"].value))
            elif pause_button.clicked(event):
                sim.paused = not sim.paused
                pause_button.text = "RESUME" if sim.paused else "PAUSE"
            elif trails_button.clicked(event):
                sim.show_trails = not sim.show_trails
            elif tracking_button.clicked(event):
                sim.track_all = not sim.track_all
                tracking_button.text = f"TRACK: {'ON' if sim.track_all else 'OFF'}"
            elif collisions_button.clicked(event):
                sim.collisions = not sim.collisions
                collisions_button.text = f"COLLISIONS: {'ON' if sim.collisions else 'OFF'}"
            elif vectors_button.clicked(event):
                sim.show_vectors = not sim.show_vectors
                vectors_button.text = f"VECTORS: {'ON' if sim.show_vectors else 'OFF'}"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and WORLD_RECT.collidepoint(event.pos):
                sim.dragging_body = sim.body_at(event.pos)
                sim.drag_origin = event.pos
                if sim.dragging_body is None:
                    sim.add_body(event.pos)
                    sliders["bodies"].value = min(sliders["bodies"].maximum, len(sim.bodies))
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if sim.dragging_body is not None and sim.drag_origin is not None:
                    body = sim.bodies[sim.dragging_body]
                    origin = sim.screen_to_world(sim.drag_origin)
                    release = sim.screen_to_world(event.pos)
                    body.vx = (release[0] - origin[0]) * 0.035
                    body.vy = (release[1] - origin[1]) * 0.035
                sim.dragging_body = None
                sim.drag_origin = None
            elif event.type == pygame.MOUSEMOTION and sim.dragging_body is not None:
                body = sim.bodies[sim.dragging_body]
                world_position = sim.screen_to_world(event.pos)
                body.x, body.y = world_position
                body.trail.clear()
                sim.selected = sim.dragging_body
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3 and WORLD_RECT.collidepoint(event.pos):
                sim.selected = sim.body_at(event.pos)

        sim.step(dt, sliders["gravity"].value, sliders["softening"].value, 0.82)
        sim.update_2d_tracking()
        draw_world_backdrop(screen)
        pygame.draw.rect(screen, PANEL, (0, 0, PANEL_WIDTH, HEIGHT))
        pygame.draw.line(screen, PANEL_EDGE, (PANEL_WIDTH, 0), (PANEL_WIDTH, HEIGHT), 1)
        draw_text(screen, title_font, "ORBIT LAB", (24, 24), ACCENT)
        draw_text(screen, small_font, "N-BODY GRAVITY SANDBOX", (25, 51), MUTED)
        pygame.draw.line(screen, PANEL_EDGE, (24, 77), (268, 77), 1)
        draw_text(screen, font, "SIMULATION", (24, 88), MUTED)
        for slider in sliders.values():
            slider.draw(screen, font, small_font)
        for button in (reset_button, pause_button, trails_button, vectors_button,
                       tracking_button, collisions_button):
            button.draw(screen, font, button.rect.collidepoint(pygame.mouse.get_pos()))
        draw_text(screen, font, "CREATE / EDIT", (24, 506), MUTED)
        draw_text(screen, small_font, "Empty click: add planet", (24, 534), TEXT)
        draw_text(screen, small_font, "Drag planet: move + launch", (24, 556), TEXT)
        draw_text(screen, small_font, "Right click: select", (24, 578), TEXT)
        draw_text(screen, small_font, "Tracking keeps every planet visible", (24, 600), ACCENT if sim.track_all else MUTED)
        draw_text(screen, font, f"BODIES  {len(sim.bodies):02d}", (24, 642), TEXT)
        status = "PAUSED" if sim.paused else "2D GRAVITY FIELD"
        draw_text(screen, small_font, status, (24, 668), ORANGE if sim.paused else ACCENT)
        if sim.selected is not None and sim.selected < len(sim.bodies):
            body = sim.bodies[sim.selected]
            speed = math.hypot(body.vx, body.vy)
            draw_text(screen, small_font, f"SELECTED  #{sim.selected + 1}", (150, 642), body.color)
            draw_text(screen, small_font, f"mass {body.mass:.0f}   speed {speed:.2f}", (150, 668), MUTED)
        sim.draw_particles(screen)
        sim.draw(screen, small_font)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()